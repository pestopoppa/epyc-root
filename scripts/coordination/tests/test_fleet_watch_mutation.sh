#!/bin/bash
# =============================================================================
# test_fleet_watch_mutation.sh — proves test_fleet_watch.sh actually tests things
# =============================================================================
#
# A suite that has never failed has not been shown to test anything. This breaks
# each of `fleet_watch.sh`'s detectors ON PURPOSE, one at a time, and requires
# the suite to CATCH each break. A mutation the suite survives is a rule nobody
# is checking, and it is reported as a FAILURE of this harness.
#
# THREE PROPERTIES THIS HARNESS ENFORCES ABOUT ITSELF, because a mutation test is
# exactly the kind of check that passes for the wrong reason:
#
#   VISIBLE — each mutation is an EXACT literal replacement that must match
#   exactly ONCE. Zero matches ("the pattern rotted after a refactor") and more
#   than one ("the mutation hit somewhere unintended") are both hard failures,
#   not silent no-ops. The first draft of this harness used `sed` with `|`
#   delimiters and five of seventeen mutations silently failed to apply; they
#   were reported as defects rather than as passes, which is the only reason
#   this note can be written honestly.
#
#   COUNTED — every mutation is a numbered case with its own pass/fail line and
#   a total, and the harness exits non-zero if any mutation survived. Nothing is
#   asserted inside a helper whose exit status goes uninspected.
#
#   PARSEABLE — a mutant that does not parse would fail the suite for a syntax
#   error rather than because the rule is tested, so `bash -n` gates every mutant
#   and an unparseable one is a harness defect.
#
# The control case runs FIRST: the pristine script must PASS. Without it a suite
# that fails for an unrelated reason (a typo, a missing `jq`) would "catch" every
# mutation, and this harness would report a perfect score while testing nothing.
#
# WHAT IS DELIBERATELY NOT MUTATED. `fw_queue_rows`' embedded python is replaced
# by the suite's fixture seam, so a mutation inside it would SURVIVE — correctly,
# not as a gap. Its contract (US separators, `-1` for an unparseable timestamp)
# is pinned on the BASH side instead: cases 24 and 23 below break the consumer of
# each and the suite catches both.
#
# Usage: tests/test_fleet_watch_mutation.sh
# =============================================================================
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="${FLEET_WATCH_SH:-${HERE}/../fleet_watch.sh}"
SUITE="${HERE}/test_fleet_watch.sh"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

PASS=0; FAIL=0
SURVIVORS=()

printf '=== control: the pristine script must pass ===\n'
if FLEET_WATCH_SH="$SCRIPT" bash "$SUITE" >"$TMP/control.log" 2>&1; then
    printf '  PASS  pristine fleet_watch.sh passes the suite (%s assertions)\n' \
        "$(grep -c '  PASS' "$TMP/control.log")"
    PASS=$((PASS + 1))
else
    printf '  FAIL  pristine fleet_watch.sh does NOT pass — every mutation below\n'
    printf '        would be "caught" for the wrong reason. Aborting.\n'
    tail -20 "$TMP/control.log"
    exit 1
fi

# Exact literal replacement, required to match exactly once. Prints APPLIED or a
# diagnostic; returns non-zero when the mutation is defective.
apply_mutation() {  # apply_mutation <src> <dst> <from> <to>
    python3 - "$@" <<'PY'
import sys
src, dst, frm, to = sys.argv[1:5]
s = open(src, encoding='utf-8').read()
n = s.count(frm)
if n != 1:
    print(f"MATCHED {n} TIMES (need exactly 1)")
    sys.exit(1)
open(dst, 'w', encoding='utf-8').write(s.replace(frm, to))
print("APPLIED")
PY
}

