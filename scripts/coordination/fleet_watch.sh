#!/bin/bash
# =============================================================================
# fleet_watch.sh — hardware- and queue-grounded stall detector (P3-3)
# =============================================================================
#
# WHY THIS EXISTS, AND WHY IT WAS REWRITTEN.
#
# The first version watched PANES. It read each main's composer row out of
# `tmux capture-pane` and reported unsubmitted text as STUCK-INPUT. Measured over
# its production life: 2,654 STUCK-INPUT reports, of which **2,499 (94%) were the
# agent CLI's own empty-composer PLACEHOLDER HINT TEXT** — "Improve documentation
# in @filename", "Find and fix a bug in @filename" and friends — reported as
# unsubmitted operator input for up to 10.6 hours at a stretch. The placeholder
# vocabulary is a calibration against a vendor TUI release, it rots, and every
# time it rots the detector manufactures a fleet-wide stall out of an empty
# composer. That is not a tuning problem; it is the wrong instrument.
#
# So under the loop-owned-fleet restructure (P3-3, D8) **the machine never reads
# a pane to make a decision.** Worker panes are visible because the OPERATOR may
# want to watch and steer them; machine authority over pane text is the defect
# being deleted. What replaces it is two signals that are facts about the world
# rather than facts about a UI string:
#
#   COMPUTE-IDLE  — rocm-smi + CPU region claims. Hardware. This is how an idle
#                   GPU with compute-gated work queued becomes visible at all.
#   QUEUE-AGING   — READY rows on the bus that have aged past a threshold while
#                   worker capacity is free. Bus files. This is how a queue that
#                   nobody is draining becomes visible without asking any pane
#                   whether it "looks busy".
#
# THE REFUSAL RULE (R9). A row REFUSED by a gate is not a row that was handled.
# Measured: 9,219 identical `dispatch-refused` advisory rows repeating one
# refusal that nobody ever acted on, because a refusal that only re-states itself
# every tick is indistinguishable from silence. Therefore:
#   * a refused / parked row COUNTS AS AGING — the gate refusing it is exactly
#     why it is still sitting there;
#   * every refusal class has a NAMED OWNER and a routed FIX, carried in the
#     alarm body;
#   * the alarm emits ONCE ON STATE CHANGE, never once per tick — enforced by
#     `alarm_channel.py`, whose whole contract is emit-once. This file adds NO
#     dedupe layer of its own; it calls raise/clear honestly and lets the channel
#     decide what is news.
#
# DETECT AND REPORT ONLY — unchanged, and now with fewer ways to violate it.
# This never sends keys, never writes the bus queue, never kills anything, never
# writes another agent's file. Its ONLY side effects are: appending to its own
# log, and invoking `alarm_channel.py raise|clear`. Because it may not write a
# bus row, "routing a fix task" means the alarm body names the OWNER and the
# EXACT command that fixes the class — the routing is in the payload a human
# reads, not in a queue write this script is forbidden to make.
#
# Tests: scripts/coordination/tests/test_fleet_watch.sh (unit + fixture suite)
#        scripts/coordination/tests/test_fleet_watch_mutation.sh (proves the
#        suite fails when each detector is deliberately broken).
#
# -----------------------------------------------------------------------------
# THE FOUR RULES THAT SHAPE EVERY DETECTOR — do not "simplify" these away
# -----------------------------------------------------------------------------
#
# 1. PERSISTENCE, NOT PRESENCE, IN BOTH DIRECTIONS. A condition must hold for
#    PERSIST_CYCLES consecutive cycles before it is raised, AND be absent for
#    PERSIST_CYCLES consecutive cycles before it is cleared. The one-sided
#    version flaps: a single unlucky sample clears an alarm and the next one
#    re-raises it, which pages a human twice for nothing. `fw_track` /
#    `fw_is_on` / `fw_is_off` implement the hysteresis; a cycle that could not
#    READ a signal calls neither, freezing both counters (rule 2).
#
# 2. THREE STATES, NEVER TWO. Every probe answers busy / idle / UNKNOWN, and
#    UNKNOWN never counts as idle. An unreadable instrument is not an idle one.
#    The pre-production version collapsed a `rocm-smi` failure to `${gpu:-0}` =
#    "0%", so a host where rocm-smi was missing, renamed or merely slow would
#    have reported COMPUTE-IDLE forever. The same rule now governs the ALARM
#    plane: a domain whose state could not be read this cycle is excluded from
#    the clear sweep, so a blind cycle can neither raise nor resolve anything.
#
# 3. IDLE COMPUTE IS ONLY AN ALARM WHEN THERE IS COMPUTE-GATED WORK QUEUED.
#    An idle GPU at 04:00 with an empty queue is a well-run night, not a fault,
#    and paging for it is precisely how a fleet trains its operator to mute the
#    channel. The gate metric for this whole restructure is "ZERO alarms on
#    well-run nights", so the idle reading is still LOGGED (the coordinator's
#    boundary report greps the COMPUTE-IDLE line for occupancy) but it is only
#    ESCALATED when `gating != none` READY rows exist to run on that hardware.
#
# 4. PANE TEXT IS EVIDENCE FOR A HUMAN, NEVER A TRIGGER. `fw_capture_pane` still
#    exists and is still read-only, but it is called from exactly one place —
#    `fw_pane_evidence`, which attaches a clearly-labelled scrollback tail to an
#    alarm that some OTHER signal already decided to raise. It is OFF by default
#    (FLEET_WATCH_EVIDENCE_PANES is empty), so a production cycle issues no tmux
#    command at all. No classifier, no verdict and no alarm condition in this
#    file reads pane text; the mutation suite pins that.
#
# -----------------------------------------------------------------------------
# WHY `set -uo pipefail` AND DELIBERATELY NOT `-e`
# -----------------------------------------------------------------------------
# A monitor must SURVIVE a failing probe — that is its entire job. Under `-e`
# this process would exit the first time `rocm-smi` was busy, `grep` found no
# match (rc 1 is normal and expected throughout), or the bus was momentarily
# unreadable, and the fleet would then be unwatched with nothing in the log to
# say so. Every external call below is explicitly rc- and emptiness-checked and
# resolves to UNKNOWN on failure (rule 2). `-u` and `pipefail` are kept: they
# catch authoring mistakes without ending the process, because every variable
# read that can legitimately be unset uses `${x:-default}`.
#
# Usage:  fleet_watch.sh              # run the detector loop
#         fleet_watch.sh --once       # one cycle, print findings, RAISE NOTHING
#         fleet_watch.sh --selftest   # run the bundled test suite
# Sourcing this file defines the functions and runs nothing (the test seam).
# =============================================================================
set -uo pipefail

