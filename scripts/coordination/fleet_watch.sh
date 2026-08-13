#!/bin/bash
# =============================================================================
# fleet_watch.sh — continuous fleet-stall detector for the coordinator
# =============================================================================
#
# WHY THIS EXISTS. The coordinator sampled fleet state only when the operator
# prompted it, and three separate mains sat idle for long stretches holding
# UNSUBMITTED text in their composers (mainB "push it", mainC "Freeze lifted…",
# mainB "run the full BGE sweep") while the MI210 sat at 0%. A queued-but-
# unsubmitted instruction is indistinguishable from a main that received the
# message and declined it, so it stays invisible until someone reads the pane by
# eye. This writes findings to a log the coordinator keeps a Monitor on, so a
# finding wakes it.
#
# DETECT AND REPORT ONLY. This never sends keys. Submitting a composer blindly
# could submit operator-typed input, and the sanctioned send path
# (`tmux_adapter.py nudge`/`doorbell`) carries guards this script has no business
# bypassing. It also never kills, never writes to the bus, and never touches the
# tmux session beyond read-only `capture-pane` / `display-message`.
#
# Tests: scripts/coordination/tests/test_fleet_watch.sh (unit + fixture suite)
#        scripts/coordination/tests/test_fleet_watch_mutation.sh (proves the
#        suite fails when each detector is deliberately broken).
#
# -----------------------------------------------------------------------------
# THE FOUR RULES THAT SHAPE EVERY DETECTOR — do not "simplify" these away
# -----------------------------------------------------------------------------
#
# 1. PERSISTENCE, NOT PRESENCE. The first version alarmed on presence and fired
#    on three mains within 90s of a routine dispatch; every one had submitted by
#    the next look. Nudging a main that is mid-generation legitimately queues
#    text in its composer. A monitor that cries wolf gets ignored, which is
#    worse than no monitor. Every condition below must hold for PERSIST_CYCLES
#    consecutive cycles, and STUCK-INPUT additionally requires the text to be
#    UNCHANGED across them.
#
# 2. THREE STATES, NEVER TWO. Every probe answers busy / idle / UNKNOWN, and
#    UNKNOWN never counts as idle. An unreadable instrument is not an idle one.
#    This is the most important property here: the pre-production version
#    collapsed a `rocm-smi` failure to `${gpu:-0}` = "0%", so a host where
#    `rocm-smi` was missing, renamed or merely slow would have reported
#    COMPUTE-IDLE forever — a fabricated alarm indistinguishable from a real one.
#
# 3. IDLE IS A CANDIDATE, NEVER A FACT. A session compacting its context renders
#    identically to an idle one (the operator corrected the coordinator on this
#    twice on 2026-08-12). The authoritative instrument is `tmux_adapter.py`'s
#    runtime check, which reports ACTIVE when the rollout JSONL ends in a
#    `token_count`/`reasoning` record rather than a turn-terminal one. Where that
#    signal exists it decides; where it does not, this reports a CANDIDATE for
#    the coordinator to confirm.
#
# 4. AUTHORITATIVE SOURCES FIRST, PANE TEXT LAST. Pane glyphs are UI strings and
#    they drift — `tmux_adapter.py`'s own glyph table drifted in fifteen days
#    (its C51 block: the whole live fleet's empty composer stopped matching, and
#    the doorbell guard then refused every ring to every Claude main). So the
#    order is runtime state -> tmux's own `window_activity` clock -> pane glyphs,
#    and a fleet-wide failure to recognise ANY glyph is reported as
#    DETECTOR-BLIND rather than silently rendered as six idle mains.
#
# -----------------------------------------------------------------------------
# WHY `set -uo pipefail` AND DELIBERATELY NOT `-e`
# -----------------------------------------------------------------------------
# A monitor must SURVIVE a failing probe — that is its entire job. Under `-e`
# this process would exit the first time `rocm-smi` was busy, a pane was
# repainting, `grep` found no match (rc 1 is normal and expected throughout), or
# `tmux` was momentarily unavailable, and the fleet would then be unwatched with
# nothing in the log to say so. Every external call below is therefore
# explicitly rc- and emptiness-checked and resolves to UNKNOWN on failure
# (rule 2). `-u` and `pipefail` are kept: they catch authoring mistakes without
# ending the process, because every variable read that can legitimately be unset
# uses `${x:-default}`.
#
# Usage:  fleet_watch.sh              # run the detector loop
#         fleet_watch.sh --once       # one cycle, print findings, exit
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
# single. env.sh canonicalizes LOG_DIR/EPYC_TMUX_ADAPTER from ANY worktree.
_FW_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${_FW_DIR}/../lib/env.sh"

