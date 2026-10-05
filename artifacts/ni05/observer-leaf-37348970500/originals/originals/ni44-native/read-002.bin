#!/bin/bash
# =============================================================================
# idle_watch.sh — return as soon as any main goes idle
# =============================================================================
#
# WHY: heartbeats can stay `working` after a task finishes, so `rebuild` may
# report a busy fleet while an agent is idle. This watcher reports idle only
# when the existing adapter probe positively qualifies the runtime state.
#
# WHAT: polls each roster agent through the existing authoritative adapter probe
# and exits 0 the moment one or more agents have qualified idle evidence, naming
# them. Exiting on the first idle main is the
# point — the coordinator's background-task notification then fires immediately,
# instead of idleness being discovered on the next manual poll.
#
# The existing tmux_adapter probe must return successful JSON with
# runtime_decided=true, runtime_state=idle, and nudge_ok=true. Every other result
# is UNKNOWN and cannot produce an idle report. Pane text and marker absence do
# not grant idle authority.
#
# Usage:  idle_watch.sh [poll_seconds] [max_seconds]
set -uo pipefail

POLL="${1:-45}"
MAX="${2:-3600}"
SESSION="${SESSION:-agent}"
MAINS="${MAINS:-inference auditor mainA mainB}"
_IS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${_IS_DIR}/../lib/env.sh"
ADAPTER="${EPYC_TMUX_ADAPTER}"

unknown=""
elapsed=0
while [ "$elapsed" -lt "$MAX" ]; do
  idle=""
  unknown=""
  for w in $MAINS; do
    if ! tmux has-session -t "$SESSION" 2>/dev/null; then
      echo "SESSION_GONE $SESSION"; exit 3
    fi
    if python3 "${_IS_DIR}/qualified_idle_probe.py" --agent "$w" --adapter "$ADAPTER" \
         >/dev/null 2>&1; then
      idle="$idle $w"
    else
      unknown="$unknown $w"
    fi
  done
  if [ -n "$idle" ]; then
    echo "IDLE:$idle"
    [ -n "$unknown" ] && echo "UNKNOWN:$unknown"
    echo "elapsed=${elapsed}s"
    exit 0
  fi
  sleep "$POLL"
  elapsed=$((elapsed + POLL))
done
if [ -n "$unknown" ]; then
  echo "UNKNOWN:$unknown"
fi
echo "NO_IDLE_WITHIN ${MAX}s"
exit 1
