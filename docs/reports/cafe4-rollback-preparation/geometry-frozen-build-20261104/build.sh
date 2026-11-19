#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/df2/cafe4-geometry-frozen-build
S=/mnt/raid0/llm/tmp/df2/cafe4-geometry-frozen-source
: "${FILLER_DEADLINE:?}" "${FILLER_STOPFILE:?}" "${FILLER_THREADS:?}"
check() { [[ ! -e "$FILLER_STOPFILE" && $(date +%s) -lt $FILLER_DEADLINE ]] || exit 75; }
check
python3 "$D/proof.py" source
mkdir -p "$D/runs"
R=$(mktemp -d "$D/runs/build-XXXXXXXX")
if [[ ${FILLER_DRYRUN:-0} == 1 ]]; then
 python3 "$D/supervise.py" "$FILLER_STOPFILE" "$FILLER_DEADLINE" c++ -std=c++17 -O2 -I"$D" -I"$S/common" -I"$S/src" -I"$S/include" -I"$S/ggml/include" -c "$D/candidate.cpp" -o "$R/candidate.o"
 python3 "$D/proof.py" write smoke "$R" "$FILLER_DRYRUN_RESULT_PATH"
 while [[ ! -e "$FILLER_STOPFILE" && $(date +%s) -lt $FILLER_DEADLINE ]]; do sleep 1; done
 exit 75
fi
python3 "$D/supervise.py" "$FILLER_STOPFILE" "$FILLER_DEADLINE" cmake -G Ninja -S "$S" -B "$R/build" -DCAFE4_MTP_DIR="$D" -DCMAKE_BUILD_TYPE=Release -DGGML_HIP=OFF -DLLAMA_BUILD_COMMON=ON -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=ON -DLLAMA_BUILD_TOOLS=OFF -DLLAMA_BUILD_SERVER=OFF -DLLAMA_CURL=OFF > "$R/configure.log" 2>&1
check
python3 "$D/supervise.py" "$FILLER_STOPFILE" "$FILLER_DEADLINE" cmake --build "$R/build" --target cafe4-mtp-rollback --parallel "$FILLER_THREADS" > "$R/build.log" 2>&1
check
LD_LIBRARY_PATH="$R/build/bin" ldd "$R/build/bin/cafe4-mtp-rollback" > "$R/linkage.log"
python3 "$D/proof.py" write build "$R" "$D/RESULT.json"
