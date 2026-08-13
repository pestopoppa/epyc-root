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
# HOW IT DRIVES THE REAL CODE. `fleet_watch.sh` is sourceable as a library (it
# returns before its dispatch block when `$0` differs from `$BASH_SOURCE`), and
# every function that touches the outside world is isolated in one probe layer.
# The suite sources the script and REDEFINES that layer to serve fixtures, so
# the classifiers, the persistence machine and the verdict logic all run as
# production code — with no live tmux, no GPU, no adapter and no roster.
#
# NOTHING HERE TOUCHES THE LIVE FLEET. No tmux command is issued (the tmux-
# facing functions are overridden before any cycle runs), no process is signalled,
# no bus file is written, and LOG points into a per-run mktemp directory.
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
export FLEET_WATCH_IDLE_QUIET_S=120
export FLEET_WATCH_AGENTS="mainA mainB"
export FLEET_WATCH_SESSION="test-session-does-not-exist"
export FLEET_WATCH_LOCK="$TMP/lock"

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

NBSP=$'\xc2\xa0'

# =============================================================================
# 1. COMPOSER CLASSIFICATION
#
# Fixtures are the REAL rows, captured read-only from the live panes at 10:5xZ
# 2026-08-12 and byte-verified: Claude renders U+276F + U+00A0, Codex U+203A +
# an ordinary space followed by a greyed placeholder.
# =============================================================================
printf '\n[1] composer classification\n'

out=$(fw_composer_pending "❯${NBSP}"); rc=$?
chk "claude empty composer -> no pending text" "${rc}:${out}" "0:"

out=$(fw_composer_pending "❯${NBSP}report when the three land"); rc=$?
chk "claude queued text -> pending text returned" "${rc}:${out}" "0:report when the three land"

out=$(fw_composer_pending "❱ older glyph text"); rc=$?
chk "older claude glyph still recognised" "${rc}:${out}" "0:older glyph text"

# THE CODEX PLACEHOLDER. An empty Codex composer RENDERS TEXT. Treating it as
# pending input parks a permanent false STUCK-INPUT on the codex main, which is
# precisely the cry-wolf failure the persistence rule exists to prevent.
out=$(fw_composer_pending "› Write tests for @filename"); rc=$?
chk "codex placeholder -> NOT pending (compliant path)" "${rc}:${out}" "0:"

out=$(fw_composer_pending "› run the full BGE sweep"); rc=$?
chk "codex real text -> pending text returned" "${rc}:${out}" "0:run the full BGE sweep"

# A row that is not a composer row must be UNKNOWN (rc 1), never "empty". The
# pre-production version grepped the whole pane and took the last glyph match,
# so a TRANSCRIPT line answered for the composer.
out=$(fw_composer_pending "  some transcript line about ❯ quoting"); rc=$?
chk "non-composer row -> UNKNOWN, not 'empty'" "$rc" "1"

out=$(fw_composer_pending "❯${NBSP}   spaced   "); rc=$?
chk "surrounding whitespace stripped" "${rc}:${out}" "0:spaced"

# =============================================================================
# 2. PANE MARKERS + DRIFT RECOGNITION
# =============================================================================
printf '\n[2] pane markers\n'

BUSY_PANE=$'some output\n  ⏵⏵ auto mode on (shift+tab to cycle) · esc to interrupt · ↓ 1 agent'
SUBAGENT_PANE=$'  ● main\n  ◯ general-purpose  Doing a thing   3m 22s\n  ⏵⏵ auto mode on'
CODEX_BUSY_PANE=$'  gpt-5.6-sol high · /workspace · Main [default]        Pursuing goal (1d 12h)'
IDLE_PANE=$'transcript line\n\n❯'"$NBSP"
GARBAGE_PANE=$'▓▒░ some entirely new TUI chrome ░▒▓\nnothing we know about'

