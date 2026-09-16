#!/bin/bash
# run_pcal_ratify_20260916.sh — the operator's single command for the P-CAL speculative-decoding
# contamination ratification (operator decision 2026-09-16, option a).
#
#   bash /mnt/raid0/llm/epyc-root/scripts/operator/run_pcal_ratify_20260916.sh --operator <your-name>
#
# It runs from any directory, as long as /mnt/raid0/llm/epyc-root is available. Steps:
#   1. git fetch origin in /mnt/raid0/llm/epyc-root
#   2. create worktree /mnt/raid0/llm/worktrees/op-pcal-ratify-20260916 on a NEW branch
#      op/pcal-ratify-apply from origin/main. If the worktree already exists, it refuses unless
#      --resume is given.
#   3. show the ratify script's dry-run (preflight plus the full amendment diff)
#   4. ask you to type RATIFY, read from your terminal
#   5. run the ratify script with --apply and RATIFY_OPERATOR=<your-name>
#   6. stage EXACTLY the five ratification paths, show the stat, and refuse unless it is those 5 files
#   7. commit with the RATIFIED message and an "Operator-applied by <your-name>" trailer
#   8. STOP, printing the branch and commit SHA. A session pushes and merges it.
#
# It never pushes. It never touches the /workspace working tree: every write lands in the new
# worktree, and the only other effects are refs and objects in the shared .git (fetch, a new
# worktree, a new branch). The trust-boundary edit itself is made by
# scripts/operator/ratify_pcal_specdec_contamination_20260916.sh, which pins every hash and rolls
# back on any failure.
#
# Options:
#   --operator <name>  required; recorded in the receipts and the commit trailer
#   --resume           reuse an existing op-pcal-ratify worktree (after an interrupted run)
#
# Test hooks (NOT for the operator): only when PCAL_RATIFY_WRAPPER_TEST=1 are these honored:
#   --yes, which skips the tty prompt, and the env overrides EPYC_ROOT, WT_DIR and OP_BRANCH.
# Without that variable, --yes is refused and the paths are fixed.
set -euo pipefail

TEST_MODE="${PCAL_RATIFY_WRAPPER_TEST:-0}"
EPYC_ROOT="/mnt/raid0/llm/epyc-root"
WT_DIR="/mnt/raid0/llm/worktrees/op-pcal-ratify-20260916"
OP_BRANCH="op/pcal-ratify-apply"
if [ "$TEST_MODE" = "1" ]; then
  EPYC_ROOT="${EPYC_ROOT_OVERRIDE:-$EPYC_ROOT}"
  WT_DIR="${WT_DIR_OVERRIDE:-$WT_DIR}"
  OP_BRANCH="${OP_BRANCH_OVERRIDE:-$OP_BRANCH}"
fi
RATIFY_REL="scripts/operator/ratify_pcal_specdec_contamination_20260916.sh"
COMMIT_PATHS=(
  "MEASUREMENT.md"
  "measurement/protocols/quality-eval.md"
  "artifacts/operator/ratify_pcal_specdec_contamination_20260916.json"
  "artifacts/operator/receipts/RATIFY-P-CAL-SPECDEC-20260916.json"
  "artifacts/operator/ratify_pcal_specdec_contamination_20260916.receipt.json"
)
SUBJECT="RATIFIED: P-CAL calibration baselines contaminated by speculative decoding; decision uses suspended pending EV-CONF-2 (2026-09-16, option a)"

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
    -h|--help)  sed -n '2,31p' "$0"; exit 0 ;;
    *) die "unknown argument: $1 (usage: $0 --operator <name> [--resume])" ;;
  esac
done
[ -n "$OPERATOR" ] || die "--operator <name> is required (usage: $0 --operator <name> [--resume])"
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

# Already committed? (resume after step 7)
if G log -1 --format=%s | grep -qF "$SUBJECT"; then
  hdr "already done"
  say "HEAD already carries the ratification commit."
  say "  branch: $OP_BRANCH"
  say "  commit: $(G rev-parse HEAD)"
  say "Nothing to do. Hand the branch to a session to push and merge."
  exit 0
fi

