#!/bin/bash
# =============================================================================
# observer_guard.sh — the three-state observation contract for watchdogs
# =============================================================================
#
# THE DEFECT CLASS THIS EXISTS TO KILL
# ------------------------------------
# 2026-08-12, `bus_supervisor.sh`. The watchdog identified the coordinator-daemon
# with `pgrep -f "session_bus_coordinator\.py run"`. The live daemon's argv was
# `... session_bus_coordinator.py --bus-root <path> run` — `--bus-root <path>` sat
# between `.py` and `run`, so the pattern never matched. The watchdog declared a
# perfectly healthy, actively heartbeating daemon dead, FOREVER, and relaunch-looped
# every ~10s. It ran that way undetected until somebody happened to read its log.
#
# Two properties made that a class and not a one-off:
#
#   1. THE GUARD COULD NOT OBSERVE THE THING IT GUARDS, AND NOTHING DETECTED THAT.
#      It had two independent signals — a fresh heartbeat and a pid — and it
#      required BOTH (`[[ -n "$(daemon_pids)" ]] && (( age <= STALE_AFTER ))`), so
#      the WORKING signal was overruled by the BROKEN one. "Cannot determine" was
#      silently collapsed into "dead".
#
#   2. A NEGATIVE THAT WAS NEVER ONCE A POSITIVE WAS BELIEVED ANYWAY. A channel
#      that has returned "not there" on every call since the process started is
#      indistinguishable from a channel that is broken. The supervisor relaunched
#      and relaunched and never once asked "or is it me?".
#
# A static lint could not have caught it. The supervisor's own launch line agreed
# with its own pattern; REALITY did not, because the live daemon had been started
# by a different caller with an extra flag. The mismatch was invisible in the file
# and only existed at runtime. So the measure has to be a runtime one.
#
# THE CONTRACT
# ------------
# Observation is THREE-VALUED, never two:
#
#     present       — my target is there. Do nothing.
#     absent        — my target is really not there. Corrective action permitted.
#     unobservable  — I CANNOT TELL. Corrective action FORBIDDEN. Alarm, loudly.
#
# `unobservable` is the entire point. It is the state the specimen lacked, and the
# reason it failed silently for hours instead of noisily in ten seconds.
#
# IDENTITY CHANNELS vs HEALTH. This folds IDENTITY only — "is my target there".
# Whether a present target is doing its job (heartbeat freshness, queue progress)
# is a SEPARATE axis, and folding the two is itself the specimen's bug: a live
# process with a stale heartbeat is `present` + wedged, which is actionable, not
# `unobservable`. Callers ask this for identity, then apply their own health test.
#
# TWO INDEPENDENT DETECTORS, because either alone has a blind spot:
#
#   A. CROSS-CHANNEL DISAGREEMENT. Register >=2 identity channels. If they
#      disagree, SOMETHING is lying and you do not know which — `unobservable`.
#      This fires on the specimen instantly: heartbeat-pid said present, the name
#      pattern said absent.
#
#   B. THE BLIND STREAK — launch is the positive control. Call `og_note_launch`
#      after (re)starting the target. If the very next verdict is not `present`,
#      a counter climbs; at OG_BLIND_STREAK_MAX consecutive launch-without-sighting
#      cycles the verdict is FORCED to `unobservable`. A watchdog that starts a
#      thing and still cannot see it has evidence about its own eyes, not about the
#      thing. This is the net for a watchdog with only one channel, and it is what
#      would have converted the specimen's forever-loop into an alarm inside ~30s.
#
# KILL TARGETS COME FROM THE AUTHORITATIVE CHANNEL ONLY. Corroborating channels
# exist to disagree, never to name a pid to signal. `og_proc_scan` is a read-only
# /proc walk and its output is documented NOT-A-KILL-TARGET: this is a shared host
# and a name pattern is a wildcard over other sessions' processes
# (INC-20260731-broad-process-pattern-kills).
#
# USAGE (sourced; safe under `set -euo pipefail`)
# -----------------------------------------------
#     source /workspace/scripts/coordination/observer_guard.sh
#     og_init my_supervisor
#
#     og_round_begin
#     og_channel hb_pid    "$(og_pid_alive "$(og_json_pid "$HB")" runner.py)"
#     og_channel proc_scan "$(og_present_if_any "$(og_proc_scan runner.py)")"
#     state=$(og_verdict) || true          # 0 present / 1 absent / 3 unobservable
#
#     case "$state" in
#       present)      : ;;                                   # nothing to do
#       absent)       start_target; og_note_launch ;;        # action permitted
#       unobservable) og_alarm "$(og_why)"; ;;               # action FORBIDDEN
#     esac
#
# Every watchdog that sources this MUST also expose an `observe` subcommand
# printing `state=<present|absent|unobservable>` and exiting 0/1/3. That uniform
# entrypoint is what makes the contract externally testable for every watchdog by
# one harness (`tests/test_observer_contract.py`) instead of per-file tests that a
# sibling watchdog silently never gets.
#
# =============================================================================

