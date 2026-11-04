#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf60-select-build-r3
S="$D/source"; O="$D/out"; B="$D/build"
: "${FILLER_THREADS:?}" "${FILLER_STOPFILE:?}" "${FILLER_DEADLINE:?}"
if [[ ${FILLER_DRYRUN:-0} == 1 ]]; then B="${FILLER_DRYRUN_DIR:?}/build"; O="${FILLER_DRYRUN_DIR:?}/build-output"; fi
mkdir -p "$O"
python3 "$D/check.py"
python3 "$D/supervise.py" "$FILLER_STOPFILE" "$FILLER_DEADLINE" cmake -G "Unix Makefiles" -S "$S" -B "$B" -DCMAKE_BUILD_TYPE=RelWithDebInfo -DGGML_HIP=OFF -DGGML_CUDA=OFF -DGGML_BACKEND_DL=OFF -DLLAMA_CURL=OFF -DLLAMA_BUILD_TESTS=ON -DLLAMA_BUILD_UI=OFF >"$O/configure.log" 2>&1
python3 "$D/supervise.py" "$FILLER_STOPFILE" "$FILLER_DEADLINE" make -C "$B" -f src/CMakeFiles/llama.dir/build.make src/CMakeFiles/llama.dir/llama-kv-cache.cpp.o -j "$FILLER_THREADS" >"$O/object.log" 2>&1
python3 "$D/check.py"
if [[ ${FILLER_DRYRUN:-0} == 1 ]]; then
 python3 - "$B/src/CMakeFiles/llama.dir/llama-kv-cache.cpp.o" "${FILLER_DRYRUN_RESULT_PATH:?}" <<'PY'
import hashlib,json,pathlib,sys
p=pathlib.Path(sys.argv[1]); pathlib.Path(sys.argv[2]).write_text(json.dumps({'status':'compiled-object','object_size_bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'scope':'model-free qualification only'})+'\n')
PY
 exit 0
fi
python3 "$D/supervise.py" "$FILLER_STOPFILE" "$FILLER_DEADLINE" cmake --build "$B" --target test-server-chunk-store test-chunk-kv --parallel "$FILLER_THREADS" >"$O/build.log" 2>&1
export LD_LIBRARY_PATH="$B/bin"
/bin/bash "$D/verify_ggml_linkage.sh" "$B/bin/test-chunk-kv" "$B" >"$O/linkage.log" 2>&1
python3 "$D/supervise.py" "$FILLER_STOPFILE" "$FILLER_DEADLINE" "$B/bin/test-server-chunk-store" >"$O/test.log" 2>&1
python3 "$D/check.py"
python3 "$D/proof.py"
