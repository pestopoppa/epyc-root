#!/bin/bash
# =============================================================================
# test_fleet_watch.sh — correctness suite for scripts/coordination/fleet_watch.sh
# =============================================================================
#
# WHY A SUITE AT ALL. This detector's failure mode is SILENCE: a broken rule does
# not crash, it just stops reporting, and the log keeps saying "ok" — which is
# indistinguishable from a healthy fleet. The pre-production version had exactly
# that shape and nobody could have told. So every rule is exercised in BOTH
# directions here: it must FIRE on the stall fixture and, crucially, must NOT
# fire on the COMPLIANT one.
#
# WHAT CHANGED AT P3-3. The pane-heuristic cases are GONE, because the detectors
# they covered are gone: STUCK-INPUT (2,499 of its 2,654 production reports were
# the agent CLI's own empty-composer placeholder text), IDLE-CANDIDATE,
# DETECTOR-BLIND, PANE-UNREADABLE, PANE-DEAD, FLEET-UNREADABLE. What is tested
# now is the two hardware/bus-grounded detectors and the ALARM plane:
#
#   [1] compute classification (unchanged, still three-valued)
#   [2] refusal classification — the R9 taxonomy, one owner per class
#   [3] the queue scan — aging, capacity, gated-work counting
#   [4] full cycles — persistence, alarm raise/clear, and the three gate
#       properties this task must prove:
#         (a) a REFUSED row counts as AGING
#         (b) the alarm fires ONCE ON STATE CHANGE, not once per tick
#         (c) a healthy quiet state produces NO alarm at all
#   [5] the log shape the coordinator's Monitor and session_bus.py both grep
#
# HOW IT DRIVES THE REAL CODE. `fleet_watch.sh` is sourceable as a library (it
# returns before its dispatch block when `$0` differs from `$BASH_SOURCE`), and
# every function that touches the outside world is isolated in one probe layer.
# The suite sources the script and REDEFINES that layer to serve fixtures, so
# the classifiers, the persistence machine, the alarm decisions and the verdict
# logic all run as production code — with no live tmux, no GPU, no bus, no
# alarm channel and no roster.
#
# NOTHING HERE TOUCHES THE LIVE FLEET. No tmux command is issued, no process is
# signalled, no bus file is read or written, `alarm_channel.py` is never invoked
# (fw_alarm_raise / fw_alarm_clear / fw_alarm_active are overridden before any
# cycle runs), and LOG points into a per-run mktemp directory.
#
# Usage:  tests/test_fleet_watch.sh
#         FLEET_WATCH_SH=/path/to/mutant.sh tests/test_fleet_watch.sh
# The env override exists so the mutation harness can run this suite against a
# deliberately broken copy — a test that has never failed has not been shown to
# test anything.
# =============================================================================
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="${FLEET_WATCH_SH:-${HERE}/../fleet_watch.sh}"

if [ ! -f "$SCRIPT" ]; then
    printf 'test_fleet_watch: no such script: %s\n' "$SCRIPT" >&2
    exit 2
fi

# REFUSE TO SOURCE A SCRIPT WITHOUT THE LIBRARY GUARD, and say why. Sourcing a
# file whose main loop runs at the bottom does not fail — it HANGS, forever,
# inside this suite, having quietly started a second detector. That happened once
# (against the pre-production prototype, which has no guard) and cost a wedged
# 120s timeout with no diagnosis in the output. Fail in one line instead.
# -F, and the exact line. The first draft of this check used a BRE that had lost
# a brace, so it matched NOTHING and refused every script including a correct
# one — and it looked fine, because it had only ever been run against the
# guard-less prototype it was written to reject. A check exercised in one
# direction only is not a check.
if ! grep -qF '"${BASH_SOURCE[0]}" != "${0}"' "$SCRIPT"; then
    printf 'test_fleet_watch: %s has no sourced-as-library guard.\n' "$SCRIPT" >&2
    printf '  Sourcing it would start its main loop and hang this suite.\n' >&2
    exit 2
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# Test-only configuration, exported BEFORE sourcing so the script picks it up.
export FLEET_WATCH_LOG="$TMP/fleet_watch.log"
export FLEET_WATCH_PERSIST_CYCLES=3
export FLEET_WATCH_INTERVAL=90
export FLEET_WATCH_LOCK="$TMP/lock"
export FLEET_WATCH_AGE_THRESHOLD_S=21600        # 6h
export FLEET_WATCH_CAPACITY=4
export FLEET_WATCH_QUEUE_FILE="$TMP/queue.jsonl"
export FLEET_WATCH_BUS_ROOT="$TMP"
# The alarm probes are overridden below, but pointing the config at a path that
# does not exist is a second belt: an override that ever went missing would fail
# loudly rather than page a real operator from a unit test.
export FLEET_WATCH_ALARM="$TMP/no-such-alarm-channel.py"
export FLEET_WATCH_EVIDENCE_PANES=""