fw_pane_busy "$BUSY_PANE";     chk "busy marker: esc to interrupt" "$?" "0"
fw_pane_busy "$SUBAGENT_PANE"; chk "busy marker: live subagent row" "$?" "0"
fw_pane_busy "$CODEX_BUSY_PANE"; chk "busy marker: codex Pursuing goal" "$?" "0"
fw_pane_busy "$IDLE_PANE";     chk "settled prompt is NOT busy" "$?" "1"

fw_pane_recognised "$IDLE_PANE";    chk "idle pane still RECOGNISED (glyph present)" "$?" "0"
fw_pane_recognised "$GARBAGE_PANE"; chk "drifted TUI is NOT recognised" "$?" "1"

# =============================================================================
# 3. LIVENESS — the three-state rule
# =============================================================================
printf '\n[3] liveness classification\n'

chk "runtime active beats a long quiet window" "$(fw_classify_liveness active 9999 1 false)" "busy"
chk "runtime idle is authoritative"            "$(fw_classify_liveness idle 0 0 false)"      "idle"
chk "no runtime + busy marker -> busy"         "$(fw_classify_liveness null 9999 0 false)"   "busy"
chk "no runtime + quiet + no marker -> idle"   "$(fw_classify_liveness null 9999 1 false)"   "idle"
chk "no runtime + recently active -> busy"     "$(fw_classify_liveness null 5 1 false)"      "busy"
chk "float quiet compares correctly"           "$(fw_classify_liveness null 243.3 1 false)"  "idle"
chk "float below threshold -> busy"            "$(fw_classify_liveness null 119.9 1 false)"  "busy"
# The fail-closed cases. An unreadable instrument is NOT an idle one.
chk "unreadable quiet -> unknown, NOT idle"    "$(fw_classify_liveness null null 1 false)"   "unknown"
chk "empty quiet -> unknown, NOT idle"         "$(fw_classify_liveness null '' 1 false)"     "unknown"
chk "unreadable pane -> unknown, NOT idle"     "$(fw_classify_liveness null 9999 2 false)"   "unknown"
chk "dead pane reported as dead"               "$(fw_classify_liveness null 9999 1 true)"    "dead"

# =============================================================================
# 4. COMPUTE — three states, and VRAM independent of GPU%
# =============================================================================
printf '\n[4] compute classification\n'

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
# 5. FULL CYCLES against fixtures — persistence, verdicts, compliant paths
#
# The probe layer is replaced below. Everything downstream is production code.
# =============================================================================
printf '\n[5] full-cycle behaviour\n'

declare -A FIX_PANE FIX_CY FIX_PROBE
FIX_SESSION_OK=0
FIX_GPU='{"card0":{"GPU use (%)":"55","GPU Memory Allocated (VRAM%)":"71"}}'
FIX_REGIONS=$'  q0  HELD   bench\n  q1  free   \n  q2  free   \n  q3  free   '

fw_session_exists() { return "$FIX_SESSION_OK"; }
fw_capture_pane()   { printf '%s' "${FIX_PANE[$1]:-}"; }
fw_cursor_row()     { printf '%s' "${FIX_CY[$1]:-}"; }
fw_probe_json()     { [ -n "${FIX_PROBE[$1]:-}" ] || return 1; printf '%s' "${FIX_PROBE[$1]}"; }
fw_gpu_json()       { [ -n "$FIX_GPU" ] || return 1; printf '%s' "$FIX_GPU"; }
fw_regions_text()   { [ -n "$FIX_REGIONS" ] || return 1; printf '%s' "$FIX_REGIONS"; }

probe_json() {  # probe_json <runtime|null> <quiet> <dead>
    printf '{"runtime_state":%s,"window_quiet_for_s":%s,"pane_dead":%s}' \
        "$([ "$1" = null ] && printf 'null' || printf '"%s"' "$1")" "$2" "$3"
}

# A pane holding queued text, with the composer on row 3 (0-based cursor_y 2).
pane_with_composer() { printf 'transcript\n%s\n%s' "$2" "❯${NBSP}$1"; }

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

