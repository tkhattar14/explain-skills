#!/usr/bin/env bash
# Integration test for render_mermaid.sh. Needs gstack browse + diagram bundle.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="$HERE/../render_mermaid.sh"
T=$(mktemp -d)
fail=0

cp "$HERE/fixtures/ok.mmd" "$T/diagram.mmd"
if (cd "$T" && bash "$SCRIPT" "$T") > "$T/ok.log" 2>&1 && file "$T/diagram.png" | grep -q "PNG image" && grep -q "₹1,499" "$T/diagram.svg"; then
  echo "PASS ok.mmd renders (png + svg with UTF-8 label)"
else
  echo "FAIL ok.mmd"; cat "$T/ok.log"; fail=1
fi
[ -s "$T/diagram.excalidraw" ] && echo "PASS excalidraw written" || { echo "FAIL excalidraw missing"; fail=1; }
[ ! -e "$T/.gstack" ] && echo "PASS no .gstack left in the output folder" || { echo "FAIL .gstack left in output folder"; fail=1; }

cp "$HERE/fixtures/broken.mmd" "$T/bad.mmd"
bash "$SCRIPT" "$T" bad > "$T/bad.log" 2>&1
code=$?
if [ "$code" -eq 4 ] && grep -q "ERROR" "$T/bad.log" && [ ! -f "$T/bad.png" ]; then
  echo "PASS broken.mmd exits 4 with ERROR and no png"
else
  echo "FAIL broken.mmd (exit $code)"; cat "$T/bad.log"; fail=1
fi

bash "$SCRIPT" "$T" missing > /dev/null 2>&1
[ $? -eq 2 ] && echo "PASS missing source exits 2" || { echo "FAIL missing source"; fail=1; }
exit $fail
