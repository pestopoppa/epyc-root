#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/cs26-f1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 RUS3_DIAGNOSTIC=1 HIP_VISIBLE_DEVICES=-1 ROCR_VISIBLE_DEVICES=-1 PYTHONDONTWRITEBYTECODE=1
cd "$D"
printf '%s  %s\n' d82040fb04db5851cf1148c0ad8c4bd0fd81932cfa82d7eefe02be072179e028 "$D/SOURCE-SHA256SUMS" | sha256sum -c - >/dev/null
sha256sum -c --quiet "$D/SOURCE-SHA256SUMS"
sha256sum -c --quiet "$D/RUNTIME.sha256"
case ${1:-} in
 --job) sha256sum -c --quiet "$D/INPUTS.sha256"; export F1_MODE=full; exec taskset -c "${FILLER_CPUS:?}" /usr/bin/python3 -B "$D/independent_capture.py";;
 --smoke) export F1_MODE=smoke FILLER_DEADLINE=$(( $(date +%s) + 250 )); exec taskset -c "${FILLER_CPUS:?}" /usr/bin/python3 -B "$D/smoke-supervisor.py" 265 -- /usr/bin/python3 -B "$D/independent_capture.py";;
 --engine) sha256sum -c --quiet "$D/INPUTS.sha256"; export FILLER_RL=/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock; exec /bin/bash "$D/engine/filler_run13.sh" --id codex3-cs26-f1-independent-20261031 --class cpu --role bench --gpu-quiet exclusive --claim-cpus "${WS58_REGIONS:?}" --min-window 2100 --stop "$D/STOP" --workdir "$D" --complete-cmd "test -s $D/run/TERMINAL.json" --cmd 'env RUS3_DIAGNOSTIC=1 taskset -c "$FILLER_CPUS" /bin/bash /mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/cs26-f1/launch-independent.sh --job';;
 '') exec sudo -n --preserve-env=WS58_REGIONS,FILLER_CPUS /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --groups=992 /bin/bash "$D/launch-independent.sh" --engine;;
 *) exit 64;;
esac
