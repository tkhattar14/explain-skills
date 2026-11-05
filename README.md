# explain-skills

Claude Code skills that explain work in three formats:

- **Text**: short, clear writing in "80% ASD-STE100" (Simplified Technical English) style.
- **Diagram**: one colour-coded Mermaid diagram, rendered offline to PNG, SVG and an editable Excalidraw file.
- **Video**: a narrated, animated explainer (Remotion engine, ElevenLabs voice), at most about 3 minutes.

They can explain the current session, a past session, any topic or system in your codebase, or a file, PR or diff.

## Commands

| Command | Makes |
|---|---|
| `/explain-text [what]` | `text.md` |
| `/explain-image [what]` | `diagram.png`, `diagram.svg`, `diagram.excalidraw` |
| `/explain-video [what]` | `video.mp4` |
| `/explain-all [what]` | all three, from one shared brief |

`[what]` picks the source:

| You type | Source |
|---|---|
| nothing | this session |
| `last session`, `last session in WORD`, a session ID, a `.jsonl` path | a past session |
| `PR 46`, a file path, `diff`, `git diff RANGE`, a commit hash | a change |
| anything else, such as `how payments work` | a topic, researched from the code |

You can also tag `@agent-explainer` with a request. With no format named, it makes text and a diagram.

Output goes to `~/Documents/Explainers/YYYY-MM-DD-<slug>/` (`brief.json`, `text.md`, `diagram.png`, `video.mp4`).

## How it works

1. Each skill runs in the `explainer` sub-agent (`context: fork`), so the calling session stays clean and gets back a reply of about 10 lines.
2. The agent gathers facts into one `brief.json` (rules in `skills/explain-core/core.md`). Every item carries a source and a status: done, verified, not verified, failed, and so on. Nothing is shown as done or tested unless the source proves it.
3. For sessions, `session_digest.py` shrinks the Claude Code transcript (`~/.claude/projects/*/*.jsonl`) into a compact digest the agent can read.
4. Each format skill renders only the facts in the brief.

## Install

```bash
git clone https://github.com/tkhattar14/explain-skills.git
cd explain-skills
mkdir -p ~/.claude/skills ~/.claude/agents
for s in skills/explain-*; do ln -s "$PWD/$s" ~/.claude/skills/; done
ln -s "$PWD/agents/explainer.md" ~/.claude/agents/
```

Restart Claude Code so it picks up the new skills and agent.

The skills refer to `~/.claude/skills/explain-*` paths, so keep the links at those names.

## Requirements

- **All formats:** Claude Code, Python 3.9+ (standard library only). macOS is assumed: the skills use `open` to show the result. On Linux, change `open` to `xdg-open`.
- **Diagram:** [gstack](https://github.com/garrytan/gstack) installed at `~/.claude/skills/gstack`, with its `browse` binary and the diagram bundle built (`cd ~/.claude/skills/gstack && bun run build:diagram-render`). The renderer prints `BLOCKED` with the fix if either is missing.
- **Video:** Node.js 18+ and npm, plus `ffmpeg` and `ffprobe`. The first render runs `npm install` in `skills/explain-video/engine` (about a minute).
- **Voice (optional):** set `ELEVENLABS_API_KEY` in your environment. Without it you get a captions-only video. The default voice is the ElevenLabs premade voice "George"; set `EXPLAIN_VOICE_ID` to use another voice, or put `voice_id` in a video's `video.json`.

## Customise

- **Writing style:** `skills/explain-core/core.md` section 6 and the "Script rules" in `skills/explain-video/SKILL.md` set the tone ("plain, simple English"). Change them to suit you.
- **Output folder:** search for `~/Documents/Explainers` in `core.md` and `agents/explainer.md`.
- **Video look:** colours and sizes are in `skills/explain-video/engine/src/theme.ts`.

## Tests

```bash
python3 skills/explain-core/tests/test_session_digest.py
python3 skills/explain-video/tests/test_validate.py
python3 skills/explain-video/tests/test_make_vo.py
python3 skills/explain-video/tests/test_still_frames.py
bash skills/explain-image/tests/test_render_mermaid.sh   # needs gstack
```

## Cost

One text or diagram run costs about $1 to $2 of model usage. A video adds about 2,000 ElevenLabs characters per 2.5 minutes of narration.

## License

MIT
