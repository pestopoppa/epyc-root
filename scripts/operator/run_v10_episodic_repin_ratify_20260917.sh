#!/bin/bash
# run_v10_episodic_repin_ratify_20260917.sh — the operator's single command for the v10 episodic
# re-pin (RATIFY-V10-EPISODIC-REPIN-20260917), after the operator-approved eval-leak memory purge
# of 2026-09-17 changed episodic.db / embeddings.faiss / id_map.npy in production_best.
#
#   From a HOST terminal (it needs a tty for the RATIFY prompt):
#   docker exec -it -u node epyc-root bash -c 'bash <(git -C /mnt/raid0/llm/epyc-root show origin/main:scripts/operator/run_v10_episodic_repin_ratify_20260917.sh) --operator <your-name>'
#
# It runs from any directory, as long as /mnt/raid0/llm/epyc-root is available. Steps:
#   1. git fetch origin in /mnt/raid0/llm/epyc-root
#   2. create worktree /mnt/raid0/llm/worktrees/op-v10-episodic-repin-20260917 on a NEW branch
#      op/v10-episodic-repin-apply from origin/main. If the worktree already exists, it refuses
#      unless --resume is given.
#   3. show the ratify script's dry-run (preflight, purge evidence and the full diff)
#   4. ask you to type RATIFY, read from your terminal
#   5. run the ratify script with --apply and RATIFY_OPERATOR=<your-name>. That step RE-PINS THE
#      UNTRACKED v10 checkpoint_meta.json IN PLACE in /mnt/raid0/llm/epyc-orchestrator/orchestration/
#      autopilot_checkpoints/multitier_v10_20260810/ (original backed up first to
#      /mnt/raid0/llm/backups/v10-episodic-repin-20260917/), and rewrites the v10 receipt in the
#      worktree. It never touches the episodic store itself. It refuses while AutoPilot runs.
#   6. stage EXACTLY the four tracked ratification paths, show the stat, refuse unless it is those 4
#   7. commit with the RATIFIED message and an "Operator-applied by <your-name>" trailer
#   8. STOP, printing the branch and commit SHA. A session pushes and merges it.
#
# It never pushes. It never touches the /workspace working tree. The only writes outside the new
# worktree are checkpoint_meta.json, its backup, and refs/objects in the shared .git.
#
# Options:
#   --operator <name>  required; recorded in the receipts and the commit trailer
#   --resume           reuse an existing op-v10-episodic-repin worktree (after an interrupted run)
#
# Test hooks (NOT for the operator): only when V10_REPIN_WRAPPER_TEST=1 are these honored:
#   --yes, which skips the tty prompt; the env overrides EPYC_ROOT_OVERRIDE, WT_DIR_OVERRIDE,
#   OP_BRANCH_OVERRIDE and BASE_REF_OVERRIDE; and ORCH / ORCH_GIT / BACKUP_DIR / PURGE_BACKUP /
#   TRUST_LOCK / V10_REPIN_TEST_* are passed through to the ratify script. Without that variable,
#   --yes is refused and every path is fixed.
set -euo pipefail

TEST_MODE="${V10_REPIN_WRAPPER_TEST:-0}"
EPYC_ROOT="/mnt/raid0/llm/epyc-root"
WT_DIR="/mnt/raid0/llm/worktrees/op-v10-episodic-repin-20260917"
OP_BRANCH="op/v10-episodic-repin-apply"
BASE_REF="origin/main"
if [ "$TEST_MODE" = "1" ]; then
  EPYC_ROOT="${EPYC_ROOT_OVERRIDE:-$EPYC_ROOT}"
  WT_DIR="${WT_DIR_OVERRIDE:-$WT_DIR}"
  OP_BRANCH="${OP_BRANCH_OVERRIDE:-$OP_BRANCH}"
  BASE_REF="${BASE_REF_OVERRIDE:-$BASE_REF}"
