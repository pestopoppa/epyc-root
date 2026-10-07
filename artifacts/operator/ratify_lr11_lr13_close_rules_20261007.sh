#!/bin/bash
# Private preparation of the LR-11/LR-13 human-only policy ratification.
# This script is review-only by default. The human operator must run --apply --attest
# from a terminal and type their own name; chat consent or agent execution is not a signature.
set -euo pipefail

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
ROOT="${ROOT:-$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd)}"
GATE="RATIFY-LR11-LR13-CLOSE-RULES-20261007"
PATCH_REL="artifacts/operator/lr11-lr13-close-rules-20261007.patch"
SCRIPT_REL="artifacts/operator/ratify_lr11_lr13_close_rules_20261007.sh"
OC_REL="agents/shared/OPERATING_CONSTRAINTS.md"
SL_REL="agents/shared/SESSION_LIFECYCLE.md"
CHECKER_REL="scripts/validate/check_ratification_receipts.py"
RECEIPT_REL="artifacts/operator/ratify_lr11_lr13_close_rules_20261007.json"
INDEX_REL="artifacts/operator/receipts/$GATE.json"
CONSOLIDATED_REL="artifacts/operator/ratify_lr11_lr13_close_rules_20261007.receipt.json"
PATCH_SHA256="e604ea87390029a4ea3d9f155d9d00dcb2dc4deae7c4d951e6b9e73687ec686b"
BASE_OC_BLOB="8290442dafcd0ad85d59947b625014d8392765d0"
BASE_SL_BLOB="6cc2c3f52c6323cabedf755f7b54ccc8e0c1f5e8"
ANCHOR_OC="- **Every subagent brief names its completion records and scratch lifetime.**"
ANCHOR_SL="- **Ticket/PR close includes the same task-owned scratch gate.**"
COMMIT_PATHS=("$OC_REL" "$SL_REL" "$RECEIPT_REL" "$INDEX_REL" "$CONSOLIDATED_REL")
COMMIT_MSG="RATIFIED: LR-11/LR-13 close-time scratch rules ($GATE)"
MODE=review; ATTEST=""; DO_COMMIT=1
while (($#)); do
  case "$1" in
    --review) MODE=review ;;
    --verify) MODE=verify ;;
    --apply) MODE=apply ;;
    --attest) shift; ATTEST="${1:-}" ;;
    --no-commit) DO_COMMIT=0 ;;
    *) echo "usage: $0 [--review|--verify|--apply --attest $GATE [--no-commit]]" >&2; exit 64 ;;
  esac
  shift
done
say(){ printf '%s\n' "$*"; }
die(){ printf 'REFUSING: %s\n' "$*" >&2; exit 65; }
sha(){ sha256sum "$1" | awk '{print $1}'; }
for f in "$OC_REL" "$SL_REL" "$PATCH_REL" "$CHECKER_REL" scripts/operator/ratification_receipt.py scripts/operator/lib/ratify_operator.sh; do
  [[ -f "$ROOT/$f" ]] || die "$f missing under ROOT=$ROOT"
done
source "$ROOT/scripts/operator/lib/ratify_operator.sh"

anchors_present(){
  local n=0
  grep -qF -- "$ANCHOR_OC" "$ROOT/$OC_REL" && n=$((n+1))
  grep -qF -- "$ANCHOR_SL" "$ROOT/$SL_REL" && n=$((n+1))
  printf '%s\n' "$n"
}
receipts_match(){
  python3 - "$ROOT/$CONSOLIDATED_REL" "$ROOT/$RECEIPT_REL" "$ROOT/$INDEX_REL" "$GATE" <<'PYRECEIPTS'
import json, sys
consolidated, decision, index = [json.load(open(p, encoding="utf-8")) for p in sys.argv[1:4]]
gate = sys.argv[4]
if consolidated.get("verdict") != "RATIFIED" or consolidated.get("ratification_id") != gate:
    raise SystemExit("consolidated receipt gate/verdict mismatch")
if decision.get("gate_id") != gate or decision.get("status") != "ratified":
    raise SystemExit("decision receipt gate/status mismatch")
if index.get("gate_id") != gate or index.get("status") != "ratified":
    raise SystemExit("keyed receipt index gate/status mismatch")
PYRECEIPTS
}

if [[ "$MODE" == verify ]]; then
  [[ "$(anchors_present)" == 2 ]] || die "both policy anchors are not present"
  for f in "$RECEIPT_REL" "$INDEX_REL" "$CONSOLIDATED_REL"; do [[ -f "$ROOT/$f" ]] || die "$f missing"; done
  receipts_match || die "one or more receipts do not attest this gate"
  python3 "$ROOT/$CHECKER_REL" --repo-root "$ROOT"
  say "VERIFIED: $GATE anchors and receipts present."
  exit 0
fi

