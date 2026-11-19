#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/kpf17-partial-row
B="$D/build"
S="$D/source"
: "${FILLER_THREADS:?}" "${FILLER_CPUS:?}" "${FILLER_DEADLINE:?}" "${FILLER_STOPFILE:?}"
python3 "$D/check.py"
mkdir -p "$B" "$D/out"
python3 "$D/supervise.py" "$FILLER_STOPFILE" "$FILLER_DEADLINE" cmake -G Ninja -S "$S" -B "$B" -DCMAKE_BUILD_TYPE=Release -DGGML_HIP=OFF -DGGML_CUDA=OFF -DLLAMA_CURL=OFF -DLLAMA_BUILD_TESTS=ON -DLLAMA_BUILD_UI=OFF > "$D/out/configure.log" 2>&1
python3 "$D/supervise.py" "$FILLER_STOPFILE" "$FILLER_DEADLINE" cmake --build "$B" --target tests/CMakeFiles/test-save-load-state.dir/test-save-load-state.cpp.o --parallel "$FILLER_THREADS" > "$D/out/object.log" 2>&1
if [[ ${FILLER_DRYRUN:-0} == 1 ]]; then
 python3 - "$B/tests/CMakeFiles/test-save-load-state.dir/test-save-load-state.cpp.o" "${FILLER_DRYRUN_RESULT_PATH:?}" <<'PY'
import hashlib,json,pathlib,subprocess,sys
obj=pathlib.Path(sys.argv[1]); assert b'PARTIAL_ONLY busy-source restore PASS' in subprocess.check_output(['strings',str(obj)])
pathlib.Path(sys.argv[2]).write_text(json.dumps({'status':'compiled-test-object','sha256':hashlib.sha256(obj.read_bytes()).hexdigest(),'scope':'smoke only; no hybrid result'})+'\n')
PY
 exit 0
fi
python3 "$D/supervise.py" "$FILLER_STOPFILE" "$FILLER_DEADLINE" cmake --build "$B" --target test-save-load-state --parallel "$FILLER_THREADS" > "$D/out/build.log" 2>&1
export LD_LIBRARY_PATH="$B/bin"
/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh "$B/bin/test-save-load-state" "$B" > "$D/out/linkage.log" 2>&1
model=$(python3 -c 'import json;print(json.load(open("/mnt/raid0/llm/tmp/kvfork/kpf17-partial-row/model.json"))["path"])')
cd "$D/out"
set +e
python3 "$D/supervise.py" "$FILLER_STOPFILE" "$FILLER_DEADLINE" taskset -c "$FILLER_CPUS" "$B/bin/test-save-load-state" -m "$model" -n 4 -b 32 -c 512 -t "$FILLER_THREADS" > "$D/out/test.log" 2>&1
rc=$?
set -e
python3 - "$rc" <<'PY'
import hashlib,json,pathlib,sys
D=pathlib.Path('/mnt/raid0/llm/tmp/kvfork/kpf17-partial-row'); log=(D/'out/test.log').read_text(errors='replace'); rc=int(sys.argv[1]); marker='Test 6: PARTIAL_ONLY busy-source restore PASS'; skip='Test 6: SKIP'
status='OBSERVED_PASS' if rc==0 and marker in log and skip not in log else 'INVALID'
bin=D/'build/bin/test-save-load-state';m=json.loads((D/'model.json').read_text())
r={'schema':'kpf17.partial.busy-source.diagnostic.v1','status':status,'rc':rc,'marker':marker in log,'skip':skip in log,'model':m,'source_commit':'a1f0c8cf9bd7102415a72577474f307b8ba94db9','patched_test_sha256':'33c2e9e54376515febeae3531ef4f5fa7038033bf7589516fda5a732428d0d5f','binary_sha256':hashlib.sha256(bin.read_bytes()).hexdigest(),'test_log_sha256':hashlib.sha256((D/'out/test.log').read_bytes()).hexdigest(),'scope':'diagnostic only; fixed 1e-3 tolerance is not a defect gate; no mutation control'}
(D/'out/RESULT.json').write_text(json.dumps(r,sort_keys=True)+'\n')
PY
[[ "$rc" == 0 ]]