else
  unset ORCH ORCH_GIT BACKUP_DIR PURGE_BACKUP TRUST_LOCK ROOT \
        V10_REPIN_TEST_MODE V10_REPIN_TEST_PINS V10_REPIN_FAIL_AT PURGE_COMMIT_OVERRIDE
fi
RATIFY_REL="scripts/operator/ratify_v10_episodic_repin_20260917.sh"
COMMIT_PATHS=(
  "artifacts/operator/ratify_multitier_baseline_v10_20260810.json"
  "artifacts/operator/ratify_v10_episodic_repin_20260917.json"
  "artifacts/operator/receipts/RATIFY-V10-EPISODIC-REPIN-20260917.json"
  "artifacts/operator/ratify_v10_episodic_repin_20260917.receipt.json"
)
SUBJECT="RATIFIED: v10 production checkpoint re-pinned after the HumanEval/55 eval-leak memory purge (2026-09-17)"

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
    -h|--help)  say "usage: run_v10_episodic_repin_ratify_20260917.sh --operator <name> [--resume]"; exit 0 ;;
    *) die "unknown argument: $1 (usage: --operator <name> [--resume])" ;;
  esac
done
[ -n "$OPERATOR" ] || die "--operator <name> is required (usage: --operator <name> [--resume])"
case "$OPERATOR" in *$'\n'*|*[[:cntrl:]]*) die "operator name contains control characters" ;; esac

[ -d "$EPYC_ROOT/.git" ] || [ -f "$EPYC_ROOT/.git" ] || die "$EPYC_ROOT is not a git checkout"
G() { git -C "$WT_DIR" "$@"; }

# ------------------------------------------------------------------ 1. fetch
hdr "1/7 fetch origin ($EPYC_ROOT)"
git -C "$EPYC_ROOT" fetch origin || die "git fetch origin failed; nothing created"
BASE_SHA="$(git -C "$EPYC_ROOT" rev-parse "$BASE_REF")"
say "$BASE_REF = $BASE_SHA"

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
  git -C "$EPYC_ROOT" worktree add -b "$OP_BRANCH" "$WT_DIR" "$BASE_SHA" \
    || die "git worktree add failed"
fi

# Already committed? (resume after step 7)
if G log -1 --format=%s | grep -qF "$SUBJECT"; then
  hdr "already done"
  say "HEAD already carries the ratification commit."
  say "  branch: $OP_BRANCH"
  say "  commit: $(G rev-parse HEAD)"
  say "Nothing to do. Hand the branch to a session to push and merge."
  exit 0
fi

[ -f "$WT_DIR/$RATIFY_REL" ] || die "$RATIFY_REL is not on $BASE_REF yet: the prepared branch (sub/v10-episodic-repin-20260917) must be merged first"

# ------------------------------------------------------------------ 3. dry-run
hdr "3/7 dry-run (writes nothing)"
DRY_LOG="$(mktemp)"; trap 'rm -f "$DRY_LOG"' EXIT
set +e
ROOT="$WT_DIR" bash "$WT_DIR/$RATIFY_REL" --dry-run 2>&1 | tee "$DRY_LOG"
dry_rc="${PIPESTATUS[0]}"
set -e
[ "$dry_rc" -eq 0 ] || die "the dry-run refused (exit $dry_rc); read the output above. Nothing written."
ALREADY=0
grep -q '^ALREADY RATIFIED' "$DRY_LOG" && ALREADY=1

