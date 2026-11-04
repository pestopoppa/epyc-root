#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/rope-ctx-assessment/lsa-screen-20261103/critical-compute-20261104/final-cpu-cases
B=/mnt/raid0/llm/tmp/rope-ctx-assessment/lsa-screen-20261103/critical-compute-20261104/final-cpu/out
S=/mnt/raid0/llm/tmp/rope-ctx-assessment/lsa-screen-20261103
python3 - "$D/approved-cpu.json" <<'PY'
import hashlib,json,pathlib,sys
a=json.load(open(sys.argv[1])); assert a['reviewed'] is True
for p,h in a['pins'].items(): assert hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()==h,p
PY
[[ ! -f "$D/FAILED" ]]
unset GGML_BACKEND_PATH
export LD_LIBRARY_PATH="$B/bin" OMP_NUM_THREADS=4
export LD_PRELOAD=/mnt/raid0/llm/tmp/rope-ctx-assessment/lsa-screen-20261103/critical-compute-20261104/numerical-combined/exec-guard.so
/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh "$B/bin/test-lsa-graph-integration" "$B" > "$D/linkage.txt"
if [[ ! -f "$D/load-witness.so" ]]; then gcc -O2 -shared -fPIC "$D/load-witness.c" -o "$D/load-witness.so"; sha256sum "$D/load-witness.so" > "$D/load-witness.sha256"; fi
sha256sum -c "$D/load-witness.sha256"
cases=(disabled-default late-fallback late-fallback-q8 selected-success-q8 mrope-text-admission native-unit runtime-unit random pca distilled)
checkpoint=0; [[ -f "$D/${cases[0]}.pass" ]] || checkpoint=1
missing=0
for case in "${cases[@]}"; do
 if [[ -f "$D/$case.pass" ]]; then (( missing == 0 )) || exit 1; sha256sum -c "$D/$case.pass"; continue; fi
 missing=1
 [[ ! -e ${FILLER_STOPFILE:?} && $(date +%s) -lt ${FILLER_DEADLINE:?} ]] || exit 75
 case "$case" in
  disabled-default|late-fallback|late-fallback-q8|selected-success-q8|mrope-text-admission)
   cmd=(/mnt/raid0/llm/epyc-inference-research/.venv/bin/python "$D/run_case.py" cpu "$case" "$B/bin/test-lsa-graph-integration" "$D/$case") ;;
  native-unit) cmd=(/mnt/raid0/llm/epyc-inference-research/.venv/bin/python "$D/native-case.py" "$case" "$B/bin/test-lsa-native-live") ;;
  runtime-unit) cmd=(/mnt/raid0/llm/epyc-inference-research/.venv/bin/python "$D/native-case.py" "$case" "$B/bin/test-lsa-runtime-live") ;;
  random) cmd=(/mnt/raid0/llm/epyc-inference-research/.venv/bin/python "$D/native-case.py" "$case" "$B/bin/test-lsa-native-live" --projection-fixture "$S/native-cpu-fixtures-v4/random27b.lsapro") ;;
  pca) cmd=(/mnt/raid0/llm/epyc-inference-research/.venv/bin/python "$D/native-case.py" "$case" "$B/bin/test-lsa-native-live" --projection-fixture "$S/native-cpu-fixtures-v4/released27b-pca-layer3.lsapro") ;;
  distilled) cmd=(/mnt/raid0/llm/epyc-inference-research/.venv/bin/python "$D/native-case.py" "$case" "$B/bin/test-lsa-native-live" --projection-fixture "$S/native-cpu-fixtures-v4/released27b-distilled-layer3.lsapro") ;;
 esac
 if ! "${cmd[@]}" > "$D/$case.log" 2>&1; then touch "$D/FAILED"; exit 1; fi
 sha256sum "$D/$case/witness.json" "$D/$case/unit.log" "$D/$case.log" > "$D/$case.pass"
 printf '{"case":"%s"}\n' "$case" >> "$D/results.jsonl"
 (( checkpoint == 0 )) || exit 75
done
touch "$D/complete"
