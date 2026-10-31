#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex3-ultra-torch-reference-v2
export CS8_SOURCE_SHA=e0580422ae608dc4546c240ff36d4e88c17b7c79dcaccadba8171b59ad36b234
printf '%s  %s\n' "$CS8_SOURCE_SHA" "$D/SOURCE-SHA256SUMS" | sha256sum -c - >/dev/null
sha256sum --check "$D/SOURCE-SHA256SUMS" >/dev/null
export CS8_PLAN_SHA=76624794f3ee5f32686adc9956891e9d12eed0b53c2bc3e1ba9978ef88cec621 CS8_NATIVE_SHA=549de26b9eaf3369c8ebd67e49769e2f728c182f8e8d842c818838800d7e0985
export FILLER_RL=/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 RUS3_DIAGNOSTIC=1 HIP_VISIBLE_DEVICES=-1 ROCR_VISIBLE_DEVICES=-1
cd "$D"
if [[ ${1:-} == --smoke ]]; then
 [[ $# == 1 ]] || exit 64
 exec taskset -c "${FILLER_CPUS:?}" /usr/bin/python3 "$D/supervisor.py" 265 -- env CS8_SMOKE=1 /usr/bin/python3 "$D/job.py"
fi
[[ $# == 0 ]] || exit 64
exec bash "$D/engine/filler_run13.sh" --id codex3-ultra-independent-25-20261031 --class cpu --role build --claim-cpus "${WS58_REGIONS:?}" --min-window 900 --complete-cmd "test -s $D/engineering25-results/TERMINAL.json" --cmd 'taskset -c "$FILLER_CPUS" /usr/bin/python3 /mnt/raid0/llm/tmp/codex3-ultra-torch-reference-v2/job.py' --stop "$D/STOP" --workdir "$D"
