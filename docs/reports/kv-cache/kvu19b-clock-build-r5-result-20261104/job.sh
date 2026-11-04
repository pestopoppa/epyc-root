#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/kvu19b-profiler-r5-20261104
: "${FILLER_STOPFILE:?}" "${FILLER_DEADLINE:?}"
python3 "$D/check.py"
if [[ ${FILLER_DRYRUN:-0} == 1 ]]; then
 python3 -c 'import os,sys; a=os.sched_getaffinity(0); sys.exit(0 if len(a)==4 else 1)'
fi
if [[ ${FILLER_DRYRUN:-0} == 1 ]]; then O="${FILLER_DRYRUN_RESULT_PATH:?}.build"; else O="$D/out"; fi
mkdir -p "$O"
python3 "$D/supervise.py" "$FILLER_STOPFILE" "$FILLER_DEADLINE" /usr/bin/g++ -O2 -std=c++17 -I"$D/headers/llama" -I"$D/headers/ggml" -I/opt/rocm/include "$D/p3batch-clock.cpp" -L"$D/bin" "-Wl,-rpath,$D/bin" -lllama -lggml -lggml-base -ldl -o "$O/p3batch-clock" >"$O/build.log" 2>&1
python3 "$D/check.py"
python3 "$D/finalize.py" "$O" "${FILLER_DRYRUN_RESULT_PATH:-}"
