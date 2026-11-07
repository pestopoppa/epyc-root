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
#   every 30 min  LINK: filing.py autolink --apply (zero-token: an ended-unfiled row is FILED when exactly ONE origin/main commit ticks or
#                 annotates a handoff box naming its id; ambiguous matches are listed, never filed; operator 2026-11-07).
#   every 30 min  BUDGET: row_disk_budget.py --alert (per-row disk budget: used vs budget_gib for every live grant; alert only).
#   every 24 h    the LIFECYCLE pass (operator 2026-11-07, "we can't have so much disk leak"; all zero-token, all trash-first):
#                   WTREAP  worktree_reaper.py --apply   agent worktrees: clean+landed idle >= 3 d removed; dirty/unlanded idle
#                                                        >= 7 d salvaged (patch bundle + salvage branch) then trashed, then
#                                                        deregistered. Never --force, never prune. mains/, pool/, locked, KEEP: skipped.
#                   KGC     kernel_store_gc.py --apply   kernels/builds/* not production/archive/candidate targets, not named by
#                                                        a manifest/handoff/ready row/champion file, not busy, idle >= 7 d -> trash.
#                   LEASE   scratch_lease.py backfill    every KEEP marker under tmp/ without a lease gets a 14-day lease, so a
#                                                        marker can no longer hold bytes forever (scratch-lease Phase 1).
#                   OWNER   owner_check.py --fix-modes      root-owned or unwritable dirs under tmp/, .trash*, worktrees/ (a
#                                                        build that left a 555 root tree defeated trash-sweep, 11-07): modes we
#                                                        own are repaired; foreign-uid trees are flagged with the sudo chown line.
#                   CODEX   codex_retention_reaper.py report+apply  ~/.codex rollouts older than JANITOR_CODEX_KEEP_DAYS (7)
#                                                        whose sha256-identical vault copy exists are deleted (apply re-verifies each
#                                                        file); the newest 7 days stay. packages/ and sqlite untouched (--no-packages).
#                                                        Operator decision 2026-11-07 REVERSED the 2026-10-04 never-touch rule for
#                                                        ~/.codex only; every other harness tree stays NEVER_TOUCH.
#                   COMGR   comgr_cache_reaper.py --apply   /tmp/.<hex>-00000000.so ROCm comgr JIT cache files older than 3 d that
#                                                        no process has mapped/open (regenerable; /tmp is outside the trash FS, so
#                                                        direct unlink; operator 2026-11-07).
#   every pass    one FREE line (GiB available on /mnt/raid0) so disk-janitor.log carries the free-disk trend.
#
# This script deletes nothing itself: deletes happen only inside the keeper's guarded reaper (guarded_rm.sh -> its own trash),
# inside trash-sweep.sh, and inside the lifecycle tools above (guarded_rm.sh / `git worktree remove`, never rm). It never
# starts, stops or kills another process. JANITOR_LIFECYCLE=0 disables the daily pass; each tool has its own log in $F.
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
LIFECYCLE_EVERY_S=${JANITOR_LIFECYCLE_EVERY_S:-86400}
LIFECYCLE=${JANITOR_LIFECYCLE:-1}
TOOLS=${JANITOR_TOOLS:-/workspace/scripts}          # the repo's scripts/ (same tree trash-sweep.sh comes from)
LIFECYCLE_STAMP=${JANITOR_LIFECYCLE_STAMP:-$F/ws58-keeper-state/lifecycle-last}
WT_MAX=${JANITOR_WT_MAX:-20}; KGC_MAX=${JANITOR_KGC_MAX:-10}; KGC_MIN_AGE_D=${JANITOR_KGC_MIN_AGE_D:-7}
LEASE_TTL_D=${JANITOR_LEASE_TTL_D:-14}
CODEX_KEEP_DAYS=${JANITOR_CODEX_KEEP_DAYS:-7}; COMGR_MIN_AGE_D=${JANITOR_COMGR_MIN_AGE_D:-3}
TICK_S=${JANITOR_TICK_S:-60}
MODE=loop
case "${1:-}" in
  "") ;;
  --once) MODE=once;;
  --dry-run) MODE=dry;;
  -h|--help) sed -n 2,38p "$0"; exit 0;;
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

run_tool() {  # run_tool TAG <cmd...>: run one lifecycle tool, log its last line and rc; a missing tool is a SKIP, never an error
  local tag=$1; shift; local out rc=0
  [ -f "$1" ] || [ -f "$2" ] || { log "$tag-SKIP tool missing: $*"; return 0; }
  out=$("$@" 2>&1) || rc=$?
  log "$tag rc=$rc ${out:+last: $(printf '%s\n' "$out" | grep -v '^$' | tail -1 | cut -c1-200)}"
  if [ "$MODE" = dry ]; then printf '%s\n' "$out" | tail -n 25 | while IFS= read -r l; do log "$tag $l"; done; fi
}

budget() {  # per-row disk budget check over live grants: alert only (row_disk_budget.py), never stops a row
  local flags=(--flags "$F" --log "$F/disk-budget.log"); [ "$MODE" = dry ] || flags+=(--alert)
  run_tool BUDGET python3 "$TOOLS/coordination/churn/row_disk_budget.py" "${flags[@]}"
}

autolink() {  # zero-token filing sweep: ONE origin/main box commit per ended-unfiled row -> FILED; ambiguous matches are only listed
  local mode=(--apply); [ "$MODE" = dry ] && mode=()
  run_tool LINK python3 "$TOOLS/coordination/churn/filing.py" autolink --flags "$F" --repo "${JANITOR_LINK_REPO:-/workspace}" "${mode[@]}"
}