LOG="${FLEET_WATCH_LOG:-${LOG_DIR}/fleet_watch.log}"
INTERVAL="${FLEET_WATCH_INTERVAL:-90}"
# Cycles a condition must persist before it is worth waking the coordinator.
PERSIST_CYCLES="${FLEET_WATCH_PERSIST_CYCLES:-3}"
AGENTS="${FLEET_WATCH_AGENTS:-inference auditor mainA mainB mainC mainD}"
SESSION="${FLEET_WATCH_SESSION:-agent}"
ADAPTER="${FLEET_WATCH_ADAPTER:-${EPYC_TMUX_ADAPTER}}"
RL="${FLEET_WATCH_REGION_LOCK:-/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock}"
LOCK_FILE="${FLEET_WATCH_LOCK:-${LOG_DIR}/.fleet_watch.lock}"
# Quiet threshold for the fallback liveness signal. Both TUIs redraw their
# spinner about once a second while generating, so a window with no output for
# this long is settled at its prompt rather than thinking. 120s is the constant
# `tmux_adapter.py` calibrated for its heartbeat override
# (DEFAULT_HEARTBEAT_OVERRIDE_QUIET_S), measured 2026-07-29.
IDLE_QUIET_S="${FLEET_WATCH_IDLE_QUIET_S:-120}"
MAX_LOG_BYTES="${FLEET_WATCH_MAX_LOG_BYTES:-5242880}"   # 5 MiB
LOG_KEEP="${FLEET_WATCH_LOG_KEEP:-3}"
PROBE_TIMEOUT_S="${FLEET_WATCH_PROBE_TIMEOUT_S:-20}"
MAX_TEXT_CHARS="${FLEET_WATCH_MAX_TEXT_CHARS:-70}"

# ----------------------------------------------------------------------------
# CALIBRATED UI STRINGS — DRIFT-PRONE BY CONSTRUCTION.
#
# Everything in this block is a calibration against a TUI release, not a fact
# about the world. `tmux_adapter.py`'s equivalent table drifted in fifteen days.
# They are gathered here, named, and guarded by the DETECTOR-BLIND check so that
# drift announces itself instead of manufacturing six idle mains.
#
# PROMPT_GLYPHS: the composer marker at the head of the input row.
#   "❯" U+276F  Claude Code (measured across all six live Claude panes 10:52Z
#               2026-08-12; followed by U+00A0, a NON-BREAKING space)
#   "❱" U+2771  Claude Code, the older calibration tmux_adapter.py was built on
#   "›" U+203A  Codex
# BUSY_MARKERS: rendered only while a turn is in flight, in either TUI.
# ----------------------------------------------------------------------------
PROMPT_GLYPHS="${FLEET_WATCH_PROMPT_GLYPHS:-❯ ❱ ›}"
BUSY_MARKERS="${FLEET_WATCH_BUSY_MARKERS:-esc to interrupt|Working \(|Pursuing goal|Waiting for [0-9]+ background agent}"
# Rows marking a live subagent under a main. Claude renders "◯ " per running
# subagent (and "●" for the main itself); the subagent rows disappear when they
# finish, so their presence is positive evidence of work in flight.
SUBAGENT_MARKER="${FLEET_WATCH_SUBAGENT_MARKER:-◯ }"
# Codex renders a greyed PLACEHOLDER in an EMPTY composer. It carries the same
# dim SGR as real queued text in Claude (measured 2026-08-12), so styling cannot
# separate them, and the cursor is parked at column 2 in BOTH the empty and the
# text-present case on every live pane, so cursor column cannot either. The
# placeholder is therefore excluded by name. THIS IS A CALIBRATION AND IT CAN
# ROT: an unlisted placeholder reads as pending input and would sit on the codex
# main as a permanent false STUCK-INPUT. Filed as C54 in
# handoffs/active/session-bus-thin-dispatcher.md.
PLACEHOLDER_RE="${FLEET_WATCH_PLACEHOLDER_RE:-^(Write tests for @filename|Explain (this codebase|@[A-Za-z0-9_.-]+)|Fix the bug in @[A-Za-z0-9_.-]+|Ask Codex to do anything|Try \"|Describe .*task)$}"

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
# `printf '%b'`, so a composer containing a backslash escape was re-interpreted
# on the way to the log; its literal "GPU 0%%" was likewise a format escape with
# no format string to consume it, and logged as "0%%".
fw_sanitise() {
    printf '%s' "$1" | tr -d '\000-\010\013\014\016-\037\177' | cut -c "1-${MAX_TEXT_CHARS}"
}

