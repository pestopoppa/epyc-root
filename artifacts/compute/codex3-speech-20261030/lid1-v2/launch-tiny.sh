#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex3-cs26-lid1-20261030
export LD_LIBRARY_PATH=/mnt/raid0/llm/whisper.cpp/build/bin HIP_VISIBLE_DEVICES=-1 ROCR_VISIBLE_DEVICES=-1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
export FILLER_RL=/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock
printf '%s  %s\n' f8869161c53fe00006be4823e44b2c0d2433beb9c3617a3e76876d62abfb5cc4 "$D/SOURCE-SHA256SUMS" | sha256sum -c - >/dev/null
sha256sum --check "$D/SOURCE-SHA256SUMS" >/dev/null
[[ $(git -C /mnt/raid0/llm/whisper.cpp rev-parse HEAD) == b307379226d93d9c5ed790d7cea0626613c0ef4b ]]
git -C /mnt/raid0/llm/whisper.cpp diff --quiet
git -C /mnt/raid0/llm/whisper.cpp diff --cached --quiet
/workspace/repos/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh /mnt/raid0/llm/whisper.cpp/build/bin/whisper-cli /mnt/raid0/llm/whisper.cpp >/dev/null
exec bash "$D/filler_run13.sh" --id codex3-cs26-lid1-tiny-20261030 --class cpu --role build --claim-cpus "${WS58_REGIONS:?}" --min-window 900 --complete-cmd "test -s $D/results/tiny/COMPLETE.json" --cmd 'taskset -c "$FILLER_CPUS" python3 /mnt/raid0/llm/tmp/codex3-cs26-lid1-20261030/job.py tiny' --stop "$D/STOP-tiny" --workdir "$D"
