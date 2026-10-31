#!/bin/bash
# bundle_gate_c5.sh -- C5 fold serving gates (CH-31): C5 = experimental/champion-c5-20261024 @ c72ec82f5 vs the champion (C3 dcc853b55 by
# default; C5_CHAMP_IMAGE overrides, e.g. the C4 image after a C4 CAS -- C4's CPU libs are code-identical to C3's). NOT RUN (prep, 2026-10-24).
# Derived from /mnt/raid0/llm/tmp/c4-fold-prep/bundle_gate_c4.sh (itself from c3/c2): same instruments, same window guard, same re-exec-ITSELF claim.
#   (b) TIMING, whole host quiet: Q38FN C5 vs champion, 5 matched pairs, gate_compare.py q38fn (the AK loop's matched_process_v2 instrument,
#       unchanged). Both arms carry the frozen launch env, which sets GGML_FUSED_DECODE_OFF=1 -- the measured frame (the instrument refuses
#       arms that differ beyond the build). NO calibrated floor: a SIGN claim only (decisive=None by construction).
#   (c) CORRECTNESS, one quarter: Q38FN greedy identity with the DEFAULT env (greedy_compare_c5.py, own-pid server per arm, sequential):
#         CHAMP = champion image, frozen env as-is (OFF=1: the graph path every measured Q38FN number used)  [reference]
#         C5DEF = C5 image, GGML_FUSED_DECODE_OFF stripped, ON unset (the new default)                       must be IDENTICAL
#         C5OFF = C5 image, frozen env as-is (OFF=1 back-compat)                                             must be IDENTICAL
#       proves default-off == the graph path; env proof from /proc/<pid>/environ per arm. Any divergence = FAIL (graph code untouched).
#   (s) SMOKE, one quarter: the fused opt-in path still runs (KNOWN DEFECTIVE: FD-DIV-1b / INF-67; NO correctness claim):
#         C5DEF [reference] vs C5ON = C5 image, OFF stripped, GGML_FUSED_DECODE_ON=1; p1,p2, n_predict 32;
#       pass = completes + confirmed dead + ZERO files written under /tmp/qwen4exp-builds during its lifetime (CH-24 runtime half) + fused
#       engagement shown (no refusal line, per-token ms >= 3x the reference); INCONCLUSIVE (rc 5) if engagement is not shown.
# Claims: b takes `region-lock run --cpu-list 0-95 --role bench --gpu-quiet shared` and re-execs ITSELF inside it (slot file required).
#         c,s run inside the caller's claim when FILLER_CPUS is set (filler_run9 --class cpu --role build outer claim; NO second claim),
#         else take `region-lock run --cpu-list ${C5_CS_CPULIST:-72-95} --role build` and re-exec ITSELF inside it.
#         b must run alone; c,s may run together.  Never --apply; own children only; no pkill/pgrep by name.
# usage: bundle_gate_c5.sh --dry-run | --execute [--items b | --items c,s | --items c | --items s] [--lock-timeout-s N]
set -uo pipefail
D=${C5_GATE_DIR:-/mnt/raid0/llm/tmp/c5-fold-prep}
SELF=$(readlink -f -- "${BASH_SOURCE[0]}")
CSHA=c72ec82f5; CBN=cpu-20261024-c72ec82f5-c5; CBUILDNO=10419
G=/mnt/raid0/llm/tmp/fold-allkeeps-20261004          # gate_compare.py lives here (unchanged instrument)
GC=$D/greedy_compare_c5.py                           # greedy_compare.py + per-arm env ops (the original cannot strip OFF)
K=/mnt/raid0/llm/kernels/builds
LOCK=${C5_REGION_LOCK:-/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock}
CHAMP=${C5_CHAMP_IMAGE:-$K/cpu-20261023-dcc853b55-c3}
CAND=$K/$CBN
WATCH=/tmp/qwen4exp-builds
CS_PORT=18763
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/../../coordination/observer_guard.sh"
MODE=""; ITEMS="c,s"; LOCK_TIMEOUT=1800; INSIDE=0; RUN=""; OBSERVE=0
while [ $# -gt 0 ]; do case "$1" in
    --dry-run) MODE=dry; shift;; --execute) MODE=exec; shift;;
    observe) OBSERVE=1; shift;; --observe) OBSERVE=1; shift;;
    --items) ITEMS=$2; shift 2;; --lock-timeout-s) LOCK_TIMEOUT=$2; shift 2;;
    --inside) INSIDE=1; RUN=$2; shift 2;;
    *) sed -n '2,22p' "$0"; exit 64;; esac; done