# ---- 5a. compliant path: a busy fleet on busy compute reports NOTHING -------
fw_reset_state
FIX_PANE[mainA]=$(pane_with_composer "" "  ⏵⏵ auto mode on · esc to interrupt")
FIX_PANE[mainB]=$(pane_with_composer "" "  ◯ general-purpose  working   1m")
FIX_CY[mainA]=2; FIX_CY[mainB]=2
FIX_PROBE[mainA]=$(probe_json null 1.2 false)
FIX_PROBE[mainB]=$(probe_json null 0.4 false)
cycles 8; out="$LAST_OUT"
chk "COMPLIANT: busy fleet, busy compute -> no findings at all" "$(printf '%s' "$out" | tr -d '\n')" ""
chk "COMPLIANT: verdict is ok"        "$FW_VERDICT" "ok"
chk_contains "COMPLIANT: summary names what was determined" "$FW_SUMMARY" "2/2 mains determined active"

# ---- 5b. STUCK-INPUT: fires only on persistence, and only on stable text ----
fw_reset_state
FIX_PANE[mainA]=$(pane_with_composer "push it" "  ⏵⏵ auto mode on · esc to interrupt")
cycles 2; out="$LAST_OUT"
chk_lacks "STUCK-INPUT does not fire before PERSIST_CYCLES" "$out" "STUCK-INPUT"
cycles 1; out="$LAST_OUT"
chk_contains "STUCK-INPUT fires at PERSIST_CYCLES" "$out" "STUCK-INPUT mainA"
chk_contains "STUCK-INPUT quotes the pending text" "$out" "'push it'"

# A main that keeps CHANGING its composer is typing, not stalled. Alarming here
# is the cry-wolf failure: three mains fired within 90s of a routine dispatch
# and every one had submitted by the next look.
fw_reset_state
for i in 1 2 3 4 5; do
    FIX_PANE[mainA]=$(pane_with_composer "draft revision $i" "  esc to interrupt")
    fw_run_cycle
done
out=$(printf '%s\n' ${FW_FINDINGS[@]+"${FW_FINDINGS[@]}"})
chk_lacks "COMPLIANT: text that CHANGES each cycle never fires" "$out" "STUCK-INPUT"

# Submission clears the counter.
fw_reset_state
FIX_PANE[mainA]=$(pane_with_composer "push it" "  esc to interrupt")
fw_run_cycle; fw_run_cycle
FIX_PANE[mainA]=$(pane_with_composer "" "  esc to interrupt")
cycles 3; out="$LAST_OUT"
chk_lacks "COMPLIANT: submitting clears the STUCK-INPUT counter" "$out" "STUCK-INPUT"

# An unreadable composer must RESET the counter, not merely stop advancing it.
# The claim STUCK-INPUT makes is "this exact text has sat unsubmitted for N
# CONSECUTIVE cycles"; a cycle that could not read the composer cannot support
# it, so the run must start over. Note the shape of this case: two readable
# cycles, ONE unreadable, then a readable one carrying the SAME text. A version
# that merely skips the unreadable cycle reaches 3 here and fires on a run that
# was never actually consecutive — which is why an "assert no fire while
# unreadable" case is not enough to pin this down (it passed against the mutant).
fw_reset_state
FIX_PANE[mainA]=$(pane_with_composer "push it" "  esc to interrupt")
fw_run_cycle; fw_run_cycle              # counter reaches 2
FIX_CY[mainA]=""                        # cursor unreadable -> composer UNKNOWN
fw_run_cycle                            # must reset to 0
FIX_CY[mainA]=2
cycles 1; out="$LAST_OUT"               # same text again -> must be back at 1
chk_lacks "an unreadable composer RESETS the run, not just pauses it" "$out" "STUCK-INPUT"
# and it must still fire once a genuinely consecutive run accumulates
cycles 2; out="$LAST_OUT"
chk_contains "a fresh consecutive run still fires" "$out" "STUCK-INPUT mainA"

