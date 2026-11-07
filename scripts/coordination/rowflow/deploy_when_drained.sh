#!/bin/bash
# deploy_when_drained.sh - wait until no LEGACY grant reads the live engine, then deploy rowflow. NO admission hold
# (operator 2026-11-07 "no-hold deploys": a global HOLD-ADMISSIONS idled q2, q3 and the GPU for hours).
#
#   timeout 28800 deploy_when_drained.sh [--reason "<text>"] [--poll-s 30] [--repo /path/to/main-clone]
#
# Rows armed by a snapshot-aware keeper run their own engine copy (<flags>/dryrun/<id>/engine/), so they never block a
# deploy and nothing has to drain. Only LEGACY grants (pollers armed before the snapshot keeper, which still re-read
# bin/rowflow/) are waited for; admissions continue the whole time.
# 1. fresh detached worktree at origin/main (removed on every exit)
# 2. wait until `rowflow.py legacy-grants` (from that worktree) prints nothing
# 3. run  deploy_rowflow.sh --repo <fresh worktree> --ref origin/main --emergency "<reason>"
# Nothing under <flags> is created or removed by this script (no HOLD-ADMISSIONS, no HOLD_* link).
set -euo pipefail

FLAGS=${ROWFLOW_FLAGS:-/mnt/raid0/llm/tmp/compute-flags}
REPO=/workspace
POLL=30
REASON="operator 2026-11-07: rowflow deploy (no-hold)"
while [ $# -gt 0 ]; do
  case "$1" in
    --reason) REASON=$2; shift 2 ;;
    --owner) shift 2 ;;   # accepted for compatibility; there is no hold to own
    --poll-s) POLL=$2; shift 2 ;;
    --repo) REPO=$2; shift 2 ;;
    *) echo "unknown arg $1" >&2; exit 64 ;;
  esac
done
ts() { date -u +%FT%TZ; }
FRESH=""
cleanup() {
  local rc=$?
  trap - EXIT INT TERM HUP
  [ -z "$FRESH" ] || git -C "$REPO" worktree remove --force "$FRESH" >/dev/null 2>&1 || true
  echo "$(ts) deploy_when_drained: exit $rc"
  exit "$rc"
}
trap cleanup EXIT
trap 'exit 143' INT TERM HUP

git -C "$REPO" fetch -q origin
FRESH=$(mktemp -u "${REPLAY_SCRATCH:-/mnt/raid0/llm/tmp/rowflow-replay}/dwd-XXXXXX")
mkdir -p "$(dirname "$FRESH")"
git -C "$REPO" worktree add --detach -q "$FRESH" origin/main
echo "$(ts) deploy_when_drained: fresh worktree $FRESH at $(git -C "$FRESH" rev-parse --short HEAD); admissions continue (no hold)"

last=""
while :; do
  legacy=$(ROWFLOW_FLAGS="$FLAGS" python3 -I "$FRESH/scripts/coordination/rowflow/rowflow.py" --flags "$FLAGS" legacy-grants | tr '\n' ' ')
  [ -z "${legacy// /}" ] && break
  [ "$legacy" = "$last" ] || echo "$(ts) deploy_when_drained: waiting for legacy grant(s) on the live engine: $legacy"   # log on change only
  last=$legacy
  sleep "$POLL"
done
echo "$(ts) deploy_when_drained: no legacy grant reads the live engine; deploying"
rc=0
bash "$FRESH/scripts/coordination/rowflow/deploy_rowflow.sh" --repo "$FRESH" --ref HEAD --emergency "$REASON" || rc=$?
echo "$(ts) deploy_when_drained: deploy_rowflow exit $rc"
exit "$rc"
