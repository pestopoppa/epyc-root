#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex3-cs8-stt5-validation-nemotron-crisp-r3-20261030
export FILLER_RL=/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock
export LD_LIBRARY_PATH=/mnt/raid0/llm/whisper.cpp/build/bin OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 RUS3_DIAGNOSTIC=1 HIP_VISIBLE_DEVICES=-1 ROCR_VISIBLE_DEVICES=-1
cd "$D"
export CS8_SOURCE_SHA=2c54822aa94002d9f8163a00ca1c4ea413188680fb26c73b21ff3354a61d0a70
export CS8_PLAN_SHA=61722f4fa38bd4e50c1fc33a94e82f1ed3af414cbaaa1feb27dc12ababc71533
export CS8_INPUT_SHA=1bf2544d1d02d8f72b1a57d293c1e0869953aae31c3c526220b7965df09b536e
printf '%s  %s\n' "$CS8_SOURCE_SHA" "$D/SOURCE-SHA256SUMS" | sha256sum -c - >/dev/null
sha256sum --check "$D/SOURCE-SHA256SUMS" >/dev/null
P=/mnt/micron/codex3-cs8-stt2-crisp-20261030
[[ $(git -C "$P/src" rev-parse HEAD) == 2aa8d7669fcaa18d98d61a4bc8a077464e6b9919 ]]
[[ $(git -C "$P/src/ggml" rev-parse HEAD) == e2ae679a563014f46c546ce6c6448e8601e4dea6 ]]
for repo in "$P/src" "$P/src/ggml"; do git -C "$repo" diff --quiet; git -C "$repo" diff --cached --quiet; done
export LD_LIBRARY_PATH="/mnt/raid0/llm/tmp/codex3-cs8-stt5-accuracy-20261030/ultra-adapter/nemo-crisp/tc-adapter:$P/install/lib"
/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh /mnt/raid0/llm/tmp/codex3-cs8-stt5-accuracy-20261030/ultra-adapter/nemo-crisp/tc-adapter/runner "$P/install" >/dev/null
if [[ ${1:-} == --smoke ]]; then
 [[ $# == 1 ]] || exit 64
 exec taskset -c "${FILLER_CPUS:?}" python3 "$D/smoke-supervisor.py" 265 -- env CS8_SMOKE=1 python3 "$D/nemo_crisp_job.py"
fi
[[ $# == 0 ]] || exit 64
exec bash "$D/engine/filler_run13.sh" --id codex3-cs8-stt5-validation-nemotron-crisp-r3-20261030 --class cpu --role build --claim-cpus "${WS58_REGIONS:?}" --min-window 7520 --complete-cmd "test -s $D/validation-results/COMPLETE.json || test -s $D/validation-results/TERMINAL-INCOMPLETE.json" --cmd 'taskset -c "$FILLER_CPUS" python3 /mnt/raid0/llm/tmp/codex3-cs8-stt5-validation-nemotron-crisp-r3-20261030/nemo_crisp_job.py' --stop "$D/STOP" --workdir "$D"