# ============================================================================
# PROBES — the ONLY functions that touch the outside world.
#
# These are the test seam: the suite sources this file and redefines them, so
# every classifier and the whole persistence machine run against synthetic
# fixtures with no live tmux, no GPU and no adapter.
#
# Contract: print the reading on stdout and return 0, or return non-zero to mean
# UNKNOWN.
# ============================================================================

fw_session_exists() { timeout 10 tmux has-session -t "$SESSION" 2>/dev/null; }

fw_capture_pane() { timeout 10 tmux capture-pane -p -t "${SESSION}:${1}" 2>/dev/null; }

# The composer row is located by tmux's OWN cursor, not by pattern-matching the
# pane. Measured 2026-08-12: on all six live mains `cursor_y` lands exactly on
# the composer row. This matters because transcript lines can carry the same
# prompt glyph as the composer; the pre-production version took the LAST glyph
# match anywhere in the pane, which reads a stale transcript line as pending
# input the moment the composer is empty — and transcript text never changes, so
# it satisfies the persistence rule and would alarm forever.
fw_cursor_row() { timeout 10 tmux display-message -p -t "${SESSION}:${1}" '#{cursor_y}' 2>/dev/null; }

# NOTE THE rc HANDLING. `tmux_adapter.py probe --json` returns EX_BLOCKED (a
# NON-ZERO code) whenever `nudge_ok` is false, which is the normal state of every
# busy main — while still printing complete, valid JSON. Judging the probe by its
# exit status would classify every working main as "adapter unavailable" and
# throw away the authoritative signal on exactly the mains that have one. The
# verdict is taken from whether the JSON PARSES, never from rc.
fw_probe_json() {
    local out
    out=$(timeout "$PROBE_TIMEOUT_S" python3 "$ADAPTER" probe --agent "$1" --json 2>/dev/null)
    [ -n "$out" ] || return 1
    printf '%s' "$out" | jq -e . >/dev/null 2>&1 || return 1
    printf '%s' "$out"
}

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

# ============================================================================
# PURE CLASSIFIERS — no I/O, unit-testable.
# ============================================================================

# Strip leading ASCII space/tab and U+00A0. The NBSP is spelled as explicit
# bytes (\xc2\xa0) rather than as a literal so the result cannot depend on the
# locale bash happens to be started under.
fw_lstrip() {
    local s="$1"
    while :; do
        case "$s" in
            ' '*)          s="${s# }" ;;
            $'\t'*)        s="${s#$'\t'}" ;;
            $'\xc2\xa0'*)  s="${s#$'\xc2\xa0'}" ;;
            *) break ;;
        esac
    done
    printf '%s' "$s"
}

