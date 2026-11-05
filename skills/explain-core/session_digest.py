#!/usr/bin/env python3
"""Shrink a Claude Code session transcript (.jsonl) into a compact markdown digest.

Usage:
  session_digest.py REF [--out DIR] [--max-chars N] [--skip N]
  session_digest.py --list [WORD]

REF is a path to a .jsonl, a session-id prefix, or "latest" / "latest:WORD" (newest
transcript, optionally only in project folders whose name contains WORD). "latest"
refs never pick the session you are in (CLAUDE_CODE_SESSION_ID). --skip N skips the
N newest matches.

Writes digest.md, or digest.part1.md, digest.part2.md, ... when longer than
--max-chars, into --out (default: current directory). Prints one path per line.
Stdlib only. Streams the transcript, so 70 MB files are fine.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path

PROJECTS = Path.home() / ".claude" / "projects"
LIMIT = {"U": 2000, "A": 1500, "T": 200, "E": 300, "O": 200, "R": 3000, "C": 4000}
KEY_ARGS = ("file_path", "command", "pattern", "url", "description", "skill", "query", "prompt", "path")
AGENT_TOOLS = {"Agent", "Task"}
EVIDENCE_TOOLS = {"Bash"}  # successful output kept: it is how a step is shown to be verified
REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)
LEGEND = "[U] user, [A] assistant, [T] tool call, [O] command output, [E] tool error, [R] agent report, [C] compaction summary"


def clip(text: object, limit: int) -> str:
    flat = " ".join(str(text).split())
    return flat if len(flat) <= limit else flat[: limit - 3] + "..."


def clip_ends(text: object, limit: int, head: int = 60) -> str:
    """Like clip, but keeps the start and the end: command verdicts ("14 passed") come last."""
    flat = " ".join(str(text).split())
    if len(flat) <= limit:
        return flat
    return flat[:head] + " ... " + flat[-(limit - head - 5):]


def candidates(word: str = "", projects: Path | None = None) -> list[Path]:
    """All top-level transcripts, newest first, optionally only in folders whose name contains word."""
    projects = projects or PROJECTS
    word = word.lower()
    files = [p for p in projects.glob("*/*.jsonl") if word in p.parent.name.lower()]
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


def resolve(ref: str, skip: int = 0, projects: Path | None = None, exclude: str | None = None) -> Path:
    projects = projects or PROJECTS
    if not ref.strip():
        raise SystemExit("session_digest: empty session reference (is CLAUDE_CODE_SESSION_ID set?)")
    if ref == "latest" or ref.startswith("latest:"):
        hits = [p for p in candidates(ref.partition(":")[2], projects)
                if not (exclude and p.stem.startswith(exclude))]
    else:
        path = Path(os.path.expanduser(ref))
        if path.suffix == ".jsonl" and path.is_file():
            return path
        hits = sorted(projects.glob(f"*/{ref}*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    if len(hits) <= skip:
        raise SystemExit(f"session_digest: no transcript matches {ref!r} (skip={skip})")
    return hits[skip]


def text_of(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return ""


def tool_line(block: dict) -> str:
    name = block.get("name", "?")
    args = block.get("input") or {}
    for key in KEY_ARGS:
        if args.get(key):
            return f"[T] {name}: {clip(args[key], LIMIT['T'])}"
    return f"[T] {name}"


def block_line(kind: str, block: dict, names: dict[str, str]) -> str | None:
    btype = block.get("type")
    if btype == "text":
        text = REMINDER.sub("", block.get("text", "")).strip()
        if not text:
            return None
        if kind == "assistant":
            return f"[A] {clip(text, LIMIT['A'])}"
        if "<task-notification>" in text:
            return f"[R] {clip(text, LIMIT['R'])}"
        return f"[U] {clip(text, LIMIT['U'])}"
    if btype == "tool_use":
        names[block.get("id", "")] = block.get("name", "?")
        return tool_line(block)
    if btype == "tool_result":
        name = names.get(block.get("tool_use_id", ""), "?")
        text = text_of(block.get("content"))
        if block.get("is_error"):
            return f"[E] {name}: {clip(text, LIMIT['E'])}"
        if name in AGENT_TOOLS and "Async agent launched" not in text:
            return f"[R] {name}: {clip(text, LIMIT['R'])}"
        if name in EVIDENCE_TOOLS and text.strip():
            return f"[O] {name}: {clip_ends(text, LIMIT['O'])}"
    return None


def build_digest(path: Path) -> tuple[dict, list[str]]:
    meta = {"title": None, "cwd": None, "first": None, "last": None, "session": path.stem}
    names: dict[str, str] = {}
    out: list[str] = []
    with path.open(encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(rec, dict):
                continue
            if rec.get("timestamp"):
                meta["first"] = meta["first"] or rec["timestamp"]
                meta["last"] = rec["timestamp"]
            if rec.get("cwd") and not meta["cwd"]:
                meta["cwd"] = rec["cwd"]
            kind = rec.get("type")
            if kind == "ai-title":
                meta["title"] = rec.get("aiTitle") or meta["title"]
                continue
            if kind == "summary" or rec.get("isCompactSummary"):
                text = rec.get("summary") or text_of((rec.get("message") or {}).get("content"))
                if text:
                    out.append(f"[C] {clip(text, LIMIT['C'])}")
                continue
            if kind not in ("user", "assistant") or rec.get("isSidechain"):
                continue
            content = (rec.get("message") or {}).get("content")
            if isinstance(content, str):
                content = [{"type": "text", "text": content}]
            if not isinstance(content, list):
                continue
            for block in content:
                if isinstance(block, dict):
                    line = block_line(kind, block, names)
                    if line:
                        out.append(line)
    return meta, out


def render(meta: dict, lines: list[str], max_chars: int) -> list[str]:
    header = (
        f"# Session digest: {meta['title'] or meta['session']}\n\n"
        f"- Session: {meta['session']}\n- Folder: {meta['cwd']}\n"
        f"- From: {meta['first']}\n- To: {meta['last']}\n- Legend: {LEGEND}\n\n"
    )
    chunks: list[str] = []
    current = header
    for line in lines:
        if len(current) + len(line) + 1 > max_chars and current != header:
            chunks.append(current)
            current = header
        current += line + "\n"
    chunks.append(current)
    return chunks


def list_sessions(word: str, limit: int = 10) -> list[str]:
    rows = []
    for path in candidates(word)[:limit]:
        title = None
        with path.open(encoding="utf-8", errors="replace") as fh:
            for i, raw in enumerate(fh):
                if i > 400:
                    break
                if '"ai-title"' in raw:
                    try:
                        title = json.loads(raw).get("aiTitle")
                    except json.JSONDecodeError:
                        pass
                    break
        when = time.strftime("%Y-%m-%d %H:%M", time.localtime(path.stat().st_mtime))
        mb = path.stat().st_size / 1e6
        rows.append(f"{path.stem[:8]}  modified {when}  {mb:6.1f} MB  {path.parent.name}  {title or '(no title)'}")
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Shrink a Claude Code transcript into a markdown digest.")
    ap.add_argument("ref", nargs="?", default="latest")
    ap.add_argument("--out", default=".")
    ap.add_argument("--max-chars", type=int, default=60000)
    ap.add_argument("--skip", type=int, default=0)
    ap.add_argument("--list", metavar="WORD", nargs="?", const="", default=None)
    args = ap.parse_args(argv)
    if args.list is not None:
        print("\n".join(list_sessions(args.list)))
        return 0
    if args.max_chars < 5000:
        ap.error("--max-chars must be at least 5000")
    path = resolve(args.ref, args.skip, exclude=os.environ.get("CLAUDE_CODE_SESSION_ID"))
    meta, lines = build_digest(path)
    chunks = render(meta, lines, args.max_chars)
    out = Path(os.path.expanduser(args.out))
    out.mkdir(parents=True, exist_ok=True)
    names = ["digest.md"] if len(chunks) == 1 else [f"digest.part{i}.md" for i in range(1, len(chunks) + 1)]
    for name, text in zip(names, chunks):
        (out / name).write_text(text, encoding="utf-8")
        print(out / name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
