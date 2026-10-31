#!/bin/bash
set -euo pipefail
ulimit -v 8388608
cd /mnt/raid0/llm/tmp/codex3-next-runtime-20261031-0245/cs22t1
for term in finished unfinished wait; do
  /usr/bin/env -i PATH=/usr/bin:/bin LD_LIBRARY_PATH=/mnt/raid0/llm/kernels/production/cpu OMP_NUM_THREADS=1 /mnt/raid0/llm/kernels/production/cpu/llama-tokenize -m /mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf -p "$term" --no-bos --ids > "TOKEN-$term.log" 2>&1
done
