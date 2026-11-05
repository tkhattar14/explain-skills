#!/usr/bin/env bash
# Render an explain-video output folder.
# Usage: render.sh OUTDIR [--stills-only]
# Needs OUTDIR/video/video.json and OUTDIR/video/timeline.json (run make_vo.py first).
# Writes OUTDIR/video/stills/<scene>.png (one per scene, once its last line has settled)
# and OUTDIR/video.mp4, then opens the video.
set -euo pipefail
[ $# -ge 1 ] || { echo "usage: render.sh OUTDIR [--stills-only]"; exit 2; }
OUT="$(cd "$1" && pwd)"
MODE="${2:-}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENGINE="$HERE/engine"
V="$OUT/video"
BUNDLE="$OUT/.bundle"
[ -f "$V/video.json" ] && [ -f "$V/timeline.json" ] || { echo "missing $V/video.json or $V/timeline.json"; exit 2; }

export NVM_DIR="$HOME/.nvm"
# shellcheck disable=SC1091
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" >/dev/null 2>&1 || true
if [ ! -d "$ENGINE/node_modules" ]; then
  echo "SETUP: installing the video engine (one time, about a minute)"
  (cd "$ENGINE" && npm install --no-audit --no-fund --loglevel=error)
fi

python3 - "$V" <<'PY'
import json, pathlib, sys
v = pathlib.Path(sys.argv[1])
props = {"spec": json.loads((v / "video.json").read_text()), "timeline": json.loads((v / "timeline.json").read_text())}
(v / "props.json").write_text(json.dumps(props))
PY

rm -rf "$BUNDLE"
trap 'rm -rf "$BUNDLE"' EXIT
(cd "$ENGINE" && npx remotion bundle src/index.ts --out-dir="$BUNDLE" --public-dir="$V" --log=error)

mkdir -p "$V/stills"
python3 "$HERE/still_frames.py" "$V/timeline.json" > "$OUT/.frames"
while read -r ID F; do
  (cd "$ENGINE" && npx remotion still "$BUNDLE" Explainer "$V/stills/$ID.png" --frame="$F" --props="$V/props.json" --log=error) </dev/null
done < "$OUT/.frames"
rm -f "$OUT/.frames"
echo "STILLS: $V/stills"
[ "$MODE" = "--stills-only" ] && exit 0

(cd "$ENGINE" && npx remotion render "$BUNDLE" Explainer "$OUT/video.mp4" --props="$V/props.json" --codec=h264 --crf=20 --log=error)
DUR=$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$OUT/video.mp4")
echo "VIDEO: $OUT/video.mp4 (${DUR}s)"
if python3 -c "import json,sys; sys.exit(0 if json.load(open(sys.argv[1]))['hasAudio'] else 1)" "$V/timeline.json"; then
  ffmpeg -hide_banner -i "$OUT/video.mp4" -vn -af volumedetect -f null - 2>&1 | grep -E "mean_volume|max_volume" || true
  ffmpeg -hide_banner -i "$OUT/video.mp4" -vn -af silencedetect=noise=-45dB:d=2.5 -f null - 2>&1 | grep -E "silence_(start|end)" || echo "SILENCE: no gap over 2.5 s"
else
  echo "AUDIO: none (captions-only video)"
fi
open "$OUT/video.mp4"
