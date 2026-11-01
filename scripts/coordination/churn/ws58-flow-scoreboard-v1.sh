#!/bin/bash
# ws58 2026-11-01: FLOW-SCOREBOARD.md every 10 min (rows armed, blocking tasks closed, idle hours caused by blocked rows).
# Replaces ws58-code-scoreboard.sh (50-tick quota + pane nudges, retired). No tmux writes. Source: scripts/coordination/flow_scoreboard.py.
set -euo pipefail
F=/mnt/raid0/llm/tmp/compute-flags
echo "$(date -u +%FT%TZ) flow-scoreboard start pid=$$ sha256=$(sha256sum $F/bin/flow_scoreboard.py | cut -c1-16)" >> $F/flow-scoreboard.log
echo $$ > $F/ws58-flow-scoreboard.pid
while :; do
  python3 -I $F/bin/flow_scoreboard.py >> $F/flow-scoreboard.log 2>&1 || :
  sleep 600
done
