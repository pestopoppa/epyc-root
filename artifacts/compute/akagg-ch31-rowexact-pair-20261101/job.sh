#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/akagg-ch31-rowexact-pair-20261101
cd "$D"
sha256sum -c INPUT.sha256
IMAGE=/mnt/raid0/llm/kernels/builds/cpu-20261024-c72ec82f5-c5
printf '%s  %s\n' bc272ae3b6169e6cd924f390e664dd4c3c2117992844888f8c4226faafdbe58e "$IMAGE/SHA256SUMS" | sha256sum -c -
printf '%s  %s\n' 0ad885ffd4bb022fc4f0d33a3308fa108ef8613159d3b3a67e23abca056b7a6c /mnt/raid0/llm/models/unsloth/Qwen3.5-0.8B-GGUF/Qwen3.5-0.8B-Q8_0.gguf | sha256sum -c -
(cd "$IMAGE/bin" && sha256sum -c ../SHA256SUMS)
for lib in libggml.so libggml-base.so libggml-cpu.so libllama.so; do
  resolved=$(readlink -f "$IMAGE/bin/$lib")
  [[ "$resolved" == "$IMAGE/bin/"* ]] || { printf 'REFUSED library alias %s -> %s\n' "$lib" "$resolved" >&2; exit 1; }
done
strings "$IMAGE/bin/libggml-cpu.so.0.16.0" | grep -Fx GGML_ROWEXACT_N >/dev/null || { echo 'REFUSED: rowexact knob absent from manifested CPU library' >&2; exit 1; }
exec /usr/bin/python3 -I "$D/run.py"