fw_rstrip() {
    local s="$1"
    while :; do
        case "$s" in
            *' ')          s="${s% }" ;;
            *$'\t')        s="${s%$'\t'}" ;;
            *$'\xc2\xa0')  s="${s%$'\xc2\xa0'}" ;;
            *) break ;;
        esac
    done
    printf '%s' "$s"
}

# Classify one composer row.
#   stdout: the pending text ('' when the composer is empty)
#   rc 0 : row recognised as a composer row (stdout is authoritative)
#   rc 1 : NOT a recognised composer row -> caller must treat it as UNKNOWN,
#          never as "no pending input" (rule 2).
fw_composer_pending() {
    local row="$1" glyph rest matched=0
    row=$(fw_lstrip "$row")
    for glyph in $PROMPT_GLYPHS; do
        case "$row" in
            "$glyph"*) rest="${row#"$glyph"}"; matched=1; break ;;
        esac
    done
    [ "$matched" = 1 ] || return 1
    rest=$(fw_lstrip "$rest")
    rest=$(fw_rstrip "$rest")
    [ -n "$rest" ] || { printf ''; return 0; }
    if printf '%s' "$rest" | grep -qE "$PLACEHOLDER_RE" 2>/dev/null; then
        printf ''; return 0            # an empty Codex composer, rendered
    fi
    printf '%s' "$rest"
    return 0
}

# rc 0 = the pane shows positive evidence of a turn in flight.
fw_pane_busy() {
    printf '%s\n' "$1" | grep -qE "$BUSY_MARKERS" && return 0
    printf '%s\n' "$1" | grep -qF "$SUBAGENT_MARKER" && return 0
    return 1
}

# rc 0 = at least one string from the calibrated vocabulary appears. Used ONLY
# by the DETECTOR-BLIND guard: a pane showing neither a busy marker nor a prompt
# glyph is a pane this script can no longer read.
fw_pane_recognised() {
    fw_pane_busy "$1" && return 0
    local glyph
    for glyph in $PROMPT_GLYPHS; do
        printf '%s\n' "$1" | grep -qF "$glyph" && return 0
    done
    return 1
}

# Liveness for one main. Echoes busy|idle|dead|unknown.
#   $1 runtime_state  active|idle|null   (authoritative where present)
#   $2 quiet_s        seconds, or ''/'null' when unreadable
#   $3 pane_busy      0 = busy marker seen, 1 = none, 2 = pane unreadable
#   $4 pane_dead      true|false|null
fw_classify_liveness() {
    local runtime="$1" quiet="$2" pane_busy="$3" dead="$4"
    [ "$dead" = "true" ] && { printf 'dead'; return 0; }
    # Rule 3: where the runtime has an answer, it IS the answer.
    [ "$runtime" = "active" ] && { printf 'busy'; return 0; }
    [ "$runtime" = "idle" ]   && { printf 'idle'; return 0; }
    # No runtime signal — the state of every Claude main today, since the
    # adapter implements the rollout check for Codex only and honestly reports
    # UNAVAILABLE otherwise. A visible busy marker VETOES an idle verdict before
    # the clock is consulted: a marker is positive evidence, whereas quiet is
    # merely an absence of evidence.
    [ "$pane_busy" = "0" ] && { printf 'busy'; return 0; }
    [ "$pane_busy" = "2" ] && { printf 'unknown'; return 0; }
    case "$quiet" in
        ''|null|*[!0-9.]*) printf 'unknown'; return 0 ;;
    esac
    # awk, not bash arithmetic: window_quiet_for_s is a FLOAT, and
    # `[ 243.3 -ge 120 ]` is not an arithmetic comparison in bash — it is an
    # error that, without `-e`, prints to stderr and evaluates false, i.e. silently
    # reports every idle main as busy.
    if awk -v q="$quiet" -v t="$IDLE_QUIET_S" 'BEGIN{exit !(q >= t)}'; then
        printf 'idle'
    else
        printf 'busy'
    fi
}