PASS=0; FAIL=0
FAILED_NAMES=()
chk() {  # chk <name> <got> <want>
    if [ "$2" = "$3" ]; then
        PASS=$((PASS + 1)); printf '  PASS  %s\n' "$1"
    else
        FAIL=$((FAIL + 1)); FAILED_NAMES+=("$1")
        printf '  FAIL  %s\n        got:  %s\n        want: %s\n' "$1" "$2" "$3"
    fi
}
chk_contains() {  # chk_contains <name> <haystack> <needle>
    case "$2" in
        *"$3"*) PASS=$((PASS + 1)); printf '  PASS  %s\n' "$1" ;;
        *) FAIL=$((FAIL + 1)); FAILED_NAMES+=("$1")
           printf '  FAIL  %s\n        %s\n        does not contain: %s\n' "$1" "$2" "$3" ;;
    esac
}
chk_lacks() {  # chk_lacks <name> <haystack> <needle>
    case "$2" in
        *"$3"*) FAIL=$((FAIL + 1)); FAILED_NAMES+=("$1")
                printf '  FAIL  %s\n        %s\n        MUST NOT contain: %s\n' "$1" "$2" "$3" ;;
        *) PASS=$((PASS + 1)); printf '  PASS  %s\n' "$1" ;;
    esac
}

# shellcheck source=/dev/null
source "$SCRIPT"

# Snapshot the DEFAULT the script chose for pane-evidence capture, before any
# case below touches the variable. Asserting on it later would be vacuous: the
# tests that exercise evidence capture necessarily set it themselves, so a
# script that shipped with capture ON would pass every one of them. The default
# is the property, and this is the only moment it is observable.
FW_EVIDENCE_DEFAULT="${EVIDENCE_PANES:-<empty>}"

# =============================================================================
# 1. COMPUTE — three states, and VRAM independent of GPU%
# =============================================================================
printf '\n[1] compute classification\n'

chk "0%% / 0%% / all regions free -> idle"  "$(fw_classify_compute 0 0 4 4)"  "idle"
chk "gpu busy -> busy"                      "$(fw_classify_compute 7 0 4 4)"  "busy"
# VRAM IS CHECKED INDEPENDENTLY. A run that silently fell back to CPU shows 0%
# util AND 0% VRAM; a resident model with an idle card shows 0% util and NONZERO
# VRAM, and that is NOT idle compute.
chk "vram resident -> busy even at 0% util"  "$(fw_classify_compute 0 42 4 4)" "busy"
chk "a held region -> busy"                  "$(fw_classify_compute 0 0 3 4)"  "busy"
# THE FAIL-OPEN REGRESSION. The pre-production version wrote ${gpu:-0}, so an
# unreadable rocm-smi read as 0% and manufactured a COMPUTE-IDLE alarm forever.
chk "unreadable gpu -> unknown, NOT idle"    "$(fw_classify_compute unknown 0 4 4)" "unknown"
chk "unreadable vram -> unknown, NOT idle"   "$(fw_classify_compute 0 unknown 4 4)" "unknown"
chk "unreadable regions -> unknown"          "$(fw_classify_compute 0 0 unknown unknown)" "unknown"
chk "zero regions found -> unknown"          "$(fw_classify_compute 0 0 0 0)" "unknown"

# region-lock's holder column is free text. `grep -c free` over whole lines
# counts a holder whose command happens to contain the word.
REGIONS=$'  q0  free   \n  q1  HELD   pid 123 bench --output freeze.json\n  q2  free   \n  q3  free   '
chk "free regions counted from the state column" "$(fw_regions_free "$REGIONS")"  "3"
chk "total regions counted, not assumed to be 4" "$(fw_regions_total "$REGIONS")" "4"

GPU_JSON='{"card0":{"GPU use (%)":"0","GPU Memory Allocated (VRAM%)":"0"}}'
chk "gpu metric parsed from json"   "$(fw_gpu_metric "$GPU_JSON" 'GPU use (%)')" "0"
chk "absent key -> unknown, not 0"  "$(fw_gpu_metric '{"card0":{}}' 'GPU use (%)')" "unknown"
chk "max taken across cards" \
    "$(fw_gpu_metric '{"card0":{"GPU use (%)":"0"},"card1":{"GPU use (%)":"63"}}' 'GPU use (%)')" "63"

