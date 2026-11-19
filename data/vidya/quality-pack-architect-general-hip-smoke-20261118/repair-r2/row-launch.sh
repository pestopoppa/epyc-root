#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/vidya-belief-substrate/architect-general-hip-smoke-20261118-repair-r2.2o7xv56j
ID=handoff-vidya-quality-pack-architect-general-hip-smoke-20261118
RESULT=$D/out/RESULT.json
cd "$D"
/usr/bin/sha256sum --check --status SOURCE.sha256
if [[ ${FILLER_DRYRUN:-0} == 1 ]]; then
    printf -v RESULT '%q' "${FILLER_DRYRUN_RESULT_PATH:?}"
fi
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
    --id "$ID" --class gpu --gpu-quiet exclusive --no-fold-siblings \
    --min-window 2250 --port 19478 --workdir "$D" --stop "$D/STOP" \
    --complete-cmd "/usr/bin/test -s $RESULT" \
    --cmd "/usr/bin/python3 -B $D/capture.py --threads 8"
