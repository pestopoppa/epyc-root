#!/bin/bash
# ratify_ws58_lessons_20261027.sh — ONE operator signature over two operator-approved lessons added to the
# human-only file agents/shared/OPERATING_CONSTRAINTS.md (trust boundary, invariant 15; agent writes are hook-blocked).
#
#   1. "Operator Decision Requests": a missing answer is UNANSWERED, not DECLINED; re-ask with the decision tool.
#   2. "Inference and Benchmarks":   an exit code is not a result; post-measurement analysis before reporting.
#   Both approved by the operator 2026-10-27 through the decision tool. Each is appended at the END of its section.
#
#   Review / dry run (default; full trial apply + receipt in a throwaway worktree, pushes nothing, keeps nothing):
#     bash scripts/operator/ratify_ws58_lessons_20261027.sh
#   Sign, commit and push to main (the OPERATOR runs this, from a terminal):
#     RATIFY_OPERATOR='<your name>' bash scripts/operator/ratify_ws58_lessons_20261027.sh --apply --attest RATIFY-WS58-LESSONS-20261027
#   Same, but leave the signed commit unpushed in the stage worktree:   ... --apply --attest ... --no-push
#   Verify origin/main (read-only):
#     bash scripts/operator/ratify_ws58_lessons_20261027.sh --verify
#
# ratify-targets: agents/shared/OPERATING_CONSTRAINTS.md
#
# Also emits the MEASUREMENT.md section-5 consolidated receipt (the checker treats agents/shared/*.md as trust boundary).
# SAFETY: stages a detached scratch worktree of origin/main; nothing touches your checkout. Refuses unless the target's
# sha256 on the base equals the PRE pin (or already equals the POST pin = ALREADY RATIFIED, exit 0). Prints the exact
# unified diff before anything is committed. Touches no process.
# ROLLBACK: `git revert <ratify commit>` on a fresh origin/main worktree, pushed through serialized_push.py.
set -euo pipefail
export PATH="/usr/bin:/bin:${PATH}"

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
ROOT="${ROOT:-$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd)}"
SCRIPT_REL="scripts/operator/ratify_ws58_lessons_20261027.sh"
STAGE_PARENT="/mnt/raid0/llm/tmp"
LOCK_AGENT="operator-ratify-ws58-lessons"
SYS_PY="/usr/bin/python3"
GATE_ID="RATIFY-WS58-LESSONS-20261027"
TARGET="agents/shared/OPERATING_CONSTRAINTS.md"
PRE_SHA="7e453c7b115b6f3f6b50623f2b6a2b2144a7210face10e8076cc7a7cb93cc6a8"
POST_SHA="1cfcbdc9234cecded69e9439ed562e4c5d86504d99b6fe33589087beda9df8ce"
CHECKER_REL="scripts/validate/check_ratification_receipts.py"
RECEIPT_REL="artifacts/operator/ratify_ws58_lessons_20261027.json"
INDEX_REL="artifacts/operator/receipts/$GATE_ID.json"
CONSOLIDATED_REL="artifacts/operator/ratify_ws58_lessons_20261027.receipt.json"
PROTOCOL_ID="OPERATING-CONSTRAINTS-UNANSWERED-AND-POST-MEASUREMENT"
ANCHOR1="A missing answer is *unanswered*, not *declined*"
ANCHOR2="An exit code is not a result."

MODE="review"; ATTEST=""; DO_PUSH=1
while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run|--review) MODE="review" ;;
    --apply)   MODE="apply" ;;
    --verify)  MODE="verify" ;;
    --no-push) DO_PUSH=0 ;;
    --attest)  shift; ATTEST="${1:-}" ;;
    *) echo "usage: $0 [--dry-run | --verify | --apply --attest $GATE_ID [--no-push]]" >&2; exit 64 ;;
  esac
  shift
done