# Idempotent source guard — a supervisor may source this from several helpers.
if [[ -n "${_OG_SOURCED:-}" ]]; then return 0 2>/dev/null || true; fi
_OG_SOURCED=1

OG_EPYC_ROOT="${EPYC_ROOT:-/workspace}"

# Where the loud breadcrumb lands. Overridable so tests never write to the real
# alert dir (and so a sandboxed supervisor cannot mask a real production alarm).
OG_STATE_DIR="${OG_STATE_DIR:-${OG_EPYC_ROOT}/logs/observer_alerts}"

# Consecutive launch-without-sighting cycles before the verdict is forced to
# `unobservable`. 3 is deliberate: one is a slow start, two is bad luck, three is
# a pattern, and at a 10s supervisor cadence it alarms in half a minute.
OG_BLIND_STREAK_MAX="${OG_BLIND_STREAK_MAX:-3}"

OG_NAME="${OG_NAME:-unnamed_observer}"
OG_CHANNELS=()
OG_WHY=""

# --------------------------------------------------------------------------- #
# Lifecycle
# --------------------------------------------------------------------------- #

og_init() {
  OG_NAME="${1:?og_init needs an observer name}"
  mkdir -p "$OG_STATE_DIR" 2>/dev/null || true
  OG_CHANNELS=()
  OG_WHY=""
}

og_state_file() { printf '%s/%s.json\n' "$OG_STATE_DIR" "$OG_NAME"; }

# Start a fresh observation round. Channels do NOT carry across rounds; a stale
# channel from the previous tick is a lie about the present one.
og_round_begin() { OG_CHANNELS=(); OG_WHY=""; }

# og_channel <name> <present|absent|unavailable> [detail]
#
# `unavailable` is a first-class input, not an error: it means THIS channel could
# not be evaluated (tool missing, file unreadable, permission denied). Callers
# must never translate an unavailable channel into `absent` — doing so is the bug.
og_channel() {
  local name="${1:?}" state="${2:?}" detail="${3:-}"
  case "$state" in
    present|absent|unavailable) : ;;
    *) state="unavailable"; detail="invalid channel state '${2}' (${detail})" ;;
  esac
  OG_CHANNELS+=("${name}|${state}|${detail}")
}

# The reason for the last verdict.
#
# Persisted to a file rather than left in a shell variable ON PURPOSE: the natural
# call is `state=$(og_verdict)`, and a command substitution is a SUBSHELL — any
# variable `og_verdict` set there is gone by the time the caller reads it. A
# reason that silently reads empty in the one idiom everybody uses is a guard that
# alarms without saying why, which is most of the way back to the original bug.
_og_why_file() { printf '%s/%s.why\n' "$OG_STATE_DIR" "$OG_NAME"; }

og_why() {
  local f; f="$(_og_why_file)"
  if [[ -r "$f" ]]; then cat "$f" 2>/dev/null || true; else printf '%s\n' "$OG_WHY"; fi
}

