#!/bin/bash
set -euo pipefail

# Check handoff freshness — flags files not modified in 30+ days
# Usage: scripts/validate/check_handoff_freshness.sh [--warn-days N] [--stale-days N]

HANDOFF_DIR="/mnt/raid0/llm/epyc-root/handoffs/active"
WARN_DAYS="${1:-14}"
STALE_DAYS="${2:-30}"
NOW=$(date +%s)

printf "%-50s %-12s %-10s\n" "HANDOFF" "LAST UPDATED" "STATUS"
printf "%-50s %-12s %-10s\n" "-------" "------------" "------"

stale_count=0
warn_count=0

for f in "$HANDOFF_DIR"/*.md; do
    name=$(basename "$f")
    mod_epoch=$(stat -c %Y "$f")
    mod_date=$(date -d "@$mod_epoch" +%Y-%m-%d)
    age_days=$(( (NOW - mod_epoch) / 86400 ))

    if [ "$age_days" -gt "$STALE_DAYS" ]; then
        status="STALE (${age_days}d)"
        stale_count=$((stale_count + 1))
    elif [ "$age_days" -gt "$WARN_DAYS" ]; then
        status="aging (${age_days}d)"
        warn_count=$((warn_count + 1))
    else
        status="ok (${age_days}d)"
    fi

    printf "%-50s %-12s %-10s\n" "$name" "$mod_date" "$status"
done

echo ""
echo "Summary: $stale_count stale (>${STALE_DAYS}d), $warn_count aging (>${WARN_DAYS}d)"

if [ "$stale_count" -gt 0 ]; then
    exit 1
fi
