#!/bin/bash
# disk_janitor.sh — standalone, deterministic disk janitor (ws58, operator "four disk fixes", 2026-11-02).
#
# Origin: 2026-11-02 /mnt/raid0/llm/tmp reached ~534 GiB, free disk 147 GiB. Reaping lived only inside the keeper loop, so a
# stopped keeper meant no reaping, and /mnt/raid0/llm/.trash was freed only when someone remembered to sweep it.
#
#   every 30 min  the keeper's reap-only pass: `bash <keeper> --reap-now` (step 6 of ws58-calendar-keeper-v13.sh: filed
#                 manifests + the idle rule at REAP_IDLE_DAYS=1, every keeper guard intact). This is the ONLY scheduled reaper:
#                 the keeper loop no longer reaps (operator 2026-11-03). Skipped while the reap stamp
#                 (ws58-keeper-state/reap-last, touched by every --reap-now pass, e.g. a manual one) is younger than 30 min.
#   every 60 min  `trash-sweep.sh --older-than 1` for /mnt/raid0/llm/.trash and, if it exists, /mnt/raid0/llm/.trash-reap.
#   every pass    one FREE line (GiB available on /mnt/raid0) so disk-janitor.log carries the free-disk trend.
#
# This script deletes nothing itself: deletes happen only inside the keeper's guarded reaper (guarded_rm.sh -> its own trash)
# and inside trash-sweep.sh. It never starts, stops or kills another process.
#
# Usage: disk_janitor.sh            the loop (pidfile disk-janitor.pid; a second copy exits 0 at once)
#        disk_janitor.sh --once     one live pass (reap + sweep), then exit
#        disk_janitor.sh --dry-run  one read-only pass (keeper --reap-dry-run, trash-sweep --dry-run), then exit
# Started/stopped/inspected by: scripts/coordination/churn/churn_up.sh --janitor=start|stop|status|dry-run
# (churn_up.sh --stop, the inference stop, deliberately leaves the janitor running).
# Runbook: docs/guides/agent-workflows/backlog-churn-runbook.md (component inventory + verification).
set -euo pipefail

F=${JANITOR_FLAGS:-/mnt/raid0/llm/tmp/compute-flags}
KEEPER=${JANITOR_KEEPER:-$F/ws58-calendar-keeper-v13.sh}
SWEEP=${JANITOR_SWEEP:-/workspace/scripts/safety/trash-sweep.sh}
LOG=${JANITOR_LOG:-$F/disk-janitor.log}
PIDF=${JANITOR_PIDFILE:-$F/disk-janitor.pid}
STAMP=${JANITOR_REAP_STAMP:-$F/ws58-keeper-state/reap-last}
TRASHES=${JANITOR_TRASHES:-/mnt/raid0/llm/.trash /mnt/raid0/llm/.trash-reap}
DISK=${JANITOR_DISK:-/mnt/raid0}
REAP_EVERY_S=${JANITOR_REAP_EVERY_S:-1800}
SWEEP_EVERY_S=${JANITOR_SWEEP_EVERY_S:-3600}
TICK_S=${JANITOR_TICK_S:-60}
MODE=loop
case "${1:-}" in
  "") ;;
  --once) MODE=once;;
  --dry-run) MODE=dry;;
  -h|--help) sed -n 2,23p "$0"; exit 0;;
  *) echo "usage: disk_janitor.sh [--once|--dry-run]" >&2; exit 2;;
esac

log() {
  local line; line="$(date -u +%FT%TZ) $*"
  if [ "$MODE" = dry ]; then echo "[dry-run] $line"; else echo "$line" >> "$LOG"; fi
}
free_line() { log "FREE $(df -B1G --output=avail "$DISK" 2>/dev/null | tail -1 | tr -d ' ')GiB on $DISK"; }

reap() {  # reap [force]: the keeper's reap-only pass, unless the keeper reaped within REAP_EVERY_S
  local age rc=0
  if [ "$MODE" = dry ]; then
    { bash "$KEEPER" --reap-dry-run 2>&1 || true; } | tail -n 40 | while IFS= read -r l; do log "REAP $l"; done; return 0
  fi
  [ -f "$KEEPER" ] || { log "REAP-SKIP keeper $KEEPER missing"; return 0; }
  age=$(( $(date +%s) - $(stat -c %Y "$STAMP" 2>/dev/null || echo 0) ))
  if [ "${1:-}" != force ] && [ "$age" -lt "$REAP_EVERY_S" ]; then log "REAP-SKIP keeper reaped ${age}s ago"; return 0; fi
  log "REAP start: bash $KEEPER --reap-now (decisions go to ws58-calendar-keeper.log)"
  bash "$KEEPER" --reap-now >> "$LOG" 2>&1 || rc=$?
  log "REAP end rc=$rc"
}

sweep() {  # trash-sweep --older-than 1 on every trash root that exists
  local t out rc n
  for t in $TRASHES; do
    [ -d "$t" ] || { log "SWEEP-SKIP $t absent"; continue; }
    rc=0
    if [ "$MODE" = dry ]; then out=$(TRASH_ROOT=$t bash "$SWEEP" --older-than 1 --dry-run 2>&1) || rc=$?
    else out=$(TRASH_ROOT=$t bash "$SWEEP" --older-than 1 2>&1) || rc=$?; fi
    n=$(printf '%s\n' "$out" | grep -c -E '^(removed|\[dry-run\] would remove) ' || true)
    log "SWEEP $t rc=$rc entries=$n${out:+ last: $(printf '%s\n' "$out" | tail -1 | cut -c1-160)}"
  done
}

if [ "$MODE" != loop ]; then free_line; reap force; sweep; free_line; exit 0; fi

# loop: one instance (pidfile pid alive with our argv, and not us -> exit)
old=$(tr -d ' \n' < "$PIDF" 2>/dev/null || true)
if [ -n "$old" ] && [ "$old" != "$$" ] && ps -o args= -p "$old" 2>/dev/null | grep -F disk_janitor >/dev/null; then
  echo "disk_janitor already running pid $old"; exit 0
fi
echo $$ > "$PIDF"
log "disk_janitor start pid=$$ (reap every ${REAP_EVERY_S}s via $KEEPER --reap-now; sweep every ${SWEEP_EVERY_S}s: $TRASHES)"
last_reap=0; last_sweep=0
while :; do
  now=$(date +%s)
  if [ $(( now - last_reap )) -ge "$REAP_EVERY_S" ]; then free_line; reap || log "REAP error rc=$?"; last_reap=$now; free_line; fi
  if [ $(( now - last_sweep )) -ge "$SWEEP_EVERY_S" ]; then sweep || log "SWEEP error rc=$?"; last_sweep=$now; fi
  sleep "$TICK_S"
done
