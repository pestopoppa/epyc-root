#!/bin/bash
# FIXTURE — a MINIMAL watchdog that satisfies the observation contract.
#
# This is the positive control for tests/test_observer_contract.py. The behavioural
# battery is run against this file as well as against every registered observer,
# and it must PASS. That is not decoration: a battery only the broken fixture can
# fail is a battery that might be rejecting the compliant idiom too, which is a
# defect this repo has already shipped once (a guard that forbade its own idiom).
#
# It is also the smallest readable statement of what adoption costs: two identity
# channels, one fold, one `observe` entrypoint, and action gated on `absent`.
set -euo pipefail

EPYC_ROOT="${EPYC_ROOT:-/workspace}"
HEARTBEAT="${HEARTBEAT:?fixture needs HEARTBEAT}"
MARK="${RUNNER_MARK:?fixture needs RUNNER_MARK}"
STUB="${RUNNER:-}"
MARKER="${LAUNCH_MARKER:-}"

# shellcheck source=scripts/coordination/observer_guard.sh
source "${EPYC_ROOT}/scripts/coordination/observer_guard.sh"
og_init compliant_fixture

observe_target() {
  og_round_begin
  local pid; pid="$(og_json_pid "$HEARTBEAT")"

  if [[ ! -e "$HEARTBEAT" ]]; then
    og_channel hb_pid absent "no heartbeat file"
  elif [[ ! -r "$HEARTBEAT" ]]; then
    og_channel hb_pid unavailable "heartbeat unreadable"
  elif [[ -z "$pid" ]]; then
    og_channel hb_pid unavailable "heartbeat carries no parsable pid"
  else
    og_channel hb_pid "$(og_pid_alive "$pid" "$MARK")" "pid=$pid"
  fi

  if [[ -r /proc/self/cmdline ]]; then
    og_channel proc_scan "$(og_present_if_any "$(og_proc_scan "$MARK")")"
  else
    og_channel proc_scan unavailable "/proc not readable"
  fi

  og_verdict
}

case "${1:-observe}" in
  observe)
    state="$(observe_target)" || true   # og_verdict exits 1/3 by design; set -e would abort here
    printf 'state=%s\n' "$state"
    printf 'why=%s\n' "$(og_why)"
    case "$state" in present) exit 0 ;; absent) exit 1 ;; *) exit 3 ;; esac
    ;;
  once)
    state="$(observe_target)" || true   # og_verdict exits 1/3 by design; set -e would abort here
    case "$state" in
      unobservable)
        # The whole point: blind means HANDS OFF.
        og_alarm "$(og_why)"
        exit 0
        ;;
      present) og_note_sighting; og_clear; exit 0 ;;
      absent)
        [[ -n "$MARKER" ]] && : > "$MARKER"
        [[ -n "$STUB" && -x "$STUB" ]] && "$STUB" >/dev/null 2>&1 || true
        og_note_launch
        exit 0
        ;;
    esac
    ;;
  *) printf 'usage: %s [observe|once]\n' "$(basename "$0")" >&2; exit 64 ;;
esac
