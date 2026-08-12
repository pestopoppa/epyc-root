#!/bin/bash
set -euo pipefail
# setup_main_worktrees.sh — create/verify per-main LANE worktrees (P1/4).
#
# Companion doc: scripts/coordination/WORKTREE_MIGRATION.md (the two-plane
# model this machinery implements: canonical runtime plane at /workspace —
# bus, token-queue, audit log, sidecars — vs. a versioned WORK plane, one
# worktree per main, on its own `lane/<agent>` branch).
#
# WHY A SEPARATE WORKTREE PER MAIN. session_bus.py used to resolve its bus
# root via Path(__file__).resolve().parents[2] — fine for one checkout, but
# five mains committing concurrently in the SAME /workspace working tree is
# the actual mechanism behind tonight's 21-conflict merge (89 bus files
# git-tracked and churning, plus ordinary work-tree contention on everything
# else). Five worktrees isolate the CHURN; item 1 of this task already fixed
# the bus root so those five worktrees do NOT also fork the coordination
# runtime plane (every worktree's session_bus.py still resolves to the ONE
# canonical /workspace/coordination/session-bus, verified in step (b) below).
#
# WHAT THIS SCRIPT DOES, per agent name given on the command line:
#   1. git worktree add /mnt/raid0/llm/worktrees/mains/<agent> on branch
#      lane/<agent> (created from the current tip of `main` if the branch
#      does not exist yet; checked out as-is if it does — so re-running this
#      for an agent that already has commits on its lane is a no-op on the
#      branch, not a reset).
#   2. Runs the WORKTREE's OWN copy of clone-repos.sh (not /workspace's) so
#      repos/* symlinks exist there too — read clone-repos.sh first: it
#      computes REPOS_DIR from `$(dirname "$0")/..`, i.e. relative to
#      wherever it is invoked FROM, not a baked /workspace literal. Running
#      the worktree's own copy therefore naturally targets the worktree's
#      own repos/ without any change to clone-repos.sh itself.
#   3. Verifies (a) a commit made on the lane branch, inside the worktree,
#      actually fires the shared pre-commit hooks (a secret-shaped blob is
#      staged and MUST be blocked; a clean scratch file is staged and MUST
#      commit; the clean scratch commit is then `git reset --hard` off the
#      tip — sanctioned here because this is the worktree's OWN lane branch,
#      not a shared one, so rewriting its tip has zero blast radius outside
#      this worktree) and (b) session_bus.py, run from inside the worktree
#      with no EPYC_BUS_ROOT set, resolves --print-root to the ONE canonical
#      /workspace/coordination/session-bus — never a worktree-relative path.
#
# IDEMPOTENT. Re-running for an agent that already has a valid worktree on
# lane/<agent> skips creation (step 1) but always re-runs the repos symlink
# pass and both verifications — cheap, and the point of "idempotent" here is
# "safe and informative to re-run as a health check", not just "does not
# error twice".
#
# REFUSES before doing anything if MAINS_ROOT already exists and contains
# ANY entry that does not check out cleanly as a worktree of THIS repo on
# its expected lane/<name> branch (stray file, foreign directory, wrong
# branch, broken worktree metadata) — see validate_mains_root(). An empty or
# absent MAINS_ROOT, or one containing only entries that validate cleanly,
# is fine.
#
# THIS RUN (2026-08-12, guard-universe-and-worktree-isolation P1/4): built
# and tested against a single THROWAWAY agent name (wttest), never against
# mainA/mainB/mainC/mainD/auditor — creating the five real lane worktrees is
# phase 2, explicitly post-reboot, explicitly not this task's to do. The
# throwaway worktree and its lane/wttest branch were removed after
# verification (`git worktree remove` + `git worktree prune` + `git branch
# -D lane/wttest`) — see the task's final report for the transcript.
#
# Usage:
#   scripts/coordination/setup_main_worktrees.sh <agent> [<agent> ...]
#   scripts/coordination/setup_main_worktrees.sh mainA mainB mainC mainD auditor

MAINS_ROOT="/mnt/raid0/llm/worktrees/mains"
REPO_ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
CANONICAL_BUS_ROOT="/workspace/coordination/session-bus"

if [[ "$#" -eq 0 ]]; then
  echo "usage: $0 <agent> [<agent> ...]" >&2
  exit 64
fi

log() { printf '[setup-main-worktrees] %s\n' "$*"; }
die() { printf '[setup-main-worktrees] REFUSING: %s\n' "$*" >&2; exit 1; }

# --------------------------------------------------------------- validation