# ---- 5c. IDLE-CANDIDATE ----------------------------------------------------
fw_reset_state
FIX_PANE[mainA]=$(pane_with_composer "" "  ⏵⏵ auto mode on")     # no busy marker
FIX_PROBE[mainA]=$(probe_json null 400 false)                     # quiet 400s
cycles 3; out="$LAST_OUT"
chk_contains "IDLE-CANDIDATE fires on a persistently quiet main" "$out" "IDLE-CANDIDATE mainA"
chk_contains "IDLE-CANDIDATE is hedged, never asserted" "$out" "may be compacting"

# The compacting case: the operator's correction. A busy marker vetoes idle.
fw_reset_state
FIX_PANE[mainA]=$(pane_with_composer "" "  ⏵⏵ esc to interrupt")
FIX_PROBE[mainA]=$(probe_json null 400 false)
cycles 5; out="$LAST_OUT"
chk_lacks "COMPLIANT: busy marker vetoes idle despite a quiet window" "$out" "IDLE-CANDIDATE"

# The runtime is authoritative when it has an answer.
fw_reset_state
FIX_PANE[mainA]=$(pane_with_composer "" "  ⏵⏵ auto mode on")
FIX_PROBE[mainA]=$(probe_json active 9999 false)
cycles 5; out="$LAST_OUT"
chk_lacks "COMPLIANT: runtime ACTIVE vetoes a quiet window" "$out" "IDLE-CANDIDATE"

fw_reset_state
FIX_PROBE[mainA]=$(probe_json idle 0 false)
cycles 3; out="$LAST_OUT"
chk_contains "runtime IDLE is reported as authoritative" "$out" "authoritative"

# No probe at all + no marker + no quiet reading -> UNKNOWN, never idle.
fw_reset_state
FIX_PANE[mainA]=$(pane_with_composer "" "  ⏵⏵ auto mode on")
FIX_PROBE[mainA]=""
cycles 6; out="$LAST_OUT"
chk_lacks "no readable liveness signal -> never IDLE-CANDIDATE" "$out" "IDLE-CANDIDATE"
chk "unreadable liveness -> degraded verdict, not ok" "$FW_VERDICT" "degraded"
FIX_PROBE[mainA]=$(probe_json null 1.0 false)
FIX_PROBE[mainB]=$(probe_json null 0.4 false)

# ---- 5d. COMPUTE-IDLE ------------------------------------------------------
fw_reset_state
FIX_PANE[mainA]=$(pane_with_composer "" "  esc to interrupt")
FIX_PANE[mainB]=$(pane_with_composer "" "  esc to interrupt")
FIX_GPU='{"card0":{"GPU use (%)":"0","GPU Memory Allocated (VRAM%)":"0"}}'
FIX_REGIONS=$'  q0  free   \n  q1  free   \n  q2  free   \n  q3  free   '
cycles 2; out="$LAST_OUT"
chk_lacks "COMPUTE-IDLE does not fire on a single sample" "$out" "COMPUTE-IDLE"
cycles 1; out="$LAST_OUT"
chk_contains "COMPUTE-IDLE fires on persistence" "$out" "COMPUTE-IDLE"
chk_contains "GPU-IDLE is detected independently" "$out" "GPU-IDLE"
chk_contains "CPU-IDLE is detected independently" "$out" "CPU-IDLE"

# CPU work must not hide a persistently idle GPU.
fw_reset_state
FIX_GPU='{"card0":{"GPU use (%)":"0","GPU Memory Allocated (VRAM%)":"0"}}'
FIX_REGIONS=$'  q0  HELD   worker\n  q1  free   \n  q2  free   \n  q3  free   '
cycles 3; out="$LAST_OUT"
chk_contains "busy CPU does not hide GPU-IDLE" "$out" "GPU-IDLE"
chk_lacks "busy CPU suppresses CPU-IDLE" "$out" "CPU-IDLE"
chk_lacks "partially busy compute is not combined COMPUTE-IDLE" "$out" "COMPUTE-IDLE"