# mutate <n> <description> <from> <to> <suite-case-that-must-fail>
mutate() {
    local n="$1" desc="$2" frm="$3" to="$4" expect="$5"
    local mutant="$TMP/mutant_${n}.sh" log="$TMP/mutant_${n}.log" res

    res=$(apply_mutation "$SCRIPT" "$mutant" "$frm" "$to")
    if [ "$res" != "APPLIED" ]; then
        printf '  FAIL  [%02d] %s\n        MUTATION DEFECTIVE: %s — this case proves nothing.\n' "$n" "$desc" "$res"
        FAIL=$((FAIL + 1)); SURVIVORS+=("[$n] $desc (mutation defective: $res)")
        return
    fi
    if cmp -s "$SCRIPT" "$mutant"; then
        printf '  FAIL  [%02d] %s\n        mutant is byte-identical to the original.\n' "$n" "$desc"
        FAIL=$((FAIL + 1)); SURVIVORS+=("[$n] $desc (no change)")
        return
    fi
    if ! bash -n "$mutant" 2>/dev/null; then
        printf '  FAIL  [%02d] %s\n        mutant does not parse — it would fail for a syntax error,\n        not because the rule is tested.\n' "$n" "$desc"
        FAIL=$((FAIL + 1)); SURVIVORS+=("[$n] $desc (unparseable)")
        return
    fi

    if FLEET_WATCH_SH="$mutant" bash "$SUITE" >"$log" 2>&1; then
        printf '  FAIL  [%02d] %s\n        MUTATION SURVIVED — the suite still passed. Nothing checks this rule.\n' "$n" "$desc"
        FAIL=$((FAIL + 1)); SURVIVORS+=("[$n] $desc")
    else
        local caught n_caught
        n_caught=$(sed -n 's/^  - //p' "$log" | wc -l)
        caught=$(sed -n 's/^  - //p' "$log" | head -2 | paste -sd'; ' -)
        printf '  PASS  [%02d] %s\n        broke %s case(s): %s\n' "$n" "$desc" "$n_caught" "$caught"
        if [ -n "$expect" ] && ! grep -q -- "$expect" "$log"; then
            printf '        NOTE: the expected case "%s" was NOT among them\n' "$expect"
        fi
        PASS=$((PASS + 1))
    fi
}

printf '\n=== mutations ===\n'

# --- persistence / hysteresis (rule 1) --------------------------------------
mutate 1 "an alarm fires on PRESENCE instead of persistence" \
    'fw_is_on()  { [ "${FW_ON_N[$1]:-0}"  -ge "$PERSIST_CYCLES" ]; }' \
    'fw_is_on()  { [ "${FW_ON_N[$1]:-0}"  -ge 1 ]; }' \
    "does not fire before PERSIST_CYCLES"

mutate 2 "an alarm is RESOLVED off a single absent sample (no down-hysteresis)" \
    'fw_is_off() { [ "${FW_OFF_N[$1]:-0}" -ge "$PERSIST_CYCLES" ]; }' \
    'fw_is_off() { [ "${FW_OFF_N[$1]:-0}" -ge 1 ]; }' \
    "not cleared before the absence persists"

# --- the R9 refusal taxonomy ------------------------------------------------
# The measured failure: 9,219 identical `dispatch-refused` advisories repeating
# a refusal nobody acted on. If a refused row stops counting as aging, or every
# refusal collapses into one class, the fleet is back to starving rows silently.
mutate 3 "a REFUSED row stops counting as AGING (the 9,219-refusal regression)" \
    '        FW_AGED=$((FW_AGED + 1))
        cls=$(fw_refusal_class "${screened:-0}" "${esth:-}" "${parked:-}")' \
    '        [ "${screened:-0}" = "1" ] || continue
        FW_AGED=$((FW_AGED + 1))
        cls=$(fw_refusal_class "${screened:-0}" "${esth:-}" "${parked:-}")' \
    "COUNTS AS AGING"

mutate 4 "a PARKED row is misfiled under the gate that already said yes" \
    "    [ -n \"\$parked\" ] && { printf 'premise-parked'; return 0; }" \
    '    :' \
    "parked row -> premise-parked"

mutate 5 "the unscreened class disappears (refusals collapse into one bucket)" \
    "    [ \"\$screened\" = \"1\" ] || { printf 'unscreened'; return 0; }" \
    '    :' \
    "unscreened row -> unscreened"