# ----------------------------------------------------------------------------
# Configuration. Every knob is env-overridable so the test suite can drive the
# real decision code without touching production defaults.
# ----------------------------------------------------------------------------
# Canonical roots come from ONE place (B2/B7, 2026-08-12). This file used to bake
# `/mnt/raid0/llm/epyc-root` into its log + lock and `/workspace` into its adapter
# path — three literals for two directories. Under worktree-per-main a copy of this
# script exists in every lane worktree, so a self-relative default would give each
# lane its own lock and its own log and the single-instance flock would stop being
# single. env.sh canonicalizes LOG_DIR/EPYC_BUS_ROOT from ANY worktree.
_FW_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${_FW_DIR}/../lib/env.sh"

LOG="${FLEET_WATCH_LOG:-${LOG_DIR}/fleet_watch.log}"
INTERVAL="${FLEET_WATCH_INTERVAL:-90}"
# Cycles a condition must persist before it is raised, and cycles it must be
# absent before it is cleared. Symmetric on purpose — see rule 1.
PERSIST_CYCLES="${FLEET_WATCH_PERSIST_CYCLES:-3}"
RL="${FLEET_WATCH_REGION_LOCK:-/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock}"
LOCK_FILE="${FLEET_WATCH_LOCK:-${LOG_DIR}/.fleet_watch.lock}"
MAX_LOG_BYTES="${FLEET_WATCH_MAX_LOG_BYTES:-5242880}"   # 5 MiB
LOG_KEEP="${FLEET_WATCH_LOG_KEEP:-3}"
MAX_TEXT_CHARS="${FLEET_WATCH_MAX_TEXT_CHARS:-70}"

# ---- the bus (queue-aging inputs) ------------------------------------------
# EPYC_BUS_ROOT is exported by env.sh and MUST resolve byte-identically to
# session_bus.py's get_bus_root(); do not re-derive it here.
BUS_ROOT="${FLEET_WATCH_BUS_ROOT:-${EPYC_BUS_ROOT}}"
QUEUE_FILE="${FLEET_WATCH_QUEUE_FILE:-${BUS_ROOT}/queue.jsonl}"
# How long a READY row may sit before it is AGING. 6h by default: long enough
# that a row picked up inside one working session never trips it, short enough
# that a row nobody touched overnight is reported by morning.
AGE_THRESHOLD_S="${FLEET_WATCH_AGE_THRESHOLD_S:-21600}"
# Worker-pool concurrency ceiling (D1: ≤4, ratified). `capacity free` means
# CAPACITY minus rows currently in flight. When every slot is occupied a deep
# queue is EXPECTED, not an anomaly, and nothing is raised.
CAPACITY="${FLEET_WATCH_CAPACITY:-4}"

# ---- the alarm channel ------------------------------------------------------
# P0-1. The ONE operator-reachable push mechanism. It already emits once on
# state change and keeps its own active-key state, so this file MUST NOT add a
# second dedupe layer on top: it calls raise while a condition holds and clear
# when the condition is known to be gone, and the channel decides what is news.
ALARM="${FLEET_WATCH_ALARM:-${_FW_DIR}/alarm_channel.py}"
# 1 = really invoke the channel; 0 = print what would be raised/cleared. `--once`
# forces 0 so a human running a diagnostic cannot resolve an alarm the loop owns.
ALARMS_ENABLED="${FLEET_WATCH_ALARMS:-1}"

# ---- human evidence only (rule 4) ------------------------------------------
# Space-separated tmux window names whose scrollback tail is attached to an
# alarm ALREADY DECIDED by hardware or queue state. EMPTY BY DEFAULT: a
# production cycle issues no tmux command at all. This is never a trigger.
EVIDENCE_PANES="${FLEET_WATCH_EVIDENCE_PANES:-}"
EVIDENCE_SESSION="${FLEET_WATCH_SESSION:-agent}"
EVIDENCE_LINES="${FLEET_WATCH_EVIDENCE_LINES:-12}"

# ----------------------------------------------------------------------------
# REFUSAL CLASSES AND THEIR OWNERS
#
# R9, the 9,219-refusal class. A refusal with no owner is a refusal nobody acts
# on, so the class table and the owner table are the SAME table, and a class
# without an owner is itself reported (see `fw_class_owner` returning rc 1 and
# the `queue-aging-unowned` key). Adding a new refusal class without an owner
# therefore fails LOUDLY instead of silently starving rows.
#
# The classes mirror the gates that actually refuse, in the order they refuse:
#   unscreened            dispatch_gate: no `screened_by` receipt
#   no-occupancy-estimate dispatch_gate: no usable expected_occupancy.est_h
#   premise-parked        premise_screener: parked stale/unknown (READY +
#                         `parked_reason`) — this class WINS over the two above
#                         because reaching the screener means the row already
#                         passed dispatch_gate inside worker_runner
#   dispatchable          NO gate refused it. It is aging with capacity free
#                         because nothing spawned — the runner-liveness question
#                         P3-4 makes the daemon's anomaly condition.
# ----------------------------------------------------------------------------
FW_CLASSES="premise-parked unscreened no-occupancy-estimate dispatchable"

fw_class_owner() {
    case "$1" in
        unscreened|no-occupancy-estimate|premise-parked) printf 'coordinator-agent' ;;
        dispatchable) printf 'workerpool-runner' ;;
        *) return 1 ;;
    esac
}

fw_class_fix() {
    case "$1" in
        unscreened) printf 'screen each row (scripts/coordination/backlog_row_check.py --row "<task_text>") and re-append it with a screened_by receipt, or dispatch it by hand' ;;
        no-occupancy-estimate) printf 'add expected_occupancy {est_h, basis} to each row and re-append it, or dispatch it by hand' ;;
        premise-parked) printf 're-verify each parked row premise against current reality, then re-screen it to READY or CANCEL it; the screener already filed a <task_id>-premise-fix row' ;;
        dispatchable) printf 'every gate passed and capacity is free, so nothing spawned: check runner liveness (workerpool roster row + exec:worker_runner endpoint + worker_runner.py) — this is the P3-4 anomaly condition' ;;
        *) return 1 ;;
    esac
}

