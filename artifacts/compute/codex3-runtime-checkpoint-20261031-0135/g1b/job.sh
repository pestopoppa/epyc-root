#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex3-next-cpu-prep-20261031-0110
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 HIP_VISIBLE_DEVICES=-1 ROCR_VISIBLE_DEVICES=-1 PYTHONDONTWRITEBYTECODE=1
case ${1:?} in
 smoke) export G1_WORKERS=1; MAN="$D/control.json"; OUT="$D/smoke-result";;
 cutoff) export G1_WORKERS=1; MAN="$D/control.json"; OUT="$D/cutoff-result";;
 full) export G1_WORKERS=10; MAN="$D/cohort.json"; OUT="$D/results";;
 *) exit 64;;
esac
/usr/bin/env -u LD_PRELOAD LD_LIBRARY_PATH=/mnt/raid0/llm/qwentts.cpp/build:/opt/rocm/lib /mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh /mnt/raid0/llm/qwentts.cpp/build/qwen-tts /mnt/raid0/llm/qwentts.cpp/build > "$OUT.linkage-tts.txt"
/usr/bin/env -u LD_PRELOAD LD_LIBRARY_PATH=/mnt/raid0/llm/whisper.cpp/build/bin:/opt/rocm/lib /mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh /mnt/raid0/llm/whisper.cpp/build/bin/whisper-cli /mnt/raid0/llm/whisper.cpp/build > "$OUT.linkage-stt.txt"
python3 -B "$D/worker.py" "$MAN" "$OUT"
if [[ $1 == full && -f "$OUT/COMPLETE.json" ]]; then python3 -B "$D/analyze.py" "$OUT" "$MAN"; fi
