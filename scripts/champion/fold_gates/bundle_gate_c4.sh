#!/bin/bash
# bundle_gate_c4.sh -- C4 re-gate (items c,e), derived from c2-regate-20261021/bundle_gate_c2.sh by exact-string substitution: C4 = experimental/champion-c4-20261024 @ cdb4d8c77 vs champion dcc853b55 [C3]. NOT RUN (prep, 2026-10-24).
# bundle_gate_c4.sh -- C4 re-gate (items c,e), derived from c2-regate-20261021/bundle_gate_c2.sh by exact-string substitution: C4 = experimental/champion-c4-20261024 @ cdb4d8c77 vs champion dcc853b55 [C3]. NOT RUN (prep, 2026-10-24).
# Items for C2: b (Q38FN C2 vs champion, 5 pairs, QUIET TIMING, ~5 min), c (Q38FN greedy identity champion/C2, correctness, ~5 min), e (GPU 27B A/B, ALONE, ~26 min).
# Item a (DS41 Sept-Q4 gate) and d are NOT part of the C2 re-gate: a is superseded by the 1017 gate; d does not involve C2 (carried over).
# WINDOW GUARD: --execute refuses unless $D/slots/<items>.slot exists (written by main after 5c grants the slot): line1=START ISO-Z, line2=END ISO-Z;
# now must be inside [START, END-300s]. No slot file, no run. Dry-run needs none.
# bundle_gate.sh -- CPU serving bundle gate for champion-consolidation candidate C vs the current champion dd3d9721c.
# RUN ONLY AFTER 06:30Z (the host is exclusive to the operator session until then). Adapted from
# /mnt/raid0/llm/tmp/fold-allkeeps-20261004/gates_5g.sh (the Y/Yfa/Z bundle-gate recipe): same instruments, unchanged.
#   (a) DS41 serving gate  C vs champion dd3d9721c, 5 pairs, matched_process_v2, the AK loop's own floor selector
#       (gate_compare.py: serving.compare as run.py calls it; DS41 floor lineage 3.412% process unit / 4.533% as recorded for Y/Z)
#   (b) Q38FN serving gate C vs champion, 5 pairs (NO calibrated floor: sign claim only, decisive=None by construction)
#   (c) greedy identity champion / C on the frozen Q38FN prompts (greedy_compare.py, own-pid server per arm)
#   (d) the bundle gate the ten unledgered post-Y AK keeps never had: DS41 + Q38FN champion dd3d9721c vs b0ba1d427 (5 pairs each)
#       and greedy identity b0ba1d427 / dd3d9721c (V11-033..042 ledger entry needs this)
# Rules carried from the ledger: a delta inside the floor is "not decisive", not a pass/fail; NEVER --apply (nothing here writes a
# campaign store, bundle, champion of record or ref); own children only, no pkill/pgrep by name.
# Claim: the whole run sits inside ONE claim taken before any load preflight:
#   region-lock run --cpu-list 0-95 --role bench --gpu-quiet shared
#   (e) OPT-IN, GPU: paired 27B DFlash2 serving A/B, champion dd3d9721c (P) vs C (C), via the RESTORED ab_probe harness
#       (epyc-inference-research scripts/benchmark/gpu_champion_ab.sh -> ab_arms.sh + ab_probe.py, committed byte-exact 2026-10-20):
#       15 P C pairs on :8197, identity C==P, SW-9 probs, pp/tg vs the P-vs-P noise floor. Needs the GPU EXCLUSIVE, so it runs
#       ALONE (--items e) under its own claim (--gpu-quiet exclusive); mixing e with a-d is refused.
# usage: bundle_gate.sh --dry-run | --execute [--items a,b,c | --items e] [--lock-timeout-s N]
set -uo pipefail
D=${C4_GATE_DIR:-/mnt/raid0/llm/tmp/c4-fold-prep}
SELF=$(readlink -f -- "${BASH_SOURCE[0]}")
SRC=/mnt/raid0/llm/tmp/champ-consolidation-20261020   # server_args.27b-dflash2-20261004.bin lives here
CSHA=cdb4d8c77; CBN=cpu-20261024-cdb4d8c77-c4; GBN=gpu-20261024-cdb4d8c77-c4; CBUILDNO=10417   # verify CBUILDNO against the C4 llama-server --version
G=/mnt/raid0/llm/tmp/fold-allkeeps-20261004          # gate_compare.py / greedy_compare.py live here (unchanged instruments)
K=/mnt/raid0/llm/kernels/builds
LOCK=${C4_REGION_LOCK:-/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock}
CHAMP=$K/cpu-20261023-dcc853b55-c3
CAND=$K/$CBN
GAB=/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/gpu_champion_ab.sh   # committed in research main (3c428ac00)
[ -x "$GAB" ] || GAB=/mnt/raid0/llm/worktrees/research-ab-probe-restore/scripts/benchmark/gpu_champion_ab.sh   # until the shared clone fast-forwards
CHAMP_GPU=$K/gpu-20261023-dcc853b55-c3; CAND_GPU=$K/$GBN
B0=$K/cpu-20261004-b0ba1d427   # last LEDGERED champion (W fold); dd3d9721c carries ten unledgered AK keeps past it
COR_A=/mnt/raid0/llm/autokernel/campaigns/ak-ds41-cpu-decode-20260923/store/anchor-gen-007
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/../../coordination/observer_guard.sh"
MODE=""; ITEMS="b,c"; LOCK_TIMEOUT=1800; INSIDE=0; RUN=""; OBSERVE=0
while [ $# -gt 0 ]; do case "$1" in
    --dry-run) MODE=dry; shift;; --execute) MODE=exec; shift;;
    observe) OBSERVE=1; shift;; --observe) OBSERVE=1; shift;;
    --items) ITEMS=$2; shift 2;; --lock-timeout-s) LOCK_TIMEOUT=$2; shift 2;;
    --inside) INSIDE=1; RUN=$2; shift 2;;
    *) sed -n '2,12p' "$0"; exit 64;; esac; done
