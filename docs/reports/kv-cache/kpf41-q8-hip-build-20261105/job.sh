#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/kpf41-q8-build-20261105
S="$D/source"; B="$D/build"; O="$D/out"
: "${FILLER_THREADS:?}" "${FILLER_STOPFILE:?}" "${FILLER_DEADLINE:?}"
if [[ ${FILLER_DRYRUN:-0} == 1 ]]; then B="${FILLER_DRYRUN_DIR:?}/build"; O="${FILLER_DRYRUN_DIR:?}/build-output"; fi
mkdir -p "$O"
python3 "$D/check.py"
export PATH="/opt/rocm/bin:$PATH" CMAKE_PREFIX_PATH=/opt/rocm HIPCXX=/opt/rocm/lib/llvm/bin/clang++
python3 "$D/supervise.py" "$FILLER_STOPFILE" "$FILLER_DEADLINE" cmake -G 'Unix Makefiles' -S "$S" -B "$B" -DCMAKE_BUILD_TYPE=Release -DGGML_HIP=ON -DGGML_BACKEND_DL=OFF -DAMDGPU_TARGETS=gfx90a -DLLAMA_CURL=OFF -DLLAMA_BUILD_TESTS=ON -DLLAMA_BUILD_SERVER=OFF -DLLAMA_BUILD_UI=OFF >"$O/configure.log" 2>&1
python3 "$D/supervise.py" "$FILLER_STOPFILE" "$FILLER_DEADLINE" make -C "$B" -f tests/CMakeFiles/test-kv-rows-vec-direct.dir/build.make tests/CMakeFiles/test-kv-rows-vec-direct.dir/test-kv-rows-vec-direct.cpp.o -j "$FILLER_THREADS" >"$O/object.log" 2>&1
python3 "$D/check.py"
if [[ ${FILLER_DRYRUN:-0} == 1 ]]; then
 python3 - "$B/tests/CMakeFiles/test-kv-rows-vec-direct.dir/test-kv-rows-vec-direct.cpp.o" "${FILLER_DRYRUN_RESULT_PATH:?}" <<'PY'
import hashlib,json,pathlib,sys
p=pathlib.Path(sys.argv[1]); pathlib.Path(sys.argv[2]).write_text(json.dumps({'status':'compiled-object','object_size_bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'scope':'actual fixture object only; no linked build or GPU parity'})+'\n')
PY
 exit 0
fi
python3 "$D/supervise.py" "$FILLER_STOPFILE" "$FILLER_DEADLINE" cmake --build "$B" --target test-kv-rows-vec-direct --parallel "$FILLER_THREADS" >"$O/build.log" 2>&1
export LD_LIBRARY_PATH="$B/bin:/opt/rocm/lib"
bash "$D/verify_ggml_linkage.sh" "$B/bin/test-kv-rows-vec-direct" "$B/bin" >"$O/linkage.log" 2>&1
python3 "$D/check.py"
python3 "$D/proof.py"
