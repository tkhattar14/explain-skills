---
name: explain-text
description: Use when the user asks to explain something as text, in STE / ASD-STE100, or in plain simple English, such as "/explain-text", "explain this session as text", "write up what this session did", "explain how payments work in STE", or "explain PR 46". Works for this session, a past session, any topic or system, or a file, PR or diff.
context: fork
agent: explainer
---

# explain-text

Explain work as short, clear text in "80% ASD-STE100" style. Saves `text.md` and opens it.

**Request:** $ARGUMENTS

These are the words typed after the command. If they are empty, explain this session.

## Steps

1. Read `~/.claude/skills/explain-core/core.md`. Follow sections 1 to 3: pick the source, pick the output folder (reuse today's brief if it exists), and write `OUTDIR/brief.json`.
2. Write `OUTDIR/text.md` from the brief, using the layout for the source below. Use only facts in the brief. Show each item's status in words ("verified", "not verified", "failed", "not done").
3. Check the writing:
   ```bash
   python3 - "OUTDIR/text.md" <<'PY'
   import re, sys
   text = open(sys.argv[1], encoding="utf-8").read()
   if "\u2014" in text:
       print("EM DASH found")
   body = "\n".join(l for l in text.splitlines() if not l.lstrip().startswith(("|", "#", "`")))
   for s in re.split(r"(?<=[.!?])\s+|\n+", body):
       n = len(s.split())
       if n > 25:
           print(f"{n} words: {s[:90]}")
   PY
   ```
   Rewrite every sentence it lists, then run it again until it prints nothing. The check flags sentences over 25 words; keep numbered instructions at 20 words or fewer yourself.
4. Run `open "OUTDIR/text.md"`. Do not paste the whole text into your reply; the file holds it. Put the three-line summary in your final reply.
5. Give the folder path in your final reply.

## 80% STE rules

- Instructions: at most 20 words. Descriptions: at most 25 words.
- One instruction per sentence. Active voice ("Stripe sends the webhook", not "the webhook is sent").
- Present tense for how things work. Past tense for what a session did.
- One topic per paragraph. Numbered lists for anything that happens in order.
- `NOTE:` for useful information. `CAUTION:` for a risk of loss, damage or a wrong result. `WARNING:` only for safety.
- Keep technical names as they are (Stripe, `checkout.session.completed`, `shop paylink`). Spell out each acronym once.
- Everyday words are fine. Prefer the plain word ("check" or "examine", "use", "start").
- No em dashes.

## Layouts

**Session or past session**

```
# <title>

<three-line summary: what was asked, what was done, what needs you>

## What was asked
## What was done        (numbered; each line ends with its status)
## Current state        (Verified / Not verified / Failed, as three short lists)
## What needs you       (CAUTION: for risks; NOTE: for follow-ups)
## Files changed        (path: one-line change)
```

**Topic**

```
# <title>
## 1. General           (3 to 5 sentences)
## 2. Main parts        (one bold name + 2 to 3 sentences each)
## 3. Sequence          (numbered steps; mark steps that need a person)
## 4. Risks             (CAUTION / NOTE lines)
```

**Change (PR, file, diff)**

```
# <title>
## What changed
## Why
## Before and after     (a two-column table)
## Risks
## What needs you
```
