#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/kpf17-oracle-build-20261104
S=$D/source
B=$D/build
O=$D/out
: "${FILLER_THREADS:?}" "${FILLER_STOPFILE:?}" "${FILLER_DEADLINE:?}"
mkdir -p "$O"
python3 "$D/check.py"
python3 "$D/supervise.py" "$FILLER_STOPFILE" "$FILLER_DEADLINE" cmake -G "Unix Makefiles" -S "$S" -B "$B" -DCMAKE_BUILD_TYPE=RelWithDebInfo -DGGML_HIP=OFF -DGGML_CUDA=OFF -DGGML_BACKEND_DL=OFF -DLLAMA_CURL=OFF -DLLAMA_BUILD_TESTS=ON -DLLAMA_BUILD_UI=OFF >"$O/configure.log" 2>&1
python3 "$D/supervise.py" "$FILLER_STOPFILE" "$FILLER_DEADLINE" make -C "$B" -f tests/CMakeFiles/test-save-load-state.dir/build.make tests/CMakeFiles/test-save-load-state.dir/test-save-load-state.cpp.o -j "$FILLER_THREADS" >"$O/object.log" 2>&1
python3 "$D/check.py"
if [[ ${FILLER_SMOKE:-0} == 1 || ${FILLER_DRYRUN:-0} == 1 ]]; then
 python3 - "$B/tests/CMakeFiles/test-save-load-state.dir/test-save-load-state.cpp.o" "${FILLER_DRYRUN_RESULT_PATH:?}" <<'PY'
import hashlib,json,pathlib,subprocess,sys
p=pathlib.Path(sys.argv[1]); b=subprocess.check_output(['strings',str(p)])
assert b'detected_stale_logits_above_aa_floor' in b and b'invalid_valid_restore' in b
pathlib.Path(sys.argv[2]).write_text(json.dumps({'status':'compiled-object','object_size_bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'scope':'qualification only; no model result'})+'\n')
PY
 exit 0
fi
python3 "$D/supervise.py" "$FILLER_STOPFILE" "$FILLER_DEADLINE" cmake --build "$B" --target test-save-load-state --parallel "$FILLER_THREADS" >"$O/build.log" 2>&1
python3 "$D/check.py"
export LD_LIBRARY_PATH="$B/bin"
/bin/bash "$D/verify_ggml_linkage.sh" "$B/bin/test-save-load-state" "$B" >"$O/linkage.log" 2>&1
python3 "$D/proof.py"