# =============================================================================
# 2. REFUSAL CLASSIFICATION — the R9 taxonomy
#
# Every class must (a) be produced by the classifier, (b) have an owner, and
# (c) have a fix. A class with no owner is the 9,219-refusal failure in miniature:
# a refusal nobody is accountable for is a row nobody drains.
# =============================================================================
printf '\n[2] refusal classification\n'

# args: screened(1|0) est_h parked_reason
chk "unscreened row -> unscreened"        "$(fw_refusal_class 0 0.5 '')"  "unscreened"
chk "no occupancy estimate -> its class"  "$(fw_refusal_class 1 ''  '')"  "no-occupancy-estimate"
chk "zero occupancy is no estimate"       "$(fw_refusal_class 1 0   '')"  "no-occupancy-estimate"
chk "non-numeric occupancy is no estimate" "$(fw_refusal_class 1 'soon' '')" "no-occupancy-estimate"
# est_h is a FLOAT. `[ 0.5 -gt 0 ]` is not an arithmetic comparison in bash — it
# is an error that silently evaluates false, which would class every ordinary
# 0.5h row as lacking an estimate and send a human to fix a non-defect.
chk "fractional occupancy passes"         "$(fw_refusal_class 1 0.5 '')"  "dispatchable"
chk "a fully-gated row is dispatchable"   "$(fw_refusal_class 1 2   '')"  "dispatchable"
# A parked row reached the premise screener, which runs INSIDE worker_runner
# after the claim — so dispatch_gate already said yes and calling it unscreened
# would route a human to the wrong gate.
chk "parked row -> premise-parked"        "$(fw_refusal_class 1 0.5 'premise-stale')"   "premise-parked"
chk "parked beats unscreened"             "$(fw_refusal_class 0 ''  'premise-unknown')" "premise-parked"

for cls in $FW_CLASSES; do
    owner=$(fw_class_owner "$cls"); rc_o=$?
    fix=$(fw_class_fix "$cls");     rc_f=$?
    chk "class '${cls}' has an owner" "${rc_o}:$([ -n "$owner" ] && printf yes || printf no)" "0:yes"
    chk "class '${cls}' has a fix"    "${rc_f}:$([ -n "$fix" ]   && printf yes || printf no)" "0:yes"
done
fw_class_owner "a-class-nobody-declared" >/dev/null 2>&1
chk "an undeclared class has NO owner (fails loudly)" "$?" "1"

# =============================================================================
# 3. THE QUEUE SCAN
#
# Record contract: task_id | status | age_s | screened | est_h | parked | gating,
# US-separated (\x1f). NOT tab: tab is an IFS WHITESPACE character, so
# `IFS=$'\t' read` collapses runs of it and drops every empty field — a row with
# no occupancy estimate would shift `gating` into `parked_reason` and be
# misclassified as `premise-parked`, i.e. routed to the wrong owner. The empty
# `est_h` and empty `parked` fixtures below are what pin that.
# =============================================================================
printf '\n[3] queue scan\n'

OLD=30000     # > 6h threshold
NEW=60        # a minute old

US=$'\x1f'
row() { printf "%s${US}%s${US}%s${US}%s${US}%s${US}%s${US}%s" "$1" "$2" "$3" "$4" "$5" "$6" "$7"; }

TSV=$(printf '%s\n%s\n%s\n%s' \
    "$(row t-old-ok     READY    "$OLD" 1 0.5 ''              none)" \
    "$(row t-new-ok     READY    "$NEW" 1 0.5 ''              none)" \
    "$(row t-old-unscr  READY    "$OLD" 0 0.5 ''              none)" \
    "$(row t-running    RUNNING  "$OLD" 1 0.5 ''              none)")
fw_scan_queue "$TSV"
chk "READY rows counted"            "$FW_READY"     "3"
chk "in-flight rows counted"        "$FW_INFLIGHT"  "1"
chk "only rows past the threshold age" "$FW_AGED"   "2"
chk "capacity = cap - in flight"    "$FW_CAPACITY_FREE" "3"
chk "oldest row identified"         "$FW_OLDEST_ID" "t-old-ok"
chk "aged dispatchable counted"     "${FW_CLASS_AGED[dispatchable]:-0}" "1"
chk "aged unscreened counted"       "${FW_CLASS_AGED[unscreened]:-0}"   "1"

