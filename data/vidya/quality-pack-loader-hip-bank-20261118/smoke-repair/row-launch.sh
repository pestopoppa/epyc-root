#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/vidya-belief-substrate/loader-hip-bank-20261118-repair
ID=handoff-vidya-quality-pack-architect-general-hip-loader-bank-20261118
RESULT=$D/out/RESULT.json
cd "$D"
/usr/bin/sha256sum --check --status SOURCE.sha256
if [[ ${FILLER_DRYRUN:-0} == 1 ]]; then
    printf -v RESULT '%q' "${FILLER_DRYRUN_RESULT_PATH:?}"
fi
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
    --id "$ID" --class gpu --gpu-quiet exclusive --no-fold-siblings \
    --min-window 1200 --port 19489 --workdir "$D" --stop "$D/STOP" \
    --complete-cmd "/usr/bin/python3 -B $D/complete.py $RESULT" \
    --cmd "/usr/bin/python3 -B $D/capture.py --threads 8"
