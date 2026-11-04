#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/rope-ctx-assessment/lsa-screen-20261103/critical-compute-20261104/numerical-combined
S=/mnt/raid0/llm/tmp/rope-ctx-assessment/lsa-screen-20261103
[[ -f "$D/approved.json" ]]
python3 - "$D/approved.json" <<'PY'
import hashlib,json,pathlib,sys
a=json.load(open(sys.argv[1])); assert a['reviewed'] is True
for p,h in a['helper_sha256'].items(): assert hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()==h,p
PY
compgen -G "$D/FAILED-*" >/dev/null && { echo 'prior failure requires review' >&2; exit 1; }
sha256sum -c "$D/source-sha256.txt"
[[ ! -e ${FILLER_STOPFILE:?} && $(date +%s) -lt ${FILLER_DEADLINE:?} ]] || exit 75
unset LD_PRELOAD GGML_BACKEND_PATH
export LD_LIBRARY_PATH="$S/build-cpu/bin" OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
if [[ ! -f "$D/binary-sha256.txt" ]]; then
 g++ -std=c++17 -O2 -ffp-contract=off -I "$S/native-cpu-fixtures-v4/source-snapshot/src" -I "$S/llama-native-c5/ggml/include" "$S/numerics-debug-20261104/llama-lsa-native-combined-candidate.cpp" "$S/native-cpu-fixtures-v4/source-snapshot/tests/test-lsa-native.cpp" -L "$S/build-cpu/bin" -Wl,-rpath,"$S/build-cpu/bin" -lggml-cpu -lggml-base -o "$D/test-combined"
 gcc -O2 -fPIC -shared "$D/exec-guard.c" -ldl -o "$D/exec-guard.so"
 gcc -O2 "$D/guard-control.c" -o "$D/guard-control"
 LD_PRELOAD="$D/exec-guard.so" "$D/guard-control"
 objdump -d "$D/test-combined" > "$D/disassembly.txt"
 grep -Eiq '\bvdpbf16ps\b' "$D/disassembly.txt"
 if grep -Eiq '\b(v?fmadd|v?fmsub|v?fnmadd|v?fnmsub)[a-z0-9]*\b' "$D/disassembly.txt"; then echo 'FMA found' >&2; exit 1; fi
 /mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh "$D/test-combined" "$S/build-cpu" > "$D/linkage.txt"
 ldd "$D/test-combined" > "$D/ldd.txt"
 sha256sum "$D/test-combined" "$D/exec-guard.so" "$D/guard-control" "$D/disassembly.txt" "$D/source-sha256.txt" > "$D/binary-sha256.txt"
 printf '{"unit":"compiled-candidate"}\n' >> "$D/results.jsonl"
 exit 75
fi
sha256sum -c "$D/binary-sha256.txt"
[[ ! -e $FILLER_STOPFILE && $(date +%s) -lt $FILLER_DEADLINE ]] || exit 75
if [[ ! -f "$D/unit.pass" ]]; then
 if ! LD_PRELOAD="$D/exec-guard.so" "$D/test-combined" > "$D/unit.log" 2>&1; then touch "$D/FAILED-unit"; exit 1; fi
 sha256sum "$D/unit.log" > "$D/unit.pass"
fi
sha256sum -c "$D/unit.pass"
[[ ! -e $FILLER_STOPFILE && $(date +%s) -lt $FILLER_DEADLINE ]] || exit 75
if ! LD_PRELOAD="$D/exec-guard.so" "$D/test-combined" --projection-fixture "$S/native-cpu-fixtures-v4/random27b.lsapro" > "$D/projection.log" 2>&1; then touch "$D/FAILED-projection"; exit 1; fi
grep -E '^KEY_MISMATCH count=[0-9]+ max_bf16_steps=[0-9]+$' "$D/projection.log" > "$D/projection-count.txt"
printf '{"unit":"unit-and-random-projection"}\n' >> "$D/results.jsonl"
touch "$D/complete"
