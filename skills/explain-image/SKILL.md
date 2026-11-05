---
name: explain-image
description: Use when the user asks to explain something as an image, diagram, picture or flowchart, such as "/explain-image", "explain this session as an image", "draw what this session did", "diagram how payments work", or "show PR 46 as a diagram". Works for this session, a past session, any topic or system, or a file, PR or diff.
context: fork
agent: explainer
---

# explain-image

Explain work as one colour-coded Mermaid diagram, rendered offline to PNG, SVG and an editable Excalidraw file. Never use AI image generation for this (it misspells and invents).

**Request:** $ARGUMENTS

These are the words typed after the command. If they are empty, explain this session.

## Steps

1. Read `~/.claude/skills/explain-core/core.md`. Follow sections 1 to 3 and write `OUTDIR/brief.json` (or reuse it).
2. Write `OUTDIR/diagram.mmd` from the brief using the rules below.
3. Render: `bash ~/.claude/skills/explain-image/render_mermaid.sh "OUTDIR"`.
   - `ERROR ...` (exit 4): fix the Mermaid source and run again. Never hand over a broken file.
   - `BLOCKED ...` (exit 3): tell the user the exact message and stop.
4. Read `OUTDIR/diagram.png` with the Read tool. Check that every label is readable, no box overlaps another, step numbers run in order, and colours match statuses. Fix and render again if not.
5. Run `open "OUTDIR/diagram.png"`. Add the colour key as one line in your final reply: blue automatic, amber needs a person, red risk or failed, green done, dashed grey not done or not verified, pale grey before.

## Mermaid rules

- By shape:
  - `system`: `graph LR`, one `subgraph` per `group`, boxes from `parts`, arrows from `links`.
  - `story`: `graph TD`, one box per step: `S1["1 Wrote the command"]`, arrows in step order. Steps with `gate: true` use a hexagon: `S3{{"3 You approve"}}`. Add `subgraph NEEDS["Needs you"]` with one box per `needs_you` item.
  - `change`: `graph LR` with `subgraph BEFORE["Before"]` and `subgraph AFTER["After"]`. One arrow per change: `B1["no add-ons"] -->|"order.py"| A1["add-ons saved"]`. Before boxes use the `old` class. Risks go in `subgraph RISKS["Risks"]` as red boxes. Add `subgraph NEEDS["Needs you"]` for `needs_you` items, as in `story`.
- Quote every label. Replace `"` inside a label with `'`. Use `<br/>` for a second line. Keep each label line at most 26 characters (longer lines wrap).
- Edge labels are short and numbered when they show order: `-->|"2 webhook"|`.
- At most 15 boxes. If more, split into `diagram.mmd` and `diagram-2.mmd` and render both (`render_mermaid.sh "OUTDIR" diagram-2`).
- No em dashes in labels.
- End every diagram with these colour classes, then assign each box by its status:

```
  classDef auto fill:#E0F2FE,stroke:#0284C7,color:#0C1A2B
  classDef human fill:#FEF3C7,stroke:#D97706,stroke-width:2px,color:#1F1300
  classDef risk fill:#FEE2E2,stroke:#DC2626,stroke-width:2px,color:#2A0A0A
  classDef done fill:#DCFCE7,stroke:#16A34A,color:#052E16
  classDef todo fill:#F1F5F9,stroke:#94A3B8,stroke-dasharray:4 3,color:#334155
  classDef old fill:#F8FAFC,stroke:#CBD5E1,color:#64748B
```

| Status | Class |
|---|---|
| `auto` | `auto` |
| `human`, gates | `human` |
| `risk`, `failed` | `risk` |
| `done`, `verified` | `done` |
| `unverified`, `pending`, `todo` | `todo` |
| Before boxes (change shape) | `old` |
