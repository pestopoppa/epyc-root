#!/bin/bash
# restore_test_loop_state.sh -- BK-4 restore test for the loop-state snapshots written by backup_loop_state.sh.
# Restores a snapshot into a SCRATCH dir, then checks: sha256sum -c; PRAGMA integrity_check on every SQLite DB;
# vidya `verify` on the restored ledger (chain_ok). Prints one PASS/FAIL line per check; exit 0 only if all pass.
# PREPARED ONLY -- run on the host (needs /mnt/micron). The restore copies the whole snapshot
# (~4.8 GiB Monday, ~10.2 GiB Sunday), so point --scratch at a disk with room; the scratch dir
# is removed on exit unless --keep.
#
# Usage: restore_test_loop_state.sh --scratch DIR [--snapshot DIR | --backup-root DIR] [--keep] [--vidya-cli PATH]
#   --snapshot     a YYYYMMDD snapshot dir (default: newest dated dir with a SHA256SUMS under --backup-root)
#   --backup-root  default /mnt/micron/loop-state-backups
#   --vidya-cli    default <checkout>/scripts/vidya/cli.py ; if absent the ledger check FAILS (never silently skipped)
set -euo pipefail

BACKUP_ROOT=/mnt/micron/loop-state-backups; SNAPSHOT=""; SCRATCH=""; KEEP=0
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_VIDYA_CLI="$SCRIPT_DIR/../vidya/cli.py"
[[ -f "$DEFAULT_VIDYA_CLI" ]] || DEFAULT_VIDYA_CLI="/mnt/raid0/llm/epyc-root/scripts/vidya/cli.py"
VIDYA_CLI="${VIDYA_CLI:-$DEFAULT_VIDYA_CLI}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --scratch) SCRATCH="$2"; shift 2;;
    --snapshot) SNAPSHOT="$2"; shift 2;;
    --backup-root) BACKUP_ROOT="$2"; shift 2;;
    --vidya-cli) VIDYA_CLI="$2"; shift 2;;
    --keep) KEEP=1; shift;;
    *) echo "unknown arg $1" >&2; exit 2;;
  esac
done
[[ -n "$SCRATCH" ]] || { echo "--scratch DIR required" >&2; exit 2; }
if [[ -z "$SNAPSHOT" ]]; then
  latest="$(find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d -regextype posix-extended -regex '.*/[0-9]{8}' -printf '%f\n' 2>/dev/null | sort -r | head -n1 || true)"
  [[ -n "$latest" ]] || { echo "FAIL no dated snapshot under $BACKUP_ROOT"; exit 1; }
  SNAPSHOT="$BACKUP_ROOT/$latest"
fi
[[ -f "$SNAPSHOT/SHA256SUMS" ]] || { echo "FAIL $SNAPSHOT has no SHA256SUMS"; exit 1; }
[[ ! -e "$SCRATCH" || -z "$(ls -A "$SCRATCH" 2>/dev/null)" ]] || { echo "scratch $SCRATCH not empty; refusing" >&2; exit 2; }

# The restore copies the whole snapshot. Refuse early rather than filling a small disk.
SCRATCH_PARENT="$(dirname "$SCRATCH")"
mkdir -p "$SCRATCH_PARENT"
need_kib="$(du -sk "$SNAPSHOT" | awk '{print $1}')"
avail_kib="$(df -Pk "$SCRATCH_PARENT" | awk 'NR == 2 {print $4}')"
if [[ -z "$need_kib" || -z "$avail_kib" ]] || (( avail_kib < need_kib + 1048576 )); then
  echo "FAIL scratch filesystem $SCRATCH_PARENT has ${avail_kib:-unknown} KiB free;" \
       "need at least $(( ${need_kib:-0} + 1048576 )) KiB (snapshot + 1 GiB)" >&2
  exit 1
fi
mkdir -p "$SCRATCH"
cleanup() { [[ $KEEP -eq 1 ]] || rm -rf -- "$SCRATCH"; }
trap cleanup EXIT

FAILS=0
check() { if [[ "$1" == 0 ]]; then echo "PASS $2"; else echo "FAIL $2"; FAILS=$((FAILS+1)); fi; }

echo "restoring $SNAPSHOT -> $SCRATCH"
cp -a -- "$SNAPSHOT"/. "$SCRATCH"/
rc=0; ( cd "$SCRATCH" && sha256sum -c --quiet SHA256SUMS ) || rc=$?
check $rc "sha256sum -c SHA256SUMS"

ndb=0
while IFS= read -r -d '' db; do
  ndb=$((ndb+1))
  out="$(sqlite3 "$db" "pragma integrity_check" 2>&1 || true)"
  rc=0; [[ "$out" == ok ]] || rc=1
  check $rc "integrity_check ${db#"$SCRATCH"/}$([[ $rc -ne 0 ]] && echo " ($out)")"
done < <(find "$SCRATCH" -type f \( -name '*.db' -o -name '*.sqlite' -o -name '*.sqlite3' \) -print0)
rc=0; [[ $ndb -gt 0 ]] || rc=1
check $rc "found $ndb SQLite DB(s)"

LEDGER="$SCRATCH/state/vidya/ledger.jsonl"
if [[ -f "$LEDGER" && -f "$VIDYA_CLI" ]]; then
  # --json is required: the human output says "chain=OK", which the old chain_ok grep did not match.
  vout="$(python3 "$VIDYA_CLI" --ledger "$LEDGER" --json verify 2>&1 || true)"
  rc=0
  python3 -c 'import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get("chain_ok") is True else 1)' \
    <<<"$vout" || rc=1
  check $rc "vidya verify chain_ok"
  [[ $rc -eq 0 ]] || echo "$vout" | tail -5
else
  check 1 "vidya verify (ledger or cli missing: $LEDGER / $VIDYA_CLI)"
fi
echo "restore test: $FAILS failure(s)"
[[ $FAILS -eq 0 ]]
