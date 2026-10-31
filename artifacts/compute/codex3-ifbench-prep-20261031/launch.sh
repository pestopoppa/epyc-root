#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ifbench
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 RUS3_DIAGNOSTIC=1 HIP_VISIBLE_DEVICES=-1 ROCR_VISIBLE_DEVICES=-1 PYTHONDONTWRITEBYTECODE=1
cd "$D"
printf '%s  %s\n' 13328ca2547c4dbd2aaa26b6e0fb7ecd8cdf01c95774b45f1d6106ed8f46be0c "$D/SOURCE-SHA256SUMS" | sha256sum -c --quiet
printf '%s  %s\n' 1efb988ecc81098054e50d64d9b912f5b809b30af294a521e3175753f79a949c "$D/EARLY.sha256" | sha256sum -c --quiet
sha256sum -c --quiet "$D/EARLY.sha256"
case ${1:-} in
 --job) sha256sum -c --quiet "$D/SOURCE-SHA256SUMS"; sha256sum -c --quiet "$D/RUNTIME-INPUTS.sha256"; sha256sum -c --quiet "$D/SCORE-RUNTIME.sha256"; sha256sum -c --quiet "$D/MODEL.sha256"; export IFBENCH_MODE=full; exec taskset -c "${FILLER_CPUS:?}" /usr/bin/python3 -B "$D/worker.py";;
 --job-check) sha256sum -c --quiet "$D/SOURCE-SHA256SUMS"; /usr/bin/python3 -c 'import pathlib; assert all(pathlib.Path(x).exists() for x in ["/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf","/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ifbench/venv/bin/python","/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ifbench/source/run_eval.py","/mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ifbench/nltk_data/tokenizers/punkt"]); print("HOST paths exist")';;
 --smoke) sha256sum -c --quiet "$D/SOURCE-SHA256SUMS"; sha256sum -c --quiet "$D/RUNTIME-INPUTS.sha256"; sha256sum -c --quiet "$D/SCORE-RUNTIME.sha256"; export IFBENCH_MODE=smoke FILLER_DEADLINE=$(( $(date +%s) + 250 )); exec taskset -c "${FILLER_CPUS:?}" /usr/bin/python3 -B "$D/smoke-supervisor.py" 265 -- /usr/bin/python3 -B "$D/worker.py";;
 --engine) export FILLER_RL="$D/region-lock"; exec /bin/bash "$D/engine/filler_run13.sh" --id codex3-cj6-ifbench-27b-20261031 --class cpu --role bench --claim-cpus "${WS58_REGIONS:?}" --min-window 1800 --stop "$D/STOP" --workdir "$D" --complete-cmd 'test -s /mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ifbench/run/TERMINAL.json' --cmd 'env -i PATH=/usr/bin:/bin LANG=C.UTF-8 RUS3_DIAGNOSTIC=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 HIP_VISIBLE_DEVICES=-1 ROCR_VISIBLE_DEVICES=-1 FILLER_ID="$FILLER_ID" FILLER_CPUS="$FILLER_CPUS" FILLER_NEEDGPU="$FILLER_NEEDGPU" FILLER_STOPFILE="$FILLER_STOPFILE" FILLER_END="$FILLER_END" FILLER_DEADLINE="$FILLER_DEADLINE" WS58_REGIONS="$WS58_REGIONS" /bin/bash /mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/ifbench/launch.sh --job';;
 '') exec > >(tee -a "$D/ws58-launcher.out") 2>&1; exec sudo -n --preserve-env=WS58_REGIONS,FILLER_CPUS /usr/bin/chroot /proc/1/root /usr/bin/setpriv --reuid=1000 --regid=1000 --groups=992 /bin/bash "$D/launch.sh" --engine;;
 *) exit 64;;
esac
