#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/speculative-decoding-mtp/cafe4-build-row
S=/mnt/raid0/llm/tmp/speculative-decoding-mtp/cafe4-build-source
: "${FILLER_DEADLINE:?}" "${FILLER_STOPFILE:?}" "${FILLER_THREADS:?}"
check() { [[ ! -e "$FILLER_STOPFILE" && $(date +%s) -lt $FILLER_DEADLINE ]] || exit 75; }
check
python3 "$D/proof.py" source
mkdir -p "$D/runs"
R=$(mktemp -d "$D/runs/build-XXXXXXXX")
python3 "$D/supervise.py" "$FILLER_STOPFILE" "$FILLER_DEADLINE" cmake -G Ninja -S "$S" -B "$R/build" -DCMAKE_BUILD_TYPE=Release -DGGML_HIP=OFF -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_BUILD_SERVER=OFF > "$R/configure.log" 2>&1
check
if [[ ${FILLER_DRYRUN:-0} == 1 ]]; then
 python3 "$D/supervise.py" "$FILLER_STOPFILE" "$FILLER_DEADLINE" cmake --build "$R/build" --target src/CMakeFiles/llama.dir/llama-memory-recurrent.cpp.o --parallel "$FILLER_THREADS" > "$R/build.log" 2>&1
 python3 "$D/proof.py" write smoke "$R" "$FILLER_DRYRUN_RESULT_PATH"
 while [[ ! -e "$FILLER_STOPFILE" && $(date +%s) -lt $FILLER_DEADLINE ]]; do sleep 1; done
 exit 75
fi
python3 "$D/supervise.py" "$FILLER_STOPFILE" "$FILLER_DEADLINE" cmake --build "$R/build" --target llama --parallel "$FILLER_THREADS" > "$R/build.log" 2>&1
check
python3 "$D/supervise.py" "$FILLER_STOPFILE" "$FILLER_DEADLINE" g++ -std=c++17 -O2 -I"$S/include" -I"$S/ggml/include" "$D/candidate.cpp" -L"$R/build/bin" -Wl,-rpath,"$R/build/bin" -lllama -lggml -lggml-base -o "$R/candidate"
check
python3 "$D/proof.py" write build "$R" "$D/RESULT.json"