# ------------------------------------------------------------------ 4. confirm
if [ "$ALREADY" -eq 0 ]; then
  hdr "4/7 confirm"
  if [ "$YES" -eq 1 ]; then
    say "(test mode: --yes, prompt skipped)"
  else
    [ -r /dev/tty ] || die "no terminal to read the confirmation from; run this interactively (docker exec -it)"
    printf 'The diff above will be applied IN PLACE to the v10 checkpoint_meta.json (original backed up\n'
    printf 'first) and to the v10 receipt in %s, as operator "%s".\nType RATIFY to apply: ' "$WT_DIR" "$OPERATOR"
    IFS= read -r answer < /dev/tty || die "could not read from the terminal"
    [ "$answer" = "RATIFY" ] || die "confirmation was '$answer', not RATIFY. Nothing applied; the worktree is left for --resume."
  fi

  # ---------------------------------------------------------------- 5. apply
  hdr "5/7 apply"
  RATIFY_OPERATOR="$OPERATOR" ROOT="$WT_DIR" bash "$WT_DIR/$RATIFY_REL" --apply \
    || die "ratify --apply failed (it rolls itself back); read the output above"
else
  hdr "4-5/7 skipped: already applied (resume)"
fi

# ------------------------------------------------------------------ 6. stage
hdr "6/7 stage exactly the four ratification paths"
want="$(printf '%s\n' "${COMMIT_PATHS[@]}" | sort)"
if [ -n "$(G diff --cached --name-only)" ]; then
  staged_pre="$(G diff --cached --name-only | sort)"
  [ "$staged_pre" = "$want" ] || die "the index already holds other staged changes:\n$staged_pre"
fi
G add -- "${COMMIT_PATHS[@]}"
G diff --cached --stat
staged="$(G diff --cached --name-only | sort)"
n="$(printf '%s\n' "$staged" | sed '/^$/d' | wc -l | tr -d ' ')"
[ "$n" = "4" ] || die "staged $n files, expected exactly 4; nothing committed. Inspect: git -C $WT_DIR status"
[ "$staged" = "$want" ] || die "the staged set differs from the four ratification paths; nothing committed:\n$staged"
other="$(G status --porcelain --untracked-files=all | grep -v '^[AM]  ' || true)"
[ -z "$other" ] || say "note: unstaged or untracked leftovers are NOT committed:"$'\n'"$other"

# ------------------------------------------------------------------ 7. commit
hdr "7/7 commit"
MSG="$(mktemp)"
cat > "$MSG" <<EOF
$SUBJECT

Operator-approved eval-leak memory purge PURGE-EVAL-LEAK-MEMORIES-20260917
(epyc-orchestrator 41baad2b), ratified for the pinned production_best
checkpoint through scripts/operator/ratify_v10_episodic_repin_20260917.sh.
All pins were verified, and the section-5 consolidated receipt returned
RATIFIED.

The purge removed the 4 memories whose context carried the HumanEval/55
problem text from multitier_v10_20260810 (memories 63925 -> 63921, FAISS
ntotal 63925 -> 63921). episodic.db, embeddings.faiss and id_map.npy
changed, so every pin on them was false.

- multitier_v10_20260810/checkpoint_meta.json: the three file_sha256
  entries and memory_count were re-pinned, and an amendments entry was
  added. checkpoint_sha256 moved from a604276f to 3b457d98.
- ratify_multitier_baseline_v10_20260810.json: production_checkpoint.metadata
  was re-pinned to match, and an amendments entry was added. Nothing else in
  the receipt changed.
- The originals are in /mnt/raid0/llm/backups/v10-episodic-repin-20260917/;
  the pre-purge store is in /mnt/raid0/llm/backups/episodic-leak-20260917/.
- ratify_v10_episodic_repin_20260917.sh --verify supersedes
  ratify_checkpoint_prompt_leak_20260916.sh --verify as the v10 post-state
  check; it re-runs every check the older one made.

Operator-applied by $OPERATOR
EOF
G commit -q -F "$MSG" || { rm -f "$MSG"; die "git commit failed (hook?); the ratification is applied and staged in $WT_DIR. Re-run with --resume once resolved."; }
rm -f "$MSG"

hdr "DONE (not pushed)"
say "  worktree: $WT_DIR"
say "  branch:   $OP_BRANCH"
say "  commit:   $(G rev-parse HEAD)"
say "Hand these to a session to push and merge. This script never pushes."
