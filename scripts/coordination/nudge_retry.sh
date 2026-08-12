#!/bin/bash
# nudge_retry.sh <agent> <message> [attempts] — retry a nudge, SURFACING the refusal reason.
#
# WHY THIS EXISTS: the naive retry loop pipes `nudge` through `grep -q nudged`, which
# swallows WHY the adapter refused. On 2026-07-29 that hid a rate-limit refusal and
# burned several minutes on a main that was reachable the whole time. Refusals are
# diagnostic — a quiet-window refusal self-clears in ~20s, a rate-limit refusal needs
# --min-interval-s, and a heartbeat refusal needs the main to hit a boundary. They are
# not interchangeable, so they must be visible.
set -uo pipefail
# Canonical adapter path from ONE place (B7, 2026-08-12): this used to bake
# /workspace/scripts/coordination/tmux_adapter.py, so a lane-worktree copy of this
# helper would silently drive whatever adapter that lane happened to have checked out.
_NR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${_NR_DIR}/../lib/env.sh"
AGENT="${1:?agent}"
MSG="${2:?message}"
ATTEMPTS="${3:-12}"
for i in $(seq 1 "$ATTEMPTS"); do
  out=$(timeout 90 python3 "${EPYC_TMUX_ADAPTER}" nudge \
          --agent "$AGENT" --min-interval-s 20 --message "$MSG" 2>&1 | tail -3)
  if printf '%s' "$out" | grep -q 'nudged'; then
    echo "[$AGENT] DELIVERED on attempt $i"
    exit 0
  fi
  echo "[$AGENT] attempt $i refused: $(printf '%s' "$out" | tr '\n' ' ')"
  sleep 15
done
echo "[$AGENT] UNDELIVERED after $ATTEMPTS attempts"
exit 1