# Terminal and held rows are nobody's backlog — they must not inflate aging.
TSV=$(printf '%s\n%s\n%s' \
    "$(row t-done  DONE_PASS    "$OLD" 1 0.5 '' none)" \
    "$(row t-canc  CANCELLED    "$OLD" 1 0.5 '' none)" \
    "$(row t-held  HELD_OP_GATE "$OLD" 1 0.5 '' none)")
fw_scan_queue "$TSV"
chk "terminal/held rows are not READY" "${FW_READY}:${FW_AGED}" "0:0"

# A row with an unparseable timestamp reads as -1 and must never count as aged:
# UNKNOWN is not old (rule 2).
TSV=$(row t-badts READY -1 1 0.5 '' none)
fw_scan_queue "$TSV"
chk "unparseable ts -> READY but NOT aged" "${FW_READY}:${FW_AGED}" "1:0"

# `gating` names the hardware a row needs; only those can explain an idle GPU.
TSV=$(printf '%s\n%s' \
    "$(row t-cpu READY "$NEW" 1 0.5 '' cpu)" \
    "$(row t-non READY "$NEW" 1 0.5 '' none)")
fw_scan_queue "$TSV"
chk "compute-gated READY rows counted separately" "${FW_READY}:${FW_READY_GATED}" "2:1"

# =============================================================================
# 4. FULL CYCLES — persistence, the alarm plane, and the three gate properties
#
# The probe layer is replaced below. Everything downstream is production code.
# =============================================================================
printf '\n[4] full-cycle behaviour + alarm plane\n'

FIX_TSV=""
FIX_TSV_OK=0                                   # 0 = readable, 1 = UNKNOWN
FIX_GPU='{"card0":{"GPU use (%)":"55","GPU Memory Allocated (VRAM%)":"71"}}'
FIX_REGIONS=$'  q0  HELD   bench\n  q1  free   \n  q2  free   \n  q3  free   '

# The alarm channel is a FAKE with the real channel's contract: it keeps an
# active set, and a raise on an already-active key is recorded as SUPPRESSED
# rather than as a second notification. That is what lets this suite distinguish
# "emitted once on state change" from "emitted once per tick" — the property the
# 9,219 repeated `dispatch-refused` advisories violated.
declare -A FAKE_ACTIVE
declare -a ALARM_LOG=()
FAKE_ALARM_READABLE=0                          # 0 = status readable, 1 = UNKNOWN

fw_gpu_json()     { [ -n "$FIX_GPU" ] || return 1; printf '%s' "$FIX_GPU"; }
fw_regions_text() { [ -n "$FIX_REGIONS" ] || return 1; printf '%s' "$FIX_REGIONS"; }
fw_queue_rows()   { [ "$FIX_TSV_OK" = 0 ] || return 1; printf '%s' "$FIX_TSV"; }
fw_capture_pane() { printf 'PANE TEXT MUST NEVER REACH A DECISION\n'; }

fw_alarm_active() {
    [ "$FAKE_ALARM_READABLE" = 0 ] || return 1
    local k
    # The KEYS form. `${!arr[@]+word}` is parsed by bash as INDIRECT expansion
    # and explodes with "invalid variable name"; `"${!arr[@]}"` is already safe
    # on an empty associative array under `set -u`.
    for k in "${!FAKE_ACTIVE[@]}"; do printf '%s\n' "$k"; done
}
fw_alarm_raise() {
    if [ -n "${FAKE_ACTIVE[$1]:-}" ]; then
        ALARM_LOG+=("SUPPRESSED $1")
    else
        FAKE_ACTIVE[$1]="$3"
        # The EVIDENCE object is recorded too, not just the message. Anything
        # that leaks into an alarm leaks through one of the two, and a fake that
        # only kept the message would let pane text reach a real operator while
        # every "no pane text in an alarm" case still passed. `jq -nc` emits one
        # line, so this stays greppable.
        ALARM_LOG+=("NOTIFIED $1 [$2] $3 :: evidence=$4")
    fi
    return 0
}
fw_alarm_clear() {
    if [ -n "${FAKE_ACTIVE[$1]:-}" ]; then
        unset "FAKE_ACTIVE[$1]"
        ALARM_LOG+=("CLEARED $1")
    else
        ALARM_LOG+=("NOT-ACTIVE $1")
    fi
    return 0
}