# --------------------------------------------------------------------------- #
# The fold
# --------------------------------------------------------------------------- #
#
# Truth table, in evaluation order. `n_p`/`n_a`/`n_u` count present/absent/
# unavailable channels.
#
#   n_p>0 && n_a>0            -> unobservable   channels disagree; one is lying
#   n_p>0                     -> present
#   n_a>0 && n_u==0           -> absent         every channel that could speak agrees
#   n_a>0 && n_u>0            -> unobservable   partial blindness is blindness
#   nothing evaluable         -> unobservable
#   (any non-present verdict) && blind_streak >= MAX -> unobservable (forced)
#
# The `n_a>0 && n_u>0` row is the one people argue with, so: a watchdog that
# refuses to restart a genuinely dead target while HALF ITS EYES ARE SHUT and
# says so at full volume is strictly better than one that restart-loops in
# silence. The specimen proves which failure actually costs hours.
og_verdict() {
  local n_p=0 n_a=0 n_u=0 entry name state detail
  local dis_p="" dis_a="" dis_u=""

  for entry in ${OG_CHANNELS[@]+"${OG_CHANNELS[@]}"}; do
    name="${entry%%|*}"
    state="${entry#*|}"; state="${state%%|*}"
    detail="${entry##*|}"
    case "$state" in
      present)     n_p=$(( n_p + 1 )); dis_p="${dis_p}${name} " ;;
      absent)      n_a=$(( n_a + 1 )); dis_a="${dis_a}${name} " ;;
      unavailable) n_u=$(( n_u + 1 )); dis_u="${dis_u}${name}(${detail}) " ;;
    esac
  done

  local verdict
  if (( n_p > 0 && n_a > 0 )); then
    verdict="unobservable"
    OG_WHY="channels DISAGREE: present=[${dis_p% }] absent=[${dis_a% }] — one of these observers is broken and this observer cannot tell which"
  elif (( n_p > 0 )); then
    verdict="present"
    OG_WHY="present per [${dis_p% }]"
  elif (( n_a > 0 && n_u == 0 )); then
    verdict="absent"
    OG_WHY="absent per [${dis_a% }]; no channel unavailable"
  elif (( n_a > 0 && n_u > 0 )); then
    verdict="unobservable"
    OG_WHY="partial blindness: absent=[${dis_a% }] but unavailable=[${dis_u% }] — an unavailable channel is not a negative"
  else
    verdict="unobservable"
    OG_WHY="no identity channel could be evaluated (unavailable=[${dis_u% }])"
  fi

  # Detector B: launch is the positive control.
  if [[ "$verdict" != "present" ]]; then
    local streak; streak="$(og_blind_streak)"
    if (( streak >= OG_BLIND_STREAK_MAX )); then
      verdict="unobservable"
      OG_WHY="BLIND STREAK ${streak} >= ${OG_BLIND_STREAK_MAX}: this observer has (re)launched its target ${streak}x and still never seen it — the evidence now points at the observer, not the target. (${OG_WHY})"
    fi
  fi

  mkdir -p "$OG_STATE_DIR" 2>/dev/null || true
  printf '%s\n' "$OG_WHY" > "$(_og_why_file)" 2>/dev/null || true

  printf '%s\n' "$verdict"
  case "$verdict" in
    present)      return 0 ;;
    absent)       return 1 ;;
    unobservable) return 3 ;;
  esac
}

# --------------------------------------------------------------------------- #
# Channel primitives
# --------------------------------------------------------------------------- #

# og_json_pid <file> — the pid a target publishes about ITSELF. The authoritative
# identity channel: the target is the only party that cannot be wrong about which
# process it is. Prints the pid, or nothing.
og_json_pid() {
  local f="${1:-}"
  [[ -n "$f" && -r "$f" ]] || return 0
  python3 - "$f" <<'PY_EOF' 2>/dev/null || true
import json, sys
try:
    pid = json.load(open(sys.argv[1])).get("pid")
    if pid is not None:
        print(int(pid))
except Exception:
    pass
PY_EOF
}