# Round a float reading for display. `window_quiet_for_s` arrives as a raw
# double (356.71781730651855) and a log line a human has to read at 3am should
# not make them count digits. Non-numeric readings pass through untouched so
# "null" still renders as "null" rather than as a fabricated 0.
fw_round() {
    case "$1" in
        ''|null|*[!0-9.]*) printf '%s' "${1:-null}"; return 0 ;;
    esac
    awk -v v="$1" 'BEGIN{printf "%.0f", v}'
}

# Per-resource compute state. Each probe is three-valued so CPU activity cannot
# hide an idle GPU and GPU activity cannot hide idle CPU regions.
fw_classify_gpu() {
    local gpu="$1" vram="$2"
    case "${gpu}|${vram}" in
        *unknown*|*[!0-9|]*) printf 'unknown'; return 0 ;;
    esac
    if [ -z "$gpu" ] || [ -z "$vram" ]; then
        printf 'unknown'
        return 0
    fi
    # VRAM IS CHECKED INDEPENDENTLY OF GPU%. A run that silently falls back to
    # CPU shows 0% util AND 0% VRAM — that is how a "GPU benchmark" got measured
    # on 96 CPU threads on 2026-08-12 (root cause: /etc/environment puts the CPU
    # build early in LD_LIBRARY_PATH, and `ldd` cannot detect it because
    # llama.cpp dlopens libggml-hip.so). Persistence matters here too:
    # llama-bench EXITS between probes, so the card legitimately reads 0%/0%
    # inside a perfectly healthy sweep, and a single sample landing in that gap
    # is sampling error, not idleness.
    if [ "$gpu" = "0" ] && [ "$vram" = "0" ]; then
        printf 'idle'
    else
        printf 'busy'
    fi
}

fw_classify_cpu() {
    local free="$1" total="$2"
    case "${free}|${total}" in
        *unknown*|*[!0-9|]*) printf 'unknown'; return 0 ;;
    esac
    if [ -z "$free" ] || [ -z "$total" ]; then
        printf 'unknown'
        return 0
    fi
    [ "$total" -gt 0 ] 2>/dev/null || { printf 'unknown'; return 0; }
    if [ "$free" = "$total" ]; then printf 'idle'; else printf 'busy'; fi
}

