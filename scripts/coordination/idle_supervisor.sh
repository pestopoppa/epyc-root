#!/bin/bash
# =============================================================================
# idle_supervisor.sh — continuously detect idle mains and re-nudge them
# =============================================================================
#
# WHY: an idle main is a coordination failure, and on 2026-07-29 the OPERATOR —
# not the coordinator — caught idle mains four separate times, including `mainA`
# while it was holding the ENTIRE machine for an exclusive E5 decision-grade
# window. A main that stops while holding an exclusive resource is the most
# expensive idle state there is: nothing else can use the host either.
#
# The previous tool (idle_watch.sh) returned on the FIRST idle main and then had
# to be restarted by hand, so coverage had holes exactly when the coordinator was
# busy. This runs continuously and ACTS rather than reporting.
#
# WHAT IT DOES: polls every main's pane. A main with no busy marker for
# CONFIRM consecutive polls is treated as idle and sent a short continue-nudge
# through tmux_adapter.py — never raw send-keys, so every guard still applies.
#
# WHAT IT DELIBERATELY DOES NOT DO:
#   * it never bypasses a refusal. A refusal is logged with its reason and
#     retried on the next sweep. The adapter's guards exist because typing into
#     a pane mid-generation corrupts someone else's work.
#   * it never assigns work. The nudge says "drain your bus and continue" — the
#     queue and the briefs hold the actual assignments, so this cannot invent a
#     task or contradict a dispatch.
#   * a pane it cannot capture is UNKNOWN, never idle. A false idle types into a
#     busy main; a false busy costs one sweep.
#
# KNOWN GAP, and it is the reason this is a supervisor and not a fix: if a main's
# heartbeat still reads `working` while it sits at its prompt, the adapter
# refuses on state and this loop cannot deliver. That deadlock is filed for the
# C-series owner. Until it is fixed, those refusals surface in the log and need a
# human relay — which is exactly the cost this file exists to measure.
#
# Usage: idle_supervisor.sh [poll_s] [confirm_polls] [max_s]
set -uo pipefail

POLL="${1:-40}"
CONFIRM="${2:-2}"
MAX="${3:-86400}"
SESSION="${SESSION:-agent}"
MAINS="${MAINS:-inference auditor mainA mainB mainC mainD}"
# Canonical roots from ONE place (B3, 2026-08-12): a lane-worktree copy of this
# script must still drive the canonical adapter and write the canonical log.
_IS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${_IS_DIR}/../lib/env.sh"
ADAPTER="${EPYC_TMUX_ADAPTER}"
LOG="${LOG:-${LOG_DIR}/idle_supervisor.log}"

MSG='You appear to be idle at your prompt. Run: python3 scripts/coordination/session_bus.py drain --agent <your-id> --triage — then continue with your current assignment, or take the next item from coordination/session-bus/tasks/BACKLOG-DISPATCH-QUEUE.md respecting its collision map. Never sit idle: take the next item yourself rather than waiting to be told. Set state:idle in your heartbeat ONLY when you are genuinely awaiting dispatch, and state:working otherwise — an idle main whose heartbeat still says working cannot be nudged at all and deadlocks until a human relays by hand. If you are blocked or need operator input, say so on the bus with action_required true and your own recommendation.'

log() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" | tee -a "$LOG"; }

mkdir -p "$(dirname "$LOG")"
declare -A STRIKES
for w in $MAINS; do STRIKES[$w]=0; done

log "idle_supervisor start poll=${POLL}s confirm=${CONFIRM} mains='${MAINS}'"
elapsed=0
while [ "$elapsed" -lt "$MAX" ]; do
  tmux has-session -t "$SESSION" 2>/dev/null || { log "SESSION $SESSION GONE — exiting"; exit 3; }
  for w in $MAINS; do
    pane=$(tmux capture-pane -p -t "$SESSION:$w" 2>/dev/null)
    if [ -z "$pane" ]; then
      STRIKES[$w]=0                      # uncapturable is UNKNOWN, never idle
      continue
    fi
    if printf '%s' "$pane" | tail -20 | grep -qE 'esc to interrupt|Working \('; then
      STRIKES[$w]=0
      continue
    fi
    STRIKES[$w]=$(( ${STRIKES[$w]} + 1 ))
    [ "${STRIKES[$w]}" -lt "$CONFIRM" ] && continue
    out=$(timeout 90 python3 "$ADAPTER" nudge --agent "$w" --min-interval-s 20 \
            --message "${MSG//<your-id>/$w}" 2>&1 | tail -3)
    if printf '%s' "$out" | grep -q 'nudged'; then
      log "RE-NUDGED $w after ${STRIKES[$w]} idle polls"
      STRIKES[$w]=0
    else
      log "REFUSED $w: $(printf '%s' "$out" | tr '\n' ' ')"
    fi
  done
  sleep "$POLL"
  elapsed=$((elapsed + POLL))
done
log "idle_supervisor exiting after ${MAX}s"
