#!/bin/bash
# ws58 2026-11-01 (operator: "Are we still leaking?"). Zero-token. Every 10 min append free GiB of /mnt/raid0/llm plus
# worktrees/trash sizes (hourly) to disk-trend.tsv, so a leak shows as a slope. Read-only except its own file.
set -euo pipefail
O=/mnt/raid0/llm/tmp/compute-flags/disk-trend.tsv
i=0
while :; do
  f=$(df -B1G --output=avail /mnt/raid0/llm | tail -1 | tr -d ' ')
  if [ $((i % 6)) = 0 ]; then w=$(du -s -BG /mnt/raid0/llm/worktrees 2>/dev/null | cut -f1); t=$(du -s -BG /mnt/raid0/llm/.trash 2>/dev/null | cut -f1); else w=-; t=-; fi
  printf '%s\t%s\t%s\t%s\n' "$(date -u +%FT%TZ)" "$f" "$w" "$t" >> $O
  i=$((i+1)); sleep 600
done