codex_rotate() {  # report (writes a manifest + token) then apply on that exact manifest; dry mode reports only
  local tool=$TOOLS/system/codex_retention_reaper.py rep=$F/codex-retention-report.json rc=0 tok out
  [ -f "$tool" ] || { log "CODEX-SKIP tool missing: $tool"; return 0; }
  python3 "$tool" report --json --older-than-days "$CODEX_KEEP_DAYS" > "$rep.part" 2>>"$F/codex-retention-report.err" && mv -f "$rep.part" "$rep" || rc=$?
  tok=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("confirm_token") or "")' "$rep" 2>/dev/null || true)
  log "CODEX report rc=$rc keep=${CODEX_KEEP_DAYS}d token=${tok:-none} -> $rep"
  [ "$MODE" = dry ] && return 0
  if [ "$rc" = 0 ] && [ -n "$tok" ]; then
    rc=0; out=$(python3 "$tool" apply --older-than-days "$CODEX_KEEP_DAYS" --confirm-token "$tok" --no-packages 2>&1) || rc=$?
    log "CODEX apply rc=$rc $(printf '%s\n' "$out" | tr -d '\n ' | grep -o '"unlinked":[0-9]*,"unlinked_bytes":[0-9]*,"rmtree":[0-9]*,"rmtree_bytes":[0-9]*,"skipped":[0-9]*,"errors":[0-9]*' || printf '%s' "$out" | tail -1 | cut -c1-160)"
  else log "CODEX apply skipped (nothing eligible or report failed)"; fi
}

lifecycle() {  # lifecycle [force]: the daily pass (worktree TTL reaper, kernel store GC, KEEP leases, codex report)
  local age apply=(--apply) dryf=()
  [ "$LIFECYCLE" = 1 ] || { log "LIFECYCLE-SKIP disabled (JANITOR_LIFECYCLE=0)"; return 0; }
  age=$(( $(date +%s) - $(stat -c %Y "$LIFECYCLE_STAMP" 2>/dev/null || echo 0) ))
  if [ "${1:-}" != force ] && [ "$age" -lt "$LIFECYCLE_EVERY_S" ]; then return 0; fi
  if [ "$MODE" = dry ]; then apply=(); dryf=(--dry-run); else mkdir -p "$(dirname "$LIFECYCLE_STAMP")"; touch "$LIFECYCLE_STAMP"; fi
  log "LIFECYCLE start (apply=${apply[*]:-no})"
  run_tool WTREAP python3 "$TOOLS/system/worktree_reaper.py" "${apply[@]}" --max "$WT_MAX" --log "$F/worktree-reap.log"
  run_tool KGC    python3 "$TOOLS/system/kernel_store_gc.py" "${apply[@]}" --max "$KGC_MAX" --min-age-days "$KGC_MIN_AGE_D" --log "$F/kernel-gc.log"
  if [ "$MODE" = dry ]; then run_tool OWNER python3 "$TOOLS/system/owner_check.py" --log "$F/owner-check.log"
  else run_tool OWNER python3 "$TOOLS/system/owner_check.py" --fix-modes --log "$F/owner-check.log"; fi
  if [ "$MODE" = dry ]; then run_tool LEASE python3 "$TOOLS/system/scratch_lease.py" backfill --dry-run --ttl-days "$LEASE_TTL_D"
  else run_tool LEASE python3 "$TOOLS/system/scratch_lease.py" backfill --apply --ttl-days "$LEASE_TTL_D"; fi
  codex_rotate
  if [ "$MODE" = dry ]; then run_tool COMGR python3 "$TOOLS/system/comgr_cache_reaper.py" --min-age-days "$COMGR_MIN_AGE_D"
  else run_tool COMGR python3 "$TOOLS/system/comgr_cache_reaper.py" --apply --min-age-days "$COMGR_MIN_AGE_D"; fi
  log "LIFECYCLE end"
}

if [ "$MODE" != loop ]; then free_line; reap force; sweep; budget; autolink; lifecycle force; free_line; exit 0; fi

# loop: one instance (pidfile pid alive with our argv, and not us -> exit)
old=$(tr -d ' \n' < "$PIDF" 2>/dev/null || true)
if [ -n "$old" ] && [ "$old" != "$$" ] && ps -o args= -p "$old" 2>/dev/null | grep -F disk_janitor >/dev/null; then
  echo "disk_janitor already running pid $old"; exit 0
fi
echo $$ > "$PIDF"
log "disk_janitor start pid=$$ (reap+budget every ${REAP_EVERY_S}s via $KEEPER --reap-now; sweep every ${SWEEP_EVERY_S}s: $TRASHES; lifecycle every ${LIFECYCLE_EVERY_S}s from $TOOLS)"
last_reap=0; last_sweep=0
while :; do
  now=$(date +%s)
  if [ $(( now - last_reap )) -ge "$REAP_EVERY_S" ]; then free_line; reap || log "REAP error rc=$?"; budget || log "BUDGET error rc=$?"; autolink || log "LINK error rc=$?"; last_reap=$now; free_line; fi
  if [ $(( now - last_sweep )) -ge "$SWEEP_EVERY_S" ]; then sweep || log "SWEEP error rc=$?"; last_sweep=$now; fi
  lifecycle || log "LIFECYCLE error rc=$?"
  sleep "$TICK_S"
done
