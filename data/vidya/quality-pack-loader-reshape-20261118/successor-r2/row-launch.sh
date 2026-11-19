#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/vidya-belief-substrate/loader-reshape-r2-20261118
ID=handoff-vidya-quality-pack-loader-reshape-cpu-20261118-r2
RESULT=$D/out/RESULT.json
cd "$D"
/usr/bin/sha256sum --check --status SOURCE.sha256
if [[ ${FILLER_DRYRUN:-0} == 1 ]]; then
    printf -v RESULT '%q' "${FILLER_DRYRUN_RESULT_PATH:?}"
fi
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
    --id "$ID" --class cpu --role bench --gpu-quiet none --min-window 1650 \
    --port 19487 --workdir "$D" --stop "$D/STOP" \
    --complete-cmd "/usr/bin/python3 -B $D/complete.py $RESULT" \
    --cmd "/usr/bin/python3 -B $D/capture.py"