reset_all() {
    fw_reset_state
    FAKE_ACTIVE=(); ALARM_LOG=()
    FAKE_ALARM_READABLE=0
}
# Runs N cycles IN THE CURRENT SHELL and publishes the last cycle's findings in
# LAST_OUT. It must not be used as `out=$(cycles N)`: command substitution forks a
# subshell, so the persistence counters it advances would be thrown away and the
# next call would start from zero — the same trap documented on fw_run_cycle, and
# it silently made eight of these cases pass for the wrong reason on first run.
LAST_OUT=""
cycles() {
    local n="$1" i
    for ((i = 0; i < n; i++)); do fw_run_cycle; done
    LAST_OUT=$(printf '%s\n' ${FW_FINDINGS[@]+"${FW_FINDINGS[@]}"})
}
alarm_log() { printf '%s\n' ${ALARM_LOG[@]+"${ALARM_LOG[@]}"}; }
count_notified() { alarm_log | grep -c "^NOTIFIED $1" ; }

# ---- 4a. GATE PROPERTY (c): a healthy quiet state produces NO alarm ---------
# The explicit gate metric of this restructure: "zero alarms on well-run nights".
# Fresh rows, capacity free, hardware busy. Nothing may be raised — and, just as
# importantly, nothing may be *cleared* either, because nothing was ever active.
reset_all
FIX_TSV=$(printf '%s\n%s' \
    "$(row q-a READY "$NEW" 1 0.5 '' none)" \
    "$(row q-b READY "$NEW" 1 1.0 '' cpu)")
cycles 8; out="$LAST_OUT"
chk "COMPLIANT: fresh queue + busy compute -> no findings at all" "$(printf '%s' "$out" | tr -d '\n')" ""
chk "COMPLIANT: verdict is ok" "$FW_VERDICT" "ok"
chk "COMPLIANT: ZERO alarms on a well-run night" "$(alarm_log | grep -c NOTIFIED)" "0"
chk "COMPLIANT: nothing spuriously cleared either" "$(alarm_log | grep -c CLEARED)" "0"

# The quietest night of all: an EMPTY queue and an IDLE card. Idle hardware with
# nothing queued for it is not a fault, and paging for it is exactly how an
# operator learns to mute the channel.
reset_all
FIX_TSV=""
FIX_GPU='{"card0":{"GPU use (%)":"0","GPU Memory Allocated (VRAM%)":"0"}}'
FIX_REGIONS=$'  q0  free   \n  q1  free   \n  q2  free   \n  q3  free   '
cycles 8; out="$LAST_OUT"
chk "COMPLIANT: empty queue + idle card -> no findings" "$(printf '%s' "$out" | tr -d '\n')" ""
chk "COMPLIANT: empty queue + idle card -> ZERO alarms" "$(alarm_log | grep -c NOTIFIED)" "0"
# ...but the READING is still logged, because session_bus.py's boundary report
# greps this file for the COMPUTE-IDLE token to answer "is the fleet occupied".
chk_contains "the idle READING is still reported (not an alarm)" \
    "$(printf '%s\n' ${FW_OBSERVATIONS[@]+"${FW_OBSERVATIONS[@]}"})" "COMPUTE-IDLE (not an alarm)"

# ---- 4b. COMPUTE-IDLE escalates only with compute-gated work queued --------
reset_all
FIX_TSV=$(row q-cpu READY "$NEW" 1 0.5 '' cpu)      # gated work, and it is fresh
cycles 2; out="$LAST_OUT"
chk_lacks "COMPUTE-IDLE does not fire on a single sample" "$out" "COMPUTE-IDLE"
cycles 1; out="$LAST_OUT"
chk_contains "COMPUTE-IDLE fires on persistence with gated work queued" "$out" "COMPUTE-IDLE"
chk "COMPUTE-IDLE raised exactly once" "$(count_notified compute-idle-with-queued-work)" "1"
cycles 5
chk "COMPUTE-IDLE still raised exactly once after 5 more cycles" \
    "$(count_notified compute-idle-with-queued-work)" "1"

# THE llama-bench GAP. The card legitimately reads 0%/0% between probes inside a
# perfectly healthy sweep. One busy sample must reset the counter.
reset_all
for pattern in idle idle busy idle idle busy idle idle; do
    if [ "$pattern" = busy ]; then
        FIX_GPU='{"card0":{"GPU use (%)":"98","GPU Memory Allocated (VRAM%)":"71"}}'
    else
        FIX_GPU='{"card0":{"GPU use (%)":"0","GPU Memory Allocated (VRAM%)":"0"}}'
    fi
    fw_run_cycle
done
out=$(printf '%s\n' ${FW_FINDINGS[@]+"${FW_FINDINGS[@]}"})
chk_lacks "COMPLIANT: a sweep's inter-probe gaps never fire COMPUTE-IDLE" "$out" "COMPUTE-IDLE ["
chk "COMPLIANT: a sweep's inter-probe gaps raise no alarm" \
    "$(count_notified compute-idle-with-queued-work)" "0"

