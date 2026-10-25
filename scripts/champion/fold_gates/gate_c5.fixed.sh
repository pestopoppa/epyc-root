#!/bin/bash
# C5 correctness gate for kernels/builds/{cpu,gpu}-20261024-c72ec82f5-c5 (C4 cdb4d8c77 + 4976a189f fused decode default OFF + c72ec82f5 ws58 0001 / CH-24).  NOT RUN (prep).
# usage: gate_c5.sh cpu|gpu     env: GATE_CPUS (CPU set granted to this gate, required unless GATE_B_ONLY=1)
#   (a) tests from the image's bin/ directly (ctest would write Testing/ into the image):
#         test-llama-archs (FULL run, rc 0), test-llama-archs --yarn-kshift -s 1234, test-rope, test-dca, test-backend-ops -b CPU -o ROPE (448/448),
#         test-qwen4exp-fused-rope: rc 0 AND 5 'knob ... OK' lines (the C5 knob truth table: default / OFF only / ON=0 / ON+OFF -> graph,
#         ON only -> fused) AND 3 rope-config OK lines (native, yarn-f4-orig32, freq-base-1e4: fused opted in with ON=1 still matches the graph)
#   (b) fold_gate.py v4 (pinned copy ./fold_gate_src_v4) vs the C4 image cdb4d8c77, --expected-changed libllama.so (both kinds),
#         and libllama.so must actually be reported EXPECTED (code differs): proves the change is compiled in. Every ggml lib must be
#         byte-identical or EXPLAINED (no ggml code changed; 14c57cbe9 touches src/models/qwen4exp-fused.cpp only, so libggml-cpu does not move).
#   (c) llama-server --version names c72ec82f5 (build 10419), verify_ggml_linkage.sh
#   (d) CH-24 + knob strings:
#         d1 ch24_src_audit.py on the source worktree at the image commit: every /tmp/qwen4exp-builds site is behind a debug knob (AUDIT PASS);
#            then every /tmp/qwen4exp-builds literal that `strings` finds in ANY image lib must be one the audit found gated (none unknown)
#         d2 libllama carries GGML_FUSED_DECODE_ON (the opt-in knob is compiled in) and 'fused decode disabled for this model' (0001 compiled in)
#         d3 GGML_CUDA_GRAPH_MEMLOG (C4 content carried): gpu must have it in a lib, cpu in none
# GATE_B_ONLY=1 [GATE_SUFFIX=.v2]: offline re-gate (b)-(d) only.
set -uo pipefail
KIND=${1:-}; case "$KIND" in cpu|gpu) ;; *) echo "usage: $0 cpu|gpu"; exit 2 ;; esac
BONLY=${GATE_B_ONLY:-0}; SUFFIX=${GATE_SUFFIX:-}
if [ "$BONLY" = 1 ]; then CPUS=${GATE_CPUS:-0}; else CPUS=${GATE_CPUS:?set GATE_CPUS}; fi
HERE=/mnt/raid0/llm/tmp/c5-fold-prep
SRC=/mnt/raid0/llm/worktrees/c5-fold-20261024
CAND=c72ec82f5417bb2937310326120f149b665e8400; BASEC=cdb4d8c77c2300f61c404a3df6d1950934b39c98
S=/mnt/raid0/llm/kernels/builds
NEW=$S/$KIND-20261024-c72ec82f5-c5; BASE=$S/$KIND-20261024-cdb4d8c77-c4
OUT=$HERE/GATE_$KIND$SUFFIX.txt
: > "$OUT"; fail=0
say() { echo "$*" | tee -a "$OUT"; }
# BEGIN GATE VERDICT HELPERS
gate_set_verdict() {
  local rc=$1
  if [ "$rc" -eq 0 ]; then GATE_VERDICT=PASS; else GATE_VERDICT=FAIL; fail=1; fi
}
count_ok_lines() {
  sed -E 's/\x1B\[[0-9;]*m//g' "$1" | awk 'index($0, " OK") { n++ } END { print n+0 }'
}
count_matching_lines() {
  local pattern=$1 file=$2
  sed -E 's/\x1B\[[0-9;]*m//g' "$file" | awk -v pattern="$pattern" '$0 ~ pattern { n++ } END { print n+0 }'
}
# END GATE VERDICT HELPERS
[ -x "$NEW/bin/llama-server" ] && [ -d "$BASE/bin" ] || { say "FAIL: missing $NEW or $BASE"; exit 1; }
export LD_LIBRARY_PATH=$NEW/bin   # each tree its own ggml generation; verify below
unset GGML_FUSED_DECODE_ON GGML_FUSED_DECODE_OFF GGML_FUSED_DECODE_TRACE   # the tests set the knobs themselves
RUN="nice -n 19 taskset -c $CPUS"
say "gate $KIND $(date -u +%FT%TZ) new=$NEW base=$BASE"
if [ "$BONLY" = 1 ]; then
  say "== (a) tests: NOT re-run (offline re-gate)"
