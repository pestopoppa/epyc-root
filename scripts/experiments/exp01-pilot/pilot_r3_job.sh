#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/brf-exp01
if [[ "${FILLER_DRYRUN:-0}" == 1 ]]; then
  export OUT="${FILLER_DRYRUN_DIR:?}/exp01-pilot-r3"
else
  export OUT="$D/run-r3"
fi
export MODELSET="$D/models.env" LAUNCHES=3 CAP_S=5400
exec /bin/bash "$D/bin/job_r3.sh"