# Every alarm key this script may raise. The clear sweep touches ONLY these, so
# it can never resolve an alarm raised by the daemon, a supervisor or a human.
FW_OWNED_KEYS="compute-idle-with-queued-work"
for _c in $FW_CLASSES; do FW_OWNED_KEYS="${FW_OWNED_KEYS} queue-aging-${_c}"; done
FW_OWNED_KEYS="${FW_OWNED_KEYS} queue-aging-unowned"
unset _c

FW_VERDICT=""
FW_SUMMARY=""

# ----------------------------------------------------------------------------
# Logging. Rotation is COPY-TRUNCATE, deliberately: the coordinator keeps a
# tail-style Monitor on this file, and renaming it out from under that Monitor
# would leave the coordinator following a deleted inode and reading nothing
# forever — the exact silent fail-open this file exists to prevent. Truncation
# in place is detected by tail, which resets and keeps following.
# ----------------------------------------------------------------------------
fw_log() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >> "$LOG"; }

fw_rotate_log_if_needed() {
    local size i
    size=$(stat -c %s "$LOG" 2>/dev/null) || return 0
    [ -n "$size" ] || return 0
    [ "$size" -gt "$MAX_LOG_BYTES" ] 2>/dev/null || return 0
    for ((i = LOG_KEEP - 1; i >= 1; i--)); do
        [ -f "${LOG}.${i}" ] && mv -f "${LOG}.${i}" "${LOG}.$((i + 1))" 2>/dev/null
    done
    cp -f "$LOG" "${LOG}.1" 2>/dev/null && : > "$LOG"
    fw_log "log rotated at ${size} bytes (keeping ${LOG_KEEP}); previous content in ${LOG}.1"
}

# `%s` only — NEVER `%b`. The pre-production version pushed findings through
# `printf '%b'`, so text containing a backslash escape was re-interpreted on the
# way to the log; its literal "GPU 0%%" was likewise a format escape with no
# format string to consume it, and logged as "0%%".
fw_sanitise() {
    printf '%s' "$1" | tr -d '\000-\010\013\014\016-\037\177' | cut -c "1-${MAX_TEXT_CHARS}"
}

# ============================================================================
# PROBES — the ONLY functions that touch the outside world.
#
# These are the test seam: the suite sources this file and redefines them, so
# every classifier, the persistence machine and the alarm decisions all run
# against synthetic fixtures with no live tmux, no GPU, no bus and no channel.
#
# Contract: print the reading on stdout and return 0, or return non-zero to mean
# UNKNOWN.
# ============================================================================

# One call for both metrics, and `--json` rather than screen-scraping: the
# pre-production version ran `grep -oP 'GPU use \(%\): \K[0-9]+'` against a
# banner-and-underline ASCII report that exists to be read by humans.
fw_gpu_json() {
    local out
    out=$(timeout 15 rocm-smi --showuse --showmemuse --json 2>/dev/null)
    [ -n "$out" ] || return 1
    printf '%s' "$out" | jq -e . >/dev/null 2>&1 || return 1
    printf '%s' "$out"
}

fw_regions_text() {
    local out
    out=$(timeout 15 "$RL" status 2>/dev/null) || return 1
    [ -n "$out" ] || return 1
    printf '%s' "$out"
}

# The queue, folded to ONE line per task_id (the LAST record wins — queue.jsonl
# is append-only and the latest append is the row's current state, the same fold
# session_bus.py applies).
#
# Output is one row per line, fields separated by US (U+001F, \x1f):
#     task_id | status | age_s | screened(1|0) | est_h | parked_reason | gating
#
# THE SEPARATOR IS NOT A TAB, and that is not a style choice. Tab is an IFS
# WHITESPACE character, so `while IFS=$'\t' read -r a b c` COLLAPSES runs of
# tabs and silently drops every empty field — a row with no occupancy estimate
# would shift `gating` into `parked_reason` and be classified `premise-parked`,
# routing a human to the wrong owner with a straight face. US is not IFS
# whitespace, so empty fields survive. Caught by the queue-scan cases in
# tests/test_fleet_watch.sh, which assert the class counts field by field.
#
# rc 1 = UNKNOWN. A missing/unreadable queue is NOT an empty queue: an empty
# queue would read as "nothing is aging, all clear" and silently resolve every
# aging alarm, which is the fail-open this file exists to refuse.
#
# NOTE: `age_s` is measured from the row's OWN `ts`, i.e. from the moment it
# last entered its current state. That is precisely why a REFUSED row ages: a
# refusal is written to advisory.jsonl, never back onto the row, so the row's
# `ts` does not move and the clock keeps running. A design that reset the clock
# on every refusal would render the 9,219-refusal class as a permanently fresh
# queue.
fw_queue_rows() {
    local out
    out=$(timeout 20 python3 - "$QUEUE_FILE" <<'PY' 2>/dev/null
import json, sys
from datetime import datetime, timezone

path = sys.argv[1]
try:
    fh = open(path, encoding="utf-8", errors="replace")
except OSError:
    sys.exit(1)

latest = {}
with fh:
    for line in fh:
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            # A torn final line is normal on an append-only file read mid-write.
            # Skipping ONE malformed line is not the same as failing to read the
            # file; a file we could not open at all already exited 1 above.
            continue
        tid = row.get("task_id")
        if tid:
            latest[tid] = row

now = datetime.now(timezone.utc)
out = []
for tid, row in latest.items():
    raw = str(row.get("ts") or "")
    try:
        stamp = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        age = int((now - stamp).total_seconds())
        if age < 0:
            age = 0
    except ValueError:
        age = -1          # unparseable timestamp -> never counted as aged
    occ = row.get("expected_occupancy")
    est = occ.get("est_h") if isinstance(occ, dict) else None
    if est is None:
        est = row.get("est_wall_clock_h")
    screened = row.get("screened_by")

    def clean(value):
        # The record and field separators must not survive inside a field, or a
        # crafted task_id could forge extra columns.
        return "".join(" " if c in "\x1f\t\r\n" else c for c in str(value))

    fields = [
        clean(tid),
        clean(row.get("status") or ""),
        str(age),
        "1" if isinstance(screened, str) and screened.strip() else "0",
        "" if est is None else clean(est),
        clean(row.get("parked_reason") or ""),
        clean(row.get("gating") or ""),
    ]
    out.append("\x1f".join(fields))
sys.stdout.write("\n".join(sorted(out)))
PY
    ) || return 1
    # An EMPTY queue file is a legitimate reading (rc 0, no rows). An
    # unreadable one exited non-zero above. The two must not be conflated.
    printf '%s' "$out"
}

