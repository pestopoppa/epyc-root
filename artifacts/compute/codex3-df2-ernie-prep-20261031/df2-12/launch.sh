#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/df2-12
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 RUS3_DIAGNOSTIC=1 HIP_VISIBLE_DEVICES=-1 ROCR_VISIBLE_DEVICES=-1 PYTHONDONTWRITEBYTECODE=1
cd "$D"
printf '%s  %s\n' 8594405c489d1608a74654eb038f234e84f622ab27191334ca3edde1a67bf139 "$D/SOURCE-SHA256SUMS" | sha256sum -c --quiet
printf '%s  %s\n' 4e734132891b3b13100a9cfe9cae9a3f683002c851c7d2d4b3ddb2f4482198c5 "$D/EARLY.sha256" | sha256sum -c --quiet
sha256sum -c --quiet "$D/EARLY.sha256"
case ${1:-} in
 --job) sha256sum -c --quiet "$D/SOURCE-SHA256SUMS"; sha256sum -c --quiet "$D/RUNTIME-INPUTS.sha256"; sha256sum -c --quiet "$D/MODELS.sha256"; export DF2_MODE=full; exec taskset -c "${FILLER_CPUS:?}" /usr/bin/python3 -B "$D/worker.py";;
 --smoke) sha256sum -c --quiet "$D/SOURCE-SHA256SUMS"; sha256sum -c --quiet "$D/RUNTIME-INPUTS.sha256"; export DF2_MODE=smoke FILLER_DEADLINE=$(( $(date +%s) + 250 )); exec taskset -c "${FILLER_CPUS:?}" /usr/bin/python3 -B "$D/smoke-supervisor.py" 265 -- /usr/bin/python3 -B "$D/worker.py";;
 --engine) export FILLER_RL="$D/region-lock"; exec /bin/bash "$D/engine/filler_run13.sh" --id codex3-df2-12-np4-cpu-20261031 --class cpu --role bench --claim-cpus "${WS58_REGIONS:?}" --min-window 5400 --stop "$D/STOP" --workdir "$D" --complete-cmd 'test -s /mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/df2-12/run/TERMINAL.json' --cmd 'env -i PATH=/usr/bin:/bin LANG=C.UTF-8 RUS3_DIAGNOSTIC=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 HIP_VISIBLE_DEVICES=-1 ROCR_VISIBLE_DEVICES=-1 FILLER_ID="$FILLER_ID" FILLER_CPUS="$FILLER_CPUS" FILLER_NEEDGPU="$FILLER_NEEDGPU" FILLER_STOPFILE="$FILLER_STOPFILE" FILLER_END="$FILLER_END" FILLER_DEADLINE="$FILLER_DEADLINE" WS58_REGIONS="$WS58_REGIONS" /bin/bash /mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/df2-12/launch.sh --job';;
 '') exec > >(tee -a "$D/ws58-launcher.out") 2>&1; exec sudo -n --preserve-env=WS58_REGIONS,FILLER_CPUS /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --groups=992 /bin/bash "$D/launch.sh" --engine;;
 *) exit 64;;
esac
