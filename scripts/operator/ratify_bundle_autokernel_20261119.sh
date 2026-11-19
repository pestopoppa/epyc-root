#!/bin/bash
# ratify_bundle_autokernel_20261119.sh -- ONE operator command for the three AutoKernel ratifications.
#
#   1. KLD thresholds     scripts/operator/ratify_ak_graph_kld_thresholds_20261118.sh      (research + root, pushes)
#   2. P-SERVE-1 (MEAS-2) scripts/operator/run_p_serve_1_ratify_20261119.sh                (root; the bundle pushes it)
#   3. Code budget        scripts/operator/ratify_ak_loop_code_budget_new_modules_20261119.sh (research + root, pushes)
#
# Review (default; runs each script's review/dry mode, writes and pushes nothing):
#     bash scripts/operator/ratify_bundle_autokernel_20261119.sh
# Sign (the OPERATOR runs this; ONE typed attest covers all three):
#     bash scripts/operator/ratify_bundle_autokernel_20261119.sh --operator '<your name>' --attest RATIFY-BUNDLE-AUTOKERNEL-20261119
# Verify origin/main (read-only):
#     bash scripts/operator/ratify_bundle_autokernel_20261119.sh --verify
#
# Order 1, 2, 3; stops at the first failure and names it. An item that reports ALREADY RATIFIED is skipped, so a
# re-run is safe. Each item's own gate is untouched: item 1 and 3 get their own --attest, item 2 keeps its typed
# RATIFY prompt (read from your terminal, after its diff). Ends with each script's --verify and one PASS/FAIL line each.
#
# SHARED-TARGET GUARD: items 1 and 2 both append to measurement/protocols/kernel-research.md and each pins that file's
# exact pre-state hash, so the second cannot apply after the first. While both are pending the bundle REFUSES
# before writing anything (exit 66). Test hooks (PS1_RATIFY_WRAPPER_TEST=1, ROOT, RES) are for scratch repos only.
set -euo pipefail
export PATH="/usr/bin:/bin:${PATH}"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${ROOT:-$(cd "$HERE/../.." && pwd)}"
[ -f "$ROOT/scripts/coordination/serialized_push.py" ] || ROOT=/mnt/raid0/llm/epyc-root
RES="${RES:-/mnt/raid0/llm/epyc-inference-research}"; export RES
GATE_ID="RATIFY-BUNDLE-AUTOKERNEL-20261119"
G1="RATIFY-AK-GRAPH-KLD-THRESHOLDS-20261118"
G3="RATIFY-AK-LOOP-CODE-BUDGET-NEW-MODULES-20261119"
S1="$HERE/ratify_ak_graph_kld_thresholds_20261118.sh"
S2W="$HERE/run_p_serve_1_ratify_20261119.sh"
S2="$HERE/ratify_p_serve_1_20261119.sh"
S3="$HERE/ratify_ak_loop_code_budget_new_modules_20261119.sh"
NAMES=("KLD thresholds" "P-SERVE-1" "code budget")
STAGE_PARENT="/mnt/raid0/llm/tmp"
LOCK_AGENT="operator-ratify-bundle-autokernel"
SYS_PY="/usr/bin/python3"
TEST_MODE="${PS1_RATIFY_WRAPPER_TEST:-0}"
S2_WT="/mnt/raid0/llm/worktrees/op-p-serve-1-ratify-20261119"; S2_BRANCH="op/p-serve-1-ratify-apply"
if [ "$TEST_MODE" = "1" ]; then S2_WT="${WT_DIR_OVERRIDE:-$S2_WT}"; S2_BRANCH="${OP_BRANCH_OVERRIDE:-$S2_BRANCH}"; fi

MODE="review"; OPERATOR=""; ATTEST=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --operator) [ "$#" -ge 2 ] || { echo "--operator needs a name" >&2; exit 64; }; OPERATOR="$2"; shift ;;
    --attest)   [ "$#" -ge 2 ] || { echo "--attest needs a value" >&2; exit 64; }; ATTEST="$2"; shift ;;
    --verify)   MODE="verify" ;;
    --review|--dry-run) MODE="review" ;;
    *) echo "usage: $0 [--verify | --operator <name> --attest $GATE_ID]" >&2; exit 64 ;;
  esac
  shift
done

say() { printf '%s\n' "$*"; }
die() { printf 'REFUSING: %s\n' "$*" >&2; exit 65; }
hdr() { printf '\n==== %s ====\n' "$*"; }
g()   { git -c safe.directory='*' -C "$@"; }