# og_pid_alive <pid> [cmdline_substring] — echoes present|absent|unavailable.
#
# With a substring it also CONFIRMS identity: a bare `/proc/<pid>` check says a
# process exists, not that it is YOUR process — pids are recycled, and a recycled
# pid is a false `present` that keeps a watchdog asleep over a dead target.
og_pid_alive() {
  local pid="${1:-}" want="${2:-}"
  if [[ -z "$pid" ]]; then printf 'absent\n'; return 0; fi
  if [[ ! "$pid" =~ ^[0-9]+$ ]]; then printf 'unavailable\n'; return 0; fi
  if [[ ! -d "/proc/${pid}" ]]; then printf 'absent\n'; return 0; fi
  if [[ -z "$want" ]]; then printf 'present\n'; return 0; fi
  local cmd=""
  if [[ -r "/proc/${pid}/cmdline" ]]; then
    cmd="$(tr '\0' ' ' < "/proc/${pid}/cmdline" 2>/dev/null || true)"
  else
    # The process exists but we may not read its cmdline (another user's, or it
    # exited between the two checks). That is not evidence of absence.
    printf 'unavailable\n'; return 0
  fi
  if [[ "$cmd" == *"$want"* ]]; then printf 'present\n'; else printf 'absent\n'; fi
}

# og_proc_scan <substring> — read-only /proc walk. Prints matching pids.
#
# ***THE OUTPUT OF THIS FUNCTION IS NOT A KILL TARGET.*** It exists to CORROBORATE
# or CONTRADICT the authoritative channel, nothing else. On this shared host a
# name/argv match is a wildcard over other sessions' processes, and a guard's own
# argv necessarily contains the names it guards
# (INC-20260731-broad-process-pattern-kills). Signal the authoritative pid, never
# a scan result.
og_proc_scan() {
  local want="${1:?}" d pid cmd
  # SELF-EXCLUSION IS LOAD-BEARING AND pid-EXCLUSION ALONE IS NOT ENOUGH.
  # CLAUDE.md states the general hazard: "a guard process's argv necessarily
  # contains the names it guards". Excluding $$/$BASHPID/$PPID misses every
  # command-substitution subshell and every `bash -c` copy, each of which is a
  # DIFFERENT pid carrying an IDENTICAL cmdline that contains `$want`. Caught by
  # this function's own first test run, which reported `present` for a scan of a
  # string that existed nowhere but in the test's own command line.
  local own=""
  [[ -r "/proc/$$/cmdline" ]] && own="$(tr '\0' ' ' < "/proc/$$/cmdline" 2>/dev/null || true)"
  for d in /proc/[0-9]*; do
    pid="${d#/proc/}"
    [[ "$pid" == "$$" || "$pid" == "${BASHPID:-0}" || "$pid" == "$PPID" ]] && continue
    [[ -r "${d}/cmdline" ]] || continue
    cmd="$(tr '\0' ' ' < "${d}/cmdline" 2>/dev/null || true)"
    [[ -n "$cmd" ]] || continue
    [[ -n "$own" && "$cmd" == "$own" ]] && continue
    [[ "$cmd" == *"$want"* ]] && printf '%s\n' "$pid"
  done
  return 0
}

# og_present_if_any <pids...> — turn a pid list into a channel state. Empty is
# `absent`, never `unavailable`: the scan RAN and saw nothing. A scan that could
# not run must be reported `unavailable` by its caller.
og_present_if_any() {
  local pids="${*:-}"
  pids="${pids//[$'\n\t ']/}"
  if [[ -n "$pids" ]]; then printf 'present\n'; else printf 'absent\n'; fi
}

# og_tool_channel <tool> <substring> — a name-pattern channel that reports
# `unavailable` (NOT absent) when the tool itself is missing. The specimen family:
# `pgrep` absent from PATH made a two-state guard say "target dead".
og_tool_channel() {
  local tool="${1:?}" want="${2:?}"
  command -v "$tool" >/dev/null 2>&1 || { printf 'unavailable\n'; return 0; }
  og_present_if_any "$(og_proc_scan "$want")"
}

# --------------------------------------------------------------------------- #
# The blind streak (detector B)
# --------------------------------------------------------------------------- #

