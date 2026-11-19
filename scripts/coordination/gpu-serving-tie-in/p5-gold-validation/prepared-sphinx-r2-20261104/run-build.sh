#!/bin/bash
set -uo pipefail
D=/mnt/raid0/llm/tmp/gpu-serving-tie-in/p5-sphinx-second-r2-20261104
/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock run --cpu-list 48-51 --role build --timeout-s 1 --tag p5-sphinx-image-preparation -- env P5_BUILD_REGION_LOCK_HELD=48-51 /mnt/raid0/llm/epyc-inference-research/.venv-swebench/bin/python -B "$D/build-sealed.py"
rc=$?
printf '%s\n' "$rc" > "$D/preparation.exit"
if [[ "$rc" == 0 ]]; then
  DEST=/mnt/raid0/llm/worktrees/mains/h-gpu-serving-tie-in/scripts/coordination/gpu-serving-tie-in/p5-gold-validation/prepared-sphinx-20261104
  python3 "$D/retain.py" "$D" "$DEST"
  rc=$?
  printf '%s\n' "$rc" > "$D/preparation.exit"
fi
if [[ "$rc" == 0 ]]; then touch "$D/preparation.done"; else touch "$D/preparation.failed"; fi
exit "$rc"
