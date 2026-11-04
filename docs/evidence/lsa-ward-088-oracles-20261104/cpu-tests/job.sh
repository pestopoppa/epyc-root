#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/rope-ctx-assessment/lsa-screen-20261103/critical-compute-20261104/ward-fix-088/cpu-tests
B=${D%/cpu-tests}/build/out/bin
cd "$D"
sha256sum -c pins.sha256 >/dev/null
[[ ! -e ${FILLER_STOPFILE:?} && $(date +%s) -lt ${FILLER_DEADLINE:?} ]] || exit 75
export LD_LIBRARY_PATH="$B:/opt/rocm/lib" OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
run_case() {
 local name=$1;shift
 [[ ! -e $FILLER_STOPFILE && $(date +%s) -lt $FILLER_DEADLINE ]] || exit 75
 LD_DEBUG=libs timeout 300 "$B/test-lsa-native-live" "$@" > "$D/$name.log" 2> "$D/$name.linkage.log"
 grep -F "$B/libllama.so" "$D/$name.linkage.log" >/dev/null
 sha256sum "$D/$name.log" "$D/$name.linkage.log" > "$D/$name.receipt"
 printf '{"unit":"%s"}\n' "$name" >> "$D/results.jsonl"
}
if [[ ! -f tied.receipt ]]; then
 run_case tied --reference-fixture ../fixture/tied513.lsafix
 exit 75
fi
sha256sum -c tied.receipt >/dev/null
run_case native-unit
run_case random --reference-fixture /mnt/raid0/llm/tmp/rope-ctx-assessment/lsa-screen-20261103/native-cpu-fixtures-v4/random.lsafix
run_case projected5k --reference-fixture /mnt/raid0/llm/tmp/rope-ctx-assessment/lsa-screen-20261103/native-cpu-fixtures-v4/projected27b.lsafix
run_case pca-projection --projection-fixture /mnt/raid0/llm/tmp/rope-ctx-assessment/lsa-screen-20261103/native-cpu-fixtures-v4/released27b-pca-layer3.lsapro
touch complete
