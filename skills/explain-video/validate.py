#!/usr/bin/env python3
"""Check an explain-video spec (video.json) before any paid call.

Usage: validate.py PATH/TO/video.json
Exit 0 and print a one-line summary when valid; exit 1 and print one error per line.
Stdlib only.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

TYPES = {"title", "map", "steps", "before_after", "numbers", "takeaways"}
STATUSES = {"auto", "human", "risk", "failed", "done", "verified", "unverified", "pending", "todo"}
ITEM_KEY = {"steps": "items", "before_after": "pairs", "numbers": "stats", "takeaways": "cards"}
MAX_ITEMS = {"steps": 10, "before_after": 6, "numbers": 6, "takeaways": 5}
REQUIRED = {"steps": ("text", "status"), "before_after": ("before", "after"),
            "numbers": ("label", "value"), "takeaways": ("title", "status")}
MAX_WORDS = 450
MAX_NODES = 12
MAX_CHAIN = 8
MAX_CHAIN_LABELLED = 6  # labelled arrows take their own layout rank, so maps get wider
SCENE_ID = re.compile(r"[A-Za-z0-9_-]+")
MAX_LINE_CHARS = 120
WPM = 150
EM_DASH = "\u2014"


def walk_strings(obj, path="$"):
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for key, val in obj.items():
            yield from walk_strings(val, f"{path}.{key}")
    elif isinstance(obj, list):
        for i, val in enumerate(obj):
            yield from walk_strings(val, f"{path}[{i}]")


def word_count(spec: dict) -> int:
    return sum(len(str(line.get("say", "")).split())
               for scene in spec.get("scenes", []) for line in scene.get("lines", []))


def longest_chain(node_ids, edges) -> int:
    """Boxes in a row the layout needs: longest path after dropping back edges (dagre reverses them)."""
    nxt = {n: [] for n in node_ids}
    for e in edges:
        if e.get("from") in nxt and e.get("to") in nxt and e["from"] != e["to"]:
            nxt[e["from"]].append(e["to"])
    state: dict = {}
    dag = {n: [] for n in node_ids}

    def visit(n):
        state[n] = "open"
        for m in nxt[n]:
            if state.get(m) == "open":
                continue  # back edge: drawn as a returning arrow, adds no rank
            dag[n].append(m)
            if m not in state:
                visit(m)
        state[n] = "done"

    for n in sorted(node_ids, key=str):
        if n not in state:
            visit(n)
    memo: dict = {}

    def depth(n):
        if n not in memo:
            memo[n] = 1 + max((depth(m) for m in dag[n]), default=0)
        return memo[n]

    return max((depth(n) for n in node_ids), default=0)


def check_graph(graph, errs: list[str]) -> tuple[set, set]:
    node_ids, edge_ids = set(), set()
    if not isinstance(graph, dict):
        errs.append("graph: must be an object with nodes and edges lists")
        return node_ids, edge_ids
    for key in ("nodes", "edges"):
        if not isinstance(graph.get(key), list):
            errs.append(f"graph.{key} must be a list")
    nodes = graph["nodes"] if isinstance(graph.get("nodes"), list) else []
    edges = graph["edges"] if isinstance(graph.get("edges"), list) else []
    for i, n in enumerate(nodes):
        nid = n.get("id")
        if not nid or nid in node_ids:
            errs.append(f"graph.nodes[{i}]: missing or duplicate id {nid!r}")
        node_ids.add(nid)
        if not n.get("title"):
            errs.append(f"graph.nodes[{i}]: missing title")
        for k in ("title", "sub"):
            if k in n and not isinstance(n[k], str):
                errs.append(f"graph.nodes[{i}]: {k} must be text")
        if n.get("status") not in STATUSES:
            errs.append(f"graph.nodes[{i}]: bad status {n.get('status')!r}")
    if len(node_ids) > MAX_NODES:
        errs.append(f"graph: {len(node_ids)} nodes, max {MAX_NODES}; split into two maps")
    for i, e in enumerate(edges):
        eid = e.get("id")
        if not eid or eid in edge_ids:
            errs.append(f"graph.edges[{i}]: missing or duplicate id {eid!r}")
        edge_ids.add(eid)
        for end in ("from", "to"):
            if e.get(end) not in node_ids:
                errs.append(f"graph.edges[{i}]: {end} {e.get(end)!r} is not a node")
        if e.get("from") == e.get("to"):
            errs.append(f"graph.edges[{i}]: edge points to itself")
    chain = longest_chain(node_ids, edges)
    labelled = any(e.get("label") for e in edges)
    limit = MAX_CHAIN_LABELLED if labelled else MAX_CHAIN
    if chain > limit:
        why = " with labelled arrows (drop the labels for up to 8)" if labelled else ""
        errs.append(f"graph: chain of {chain} nodes, max {limit}{why}; use a steps scene for long sequences")
    return node_ids, edge_ids


def check_scene(si: int, s: dict, node_ids: set, edge_ids: set, seen: set, errs: list[str]) -> None:
    where = f"scenes[{si}]"
    stype = s.get("type")
    if stype not in TYPES:
        errs.append(f"{where}: bad type {stype!r}")
        return
    if not s.get("id") or s["id"] in seen:
        errs.append(f"{where}: missing or duplicate id {s.get('id')!r}")
    elif not isinstance(s["id"], str) or not SCENE_ID.fullmatch(s["id"]):
        errs.append(f"{where}: id {s['id']!r} may use only letters, digits, - and _")
    seen.add(s.get("id"))
    if not s.get("chip"):
        errs.append(f"{where}: missing chip")
    if (stype == "map" or (stype == "takeaways" and s.get("mini_map"))) and not node_ids:
        errs.append(f"{where}: {stype if stype == 'map' else 'mini_map'} needs graph nodes")
    items: list = []
    if stype in ITEM_KEY:
        key = ITEM_KEY[stype]
        items = s.get(key) if isinstance(s.get(key), list) else []
        if not items:
            errs.append(f"{where}: {key} must be a non-empty list")
        elif len(items) > MAX_ITEMS[stype]:
            errs.append(f"{where}: {len(items)} {key}, max {MAX_ITEMS[stype]}")
        for ii, it in enumerate(items):
            for k in REQUIRED[stype] + ("sub", "prefix", "suffix"):
                if k in REQUIRED[stype] and not it.get(k):
                    errs.append(f"{where}.{key}[{ii}]: missing {k}")
                elif k in it and not isinstance(it[k], str):
                    errs.append(f"{where}.{key}[{ii}]: {k} must be text")
            if "status" in it and it["status"] not in STATUSES:
                errs.append(f"{where}.{key}[{ii}]: bad status {it['status']!r}")
    lines = s.get("lines")
    if not isinstance(lines, list) or not lines:
        errs.append(f"{where}: needs at least one line")
        return
    for li, line in enumerate(lines):
        lw = f"{where}.lines[{li}]"
        if not str(line.get("say", "")).strip():
            errs.append(f"{lw}: empty say")
        for field in ("say", "show"):
            if field in line and not isinstance(line[field], str):
                errs.append(f"{lw}: {field} must be text")
            n = len(str(line.get(field, "")))
            if n > MAX_LINE_CHARS:
                errs.append(f"{lw}: {field} is {n} characters, max {MAX_LINE_CHARS}")
        cue = line.get("cue") or {}
        for nid in cue.get("nodes", []):
            if nid not in node_ids:
                errs.append(f"{lw}: cue node {nid!r} is not in graph")
        for eid in cue.get("edges", []) + cue.get("rev", []):
            if eid not in edge_ids:
                errs.append(f"{lw}: cue edge {eid!r} is not in graph")
        if "reveal" in cue:
            r = cue["reveal"]
            if not isinstance(r, int) or not 1 <= r <= len(items):
                errs.append(f"{lw}: reveal {r!r} out of range 1..{len(items)}")


def validate(spec: dict) -> list[str]:
    errs: list[str] = []
    if not isinstance(spec.get("title"), str) or not spec["title"].strip():
        errs.append("title: missing")
    scenes = spec.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        return errs + ["scenes: must be a non-empty list"]
    if "graph" in spec:
        node_ids, edge_ids = check_graph(spec["graph"], errs)
    else:
        node_ids, edge_ids = set(), set()
    seen: set = set()
    for si, s in enumerate(scenes):
        check_scene(si, s, node_ids, edge_ids, seen, errs)
    for path, text in walk_strings(spec):
        if EM_DASH in text:
            errs.append(f"{path}: contains an em dash")
    words = word_count(spec)
    if words > MAX_WORDS:
        errs.append(f"script: {words} words, max {MAX_WORDS}")
    return errs


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: validate.py video.json")
        return 2
    spec = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    errs = validate(spec)
    if errs:
        print("\n".join(errs))
        return 1
    words = word_count(spec)
    print(f"OK: {len(spec['scenes'])} scenes, {words} words, about {round(words / WPM * 60)} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