if [[ "$(anchors_present)" == 2 && -f "$ROOT/$RECEIPT_REL" && -f "$ROOT/$INDEX_REL" && -f "$ROOT/$CONSOLIDATED_REL" ]]; then
  receipts_match || die "amended targets have missing or mismatched receipts; resolve manually"
  say "ALREADY RATIFIED: both exact anchors and matching receipts exist; no changes made."
  exit 0
fi
[[ "$(anchors_present)" == 0 ]] || die "target is partially amended; resolve manually"
for f in "$RECEIPT_REL" "$INDEX_REL" "$CONSOLIDATED_REL"; do [[ ! -e "$ROOT/$f" ]] || die "$f already exists"
done
[[ "$(sha "$ROOT/$PATCH_REL")" == "$PATCH_SHA256" ]] || die "patch hash differs; regenerate and review the bundle"
for pair in "$OC_REL:$BASE_OC_BLOB" "$SL_REL:$BASE_SL_BLOB"; do
  path="${pair%%:*}"; expected="${pair#*:}"
  actual="$(git -C "$ROOT" rev-parse "HEAD:$path" 2>/dev/null || true)"
  [[ "$actual" == "$expected" ]] || die "$path HEAD blob moved; regenerate the bundle"
  [[ -z "$(git -C "$ROOT" status --porcelain -- "$path")" ]] || die "$path has local changes"
done
[[ -z "$(git -C "$ROOT" status --porcelain -- "${COMMIT_PATHS[@]}")" ]] || die "ratification output paths are dirty"
git -C "$ROOT" apply --check "$ROOT/$PATCH_REL" || die "exact patch context no longer applies"
python3 "$ROOT/$CHECKER_REL" --repo-root "$ROOT" >/dev/null || die "ratification receipt checker is not clean before amendment"

if [[ "$MODE" == review ]]; then
  say "REVIEW ONLY — no files written."
  say "Decision: approve two additive common-policy bullets for LR-11 ticket/PR close inventory/cleanup retention and LR-13 task-owned records/scratch lifetime."
  say "Patch SHA-256: $PATCH_SHA256"
  cat "$ROOT/$PATCH_REL"
  say "To sign, the human operator must run from a terminal:"
  say "  RATIFY_OPERATOR='<your name>' ROOT='$ROOT' bash '$SCRIPT_PATH' --apply --attest $GATE"
  exit 0
fi

[[ "$MODE" == apply ]] || die "unsupported mode"
[[ -t 0 && -t 1 ]] || die "--apply must be run directly in an operator terminal"
ratify_require_operator
[[ "$ATTEST" == "$GATE" ]] || die "--apply requires exact --attest $GATE"

TMPD="$(mktemp -d)"
trap 'rm -rf "$TMPD"' EXIT
python3 "$ROOT/scripts/operator/ratification_receipt.py" capture --repo-root "$ROOT" \
  --state "$OC_REL" --state "$SL_REL" --out "$TMPD/pre.json"
restore(){
  if [[ -f "$ROOT/$CONSOLIDATED_REL" ]]; then
    refused="$ROOT/artifacts/operator/ratify_lr11_lr13_close_rules_20261007.refused.$(date -u +%Y%m%dT%H%M%SZ).$$.receipt.json"
    cp -p "$ROOT/$CONSOLIDATED_REL" "$refused"
  fi
  cp "$TMPD/oc.before" "$ROOT/$OC_REL"
  cp "$TMPD/sl.before" "$ROOT/$SL_REL"
  rm -f "$ROOT/$RECEIPT_REL" "$ROOT/$INDEX_REL" "$ROOT/$CONSOLIDATED_REL"
}
cp "$ROOT/$OC_REL" "$TMPD/oc.before"
cp "$ROOT/$SL_REL" "$TMPD/sl.before"
if ! git -C "$ROOT" apply "$ROOT/$PATCH_REL"; then restore; die "patch application failed; targets restored"
fi
OC_AFTER="$(sha "$ROOT/$OC_REL")"; SL_AFTER="$(sha "$ROOT/$SL_REL")"
if ! python3 - "$TMPD/oc.before" "$TMPD/sl.before" "$ROOT/$OC_REL" "$ROOT/$SL_REL" "$ANCHOR_OC" "$ANCHOR_SL" <<'PY'
import difflib, pathlib, sys
before = [pathlib.Path(p).read_text(encoding="utf-8") for p in sys.argv[1:3]]
after = [pathlib.Path(p).read_text(encoding="utf-8") for p in sys.argv[3:5]]
anchors = sys.argv[5:7]
for old, new, anchor in zip(before, after, anchors):
    diff = list(difflib.unified_diff(old.splitlines(), new.splitlines(), n=0))
    removed = [line for line in diff if line.startswith("-") and not line.startswith("---")]
    if removed: raise SystemExit("refuse: policy amendment removed or rewrote a line")
    if new.count(anchor) != 1: raise SystemExit(f"refuse: anchor count is not exactly one: {anchor}")
