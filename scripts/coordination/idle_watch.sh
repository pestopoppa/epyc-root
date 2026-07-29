#!/bin/bash
# =============================================================================
# idle_watch.sh — return as soon as any main goes idle
# =============================================================================
#
# WHY: heartbeats lie. A main that finishes a task and sits at its prompt very
# often still has state:working in its heartbeat, so `rebuild` reports a busy
# fleet while two panes sit at an empty composer. On 2026-07-29 the operator had
# to point out an idle `inference` and an idle `auditor` that the bus reported as
# working. Pane state is the ground truth; the heartbeat is a claim.
#
# WHAT: polls each roster window's pane for a BUSY marker and exits 0 the moment
# one or more mains look idle, naming them. Exiting on the first idle main is the
# point — the coordinator's background-task notification then fires immediately,
# instead of idleness being discovered on the next manual poll.
#
# BUSY markers, both TUIs:
#   claude : "esc to interrupt"
#   codex  : "Working ("  /  "esc to interrupt"
# Neither appears at a settled prompt. A pane that cannot be captured is reported
# as UNKNOWN, never as idle — the C14 polarity: absence of evidence is not
# evidence of idleness, and a false idle hands out work to a busy main.
#
# Usage:  idle_watch.sh [poll_seconds] [max_seconds]
set -uo pipefail

POLL="${1:-45}"
MAX="${2:-3600}"
SESSION="${SESSION:-agent}"
MAINS="${MAINS:-inference auditor mainA mainB}"

elapsed=0
while [ "$elapsed" -lt "$MAX" ]; do
  idle=""
  unknown=""
  for w in $MAINS; do
    if ! tmux has-session -t "$SESSION" 2>/dev/null; then
      echo "SESSION_GONE $SESSION"; exit 3
    fi
    pane=$(tmux capture-pane -p -t "$SESSION:$w" 2>/dev/null)
    if [ -z "$pane" ]; then
      unknown="$unknown $w"
      continue
    fi
    tail=$(printf '%s' "$pane" | tail -20)
    if printf '%s' "$tail" | grep -qE 'esc to interrupt|Working \('; then
      continue
    fi
    idle="$idle $w"
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
echo "NO_IDLE_WITHIN ${MAX}s"
exit 1
