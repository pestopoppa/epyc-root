#!/bin/bash
# run_shadow.sh - rowflow2 SHADOW beside the live keeper (operator 2026-11-05, "Freeze current + build rowflow2").
# A SEPARATE process: the live keeper (ws58-calendar-keeper-v12.sh) is not touched and never calls this.
# Every INTERVAL s: `rowflow2.py shadow --once` (read-only on compute-flags; audit-hook write guard) appends
# SHADOW-GRANT / SHADOW-IDLE-WHY / SHADOW-HOLD lines to $OUT/shadow.log. At each UTC day rollover it writes the
# daily live-vs-shadow diff for the finished day to $OUT/diff-<date>.md and .json.
#
#   run_shadow.sh [--interval 120] [--out /mnt/raid0/llm/tmp/rowflow2-shadow] [--once]
# Start detached:  setsid nohup run_shadow.sh >/dev/null 2>&1 &   (pid in $OUT/shadow.pid)
set -euo pipefail
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
FLAGS=${ROWFLOW_FLAGS:-/mnt/raid0/llm/tmp/compute-flags}
OUT=/mnt/raid0/llm/tmp/rowflow2-shadow
INTERVAL=120; ONCE=0
while [ $# -gt 0 ]; do
  case "$1" in
    --interval) INTERVAL=$2; shift 2 ;;
    --out) OUT=$2; shift 2 ;;
    --once) ONCE=1; shift ;;
    *) echo "unknown arg $1" >&2; exit 64 ;;
  esac
done
case "$OUT" in "$FLAGS"|"$FLAGS"/*) echo "REFUSED: --out under the flags dir" >&2; exit 64 ;; esac
mkdir -p "$OUT"
echo $$ > "$OUT/shadow.pid"
PY=python3
LAST_DAY=$(date -u +%F)
while :; do
  "$PY" -B "$HERE/rowflow2.py" shadow --once --flags "$FLAGS" --log "$OUT/shadow.log" >> "$OUT/shadow.out" 2>&1 \
    || echo "$(date -u +%FT%TZ) SHADOW-ERROR rc=$?" >> "$OUT/shadow.log"
  [ "$ONCE" = 1 ] && exit 0
  DAY=$(date -u +%F)
  if [ "$DAY" != "$LAST_DAY" ]; then
    "$PY" -B "$HERE/rowflow2.py" diff --keeper-log "$FLAGS/ws58-calendar-keeper.log" --shadow-log "$OUT/shadow.log" \
      --date "$LAST_DAY" > "$OUT/diff-$LAST_DAY.md" 2>>"$OUT/shadow.out" || true
    "$PY" -B "$HERE/rowflow2.py" diff --keeper-log "$FLAGS/ws58-calendar-keeper.log" --shadow-log "$OUT/shadow.log" \
      --date "$LAST_DAY" --json > "$OUT/diff-$LAST_DAY.json" 2>>"$OUT/shadow.out" || true
    LAST_DAY=$DAY
  fi
  sleep "$INTERVAL"
done