else
say "== (a) tests"
$RUN "$NEW/bin/test-llama-archs" > "$HERE/a_llama_archs_$KIND.log" 2>&1; rc=$?; gate_set_verdict "$rc"; say "(a0) test-llama-archs (full) rc=$rc $GATE_VERDICT"
$RUN "$NEW/bin/test-llama-archs" --yarn-kshift -s 1234 > "$HERE/a_yarn_kshift_$KIND.log" 2>&1; rc=$?; gate_set_verdict "$rc"; say "(a1) test-yarn-kshift rc=$rc $GATE_VERDICT"
for t in test-rope test-dca; do
  $RUN "$NEW/bin/$t" > "$HERE/a_${t}_$KIND.log" 2>&1; rc=$?; gate_set_verdict "$rc"; say "(a) $t rc=$rc $GATE_VERDICT"
done
L=$HERE/a_test-qwen4exp-fused-rope_$KIND.log
$RUN "$NEW/bin/test-qwen4exp-fused-rope" > "$L" 2>&1; rc=$?
nk=$(count_matching_lines '^knob .*  OK$' "$L"); nr=$(count_matching_lines '^(native|yarn-f4-orig32|freq-base-1e4) .*  OK$' "$L")
if [ "$rc" -eq 0 ] && [ "$nk" = 5 ] && [ "$nr" = 3 ]; then verdict=PASS; else verdict=FAIL; fail=1; fi
say "(a2) test-qwen4exp-fused-rope rc=$rc knob-OK=$nk/5 rope-OK=$nr/3 $verdict"
grep '^knob ' "$L" | sed 's/^/      /' | tee -a "$OUT" >/dev/null
$RUN "$NEW/bin/test-backend-ops" test -b CPU -o ROPE > "$HERE/a_tbo_cpu_rope_$KIND.log" 2>&1; rc=$?
say "(a) test-backend-ops -b CPU -o ROPE rc=$rc: $(grep -E 'tests passed' "$HERE/a_tbo_cpu_rope_$KIND.log" | tail -n1)"; [ $rc = 0 ] || fail=1
fi
say "== (b) fold_gate.py vs $(basename "$BASE")"
FG=$HERE/fold_gate_$KIND$SUFFIX.log
/usr/bin/python3 -I "$HERE/fold_gate_src_v4/scripts/kernel_rnd/fold_gate/fold_gate.py" --base-image "$BASE/bin" --new-image "$NEW/bin" \
   --src-repo /mnt/raid0/llm/llama.cpp --base-commit $BASEC --cand-commit $CAND \
   --expected-changed libllama.so > "$FG" 2>&1; rc=$?
