---
name: explain-video
description: Use when the user asks to explain something as a video, explainer video, animation or "3b1b style" walkthrough, such as "/explain-video", "explain this session as a video", "make a video of what this session did", "video explainer on how payments work", or "explain PR 46 as a video". Works for this session, a past session, any topic or system, or a file, PR or diff.
context: fork
agent: explainer
---

# explain-video

Explain work as a narrated, animated video: a Remotion engine with six scene types and an ElevenLabs voice (set `EXPLAIN_VOICE_ID` to use your own). Length scales with content, at most about 3 minutes.

**Request:** $ARGUMENTS

These are the words typed after the command. If they are empty, explain this session.

## Steps

1. Read `~/.claude/skills/explain-core/core.md`. Follow sections 1 to 3 and write `OUTDIR/brief.json` (or reuse it).
2. Plan the scenes (below) and write `OUTDIR/video/video.json`. Copy the format of `~/.claude/skills/explain-video/engine/fixtures/all-scenes.json`.
3. Validate: `python3 ~/.claude/skills/explain-video/validate.py "OUTDIR/video/video.json"`. Fix every error and run it again until it prints `OK`.
4. Voice: `python3 ~/.claude/skills/explain-video/make_vo.py "OUTDIR"`. If it prints `NO VOICE: ...`, continue; the video will have captions only, and you must say so in your final message.
5. Stills: `bash ~/.claude/skills/explain-video/render.sh "OUTDIR" --stills-only`. Read every PNG in `OUTDIR/video/stills/`. Each still shows its scene after the last line has settled, so map highlights from every line are lit. Check: text stays inside boxes and cards, the caption fits in one or two lines, the lit boxes match the scene's lines, and counted numbers show their final values. If a still is wrong, fix `video.json` and repeat from step 3.
6. Render: `bash ~/.claude/skills/explain-video/render.sh "OUTDIR"`. It takes about one minute per minute of video, then opens the video. The first run ever installs the engine (about a minute). If `render.sh` exits with an error, show the user the error and the stills folder, and do not say the video is ready.
7. Final message: video length, voice or captions-only, the volume and silence lines, and the folder path.

## Scene plan

Always start with a `title` scene: two lines, what this is and what you will learn.

| Source | Scenes after the title |
|---|---|
| session, past_session, change | `map` (only if the brief has 3+ parts with links) → `steps` ("What was done", from `brief.steps`, statuses kept) → `before_after` (if `changes`) → `numbers` (if `numbers`) → `takeaways` ("Needs you", from `needs_you`, `mini_map: true` if there is a map) |
| topic | one or more `map` scenes walking the flow, 4 to 6 lines each, all on the same graph → `numbers` (optional) → `takeaways` ("Three things to remember": the main point from `one_line`, where people must act from steps with `gate: true`, the biggest risk by `severity`) |

- Item statuses come from the brief. A gate that already happened is `done`; use `human` only when it still waits for a person.
- The graph is the brief's `parts` (as `nodes`: `id`, `title` = name, `sub` = what, `status`) and `links` (as `edges`: `id` = `from-to`, `label`).
- Give each main point about 20 to 30 seconds (3 to 5 lines). The whole script is at most 450 words.
- A map allows at most 6 boxes in a row when any arrow has a label, or 8 with no labels. Anything longer is a `steps` scene.

## Script rules

- One line is one sentence: at most 20 words and 120 characters.
- Speak to the user as "you". Plain, simple English. No slang and no idioms.
- Use `show` when the spoken form differs from the written one: "eff eff em peg" / "FFmpeg", "S 3" / "S3", "example dot com" / "example.com", numbers read as words.
- Only say something is done or works if its brief status is `done` or `verified`. For `unverified` say "not tested yet" (for a topic: "not checked yet"). For `failed` say it failed.
- Say acronyms that are not words letter by letter, with spaces: `say` "A P I", `show` "API"; `say` "S T E", `show` "STE".
- Map cues: `nodes` and `edges` light up; use `rev` for an arrow travelling backwards. Steps, before/after, numbers and takeaways cues use `reveal` (how many items are visible). Takeaways cues may also light `nodes` on the mini map.
- No em dashes anywhere.
