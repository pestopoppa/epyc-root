#!/bin/bash
# ws58 2026-10-31 (operator "make sure this gap gets fixed"): zero-token keeper watchdog. Every 2 min: if the keeper
# MAIN LOOP (pid in ws58-calendar-keeper.pid, argv naming the keeper script) is gone, start the keeper named in
# ws58-calendar-keeper.current. Never kills anything. Job wrapper subshells share the keeper's argv, so liveness
# is judged only by the recorded main-loop pid.
set -euo pipefail
F=/mnt/raid0/llm/tmp/compute-flags
LOG=$F/ws58-keeper-watchdog.log
echo "$(date -u +%FT%TZ) watchdog start pid=$$" >> $LOG
while :; do
  K=$(cat $F/ws58-calendar-keeper.current 2>/dev/null || true)
  p=$(cat $F/ws58-calendar-keeper.pid 2>/dev/null || true)
  args=$(ps -o args= -p "$p" 2>/dev/null || true)   # no pipe: pipefail + grep -q reads a live keeper as dead
  if [ -n "$K" ] && [ -f "$F/$K" ] && ! { [ -n "$p" ] && [[ $args == *"$K"* ]]; }; then
    echo "$(date -u +%FT%TZ) keeper main loop (pid ${p:-none}) not alive; starting $K" >> $LOG
    (cd $F && setsid bash "$F/$K" </dev/null >/dev/null 2>&1 &)
    sleep 60
  fi
  sleep 120
done