# Keys the alarm channel currently holds ACTIVE. Read from the channel's OWN
# state rather than from a counter kept here — that is what makes the clear
# sweep able to resolve an alarm raised by a PREVIOUS fleet_watch process, and
# what keeps this file free of a second dedupe layer.
fw_alarm_active() {
    local out keys
    # `--json` is a GLOBAL option on alarm_channel.py's parser, so it must come
    # BEFORE the subcommand: `status --json` is an argparse USAGE ERROR (exit 2)
    # and would make every cycle report the channel as unreadable — a watchdog
    # that never clears anything, quietly. Caught by a live smoke run, not by
    # the suite, because the suite necessarily fakes this probe.
    out=$(timeout 30 python3 "$ALARM" --json status 2>/dev/null) || return 1
    [ -n "$out" ] || return 1
    printf '%s' "$out" | jq -e . >/dev/null 2>&1 || return 1
    keys=$(printf '%s' "$out" | jq -r '(.active // {}) | keys[]' 2>/dev/null) || return 1
    printf '%s' "$keys"
}

fw_alarm_raise() {   # fw_alarm_raise <key> <severity> <message> <evidence-json>
    if [ "$ALARMS_ENABLED" != "1" ]; then
        printf 'WOULD-RAISE %s [%s] %s\n' "$1" "$2" "$3"
        return 0
    fi
    timeout 60 python3 "$ALARM" raise --key "$1" --severity "$2" --message "$3" \
        --evidence "$4" >/dev/null 2>&1
}

fw_alarm_clear() {   # fw_alarm_clear <key> <message>
    if [ "$ALARMS_ENABLED" != "1" ]; then
        printf 'WOULD-CLEAR %s\n' "$1"
        return 0
    fi
    timeout 60 python3 "$ALARM" clear --key "$1" --message "$2" >/dev/null 2>&1
}

# EVIDENCE ONLY (rule 4). Read-only, and never consulted by any classifier.
fw_capture_pane() { timeout 10 tmux capture-pane -p -t "${EVIDENCE_SESSION}:${1}" 2>/dev/null; }

# ============================================================================
# PURE CLASSIFIERS — no I/O, unit-testable.
# ============================================================================

# Compute state. Echoes busy|idle|unknown.
#   $1 gpu%  $2 vram%  $3 regions free  $4 regions total  ('unknown' allowed)
fw_classify_compute() {
    local gpu="$1" vram="$2" free="$3" total="$4"
    case "${gpu}|${vram}|${free}|${total}" in
        *unknown*) printf 'unknown'; return 0 ;;
        *[!0-9|]*) printf 'unknown'; return 0 ;;
    esac
    [ -n "$gpu" ] && [ -n "$vram" ] && [ -n "$free" ] && [ -n "$total" ] || { printf 'unknown'; return 0; }
    [ "$total" -gt 0 ] 2>/dev/null || { printf 'unknown'; return 0; }
    # VRAM IS CHECKED INDEPENDENTLY OF GPU%. A run that silently falls back to
    # CPU shows 0% util AND 0% VRAM — that is how a "GPU benchmark" got measured
    # on 96 CPU threads on 2026-08-12 (root cause: /etc/environment puts the CPU
    # build early in LD_LIBRARY_PATH, and `ldd` cannot detect it because
    # llama.cpp dlopens libggml-hip.so). Persistence matters here too:
    # llama-bench EXITS between probes, so the card legitimately reads 0%/0%
    # inside a perfectly healthy sweep, and a single sample landing in that gap
    # is sampling error, not idleness.
    if [ "$gpu" = "0" ] && [ "$vram" = "0" ] && [ "$free" = "$total" ]; then
        printf 'idle'
    else
        printf 'busy'
    fi
}

# max over all cards of one rocm-smi key; 'unknown' if the key is absent
# everywhere, so a schema change cannot read as 0%.
fw_gpu_metric() {
    local json="$1" key="$2" v
    v=$(printf '%s' "$json" | jq -r --arg k "$key" \
        '[ .[] | objects | (.[$k] // empty) | tonumber? ] | if length == 0 then "unknown" else (max | floor) end' 2>/dev/null)
    [ -n "$v" ] || v="unknown"
    printf '%s' "$v"
}

# region-lock renders "  q0  free   " / "  q0  HELD   <holder>". The holder
# column is free text, so `grep -c free` over whole lines counts any holder whose
# command line happens to contain the word. Anchored to the state column here,
# and the total is COUNTED rather than assumed to be 4.
fw_regions_free()  { printf '%s\n' "$1" | grep -cE '^[[:space:]]*[A-Za-z0-9_]+[[:space:]]+free([[:space:]]|$)'; }
fw_regions_total() { printf '%s\n' "$1" | grep -cE '^[[:space:]]*[A-Za-z0-9_]+[[:space:]]+(free|HELD)([[:space:]]|$)'; }

# Which gate is holding this READY row? Pure; the ONE place the refusal taxonomy
# is decided. Mirrors `session_bus_coordinator.dispatch_gate` — screening before
# occupancy, because an unscreened row's occupancy estimate is an estimate of
# work nobody has confirmed still exists.
#   $1 screened (1|0)   $2 est_h ('' when absent)   $3 parked_reason ('' when not parked)
fw_refusal_class() {
    local screened="$1" esth="$2" parked="$3"
    # A parked row got as far as the premise screener, which runs INSIDE
    # worker_runner after the claim — so it already passed dispatch_gate, and
    # reporting it as "unscreened" would send a human to fix a gate that already
    # said yes. The later refusal is the live one.
    [ -n "$parked" ] && { printf 'premise-parked'; return 0; }
    [ "$screened" = "1" ] || { printf 'unscreened'; return 0; }
    case "$esth" in
        ''|*[!0-9.]*) printf 'no-occupancy-estimate'; return 0 ;;
    esac
    # awk, not bash arithmetic: est_h is a FLOAT, and `[ 0.5 -gt 0 ]` is not an
    # arithmetic comparison in bash — it is an error that, without `-e`, prints
    # to stderr and evaluates false, i.e. classifies every well-formed row as
    # lacking an occupancy estimate.
    awk -v v="$esth" 'BEGIN{exit !(v > 0)}' || { printf 'no-occupancy-estimate'; return 0; }
    printf 'dispatchable'
}