# GPU work must not hide persistently idle CPU regions.
fw_reset_state
FIX_GPU='{"card0":{"GPU use (%)":"55","GPU Memory Allocated (VRAM%)":"71"}}'
FIX_REGIONS=$'  q0  free   \n  q1  free   \n  q2  free   \n  q3  free   '
cycles 3; out="$LAST_OUT"
chk_contains "busy GPU does not hide CPU-IDLE" "$out" "CPU-IDLE"
chk_lacks "busy GPU suppresses GPU-IDLE" "$out" "GPU-IDLE"
chk_lacks "partially busy compute is not combined COMPUTE-IDLE (GPU)" "$out" "COMPUTE-IDLE"

# THE llama-bench GAP. The card legitimately reads 0%/0% between probes inside a
# perfectly healthy sweep. One busy sample must reset the counter.
fw_reset_state
for pattern in idle idle busy idle idle busy idle idle; do
    if [ "$pattern" = busy ]; then
        FIX_GPU='{"card0":{"GPU use (%)":"98","GPU Memory Allocated (VRAM%)":"71"}}'
    else
        FIX_GPU='{"card0":{"GPU use (%)":"0","GPU Memory Allocated (VRAM%)":"0"}}'
    fi
    fw_run_cycle
done
out=$(printf '%s\n' ${FW_FINDINGS[@]+"${FW_FINDINGS[@]}"})
chk_lacks "COMPLIANT: a sweep's inter-probe gaps never fire COMPUTE-IDLE" "$out" "COMPUTE-IDLE"
chk_lacks "COMPLIANT: a sweep's inter-probe gaps never fire GPU-IDLE" "$out" "GPU-IDLE"

# An unreadable GPU is not an idle GPU.
fw_reset_state
FIX_GPU=""
cycles 6; out="$LAST_OUT"
chk_lacks "unreadable rocm-smi never fires COMPUTE-IDLE" "$out" "COMPUTE-IDLE"
chk_lacks "unreadable rocm-smi never fires GPU-IDLE" "$out" "GPU-IDLE"
chk_contains "known-idle CPU remains reportable with unreadable GPU" "$out" "CPU-IDLE"
chk "known CPU stall takes precedence while GPU remains unknown" "$FW_VERDICT" "stall"
FIX_GPU='{"card0":{"GPU use (%)":"55","GPU Memory Allocated (VRAM%)":"71"}}'

# ---- 5e. THE FIRST-CYCLE LIE ----------------------------------------------
# Cycle 1 with compute ALREADY idle. The pre-production version logged
# "ok — no stalls, compute in use" here, because persistence had not accumulated.
fw_reset_state
FIX_GPU='{"card0":{"GPU use (%)":"0","GPU Memory Allocated (VRAM%)":"0"}}'
FIX_REGIONS=$'  q0  free   \n  q1  free   \n  q2  free   \n  q3  free   '
fw_run_cycle
chk "cycle 1 verdict is 'warming', not 'ok'" "$FW_VERDICT" "warming"
chk_lacks "cycle 1 never claims compute is in use" "$FW_SUMMARY" "compute in use"
chk_contains "cycle 1 says nothing is asserted yet" "$FW_SUMMARY" "NOTHING is asserted yet"
chk_contains "cycle 1 reports the compute reading honestly" "$FW_SUMMARY" "compute=idle"
FIX_GPU='{"card0":{"GPU use (%)":"55","GPU Memory Allocated (VRAM%)":"71"}}'
FIX_REGIONS=$'  q0  HELD   bench\n  q1  free   \n  q2  free   \n  q3  free   '

# ---- 5f. absent session and unreadable panes -------------------------------
fw_reset_state
FIX_SESSION_OK=1                       # has-session fails
cycles 1; out="$LAST_OUT"
chk_contains "absent tmux session is REPORTED" "$out" "FLEET-UNREADABLE"
chk "absent session verdict is not ok" "$FW_VERDICT" "unreadable"
FIX_SESSION_OK=0

