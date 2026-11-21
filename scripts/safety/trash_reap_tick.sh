#!/bin/bash
# trash_reap_tick.sh - cron-able deterministic trash reaper (operator 2026-11-21 disk guards). No LLM, no args.
# Runs `trash-sweep.sh --older-than 24h` on the trash root(s): guarded_rm.sh only MOVES, so without a scheduled
# sweep trashed bytes are never freed. Age = the trash stamp in the entry name, never mtime (see trash-sweep.sh).
# Roots: $TRASH_ROOT (default /mnt/raid0/llm/.trash) and, when TRASH_ROOT is unset, /mnt/raid0/llm/.trash-reap.
# flock: one tick at a time. Logs one line per root to $TRASH_TICK_LOG (default /workspace/logs/trash_reap_tick.log).
set -euo pipefail
HERE="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
LOG="${TRASH_TICK_LOG:-/workspace/logs/trash_reap_tick.log}"
AGE="${TRASH_TICK_AGE:-24h}"
LOCK="${TRASH_TICK_LOCK:-/tmp/trash_reap_tick.lock}"
exec 9>"$LOCK"
flock -n 9 || { echo "trash_reap_tick: another tick is running"; exit 0; }
roots=()
if [ -n "${TRASH_ROOT:-}" ]; then roots=("$TRASH_ROOT"); else roots=(/mnt/raid0/llm/.trash /mnt/raid0/llm/.trash-reap); fi
mkdir -p "$(dirname "$LOG")" 2>/dev/null || true
for r in "${roots[@]}"; do
    [ -d "$r" ] || continue
    before=$(du -sk "$r" 2>/dev/null | cut -f1 || echo 0)
    out=$(TRASH_ROOT="$r" bash "$HERE/trash-sweep.sh" --older-than "$AGE" 2>&1) || true
    after=$(du -sk "$r" 2>/dev/null | cut -f1 || echo 0)
    n=$(printf '%s\n' "$out" | grep -c '^removed ' || true)
    line="$(date -u +%Y-%m-%dT%H:%M:%SZ) TRASH-REAP root=$r removed=$n freed_kib=$(( before - after )) age=$AGE"
    echo "$line"; echo "$line" >> "$LOG" 2>/dev/null || true
done