if [ "$OBSERVE" -eq 1 ]; then og_bundle_observe bundle_gate_c4; exit $?; fi
[ -n "$MODE" ] || { sed -n '2,12p' "$0"; exit 64; }
say() { echo "[$(date -u +%H:%M:%S)] $*" | tee -a "${RUN:-$D}/bundle_gate.log"; }
has() { case ",$ITEMS," in *",$1,"*) return 0;; esac; return 1; }
preflight() {
    local bad=0 b
    BUNDLE_OBSERVER_REFUSED=0
    for b in "$CHAMP" "$CAND"; do [ -x "$b/bin/llama-server" ] || { say "REFUSE: no llama-server in $b"; bad=1; }; done
    grep -q "@CANDSHA""@" "$0" && { say "REFUSE: candidate sha placeholder not filled"; bad=1; }
    grep -q "$CSHA" "$CAND/VERSION.txt" 2>/dev/null || { say "REFUSE: $CAND VERSION does not name its sha"; bad=1; }
    grep -q 'PASS' "$CAND/LINKAGE.txt" 2>/dev/null || say "WARN: $CAND LINKAGE.txt has no PASS line"
    og_bundle_require_absent bundle_gate_c4 || { say "REFUSE: DS41/Q38FN loop presence is busy or unobservable"; BUNDLE_OBSERVER_REFUSED=1; return 1; }
    for p in 18641 18651 18761; do (exec 3<>"/dev/tcp/127.0.0.1/$p") 2>/dev/null && { say "REFUSE: port $p busy"; bad=1; }; done
    local busy; busy=$(top -bn2 -d 2 | awk '/^%Cpu/ {u=$2+$4} END {printf "%d", u*192}')
    local free; free=$(awk '/MemAvailable/ {printf "%d", $2/1048576}' /proc/meminfo)
    if [ "$ITEMS" = e ]; then
        # 3c4ca599 2026-10-24: item e is the GPU 27B A/B on its own 8 host threads (72-79) under --gpu-quiet exclusive; the whole-host
        # CPU-quiet check below belongs to the CPU server items (b timing, c greedy on 0-95) and is not its guard. ab_arms.sh runs its
        # own window-watch on its cpuset; e still needs host RAM for the 27B arms (~34 GiB) plus headroom.
        say "host busy ~${busy}% (informational for item e; CPU-quiet is not an item-e guard)"
        say "MemAvailable ${free} GiB (item e needs ~34 + headroom)"; [ "$free" -ge 64 ] || { say "REFUSE: < 64 GiB available"; bad=1; }
    else
        say "host busy ~${busy}% of one CPU (192 threads) over 2 s"; [ "${busy:-0}" -le 1200 ] || { say "REFUSE: host busy ${busy}% > 1200%"; bad=1; }
        say "MemAvailable ${free} GiB (DS41 --no-mmap needs ~540)"; [ "$free" -ge 600 ] || { say "REFUSE: < 600 GiB available"; bad=1; }
    fi
    return $bad
}
# BEGIN BUNDLE GATE VERDICT
bundle_gate_verdict_rc() {
    local child_rc=$1 result=$2 mode=$3
    [ "$child_rc" -eq 0 ] || return "$child_rc"
    /usr/bin/python3 -I - "$result" "$mode" 2>/dev/null <<'PY'
import json
import sys

def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result

def reject_constant(value):
    raise ValueError("non-JSON constant")

try:
    with open(sys.argv[1], encoding="utf-8") as stream:
        document = json.load(stream, object_pairs_hook=unique_object, parse_constant=reject_constant)
    mode = sys.argv[2]
    valid = False
    if type(document) is dict:
        if mode == "mtp":
            verdict = document.get("verdict")
            valid = (document.get("schema") == "epyc.gpu_champion_ab.result.v1"
                     and document.get("kind") == "mtp"
                     and type(verdict) is dict
                     and type(verdict.get("PASS")) is bool
                     and verdict["PASS"] is True)
        elif mode == "greedy":
            results = document.get("results")
            verdicts = document.get("verdict_vs_CHAMP")
            candidate = verdicts.get("C") if type(verdicts) is dict else None
            valid = (type(results) is list and len(results) == 2
                     and all(type(r) is dict for r in results)
                     and [r.get("arm") for r in results] == ["CHAMP", "C"]
                     and all(r.get("completed") is True and r.get("confirmed_dead") is True for r in results)
                     and type(verdicts) is dict and set(verdicts) == {"C"}
                     and type(candidate) is dict and set(candidate) == {"p1", "p2", "p3"}
                     and all(type(candidate[p]) is str and candidate[p] == "IDENTICAL"
                             for p in ("p1", "p2", "p3")))
except (OSError, TypeError, ValueError):
    valid = False
sys.exit(0 if valid else 1)
PY
}
# END BUNDLE GATE VERDICT
steps() {
    local flag=--dry-run; [ "$1" = exec ] && flag=--execute
    local rc=0 out=${RUN:-$D/dry}
    has a && { say "(a) (RETIRED for C2: DS41 runs as the 1017 gate, not here) DS41 C2 vs champion, 5 pairs"; python3 "$G/gate_compare.py" ds41 --anchor-build "$CHAMP" --cand-build "$CAND" --pairs 5 --out "$out/a" $flag 2>&1 | tee -a "$out/bundle_gate.log" | grep -E 'floor|admission|DRY|RESULT|REFUSED|Error'; rc=$((rc|PIPESTATUS[0])); }
    has b && { say "(b) Q38FN C vs champion, 5 pairs"; python3 "$G/gate_compare.py" q38fn --anchor-build "$CHAMP" --cand-build "$CAND" --pairs 5 --out "$out/b" $flag 2>&1 | tee -a "$out/bundle_gate.log" | grep -E 'floor|admission|DRY|RESULT|REFUSED|Error'; rc=$((rc|PIPESTATUS[0])); }
    has c && { say "(c) Q38FN greedy identity champion / C"; python3 "$G/greedy_compare.py" --arm CHAMP="$CHAMP" --arm C="$CAND" --out "$out/c" $flag 2>&1 | tee -a "$out/bundle_gate.log" | grep -E 'DRY|vs CHAMP|REFUSED|Error'
        local greedy_rc=${PIPESTATUS[0]} verdict_rc
        if [ "$flag" = --execute ]; then
            bundle_gate_verdict_rc "$greedy_rc" "$out/c/greedy.json" greedy; verdict_rc=$?
            [ "$verdict_rc" -eq 0 ] || say "FAIL: item c did not produce complete CHAMP/C results with p1,p2,p3 IDENTICAL"
        else verdict_rc=$greedy_rc; fi
        rc=$((rc|verdict_rc))
    }
    has d && {
        [ -x "$B0/bin/llama-server" ] || say "WARN: no $B0 build for item d"
        say "(d1) DS41 champion dd3d9721c vs b0ba1d427 (ten unledgered keeps), 5 pairs"; python3 "$G/gate_compare.py" ds41 --anchor-build "$B0" --cand-build "$CHAMP" --pairs 5 --out "$out/d1" $flag 2>&1 | tee -a "$out/bundle_gate.log" | grep -E 'floor|admission|DRY|RESULT|REFUSED|Error'; rc=$((rc|PIPESTATUS[0]))
        say "(d2) Q38FN champion dd3d9721c vs b0ba1d427, 5 pairs"; python3 "$G/gate_compare.py" q38fn --anchor-build "$B0" --cand-build "$CHAMP" --pairs 5 --out "$out/d2" $flag 2>&1 | tee -a "$out/bundle_gate.log" | grep -E 'floor|admission|DRY|RESULT|REFUSED|Error'; rc=$((rc|PIPESTATUS[0]))
        say "(d3) Q38FN greedy identity b0ba1d427 / dd3d9721c"; python3 "$G/greedy_compare.py" --arm B0="$B0" --arm CHAMP="$CHAMP" --out "$out/d3" $flag 2>&1 | tee -a "$out/bundle_gate.log" | grep -E 'DRY|vs B0|REFUSED|Error'; rc=$((rc|PIPESTATUS[0]))
    }
    has e && {
        local pn=10413 cn=$CBUILDNO   # C4 cdb4d8c77 = 10417 (verify); champion C3 dcc853b55 = 10413
        say "(e) GPU 27B DFlash2 serving A/B, champion dcc853b55 [C3] (P) vs C4, 15 pairs, ab_probe harness"
        local abflag=--dry-run; [ "$1" = exec ] && abflag=--execute
        # argv: the live :8083 server's when it is up (gpu_champion_ab derives it), else the 2026-10-04 receipt's DFlash2 argv (copied from
        # epyc-root artifacts/champion-fold-kvu19-20261004/receipt-ab/champion-only-*/server_args.bin)
        local argsopt=(); [ -n "$(ss -ltnH '( sport = :8083 )' 2>/dev/null)" ] || argsopt=(--args-file "$SRC/server_args.27b-dflash2-20261004.bin")
        say "(e) argv source: ${argsopt[*]:-live :8083}"
        AB_INSIDE_CLAIM=1 "$GAB" "${argsopt[@]}" --p-build "$CHAMP_GPU" --p-tip dcc853b55 --p-buildno $pn --c-build "$CAND_GPU" --c-tip $CSHA --c-buildno $cn \
            --run "$out/e" --pairs 15 $abflag 2>&1 | tee -a "$out/bundle_gate.log" | grep -E 'RESULT|REFUSE|ERROR|WARNING|sequence|arm [PC]:|dry-run\] summarize'
        local ab_rc=${PIPESTATUS[0]} verdict_rc
        if [ "$abflag" = --execute ]; then
            bundle_gate_verdict_rc "$ab_rc" "$out/e/result.json" mtp; verdict_rc=$?
            [ "$verdict_rc" -eq 0 ] || say "FAIL: GPU item e did not produce child rc 0 plus explicit PASS=true"
        else verdict_rc=$ab_rc; fi
        rc=$((rc|verdict_rc))
    }
    return $rc
}
for _i in ${ITEMS//,/ }; do case $_i in c|e) ;; *) echo "REFUSE: item $_i is not part of the C4 re-gate (c,e only; b timing is not needed, no CPU code changes)" >&2; exit 64;; esac; done

window_guard() {
    local f="$D/slots/$ITEMS.slot" s e now
    [ -r "$f" ] || { echo "REFUSE: no slot file $f (main writes START/END ISO-Z after 5c grants the slot)" >&2; return 3; }
    s=$(date -u -d "$(sed -n 1p "$f")" +%s) && e=$(date -u -d "$(sed -n 2p "$f")" +%s) || { echo "REFUSE: bad slot file" >&2; return 3; }
    now=$(date -u +%s)
    [ "$now" -ge "$s" ] && [ "$now" -le $((e-300)) ] || { echo "REFUSE: now $(date -u +%T) outside slot $(sed -n 1p "$f") .. $(sed -n 2p "$f") (-5 min)" >&2; return 3; }
    [ $((e-300-now)) -ge "${C2_MIN_LEFT_S:-0}" ] || { echo "REFUSE: only $((e-300-now)) s left in slot, need ${C2_MIN_LEFT_S} s (hard stop $(sed -n 2p "$f"))" >&2; return 3; }
}
case ",$ITEMS," in *",e,"*) [ "$ITEMS" = e ] || { echo "REFUSE: item e (GPU exclusive) must run alone: --items e" >&2; exit 64; };; esac
if [ "$MODE" = exec ] || [ "$INSIDE" = 1 ]; then window_guard || exit 3; fi
if [ "$INSIDE" = 1 ]; then
    mkdir -p "$RUN"; say "inside claim: items=$ITEMS run=$RUN"
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
GPUQ=shared; CPUL=0-95; [ "$ITEMS" = e ] && { GPUQ=exclusive; CPUL=${C2_E_CPULIST:-72-79}; }   # e: the probe only needs its 8 host threads (72-79, membind 3); CPU timing stays free for others
exec "$LOCK" run --cpu-list "$CPUL" --role bench --gpu-quiet "$GPUQ" --timeout-s "$LOCK_TIMEOUT" --tag c4-regate-bundle-gate -- \
    /bin/bash "$SELF" --execute --items "$ITEMS" --inside "$D/runs/$TS"