# Seconds -> hours, one decimal, for a line a human reads at 3am.
fw_hours() {
    case "$1" in
        ''|*[!0-9]*) printf '?'; return 0 ;;
    esac
    awk -v v="$1" 'BEGIN{printf "%.1f", v / 3600}'
}

# ============================================================================
# PERSISTENCE STATE
#
# Associative arrays, NOT `printf -v "prev_${name}"`. Dynamic variable names
# built from a class or roster id are not valid identifiers for every value they
# can hold — `no-occupancy-estimate` and `coordinator-agent` both contain
# hyphens, so `printf -v prev_no-occupancy-estimate` fails and `${!prev_var}`
# raises a bad-substitution error mid-loop.
# ============================================================================
declare -A FW_ON_N FW_OFF_N FW_CLASS_AGED
declare -a FW_FINDINGS=() FW_OBSERVATIONS=()
FW_CYCLE=0
FW_READY=0; FW_AGED=0; FW_INFLIGHT=0; FW_READY_GATED=0
FW_CAPACITY_FREE=0; FW_OLDEST_ID=""; FW_OLDEST_AGE=0

fw_reset_state() {
    FW_ON_N=(); FW_OFF_N=(); FW_CLASS_AGED=()
    FW_FINDINGS=(); FW_OBSERVATIONS=()
    FW_CYCLE=0
    FW_READY=0; FW_AGED=0; FW_INFLIGHT=0; FW_READY_GATED=0
    FW_CAPACITY_FREE=0; FW_OLDEST_ID=""; FW_OLDEST_AGE=0
    FW_VERDICT=""; FW_SUMMARY=""
}

# Symmetric hysteresis (rule 1). Call with 1 when the condition was OBSERVED
# present, 0 when OBSERVED absent, and DO NOT CALL AT ALL when it could not be
# read — an unread cycle must advance neither counter, or an unreadable
# instrument would eventually "prove" the condition gone and resolve the alarm.
fw_track() {
    if [ "$2" = "1" ]; then
        FW_ON_N[$1]=$(( ${FW_ON_N[$1]:-0} + 1 )); FW_OFF_N[$1]=0
    else
        FW_OFF_N[$1]=$(( ${FW_OFF_N[$1]:-0} + 1 )); FW_ON_N[$1]=0
    fi
}
fw_is_on()  { [ "${FW_ON_N[$1]:-0}"  -ge "$PERSIST_CYCLES" ]; }
fw_is_off() { [ "${FW_OFF_N[$1]:-0}" -ge "$PERSIST_CYCLES" ]; }

# ============================================================================
# QUEUE SCAN — pure over the TSV the probe returns.
#
# MUST NOT BE CALLED IN A COMMAND SUBSTITUTION: it publishes into globals, and
# `$(fw_scan_queue ...)` would run it in a subshell and discard every one of
# them. The `while read` loop below is fed by a HERE-STRING rather than a pipe
# for exactly the same reason — `... | while read` is also a subshell.
# ============================================================================
fw_scan_queue() {
    local tsv="$1"
    local task status age screened esth parked gating cls
    FW_READY=0; FW_AGED=0; FW_INFLIGHT=0; FW_READY_GATED=0
    FW_OLDEST_ID=""; FW_OLDEST_AGE=0
    FW_CLASS_AGED=()

    # US, not tab — see the separator note on fw_queue_rows. An IFS whitespace
    # delimiter would collapse empty fields and shift every column after them.
    while IFS=$'\x1f' read -r task status age screened esth parked gating; do
        [ -n "${task:-}" ] || continue
        case "${status:-}" in
            ASSIGNED|CLAIMED|RUNNING) FW_INFLIGHT=$((FW_INFLIGHT + 1)); continue ;;
            READY) ;;
            *) continue ;;     # terminal, INFRA_BLOCKED, HELD_OP_GATE: nobody is waiting on them
        esac
        FW_READY=$((FW_READY + 1))
        # `gating` names the hardware a row needs. A row that needs none can
        # never be the reason a GPU is idle, so only gated rows escalate
        # COMPUTE-IDLE (rule 3).
        case "${gating:-}" in
            ''|none) ;;
            *) FW_READY_GATED=$((FW_READY_GATED + 1)) ;;
        esac
        # age -1 is an unparseable timestamp: UNKNOWN, and unknown is not aged.
        [ "${age:-0}" -ge "$AGE_THRESHOLD_S" ] 2>/dev/null || continue
        FW_AGED=$((FW_AGED + 1))
        cls=$(fw_refusal_class "${screened:-0}" "${esth:-}" "${parked:-}")
        FW_CLASS_AGED[$cls]=$(( ${FW_CLASS_AGED[$cls]:-0} + 1 ))
        if [ "$age" -gt "$FW_OLDEST_AGE" ]; then
            FW_OLDEST_AGE="$age"; FW_OLDEST_ID="$task"
        fi
    done <<< "$tsv"

    FW_CAPACITY_FREE=$(( CAPACITY - FW_INFLIGHT ))
    [ "$FW_CAPACITY_FREE" -lt 0 ] && FW_CAPACITY_FREE=0
    return 0
}

# ============================================================================
# EVIDENCE (rule 4) — human-readable only, attached to an already-decided alarm.
# ============================================================================
fw_pane_evidence() {
    local name pane out=""
    [ -n "$EVIDENCE_PANES" ] || { printf ''; return 0; }
    for name in $EVIDENCE_PANES; do
        pane=$(fw_capture_pane "$name") || pane=""
        if [ -z "$pane" ]; then
            out="${out}[${name}: pane unreadable] "
            continue
        fi
        out="${out}[${name}] $(printf '%s\n' "$pane" | tail -n "$EVIDENCE_LINES" | tr '\n' ' ') "
    done
    printf '%s' "$out"
}

