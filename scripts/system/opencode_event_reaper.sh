#!/bin/bash
# opencode event-feed reaper — bounds opencode.db growth at the SOURCE.
# opencode keeps every streaming revision of every part in the `event` table (measured 1.7 GB/h
# under subagent load; 236 GB by 2026-09-07). This daemon prunes the events of sessions idle for
# more than IDLE_HOURS, every INTERVAL seconds. It NEVER touches session/message/part (the content),
# never touches a session updated within IDLE_HOURS (the live TUI and its running subagents), waits
# on the write lock rather than failing, and only VACUUMs when opencode is DEFINITELY not running.
#
# Run:   bash scripts/system/opencode_event_reaper.sh            (daemon; same as `run`)
#        bash scripts/system/opencode_event_reaper.sh once       (one reap iteration, no pidfile)
#        bash scripts/system/opencode_event_reaper.sh observe    (state=present|absent|unobservable, exit 0/1/3)
# Stop:  kill "$(cat /mnt/raid0/llm/tmp/opencode-reaper.pid)"   Log: /mnt/raid0/llm/tmp/opencode-reaper.log
#
# OBSERVATION CONTRACT (NI-OC-a, 2026-09-17; registry: scripts/coordination/observer_registry.json,
# contract v1). The original probe was a bare name-presence check (`pgrep -x opencode`): two-state,
# and a name pattern is a wildcard over other sessions' processes on this shared host
# (INC-20260731). It is replaced by observer_guard.sh's three-valued fold over two INDEPENDENT
# identity channels, neither of which is ever a kill target (the reaper never kills anything):
#
#   proc_scan  — read-only /proc walk for OPENCODE_MARK in a cmdline (og_proc_scan, self-excluding).
#                Default mark "opencode " (trailing space): argv[0] of the TUI is `opencode`, so its
#                cmdline is "opencode "; the reaper's own "opencode_event_reaper.sh" and
#                "opencode.db" do NOT match. A stray match (e.g. someone's `grep opencode x`) only
#                costs a deferred VACUUM — the safe direction.
#   db_fd      — read-only /proc/*/fd walk: does any process this user can inspect hold OPENCODE_DB
#                open? This is the channel VACUUM actually cares about, and it does not depend on
#                argv at all, so a drifted argv shows up as channel DISAGREEMENT, not as "absent".
#   hb_pid     — optional. If OPENCODE_PIDFILE names a JSON file carrying {"pid": N}, that pid is
#                checked (og_pid_alive + mark). opencode publishes no such file, so production runs
#                without it; the contract battery uses it as the authoritative channel.
#
# THE CONSUMER — the VACUUM decision — FAILS CLOSED and the third state takes the SAFE branch:
#
#     present       -> VACUUM withheld            (opencode is using the DB)
#     unobservable  -> VACUUM withheld + og_alarm (cannot tell; assume it is running; say so LOUDLY)
#     absent        -> VACUUM permitted           (every channel that could speak agrees it is gone)
#
# Freed pages are reused regardless, so the cost of a wrong non-VACUUM is a deferred shrink, never a
# corrupted live session. The reaper takes no other action on the verdict: it never launches or
# kills opencode, so og_note_launch is never called and the blind streak stays at 0 by design.
set -euo pipefail

REAPER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EPYC_ROOT="${EPYC_ROOT:-$(cd "${REAPER_DIR}/../.." && pwd)}"
IDLE_HOURS="${IDLE_HOURS:-2}"
INTERVAL="${INTERVAL:-1800}"
PRUNE="${REAPER_PRUNE:-${REAPER_DIR}/prune_agent_event_store.py}"
REAPER_PIDFILE="${REAPER_PIDFILE:-/mnt/raid0/llm/tmp/opencode-reaper.pid}"
# `-` not `:-`: an explicitly EMPTY OPENCODE_DB disables the db_fd channel (the contract sandbox has
# no real DB and a stand-in that holds nothing open); unset means the production default.
OPENCODE_DB="${OPENCODE_DB-/home/node/.local/share/opencode/opencode.db}"
OPENCODE_MARK="${OPENCODE_MARK:-opencode }"
OPENCODE_PIDFILE="${OPENCODE_PIDFILE:-}"

# shellcheck source=scripts/coordination/observer_guard.sh
source "${EPYC_ROOT}/scripts/coordination/observer_guard.sh"
og_init opencode_event_reaper