# Compatibility aggregate used by the existing health verdict and log format.
fw_classify_compute() {
    local gpu_state cpu_state
    gpu_state=$(fw_classify_gpu "$1" "$2")
    cpu_state=$(fw_classify_cpu "$3" "$4")
    if [ "$gpu_state" = unknown ] || [ "$cpu_state" = unknown ]; then
        printf 'unknown'
    elif [ "$gpu_state" = idle ] && [ "$cpu_state" = idle ]; then
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

# ============================================================================
# PERSISTENCE STATE
#
# Associative arrays, NOT `printf -v "prev_${agent}"`. Dynamic variable names
# built from a roster id are not valid identifiers for every id the roster can
# hold — `coordinator-agent` contains a hyphen, so `printf -v prev_coordinator-agent`
# fails and `${!prev_var}` raises a bad-substitution error mid-loop.
# ============================================================================
declare -A FW_PEND_TEXT FW_PEND_N FW_IDLE_N
declare -a FW_FINDINGS=()
FW_COMPUTE_N=0
FW_GPU_IDLE_N=0
FW_CPU_IDLE_N=0
FW_BLIND_N=0
FW_CYCLE=0

fw_reset_state() {
    FW_PEND_TEXT=(); FW_PEND_N=(); FW_IDLE_N=(); FW_FINDINGS=()
    FW_COMPUTE_N=0; FW_GPU_IDLE_N=0; FW_CPU_IDLE_N=0
    FW_BLIND_N=0; FW_CYCLE=0
}

# ============================================================================
# ONE CYCLE. Fills the GLOBAL FW_FINDINGS / FW_VERDICT / FW_SUMMARY.
#
# IT MUST NOT BE CALLED IN A COMMAND SUBSTITUTION, and that is why it returns
# its findings in a global rather than on stdout. `findings=$(fw_run_cycle)`
# runs the cycle in a SUBSHELL, so every counter it increments — FW_CYCLE,
# FW_PEND_N, FW_IDLE_N, FW_COMPUTE_N — is discarded when that subshell exits.
# The persistence machine would then reset on every cycle and NO condition could
# ever reach PERSIST_CYCLES: the whole detector would run forever and report
# nothing, while looking perfectly healthy. Caught by the persistence cases in
# tests/test_fleet_watch.sh.
# ============================================================================
fw_run_cycle() {
    local a pane cy row pending probe runtime quiet dead pane_busy live composer_known
    local determined=0 unknown_mains=0 readable=0 recognised=0 total_mains=0
    FW_FINDINGS=()

    FW_CYCLE=$((FW_CYCLE + 1))
    FW_VERDICT=""; FW_SUMMARY=""

    if ! fw_session_exists; then
        # The biggest possible finding must not be silence. The pre-production
        # version `continue`d past every uncapturable pane, so a vanished tmux
        # session produced a clean "ok — no stalls" on every cycle forever.
        FW_VERDICT="unreadable"
        FW_SUMMARY="FLEET-UNREADABLE tmux session ${SESSION} is absent"
        FW_FINDINGS=("FLEET-UNREADABLE tmux session ${SESSION} is absent — every main is unobservable")
        return 0
    fi

    for a in $AGENTS; do
        total_mains=$((total_mains + 1))
        pane=$(fw_capture_pane "$a")
        if [ -z "$pane" ]; then
            # UNKNOWN, never idle. A false idle nudges into a working main; a
            # false busy costs one cycle.
            unknown_mains=$((unknown_mains + 1))
            FW_IDLE_N[$a]=0
            FW_PEND_N[$a]=0
            FW_FINDINGS+=("PANE-UNREADABLE ${a} — capture-pane returned nothing (reported, NOT treated as idle)")
            continue
        fi
        readable=$((readable + 1))
        fw_pane_recognised "$pane" && recognised=$((recognised + 1))

        # ---- STUCK-INPUT -------------------------------------------------
        cy=$(fw_cursor_row "$a")
        pending=""
        composer_known=0
        if [ -n "$cy" ] && [ -z "${cy//[0-9]/}" ]; then
            row=$(printf '%s\n' "$pane" | sed -n "$((cy + 1))p")
            if pending=$(fw_composer_pending "$row"); then
                composer_known=1
            fi
        fi
        if [ "$composer_known" = 1 ] && [ -n "$pending" ]; then
            if [ "$pending" = "${FW_PEND_TEXT[$a]:-}" ]; then
                FW_PEND_N[$a]=$(( ${FW_PEND_N[$a]:-0} + 1 ))
            else
                FW_PEND_N[$a]=1
            fi
            FW_PEND_TEXT[$a]="$pending"
        else
            # An unreadable composer RESETS the counter rather than holding it:
            # the claim is "this exact text has sat unsubmitted for N cycles",
            # and a cycle that could not read the composer cannot support it.
            FW_PEND_N[$a]=0
            FW_PEND_TEXT[$a]=""
        fi
        if [ "${FW_PEND_N[$a]:-0}" -ge "$PERSIST_CYCLES" ]; then
            FW_FINDINGS+=("STUCK-INPUT ${a} (${FW_PEND_N[$a]} cycles ~ $(( ${FW_PEND_N[$a]} * INTERVAL ))s unsubmitted): '$(fw_sanitise "$pending")'")
        fi

        # ---- IDLE-CANDIDATE ---------------------------------------------
        runtime=null; quiet=null; dead=null
        if probe=$(fw_probe_json "$a"); then
            IFS=$'\t' read -r runtime quiet dead <<< "$(printf '%s' "$probe" | jq -r \
                '[(.runtime_state // "null"), (.window_quiet_for_s // "null"), (.pane_dead // "null")] | @tsv' 2>/dev/null)"
            [ -n "${runtime:-}" ] || runtime=null
            [ -n "${quiet:-}" ]   || quiet=null
            [ -n "${dead:-}" ]    || dead=null
        fi
        if fw_pane_busy "$pane"; then pane_busy=0; else pane_busy=1; fi
        live=$(fw_classify_liveness "$runtime" "$quiet" "$pane_busy" "$dead")
        case "$live" in
            idle) FW_IDLE_N[$a]=$(( ${FW_IDLE_N[$a]:-0} + 1 )); determined=$((determined + 1)) ;;
            busy) FW_IDLE_N[$a]=0; determined=$((determined + 1)) ;;
            dead) FW_IDLE_N[$a]=0; FW_FINDINGS+=("PANE-DEAD ${a} — the pane has exited; the main is gone") ;;
            *)    FW_IDLE_N[$a]=0; unknown_mains=$((unknown_mains + 1)) ;;
        esac
        if [ "${FW_IDLE_N[$a]:-0}" -ge "$PERSIST_CYCLES" ]; then
            if [ "$runtime" = "idle" ]; then
                FW_FINDINGS+=("IDLE-CANDIDATE ${a} (${FW_IDLE_N[$a]} cycles; the RUNTIME reports idle — authoritative)")
            else
                FW_FINDINGS+=("IDLE-CANDIDATE ${a} (${FW_IDLE_N[$a]} cycles, window quiet $(fw_round "$quiet")s — confirm via tmux_adapter runtime check, may be compacting)")
            fi
        fi
    done

    # ---- DETECTOR-BLIND -------------------------------------------------
    # Every readable pane failed to show ANY calibrated glyph. Six mains losing
    # their vocabulary in the same cycle is a TUI release, not a fleet-wide
    # stall, and the honest report is that this script has gone blind — NOT six
    # IDLE-CANDIDATEs, which is what an unguarded glyph table emits.
    if [ "$readable" -gt 0 ] && [ "$recognised" -eq 0 ]; then
        FW_BLIND_N=$((FW_BLIND_N + 1))
        if [ "$FW_BLIND_N" -ge "$PERSIST_CYCLES" ]; then
            FW_FINDINGS=("DETECTOR-BLIND ${FW_BLIND_N} cycles: none of ${readable} readable panes shows any known marker — the TUI vocabulary has drifted, and idle/stuck verdicts are SUPPRESSED this cycle as untrustworthy")
        fi
    else
        FW_BLIND_N=0
    fi

    # ---- COMPUTE-IDLE ---------------------------------------------------
    local gpu=unknown vram=unknown free=unknown total=unknown rocm regions compute gpu_state cpu_state
    if rocm=$(fw_gpu_json); then
        gpu=$(fw_gpu_metric "$rocm" 'GPU use (%)')
        vram=$(fw_gpu_metric "$rocm" 'GPU Memory Allocated (VRAM%)')
    fi
    if regions=$(fw_regions_text); then
        free=$(fw_regions_free "$regions")
        total=$(fw_regions_total "$regions")
    fi
    gpu_state=$(fw_classify_gpu "$gpu" "$vram")
    cpu_state=$(fw_classify_cpu "$free" "$total")
    compute=$(fw_classify_compute "$gpu" "$vram" "$free" "$total")
    if [ "$gpu_state" = "idle" ]; then
        FW_GPU_IDLE_N=$((FW_GPU_IDLE_N + 1))
    else
        FW_GPU_IDLE_N=0
    fi
    if [ "$cpu_state" = "idle" ]; then
        FW_CPU_IDLE_N=$((FW_CPU_IDLE_N + 1))
    else
        FW_CPU_IDLE_N=0
    fi
    if [ "$compute" = "idle" ]; then
        FW_COMPUTE_N=$((FW_COMPUTE_N + 1))
    else
        FW_COMPUTE_N=0
    fi
    if [ "$FW_COMPUTE_N" -ge "$PERSIST_CYCLES" ]; then
        FW_FINDINGS+=("COMPUTE-IDLE ${FW_COMPUTE_N} cycles ~ $((FW_COMPUTE_N * INTERVAL))s: GPU ${gpu}% / VRAM ${vram}% / ${free} of ${total} CPU regions free")
    fi
    if [ "$FW_GPU_IDLE_N" -ge "$PERSIST_CYCLES" ]; then
        FW_FINDINGS+=("GPU-IDLE ${FW_GPU_IDLE_N} cycles ~ $((FW_GPU_IDLE_N * INTERVAL))s: GPU ${gpu}% / VRAM ${vram}%")
    fi
    if [ "$FW_CPU_IDLE_N" -ge "$PERSIST_CYCLES" ]; then
        FW_FINDINGS+=("CPU-IDLE ${FW_CPU_IDLE_N} cycles ~ $((FW_CPU_IDLE_N * INTERVAL))s: ${free} of ${total} CPU regions free")
    fi

    # ---- verdict --------------------------------------------------------
    # THE FIRST-CYCLE LIE, FIXED. The pre-production version logged
    # "ok — no stalls, compute in use" on cycle 1 even when compute was idle,
    # because persistence had not accumulated — a fail-open message asserting
    # health from an absence of evidence it had not yet had time to collect.
    # "Not yet determined" is now a DISTINCT verdict from "healthy", and health
    # is only ever claimed over signals actually read this cycle.
    if [ "${#FW_FINDINGS[@]}" -gt 0 ]; then
        FW_VERDICT="stall"
        FW_SUMMARY="STALL REPORT"
    elif [ "$FW_CYCLE" -lt "$PERSIST_CYCLES" ]; then
        FW_VERDICT="warming"
        FW_SUMMARY="warming — cycle ${FW_CYCLE}/${PERSIST_CYCLES}, persistence not yet accumulated; NOTHING is asserted yet (compute=${compute}, mains determined ${determined}/${total_mains})"
    elif [ "$unknown_mains" -gt 0 ] || [ "$compute" = "unknown" ]; then
        FW_VERDICT="degraded"
        FW_SUMMARY="UNDETERMINED — ${unknown_mains}/${total_mains} mains unreadable, compute=${compute}; no health is claimed for what could not be read"
    else
        FW_VERDICT="ok"
        FW_SUMMARY="ok — ${determined}/${total_mains} mains determined active, no unsubmitted input, compute in use (GPU ${gpu}% / VRAM ${vram}% / ${free} of ${total} regions free)"
    fi

}

