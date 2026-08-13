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

# --- STUCK-INPUT ------------------------------------------------------------
mutate 1 "STUCK-INPUT alarms on PRESENCE instead of persistence" \
    '[ "${FW_PEND_N[$a]:-0}" -ge "$PERSIST_CYCLES" ]' \
    '[ "${FW_PEND_N[$a]:-0}" -ge 1 ]' \
    "does not fire before PERSIST_CYCLES"

mutate 2 "STUCK-INPUT ignores whether the text CHANGED between cycles" \
    'if [ "$pending" = "${FW_PEND_TEXT[$a]:-}" ]; then' \
    'if true; then' \
    "text that CHANGES each cycle never fires"

mutate 3 "composer treats the Codex placeholder as pending input" \
    '    if printf '"'"'%s'"'"' "$rest" | grep -qE "$PLACEHOLDER_RE" 2>/dev/null; then' \
    '    if false; then' \
    "codex placeholder"

mutate 4 "composer reports an unrecognised row as EMPTY instead of UNKNOWN" \
    '[ "$matched" = 1 ] || return 1' \
    '[ "$matched" = 1 ] || { printf ""; return 0; }' \
    "non-composer row"

mutate 5 "an unreadable composer HOLDS its persistence counter instead of resetting" \
    '            FW_PEND_N[$a]=0
            FW_PEND_TEXT[$a]=""' \
    '            :' \
    "unreadable composer resets"

# --- IDLE-CANDIDATE ---------------------------------------------------------
mutate 6 "liveness treats an UNREADABLE quiet reading as idle (fail-open)" \
    "        ''|null|*[!0-9.]*) printf 'unknown'; return 0 ;;" \
    "        ''|null|*[!0-9.]*) printf 'idle'; return 0 ;;" \
    "unreadable quiet"

mutate 7 "liveness ignores the authoritative runtime ACTIVE signal" \
    '    [ "$runtime" = "active" ] && { printf '"'"'busy'"'"'; return 0; }' \
    '    :' \
    "runtime active beats a long quiet window"

mutate 8 "liveness drops the busy-marker veto (the compacting case)" \
    '    [ "$pane_busy" = "0" ] && { printf '"'"'busy'"'"'; return 0; }' \
    '    :' \
    "busy marker vetoes idle"

mutate 9 "an UNREADABLE pane is treated as idle rather than unknown" \
    '    [ "$pane_busy" = "2" ] && { printf '"'"'unknown'"'"'; return 0; }' \
    '    [ "$pane_busy" = "2" ] && { printf '"'"'idle'"'"'; return 0; }' \
    "unreadable pane"

# The bash-arithmetic regression, spelled EXACTLY as it would be written by
# hand. `[ 243.3 -ge 120 ]` is not a float comparison in bash — it is an error,
# and without `set -e` it simply evaluates false, so every genuinely idle main
# silently reports busy and IDLE-CANDIDATE never fires again.
#
# NOTE what this mutation is NOT. An earlier version of this case used
# `[ "${quiet%%.*}" -ge ... ]`, which truncates before comparing. That mutant
# SURVIVED, and correctly so: floor(q) >= t is equivalent to q >= t for an
# integer threshold, so it is an equivalent mutant and not a gap in the suite.
# It is recorded here because "the suite did not catch it" and "the suite has a
# hole" are different conclusions, and only the second one is a defect.
mutate 10 "liveness compares a FLOAT quiet reading with bash integer test" \
    "    if awk -v q=\"\$quiet\" -v t=\"\$IDLE_QUIET_S\" 'BEGIN{exit !(q >= t)}'; then" \
    '    if [ "$quiet" -ge "$IDLE_QUIET_S" ] 2>/dev/null; then' \
    "float quiet compares correctly"

# --- COMPUTE-IDLE -----------------------------------------------------------
mutate 11 'compute reinstates the ${gpu:-0} fail-open (unknown reads as 0%)' \
    '    local gpu="$1" vram="$2"' \
    '    local gpu="${1/unknown/0}" vram="${2/unknown/0}"' \
    "unreadable gpu"

mutate 12 "compute stops checking VRAM independently of GPU%" \
    '    if [ "$gpu" = "0" ] && [ "$vram" = "0" ]; then' \
    '    if [ "$gpu" = "0" ]; then' \
    "vram resident"

mutate 13 "COMPUTE-IDLE fires on a single sample (no persistence)" \
    '[ "$FW_COMPUTE_N" -ge "$PERSIST_CYCLES" ]' \
    '[ "$FW_COMPUTE_N" -ge 1 ]' \
    "does not fire on a single sample"

mutate 14 "regions counted with a bare 'grep -c free' over whole lines" \
    "fw_regions_free()  { printf '%s\\n' \"\$1\" | grep -cE '^[[:space:]]*[A-Za-z0-9_]+[[:space:]]+free([[:space:]]|\$)'; }" \
    "fw_regions_free()  { printf '%s\\n' \"\$1\" | grep -c 'free'; }" \
    "free regions counted from the state column"

mutate 15 "an absent rocm-smi key reads as 0% instead of unknown" \
    'if length == 0 then "unknown" else (max | floor) end' \
    'if length == 0 then 0 else (max | floor) end' \
    "absent key -> unknown, not 0"

# --- verdict / reporting ----------------------------------------------------
mutate 16 "the first-cycle lie is reinstated (warming collapses into ok)" \
    '    elif [ "$FW_CYCLE" -lt "$PERSIST_CYCLES" ]; then' \
    '    elif false; then' \
    "cycle 1 verdict"

mutate 17 "a degraded cycle is reported as fully healthy" \
    '    elif [ "$unknown_mains" -gt 0 ] || [ "$compute" = "unknown" ]; then' \
    '    elif false; then' \
    "degraded verdict"

mutate 18 "an absent tmux session is passed over silently" \
    '    if ! fw_session_exists; then' \
    '    if false; then' \
    "absent tmux session is REPORTED"

mutate 19 "the DETECTOR-BLIND drift guard is removed" \
    '    if [ "$readable" -gt 0 ] && [ "$recognised" -eq 0 ]; then' \
    '    if false; then' \
    "DETECTOR-BLIND"

mutate 20 "findings go back through printf '%b' (escapes re-interpreted)" \
    '            [ -n "$line" ] && printf '"'"'  %s\n'"'"' "$line" >> "$LOG"' \
    '            [ -n "$line" ] && printf '"'"'  %b\n'"'"' "$line" >> "$LOG"' \
    "backslashes in composer text"

mutate 21 "an unreadable pane is skipped instead of reported" \
    '            FW_FINDINGS+=("PANE-UNREADABLE ${a} — capture-pane returned nothing (reported, NOT treated as idle)")' \
    '            :' \
    "unreadable pane is REPORTED"

printf '\n=========================================\n'
printf 'mutation harness: %d caught, %d survived\n' "$((PASS - 1))" "$FAIL"
printf '(plus 1 control case: the pristine script passes)\n'
if [ "$FAIL" -gt 0 ]; then
    printf 'SURVIVING OR DEFECTIVE MUTATIONS:\n'
    printf '  - %s\n' ${SURVIVORS[@]+"${SURVIVORS[@]}"}
    exit 1
fi
exit 0