cat "$FG" >> "$OUT"; [ $rc = 0 ] || { say "(b) fold_gate rc=$rc FAIL"; fail=1; }
if grep -E '^ *EXPECTED +libllama\.so' "$FG" >/dev/null; then say "(b) libllama.so reported EXPECTED (code differs): PASS"; else say "(b) FAIL: libllama.so not reported as changed (is the C5 change compiled in?)"; fail=1; fi
if grep -E '^ *EXPECTED +libggml' "$FG" >/dev/null; then say "(b) FAIL: a ggml lib changed (C5 touches no ggml code)"; fail=1; fi
say "== (c) versions"
v=$("$NEW/bin/llama-server" --version 2>&1 | tail -n 2 | tr '\n' ' '); say "$v"; echo "$v" | grep c72ec82f5 >/dev/null || { say "(c) FAIL version"; fail=1; }
/workspace/repos/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh "$NEW/bin/llama-server" > "$HERE/linkage_$KIND$SUFFIX.txt" 2>&1 && say "(c) linkage PASS" || { say "(c) linkage CHECK (see linkage_$KIND$SUFFIX.txt)"; fail=1; }
say "== (d) CH-24 + knob strings"
[ "$(git -C "$SRC" rev-parse HEAD)" = "$CAND" ] || { say "(d1) FAIL: $SRC HEAD is not the image commit $CAND (audit would read other source)"; fail=1; }
AJ=$HERE/audit_${KIND}$SUFFIX.json
/usr/bin/python3 -I "$HERE/ch24_src_audit.py" "$SRC" --json "$AJ" > "$HERE/audit_${KIND}$SUFFIX.txt" 2>&1; rc=$?
say "(d1) source audit rc=$rc: $(tail -n 2 "$HERE/audit_${KIND}$SUFFIX.txt" | tr '\n' ' ')"; [ $rc = 0 ] || fail=1
BL=$HERE/strings_tmp_${KIND}$SUFFIX.txt; : > "$BL"
for l in "$NEW"/bin/lib*.so*; do [ -f "$l" ] && [ ! -L "$l" ] || continue; strings -a "$l" | grep -F /tmp/qwen4exp-builds | sed "s#^#$(basename "$l")\t#" >> "$BL"; done
nb=$(wc -l < "$BL")
unk=$(/usr/bin/python3 -I -c '
import json,sys
g=set(json.load(open(sys.argv[1]))["literals_gated"])
bad=[l.rstrip("\n") for l in open(sys.argv[2]) if l.split("\t",1)[1].rstrip("\n") not in g]
print(len(bad)); [print("   unknown:", b, file=sys.stderr) for b in bad]' "$AJ" "$BL" 2>>"$OUT")
if [ "$unk" = 0 ] && [ "$nb" -gt 0 ]; then verdict=PASS; else verdict=FAIL; fail=1; fi
say "(d1) strings: $nb /tmp/qwen4exp-builds literal(s) in image libs ($(cut -f1 "$BL" | sort -u | tr '\n' ' ')), unknown-or-ungated=$unk $verdict"
LL=$(ls "$NEW"/bin/libllama.so* 2>/dev/null | head -n1)
for s in GGML_FUSED_DECODE_ON 'fused decode disabled for this model'; do
  if strings -a "$LL" | grep -F "$s" >/dev/null; then say "(d2) libllama has '$s': PASS"; else say "(d2) FAIL: '$s' not in $(basename "$LL")"; fail=1; fi
done
n=0; for l in "$NEW"/bin/lib*.so*; do [ -f "$l" ] || continue; if strings "$l" | grep GGML_CUDA_GRAPH_MEMLOG >/dev/null; then n=$((n+1)); say "   has MEMLOG: $(basename "$l")"; fi; done
if [ "$KIND" = gpu ]; then
  [ "$n" -ge 1 ] && say "(d3) PASS (MEMLOG compiled into $n lib)" || { say "(d3) FAIL: MEMLOG not in any lib"; fail=1; }
else
  [ "$n" = 0 ] && say "(d3) PASS (no ggml-cuda code in the cpu image)" || { say "(d3) FAIL: MEMLOG in a cpu-image lib"; fail=1; }
fi
[ $fail = 0 ] && say "GATE $KIND PASS" || say "GATE $KIND FAIL"
exit $fail
