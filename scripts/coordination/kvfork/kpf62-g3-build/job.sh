#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/kpf62-g3-build-20261104
S=$D/source; B=$D/build; O=$D/out
: "${FILLER_THREADS:?}" "${FILLER_STOPFILE:?}" "${FILLER_DEADLINE:?}"
mkdir -p "$O"
python3 "$D/check.py"
python3 "$D/supervise.py" "$FILLER_STOPFILE" "$FILLER_DEADLINE" cmake -G "Unix Makefiles" -S "$S" -B "$B" -DCMAKE_BUILD_TYPE=RelWithDebInfo -DGGML_HIP=OFF -DGGML_CUDA=OFF -DGGML_BACKEND_DL=OFF -DLLAMA_CURL=OFF -DLLAMA_BUILD_TESTS=ON -DLLAMA_BUILD_UI=OFF >"$O/configure.log" 2>&1
python3 "$D/supervise.py" "$FILLER_STOPFILE" "$FILLER_DEADLINE" make -C "$B" -f tests/CMakeFiles/test-chunk-kv-g3.dir/build.make tests/CMakeFiles/test-chunk-kv-g3.dir/test-chunk-kv-g3.cpp.o -j "$FILLER_THREADS" >"$O/object.log" 2>&1
python3 "$D/check.py"
if [[ ${FILLER_SMOKE:-0} == 1 || ${FILLER_DRYRUN:-0} == 1 ]]; then
 python3 - "$B/tests/CMakeFiles/test-chunk-kv-g3.dir/test-chunk-kv-g3.cpp.o" "${FILLER_DRYRUN_RESULT_PATH:?}" <<'INNER'
import hashlib,json,pathlib,sys
p=pathlib.Path(sys.argv[1]); pathlib.Path(sys.argv[2]).write_text(json.dumps({'status':'compiled-object','object_size_bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'scope':'model-free qualification only'})+'\n')
INNER
 exit 0
fi
python3 "$D/supervise.py" "$FILLER_STOPFILE" "$FILLER_DEADLINE" cmake --build "$B" --target test-chunk-kv-g3 test-kpf62-outcome-budget --parallel "$FILLER_THREADS" >"$O/build.log" 2>&1
export LD_LIBRARY_PATH="$B/bin"
/bin/bash "$D/verify_ggml_linkage.sh" "$B/bin/test-chunk-kv-g3" "$B" >"$O/linkage.log" 2>&1
python3 "$D/supervise.py" "$FILLER_STOPFILE" "$FILLER_DEADLINE" "$B/bin/test-kpf62-outcome-budget" >"$O/budget.log" 2>&1
python3 "$D/supervise.py" "$FILLER_STOPFILE" "$FILLER_DEADLINE" python3 -m pytest -q "$S/scripts/chunk-kv/tests/test_g3_gate.py" "$S/scripts/chunk-kv/tests/test_g3_manifest.py" "$S/scripts/chunk-kv/tests/test_g3_outcome_guard_integration.py" >"$O/pytest.log" 2>&1
python3 "$D/check.py"
python3 "$D/proof.py"
