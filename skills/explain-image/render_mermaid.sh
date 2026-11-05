#!/usr/bin/env bash
# Render OUTDIR/NAME.mmd to NAME.svg, NAME.png (2600 px wide) and NAME.excalidraw, offline,
# with the gstack /diagram bundle. Everything runs in ONE call because the browse daemon
# can restart between calls and drop the render tab. browse only writes --out files under
# /private/tmp or its own start folder, so files are staged in /private/tmp and then moved.
# Usage: render_mermaid.sh OUTDIR [NAME]    (NAME defaults to "diagram")
# Exit: 0 ok, 2 usage/missing source, 3 BLOCKED (tooling missing), 4 Mermaid ERROR.
set -euo pipefail
[ $# -ge 1 ] || { echo "usage: render_mermaid.sh OUTDIR [NAME]"; exit 2; }
OUT="$(cd "$1" && pwd)"
NAME="${2:-diagram}"
SRC="$OUT/$NAME.mmd"
[ -f "$SRC" ] || { echo "missing $SRC"; exit 2; }
B="$HOME/.claude/skills/gstack/browse/dist/browse"
BUNDLE="$HOME/.claude/skills/gstack/lib/diagram-render/dist/diagram-render.html"
[ -x "$B" ] || { echo "BLOCKED: gstack browse missing at $B"; exit 3; }
[ -f "$BUNDLE" ] || { echo "BLOCKED: diagram bundle missing; run: cd ~/.claude/skills/gstack && bun run build:diagram-render"; exit 3; }
SHA=$(shasum -a 256 "$BUNDLE" | cut -c1-16)
STAGED="/tmp/gstack-diagram-render-$SHA.html"
[ -f "$STAGED" ] || { cp "$BUNDLE" "$STAGED.$$" && mv "$STAGED.$$" "$STAGED"; }

STAGE=$(mktemp -d /private/tmp/explain-mmd.XXXXXX)
cd "$STAGE"  # a cold browse daemon writes .gstack/ into its start folder; keep that out of OUTDIR
TAB=$("$B" newtab --json | sed -n 's/.*"tabId":[[:space:]]*\([0-9]*\).*/\1/p')
[ -n "$TAB" ] || { echo "BLOCKED: could not open a browse tab"; exit 3; }
trap '"$B" closetab "$TAB" >/dev/null 2>&1 || true; rm -rf "$STAGE"' EXIT
"$B" load-html "$STAGED" --tab-id "$TAB" >/dev/null
"$B" wait '#done' --tab-id "$TAB" >/dev/null

B64=$(base64 < "$SRC" | tr -d '\n')
DECODE="decodeURIComponent(escape(atob('$B64')))"
RES=$("$B" js --tab-id "$TAB" "window.__renderMermaid('d1', $DECODE).then(s => { window.__svg = s; return 'SVG OK ' + s.length }).catch(e => 'ERROR ' + (e && e.message ? e.message : e))")
echo "$RES"
case "$RES" in *ERROR*) exit 4 ;; esac
"$B" js --tab-id "$TAB" "window.__svg" --out "$STAGE/$NAME.svg" >/dev/null
"$B" js --tab-id "$TAB" "window.__rasterize(window.__svg, 2600)" --out "$STAGE/$NAME.png" >/dev/null
"$B" js --tab-id "$TAB" "window.__mermaidToExcalidraw($DECODE).then(j => { window.__scene = j; return 'SCENE OK' }).catch(e => { window.__scene = ''; return 'SCENE SKIPPED ' + e.message })"
"$B" js --tab-id "$TAB" "window.__scene || ''" --out "$STAGE/$NAME.excalidraw" >/dev/null
[ -s "$STAGE/$NAME.excalidraw" ] || rm -f "$STAGE/$NAME.excalidraw"
[ -s "$STAGE/$NAME.png" ] || { echo "ERROR no PNG was written"; exit 4; }
mv "$STAGE/$NAME".* "$OUT/"
echo "PNG: $OUT/$NAME.png"
