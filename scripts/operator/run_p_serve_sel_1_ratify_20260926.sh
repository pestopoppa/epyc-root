#!/bin/bash
# run_p_serve_sel_1_ratify_20260926.sh — the operator's single command for P-SERVE-SEL-1
# (operator decision OP-62, ratified 2026-09-26 in the orchestrator-design session).
#
#   bash /mnt/raid0/llm/epyc-root/scripts/operator/run_p_serve_sel_1_ratify_20260926.sh --operator <your-name>
#
# It runs from any directory, as long as /mnt/raid0/llm/epyc-root is available. Steps:
#   1. git fetch origin in /mnt/raid0/llm/epyc-root
#   2. create worktree /mnt/raid0/llm/worktrees/op-p-serve-sel-1-ratify-20260926 on a NEW branch
#      op/p-serve-sel-1-ratify-apply from origin/main. If the worktree already exists, it refuses
#      unless --resume is given.
#   3. show the ratify script's review (preflight plus the full amendment diff); writes nothing
#   4. ask you to type RATIFY, read from your terminal
#   5. run the ratify script with --apply and RATIFY_OPERATOR=<your-name>. It applies the pinned
#      patch, writes the three receipts, and commits exactly its five paths through a private index.
#   6. run the ratify script with --verify (read-only post-state check)
#   7. STOP, printing the branch and commit SHA. A session pushes and merges it.
#
# It never pushes. It never touches the /workspace working tree: every write lands in the new
# worktree, and the only other effects are refs and objects in the shared .git (fetch, a new
# worktree, a new branch). The trust-boundary edit itself is made by
# scripts/operator/ratify_p_serve_sel_1_20260926.sh, which pins every hash and rolls back on any
# failure.
#
# Options:
#   --operator <name>  required; recorded in the receipts and the commit trailer
#   --resume           reuse an existing op-p-serve-sel-1-ratify worktree (after an interrupted run)
#
# Test hooks (NOT for the operator): only when PSS1_RATIFY_WRAPPER_TEST=1 are these honored:
#   --yes, which skips the tty prompt, and the env overrides EPYC_ROOT_OVERRIDE, WT_DIR_OVERRIDE and
#   OP_BRANCH_OVERRIDE. Without that variable, --yes is refused and the paths are fixed.
set -euo pipefail

TEST_MODE="${PSS1_RATIFY_WRAPPER_TEST:-0}"
EPYC_ROOT="/mnt/raid0/llm/epyc-root"
WT_DIR="/mnt/raid0/llm/worktrees/op-p-serve-sel-1-ratify-20260926"
OP_BRANCH="op/p-serve-sel-1-ratify-apply"
if [ "$TEST_MODE" = "1" ]; then
  EPYC_ROOT="${EPYC_ROOT_OVERRIDE:-$EPYC_ROOT}"
  WT_DIR="${WT_DIR_OVERRIDE:-$WT_DIR}"
  OP_BRANCH="${OP_BRANCH_OVERRIDE:-$OP_BRANCH}"
fi
RATIFY_REL="scripts/operator/ratify_p_serve_sel_1_20260926.sh"
SUBJECT="RATIFIED: P-SERVE-SEL-1 — text-LLM serving-selection load-sweep A/B protocol, Annex Q (OP-62, 2026-09-26)"

die() { printf '\nREFUSING: %b\n' "$*" >&2; exit 65; }
say() { printf '%s\n' "$*"; }
hdr() { printf '\n==== %s ====\n' "$*"; }

OPERATOR=""; RESUME=0; YES=0
while [ $# -gt 0 ]; do
  case "$1" in
    --operator) [ $# -ge 2 ] || die "--operator needs a name"; OPERATOR="$2"; shift 2 ;;
    --resume)   RESUME=1; shift ;;
    --yes)      [ "$TEST_MODE" = "1" ] || die "--yes is a test-only flag; the operator path is interactive"
                YES=1; shift ;;
    -h|--help)  sed -n '2,33p' "$0"; exit 0 ;;
    *) die "unknown argument: $1 (usage: $0 --operator <name> [--resume])" ;;
  esac
done
[ -n "$OPERATOR" ] || die "--operator <name> is required (usage: $0 --operator <name> [--resume])"
# Same rule as the ratifier: a system account, the login (id -un) or an agent id is refused.
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/ratify_operator.sh"
ratify_require_operator "$OPERATOR"; OPERATOR="$RATIFY_OPERATOR"
case "$OPERATOR" in *$'\n'*|*[[:cntrl:]]*) die "operator name contains control characters" ;; esac

[ -d "$EPYC_ROOT/.git" ] || [ -f "$EPYC_ROOT/.git" ] || die "$EPYC_ROOT is not a git checkout"
G() { git -C "$WT_DIR" "$@"; }

