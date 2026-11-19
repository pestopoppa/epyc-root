#!/bin/bash
# backup_loop_state.sh -- nightly off-RAID0 snapshot of AutoKernel / AutoPilot / belief-kernel loop state.
# Box BK-1 of handoffs/active/engineering-hygiene-backlog.md (loop-state off-RAID0 backup).
# Intended home on the host: next to backup-claude-sessions.sh in the filesystem agent's script dir
# (copy this file there). Scheduling text: scripts/backup/loop-state-backup.crontab (BK-2).
#
# Output:  $BACKUP_ROOT/YYYYMMDD/{<paths relative to $SRC_ROOT>, SHA256SUMS, SKIPPED.txt}
# Status:  "<UTC ts> STATUS OK|FAILED [detail]" in $BACKUP_ROOT/LAST_STATUS and, when set, $LOCAL_STATUS_FILE
#          (a second copy on a path the container can see, read by host_hygiene_tick.loop_state_backups).
# Exit:    0 = snapshot complete and manifest written; non-zero on ANY failure (a failed snapshot is removed).
#
# Config (env; defaults are the production values):
#   SRC_ROOT            /mnt/raid0/llm
#   BACKUP_ROOT         /mnt/micron/loop-state-backups      (must be on a different device than SRC_ROOT)
#   BACKUP_MOUNT        /mnt/micron                          (must be a real mountpoint; checked with findmnt)
#   LOCAL_STATUS_FILE   /mnt/raid0/llm/claude-backups/loop-state.LAST_STATUS
#   LOCK_FILE           /mnt/raid0/llm/claude-backups/loop-state-backup.lock
#   LARGE_DB_POLICY     weekly (default, operator BK-3 decision 2026-11-09) | exclude | include
#                       exclude: SQLite DBs >= LARGE_DB_MIN_BYTES are skipped and listed in SKIPPED.txt
#                       weekly : included only on Sundays; include: always
#   LARGE_DB_MIN_BYTES  1000000000  (1 GB; the 4.3 GB and 1.1 GB historical DS41 DBs, not the ~317 MB live store)
#   KEEP_DAILY=7  KEEP_WEEKLY=4     (weekly = Sunday-dated snapshots)
#   ALLOW_SAME_DEVICE   0           (1 only for fixtures: disables the off-md127 refusal)
#   ALLOW_ROOT          0           (1 only if the operator deliberately runs as root)
#   SNAPSHOT_DATE       today UTC YYYYMMDD (test hook)
#   LEDGER_LOCK_WAIT_S  60
# Requires: sqlite3, flock, findmnt, sha256sum, find, cp. Reads sources; writes only under
# $BACKUP_ROOT and the status files.
set -euo pipefail

SRC_ROOT="${SRC_ROOT:-/mnt/raid0/llm}"
BACKUP_ROOT="${BACKUP_ROOT:-/mnt/micron/loop-state-backups}"
BACKUP_MOUNT="${BACKUP_MOUNT:-/mnt/micron}"
[[ "$BACKUP_MOUNT" == "/" ]] || BACKUP_MOUNT="${BACKUP_MOUNT%/}"
LOCAL_STATUS_FILE="${LOCAL_STATUS_FILE-/mnt/raid0/llm/claude-backups/loop-state.LAST_STATUS}"
LOCK_FILE="${LOCK_FILE:-/mnt/raid0/llm/claude-backups/loop-state-backup.lock}"
ALLOW_ROOT="${ALLOW_ROOT:-0}"
LARGE_DB_POLICY="${LARGE_DB_POLICY:-weekly}"
LARGE_DB_MIN_BYTES="${LARGE_DB_MIN_BYTES:-1000000000}"
KEEP_DAILY="${KEEP_DAILY:-7}"
KEEP_WEEKLY="${KEEP_WEEKLY:-4}"
ALLOW_SAME_DEVICE="${ALLOW_SAME_DEVICE:-0}"
LEDGER_LOCK_WAIT_S="${LEDGER_LOCK_WAIT_S:-60}"
SNAP="${SNAPSHOT_DATE:-$(date -u +%Y%m%d)}"

# Scope: globs relative to SRC_ROOT (docs: engineering-hygiene-backlog.md, "Scope: back up exactly these").
SCOPE=(
  "state/vidya"
  "autokernel/campaigns/*/store*/experiments.db"
  "autokernel/campaigns/*/store*/inbox"
  "autokernel/campaigns/*/store*/accumulator-bundle.json"
  "autokernel/campaigns/*/store*/journal*"
  "autokernel/campaigns/*/store*/resume-claims.sqlite3"
  "autokernel/campaigns/*/inputs*"
  "autokernel/loop-memory/experiments.db"
  "autokernel/loop-memory/inbox"
  "epyc-orchestrator/orchestration/autopilot_state.json"
  "epyc-orchestrator/orchestration/autopilot_journal*.jsonl"
  "epyc-orchestrator/orchestration/autopilot_checkpoints"
  "epyc-orchestrator/orchestration/repl_memory/strategies"
  "epyc-orchestrator/orchestration/operator_hypotheses.yaml"
  "epyc-orchestrator/orchestration/operator_hypothesis_resolutions.jsonl"
)

ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
log() { echo "[$(ts)] backup_loop_state: $*"; }