if [ -n "$OPERATOR" ] || [ -n "$ATTEST" ]; then MODE_REQ="apply"; else MODE_REQ="$MODE"; fi
[ "$MODE" != "verify" ] || MODE_REQ="verify"
if [ "$MODE_REQ" = "apply" ]; then
  [ -n "$OPERATOR" ] || die "--operator <name> is required with --attest. Nothing written."
  [ "$ATTEST" = "$GATE_ID" ] || die "--operator needs the typed confirmation --attest $GATE_ID. Nothing written."
  [ "$TEST_MODE" = "1" ] || [ -t 0 ] || die "run this from a terminal (item 2 reads its RATIFY confirmation from /dev/tty)."
  # shellcheck source=/dev/null
  source "$ROOT/scripts/operator/lib/ratify_operator.sh"
  ratify_require_operator "$OPERATOR"; OPERATOR="$RATIFY_OPERATOR"
  say "signer: $OPERATOR"
fi
for f in "$S1" "$S2W" "$S2" "$S3"; do
  [ -f "$f" ] || die "$f is missing. Run 'git -C $ROOT pull' (these scripts are on origin/main) and retry. Nothing written."
done

g "$ROOT" fetch -q origin main || die "cannot fetch origin main in $ROOT"
VWT="$(mktemp -d "$STAGE_PARENT/bundle-autokernel-ro.XXXXXX")"; VWT_ADDED=0
cleanup() {
  local rc=$?
  if [ "$VWT_ADDED" -eq 1 ]; then g "$ROOT" worktree remove "$VWT" >/dev/null 2>&1 || say "WARN: could not remove read-only worktree $VWT"; fi
  rmdir "$VWT" 2>/dev/null || true
  exit "$rc"
}
trap cleanup EXIT
fresh_ro_worktree() {  # (re)create the read-only worktree at current origin/main
  if [ "$VWT_ADDED" -eq 1 ]; then g "$ROOT" worktree remove "$VWT" >/dev/null 2>&1 || die "could not remove read-only worktree $VWT"; VWT_ADDED=0; fi
  rmdir "$VWT" 2>/dev/null || true
  g "$ROOT" fetch -q origin main || die "cannot fetch origin main in $ROOT"
  g "$ROOT" worktree add -q --detach "$VWT" origin/main || die "could not create read-only worktree"; VWT_ADDED=1
}

OUT=""; RC=0
capture() { set +e; OUT="$("$@" 2>&1)"; RC=$?; set -e; printf '%s\n' "$OUT"; }
is_already() { [ "$(printf '%s\n' "$OUT" | grep -c '^ALREADY RATIFIED' || true)" -ge 1 ]; }

STATE=("" "" "")   # already | pending | refused
review_item() {    # n
  case "$1" in
    1) hdr "review 1/3: ${NAMES[0]}"; capture bash "$S1" ;;
    2) hdr "review 2/3: ${NAMES[1]}"; fresh_ro_worktree; capture env ROOT="$VWT" bash "$S2" --review ;;
    3) hdr "review 3/3: ${NAMES[2]}"; capture bash "$S3" ;;
  esac
  if [ "$RC" -ne 0 ]; then STATE[$(($1-1))]="refused"
  elif is_already; then STATE[$(($1-1))]="already"
  else STATE[$(($1-1))]="pending"; fi
}

verify_all() {
  local fails=0 i
  hdr "verify (read-only, origin/main)"
  fresh_ro_worktree
  for i in 1 2 3; do
    case "$i" in
      1) capture bash "$S1" --verify ;;
      2) capture env ROOT="$VWT" bash "$S2" --verify ;;
      3) capture bash "$S3" --verify ;;
    esac
    if [ "$RC" -eq 0 ]; then say "PASS  item $i ${NAMES[$((i-1))]}"; else say "FAIL  item $i ${NAMES[$((i-1))]} (verify rc=$RC)"; fails=$((fails+1)); fi
  done
  return "$fails"
}

if [ "$MODE_REQ" = "verify" ]; then
  verify_all && { say "BUNDLE VERIFIED."; exit 0; } || { say "BUNDLE VERIFY FAILED."; exit 1; }
fi

# ---- review phase (also the preflight of --apply)
for i in 1 2 3; do review_item "$i"; done
hdr "review summary"
for i in 1 2 3; do say "  item $i ${NAMES[$((i-1))]}: ${STATE[$((i-1))]}"; done
if [ "${STATE[0]}" = "pending" ] && [ "${STATE[1]}" = "pending" ]; then
  say ""
  say "REFUSING (exit 66): items 1 and 2 both amend measurement/protocols/kernel-research.md and each pins its exact"
  say "pre-state hash (c086e4ee9f7b...), so the second cannot apply after the first. Nothing was written."
  say "Fix first: re-pin one script to the other's post-state (apply P-SERVE-1 first, then accept its kernel-research.md"
  say "post-state c5bd00d760bb... as item 1's pre-state), re-derive the receipts, then re-run."
  exit 66