_og_streak_file() { printf '%s/%s.streak\n' "$OG_STATE_DIR" "$OG_NAME"; }

og_blind_streak() {
  local f; f="$(_og_streak_file)"
  if [[ -r "$f" ]]; then
    local v; v="$(cat "$f" 2>/dev/null || echo 0)"
    [[ "$v" =~ ^[0-9]+$ ]] && { printf '%s\n' "$v"; return 0; }
  fi
  printf '0\n'
}

# Call immediately AFTER (re)launching the target. Launch is the positive control:
# from here on, "still cannot see it" is evidence about the observer.
og_note_launch() {
  mkdir -p "$OG_STATE_DIR" 2>/dev/null || true
  local n; n="$(og_blind_streak)"
  printf '%s\n' "$(( n + 1 ))" > "$(_og_streak_file)" 2>/dev/null || true
}

# Call on any `present` verdict. Seeing the target is proof the eyes work.
og_note_sighting() { printf '0\n' > "$(_og_streak_file)" 2>/dev/null || true; }

# --------------------------------------------------------------------------- #
# LOUD
# --------------------------------------------------------------------------- #
#
# The specimen's failure was not that it lacked a log line — it logged every 10
# seconds for hours. It was that nothing DISTINGUISHED those lines from ordinary
# noise and nothing outside the log could see the state. So the alarm is:
#   1. a fixed, greppable token on stderr, banner-framed;
#   2. a machine-readable breadcrumb with an mtime, so freshness is checkable;
#   3. a non-zero exit from `observer_guard.sh alerts`, which any health fold,
#      cron, or CI step can call without knowing which watchdogs exist.
OG_ALARM_TOKEN="OBSERVER-BLIND"

og_alarm() {
  local detail="${1:-${OG_WHY}}"
  local ts; ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  {
    printf '\n'
    printf '!!! %s !!! %s cannot observe its target\n' "$OG_ALARM_TOKEN" "$OG_NAME"
    printf '    at   : %s\n' "$ts"
    printf '    why  : %s\n' "$detail"
    printf '    NOTE : corrective action is SUPPRESSED while blind. Fix the observer,\n'
    printf '           not the target — the target may be perfectly healthy.\n'
    printf '\n'
  } >&2
  mkdir -p "$OG_STATE_DIR" 2>/dev/null || true
  local f; f="$(og_state_file)"
  python3 - "$f" "$OG_NAME" "$ts" "$detail" "$(og_blind_streak)" <<'PY_EOF' 2>/dev/null || true
import json, os, sys
path, name, ts, detail, streak = sys.argv[1:6]
tmp = f"{path}.{os.getpid()}.tmp"
with open(tmp, "w") as fh:
    json.dump({"observer": name, "state": "unobservable", "ts": ts,
               "detail": detail, "blind_streak": int(streak or 0)}, fh, indent=2)
    fh.write("\n")
os.replace(tmp, path)
PY_EOF
}

# Clear the breadcrumb once the observer can see again. Only ever called on a
# `present` verdict — clearing on `absent` would erase the alarm of a watchdog
# that is blind AND whose target then really died.
og_clear() {
  rm -f "$(og_state_file)" 2>/dev/null || true
}

# --------------------------------------------------------------------------- #
# CLI: `observer_guard.sh alerts`
# --------------------------------------------------------------------------- #
# Exit 3 if any observer is currently blind, 0 otherwise. Discovers them from the
# breadcrumb dir, so it needs no list of watchdogs and cannot go stale as new ones
# are added.
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  case "${1:-alerts}" in
    alerts)
      shopt -s nullglob
      found=0
      for f in "$OG_STATE_DIR"/*.json; do
        found=1
        printf '%s %s\n' "$OG_ALARM_TOKEN" "$f"
        cat "$f"
      done
      (( found )) && exit 3
      printf 'no blind observers (%s)\n' "$OG_STATE_DIR"
      exit 0
      ;;
    *)
      printf 'usage: %s [alerts]\n' "$(basename "$0")" >&2
      exit 64
      ;;
  esac
fi