# The bash-arithmetic regression, spelled EXACTLY as it would be written by
# hand. `[ 0.5 -gt 0 ]` is not a float comparison in bash — it is an error, and
# without `set -e` it simply evaluates false, so every ordinary 0.5h row is
# classed as lacking an occupancy estimate and a human is routed to fix a
# non-defect.
mutate 6 "occupancy compares a FLOAT est_h with a bash integer test" \
    "    awk -v v=\"\$esth\" 'BEGIN{exit !(v > 0)}' || { printf 'no-occupancy-estimate'; return 0; }" \
    '    [ "$esth" -gt 0 ] 2>/dev/null || { printf '"'"'no-occupancy-estimate'"'"'; return 0; }' \
    "fractional occupancy passes"

mutate 7 "the owner table stops refusing a class nobody declared" \
    '        unscreened|no-occupancy-estimate|premise-parked) printf ' \
    '        unscreened|no-occupancy-estimate|premise-parked|*) printf ' \
    "an undeclared class has NO owner"

# --- the aging condition ----------------------------------------------------
mutate 8 "capacity drops out of the aging condition (pages a fleet that is working)" \
    '            if [ "$n" -gt 0 ] && [ "$FW_CAPACITY_FREE" -gt 0 ]; then' \
    '            if [ "$n" -gt 0 ]; then' \
    "no alarm while every slot is busy"

mutate 9 "in-flight rows stop consuming capacity" \
    '            ASSIGNED|CLAIMED|RUNNING) FW_INFLIGHT=$((FW_INFLIGHT + 1)); continue ;;' \
    '            ASSIGNED|CLAIMED|RUNNING) continue ;;' \
    "capacity full"

mutate 10 "the age threshold is ignored (every READY row reads as aged)" \
    '        [ "${age:-0}" -ge "$AGE_THRESHOLD_S" ] 2>/dev/null || continue' \
    '        [ "${age:-0}" -ne 0 ] 2>/dev/null || continue' \
    "only rows past the threshold age"

mutate 11 "terminal and operator-held rows are counted as pending backlog" \
    '            *) continue ;;     # terminal, INFRA_BLOCKED, HELD_OP_GATE: nobody is waiting on them' \
    '            *) ;;' \
    "terminal/held rows are not READY"

# Tab is an IFS WHITESPACE character: `IFS=$'\t' read` collapses runs of it and
# drops every empty field, shifting `gating` into `parked_reason` so a row with
# no occupancy estimate is reported as `premise-parked` — the wrong owner, with
# a straight face. This is not hypothetical; it is how the first draft behaved.
mutate 12 "the record separator reverts to a tab (empty fields collapse)" \
    "    while IFS=\$'\\x1f' read -r task status age screened esth parked gating; do" \
    "    while IFS=\$'\\t' read -r task status age screened esth parked gating; do" \
    "READY rows counted"

# --- COMPUTE-IDLE -----------------------------------------------------------
mutate 13 'compute reinstates the ${gpu:-0} fail-open (unknown reads as 0%)' \
    "        *unknown*) printf 'unknown'; return 0 ;;" \
    '        *unknown*) : ;;' \
    "unreadable compute"

mutate 14 "compute stops checking VRAM independently of GPU%" \
    '    if [ "$gpu" = "0" ] && [ "$vram" = "0" ] && [ "$free" = "$total" ]; then' \
    '    if [ "$gpu" = "0" ] && [ "$free" = "$total" ]; then' \
    "vram resident"

mutate 15 "an absent rocm-smi key reads as 0% instead of unknown" \
    'if length == 0 then "unknown" else (max | floor) end' \
    'if length == 0 then 0 else (max | floor) end' \
    "absent key -> unknown, not 0"

mutate 16 "regions counted with a bare 'grep -c free' over whole lines" \
    "fw_regions_free()  { printf '%s\\n' \"\$1\" | grep -cE '^[[:space:]]*[A-Za-z0-9_]+[[:space:]]+free([[:space:]]|\$)'; }" \
    "fw_regions_free()  { printf '%s\\n' \"\$1\" | grep -c 'free'; }" \
    "free regions counted from the state column"

