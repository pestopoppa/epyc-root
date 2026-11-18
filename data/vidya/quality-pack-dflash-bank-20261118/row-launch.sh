#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/vidya-belief-substrate/dflash-bank-20261118
ID=handoff-vidya-quality-pack-dflash-bank-20261118
RESULT=$D/out/RESULT.json
MODE=bank
cd "$D"
/usr/bin/sha256sum --check --status SOURCE.sha256
if [[ ${FILLER_DRYRUN:-0} == 1 ]]; then
    printf -v RESULT '%q' "${FILLER_DRYRUN_RESULT_PATH:?}"
    MODE=smoke
fi
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
    --id "$ID" --class cpu --role bench --gpu-quiet none \
    --min-window 2250 --port 19488 --workdir "$D" --stop "$D/STOP" \
    --complete-cmd "/usr/bin/python3 -B $D/complete_predicate.py $RESULT $MODE" \
    --cmd "/usr/bin/python3 -B $D/capture.py"