# An unreadable GPU is not an idle GPU.
reset_all
FIX_GPU=""
cycles 6; out="$LAST_OUT"
chk "unreadable compute raises nothing" "$(count_notified compute-idle-with-queued-work)" "0"
chk "unreadable compute -> degraded verdict" "$FW_VERDICT" "degraded"
FIX_GPU='{"card0":{"GPU use (%)":"0","GPU Memory Allocated (VRAM%)":"0"}}'

# ---- 4c. GATE PROPERTY (a): a REFUSED row COUNTS AS AGING ------------------
# The R9 finding: 9,219 identical `dispatch-refused` advisories repeated a
# refusal nobody ever acted on. A row the gate refuses is not a row that was
# handled — the refusal is precisely WHY it is still sitting there — so it must
# age, and the alarm must name the class's OWNER and its FIX.
reset_all
FIX_REGIONS=$'  q0  HELD   bench\n  q1  free   \n  q2  free   \n  q3  free   '
FIX_GPU='{"card0":{"GPU use (%)":"55","GPU Memory Allocated (VRAM%)":"71"}}'
FIX_TSV=$(row r-unscreened READY "$OLD" 0 0.5 '' none)   # refused: no screened_by
cycles 2; out="$LAST_OUT"
chk_lacks "QUEUE-AGING does not fire before PERSIST_CYCLES" "$out" "QUEUE-AGING"
cycles 1; out="$LAST_OUT"
chk_contains "a REFUSED (unscreened) row COUNTS AS AGING" "$out" "QUEUE-AGING unscreened"
chk_contains "the aging alarm names the class OWNER" "$(alarm_log)" "OWNER: coordinator-agent"
chk_contains "the aging alarm carries a routed FIX" "$(alarm_log)" "backlog_row_check.py"
chk "the refused row was raised on ITS OWN class key" \
    "$(count_notified queue-aging-unscreened)" "1"

# A row PARKED by the premise screener (READY + parked_reason) is refused by a
# later gate and must age on its own class, not be silently absorbed.
reset_all
FIX_TSV=$(row r-parked READY "$OLD" 1 0.5 'premise-stale' none)
cycles 3; out="$LAST_OUT"
chk_contains "a PARKED row counts as aging on its own class" "$out" "QUEUE-AGING premise-parked"
chk "parked row raised the premise-parked key" "$(count_notified queue-aging-premise-parked)" "1"
chk "parked row did NOT raise the unscreened key" "$(count_notified queue-aging-unscreened)" "0"

# A row that NO gate refused, aging with capacity free, is the P3-4 anomaly:
# nothing spawned. Different owner, different fix.
reset_all
FIX_TSV=$(row r-clean READY "$OLD" 1 0.5 '' none)
cycles 3
chk "a fully-gated aging row lands on the runner owner" \
    "$(count_notified queue-aging-dispatchable)" "1"
chk_contains "the runner class names the runner as owner" "$(alarm_log)" "OWNER: workerpool-runner"

# ---- 4d. GATE PROPERTY (b): ONCE ON STATE CHANGE, not once per tick --------
# This is the whole point of R9. Twenty cycles of an unchanged condition is ONE
# notification. The rest are suppressed by the channel, which this suite's fake
# models faithfully.
reset_all
FIX_TSV=$(row r-unscreened READY "$OLD" 0 0.5 '' none)
cycles 20
chk "20 cycles of an unchanged refusal -> exactly ONE notification" \
    "$(count_notified queue-aging-unscreened)" "1"
chk "the other 17 raises were SUPPRESSED, not re-notified" \
    "$(alarm_log | grep -c '^SUPPRESSED queue-aging-unscreened')" "17"
chk "and nothing was cleared while the condition held" \
    "$(alarm_log | grep -c '^CLEARED')" "0"

# The state CHANGING back is itself news, exactly once, and only after the
# condition has been absent for PERSIST_CYCLES (hysteresis: one unlucky sample
# must not page a RESOLVED that the next cycle un-resolves).
FIX_TSV=$(row r-unscreened READY "$NEW" 0 0.5 '' none)     # the row got refreshed
cycles 2
chk "not cleared before the absence persists" \
    "$(alarm_log | grep -c '^CLEARED queue-aging-unscreened')" "0"
cycles 1
chk "cleared exactly once when the condition genuinely goes away" \
    "$(alarm_log | grep -c '^CLEARED queue-aging-unscreened')" "1"
