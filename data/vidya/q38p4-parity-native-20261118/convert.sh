#!/bin/bash
set -euo pipefail
D=$(cd -- "$(dirname -- "$0")" && pwd -P)
C6=729599d69871181d67af715a4c2f9162d5153a2e
SRC=/mnt/raid0/llm/worktrees/kernels/refactor-c6-20261030
HF=/mnt/raid0/llm/models/Qwen3-4B-Instruct-2507
IMG='vllm/vllm-openai-rocm@sha256:4fcd39b758b660c4e9c345c021e2ea8f0ccdb31e3c32507d676cc3005ae83fba'
TARGET="$D/model/Qwen3-4B-Instruct-2507-BF16.gguf"
[ "$(git -C "$SRC" rev-parse HEAD)" = "$C6" ]
[ -z "$(git -C "$SRC" status --porcelain)" ]
[ ! -e "$TARGET" ] && [ ! -e "$TARGET.partial" ]
timeout --signal=TERM 180 docker run --rm --pull never --name q38p4-greedy-parity-cpu-conversion-20261118 \
  --network none --cpus 2 -u "$(id -u):$(id -g)" -e HOME=/tmp -e HF_HUB_OFFLINE=1 -e PYTHONPATH=/src/gguf-py \
  -v "$SRC:/src:ro" -v "$HF:/model:ro" -v "$D/model:/output" --entrypoint python3 "$IMG" \
  /src/convert_hf_to_gguf.py /model --outtype bf16 \
  --outfile /output/Qwen3-4B-Instruct-2507-BF16.gguf.partial > "$D/convert.log" 2>&1
[ -s "$TARGET.partial" ]
mv -- "$TARGET.partial" "$TARGET"
