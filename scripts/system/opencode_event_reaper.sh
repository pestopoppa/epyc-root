#!/bin/bash
# opencode event-feed reaper — bounds opencode.db growth at the SOURCE.
# opencode keeps every streaming revision of every part in the `event` table (measured 1.7 GB/h
# under subagent load; 236 GB by 2026-09-07). This daemon prunes the events of sessions idle for
# more than IDLE_HOURS, every INTERVAL seconds. It NEVER touches session/message/part (the content),
# never touches a session updated within IDLE_HOURS (the live TUI and its running subagents), waits
# on the write lock rather than failing, and only VACUUMs when no opencode process is running.
# Stop: kill "$(cat /mnt/raid0/llm/tmp/opencode-reaper.pid)"   Log: /mnt/raid0/llm/tmp/opencode-reaper.log
set -uo pipefail
IDLE_HOURS="${IDLE_HOURS:-2}"; INTERVAL="${INTERVAL:-1800}"
PRUNE="$(dirname "$(readlink -f "$0")")/prune_agent_event_store.py"
echo $$ > /mnt/raid0/llm/tmp/opencode-reaper.pid
while true; do
  if pgrep -x opencode >/dev/null 2>&1; then VAC=""; else VAC="--vacuum"; fi
  echo "[$(date -u +%FT%TZ)] reap idle>${IDLE_HOURS}h ${VAC:-(no vacuum: opencode running)}"
  python3 "$PRUNE" --idle-hours "$IDLE_HOURS" --apply $VAC 2>&1 | tail -3
  echo "[$(date -u +%FT%TZ)] db=$(stat -c %s /home/node/.local/share/opencode/opencode.db | awk '{printf "%.1f GB",$1/1e9}')"
  sleep "$INTERVAL"
done
