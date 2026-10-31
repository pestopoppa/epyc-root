#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex3-cs8-stt5-accuracy-20261030/nemo-traced
T=/mnt/raid0/llm/tmp/codex3-cs8-stt2-transcribe-20261030
M=/mnt/raid0/llm/models/nemotron-3.5-asr-streaming-0.6b-Q8_0.gguf
export LD_LIBRARY_PATH="$T/install/lib" OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 HIP_VISIBLE_DEVICES=-1 ROCR_VISIBLE_DEVICES=-1
for right in 0 3 6 13; do
 for mode in auto forced; do
  args=(); [[ $mode == forced ]] && args=(--language en-US)
  "$D/transcribe-cli" --backend cpu --threads 2 --timestamps token --raw-tokens --stream-chunk-ms "$((80*(right+1)))" --stream-att-right "$right" "${args[@]}" -m "$M" -o "$D/$right-$mode.txt" /mnt/raid0/llm/whisper.cpp/samples/jfk.wav > "$D/$right-$mode.stdout" 2> "$D/$right-$mode.stderr"
 done
done
