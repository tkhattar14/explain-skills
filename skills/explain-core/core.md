# explain-core: shared rules for explain-text, explain-image, explain-video, explain-all

Read this whole file before making any explanation. It decides the source, the output
folder, and the facts. The format skills only render the facts.

## 1. Pick the source

Look at the words the user typed after the command.

| Words | Source kind | ref |
|---|---|---|
| none | `session` | `$CLAUDE_CODE_SESSION_ID` |
| "last session", "last session in WORD", "session ID", a `.jsonl` path | `past_session` | the transcript path |
| "PR N", an existing file path, "diff", "git diff RANGE", a commit hash | `change` | e.g. `PR 46 acme/shop-backend`, the file path, the range |
| anything else | `topic` | the words, as typed |

If two kinds fit, ask one AskUserQuestion. Do not guess.

Shape: `session` and `past_session` are `story`. A PR, diff or commit is `change`. A topic about how something works ("how the app works", "end to end") is `system`; a topic about one process in order ("how a refund happens") is `story`. A file is `system` for code or config, `story` for a runbook or plan.

## 2. Pick the output folder

1. For `past_session`, first find the transcript (section 3, past_session step 1). Its path is the ref.
2. Look for a brief for the same source from today. Use `find`, not a glob (zsh stops a command when a glob matches nothing):
   ```bash
   find ~/Documents/Explainers -maxdepth 2 -path "*/$(date +%F)-*" -name brief.json -exec grep -l '"ref": "REF"' {} + 2>/dev/null
   ```
   If one exists and the user did not say "fresh", reuse that folder and its `brief.json`. Skip section 3.
   Never reuse for a `session` source: a live session keeps changing, so gather fresh each time and write over the brief in that folder. (`explain-all` still writes one brief for its three formats.)
3. Otherwise create `~/Documents/Explainers/YYYY-MM-DD-<slug>/`. The slug is the brief title in kebab case: lowercase, `a-z0-9-` only, at most 40 characters. If the title is not known yet, use a slug from the source words, and rename the folder once the title is set.
4. If that folder already exists and its `brief.json` has a different ref, add `-2` (then `-3`) to the slug. Never write into another source's folder.

## 3. Gather facts into brief.json

### session
If you are a sub-agent, use section 7 instead of steps 1 and 3.

1. From the conversation, list: what the user asked; each action taken; each result; each error; what was verified (a test or command actually ran and passed) and what was only written.
2. For each git repo the session edited: `git -C REPO status --short` and `git -C REPO diff --stat`. Add changed files to `changes`.
3. If this conversation was compacted (a summary replaced earlier turns), recover early details:
   ```bash
   python3 ~/.claude/skills/explain-core/session_digest.py "$CLAUDE_CODE_SESSION_ID" --out OUTDIR
   ```
   Read `digest.md`.

### past_session
1. Find it:
   - "last session in WORD": `python3 ~/.claude/skills/explain-core/session_digest.py --list WORD`, then `python3 ~/.claude/skills/explain-core/session_digest.py latest:WORD --out OUTDIR`.
   - "last session": `... latest --out OUTDIR`.
   - "session ID" or a path: `... ID --out OUTDIR`.
   `latest` never picks the session you are in. Tell the user in one line which session was picked (id, date, title).
   WORD matches any part of a project folder name (`shop` also matches `shop-admin` folders), so check the folder column. The `--list` date is when the file was last modified; the digest header has the real start and end times.
2. If one `digest.md` was written, read it.
3. If `digest.part1.md` ... `digest.partN.md` were written, dispatch one general-purpose subagent per part, all in one message, with this prompt:

   > Read PART_PATH. It is part K of N of a digest of a Claude Code session (legend at the top). Return JSON with keys `asked`, `steps`, `changes`, `numbers`, `state`, `needs_you`, `risks`, following these rules: every item has `src` quoting the digest line it came from; something only planned or written is not "done"; a failed command is "failed"; never guess to fill a gap. At most 600 words.

   Merge the parts in order. Drop duplicates. Keep the latest status of each step.

### topic
Dispatch one Explore agent (search breadth: very thorough) with this prompt, filling TOPIC and START:

> I need an accurate, current map of TOPIC so I can explain it to the user as text, a diagram and a short video. Start from START. Prefer code, configs, recent specs and git history over README or CLAUDE.md files, which may be stale; say when a document disagrees with the code. Return, with file paths as evidence, at most 900 words: (1) the main parts, at most 12, one line each: what it does, tech, where it runs; (2) the flow as numbered steps, each marked automatic or human; (3) data stores and outside services, one line each; (4) anything commonly believed that the code shows is wrong or out of date; (5) risks and quirks that matter. Do not modify any files.

