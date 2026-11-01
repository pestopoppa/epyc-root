#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex-ni-specgram3-repair-20261101/cpu-r2-20261101
if [[ ${WS58_QUAL:-0} == 1 ]]; then
  [[ -n ${WS58_MANIFEST_PATH:-} && -f $WS58_MANIFEST_PATH ]] || {
    echo "REFUSED: qualification manifest absent" >&2; exit 70; }
  read -r production_state < <(/usr/bin/python3 -I - "$WS58_MANIFEST_PATH" <<'PYMAN'
import json,sys
v=json.load(open(sys.argv[1])).get("production", "__missing__")
print("invalid" if type(v) is not bool else ("true" if v else "false"))
PYMAN
)
  if [[ $production_state == true ]]; then
    echo "REFUSED: production qualification cannot use the model-free command fixture; actual same-job science qualification is not yet implemented" >&2
    exit 70
  fi
  if [[ $production_state != false ]]; then
    echo "REFUSED: nonproduction fixture requires an explicit JSON boolean false" >&2
    exit 70
  fi
  [[ -n ${FILLER_QUAL_PHASE:-} && -n ${FILLER_QUAL_FIXTURE:-} ]] || {
    echo "REFUSED: nonproduction qualification fixture context incomplete" >&2; exit 70; }
  [[ $FILLER_QUAL_FIXTURE == "$D/qual_fixture.py" ]] || {
    echo "REFUSED: nonproduction fixture path differs from pinned r2 source" >&2; exit 70; }
  exec /usr/bin/python3 -I -B "$FILLER_QUAL_FIXTURE"
fi
[[ -n ${FILLER_CPUS:-} && -n ${FILLER_DEADLINE:-} && -n ${FILLER_THREADS:-} ]] || {
  echo "REFUSED: production filler environment incomplete" >&2; exit 70; }
exec /usr/bin/python3 -I -B "$D/job.py" full
