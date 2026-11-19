#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/vidya-belief-substrate/worker-vision-20261118-repair-r2._blwnc1p
ID=handoff-vidya-quality-pack-worker-vision-hip-mmproj-20261118
RESULT=$D/out/RESULT.json
cd "$D"
/usr/bin/sha256sum --check --status SOURCE.sha256
if [[ ${FILLER_DRYRUN:-0} == 1 ]]; then
    printf -v RESULT '%q' "${FILLER_DRYRUN_RESULT_PATH:?}"
fi
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
    --id "$ID" --class gpu --gpu-quiet exclusive --no-fold-siblings \
    --min-window 2100 --port 19479 --workdir "$D" --stop "$D/STOP" \
    --complete-cmd "/usr/bin/test -s $RESULT" \
    --cmd "/usr/bin/python3 -B $D/capture.py --threads 8"
