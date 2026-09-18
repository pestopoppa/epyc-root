#!/bin/bash
# TD-1d: bring up the frozen-v9 HIP server on the worker model, same shape as the
# 2026-09-17 typed-decision runs so the numbers stay comparable.
set -euo pipefail
OUT=/workspace/tmp/td1d-20260918
mkdir -p "$OUT"

BIN=/mnt/raid0/llm/llama.cpp/build-hip/bin/llama-server
MODEL=/mnt/raid0/llm/models/Qwen_Qwen3.6-35B-A3B-Q8_0.gguf
PORT=8199

test -x "$BIN"
test -f "$MODEL"

# three-ggml-generations hazard: pin the loader to THIS tree's libs, never ambient
export LD_LIBRARY_PATH=/mnt/raid0/llm/llama.cpp/build-hip/bin
export HIP_VISIBLE_DEVICES=0

# GPU host threads are 184-191 (the champion recipe's cpu_list; NOT 88-95)
setsid taskset -c 184-191 "$BIN" \
  --model "$MODEL" \
  --host 127.0.0.1 --port "$PORT" \
  --n-gpu-layers 99 \
  --parallel 4 \
  --ctx-size 131072 \
  --batch-size 2048 --ubatch-size 2048 \
  --threads 8 \
  --flash-attn on \
  --temp 0 --top-k 1 --top-p 0.95 \
  --jinja \
  > "$OUT/server-worker.log" 2>&1 &

PID=$!
echo "$PID" > "$OUT/server-worker.pid"
echo "launched pid=$PID port=$PORT"
echo "binary: $(sha256sum "$BIN" | cut -d' ' -f1)"