# Build the evidence object with jq so a task_id or a fix string containing a
# quote, a backslash or a newline cannot forge JSON into the alarm record.
fw_evidence_json() {   # fw_evidence_json k v k v ...
    local args=() k v pane
    while [ "$#" -ge 2 ]; do
        k="$1"; v="$2"; shift 2
        args+=(--arg "$k" "$v")
    done
    pane=$(fw_pane_evidence)
    if [ -n "$pane" ]; then
        args+=(--arg human_evidence_pane_tail "EVIDENCE ONLY, NOT A TRIGGER — pane scrollback for human triage: $(fw_sanitise "$pane")")
    fi
    jq -nc "${args[@]}" '$ARGS.named' 2>/dev/null || printf '{}'
}

# ============================================================================
# ONE CYCLE. Fills the GLOBAL FW_FINDINGS / FW_VERDICT / FW_SUMMARY and drives
# the alarm channel.
#
# IT MUST NOT BE CALLED IN A COMMAND SUBSTITUTION, and that is why it returns
# its findings in a global rather than on stdout. `findings=$(fw_run_cycle)`
# runs the cycle in a SUBSHELL, so every counter it advances — FW_CYCLE,
# FW_ON_N, FW_OFF_N — is discarded when that subshell exits. The persistence
# machine would then reset on every cycle and NO condition could ever reach
# PERSIST_CYCLES: the whole detector would run forever and report nothing, while
# looking perfectly healthy. Caught by the persistence cases in
# tests/test_fleet_watch.sh.
# ============================================================================
fw_run_cycle() {
    local gpu=unknown vram=unknown free=unknown total=unknown rocm regions compute
    local tsv queue_ok=0 cls n owner fix key msg
    local want_keys="" eligible_keys="" unowned="" unowned_n=0
    FW_FINDINGS=(); FW_OBSERVATIONS=()
    FW_CYCLE=$((FW_CYCLE + 1))
    FW_VERDICT=""; FW_SUMMARY=""

    # ---- 1. QUEUE (bus files) ------------------------------------------
    if tsv=$(fw_queue_rows); then
        queue_ok=1
        fw_scan_queue "$tsv"
    else
        # UNKNOWN. Not "the queue is empty" — see fw_queue_rows.
        FW_FINDINGS+=("QUEUE-UNREADABLE ${QUEUE_FILE} could not be read — aging is UNKNOWN this cycle (reported, NOT treated as an empty queue)")
    fi

    # ---- 2. COMPUTE (hardware) -----------------------------------------
    if rocm=$(fw_gpu_json); then
        gpu=$(fw_gpu_metric "$rocm" 'GPU use (%)')
        vram=$(fw_gpu_metric "$rocm" 'GPU Memory Allocated (VRAM%)')
    fi
    if regions=$(fw_regions_text); then
        free=$(fw_regions_free "$regions")
        total=$(fw_regions_total "$regions")
    fi
    compute=$(fw_classify_compute "$gpu" "$vram" "$free" "$total")

    # ---- 3. COMPUTE-IDLE -----------------------------------------------
    # Two conjuncts, and BOTH must be readable. Idle hardware with nothing that
    # needs it is a well-run night (rule 3); idle hardware with compute-gated
    # work queued is the reportable condition the operator asked for.
    if [ "$compute" != "unknown" ] && [ "$queue_ok" = "1" ]; then
        eligible_keys="${eligible_keys} compute-idle-with-queued-work"
        if [ "$compute" = "idle" ] && [ "$FW_READY_GATED" -gt 0 ]; then
            fw_track compute-idle-with-queued-work 1
        else
            fw_track compute-idle-with-queued-work 0
        fi
        if fw_is_on compute-idle-with-queued-work; then
            want_keys="${want_keys} compute-idle-with-queued-work"
            n="${FW_ON_N[compute-idle-with-queued-work]}"
            FW_FINDINGS+=("COMPUTE-IDLE ${n} cycles ~ $(( n * INTERVAL ))s: GPU ${gpu}% / VRAM ${vram}% / ${free} of ${total} CPU regions free, with ${FW_READY_GATED} compute-gated READY row(s) waiting")
            fw_alarm_raise "compute-idle-with-queued-work" "warning" \
                "Compute idle for ${n} cycles (~$(( n * INTERVAL ))s) while ${FW_READY_GATED} compute-gated READY row(s) wait. GPU ${gpu}% / VRAM ${vram}% / ${free} of ${total} CPU regions free. OWNER: coordinator-agent. FIX: dispatch the gated rows or grant a compute window." \
                "$(fw_evidence_json gpu_pct "$gpu" vram_pct "$vram" regions_free "$free" regions_total "$total" ready_gated "$FW_READY_GATED" cycles "$n" owner "coordinator-agent")"
        elif [ "$compute" = "idle" ]; then
            # Logged, never escalated: the coordinator's boundary report greps
            # the COMPUTE-IDLE token for its occupancy line, so the reading must
            # still reach the log even when it is not alarm-worthy.
            #
            # TWO DIFFERENT REASONS reach this branch and they must not share one
            # sentence. A first draft printed "NO compute-gated READY row is
            # waiting" unconditionally, so a live cycle with FOURTEEN gated rows
            # queued logged a flat denial that there were any — a fabricated
            # reading in the one line the boundary report relays verbatim.
            if [ "$FW_READY_GATED" -eq 0 ]; then
                FW_OBSERVATIONS+=("COMPUTE-IDLE (not an alarm) GPU ${gpu}% / VRAM ${vram}% / ${free} of ${total} CPU regions free, and NO compute-gated READY row is waiting — idle hardware with nothing queued for it is a well-run night")
            else
                FW_OBSERVATIONS+=("COMPUTE-IDLE (${FW_ON_N[compute-idle-with-queued-work]:-0}/${PERSIST_CYCLES} cycles, nothing asserted yet) GPU ${gpu}% / VRAM ${vram}% / ${free} of ${total} CPU regions free, with ${FW_READY_GATED} compute-gated READY row(s) waiting")
            fi
        fi
    fi

    # ---- 4. QUEUE-AGING, per refusal class ------------------------------
    # A refused row COUNTS AS AGING (R9): the scan classifies every aged READY
    # row by the gate holding it, and each class is its own alarm so each lands
    # on its own owner with its own fix.
    if [ "$queue_ok" = "1" ]; then
        for cls in $FW_CLASSES; do
            eligible_keys="${eligible_keys} queue-aging-${cls}"
        done
        eligible_keys="${eligible_keys} queue-aging-unowned"

        # A class the scan produced that the owner table does not know about is
        # itself the finding — rows starving behind an unowned refusal is the
        # exact 9,219-refusal failure, so it fails loudly rather than silently.
        # `"${!arr[@]}"` (the KEYS form) — NOT `${!arr[@]+"${!arr[@]}"}`. Bash
        # parses the latter as INDIRECT expansion with an alternate word: it
        # takes the joined VALUES of the array and uses them as a variable name,
        # which fails with "invalid variable name" and skips the loop entirely.
        # The keys form is already safe on an empty array under `set -u`.
        for cls in "${!FW_CLASS_AGED[@]}"; do
            if ! fw_class_owner "$cls" >/dev/null 2>&1; then
                unowned="${unowned}${cls}=${FW_CLASS_AGED[$cls]} "
                unowned_n=$(( unowned_n + FW_CLASS_AGED[$cls] ))
            fi
        done
        if [ "$unowned_n" -gt 0 ] && [ "$FW_CAPACITY_FREE" -gt 0 ]; then
            fw_track queue-aging-unowned 1
        else
            fw_track queue-aging-unowned 0
        fi
        if fw_is_on queue-aging-unowned; then
            want_keys="${want_keys} queue-aging-unowned"
            FW_FINDINGS+=("QUEUE-AGING-UNOWNED ${unowned_n} aged row(s) in refusal class(es) with NO OWNER: ${unowned}")
            fw_alarm_raise "queue-aging-unowned" "warning" \
                "${unowned_n} aged READY row(s) sit in a refusal class with no owner: ${unowned}. A refusal nobody owns is a row nobody drains. OWNER: coordinator-agent. FIX: add the class to FW_CLASSES/fw_class_owner/fw_class_fix in scripts/coordination/fleet_watch.sh." \
                "$(fw_evidence_json classes "$unowned" aged_rows "$unowned_n" owner "coordinator-agent")"
        fi

        for cls in $FW_CLASSES; do
            n="${FW_CLASS_AGED[$cls]:-0}"
            key="queue-aging-${cls}"
            # CAPACITY IS PART OF THE CONDITION. A deep queue with every worker
            # slot occupied is a fleet working, not a fleet stalled, and paging
            # for it is the cry-wolf failure.
            if [ "$n" -gt 0 ] && [ "$FW_CAPACITY_FREE" -gt 0 ]; then
                fw_track "$key" 1
            else
                fw_track "$key" 0
            fi
            fw_is_on "$key" || continue
            want_keys="${want_keys} ${key}"
            owner=$(fw_class_owner "$cls")
            fix=$(fw_class_fix "$cls")
            msg="${n} READY row(s) refused as '${cls}' have aged past $(fw_hours "$AGE_THRESHOLD_S")h while ${FW_CAPACITY_FREE} of ${CAPACITY} worker slot(s) are free. OWNER: ${owner}. FIX: ${fix}. Oldest overall: ${FW_OLDEST_ID} ($(fw_hours "$FW_OLDEST_AGE")h)."
            FW_FINDINGS+=("QUEUE-AGING ${cls} ${n} row(s) past $(fw_hours "$AGE_THRESHOLD_S")h, ${FW_CAPACITY_FREE}/${CAPACITY} slots free — owner ${owner}; oldest ${FW_OLDEST_ID} $(fw_hours "$FW_OLDEST_AGE")h")
            fw_alarm_raise "$key" "warning" "$msg" \
                "$(fw_evidence_json refusal_class "$cls" aged_rows "$n" owner "$owner" fix "$fix" \
                    oldest_task_id "$FW_OLDEST_ID" oldest_age_h "$(fw_hours "$FW_OLDEST_AGE")" \
                    threshold_h "$(fw_hours "$AGE_THRESHOLD_S")" ready_rows "$FW_READY" \
                    in_flight "$FW_INFLIGHT" capacity_free "$FW_CAPACITY_FREE" \
                    queue_file "$QUEUE_FILE")"
        done
    fi

    # ---- 5. CLEAR SWEEP -------------------------------------------------
    fw_reconcile_alarms "$want_keys" "$eligible_keys"

    # ---- 6. verdict -----------------------------------------------------
    # THE FIRST-CYCLE LIE, FIXED. The pre-production version logged "ok — no
    # stalls, compute in use" on cycle 1 even when compute was idle, because
    # persistence had not accumulated — a fail-open message asserting health from
    # an absence of evidence it had not yet had time to collect. "Not yet
    # determined" is a DISTINCT verdict from "healthy", and health is only ever
    # claimed over signals actually read this cycle.
    local qstate
    if [ "$queue_ok" = "1" ]; then qstate=read; else qstate=UNREADABLE; fi
    if [ "${#FW_FINDINGS[@]}" -gt 0 ]; then
        FW_VERDICT="stall"
        FW_SUMMARY="STALL REPORT"
    elif [ "$FW_CYCLE" -lt "$PERSIST_CYCLES" ]; then
        FW_VERDICT="warming"
        FW_SUMMARY="warming — cycle ${FW_CYCLE}/${PERSIST_CYCLES}, persistence not yet accumulated; NOTHING is asserted yet (compute=${compute}, queue=${qstate})"
    elif [ "$compute" = "unknown" ] || [ "$queue_ok" != "1" ]; then
        FW_VERDICT="degraded"
        FW_SUMMARY="UNDETERMINED — compute=${compute}, queue=${qstate}; no health is claimed for what could not be read"
    else
        FW_VERDICT="ok"
        FW_SUMMARY="ok — ${FW_READY} READY (${FW_AGED} aged past $(fw_hours "$AGE_THRESHOLD_S")h), ${FW_INFLIGHT} in flight, ${FW_CAPACITY_FREE}/${CAPACITY} slots free, compute=${compute} (GPU ${gpu}% / VRAM ${vram}% / ${free} of ${total} regions free)"
    fi
}