write_status() {  # write_status OK|FAILED [detail]
  local line="$(ts) STATUS $1${2:+ $2}"
  # never mkdir BACKUP_ROOT here: with the off-array mount absent that would create dirs on md127
  if [[ -d "$BACKUP_ROOT" ]]; then echo "$line" > "$BACKUP_ROOT/LAST_STATUS" || true; fi
  if [[ -n "$LOCAL_STATUS_FILE" ]]; then
    mkdir -p "$(dirname "$LOCAL_STATUS_FILE")" 2>/dev/null && echo "$line" > "$LOCAL_STATUS_FILE" || true
  fi
}

STAGE=""
DONE=0
on_exit() {
  local rc=$?
  if [[ $DONE -ne 1 ]]; then
    [[ -n "$STAGE" && -d "$STAGE" ]] && rm -rf -- "$STAGE"
    write_status FAILED "rc=$rc snapshot=$SNAP"
    log "FAILED rc=$rc"
  fi
}
trap on_exit EXIT

# Refuse root by default: the cron job runs as daniele, and root-owned snapshots would
# poison later retention/status writes by the daniele job.
if [[ "$(id -u)" -eq 0 && "$ALLOW_ROOT" != 1 ]]; then
  log "REFUSING to run as root; run as daniele or set ALLOW_ROOT=1"; exit 2
fi