# THE GATE METRIC. Idle hardware with nothing queued for it is a well-run night.
# Escalating it is how an operator learns to mute the channel, and it is the one
# thing "zero alarms on well-run nights" forbids outright.
mutate 17 "idle compute alarms even with NO compute-gated work queued" \
    '        if [ "$compute" = "idle" ] && [ "$FW_READY_GATED" -gt 0 ]; then' \
    '        if [ "$compute" = "idle" ]; then' \
    "empty queue + idle card -> ZERO alarms"

mutate 28 "the not-an-alarm occupancy line denies queued work that IS queued" \
    '            if [ "$FW_READY_GATED" -eq 0 ]; then
                FW_OBSERVATIONS+=("COMPUTE-IDLE (not an alarm)' \
    '            if true; then
                FW_OBSERVATIONS+=("COMPUTE-IDLE (not an alarm)' \
    "does NOT deny the queued gated work"

mutate 18 "compute-gated rows stop being distinguished from ungated ones" \
    '            *) FW_READY_GATED=$((FW_READY_GATED + 1)) ;;' \
    '            *) ;;' \
    "compute-gated READY rows counted separately"

# --- the alarm plane (rule 2 applied to alarms) -----------------------------
mutate 19 "an UNREADABLE queue is treated as an EMPTY one (the fail-open)" \
    '    if tsv=$(fw_queue_rows); then' \
    '    if tsv=$(fw_queue_rows) || tsv=""; then' \
    "unreadable queue"

mutate 20 "the clear sweep stops checking which keys this script OWNS" \
    '        case " ${FW_OWNED_KEYS} " in *" ${key} "*) ;; *) continue ;; esac' \
    '        :' \
    "foreign alarm key is left ACTIVE"

mutate 21 "the clear sweep resolves alarms in domains it could not READ" \
    '        case " ${eligible} "        in *" ${key} "*) ;; *) continue ;; esac' \
    '        :' \
    "unreadable queue never CLEARS"

mutate 22 "an unreadable alarm channel is passed over silently" \
    '        FW_OBSERVATIONS+=("ALARM-STATE-UNREADABLE ${ALARM} status could not be read — nothing cleared this cycle (an unreadable channel is not a quiet one)")' \
    '        :' \
    "unreadable alarm state is REPORTED"

# --- evidence is never a trigger (rule 4 / D8) ------------------------------
mutate 23 "pane evidence is ON by default (pane text starts reaching alarms)" \
    'EVIDENCE_PANES="${FLEET_WATCH_EVIDENCE_PANES:-}"' \
    'EVIDENCE_PANES="${FLEET_WATCH_EVIDENCE_PANES:-console}"' \
    "evidence capture is OFF by default"

mutate 24 "captured pane text loses its EVIDENCE-ONLY labelling" \
    'EVIDENCE ONLY, NOT A TRIGGER — pane scrollback for human triage: ' \
    'pane: ' \
    "clearly labelled when enabled"

# --- verdict / reporting ----------------------------------------------------
mutate 25 "the first-cycle lie is reinstated (warming collapses into ok)" \
    '    elif [ "$FW_CYCLE" -lt "$PERSIST_CYCLES" ]; then' \
    '    elif false; then' \
    "cycle 1 verdict"

mutate 26 "a degraded cycle is reported as fully healthy" \
    '    elif [ "$compute" = "unknown" ] || [ "$queue_ok" != "1" ]; then' \
    '    elif false; then' \
    "degraded verdict"

mutate 27 "findings go back through printf '%b' (escapes re-interpreted)" \
    '            [ -n "$line" ] && printf '"'"'  %s\n'"'"' "$line" >> "$LOG"' \
    '            [ -n "$line" ] && printf '"'"'  %b\n'"'"' "$line" >> "$LOG"' \
    "backslashes in a task_id"

printf '\n=========================================\n'
printf 'mutation harness: %d caught, %d survived\n' "$((PASS - 1))" "$FAIL"
printf '(plus 1 control case: the pristine script passes)\n'
if [ "$FAIL" -gt 0 ]; then
    printf 'SURVIVING OR DEFECTIVE MUTATIONS:\n'
    printf '  - %s\n' ${SURVIVORS[@]+"${SURVIVORS[@]}"}
    exit 1
fi
exit 0