print("PASS: both files changed additively; each amendment anchor occurs once")
PY
then restore; die "postflight failed; targets restored"; fi

receipt_rc=0
python3 "$ROOT/scripts/operator/ratification_receipt.py" emit --repo-root "$ROOT" \
  --pre "$TMPD/pre.json" --protocol-id "LR11-LR13-CLOSE-RULES" \
  --ratification-id "$GATE" --script "$SCRIPT_REL" \
  --operator "$RATIFY_OPERATOR" \
  --anchor "$ANCHOR_OC" --anchor "$ANCHOR_SL" \
  --no-evidence-reason "workflow doctrine amendment; source is the LR-11/LR-13 task and exact additive patch" \
  --validation "git diff --check -- $OC_REL $SL_REL" \
  --validation "test \"\$(grep -cF -- '$ANCHOR_OC' '$OC_REL')\" = 1 && test \"\$(grep -cF -- '$ANCHOR_SL' '$SL_REL')\" = 1" \
  --out "$ROOT/$CONSOLIDATED_REL" || receipt_rc=$?
if ((receipt_rc != 0)); then restore; die "consolidated receipt refused (exit $receipt_rc); amendment rolled back"; fi

RATIFIED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
if ! python3 - "$ROOT" "$GATE" "$RATIFY_OPERATOR" "$RATIFIED_AT" "$PATCH_REL" "$PATCH_SHA256" "$SCRIPT_REL" "$RECEIPT_REL" "$INDEX_REL" "$CONSOLIDATED_REL" "$OC_REL" "$SL_REL" "$OC_AFTER" "$SL_AFTER" <<'PY'
import json, os, sys
(root, gate, operator, at, patch, patch_sha, script, receipt, index, consolidated,
 oc, sl, oc_after, sl_after) = sys.argv[1:]
doc = {
  "schema": "epyc.operating_constraints_amendment.v1",
  "decision": "LR11-LR13-CLOSE-TIME-SCRATCH-AND-SUBAGENT-RECORDS",
  "gate_id": gate, "operator_decision": "explicit human ratification of the two-file additive amendment",
  "ratified_at": at, "operator": operator, "status": "ratified",
  "targets": [oc, sl],
  "rule": "Ticket/PR close performs an exact declared-root/lane inventory; cleanup is limited to main-released paths through the existing cleanup gate. Each subagent owns its private completion records; the main specifies scratch retention and release.",
  "not_changed": "two additive bullets only; no lines rewritten or deleted; no human_only_paths.yaml or pin change",
  "patch": {"path": patch, "sha256": patch_sha},
  "state": {oc: {"sha256_after": oc_after}, sl: {"sha256_after": sl_after}},
  "consolidated_receipt": consolidated, "applied_by": script,
}
with open(os.path.join(root, receipt), "x", encoding="utf-8") as f:
    json.dump(doc, f, indent=2, ensure_ascii=False); f.write("\n")
with open(os.path.join(root, index), "x", encoding="utf-8") as f:
    json.dump({"gate_id": gate, "indexed_by": "ratify", "receipt": "/workspace/"+receipt,
               "schema_version": "session_bus.receipt_index.v1", "status": "ratified"},
              f, indent=2, sort_keys=True); f.write("\n")
PY
then
  restore
  die "decision receipt/index creation failed; target files restored"
fi
if ! python3 "$ROOT/$CHECKER_REL" --repo-root "$ROOT"; then
  restore
  die "post-ratification receipt checker failed; target files and receipts restored"
fi

if ((DO_COMMIT)); then
  PIDX="$TMPD/private.index"
  GIT_INDEX_FILE="$PIDX" git -C "$ROOT" read-tree HEAD
  GIT_INDEX_FILE="$PIDX" git -C "$ROOT" add -- "${COMMIT_PATHS[@]}"
  staged="$(GIT_INDEX_FILE="$PIDX" git -C "$ROOT" diff --cached --name-only HEAD | sort)"
  expected="$(printf '%s\n' "${COMMIT_PATHS[@]}" | sort)"
  [[ "$staged" == "$expected" ]] || die "private index path set differs; not committed"
  GIT_INDEX_FILE="$PIDX" git -C "$ROOT" commit -m "$COMMIT_MSG"
  # The isolated commit index leaves the ordinary index at the old HEAD. Refresh
  # only these preflight-clean paths to the new HEAD; do not touch peer entries.
  git -C "$ROOT" restore --staged --source=HEAD -- "${COMMIT_PATHS[@]}"
  [[ -z "$(git -C "$ROOT" status --porcelain -- "${COMMIT_PATHS[@]}")" ]] || die "committed target paths are not clean in ordinary index/worktree"
else
  say "APPLIED, not committed (--no-commit); exact receipt and two policy targets remain in working tree."
fi
say "Ratification transaction complete locally; no push performed."