# Resolve alarms this script owns whose condition is KNOWN to be gone.
#   $1 want      — keys whose condition holds right now
#   $2 eligible  — keys whose domain was READABLE this cycle. A key outside this
#                  set is left exactly as it is: an unreadable instrument may
#                  neither raise nor resolve (rule 2).
# The active set comes from the CHANNEL's own state, so an alarm left active by
# a previous fleet_watch process is still resolvable after a restart — and no
# alarm raised by the daemon, a supervisor or a human is ever touched, because
# the sweep intersects with FW_OWNED_KEYS first.
fw_reconcile_alarms() {
    local want="$1" eligible="$2" active key
    if ! active=$(fw_alarm_active); then
        FW_OBSERVATIONS+=("ALARM-STATE-UNREADABLE ${ALARM} status could not be read — nothing cleared this cycle (an unreadable channel is not a quiet one)")
        return 0
    fi
    for key in $active; do
        case " ${FW_OWNED_KEYS} " in *" ${key} "*) ;; *) continue ;; esac
        case " ${eligible} "        in *" ${key} "*) ;; *) continue ;; esac
        case " ${want} "            in *" ${key} "*) continue ;; esac
        # Hysteresis on the way down too: only resolve once the condition has
        # been absent for PERSIST_CYCLES, so one unlucky sample cannot page the
        # operator with a RESOLVED it has to un-resolve on the next cycle.
        fw_is_off "$key" || continue
        FW_OBSERVATIONS+=("ALARM-CLEARED ${key} — condition absent for ${FW_OFF_N[$key]} consecutive cycles")
        fw_alarm_clear "$key" "RESOLVED: condition absent for ${FW_OFF_N[$key]} consecutive fleet_watch cycles"
    done
}

