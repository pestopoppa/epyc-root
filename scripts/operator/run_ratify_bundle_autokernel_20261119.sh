#!/bin/bash
# run_ratify_bundle_autokernel_20261119.sh -- pull-free launcher for ratify_bundle_autokernel_20261119.sh.
# Fetches origin, checks out a detached worktree on origin/main, runs the bundle there (all args pass through,
# terminal attached for item 1's RATIFY prompt), then removes the worktree. Works from a stale clone:
#   git -C /mnt/raid0/llm/epyc-root fetch -q origin main && git -C /mnt/raid0/llm/epyc-root show origin/main:scripts/operator/run_ratify_bundle_autokernel_20261119.sh | bash -s -- --operator '<name>' --attest RATIFY-BUNDLE-AUTOKERNEL-20261119
set -euo pipefail
main() {
  R="${RUNNER_ROOT:-/mnt/raid0/llm/epyc-root}"
  P="${RUNNER_WT_PARENT:-/mnt/raid0/llm/worktrees}"
  D="$P/ratify-bundle-run-$(date -u +%m%d-%H%M%S)-$$"
  git -C "$R" fetch -q origin main
  git -C "$R" worktree add -q --detach "$D" origin/main
  rc=0
  if { : </dev/tty; } 2>/dev/null; then bash "$D/scripts/operator/ratify_bundle_autokernel_20261119.sh" "$@" </dev/tty || rc=$?
  else bash "$D/scripts/operator/ratify_bundle_autokernel_20261119.sh" "$@" </dev/null || rc=$?; fi
  git -C "$R" worktree remove "$D" || echo "WARN: could not remove $D (plain remove); remove it by hand" >&2
  return "$rc"
}
main "$@"
exit $?
