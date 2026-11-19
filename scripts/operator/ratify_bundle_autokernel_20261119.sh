#!/bin/bash
# ratify_bundle_autokernel_20261119.sh -- ONE operator command for the three AutoKernel ratifications.
#
#   1. P-SERVE-1 (MEAS-2) scripts/operator/run_p_serve_1_ratify_20261119.sh                (root; the bundle pushes it)
#   2. KLD thresholds     scripts/operator/ratify_ak_graph_kld_thresholds_20261118.sh      (research + root, pushes)
#   3. Code budget        scripts/operator/ratify_ak_loop_code_budget_new_modules_20261119.sh (research + root, pushes)
#
# Pull-free single command (fetch, detached worktree on origin/main, run this, remove the worktree):
#     git -C /mnt/raid0/llm/epyc-root fetch -q origin main && git -C /mnt/raid0/llm/epyc-root show origin/main:scripts/operator/run_ratify_bundle_autokernel_20261119.sh | bash -s -- --operator '<your name>' --attest RATIFY-BUNDLE-AUTOKERNEL-20261119
# Review (default; runs each script's review/dry mode, writes and pushes nothing): same line without --operator/--attest.
# Verify origin/main (read-only): same line with --verify.
#
# Order 1, 2, 3; stops at the first failure and names it. An item that reports ALREADY RATIFIED is skipped, so a
# re-run is safe. Items 2 and 3 get their own --attest from the bundle's; item 1 keeps its typed RATIFY prompt (read
# from your terminal, after its diff). Ends with each script's --verify and one PASS/FAIL line each.
#
# ORDER: items 1 and 2 both append to measurement/protocols/kernel-research.md; item 2 is pinned to item 1's post-state,
# so its review is deferred until item 1 has landed (state "after-1") and re-run just before it applies.
set -euo pipefail
export PATH="/usr/bin:/bin:${PATH}"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${ROOT:-$(cd "$HERE/../.." && pwd)}"
[ -f "$ROOT/scripts/coordination/serialized_push.py" ] || ROOT=/mnt/raid0/llm/epyc-root
RES="${RES:-/mnt/raid0/llm/epyc-inference-research}"; export RES
GATE_ID="RATIFY-BUNDLE-AUTOKERNEL-20261119"
G2="RATIFY-AK-GRAPH-KLD-THRESHOLDS-20261118"
G3="RATIFY-AK-LOOP-CODE-BUDGET-NEW-MODULES-20261119"
SK="$HERE/ratify_ak_graph_kld_thresholds_20261118.sh"
S1W="$HERE/run_p_serve_1_ratify_20261119.sh"
S1="$HERE/ratify_p_serve_1_20261119.sh"
S2="$SK"
S3="$HERE/ratify_ak_loop_code_budget_new_modules_20261119.sh"
NAMES=("P-SERVE-1" "KLD thresholds" "code budget")
STAGE_PARENT="/mnt/raid0/llm/tmp"
LOCK_AGENT="operator-ratify-bundle-autokernel"
SYS_PY="/usr/bin/python3"
TEST_MODE="${PS1_RATIFY_WRAPPER_TEST:-0}"
S1_WT="/mnt/raid0/llm/worktrees/op-p-serve-1-ratify-20261119"; S1_BRANCH="op/p-serve-1-ratify-apply"
if [ "$TEST_MODE" = "1" ]; then S1_WT="${WT_DIR_OVERRIDE:-$S1_WT}"; S1_BRANCH="${OP_BRANCH_OVERRIDE:-$S1_BRANCH}"; fi

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
  [ "$TEST_MODE" = "1" ] || { : </dev/tty; } 2>/dev/null || die "no terminal (item 1 reads its RATIFY confirmation from /dev/tty)."
  # shellcheck source=/dev/null
  source "$ROOT/scripts/operator/lib/ratify_operator.sh"
  ratify_require_operator "$OPERATOR"; OPERATOR="$RATIFY_OPERATOR"
  say "signer: $OPERATOR"
fi
for f in "$S1" "$S1W" "$S2" "$S3"; do
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
    1) hdr "review 1/3: ${NAMES[0]}"; fresh_ro_worktree; capture env ROOT="$VWT" bash "$S1" --review ;;
    2) hdr "review 2/3: ${NAMES[1]}"; capture bash "$S2" ;;
    3) hdr "review 3/3: ${NAMES[2]}"; capture bash "$S3" ;;
  esac
  if [ "$RC" -ne 0 ]; then
    if [ "$1" = "2" ] && [ "$(printf '%s\n' "$OUT" | grep -c 'apply run_p_serve_1_ratify_20261119.sh first' || true)" -ge 1 ]; then STATE[1]="after-1"
    else STATE[$(($1-1))]="refused"; fi
  elif is_already; then STATE[$(($1-1))]="already"
  else STATE[$(($1-1))]="pending"; fi
}

