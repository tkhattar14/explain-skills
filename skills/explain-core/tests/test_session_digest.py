import io
import json
import os
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import session_digest as sd  # noqa: E402


def write_jsonl(path: Path, records) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(rec if isinstance(rec, str) else json.dumps(rec))
            fh.write("\n")


RECORDS = [
    {"type": "ai-title", "aiTitle": "Fix webhook race", "sessionId": "abc"},
    {"type": "user", "timestamp": "2026-10-01T10:00:00Z", "cwd": "/repo",
     "message": {"role": "user", "content": "Please fix the webhook race"}},
    {"type": "assistant", "timestamp": "2026-10-01T10:01:00Z", "message": {"content": [
        {"type": "thinking", "thinking": "secret reasoning"},
        {"type": "text", "text": "I will look at the webhook."},
        {"type": "tool_use", "id": "t1", "name": "Bash",
         "input": {"command": "pytest tests/test_webhook.py", "description": "Run webhook tests"}},
    ]}},
    {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": "t1", "is_error": True,
         "content": "FAILED test_concurrent - E11000 duplicate key"}]}},
    {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "t2", "name": "Agent", "input": {"description": "Map the code", "prompt": "Find..."}}]}},
    {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": "t2",
         "content": [{"type": "text", "text": "Report: the race is in payment_webhook.py"}]}]}},
    {"type": "user", "message": {"content": "<system-reminder>CLAUDE.md contents</system-reminder>"}},
    {"type": "user", "message": {"content": "<task-notification><result>Agent done: 3 fixes</result></task-notification>"}},
    {"type": "assistant", "isSidechain": True, "message": {"content": [{"type": "text", "text": "sidechain chatter"}]}},
    {"type": "file-history-snapshot", "snapshot": {}},
    "this is not json",
    {"type": "assistant", "timestamp": "2026-10-01T11:00:00Z",
     "message": {"content": [{"type": "text", "text": "Done. Tests not run yet."}]}},
]

EXPECTED = [
    "[U] Please fix the webhook race",
    "[A] I will look at the webhook.",
    "[T] Bash: pytest tests/test_webhook.py",
    "[E] Bash: FAILED test_concurrent - E11000 duplicate key",
    "[T] Agent: Map the code",
    "[R] Agent: Report: the race is in payment_webhook.py",
    "[R] <task-notification><result>Agent done: 3 fixes</result></task-notification>",
    "[A] Done. Tests not run yet.",
]


class DigestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.path = self.root / "abc123.jsonl"
        write_jsonl(self.path, RECORDS)

    def tearDown(self):
        self.tmp.cleanup()

    def test_build_digest_keeps_the_right_lines_in_order(self):
        meta, lines = sd.build_digest(self.path)
        self.assertEqual(lines, EXPECTED)
        self.assertEqual(meta["title"], "Fix webhook race")
        self.assertEqual(meta["cwd"], "/repo")
        self.assertEqual(meta["first"], "2026-10-01T10:00:00Z")
        self.assertEqual(meta["last"], "2026-10-01T11:00:00Z")

    def test_thinking_and_sidechain_are_dropped(self):
        _, lines = sd.build_digest(self.path)
        joined = "\n".join(lines)
        self.assertNotIn("secret reasoning", joined)
        self.assertNotIn("sidechain chatter", joined)

    def test_compaction_summary_is_kept(self):
        path = self.root / "c.jsonl"
        write_jsonl(path, [{"type": "user", "isCompactSummary": True,
                            "message": {"content": "Summary: built the CLI, tests pass"}}])
        _, lines = sd.build_digest(path)
        self.assertEqual(lines, ["[C] Summary: built the CLI, tests pass"])

    def test_empty_transcript_gives_header_only(self):
        path = self.root / "empty.jsonl"
        write_jsonl(path, [{"type": "permission-mode", "mode": "default"}])
        meta, lines = sd.build_digest(path)
        self.assertEqual(lines, [])
        chunks = sd.render(meta, lines, 60000)
        self.assertEqual(len(chunks), 1)
        self.assertTrue(chunks[0].startswith("# Session digest: empty"))

    def test_clip_flattens_and_trims(self):
        self.assertEqual(sd.clip("a\n  b", 10), "a b")
        self.assertEqual(sd.clip("x" * 20, 10), "xxxxxxx...")

    def test_render_chunks_stay_under_the_limit(self):
        meta = {"title": "T", "cwd": "/r", "first": None, "last": None, "session": "s"}
        lines = [f"[U] {'x' * 900}" for _ in range(30)]
        chunks = sd.render(meta, lines, 6000)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 6000)
            self.assertTrue(chunk.startswith("# Session digest: T"))
        self.assertEqual(sum(1 for c in chunks for line in c.splitlines() if line.startswith("[U] ")), 30)

    def test_resolve_by_prefix_latest_word_skip_and_exclude(self):
        projects = self.root / "projects"
        (projects / "-Users-a-SHOP").mkdir(parents=True)
        (projects / "-Users-a-BLOG").mkdir(parents=True)
        files = {
            "old": projects / "-Users-a-SHOP" / "aaa111.jsonl",
            "new": projects / "-Users-a-SHOP" / "bbb222.jsonl",
            "blog": projects / "-Users-a-BLOG" / "ccc333.jsonl",
        }
        now = time.time()
        for i, (_, p) in enumerate(files.items()):
            p.write_text("{}\n")
            os.utime(p, (now + i, now + i))
        self.assertEqual(sd.resolve("aaa", projects=projects), files["old"])
        self.assertEqual(sd.resolve("latest:shop", projects=projects), files["new"])
        self.assertEqual(sd.resolve("latest:shop", skip=1, projects=projects), files["old"])
        self.assertEqual(sd.resolve("latest", projects=projects), files["blog"])
        self.assertEqual(sd.resolve("latest", projects=projects, exclude="ccc"), files["new"])
        self.assertEqual(sd.resolve(str(files["blog"])), files["blog"])
        with self.assertRaises(SystemExit):
            sd.resolve("zzz", projects=projects)

    def test_main_writes_digest_md(self):
        out = self.root / "out"
        with redirect_stdout(io.StringIO()):
            self.assertEqual(sd.main([str(self.path), "--out", str(out)]), 0)
        text = (out / "digest.md").read_text()
        self.assertIn("Fix webhook race", text)
        self.assertIn("[E] Bash: FAILED", text)

    def test_main_writes_parts_when_long(self):
        path = self.root / "long.jsonl"
        write_jsonl(path, [{"type": "user", "message": {"content": "y" * 1900}} for _ in range(10)])
        out = self.root / "out2"
        with redirect_stdout(io.StringIO()):
            sd.main([str(path), "--out", str(out), "--max-chars", "5000"])
        parts = sorted(p.name for p in out.glob("digest.part*.md"))
        self.assertGreaterEqual(len(parts), 4)
        self.assertFalse((out / "digest.md").exists())

    def test_successful_bash_output_is_kept_as_evidence(self):
        path = self.root / "ok.jsonl"
        write_jsonl(path, [
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "b1", "name": "Bash", "input": {"command": "pytest -q"}},
                {"type": "tool_use", "id": "r1", "name": "Read", "input": {"file_path": "/x.py"}}]}},
            {"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "b1", "content": "....\n14 passed in 0.31s"},
                {"type": "tool_result", "tool_use_id": "r1", "content": "def x(): pass"}]}},
        ])
        _, lines = sd.build_digest(path)
        self.assertEqual(lines, ["[T] Bash: pytest -q", "[T] Read: /x.py", "[O] Bash: .... 14 passed in 0.31s"])

    def test_list_rows_say_modified(self):
        projects = self.root / "projects"
        (projects / "-Users-a-SHOP").mkdir(parents=True)
        write_jsonl(projects / "-Users-a-SHOP" / "abc.jsonl", [{"type": "ai-title", "aiTitle": "Docker check"}])
        with mock.patch.object(sd, "PROJECTS", projects):
            rows = sd.list_sessions("shop")
        self.assertEqual(len(rows), 1)
        self.assertIn("modified ", rows[0])
        self.assertIn("Docker check", rows[0])

    def test_long_command_output_keeps_the_verdict_at_the_end(self):
        path = self.root / "long_out.jsonl"
        out = "collected 14 items\ntests/test_paylink.py " + "." * 300 + "\n14 passed in 0.31s"
        write_jsonl(path, [
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "b1", "name": "Bash", "input": {"command": "pytest"}}]}},
            {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "b1", "content": out}]}},
        ])
        _, lines = sd.build_digest(path)
        self.assertTrue(lines[-1].startswith("[O] Bash: collected 14 items"))
        self.assertTrue(lines[-1].endswith("14 passed in 0.31s"))
        self.assertLessEqual(len(lines[-1]), 220)

    def test_empty_ref_is_refused(self):
        projects = self.root / "projects"
        (projects / "-Users-a-OTHER").mkdir(parents=True)
        write_jsonl(projects / "-Users-a-OTHER" / "zzz999.jsonl", [{"type": "ai-title", "aiTitle": "someone else"}])
        for ref in ("", "  "):
            with self.assertRaises(SystemExit):
                sd.resolve(ref, projects=projects)


if __name__ == "__main__":
    unittest.main()
