#!/bin/bash
# deploy_when_drained.sh - hold NEW admissions, let running grants drain, deploy rowflow, ALWAYS release the hold
# (operator 2026-11-07, "Pause admissions, then deploy").
#
#   timeout 28800 deploy_when_drained.sh [--reason "<text>"] [--owner <id>] [--poll-s 30] [--repo /path/to/main-clone]
#
# 1. set  <flags>/HOLD-ADMISSIONS (owner=, reason=, since=). Keepers built from this tree honour it (no new grants or
#         admissions; running rows and healing continue). The keeper deployed BEFORE this change only knows HOLD_*, so a
#         compat symlink HOLD_ADMISSIONS -> HOLD-ADMISSIONS is created too (the live keeper then logs "HOLD present;
#         nothing allocated"); the symlink is removed the moment the new files are installed, because deploy_rowflow's
#         post-install verification needs a keeper SNAPSHOT line, which a HOLD_* keeper never writes.
# 2. wait until <flags>/grants has no *.grant (deploy_rowflow refuses to swap filler_run15.sh under open grants).
# 3. run  deploy_rowflow.sh --repo <fresh worktree at origin/main> --ref origin/main --emergency "<reason>".
# 4. trap: HOLD-ADMISSIONS (and the compat symlink) are removed on EVERY exit - success, failure, signal, timeout.
set -euo pipefail

FLAGS=${ROWFLOW_FLAGS:-/mnt/raid0/llm/tmp/compute-flags}
REPO=/workspace
POLL=30
OWNER=${DEPLOY_OWNER:-operator-adhoc-ops-20261105}
REASON="operator 2026-11-07: batch (q3/docker, Pass-5, gpu-quiet guard, disk-floor pause, admission hold)"
while [ $# -gt 0 ]; do
  case "$1" in
    --reason) REASON=$2; shift 2 ;;
    --owner) OWNER=$2; shift 2 ;;
    --poll-s) POLL=$2; shift 2 ;;
    --repo) REPO=$2; shift 2 ;;
    *) echo "unknown arg $1" >&2; exit 64 ;;
  esac
done
HOLD="$FLAGS/HOLD-ADMISSIONS"; COMPAT="$FLAGS/HOLD_ADMISSIONS"
ts() { date -u +%FT%TZ; }
FRESH=""; DPID=""
cleanup() {
  local rc=$?
  trap - EXIT INT TERM HUP
  [ -z "$DPID" ] || { kill -0 "$DPID" 2>/dev/null && echo "$(ts) deploy_when_drained: deploy_rowflow pid $DPID still running at exit; leaving it to finish" >&2; } || true
  rm -f "$COMPAT" "$HOLD"
  [ -z "$FRESH" ] || git -C "$REPO" worktree remove --force "$FRESH" >/dev/null 2>&1 || true
  echo "$(ts) deploy_when_drained: HOLD-ADMISSIONS released (exit $rc)"
  exit "$rc"
}
trap cleanup EXIT
trap 'exit 143' INT TERM HUP

git -C "$REPO" fetch -q origin
FRESH=$(mktemp -u "${REPLAY_SCRATCH:-/mnt/raid0/llm/tmp/rowflow-replay}/dwd-XXXXXX")
mkdir -p "$(dirname "$FRESH")"
git -C "$REPO" worktree add --detach -q "$FRESH" origin/main
echo "$(ts) deploy_when_drained: fresh worktree $FRESH at $(git -C "$FRESH" rev-parse --short origin/main)"

printf 'owner=%s\nreason=%s\nsince=%s\n' "$OWNER" "$REASON" "$(ts)" > "$HOLD.part"; mv -f "$HOLD.part" "$HOLD"
ln -sfn HOLD-ADMISSIONS "$COMPAT"
echo "$(ts) deploy_when_drained: HOLD-ADMISSIONS set (owner=$OWNER); waiting for grants/ to drain"

last=-1
while :; do
  n=$(find "$FLAGS/grants" -maxdepth 1 -name '*.grant' | wc -l)
  [ "$n" -eq 0 ] && break
  [ "$n" = "$last" ] || echo "$(ts) deploy_when_drained: $n open grant(s)"   # log on change only
  last=$n
  sleep "$POLL"
done
echo "$(ts) deploy_when_drained: drained; deploying"

SHA=$(git -C "$FRESH" rev-parse origin/main)
bash "$FRESH/scripts/coordination/rowflow/deploy_rowflow.sh" --repo "$FRESH" --ref origin/main --emergency "$REASON" &
DPID=$!
while kill -0 "$DPID" 2>/dev/null; do   # the moment the new files are in, the HOLD_* compat link must go (see header)
  if [ -e "$COMPAT" ] && [ "$(python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get('sha',''))" "$FLAGS/bin/rowflow/DEPLOYED.json" 2>/dev/null)" = "$SHA" ]; then
    rm -f "$COMPAT"; echo "$(ts) deploy_when_drained: installed $SHA; HOLD_ADMISSIONS compat link removed for the keeper SNAPSHOT check"
  fi
  sleep 2
done
rc=0; wait "$DPID" || rc=$?
DPID=""
echo "$(ts) deploy_when_drained: deploy_rowflow exit $rc"
exit "$rc"