cycles 5
chk "and not cleared again on every subsequent tick" \
    "$(alarm_log | grep -c '^CLEARED queue-aging-unscreened')" "1"

# ---- 4e. capacity is part of the condition ---------------------------------
# A deep queue with every worker slot occupied is a fleet WORKING. Paging for it
# is the cry-wolf failure that trains an operator to ignore the channel.
reset_all
FIX_TSV=$(printf '%s\n%s\n%s\n%s\n%s' \
    "$(row r-aged READY   "$OLD" 0 0.5 '' none)" \
    "$(row w1 RUNNING "$NEW" 1 0.5 '' none)" \
    "$(row w2 RUNNING "$NEW" 1 0.5 '' none)" \
    "$(row w3 CLAIMED "$NEW" 1 0.5 '' none)" \
    "$(row w4 ASSIGNED "$NEW" 1 0.5 '' none)")
cycles 6; out="$LAST_OUT"
chk "capacity full -> aged rows are expected, not an anomaly" "$FW_CAPACITY_FREE" "0"
chk_lacks "COMPLIANT: no QUEUE-AGING finding while every slot is busy" "$out" "QUEUE-AGING"
chk "COMPLIANT: no alarm while every slot is busy" "$(alarm_log | grep -c NOTIFIED)" "0"

# ---- 4f. an UNREADABLE queue is not an empty one ---------------------------
# The fail-open this whole file exists to refuse: an empty read would resolve
# every aging alarm and report a clean queue.
reset_all
FIX_TSV=$(row r-unscreened READY "$OLD" 0 0.5 '' none)
cycles 4
chk "precondition: the aging alarm is active" "$(count_notified queue-aging-unscreened)" "1"
FIX_TSV_OK=1                                     # queue unreadable from here
cycles 6; out="$LAST_OUT"
chk_contains "an unreadable queue is REPORTED" "$out" "QUEUE-UNREADABLE"
chk "an unreadable queue never CLEARS an aging alarm" \
    "$(alarm_log | grep -c '^CLEARED')" "0"
chk "an unreadable queue never RAISES a new aging alarm" \
    "$(alarm_log | grep -c '^NOTIFIED queue-aging')" "1"
chk "unreadable queue -> not an ok verdict" "$FW_VERDICT" "stall"
FIX_TSV_OK=0

# An unreadable ALARM CHANNEL is likewise not a quiet one: nothing is cleared.
reset_all
FIX_TSV=$(row r-unscreened READY "$OLD" 0 0.5 '' none)
cycles 4
FIX_TSV=$(row r-unscreened READY "$NEW" 0 0.5 '' none)
FAKE_ALARM_READABLE=1
cycles 6
chk "unreadable alarm state clears nothing" "$(alarm_log | grep -c '^CLEARED')" "0"
chk_contains "unreadable alarm state is REPORTED" \
    "$(printf '%s\n' ${FW_OBSERVATIONS[@]+"${FW_OBSERVATIONS[@]}"})" "ALARM-STATE-UNREADABLE"
FAKE_ALARM_READABLE=0

# ---- 4g. the clear sweep touches ONLY this script's own keys ---------------
# The daemon (P0-2), the supervisors and the operator all use the same channel.
# A sweep that resolved a key it does not own would silently un-page a real
# emergency.
reset_all
FAKE_ACTIVE[fleet-absent]="raised by the daemon, not by fleet_watch"
FAKE_ACTIVE[bus-supervisor-dead]="raised by a supervisor"
FIX_TSV=$(row q-fresh READY "$NEW" 1 0.5 '' none)
cycles 8
chk "a foreign alarm key is left ACTIVE" "${FAKE_ACTIVE[fleet-absent]:+present}" "present"
chk "a second foreign key is left ACTIVE" "${FAKE_ACTIVE[bus-supervisor-dead]:+present}" "present"
chk "nothing foreign was cleared" "$(alarm_log | grep -c '^CLEARED')" "0"

# ---- 4h. the first-cycle lie ----------------------------------------------
# Cycle 1 with compute ALREADY idle. The pre-production version logged
# "ok — no stalls, compute in use" here, because persistence had not accumulated.
reset_all
FIX_GPU='{"card0":{"GPU use (%)":"0","GPU Memory Allocated (VRAM%)":"0"}}'
FIX_REGIONS=$'  q0  free   \n  q1  free   \n  q2  free   \n  q3  free   '
FIX_TSV=$(row q-cpu READY "$NEW" 1 0.5 '' cpu)
fw_run_cycle
chk "cycle 1 verdict is 'warming', not 'ok'" "$FW_VERDICT" "warming"
chk_contains "cycle 1 says nothing is asserted yet" "$FW_SUMMARY" "NOTHING is asserted yet"
chk_contains "cycle 1 reports the compute reading honestly" "$FW_SUMMARY" "compute=idle"
chk "cycle 1 raises nothing" "$(alarm_log | grep -c NOTIFIED)" "0"
FIX_GPU='{"card0":{"GPU use (%)":"55","GPU Memory Allocated (VRAM%)":"71"}}'
FIX_REGIONS=$'  q0  HELD   bench\n  q1  free   \n  q2  free   \n  q3  free   '