verify_all() {
  local fails=0 i
  hdr "verify (read-only, origin/main)"
  fresh_ro_worktree
  for i in 1 2 3; do
    case "$i" in
      1) capture env ROOT="$VWT" bash "$S1" --verify ;;
      2) capture bash "$S2" --verify ;;
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
if [ "${STATE[1]}" = "after-1" ] && [ "${STATE[0]}" != "pending" ]; then
  say "STOP: item 2 (${NAMES[1]}) needs item 1 (${NAMES[0]}) on origin/main first, but item 1 is ${STATE[0]}. Nothing was written."; exit 1
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

# ---- push helper for item 1 (the P-SERVE-1 script commits on a branch and never pushes)
push_s1_branch() {
  local tokdir tok prc=0 PUSHER="$ROOT/scripts/coordination/serialized_push.py"
  g "$ROOT" fetch -q origin main || die "cannot fetch origin main"
  if ! g "$S1_WT" merge-base --is-ancestor origin/main HEAD; then
    say "origin/main moved; rebasing $S1_BRANCH onto it (never amend)"
    g "$S1_WT" rebase -q origin/main || die "rebase of $S1_BRANCH failed; resolve by hand in $S1_WT"
  fi
  tokdir="$(mktemp -d "$STAGE_PARENT/bundle-push-token.XXXXXX")"; chmod 700 "$tokdir"; tok="$tokdir/lease.token"
  "$SYS_PY" "$PUSHER" --agent "$LOCK_AGENT" --repo "$ROOT" --lock-name push --acquire --token-file "$tok" >/dev/null \
    || die "could not take the push lock for $ROOT; re-run (item 1's commit is kept on $S1_BRANCH)."
  AGENT_ID="$LOCK_AGENT" EPYC_PUSH_LOCK_HOLDER="$LOCK_AGENT" g "$S1_WT" push -q origin HEAD:refs/heads/main || prc=$?
  "$SYS_PY" "$PUSHER" --agent "$LOCK_AGENT" --repo "$ROOT" --lock-name push --release --token-file "$tok" >/dev/null \
    || say "WARN: push lock release failed"
  rm -f "$tok"; rmdir "$tokdir" 2>/dev/null || true
  [ "$prc" -eq 0 ] || die "push of $S1_BRANCH rejected (rc=$prc). Re-run; the commit is kept and will be re-pushed."
  g "$ROOT" fetch -q origin main
  g "$ROOT" merge-base --is-ancestor "$(g "$S1_WT" rev-parse HEAD)" origin/main || die "item 1 commit is not on origin/main after the push"
  g "$ROOT" worktree remove "$S1_WT" >/dev/null 2>&1 || say "WARN: could not remove $S1_WT (plain remove)"
  g "$ROOT" branch -d "$S1_BRANCH" >/dev/null 2>&1 || say "WARN: branch $S1_BRANCH not deleted (inspect by hand)"
}

# ---- apply phase
for i in 1 2 3; do
  hdr "apply $i/3: ${NAMES[$((i-1))]}"
  if [ "$i" = "2" ] && [ "${STATE[1]}" = "after-1" ]; then
    say "item 1 has landed; re-reviewing item 2 against the new origin/main"
    review_item 2
    [ "${STATE[1]}" != "refused" ] && [ "${STATE[1]}" != "after-1" ] || { say "FAILED at item 2 (${NAMES[1]}): its review refuses after item 1 landed. Item 3 was not run."; exit 1; }
  fi
  if [ "${STATE[$((i-1))]}" = "already" ]; then say "SKIP: ALREADY RATIFIED"; continue; fi
  case "$i" in
    1) a=(--operator "$OPERATOR")
       [ ! -e "$S1_WT" ] || a+=(--resume)
       [ "$TEST_MODE" != "1" ] || a+=(--yes)
       bash "$S1W" "${a[@]}" || { say "FAILED at item 1 (${NAMES[0]}). Items after it were not run."; exit 1; }
       push_s1_branch ;;
    2) RATIFY_OPERATOR="$OPERATOR" bash "$S2" --apply --attest "$G2" || { say "FAILED at item 2 (${NAMES[1]}). Item 3 was not run."; exit 1; } ;;
    3) RATIFY_OPERATOR="$OPERATOR" bash "$S3" --apply --attest "$G3" || { say "FAILED at item 3 (${NAMES[2]})."; exit 1; } ;;
  esac
done

if verify_all; then say "BUNDLE RATIFIED AND VERIFIED by $OPERATOR."; exit 0; fi
say "BUNDLE APPLIED BUT VERIFY FAILED; read the FAIL lines above."; exit 1