our_common_dir() {
  local c
  c="$(git -C "$REPO_ROOT" rev-parse --git-common-dir 2>/dev/null)" || return 1
  [[ "$c" = /* ]] || c="${REPO_ROOT}/${c}"
  (cd "$c" 2>/dev/null && pwd -P) || printf '%s\n' "$c"
}

validate_mains_root() {
  [[ -d "$MAINS_ROOT" ]] || return 0
  local expect_common entry name branch entry_common
  expect_common="$(our_common_dir)" || die "cannot resolve this repo's own git-common-dir"

  local -a entries=()
  shopt -s nullglob
  entries=("$MAINS_ROOT"/*)
  shopt -u nullglob

  for entry in "${entries[@]}"; do
    name="$(basename "$entry")"
    [[ -e "$entry/.git" ]] || die "$entry exists but has no .git — not a worktree"
    branch="$(git -C "$entry" symbolic-ref --short -q HEAD || true)"
    [[ "$branch" == "lane/$name" ]] || \
      die "$entry is on branch '${branch:-<detached>}', expected 'lane/$name'"
    entry_common="$(git -C "$entry" rev-parse --git-common-dir 2>/dev/null)" || \
      die "$entry: git-common-dir unresolvable"
    [[ "$entry_common" = /* ]] || entry_common="${entry}/${entry_common}"
    entry_common="$(cd "$entry_common" 2>/dev/null && pwd -P)" || \
      die "$entry: git-common-dir does not resolve to a real path"
    [[ "$entry_common" == "$expect_common" ]] || \
      die "$entry is a worktree of a DIFFERENT repo (common-dir $entry_common != $expect_common)"
  done
}

# ------------------------------------------------------------------ per-agent

setup_one() {
  local agent="$1" wt="$MAINS_ROOT/$agent" branch="lane/$agent"

  if [[ -e "$wt" ]]; then
    log "$agent: worktree already present at $wt — verifying, not recreating"
  else
    if git -C "$REPO_ROOT" show-ref --verify --quiet "refs/heads/$branch"; then
      log "$agent: branch $branch already exists — checking it out into a new worktree"
      git -C "$REPO_ROOT" worktree add "$wt" "$branch"
    else
      log "$agent: creating $wt on new branch $branch (from current tip of main)"
      git -C "$REPO_ROOT" worktree add -b "$branch" "$wt" main
    fi
  fi

  log "$agent: syncing repos/* symlinks via the worktree's OWN clone-repos.sh"
  if [[ -x "$wt/scripts/clone-repos.sh" || -f "$wt/scripts/clone-repos.sh" ]]; then
    DRY_RUN=0 bash "$wt/scripts/clone-repos.sh"
  else
    die "$wt/scripts/clone-repos.sh missing — worktree checkout is incomplete"
  fi

  verify_hooks_fire "$agent" "$wt"
  verify_bus_root_canonical "$agent" "$wt"
  log "$agent: OK"
}

# Stage a secret-shaped blob and a clean file in turn, on the lane branch,
# inside the worktree; confirm the shared pre-commit hook blocks the first
# and allows the second, then remove the scratch commit. `git reset --hard`
# is sanctioned here (see header) because lane/<agent> is this worktree's own
# throwaway-for-verification branch at this point in setup — no other
# worktree or session has based anything on this tip yet.
#
# BAD_BLOB is assembled from two literals, not written whole: a single
# literal would itself match pii_precommit.sh's AKIA[0-9A-Z]{16} pattern and
# block every commit of THIS FILE. Same trick, same reason, as
# scripts/hooks/tests/test_precommit_wrapper.sh's BAD_BLOB. Not a real
# credential; do not "simplify" this to one literal.
verify_hooks_fire() {
  local agent="$1" wt="$2" before after
  local bad_blob="AKIA""1234567890ABCDEF"
  before="$(git -C "$wt" rev-parse HEAD)"

  printf '%s\n' "$bad_blob" > "$wt/.setup-worktree-scratch"
  git -C "$wt" add .setup-worktree-scratch
  if git -C "$wt" commit -m "scratch: secret-shaped blob (setup verification, must block)" \
       >/tmp/setup-worktree-hook-check.$$ 2>&1; then
    rm -f /tmp/setup-worktree-hook-check.$$
    die "$agent: pre-commit hook did NOT block a secret-shaped blob inside $wt — hooks are not firing"
  fi
  rm -f /tmp/setup-worktree-hook-check.$$
  git -C "$wt" reset --quiet HEAD -- .setup-worktree-scratch 2>/dev/null || true

  printf '%s\n' 'setup-worktree verification scratch file' > "$wt/.setup-worktree-scratch"
  git -C "$wt" add .setup-worktree-scratch
  git -C "$wt" commit -q -m "scratch: clean file (setup verification, must pass then be reverted)"
  after="$(git -C "$wt" rev-parse HEAD)"
  [[ "$after" != "$before" ]] || die "$agent: clean scratch commit did not land"

  git -C "$wt" reset --hard --quiet "$before"
  rm -f "$wt/.setup-worktree-scratch"
  log "$agent: shared pre-commit hooks fire correctly inside the worktree (blocked the secret, allowed the clean commit, scratch commit removed)"
}

verify_bus_root_canonical() {
  local agent="$1" wt="$2" resolved
  resolved="$(cd "$wt" && env -u EPYC_BUS_ROOT python3 scripts/coordination/session_bus.py --print-root)"
  [[ "$resolved" == "$CANONICAL_BUS_ROOT" ]] || \
    die "$agent: session_bus.py --print-root resolved to '$resolved', expected the canonical '$CANONICAL_BUS_ROOT' — bus root is NOT worktree-safe"
  log "$agent: session_bus.py --print-root -> $resolved (canonical, worktree-safe)"
}

# ----------------------------------------------------------------------- main

validate_mains_root
mkdir -p "$MAINS_ROOT"

for agent in "$@"; do
  setup_one "$agent"
done

log "done: $* — $MAINS_ROOT"
