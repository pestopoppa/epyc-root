#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/rope-ctx-assessment/lsa-screen-20261103/critical-compute-20261104/ward-fix-088/hip-tests
B=${D%/hip-tests}/build/out
if [[ ${FILLER_DIRECT:-0} == 1 ]]; then
 exec 9>/mnt/raid0/llm/tmp/gpu_device.mi210_0.lock
 flock -n 9 || { echo 'MI210 device flock unavailable' >&2; exit 75; }
fi
python3 - "$D/approved-hip.json" <<'PY'
import hashlib,json,pathlib,sys
a=json.load(open(sys.argv[1]));assert a['reviewed'] and a['source_commit']=='088a77bd6ce5fac1ad3bf397912d884ae62b909e'
for p,h in a['pins'].items(): assert hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()==h,p
PY
[[ ! -f "$D/FAILED" ]]
unset GGML_BACKEND_PATH
export LD_LIBRARY_PATH="$B/bin:/opt/rocm/lib" ROCR_VISIBLE_DEVICES=0 HIP_VISIBLE_DEVICES=0 OMP_NUM_THREADS=2
export LD_PRELOAD=/mnt/raid0/llm/tmp/rope-ctx-assessment/lsa-screen-20261103/critical-compute-20261104/numerical-combined/exec-guard.so
/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh "$B/bin/test-lsa-native-hip-live" "$B" > "$D/linkage.txt"
for case in tied native-27b; do
 if [[ -f "$D/$case.pass" ]]; then sha256sum -c "$D/$case.pass"; continue; fi
 [[ ! -e ${FILLER_STOPFILE:?} && $(date +%s) -lt ${FILLER_DEADLINE:?} ]] || exit 75
 if [[ $case == tied ]]; then args=(--run-hip-ward-fixture "${D%/hip-tests}/fixture/tied513.lsafix"); else args=(--run-hip-27b); fi
 if ! /mnt/raid0/llm/epyc-inference-research/.venv/bin/python "$D/hip-case.py" "$case" "$B/bin/test-lsa-native-hip-live" "${args[@]}" > "$D/$case.log" 2>&1; then touch "$D/FAILED";exit 1;fi
 sha256sum "$D/$case/witness.json" "$D/$case/unit.log" "$D/$case.log" > "$D/$case.pass"
 printf '{"case":"%s"}\n' "$case" >> "$D/results.jsonl"
 if [[ $case == tied && ! -f "$D/qualification-observed" ]]; then touch "$D/qualification-observed";exit 75;fi
done
touch "$D/complete"