fi
for i in 1 2 3; do
  [ "${STATE[$((i-1))]}" != "refused" ] || { say "STOP: review of item $i (${NAMES[$((i-1))]}) refused; read its output above. Nothing was written."; exit 1; }
done
if [ "$MODE_REQ" != "apply" ]; then
  say ""
  say "REVIEW COMPLETE: nothing written, committed or pushed. Sign all three with ONE command:"
  say "  bash $HERE/ratify_bundle_autokernel_20261119.sh --operator '<your name>' --attest $GATE_ID"
  exit 0
fi

# ---- push helper for item 2 (the P-SERVE-1 script commits on a branch and never pushes)
push_s2_branch() {
  local tokdir tok prc=0 PUSHER="$ROOT/scripts/coordination/serialized_push.py"
  g "$ROOT" fetch -q origin main || die "cannot fetch origin main"
  if ! g "$S2_WT" merge-base --is-ancestor origin/main HEAD; then
    say "origin/main moved; rebasing $S2_BRANCH onto it (never amend)"
    g "$S2_WT" rebase -q origin/main || die "rebase of $S2_BRANCH failed; resolve by hand in $S2_WT"
  fi
  tokdir="$(mktemp -d "$STAGE_PARENT/bundle-push-token.XXXXXX")"; chmod 700 "$tokdir"; tok="$tokdir/lease.token"
  "$SYS_PY" "$PUSHER" --agent "$LOCK_AGENT" --repo "$ROOT" --lock-name push --acquire --token-file "$tok" >/dev/null \
    || die "could not take the push lock for $ROOT; re-run (item 2's commit is kept on $S2_BRANCH)."
  AGENT_ID="$LOCK_AGENT" EPYC_PUSH_LOCK_HOLDER="$LOCK_AGENT" g "$S2_WT" push -q origin HEAD:refs/heads/main || prc=$?
  "$SYS_PY" "$PUSHER" --agent "$LOCK_AGENT" --repo "$ROOT" --lock-name push --release --token-file "$tok" >/dev/null \
    || say "WARN: push lock release failed"
  rm -f "$tok"; rmdir "$tokdir" 2>/dev/null || true
  [ "$prc" -eq 0 ] || die "push of $S2_BRANCH rejected (rc=$prc). Re-run; the commit is kept and will be re-pushed."
  g "$ROOT" fetch -q origin main
  g "$ROOT" merge-base --is-ancestor "$(g "$S2_WT" rev-parse HEAD)" origin/main || die "item 2 commit is not on origin/main after the push"
  g "$ROOT" worktree remove "$S2_WT" >/dev/null 2>&1 || say "WARN: could not remove $S2_WT (plain remove)"
  g "$ROOT" branch -d "$S2_BRANCH" >/dev/null 2>&1 || say "WARN: branch $S2_BRANCH not deleted (inspect by hand)"
}

# ---- apply phase
for i in 1 2 3; do
  if [ "${STATE[$((i-1))]}" = "already" ]; then hdr "apply $i/3: ${NAMES[$((i-1))]}"; say "SKIP: ALREADY RATIFIED"; continue; fi
  hdr "apply $i/3: ${NAMES[$((i-1))]}"
  case "$i" in
    1) RATIFY_OPERATOR="$OPERATOR" bash "$S1" --apply --attest "$G1" || { say "FAILED at item 1 (${NAMES[0]}). Items after it were not run."; exit 1; } ;;
    2) a=(--operator "$OPERATOR")
       [ ! -e "$S2_WT" ] || a+=(--resume)
       [ "$TEST_MODE" != "1" ] || a+=(--yes)
       bash "$S2W" "${a[@]}" || { say "FAILED at item 2 (${NAMES[1]}). Item 3 was not run."; exit 1; }
       push_s2_branch ;;
    3) RATIFY_OPERATOR="$OPERATOR" bash "$S3" --apply --attest "$G3" || { say "FAILED at item 3 (${NAMES[2]})."; exit 1; } ;;
  esac
done

if verify_all; then say "BUNDLE RATIFIED AND VERIFIED by $OPERATOR."; exit 0; fi
say "BUNDLE APPLIED BUT VERIFY FAILED; read the FAIL lines above."; exit 1
