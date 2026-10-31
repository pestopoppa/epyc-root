#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex3-cs8-stt5-accuracy-20261030/nemo-traced-v2
T=/mnt/raid0/llm/tmp/codex3-cs8-stt2-transcribe-20261030
W=/mnt/raid0/llm/tmp/codex3-ultra-torch-reference/control-tone.wav
export LD_LIBRARY_PATH="$T/install/lib" OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 HIP_VISIBLE_DEVICES=-1 ROCR_VISIBLE_DEVICES=-1
"$D/transcribe-cli" --backend cpu --threads 2 --timestamps token --raw-tokens --stream-chunk-ms 320 --stream-att-right 3 -m /mnt/raid0/llm/models/nemotron-3.5-asr-streaming-0.6b-Q8_0.gguf -o "$D/nemo-tone.txt" "$W" > "$D/nemo-tone.stdout" 2> "$D/nemo-tone.stderr"
"$D/transcribe-cli" --backend cpu --threads 2 --timestamps token --raw-tokens -m /mnt/raid0/llm/models/parakeet-tdt-0.6b-v3-F16.gguf -o "$D/v3-tone.txt" "$W" > "$D/v3-tone.stdout" 2> "$D/v3-tone.stderr"