say() { printf '%s\n' "$*"; }
die() { printf 'REFUSING: %s\n' "$*" >&2; exit 65; }
g() { git -c safe.directory='*' -C "$@"; }
sha() { sha256sum -- "$1" | awk '{print $1}'; }
ok() { printf '  ok    %s\n' "$*"; }
for tool in git sha256sum awk diff "$SYS_PY"; do command -v "$tool" >/dev/null || die "$tool not available"; done
[ -f "$ROOT/scripts/coordination/serialized_push.py" ] || die "ROOT=$ROOT is not an epyc-root checkout"
PUSHER="$ROOT/scripts/coordination/serialized_push.py"

if [ "$MODE" = "apply" ]; then
  [ "$ATTEST" = "$GATE_ID" ] || die "--apply needs the typed confirmation --attest $GATE_ID. Nothing written."
  [ -z "${BASE_REF:-}" ] || [ "${BASE_REF}" = "origin/main" ] || die "--apply always stages from origin/main; unset BASE_REF."
  # shellcheck source=/dev/null
  source "$ROOT/scripts/operator/lib/ratify_operator.sh"
  ratify_require_operator
  say "signer: $RATIFY_OPERATOR"
fi

g "$ROOT" fetch -q origin main || die "cannot fetch origin main in $ROOT"
BASE="${BASE_REF:-origin/main}"
BASE_SHA="$(g "$ROOT" rev-parse --verify "$BASE^{commit}")" || die "cannot resolve $BASE"
say "== base $BASE = $BASE_SHA =="

if [ "$MODE" = "verify" ]; then
  have="$(g "$ROOT" show "origin/main:$TARGET" | sha256sum | awk '{print $1}')"
  [ "$have" = "$POST_SHA" ] || { say "  FAIL  $TARGET is ${have:0:12}, post-state is ${POST_SHA:0:12}"; exit 1; }
  ok "$TARGET at post-state ${POST_SHA:0:12}"
  for f in "$RECEIPT_REL" "$CONSOLIDATED_REL" "$INDEX_REL"; do
    if g "$ROOT" cat-file -e "origin/main:$f" 2>/dev/null; then ok "$f on origin/main"; else say "  FAIL  $f not on origin/main"; exit 1; fi
  done
  say "VERIFIED: $GATE_ID is on origin/main, pinned and receipted."; exit 0
fi

# ---- stage
STAGE="$(mktemp -d "$STAGE_PARENT/ratify-ws58-lessons.XXXXXX")"
WT="$STAGE/root"; WT_ADDED=0; KEEP_STAGE=0
cleanup() {
  local rc=$?
  if [ "$WT_ADDED" -eq 1 ] && [ "$KEEP_STAGE" -eq 0 ]; then
    g "$ROOT" worktree remove --force "$WT" >/dev/null 2>&1 || say "WARN: could not remove stage worktree $WT"
  fi
  if [ "$KEEP_STAGE" -eq 0 ]; then rm -f "$STAGE"/pre.json "$STAGE"/xform.py "$STAGE"/before.md "$STAGE"/after.md; rmdir "$STAGE" 2>/dev/null || true; fi
  exit "$rc"
}
trap cleanup EXIT
g "$ROOT" worktree add -q --detach "$WT" "$BASE_SHA" || die "could not stage a worktree of $BASE"
WT_ADDED=1
ok "staged detached worktree $WT at ${BASE_SHA:0:12}"

# ---- preflight
say "== preflight (mode=$MODE) =="
have="$(sha "$WT/$TARGET")"
if [ "$have" = "$POST_SHA" ] && [ -f "$WT/$INDEX_REL" ]; then
  say "ALREADY RATIFIED: $TARGET is at the post-state pin and the receipt index is present. Nothing to do."; exit 0
fi
[ ! -e "$WT/$INDEX_REL" ] || die "receipt index exists but $TARGET is not at the post-state pin (half state). Not touching it."
if grep -qF -- "$ANCHOR1" "$WT/$TARGET" || grep -qF -- "$ANCHOR2" "$WT/$TARGET"; then
  die "a lesson is already present without a receipt (partial or manual state). Reconcile by hand; not touching it."
