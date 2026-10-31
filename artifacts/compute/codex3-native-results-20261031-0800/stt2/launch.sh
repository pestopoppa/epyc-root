#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex3-cs8-stt2-transcribe-20261030
export LD_LIBRARY_PATH="$D/install/lib" OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 RUS3_DIAGNOSTIC=1 HIP_VISIBLE_DEVICES=-1 ROCR_VISIBLE_DEVICES=-1
cd "$D"
printf '2ffaa3939c113f16fe3a57acdd0ce81d45bb56179aeb905efae4bf0e946649ee  %s\n' "$D/SOURCE-SHA256SUMS" | sha256sum -c - >/dev/null
sha256sum --check "$D/SOURCE-SHA256SUMS" >/dev/null
if [[ ${1:-} == --smoke ]]; then
  [[ $# == 1 ]] || exit 64
  exec taskset -c "${FILLER_CPUS:?}" python3 "$D/smoke-supervisor.py" 265 -- env CS8_SMOKE=1 python3 "$D/job.py"
fi
[[ $# == 0 ]] || exit 64
exec bash "$D/engine/filler_run13.sh" --id codex3-cs8-stt2-transcribe-cpu-20261030 --class cpu --role build --claim-cpus "${WS58_REGIONS:?}" --min-window 900 --complete-cmd "test -s $D/results/COMPLETE.json || test -s $D/results/TERMINAL-INCOMPLETE.json" --cmd 'taskset -c "$FILLER_CPUS" python3 /mnt/raid0/llm/tmp/codex3-cs8-stt2-transcribe-20261030/job.py' --stop "$D/STOP" --workdir "$D"