[ -f "$WT_DIR/$RATIFY_REL" ] || die "$RATIFY_REL is not on origin/main yet: the prepared branch (sub/pcal-ratify-20260916) must be merged first"

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
    [ -r /dev/tty ] || die "no terminal to read the confirmation from; run this interactively"
    printf 'The diff above will be applied to MEASUREMENT.md and measurement/protocols/quality-eval.md\n'
    printf 'in %s, as operator "%s".\nType RATIFY to apply: ' "$WT_DIR" "$OPERATOR"
    IFS= read -r answer < /dev/tty || die "could not read from the terminal"
    [ "$answer" = "RATIFY" ] || die "confirmation was '$answer', not RATIFY. Nothing applied; the worktree is left for --resume."
  fi

  # ---------------------------------------------------------------- 5. apply
  hdr "5/7 apply"
  RATIFY_OPERATOR="$OPERATOR" ROOT="$WT_DIR" bash "$WT_DIR/$RATIFY_REL" --apply \
    || die "ratify --apply failed (it rolls itself back); read the output above"
else
  hdr "4-5/7 skipped: the amendment is already applied in this worktree (resume)"
fi

# ------------------------------------------------------------------ 6. stage
hdr "6/7 stage exactly the five ratification paths"
if [ -n "$(G diff --cached --name-only)" ]; then
  staged_pre="$(G diff --cached --name-only | sort)"
  want="$(printf '%s\n' "${COMMIT_PATHS[@]}" | sort)"
  [ "$staged_pre" = "$want" ] || die "the index already holds other staged changes:\n$staged_pre"
fi
G add -- "${COMMIT_PATHS[@]}"
G diff --cached --stat
staged="$(G diff --cached --name-only | sort)"
want="$(printf '%s\n' "${COMMIT_PATHS[@]}" | sort)"
n="$(printf '%s\n' "$staged" | sed '/^$/d' | wc -l | tr -d ' ')"
[ "$n" = "5" ] || die "staged $n files, expected exactly 5; nothing committed. Inspect: git -C $WT_DIR status"
[ "$staged" = "$want" ] || die "the staged set differs from the five ratification paths; nothing committed:\n$staged"
other="$(G status --porcelain --untracked-files=all | grep -v '^[AM]  ' || true)"
[ -z "$other" ] || say "note: unstaged or untracked leftovers are NOT committed:"$'\n'"$other"

# ------------------------------------------------------------------ 7. commit
hdr "7/7 commit"
MSG="$(mktemp)"
cat > "$MSG" <<EOF
$SUBJECT

Operator decision 2026-09-16, option (a), applied by operator ratification
through scripts/operator/ratify_pcal_specdec_contamination_20260916.sh. All
pins were verified, and the section-5 consolidated receipt returned RATIFIED.

Annex Q, P-CAL:
- The E7c math calibration (ECE 0.2114/0.2199, AUROC 0.4013/0.4114) is
  CONTAMINATED and INVALID. The rows are saturated: 1528/1684 and 1485/1628.
- The EV-4c code calibration (ECE 0.2532/0.3216, AUROC 0.6337/0.5751) is
  CONTAMINATED by an unmeasured amount and is demoted-to-prior.
- RLVR code calibration and EV-5/EV-7 verifier promotion are SUSPENDED
  pending EV-CONF-2.
- Standing rule: confidence metrics are admissible only from spec-off runs,
  or with placeholder tokens excluded.
- No historical number is edited.

MEASUREMENT.md: the section-2 status cell, plus a CHANGELOG entry.

Evidence: epyc-orchestrator b98dee18 and f2e9ee07, merged 2026-09-16 via
d8b915ee/88a2902d.

Operator-applied by $OPERATOR
EOF
G commit -q -F "$MSG" || { rm -f "$MSG"; die "git commit failed (hook?); the amendment is applied and staged in $WT_DIR. Re-run with --resume once resolved."; }
rm -f "$MSG"

hdr "DONE (not pushed)"
say "  worktree: $WT_DIR"
say "  branch:   $OP_BRANCH"
say "  commit:   $(G rev-parse HEAD)"
say "Hand these to a session to push and merge. This script never pushes."