if [ "$OBSERVE" -eq 1 ]; then og_bundle_observe bundle_gate_c5; exit $?; fi
[ -n "$MODE" ] || { sed -n '2,22p' "$0"; exit 64; }
for _i in ${ITEMS//,/ }; do case $_i in b|c|s) ;; *) echo "REFUSE: item $_i is not part of the C5 gate set (b | c,s)" >&2; exit 64;; esac; done
case ",$ITEMS," in *",b,"*) [ "$ITEMS" = b ] || { echo "REFUSE: item b (whole-host quiet timing) must run alone: --items b" >&2; exit 64; };; esac
say() { echo "[$(date -u +%H:%M:%S)] $*" | tee -a "${RUN:-$D}/bundle_gate.log"; }
has() { case ",$ITEMS," in *",$1,"*) return 0;; esac; return 1; }
ncpus() { /usr/bin/python3 -I -c 'import sys
n=0
for p in sys.argv[1].split(","):
    a,_,b=p.partition("-"); n+=int(b or a)-int(a)+1
print(n)' "$1"; }
CS_CPUS=${FILLER_CPUS:-${C5_CS_CPULIST:-72-95}}
preflight() {
    local bad=0 b
    BUNDLE_OBSERVER_REFUSED=0
    for b in "$CHAMP" "$CAND"; do [ -x "$b/bin/llama-server" ] || { say "REFUSE: no llama-server in $b"; bad=1; }; done
    grep "$CSHA" "$CAND/VERSION.txt" >/dev/null 2>&1 || { say "REFUSE: $CAND VERSION does not name $CSHA"; bad=1; }
    grep 'PASS' "$CAND/LINKAGE.txt" >/dev/null 2>&1 || say "WARN: $CAND LINKAGE.txt has no PASS line"
    [ -e "$D/DONE" ] || { say "REFUSE: $D/DONE absent (the build + gate_c5 row has not passed)"; bad=1; }
    local free; free=$(awk '/MemAvailable/ {printf "%d", $2/1048576}' /proc/meminfo)
    if [ "$ITEMS" = b ]; then
        og_bundle_require_absent bundle_gate_c5 || { say "REFUSE: DS41/Q38FN loop presence is busy or unobservable"; BUNDLE_OBSERVER_REFUSED=1; return 1; }
        for p in 18641 18651 18761; do (exec 3<>"/dev/tcp/127.0.0.1/$p") 2>/dev/null && { say "REFUSE: port $p busy"; bad=1; }; done
        local busy; busy=$(top -bn2 -d 2 | awk '/^%Cpu/ {u=$2+$4} END {printf "%d", u*192}')
        say "host busy ~${busy}% of one CPU (192 threads) over 2 s"; [ "${busy:-0}" -le 1200 ] || { say "REFUSE: host busy ${busy}% > 1200%"; bad=1; }
        say "MemAvailable ${free} GiB (Q38FN --no-mmap ~88 GiB, one server at a time)"; [ "$free" -ge 200 ] || { say "REFUSE: < 200 GiB available"; bad=1; }
    else
        (exec 3<>"/dev/tcp/127.0.0.1/$CS_PORT") 2>/dev/null && { say "REFUSE: port $CS_PORT busy"; bad=1; }
        say "MemAvailable ${free} GiB (Q38FN --no-mmap ~88 GiB, one server at a time)"; [ "$free" -ge 120 ] || { say "REFUSE: < 120 GiB available"; bad=1; }
        say "c,s pinning: cpus=$CS_CPUS threads=$(ncpus "$CS_CPUS") (same rewrite on every arm)"
        if has s; then [ -d "$WATCH" ] && [ -w "$WATCH" ] || { say "REFUSE: $WATCH is not an existing writable dir; the CH-24 runtime watch would be vacuous"; bad=1; }; fi
    fi
    return $bad
}
# BEGIN BUNDLE GATE VERDICT
bundle_gate_verdict_rc() {
    local child_rc=$1 result=$2 mode=$3
    if [ "$child_rc" -ne 0 ] && ! { [ "$mode" = smoke ] && [ "$child_rc" -eq 5 ]; }; then
        return "$child_rc"
    fi
    /usr/bin/python3 -I - "$result" "$mode" "$child_rc" 2>/dev/null <<'PY'
import json
import math
import sys

def unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON key")
        value[key] = item
    return value

def reject_constant(value):
    raise ValueError("non-JSON constant")

def finite_number(value):
    return type(value) in (int, float) and math.isfinite(value)

def finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("nonfinite JSON number")
    return number

try:
    with open(sys.argv[1], encoding="utf-8") as stream:
        document = json.load(stream, object_pairs_hook=unique_object, parse_constant=reject_constant, parse_float=finite_float)
    mode = sys.argv[2]
    child_rc = int(sys.argv[3])
    valid = False
    result_rc = 1

    if type(document) is dict and mode == "gate_compare":
        comparison = document.get("comparison")
        valid = (
            document.get("schema") == "epyc.fold.gate_compare.v1"
            and document.get("surface") == "q38fn"
            and "verdict" not in document
            and type(comparison) is dict
            and "verdict" not in comparison
            and comparison.get("schema") == "epyc.autokernel.serving_ab.v2"
            and comparison.get("metric") == "aggregate_tok_s"
            and comparison.get("pairs") == 5
            and comparison.get("decisive", object()) is None
            and comparison.get("noise_floor_pct", object()) is None
            and comparison.get("floor_unit", object()) is None
            and type(comparison.get("anchor_samples")) is list
            and len(comparison["anchor_samples"]) == 5
            and type(comparison.get("candidate_samples")) is list
            and len(comparison["candidate_samples"]) == 5
            and all(finite_number(x) and x > 0 for x in comparison["anchor_samples"])
            and all(finite_number(x) and x > 0 for x in comparison["candidate_samples"])
            and finite_number(comparison.get("anchor_tok_s")) and comparison["anchor_tok_s"] > 0
            and finite_number(comparison.get("candidate_tok_s")) and comparison["candidate_tok_s"] > 0
            and finite_number(comparison.get("effect_pct"))
        )
        result_rc = 0 if valid and child_rc == 0 else 1

    elif type(document) is dict and mode in ("identity", "smoke"):
        results = document.get("results")
        expected_arms = ["CHAMP", "C5DEF", "C5OFF"] if mode == "identity" else ["C5DEF", "C5ON"]
        prompts = {"p1", "p2", "p3"} if mode == "identity" else {"p1", "p2"}
        results_ok = (
            document.get("schema") == "epyc.fold.greedy_compare_c5.v1"
            and "verdict" not in document
            and type(results) is list
            and [r.get("arm") for r in results if type(r) is dict] == expected_arms
            and len(results) == len(expected_arms)
            and all(r.get("completed") is True and r.get("confirmed_dead") is True and "error" not in r
                    for r in results if type(r) is dict)
            and all(type(r.get("prompts")) is dict and set(r["prompts"]) == prompts
                    and all(type(p) is dict and type(p.get("tokens")) is list and p["tokens"]
                            and all(type(token) is int for token in p["tokens"])
                            for p in r["prompts"].values()) for r in results)
        )
        if mode == "identity":
            verdict = document.get("verdict_vs_CHAMP")
            identity = document.get("identity")
            arms = ("C5DEF", "C5OFF")
            verdict_ok = (type(verdict) is dict and type(identity) is dict
                          and set(identity) == set(arms)
                          and all(identity.get(arm) is True for arm in arms)
                          and set(verdict) == set(arms)
                          and all(type(verdict[arm]) is dict
                                  and set(verdict[arm]) == {"p1", "p2", "p3"}
                                  and all(verdict[arm][prompt] == "IDENTICAL"
                                          for prompt in ("p1", "p2", "p3"))
                                  for arm in arms))
            tokens_ok = results_ok and all(r["prompts"][p]["tokens"] == results[0]["prompts"][p]["tokens"]
                                          for r in results[1:] for p in prompts)
            valid = results_ok and verdict_ok and tokens_ok and document.get("smoke", object()) is None and child_rc == 0
            result_rc = 0 if valid else (child_rc if child_rc not in (0, 5) else 1)
        else:
            smoke = document.get("smoke")
            smoke_arm = next((r for r in results if type(r) is dict and r.get("arm") == "C5ON"), {}) if type(results) is list else {}
            smoke_common = (type(smoke) is dict and smoke.get("arm") == "C5ON"
                            and smoke.get("completed") is True
                            and smoke.get("confirmed_dead") is True
                            and smoke.get("tmp_new_files") == []
                            and smoke_arm.get("tmp_new_files") == []
                            and smoke_arm.get("refusal_logged") is smoke.get("refusal_logged")
                            and document.get("identity") == {})
            ratio = smoke.get("ratio") if type(smoke) is dict else None
            refusal = smoke.get("refusal_logged") if type(smoke) is dict else None
            # Preserve the producer's existing >=3 engagement rule; no new timing bar.
            engagement_ok = (type(refusal) is bool and
                             (ratio is None or finite_number(ratio) and ratio > 0))
            expected_engaged = not refusal and ratio is not None and ratio >= 3 if engagement_ok else None
            if smoke_common and smoke.get("verdict") == "PASS":
                valid = (results_ok and engagement_ok and child_rc == 0
                         and smoke.get("refusal_logged") is False
                         and smoke.get("engaged") is True
                         and finite_number(smoke.get("ratio"))
                         and smoke["ratio"] >= 3)
                result_rc = 0 if valid else 1
            elif smoke_common and smoke.get("verdict") == "INCONCLUSIVE":
                valid = (results_ok and engagement_ok and expected_engaged is False and smoke.get("engaged") is False
                         and child_rc in (0, 5))
                result_rc = 5 if valid else 1
            else:
                valid = False
                result_rc = child_rc if child_rc not in (0, 5) else 1
except Exception:
    valid = False
    result_rc = 1

sys.exit(result_rc)
PY
}
# END BUNDLE GATE VERDICT
steps() {
    local flag=--dry-run; [ "$1" = exec ] && flag=--execute
    local rc=0 out=${RUN:-$D/dry} t child_rc gate_rc; t=$(ncpus "$CS_CPUS")
    has b && { say "(b) Q38FN C5 vs champion $(basename "$CHAMP"), 5 matched pairs (frozen env, OFF=1 both arms; sign claim)"; python3 "$G/gate_compare.py" q38fn --anchor-build "$CHAMP" --cand-build "$CAND" --pairs 5 --out "$out/b" $flag 2>&1 | tee -a "$out/bundle_gate.log" | grep -E 'floor|admission|DRY|RESULT|REFUSED|Error'; child_rc=${PIPESTATUS[0]}; if [ "$flag" = --dry-run ]; then gate_rc=$child_rc; else bundle_gate_verdict_rc "$child_rc" "$out/b/compare-q38fn.json" gate_compare; gate_rc=$?; fi; rc=$((rc|gate_rc)); }
    has c && { say "(c) Q38FN greedy identity, DEFAULT env: CHAMP(OFF=1) vs C5DEF(no knob) and C5OFF(OFF=1)"
        /usr/bin/python3 -I "$GC" --arm CHAMP="$CHAMP" --arm C5DEF="$CAND@-GGML_FUSED_DECODE_OFF" --arm C5OFF="$CAND" \
            --expect-identical C5DEF,C5OFF --cpus "$CS_CPUS" --threads "$t" --port $CS_PORT --out "$out/c" $flag 2>&1 \
            | tee -a "$out/bundle_gate.log" | grep -E 'DRY|vs CHAMP|IDENTITY|REFUSED|DID NOT|Error'; child_rc=${PIPESTATUS[0]}; if [ "$flag" = --dry-run ]; then gate_rc=$child_rc; else bundle_gate_verdict_rc "$child_rc" "$out/c/greedy.json" identity; gate_rc=$?; fi; rc=$((rc|gate_rc)); }
    has s && { say "(s) fused opt-in smoke (KNOWN DEFECTIVE, no correctness claim): C5DEF vs C5ON(GGML_FUSED_DECODE_ON=1), p1,p2 x 32 tokens, watch $WATCH"
        /usr/bin/python3 -I "$GC" --arm C5DEF="$CAND@-GGML_FUSED_DECODE_OFF" --arm C5ON="$CAND@-GGML_FUSED_DECODE_OFF,GGML_FUSED_DECODE_ON=1" \
            --label "C5ON=KNOWN-DEFECTIVE fused path (FD-DIV-1b, INF-67): no correctness claim" --smoke-arm C5ON --tmp-watch "$WATCH" \
            --prompts p1,p2 --n-predict 32 --cpus "$CS_CPUS" --threads "$t" --port $CS_PORT --out "$out/s" $flag 2>&1 \
            | tee -a "$out/bundle_gate.log" | grep -E 'DRY|vs C5DEF|SMOKE|REFUSED|DID NOT|Error'; child_rc=${PIPESTATUS[0]}; if [ "$flag" = --dry-run ]; then gate_rc=$child_rc; else bundle_gate_verdict_rc "$child_rc" "$out/s/greedy.json" smoke; gate_rc=$?; fi; rc=$((rc|gate_rc)); }
    return $rc
}
window_guard() {
    local f="$D/slots/$ITEMS.slot" s e now
    [ -r "$f" ] || { echo "REFUSE: no slot file $f (the job wrapper writes START/END ISO-Z from the grant)" >&2; return 3; }
    s=$(date -u -d "$(sed -n 1p "$f")" +%s) && e=$(date -u -d "$(sed -n 2p "$f")" +%s) || { echo "REFUSE: bad slot file" >&2; return 3; }
    now=$(date -u +%s)
    [ "$now" -ge "$s" ] && [ "$now" -le $((e-300)) ] || { echo "REFUSE: now $(date -u +%T) outside slot $(sed -n 1p "$f") .. $(sed -n 2p "$f") (-5 min)" >&2; return 3; }
    [ $((e-300-now)) -ge "${C5_MIN_LEFT_S:-0}" ] || { echo "REFUSE: only $((e-300-now)) s left in slot, need ${C5_MIN_LEFT_S} s (hard stop $(sed -n 2p "$f"))" >&2; return 3; }
}
if [ "$MODE" = exec ] || [ "$INSIDE" = 1 ]; then window_guard || exit 3; fi
if [ "$INSIDE" = 1 ]; then
    mkdir -p "$RUN"; say "inside claim: items=$ITEMS run=$RUN champ=$CHAMP cand=$CAND"
    preflight || { say "REFUSED by preflight -- nothing launched"; exit 3; }
    steps exec; rc=$?; say "done rc=$rc"; exit $rc
fi
if [ "$MODE" = dry ]; then
    mkdir -p "$D/dry"; : > "$D/dry/bundle_gate.log"
    say "DRY RUN items=$ITEMS (no claim taken, nothing launched)"
    preflight; p=$?; say "preflight (outside the claim, informational) rc=$p"
    [ "${BUNDLE_OBSERVER_REFUSED:-0}" -eq 0 ] || { say "REFUSED by observer preflight -- no child invoked"; exit 3; }
    steps dry; rc=$?; say "dry-run steps rc=$rc"; exit $rc
fi
TS=$(date -u +%Y%m%dT%H%M%SZ)
if [ "$ITEMS" != b ] && [ -n "${FILLER_CPUS:-}" ]; then
    # already inside the filler's own build-role claim over FILLER_CPUS: a second claim on the same CPUs would self-deadlock
    exec /bin/bash "$SELF" --execute --items "$ITEMS" --inside "$D/runs/$TS"
fi
if [ "$ITEMS" = b ]; then
    exec "$LOCK" run --cpu-list 0-95 --role bench --gpu-quiet shared --timeout-s "$LOCK_TIMEOUT" --tag c5-bundle-gate-b -- \
        /bin/bash "$SELF" --execute --items "$ITEMS" --inside "$D/runs/$TS"
fi
exec "$LOCK" run --cpu-list "$CS_CPUS" --role build --timeout-s "$LOCK_TIMEOUT" --tag c5-bundle-gate-cs -- \
    /bin/bash "$SELF" --execute --items "$ITEMS" --inside "$D/runs/$TS"