# ============================================================================
# MAIN LOOP
# ============================================================================
fw_validate_config() {
    local name val bad=0
    for name in INTERVAL PERSIST_CYCLES MAX_LOG_BYTES LOG_KEEP MAX_TEXT_CHARS \
                AGE_THRESHOLD_S CAPACITY EVIDENCE_LINES; do
        val="${!name}"
        # A non-numeric INTERVAL makes `sleep` fail instantly and turns this into
        # a busy loop that pins a core on a shared host. Fail LOUDLY at startup,
        # where a human is watching, rather than quietly at 100% CPU.
        if [ -z "$val" ] || [ -n "${val//[0-9]/}" ] || [ "$val" -lt 1 ] 2>/dev/null; then
            printf 'fleet_watch: %s must be a positive integer, got "%s"\n' "$name" "$val" >&2
            bad=1
        fi
    done
    [ "$bad" = 0 ]
}

# Log shape is UNCHANGED from the pane-era version and must stay that way: the
# coordinator has a standing Monitor keyed on the "STALL REPORT" header and the
# two-space-indented finding lines beneath it, and `session_bus.py`'s boundary
# report greps this file for a line containing COMPUTE-IDLE. New condition
# tokens are additive (QUEUE-AGING, QUEUE-AGING-UNOWNED, QUEUE-UNREADABLE,
# ALARM-CLEARED, ALARM-STATE-UNREADABLE); COMPUTE-IDLE keeps its exact spelling.
# RETIRED with the pane heuristics: STUCK-INPUT, IDLE-CANDIDATE, PANE-DEAD,
# PANE-UNREADABLE, DETECTOR-BLIND, FLEET-UNREADABLE.
fw_emit() {
    local line
    if [ "${#FW_FINDINGS[@]}" -gt 0 ]; then
        fw_log "STALL REPORT"
        for line in ${FW_FINDINGS[@]+"${FW_FINDINGS[@]}"}; do
            [ -n "$line" ] && printf '  %s\n' "$line" >> "$LOG"
        done
    else
        fw_log "$FW_SUMMARY"
    fi
    for line in ${FW_OBSERVATIONS[@]+"${FW_OBSERVATIONS[@]}"}; do
        [ -n "$line" ] && printf '  %s\n' "$line" >> "$LOG"
    done
}

fw_main() {
    mkdir -p "$(dirname "$LOG")" 2>/dev/null
    fw_validate_config || exit 64

    # Single instance. Two watchers double every finding into the coordinator's
    # Monitor, and a duplicated report reads as a second, independent
    # confirmation of the same stall.
    exec 9>"$LOCK_FILE" || exit 70
    if ! flock -n 9; then
        printf 'fleet_watch: another instance holds %s — exiting\n' "$LOCK_FILE" >&2
        exit 3
    fi

    trap 'fw_log "fleet_watch stopping (signal, pid $$)"; exit 0' TERM INT

    fw_log "fleet_watch started (interval ${INTERVAL}s, persist ${PERSIST_CYCLES}, aging threshold $(fw_hours "$AGE_THRESHOLD_S")h, capacity ${CAPACITY}, queue ${QUEUE_FILE}, alarms $([ "$ALARMS_ENABLED" = 1 ] && printf 'ON' || printf 'OFF'), pid $$)"

    while true; do
        fw_rotate_log_if_needed
        fw_run_cycle          # NOT $(...) — see the note on fw_run_cycle
        fw_emit
        sleep "$INTERVAL" || sleep 5
    done
}

# ============================================================================
# Sourced as a library (the test seam) -> define everything, run nothing.
# ============================================================================
if [ "${BASH_SOURCE[0]}" != "${0}" ]; then
    return 0 2>/dev/null || true
fi

case "${1:-}" in
    --once)
        # A human diagnostic must not resolve an alarm the loop owns, and must
        # not raise one off a single sample either — so it reports what it WOULD
        # do and touches the channel not at all.
        ALARMS_ENABLED=0
        fw_run_cycle
        if [ "${#FW_FINDINGS[@]}" -gt 0 ]; then
            printf 'STALL REPORT\n'
            printf '  %s\n' ${FW_FINDINGS[@]+"${FW_FINDINGS[@]}"}
        else
            printf '%s\n' "$FW_SUMMARY"
        fi
        printf '  %s\n' ${FW_OBSERVATIONS[@]+"${FW_OBSERVATIONS[@]}"}
        printf '(--once is a diagnostic: no alarm was raised or cleared)\n'
        ;;
    --selftest)
        exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/tests/test_fleet_watch.sh"
        ;;
    "") fw_main ;;
    *)  printf 'usage: %s [--once|--selftest]\n' "$0" >&2; exit 64 ;;
esac
