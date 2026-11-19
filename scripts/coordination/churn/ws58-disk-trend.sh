#!/bin/bash
# ws58 2026-11-01 (operator: "Are we still leaking?"). Zero-token. Every 10 min append free GiB of /mnt/raid0/llm plus
# worktrees/trash sizes (hourly) to disk-trend.tsv, so a leak shows as a slope. Read-only except its own file.
set -euo pipefail
O=${DISK_TREND_OUT:-/mnt/raid0/llm/tmp/compute-flags/disk-trend.tsv}
H=$(cd "$(dirname "$0")" && pwd)
# The ONE quiet-host helper ($F/bin/ when installed, scripts/coordination/ in the repo). Under a live quiet-host grant
# the hourly du columns are written as `defer` (DEFER-QUIET-HOST in disk-trend.log); the df column always runs.
QH=${DISK_TREND_QUIET_HOST:-$([ -f "$H/bin/quiet_host.py" ] && echo "$H/bin/quiet_host.py" || echo "$H/../quiet_host.py")}
L=${DISK_TREND_LOG:-$(dirname "$O")/disk-trend.log}
scan() {  # scan TAG PATH: du -s -BG under nice/ionice via quiet_host.py exec; prints GiB, `defer`, or empty
  local out rc=0
  out=$(python3 "$QH" exec "disk-trend $1" -- du -s -BG "$2" 2>/dev/null) || rc=$?
  if [ "$rc" = 75 ]; then echo "$(date -u +%FT%TZ) DEFER-QUIET-HOST disk-trend $1" >> "$L"; echo defer; return 0; fi
  printf '%s\n' "$out" | cut -f1
}
[ "${1:-}" = --once-scan ] && { scan "$2" "$3"; exit 0; }   # test hook: one scan, no loop
i=0
while :; do
  f=$(df -B1G --output=avail /mnt/raid0/llm | tail -1 | tr -d ' ')
  if [ $((i % 6)) = 0 ]; then w=$(scan worktrees /mnt/raid0/llm/worktrees); t=$(scan trash /mnt/raid0/llm/.trash); else w=-; t=-; fi
  printf '%s\t%s\t%s\t%s\n' "$(date -u +%FT%TZ)" "$f" "$w" "$t" >> $O
  i=$((i+1)); sleep 600
done
