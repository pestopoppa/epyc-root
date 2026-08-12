#!/bin/bash
# FIXTURE — THE DEFECT, PRESERVED ON PURPOSE. DO NOT "FIX" THIS FILE.
#
# This is the permanent mutation for tests/test_observer_contract.py. It is the
# specimen's shape, reduced: ONE identity channel, believed absolutely, with two
# states where three are needed. `observe` can only ever print `present` or
# `absent`; there is no way for it to say "I cannot tell", so a broken channel and
# a dead target are the same answer — and `once` relaunches on that answer.
#
# tests/test_observer_contract.py runs the SAME battery it runs against every real
# observer against this file and asserts the battery FAILS, naming the drift case.
# That is what stops the harness from silently becoming vacuous: if someone waters
# the battery down, the mutation stops being detected and the mutation test — a
# real pytest test, collected and counted by the reporter, not an assert buried in
# a main() nobody runs — goes red.
#
# The specimen it reproduces: bus_supervisor.sh identified the coordinator-daemon
# by an argv pattern that stopped matching when a flag was inserted into the live
# daemon's command line. Its heartbeat was fresh the entire time. One channel said
# "there", one said "not there", and the code ANDed them into "dead", forever.
set -euo pipefail

HEARTBEAT="${HEARTBEAT:?fixture needs HEARTBEAT}"
STUB="${RUNNER:-}"
MARKER="${LAUNCH_MARKER:-}"

# The single channel. No cross-check, no unavailable state.
target_alive() {
  local pid=""
  [[ -r "$HEARTBEAT" ]] && pid="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("pid",""))' "$HEARTBEAT" 2>/dev/null || true)"
  [[ -n "$pid" && -d "/proc/${pid}" ]]
}

case "${1:-observe}" in
  observe)
    if target_alive; then printf 'state=present\n'; exit 0
    else printf 'state=absent\n'; exit 1; fi
    ;;
  once)
    if ! target_alive; then
      [[ -n "$MARKER" ]] && : > "$MARKER"
      [[ -n "$STUB" && -x "$STUB" ]] && "$STUB" >/dev/null 2>&1 || true
    fi
    exit 0
    ;;
  *) printf 'usage: %s [observe|once]\n' "$(basename "$0")" >&2; exit 64 ;;
esac
