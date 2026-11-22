#!/bin/bash
# run_ratify_codebudget_ratchet_autokernel_20261122.sh -- pull-free launcher for
# ratify_ak_loop_code_budget_ratchet_20261122.sh (OP-AK-CODEBUDGET-43). Fetches origin, checks out a detached
# worktree on origin/main, runs the ratify script there (args pass through), removes the worktree.
# Single line, works from fish or bash, no sudo needed (scripts/operator is node-owned):
#   Sign:   git -C /mnt/raid0/llm/epyc-root fetch -q origin main; and git -C /mnt/raid0/llm/epyc-root show origin/main:scripts/operator/run_ratify_codebudget_ratchet_autokernel_20261122.sh | env RATIFY_OPERATOR='<your name>' bash -s -- --apply --attest RATIFY-AK-LOOP-CODE-BUDGET-RATCHET-20261122
#   Review: same line, drop `env RATIFY_OPERATOR=...` and the args.   Verify: `... | bash -s -- --verify`.
set -euo pipefail
main() {
  R="${RUNNER_ROOT:-/mnt/raid0/llm/epyc-root}"
  P="${RUNNER_WT_PARENT:-/mnt/raid0/llm/worktrees}"
  D="$P/ratify-cb-ratchet22-run-$(date -u +%m%d-%H%M%S)-$$"
  git -C "$R" fetch -q origin main
  git -C "$R" worktree add -q --detach "$D" origin/main
  rc=0
  ROOT="$D" bash "$D/scripts/operator/ratify_ak_loop_code_budget_ratchet_20261122.sh" "$@" </dev/null || rc=$?
  git -C "$R" worktree remove "$D" || echo "WARN: could not remove $D (plain remove); remove it by hand" >&2
  return "$rc"
}
main "$@"
exit $?