fi
[ "$have" = "$PRE_SHA" ] || die "$TARGET on $BASE is ${have:0:12}, expected pre-state ${PRE_SHA:0:12}. The base changed since this script was prepared; re-derive, do not overwrite."
ok "$TARGET at pre-state ${PRE_SHA:0:12}"
[ ! -e "$WT/$RECEIPT_REL" ] || die "$RECEIPT_REL already exists"
if "$SYS_PY" "$WT/$CHECKER_REL" --repo-root "$WT" >/dev/null 2>&1; then ok "receipt checker exits 0 before the amendment"
else die "receipt checker does not exit 0 before the amendment"; fi

# ---- apply (in the stage only) and show exactly what changes
XFORM="$STAGE/xform.py"
cat >"$XFORM" <<'PYEOF'
import sys,re
p=sys.argv[1]
t=open(p,encoding="utf-8").read()
A="A missing answer is *unanswered*, not *declined*: on the remote app the AskUserQuestion UI can vanish without operator action. Re-ask the same question with the decision tool, never as prose; only that item pauses. (origin: 2026-10-26/27, ws58 calendar freezes)"
B="An exit code is not a result. Every measurement row that ends gets a post-measurement analysis (verdict vs predeclared rule and direction, classification, owning-handoff result bullet, belief/wiki candidates) before it is reported, and reports state what each result means. Checklist: `.claude/skills/inference-backlog-scheduling/references/post-measurement-analysis.md`. (origin: 2026-10-27)"
def add(t,head,txt):
    if txt in t: return t
    i=t.index("\n"+head+"\n")+1
    m=re.compile(r"^## ",re.M).search(t,i+len(head)+1)
    j=m.start() if m else len(t)
    k=len(t[:j].rstrip("\n"))
    return t[:k]+"\n\n"+txt+t[k:]
t=add(t,"## Operator Decision Requests",A)
t=add(t,"## Inference and Benchmarks",B)
sys.stdout.write(t)
PYEOF
cp "$WT/$TARGET" "$STAGE/before.md"
"$SYS_PY" "$WT/scripts/operator/ratification_receipt.py" capture --repo-root "$WT" --state "$TARGET" --out "$STAGE/pre.json" \
  || die "could not snapshot the pre-amendment state"
"$SYS_PY" "$XFORM" "$STAGE/before.md" >"$STAGE/after.md" || die "transform failed"
cp "$STAGE/after.md" "$WT/$TARGET"
say "== exact change to $TARGET =="
diff -u --label "a/$TARGET" --label "b/$TARGET" "$STAGE/before.md" "$WT/$TARGET" || true
removed="$(diff "$STAGE/before.md" "$WT/$TARGET" | grep -c '^<' || true)"
[ "$removed" -eq 0 ] || die "postflight: $removed lines removed; additions only expected."
[ "$(grep -cF -- "$ANCHOR1" "$WT/$TARGET")" -eq 1 ] && [ "$(grep -cF -- "$ANCHOR2" "$WT/$TARGET")" -eq 1 ] || die "postflight: each lesson must occur exactly once."
[ "$(sha "$WT/$TARGET")" = "$POST_SHA" ] || die "postflight: post-state sha $(sha "$WT/$TARGET") != pin ${POST_SHA}."
ok "additions only (0 lines removed); each lesson once; post-state ${POST_SHA:0:12}"

# ---- receipts
say "== MEASUREMENT.md section-5 consolidated receipt =="
receipt_rc=0
"$SYS_PY" "$WT/scripts/operator/ratification_receipt.py" emit \
  --repo-root "$WT" \
  --pre "$STAGE/pre.json" \
  --protocol-id "$PROTOCOL_ID" \
  --anchor "$ANCHOR1" \
  --anchor "$ANCHOR2" \
  --ratification-id "$GATE_ID" \
  --script "$SCRIPT_PATH" \
  --operator "${RATIFY_OPERATOR:-DRY-RUN-PREVIEW}" \
  --no-evidence-reason "workflow doctrine, not a measured claim; origin is the 2026-10-26/27 workspace-58 calendar freezes and the operator's 2026-10-27 decision-tool approvals" \
  --validation "python3 $CHECKER_REL --repo-root ." \
  --validation "test \"\$(sha256sum $TARGET | cut -d' ' -f1)\" = $POST_SHA" \
  --out "$WT/$CONSOLIDATED_REL" || receipt_rc=$?
