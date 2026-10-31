#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ernie-typo
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 RUS3_DIAGNOSTIC=1 HIP_VISIBLE_DEVICES=0 PYTHONDONTWRITEBYTECODE=1
cd "$D"
printf '%s  %s\n' 08ce7e24d61a17175586f2575845303e431cc2fc3e63651c70e4dc6b3da4789d "$D/SOURCE-SHA256SUMS" | sha256sum -c --quiet
printf '%s  %s\n' a7eb0f4666f661e8b5ddb5d7e7d25ac7b09b3156a0632a5c2993e4b279620a72 "$D/EARLY.sha256" | sha256sum -c --quiet
sha256sum -c --quiet "$D/EARLY.sha256"
case ${1:-} in
 --job) sha256sum -c --quiet "$D/SOURCE-SHA256SUMS"; sha256sum -c --quiet "$D/RUNTIME.sha256"; sha256sum -c --quiet "$D/MODELS.sha256"; export ERNIE_MODE=full; exec taskset -c "${FILLER_CPUS:?}" /usr/bin/python3 -B "$D/worker.py";;
 --smoke|--cutoff) /usr/bin/python3 -B "$D/gpu_preflight.py"; export ERNIE_OUT=smoke-${1#--}; exec "$D/region-lock" run --gpu-quiet exclusive --timeout-s 1 --tag ernie-r7-control -- /usr/bin/taskset -c 184,185 /bin/bash "$D/launch.sh" --smoke-locked;;
 --smoke-locked) /usr/bin/python3 -B "$D/gpu_preflight.py"; sha256sum -c --quiet "$D/SOURCE-SHA256SUMS"; sha256sum -c --quiet "$D/RUNTIME.sha256"; sha256sum -c --quiet "$D/MODELS.sha256"; export ERNIE_MODE=smoke FILLER_DEADLINE=$(( $(date +%s) + 270 )); exec /usr/bin/python3 -B "$D/gpu_smoke_supervisor.py" /usr/bin/python3 -B "$D/worker.py";;
 --engine) export FILLER_RL="$D/region-lock"; exec /bin/bash "$D/engine/filler_run13.sh" --id codex3-ernie-typo20-20261031 --class gpu --role bench --gpu-quiet exclusive --no-fold-siblings --gpu-threads 184-191 --min-window 1800 --stop "$D/STOP" --workdir "$D" --complete-cmd 'test -s /mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ernie-typo/run/TERMINAL.json' --cmd 'env -i PATH=/usr/bin:/bin LANG=C.UTF-8 RUS3_DIAGNOSTIC=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 HIP_VISIBLE_DEVICES=0 ROCR_VISIBLE_DEVICES=0 FILLER_ID="$FILLER_ID" FILLER_CPUS="$FILLER_CPUS" FILLER_NEEDGPU="$FILLER_NEEDGPU" FILLER_STOPFILE="$FILLER_STOPFILE" FILLER_END="$FILLER_END" FILLER_DEADLINE="$FILLER_DEADLINE" /bin/bash /mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ernie-typo/launch.sh --job';;
 '') exec > >(tee -a "$D/ws58-launcher.out") 2>&1; exec sudo -n /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --groups=992 /bin/bash "$D/launch.sh" --engine;;
 *) exit 64;;
esac
