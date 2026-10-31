#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex3-cs8-stt5-validation-ultra-20261030
export FILLER_RL=/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock
export LD_LIBRARY_PATH=/mnt/raid0/llm/whisper.cpp/build/bin OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 RUS3_DIAGNOSTIC=1 HIP_VISIBLE_DEVICES=-1 ROCR_VISIBLE_DEVICES=-1
cd "$D"
export CS8_SOURCE_SHA=5d3bb46a4b240d78b6bb4b984c0f1264ae50f424633ebe1c7c21d5525946b5a0
export CS8_PLAN_SHA=61722f4fa38bd4e50c1fc33a94e82f1ed3af414cbaaa1feb27dc12ababc71533
export CS8_INPUT_SHA=1bf2544d1d02d8f72b1a57d293c1e0869953aae31c3c526220b7965df09b536e
printf '%s  %s\n' "$CS8_SOURCE_SHA" "$D/SOURCE-SHA256SUMS" | sha256sum -c - >/dev/null
sha256sum --check "$D/SOURCE-SHA256SUMS" >/dev/null
P=/mnt/micron/codex3-cs8-stt2-crisp-20261030
[[ $(git -C "$P/src" rev-parse HEAD) == 2aa8d7669fcaa18d98d61a4bc8a077464e6b9919 ]]
[[ $(git -C "$P/src/ggml" rev-parse HEAD) == e2ae679a563014f46c546ce6c6448e8601e4dea6 ]]
for repo in "$P/src" "$P/src/ggml"; do git -C "$repo" diff --quiet; git -C "$repo" diff --cached --quiet; done
export LD_LIBRARY_PATH="/mnt/raid0/llm/tmp/codex3-cs8-stt5-accuracy-20261030/ultra-adapter/ultra-traced:$P/install/lib"
/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh "$P/install/bin/crispasr" "$P/install" >/dev/null
if [[ ${1:-} == --smoke ]]; then
 [[ $# == 1 ]] || exit 64
 exec taskset -c "${FILLER_CPUS:?}" python3 "$D/smoke-supervisor.py" 265 -- env CS8_SMOKE=1 python3 "$D/ultra_job.py"
fi
[[ $# == 0 ]] || exit 64
exec bash "$D/engine/filler_run13.sh" --id codex3-cs8-stt5-validation-ultra-20261030 --class cpu --role build --claim-cpus "${WS58_REGIONS:?}" --min-window 900 --complete-cmd "test -s $D/validation-results/COMPLETE.json || test -s $D/validation-results/TERMINAL-INCOMPLETE.json" --cmd 'taskset -c "$FILLER_CPUS" python3 /mnt/raid0/llm/tmp/codex3-cs8-stt5-validation-ultra-20261030/ultra_job.py' --stop "$D/STOP" --workdir "$D"
