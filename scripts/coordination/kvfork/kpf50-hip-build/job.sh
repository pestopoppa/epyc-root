#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/kpf50-hip-build-20261104
S=$D/source; B=$D/build; O=$D/out
: "${FILLER_THREADS:?}" "${FILLER_STOPFILE:?}" "${FILLER_DEADLINE:?}"
mkdir -p "$O"
python3 "$D/check.py"
export PATH=/opt/rocm/bin:$PATH CMAKE_PREFIX_PATH=/opt/rocm HIPCXX=/opt/rocm/llvm/bin/clang++
python3 "$D/supervise.py" "$FILLER_STOPFILE" "$FILLER_DEADLINE" cmake -G 'Unix Makefiles' -S "$S" -B "$B" -DCMAKE_BUILD_TYPE=Release -DGGML_HIP=ON -DAMDGPU_TARGETS=gfx90a -DLLAMA_CURL=OFF -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_SERVER=ON -DLLAMA_BUILD_UI=OFF >"$O/configure.log" 2>&1
python3 "$D/supervise.py" "$FILLER_STOPFILE" "$FILLER_DEADLINE" make -C "$B" -f tools/server/CMakeFiles/server-context.dir/build.make tools/server/CMakeFiles/server-context.dir/server-context.cpp.o -j "$FILLER_THREADS" >"$O/object.log" 2>&1
python3 "$D/check.py"
if [[ ${FILLER_SMOKE:-0} == 1 || ${FILLER_DRYRUN:-0} == 1 ]]; then
 python3 - "$B/tools/server/CMakeFiles/server-context.dir/server-context.cpp.o" "${FILLER_DRYRUN_RESULT_PATH:?}" <<'PY'
import hashlib,json,pathlib,sys
p=pathlib.Path(sys.argv[1]); b=p.read_bytes()
assert b'KPF50_STEP_BEGIN' in b and b'KPF50_ITER_BEGIN' in b
pathlib.Path(sys.argv[2]).write_text(json.dumps({'status':'compiled-object','object_size_bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'scope':'build qualification only'})+'\n')
PY
 exit 0
fi
python3 "$D/supervise.py" "$FILLER_STOPFILE" "$FILLER_DEADLINE" cmake --build "$B" --target llama-server --parallel "$FILLER_THREADS" >"$O/build.log" 2>&1
export LD_LIBRARY_PATH="$B/bin:/opt/rocm/lib"
/bin/bash "$D/verify_ggml_linkage.sh" "$B/bin/llama-server" "$B" >"$O/linkage.log" 2>&1
python3 "$D/check.py"
python3 "$D/proof.py"