if [ "$receipt_rc" -ne 0 ]; then
  [ ! -f "$WT/$CONSOLIDATED_REL" ] || { cp "$WT/$CONSOLIDATED_REL" "$STAGE/refused.receipt.json"; KEEP_STAGE=1; say "  refused receipt kept: $STAGE/refused.receipt.json"; }
  die "consolidated receipt returned $receipt_rc (1 REFUSED, 2 COULD-NOT-CHECK). Nothing committed or pushed."
fi
ok "consolidated receipt: $CONSOLIDATED_REL"

RATIFIED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
OPERATOR_NAME="${RATIFY_OPERATOR:-DRY-RUN-PREVIEW}"
WT="$WT" RECEIPT_REL="$RECEIPT_REL" INDEX_REL="$INDEX_REL" CONSOLIDATED_REL="$CONSOLIDATED_REL" GATE_ID="$GATE_ID" TARGET="$TARGET" PRE="$PRE_SHA" POST="$POST_SHA" \
OPERATOR="$OPERATOR_NAME" TS="$RATIFIED_AT" BASE_SHA="$BASE_SHA" SCRIPT_SHA="$(sha "$SCRIPT_PATH")" SCRIPT_REL="$SCRIPT_REL" \
"$SYS_PY" - <<'PYEOF' || die "could not write the receipts. Nothing committed or pushed."
import json, os
e = os.environ
doc = {
    "schema": "epyc.operating_constraints_amendment.v1",
    "gate_id": e["GATE_ID"],
    "status": "ratified",
    "ratified_at": e["TS"],
    "operator": e["OPERATOR"],
    "signature_channel": "operator-run script (--attest typed confirmation)",
    "operator_decisions": {
        "1": "2026-10-27 (decision tool): Operator Decision Requests: a missing answer is unanswered, not declined; re-ask with the decision tool, never as prose; only that item pauses",
        "2": "2026-10-27 (decision tool): Inference and Benchmarks: an exit code is not a result; post-measurement analysis before reporting",
    },
    "origin": "2026-10-26/27 workspace-58 calendar freezes (1); 2026-10-27 (2)",
    "base_origin_main": e["BASE_SHA"],
    "consolidated_receipt": e["CONSOLIDATED_REL"],
    "state": {e["TARGET"]: {"sha256_before": e["PRE"], "sha256_after": e["POST"]}},
    "applied_by": e["SCRIPT_REL"],
    "ratify_script_sha256": e["SCRIPT_SHA"],
    "processes_touched": [],
}
wt = e["WT"]
with open(os.path.join(wt, e["RECEIPT_REL"]), "x", encoding="utf-8") as fh:
    json.dump(doc, fh, indent=2, ensure_ascii=False); fh.write("\n")
os.makedirs(os.path.dirname(os.path.join(wt, e["INDEX_REL"])), exist_ok=True)
with open(os.path.join(wt, e["INDEX_REL"]), "x", encoding="utf-8") as fh:
    json.dump({"gate_id": e["GATE_ID"], "indexed_by": "ratify", "receipt": e["RECEIPT_REL"],
               "schema_version": "session_bus.receipt_index.v1", "status": "ratified"}, fh, indent=2, sort_keys=True)
    fh.write("\n"); fh.flush(); os.fsync(fh.fileno())
print(f"  ok    decision receipt {e['RECEIPT_REL']}")
print(f"  ok    keyed index      {e['INDEX_REL']}")
PYEOF
if "$SYS_PY" "$WT/$CHECKER_REL" --repo-root "$WT" >/dev/null 2>&1; then ok "receipt checker exits 0 after the amendment"
else die "receipt checker fails after the amendment. Nothing committed or pushed."; fi