# ---- 4i. PANE TEXT IS NEVER A TRIGGER (D8) ---------------------------------
# `fw_capture_pane` is overridden above to return a loud string. With evidence
# capture OFF (the production default) it must not be called at all, and no
# finding, verdict or alarm may contain a byte of it under ANY setting.
reset_all
FIX_TSV=$(row r-unscreened READY "$OLD" 0 0.5 '' none)
cycles 4; out="$LAST_OUT"
chk_lacks "no finding contains pane text" "$out" "PANE TEXT MUST NEVER"
chk_lacks "no alarm contains pane text (evidence off)" "$(alarm_log)" "PANE TEXT MUST NEVER"
# Turned ON, the pane tail may appear ONLY inside an alarm's evidence, and only
# on an alarm some other signal already decided to raise — clearly labelled.
reset_all
EVIDENCE_PANES="console"
ev=$(fw_evidence_json k v)
chk_contains "evidence capture is clearly labelled when enabled" "$ev" "EVIDENCE ONLY, NOT A TRIGGER"
EVIDENCE_PANES=""
ev=$(fw_evidence_json k v)
chk_lacks "evidence capture is OFF by default" "$ev" "PANE TEXT MUST NEVER"

# =============================================================================
# 5. THE LOG LINES OTHER TOOLS GREP
#
# The coordinator's Monitor keys on the "STALL REPORT" header and the two-space
# indent; `session_bus.py:_print_fleet_watch_occupancy` greps this file for a
# line containing COMPUTE-IDLE. Both spellings are load-bearing.
# =============================================================================
printf '\n[5] log shape\n'

reset_all
FIX_TSV=$(row r-unscreened READY "$OLD" 0 0.5 '' none)
: > "$FLEET_WATCH_LOG"
for i in 1 2 3; do fw_run_cycle; fw_emit; done
logged=$(cat "$FLEET_WATCH_LOG")
chk_contains "log keeps the STALL REPORT header" "$logged" "STALL REPORT"
chk_contains "log indents findings by two spaces" "$logged" "  QUEUE-AGING unscreened"

reset_all
FIX_GPU='{"card0":{"GPU use (%)":"0","GPU Memory Allocated (VRAM%)":"0"}}'
FIX_REGIONS=$'  q0  free   \n  q1  free   \n  q2  free   \n  q3  free   '
FIX_TSV=""
: > "$FLEET_WATCH_LOG"
for i in 1 2 3 4; do fw_run_cycle; fw_emit; done
logged=$(cat "$FLEET_WATCH_LOG")
chk_contains "the COMPUTE-IDLE token still reaches the log on a quiet night" "$logged" "COMPUTE-IDLE"
FIX_GPU='{"card0":{"GPU use (%)":"55","GPU Memory Allocated (VRAM%)":"71"}}'
FIX_REGIONS=$'  q0  HELD   bench\n  q1  free   \n  q2  free   \n  q3  free   '

# A task_id holding a backslash escape must reach the log LITERALLY. The
# pre-production version pushed findings through printf '%b'.
reset_all
FIX_TSV=$(row 'C:\new\table' READY "$OLD" 0 0.5 '' none)
: > "$FLEET_WATCH_LOG"
for i in 1 2 3; do fw_run_cycle; fw_emit; done
logged=$(cat "$FLEET_WATCH_LOG")
chk_contains "backslashes in a task_id are not re-interpreted" "$logged" 'C:\new\table'
chk "no stray newline injected by an escape" "$(grep -c 'QUEUE-AGING unscreened' "$FLEET_WATCH_LOG")" "1"

# =============================================================================
printf '\n=========================================\n'
printf 'fleet_watch self-test: %d passed, %d failed\n' "$PASS" "$FAIL"
if [ "$FAIL" -gt 0 ]; then
    printf 'failed cases:\n'
    printf '  - %s\n' ${FAILED_NAMES[@]+"${FAILED_NAMES[@]}"}
    exit 1
fi
exit 0