# ============================================================================
# MAIN LOOP
# ============================================================================
fw_validate_config() {
    local name val bad=0
    for name in INTERVAL PERSIST_CYCLES IDLE_QUIET_S MAX_LOG_BYTES LOG_KEEP PROBE_TIMEOUT_S MAX_TEXT_CHARS; do
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

# Log shape is UNCHANGED from the pre-production version and must stay that way:
# the coordinator has a standing Monitor keyed on the "STALL REPORT" header and
# the two-space-indented finding lines beneath it. New condition tokens are
# additive (PANE-UNREADABLE, PANE-DEAD, DETECTOR-BLIND, FLEET-UNREADABLE); the
# three original ones keep their exact spelling.
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

    fw_log "fleet_watch started (interval ${INTERVAL}s, persist ${PERSIST_CYCLES}, idle-quiet ${IDLE_QUIET_S}s, agents '${AGENTS}', pid $$)"

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
        fw_run_cycle
        if [ "${#FW_FINDINGS[@]}" -gt 0 ]; then
            printf 'STALL REPORT\n'
            printf '  %s\n' ${FW_FINDINGS[@]+"${FW_FINDINGS[@]}"}
        else
            printf '%s\n' "$FW_SUMMARY"
        fi
        ;;
    --selftest)
        exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/tests/test_fleet_watch.sh"
        ;;
    "") fw_main ;;
    *)  printf 'usage: %s [--once|--selftest]\n' "$0" >&2; exit 64 ;;
esac