COMMIT_PATHS=("$TARGET" "$RECEIPT_REL" "$CONSOLIDATED_REL" "$INDEX_REL")
if [ "$MODE" = "review" ]; then
  say ""
  say "DRY RUN COMPLETE: all checks passed in a throwaway stage. Nothing committed or pushed. --apply would commit:"
  printf '    %s\n' "${COMMIT_PATHS[@]}"
  say "Sign with ONE command:"
  say "    RATIFY_OPERATOR='<your name>' bash $SCRIPT_REL --apply --attest $GATE_ID"
  exit 0
fi

# ---- commit + push
say "== commit (stage, detached at ${BASE_SHA:0:12}) =="
g "$WT" add -- "${COMMIT_PATHS[@]}"
staged="$(g "$WT" diff --cached --name-only HEAD | sort)"
want="$(printf '%s\n' "${COMMIT_PATHS[@]}" | sort)"
[ "$staged" = "$want" ] || die "stage index holds an unexpected path set; NOT committed. Staged: $(echo $staged)"
g "$WT" commit -q \
  -m "RATIFIED $GATE_ID: unanswered-is-not-declined + exit-code-is-not-a-result (signed by $RATIFY_OPERATOR)" \
  -m "OPERATING_CONSTRAINTS.md: Operator Decision Requests (a missing answer is unanswered, not declined) and Inference and Benchmarks (post-measurement analysis before reporting). Receipts: $RECEIPT_REL, $CONSOLIDATED_REL, $INDEX_REL. No process touched." \
  || die "commit failed (a hook refused it?). Nothing pushed; re-run to retry."
COMMIT_SHA="$(g "$WT" rev-parse HEAD)"
ok "committed ${COMMIT_SHA:0:12}"

if [ "$DO_PUSH" -eq 0 ]; then
  KEEP_STAGE=1
  say "SIGNED AND COMMITTED, NOT PUSHED (--no-push): $COMMIT_SHA in $WT"
  say "Remove the stage afterwards: python3 $ROOT/scripts/system/worktree_gate.py remove $WT"
  exit 0
fi

say "== push (serialized, push lock) =="
TOKDIR="$(mktemp -d "$STAGE/push-token.XXXXXX")"; chmod 700 "$TOKDIR"; TOK="$TOKDIR/lease.token"
"$SYS_PY" "$PUSHER" --agent "$LOCK_AGENT" --repo "$ROOT" --lock-name push --acquire --token-file "$TOK" >/dev/null \
  || die "could not take the push lock. Nothing pushed; re-run."
prc=0
AGENT_ID="$LOCK_AGENT" EPYC_PUSH_LOCK_HOLDER="$LOCK_AGENT" g "$WT" push -q origin HEAD:refs/heads/main || prc=$?
"$SYS_PY" "$PUSHER" --agent "$LOCK_AGENT" --repo "$ROOT" --lock-name push --release --token-file "$TOK" >/dev/null \
  || say "WARN: push lock release failed; check: python3 $PUSHER --agent $LOCK_AGENT --repo $ROOT --lock-name push --status"
rm -f "$TOK"; rmdir "$TOKDIR" 2>/dev/null || true
[ "$prc" -eq 0 ] || die "git push rejected (rc=$prc; origin/main probably moved). Nothing landed; re-run."
g "$ROOT" fetch -q origin main
g "$ROOT" merge-base --is-ancestor "$COMMIT_SHA" origin/main || die "pushed, but $COMMIT_SHA is not on origin/main after fetch. Check by hand."
cat <<REPORT

RATIFIED $GATE_ID by $RATIFY_OPERATOR.
  root main: $COMMIT_SHA (pushed under the push lock)
  receipts:  $RECEIPT_REL, $CONSOLIDATED_REL, $INDEX_REL
NO PROCESS WAS TOUCHED.  VERIFY (read-only): bash $SCRIPT_REL --verify
ROLLBACK (operator): git revert $COMMIT_SHA on a fresh origin/main worktree, then push through serialized_push.py.
REPORT
