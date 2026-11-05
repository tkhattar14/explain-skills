---
name: explain-all
description: Use when the user asks to explain something in all formats, "all three", "text, image and video", or "/explain-all", for this session, a past session, any topic or system, or a file, PR or diff.
context: fork
agent: explainer
---

# explain-all

Make all three explanations from one brief, in one output folder.

**Request:** $ARGUMENTS

These are the words typed after the command. If they are empty, explain this session.

1. Read `~/.claude/skills/explain-core/core.md`. Follow sections 1 to 3 once and write `OUTDIR/brief.json`.
2. Read `~/.claude/skills/explain-text/SKILL.md` and follow it from step 2.
3. Read `~/.claude/skills/explain-image/SKILL.md` and follow it from step 2.
4. Read `~/.claude/skills/explain-video/SKILL.md` and follow it from step 2. Video goes last because it is the slowest.
5. Final message: the paths of `text.md`, `diagram.png` and `video.mp4`; say so if the video is captions-only; list the brief's "needs you" items.