# db_fd channel: present|absent|unavailable. Read-only. NOT a kill target (nothing here is).
# `unavailable` when the DB path cannot be resolved or when not a single /proc/<pid>/fd directory
# was readable — a scan that could inspect nothing has not seen "nothing".
db_fd_channel() {
  local db="${1:-}" real d f pid target inspected=0
  [[ -n "$db" && -e "$db" ]] || { printf 'unavailable\n'; return 0; }
  real="$(readlink -f -- "$db" 2>/dev/null)" || { printf 'unavailable\n'; return 0; }
  [[ -n "$real" ]] || { printf 'unavailable\n'; return 0; }
  shopt -s nullglob
  for d in /proc/[0-9]*; do
    pid="${d#/proc/}"
    [[ "$pid" == "$$" || "$pid" == "${BASHPID:-0}" ]] && continue
    [[ -r "${d}/fd" && -x "${d}/fd" ]] || continue
    inspected=1
    for f in "${d}"/fd/*; do
      target="$(readlink -- "$f" 2>/dev/null || true)"
      if [[ "$target" == "$real" ]]; then printf 'present\n'; return 0; fi
    done
  done
  if (( inspected )); then printf 'absent\n'; else printf 'unavailable\n'; fi
}

# One observation round. Prints the verdict; exits 0/1/3 like og_verdict.
observe_opencode() {
  og_round_begin

  if [[ -n "$OPENCODE_PIDFILE" ]]; then
    local pid; pid="$(og_json_pid "$OPENCODE_PIDFILE")"
    if [[ ! -e "$OPENCODE_PIDFILE" ]]; then
      og_channel hb_pid absent "no pidfile at ${OPENCODE_PIDFILE}"
    elif [[ ! -r "$OPENCODE_PIDFILE" ]]; then
      og_channel hb_pid unavailable "pidfile unreadable"
    elif [[ -z "$pid" ]]; then
      og_channel hb_pid unavailable "pidfile carries no parsable pid"
    else
      og_channel hb_pid "$(og_pid_alive "$pid" "$OPENCODE_MARK")" "pid=${pid}"
    fi
  fi

  if [[ -r /proc/self/cmdline ]]; then
    og_channel proc_scan "$(og_present_if_any "$(og_proc_scan "$OPENCODE_MARK")")" "mark=${OPENCODE_MARK}"
  else
    og_channel proc_scan unavailable "/proc not readable"
  fi

  if [[ -n "$OPENCODE_DB" ]]; then
    og_channel db_fd "$(db_fd_channel "$OPENCODE_DB")" "db=${OPENCODE_DB}"
  fi

  og_verdict
}

# The consumer. Maps the three states onto the VACUUM flag; ONLY `absent` yields "--vacuum".
# Side effects: sighting bookkeeping on present, the LOUD alarm on unobservable.
vacuum_flag_for() {
  local state="${1:?}"
  case "$state" in
    absent)       printf -- '--vacuum\n' ;;
    present)      og_note_sighting; og_clear; printf '\n' ;;
    *)            og_alarm "$(og_why)"; printf '\n' ;;
  esac
}

reap_once() {
  local state vac db_size
  state="$(observe_opencode)" || true   # og_verdict exits 1/3 by design; set -e would abort here
  vac="$(vacuum_flag_for "$state")"
  case "$state" in
    absent)       echo "[$(date -u +%FT%TZ)] reap idle>${IDLE_HOURS}h --vacuum (opencode absent: $(og_why))" ;;
    present)      echo "[$(date -u +%FT%TZ)] reap idle>${IDLE_HOURS}h (no vacuum: opencode running)" ;;
    *)            echo "[$(date -u +%FT%TZ)] reap idle>${IDLE_HOURS}h (no vacuum: ${OG_ALARM_TOKEN} — $(og_why))" ;;
  esac
  # $vac is intentionally unquoted-when-empty: it is either "--vacuum" or nothing.
  # shellcheck disable=SC2086
  python3 "$PRUNE" --idle-hours "$IDLE_HOURS" --apply $vac 2>&1 | tail -3 || echo "prune failed (rc=$?)"
  if [[ -n "$OPENCODE_DB" && -e "$OPENCODE_DB" ]]; then
    db_size="$(stat -c %s "$OPENCODE_DB" 2>/dev/null | awk '{printf "%.1f GB",$1/1e9}' || true)"
    echo "[$(date -u +%FT%TZ)] db=${db_size:-?}"
  fi
}

case "${1:-run}" in
  observe)
    state="$(observe_opencode)" || true
    printf 'state=%s\n' "$state"
    printf 'why=%s\n' "$(og_why)"
    case "$state" in
      absent) printf 'vacuum=permitted\n' ;;
      *)      printf 'vacuum=withheld\n' ;;
    esac
    case "$state" in present) exit 0 ;; absent) exit 1 ;; *) exit 3 ;; esac
    ;;
  once)
    reap_once
    exit 0
    ;;
  run)
    echo $$ > "$REAPER_PIDFILE"
    while true; do
      reap_once
      sleep "$INTERVAL"
    done
    ;;
  *)
    printf 'usage: %s [run|once|observe]\n' "$(basename "$0")" >&2
    exit 64
    ;;
esac
