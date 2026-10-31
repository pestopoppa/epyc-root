#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex3-cs8-stt5-accuracy-20261030/ultra-adapter/nemo-crisp/tc-adapter
S=/mnt/micron/codex3-cs8-stt2-crisp-20261030/install
M=/mnt/raid0/llm/models/nemotron-3.5-asr-streaming-0.6b-Q8_0.gguf
export LD_LIBRARY_PATH="$D:$S/lib" CRISPASR_NEMOTRON_STREAMING=1 CRISPASR_FC_PW_Q8=0 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 HIP_VISIBLE_DEVICES=-1 ROCR_VISIBLE_DEVICES=-1
for setting in 1:0 0:3 2:6 3:13; do
 preset=${setting%:*};right=${setting#*:}
 for lang in auto en-US; do
  "$D/runner" "$M" /mnt/raid0/llm/whisper.cpp/samples/jfk.wav "$preset" "$lang" 2 "$D/matrix-v2-$right-$lang.txt" > "$D/matrix-v2-$right-$lang.stdout" 2> "$D/matrix-v2-$right-$lang.stderr"
 done
done