START is the folder to search: the current project folder, or a sub-folder when the topic lives there (for example `backend/api`). If the user names folders to skip, add "Do not read FOLDERS." to the prompt.

When the report comes back, check 2 or 3 key facts (numbers, names, settings) in the code yourself. Fix or drop any that do not hold.

### change
- PR: `gh pr view N -R OWNER/REPO --json title,body,files,commits` and `gh pr diff N -R OWNER/REPO`. Find OWNER/REPO with `git -C DIR remote get-url origin` in the likely repo; ask if unclear. If `gh` fails, use `git log` and `git diff` on the PR branch, or ask.
- File: Read it.
- Diff: `git diff RANGE --stat` and `git diff RANGE`.

## 4. brief.json format

See `~/.claude/skills/explain-core/brief_example.json` for a filled example.

| Key | Type | Notes |
|---|---|---|
| `version` | 1 | |
| `title`, `one_line` | string | `one_line` is one sentence |
| `created` | `YYYY-MM-DD` | |
| `source` | `{kind, ref}` | from section 1 |
| `shape` | `system` / `story` / `change` | system = parts and connections; story = steps in order; change = before and after |
| `asked` | string[] | required for sessions |
| `parts` | `{id, name, what, group, status, src}`[] | at most 12; pick the 12 most important and say what was left out |
| `links` | `{from, to, label, src}`[] | ids from `parts` |
| `steps` | `{n, text, parts, gate, status, src}`[] | at most 10; `gate` true when the user or their team must act before the next step (an outside person's action, such as a customer's, is not a gate; give it status `human`) |
| `changes` | `{what, before, after, file, src}`[] | |
| `numbers` | `{label, value, src}`[] | `value` is a string |
| `state` | `{verified[], unverified[], failed[]}` | required for sessions |
| `needs_you` | `{text, kind, src}`[] | kind: decision, approval, risk, followup; required for sessions, optional for topics |
| `left_out` | string[] | optional: parts or steps dropped to stay within the limits |
| `risks` | `{text, severity, src}`[] | severity: high, medium, low |

Statuses: `auto`, `human`, `risk`, `failed`, `done`, `verified`, `unverified`, `pending`, `todo`.

## 5. Accuracy rules (every format)

- Every item has `src`: a file path (with line if useful), a command and its result, a transcript or digest line, or a PR/commit. No source means `"src": null` and status `unverified`, and the text says "not verified".
- "done" means it was made. "verified" means a test, command or check actually ran and passed in the source. Written but never run is `unverified`.
- A failed command or test is `failed`, even if a later step worked around it; say both.
- Plans, ideas and next steps are never shown as done.
- Do not fill gaps with guesses. Leave a gap and say it is unknown.
- In a digest, `[O]` lines are command output. A step is `verified` only when an `[O]` line or a quoted result shows it passed.
- Something only read in a document or runbook, and not checked in code or by a command, is `unverified`. Its `src` names the document.
- For a topic, say "not checked" for `unverified` items. Nothing was "tested" there.
- Use only facts from the brief in every format.

## 6. Writing rules (every format)

- No em dashes. Use commas, colons, full stops or brackets.
- Speak to the user as "you". Plain, simple English. No slang and no idioms.
- Spell out each acronym once.

## 7. Running as a sub-agent

The `/explain-...` skills and `@agent-explainer` run in a separate agent, so the calling session stays clean. In that agent:

- **You cannot see the calling conversation.** For a `session` source, its transcript is the conversation. Run:
  ```bash
  python3 ~/.claude/skills/explain-core/session_digest.py "$CLAUDE_CODE_SESSION_ID" --out OUTDIR
  ```
  `CLAUDE_CODE_SESSION_ID` is the calling session's ID, so this reads the right transcript. Then run section 3 session step 2 (git status) for the repos the digest shows were edited.
- **You cannot start other agents.** For a `topic`, do the research yourself with Grep, Glob and Read. Cover the same five points as the research prompt in section 3, and write findings to `OUTDIR/research.md` as you go.
- **Long digests.** If the digest has several parts, read them in order. After each part, add its facts to `OUTDIR/notes.md`. Build the brief from `notes.md`, so your own context does not fill up.
- **You cannot ask the user.** Where this file says to ask, pick the most likely option and list it under "Choices I made" in your final reply.
- **Your final reply goes back into the user's session.** Keep it short (folder, files, three-line summary, needs you, choices). Never paste tool output or the full text.