# Real mount guard: the parent directory exists even when /mnt/micron is unmounted, so the
# old parent check alone would create the snapshot on the root SSD.
mount_target="$(findmnt -rn -T "$BACKUP_MOUNT" -o TARGET 2>/dev/null || true)"
[[ "$mount_target" == "$BACKUP_MOUNT" ]] || {
  log "REFUSING: $BACKUP_MOUNT is not a mountpoint (found ${mount_target:-none}; BACKUP_ROOT=$BACKUP_ROOT)"
  exit 2
}
if [[ "$BACKUP_MOUNT" != "/" ]]; then
  [[ "$BACKUP_ROOT" == "$BACKUP_MOUNT" || "$BACKUP_ROOT" == "$BACKUP_MOUNT"/* ]] || {
    log "REFUSING: BACKUP_ROOT $BACKUP_ROOT is not under BACKUP_MOUNT $BACKUP_MOUNT"; exit 2
  }
fi

# One instance at a time. A benign skip must not write a FAILED status.
mkdir -p "$(dirname "$LOCK_FILE")"
exec 8>>"$LOCK_FILE"
flock -n 8 || { log "already running"; DONE=1; exit 0; }

[[ "$SNAP" =~ ^[0-9]{8}$ ]] || { log "bad SNAPSHOT_DATE '$SNAP'"; exit 2; }
case "$LARGE_DB_POLICY" in exclude|weekly|include) ;; *) log "bad LARGE_DB_POLICY '$LARGE_DB_POLICY'"; exit 2;; esac
command -v sqlite3 >/dev/null || { log "sqlite3 not found"; exit 2; }
[[ -d "$SRC_ROOT" ]] || { log "SRC_ROOT missing: $SRC_ROOT"; exit 2; }
# BACKUP_ROOT itself may not exist yet on first run (its parent must: mount absent => refuse, never create on md127).
[[ -d "$(dirname "$BACKUP_ROOT")" ]] || { log "parent of BACKUP_ROOT missing (mount absent?): $BACKUP_ROOT"; exit 2; }
mkdir -p "$BACKUP_ROOT"
if [[ "$ALLOW_SAME_DEVICE" != 1 && "$(stat -c %d "$SRC_ROOT")" == "$(stat -c %d "$BACKUP_ROOT")" ]]; then
  log "REFUSING: BACKUP_ROOT is on the same device as SRC_ROOT (backup must be off md127)"; exit 2
fi

FINAL="$BACKUP_ROOT/$SNAP"
if [[ -f "$FINAL/SHA256SUMS" ]]; then
  log "snapshot $SNAP already exists with a manifest; nothing to do"
  DONE=1; write_status OK "snapshot=$SNAP (already present)"; exit 0
fi
STAGE="$BACKUP_ROOT/$SNAP.partial"
rm -rf -- "$STAGE"; mkdir -p "$STAGE"

IS_SUNDAY=0; [[ "$(date -u -d "${SNAP:0:4}-${SNAP:4:2}-${SNAP:6:2}" +%u)" == 7 ]] && IS_SUNDAY=1
FAILS=0; NFILES=0
: > "$STAGE/SKIPPED.txt"

is_sqlite_name() { case "$1" in *.db|*.sqlite|*.sqlite3) return 0;; *) return 1;; esac; }

copy_plain() {  # copy_plain <rel>   (consistent ledger copy: compare against source after copy, retry)
  local rel="$1" i
  mkdir -p "$STAGE/$(dirname "$rel")"
  for i in 1 2 3; do
    cp -p -- "$SRC_ROOT/$rel" "$STAGE/$rel" || return 1
    [[ "$rel" == *.jsonl ]] || return 0
    [[ "$(sha256sum < "$SRC_ROOT/$rel")" == "$(sha256sum < "$STAGE/$rel")" ]] && return 0
    sleep 1
  done
  log "source kept changing during copy: $rel"; return 1
}

copy_file() {  # copy_file <rel>
  local rel="$1" base size
  base="$(basename "$rel")"
  case "$base" in *-wal|*-shm|*-journal) return 0;; esac   # captured by .backup of the main DB
  if is_sqlite_name "$base"; then
    size=$(stat -c %s "$SRC_ROOT/$rel")
    if (( size >= LARGE_DB_MIN_BYTES )) && [[ "$LARGE_DB_POLICY" == exclude || ( "$LARGE_DB_POLICY" == weekly && $IS_SUNDAY -ne 1 ) ]]; then
      echo "$rel $size policy=$LARGE_DB_POLICY" >> "$STAGE/SKIPPED.txt"; return 0
    fi
    mkdir -p "$STAGE/$(dirname "$rel")"
    sqlite3 "$SRC_ROOT/$rel" ".timeout 60000" ".backup '$STAGE/$rel'" || return 1
  else
    copy_plain "$rel" || return 1
  fi
  NFILES=$((NFILES+1))
}

walk() {  # walk <rel> : files of a file-or-directory scope entry
  local rel="$1" f
  if [[ -d "$SRC_ROOT/$rel" ]]; then
    while IFS= read -r -d '' f; do
      copy_file "${f#"$SRC_ROOT"/}" || { log "FAILED copy: ${f#"$SRC_ROOT"/}"; FAILS=$((FAILS+1)); }
    done < <(find "$SRC_ROOT/$rel" -type f -print0)
  elif [[ -f "$SRC_ROOT/$rel" ]]; then
    copy_file "$rel" || { log "FAILED copy: $rel"; FAILS=$((FAILS+1)); }
  fi
}

run_scope() {
  local pat p matched
  shopt -s nullglob
  for pat in "${SCOPE[@]}"; do
    matched=0
    for p in $SRC_ROOT/$pat; do matched=1; walk "${p#"$SRC_ROOT"/}"; done
    [[ $matched -eq 1 ]] || echo "(no match) $pat" >> "$STAGE/SKIPPED.txt"
  done
  shopt -u nullglob
}

log "snapshot $SNAP: $SRC_ROOT -> $FINAL (large-db policy: $LARGE_DB_POLICY)"
LEDGER_LOCK="$SRC_ROOT/state/vidya/ledger.jsonl.lock"
if [[ -e "$LEDGER_LOCK" ]]; then
  # Hold the ingest lock (verified: scripts/vidya/ledger.py flock(LOCK_EX) on <ledger>.lock) for the whole belief-ledger tree; the sha re-check in copy_plain also guards.
  exec 9>>"$LEDGER_LOCK"
  flock -w "$LEDGER_LOCK_WAIT_S" 9 || { log "could not take $LEDGER_LOCK within ${LEDGER_LOCK_WAIT_S}s"; exit 3; }
  walk "state/vidya"
  flock -u 9
  SCOPE=("${SCOPE[@]:1}")
fi
run_scope
(( FAILS == 0 )) || { log "$FAILS copy failure(s)"; exit 4; }
(( NFILES > 0 )) || { log "nothing was copied: empty scope under $SRC_ROOT"; exit 5; }

# Manifest last, over everything including SKIPPED.txt; relative paths so `sha256sum -c` works from the snapshot dir.
( cd "$STAGE" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS )
( cd "$STAGE" && sha256sum -c --quiet SHA256SUMS ) || { log "manifest self-check failed"; exit 6; }
mv -- "$STAGE" "$FINAL"
STAGE=""

# Retention: newest KEEP_DAILY dated dirs + newest KEEP_WEEKLY Sunday-dated dirs; only strict YYYYMMDD names with a manifest.
mapfile -t DIRS < <(find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d -regextype posix-extended -regex '.*/[0-9]{8}' -printf '%f\n' | sort -r)
declare -A KEEP=(); n=0; w=0
for d in "${DIRS[@]}"; do
  (( n < KEEP_DAILY )) && { KEEP[$d]=1; }
  n=$((n+1))
  if [[ "$(date -u -d "${d:0:4}-${d:4:2}-${d:6:2}" +%u 2>/dev/null)" == 7 ]] && (( w < KEEP_WEEKLY )); then KEEP[$d]=1; w=$((w+1)); fi
done
for d in "${DIRS[@]}"; do
  [[ -n "${KEEP[$d]:-}" ]] && continue
  [[ -f "$BACKUP_ROOT/$d/SHA256SUMS" ]] || { log "retention: skipping $d (no manifest)"; continue; }
  log "retention: removing $d"; rm -rf -- "${BACKUP_ROOT:?}/$d"
done

DONE=1
write_status OK "snapshot=$SNAP files=$NFILES"
log "OK snapshot=$SNAP files=$NFILES"