fw_reset_state
FIX_PANE[mainA]=""                     # capture-pane returns nothing
cycles 4; out="$LAST_OUT"
chk_contains "unreadable pane is REPORTED" "$out" "PANE-UNREADABLE mainA"
chk_lacks "unreadable pane is never called idle" "$out" "IDLE-CANDIDATE mainA"
FIX_PANE[mainA]=$(pane_with_composer "" "  esc to interrupt")

fw_reset_state
FIX_PROBE[mainA]=$(probe_json null 1.0 true)     # pane_dead
cycles 1; out="$LAST_OUT"
chk_contains "dead pane is reported" "$out" "PANE-DEAD mainA"
FIX_PROBE[mainA]=$(probe_json null 1.0 false)

# ---- 5g. DETECTOR-BLIND ----------------------------------------------------
# A TUI release renames every marker. The honest report is blindness, NOT a
# fleet-wide idle claim built on a vocabulary that no longer matches anything.
fw_reset_state
FIX_PANE[mainA]="$GARBAGE_PANE"
FIX_PANE[mainB]="$GARBAGE_PANE"
FIX_PROBE[mainA]=$(probe_json null 9999 false)
FIX_PROBE[mainB]=$(probe_json null 9999 false)
cycles 4; out="$LAST_OUT"
chk_contains "drifted markers -> DETECTOR-BLIND" "$out" "DETECTOR-BLIND"
chk_lacks "DETECTOR-BLIND suppresses the idle claims it cannot support" "$out" "IDLE-CANDIDATE"

# ---- 5h. a roster id containing a hyphen -----------------------------------
# `printf -v prev_coordinator-agent` is not a valid assignment; the
# pre-production version would have raised a bad-substitution error mid-loop.
fw_reset_state
saved_agents="$AGENTS"; AGENTS="coordinator-agent"
FIX_PANE[coordinator-agent]=$(pane_with_composer "hello" "  esc to interrupt")
FIX_CY[coordinator-agent]=2
FIX_PROBE[coordinator-agent]=$(probe_json null 1.0 false)
cycles 3 2>"$TMP/err.txt"; out="$LAST_OUT$(cat "$TMP/err.txt")"
chk_contains "hyphenated roster id works" "$out" "STUCK-INPUT coordinator-agent"
chk_lacks "hyphenated roster id raises no bad substitution" "$out" "bad substitution"
AGENTS="$saved_agents"

# ---- 5i. the log line the coordinator's Monitor greps ----------------------
fw_reset_state
FIX_PANE[mainA]=$(pane_with_composer "push it" "  esc to interrupt")
FIX_PANE[mainB]=$(pane_with_composer "" "  esc to interrupt")
: > "$FLEET_WATCH_LOG"
for i in 1 2 3; do fw_run_cycle; fw_emit; done
logged=$(cat "$FLEET_WATCH_LOG")
chk_contains "log keeps the STALL REPORT header" "$logged" "STALL REPORT"
chk_contains "log indents findings by two spaces" "$logged" "  STUCK-INPUT mainA"

# A composer holding a backslash escape must reach the log LITERALLY. The
# pre-production version pushed findings through printf '%b'.
fw_reset_state
FIX_PANE[mainA]=$(pane_with_composer 'check C:\new\table path' "  esc to interrupt")
: > "$FLEET_WATCH_LOG"
for i in 1 2 3; do fw_run_cycle; fw_emit; done
logged=$(cat "$FLEET_WATCH_LOG")
chk_contains "backslashes in composer text are not re-interpreted" "$logged" 'C:\new\table'
chk "no stray newline injected by an escape" "$(grep -c 'STUCK-INPUT' "$FLEET_WATCH_LOG")" "1"

# =============================================================================
printf '\n=========================================\n'
printf 'fleet_watch self-test: %d passed, %d failed\n' "$PASS" "$FAIL"
if [ "$FAIL" -gt 0 ]; then
    printf 'failed cases:\n'
    printf '  - %s\n' ${FAILED_NAMES[@]+"${FAILED_NAMES[@]}"}
    exit 1
fi
exit 0