# ------------------------------------------------------------------ 1. fetch
hdr "1/7 fetch origin ($EPYC_ROOT)"
git -C "$EPYC_ROOT" fetch origin || die "git fetch origin failed; nothing created"
ORIGIN_MAIN="$(git -C "$EPYC_ROOT" rev-parse origin/main)"
say "origin/main = $ORIGIN_MAIN"

# ------------------------------------------------------------------ 2. worktree
hdr "2/7 worktree $WT_DIR (branch $OP_BRANCH)"
if [ -e "$WT_DIR" ]; then
  [ "$RESUME" -eq 1 ] || die "$WT_DIR already exists. If a previous run was interrupted, re-run with --resume; otherwise inspect it first."
  cur="$(G rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
  [ "$cur" = "$OP_BRANCH" ] || die "--resume: $WT_DIR is on '$cur', not $OP_BRANCH"
  say "resuming the existing worktree on $OP_BRANCH ($(G rev-parse --short HEAD))"
else
  [ "$RESUME" -eq 0 ] || die "--resume given, but $WT_DIR does not exist"
  if git -C "$EPYC_ROOT" show-ref --verify --quiet "refs/heads/$OP_BRANCH"; then
    die "branch $OP_BRANCH already exists without the worktree. Inspect it (git -C $EPYC_ROOT log -3 $OP_BRANCH) and delete it by hand if it is stale."
  fi
  mkdir -p "$(dirname "$WT_DIR")"
  git -C "$EPYC_ROOT" worktree add -b "$OP_BRANCH" "$WT_DIR" origin/main \
    || die "git worktree add failed"
fi

[ -f "$WT_DIR/$RATIFY_REL" ] || die "$RATIFY_REL is not on origin/main yet: the research-intake lane intake/orch-prior-art-20260926 must be merged first"

# Already committed? (resume after step 5)
if G log -1 --format=%s | grep -qF "$SUBJECT"; then
  hdr "already done"
  say "HEAD already carries the ratification commit."
  ROOT="$WT_DIR" bash "$WT_DIR/$RATIFY_REL" --verify || die "--verify failed on the committed state; read the output above"
  say "  branch: $OP_BRANCH"
  say "  commit: $(G rev-parse HEAD)"
  say "Nothing to do. Hand the branch to a session to push and merge."
  exit 0
fi

# ------------------------------------------------------------------ 3. review
hdr "3/7 review (writes nothing)"
REV_LOG="$(mktemp)"; trap 'rm -f "$REV_LOG"' EXIT
set +e
ROOT="$WT_DIR" bash "$WT_DIR/$RATIFY_REL" --review 2>&1 | tee "$REV_LOG"
rev_rc="${PIPESTATUS[0]}"
set -e
[ "$rev_rc" -eq 0 ] || die "the review refused (exit $rev_rc); read the output above. Nothing written."
grep -q '^ALREADY RATIFIED' "$REV_LOG" && die "the amendment is already applied in this worktree but not committed with the expected subject; resolve by hand (ROOT=$WT_DIR bash $WT_DIR/$RATIFY_REL --verify)"

# ------------------------------------------------------------------ 4. confirm
hdr "4/7 confirm"
if [ "$YES" -eq 1 ]; then
  say "(test mode: --yes, prompt skipped)"
else
  [ -r /dev/tty ] || die "no terminal to read the confirmation from; run this interactively"
  printf 'The diff above will be applied to MEASUREMENT.md and measurement/protocols/quality-eval.md\n'
  printf 'in %s, as operator "%s", and committed on %s.\nType RATIFY to apply: ' "$WT_DIR" "$OPERATOR" "$OP_BRANCH"
  IFS= read -r answer < /dev/tty || die "could not read from the terminal"
  [ "$answer" = "RATIFY" ] || die "confirmation was '$answer', not RATIFY. Nothing applied; the worktree is left for --resume."
fi

# ------------------------------------------------------------------ 5. apply + commit
hdr "5/7 apply + receipts + commit"
RATIFY_OPERATOR="$OPERATOR" ROOT="$WT_DIR" bash "$WT_DIR/$RATIFY_REL" --apply \
  || die "ratify --apply failed (it rolls itself back before the commit step); read the output above"

# ------------------------------------------------------------------ 6. verify
hdr "6/7 verify (read-only)"
ROOT="$WT_DIR" bash "$WT_DIR/$RATIFY_REL" --verify || die "--verify failed after apply; read the output above. Nothing was pushed."

# ------------------------------------------------------------------ 7. stop
hdr "7/7 DONE (not pushed)"
say "  worktree: $WT_DIR"
say "  branch:   $OP_BRANCH"
say "  commit:   $(G rev-parse HEAD)"
say "Hand these to a session to push and merge. This script never pushes."
