#!/bin/bash
# Private preparation of the RTG-34 FM-9 (Codex delegation contract) human-only policy ratification.
# This script is review-only by default. The human operator must run --apply --attest
# from a terminal and type their own name; chat consent or agent execution is not a signature.
set -euo pipefail

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
ROOT="${ROOT:-$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd)}"
GATE="RATIFY-FM9-DELEGATION-CONTRACT-20261111"
PATCH_REL="artifacts/operator/fm9-delegation-contract-20261111.patch"
SCRIPT_REL="artifacts/operator/ratify_fm9_delegation_contract_20261111.sh"
SL_REL="agents/shared/OPERATING_CONSTRAINTS.md"
CHECKER_REL="scripts/validate/check_ratification_receipts.py"
RECEIPT_REL="artifacts/operator/ratify_fm9_delegation_contract_20261111.json"
INDEX_REL="artifacts/operator/receipts/$GATE.json"
CONSOLIDATED_REL="artifacts/operator/ratify_fm9_delegation_contract_20261111.receipt.json"
PATCH_SHA256="b02e0309582466f5525ca189129e3e4aaa7ed2e44f3e13a1c238edb04c740e0f"
BASE_SL_BLOB="c5a0ad0ed0c7b3fbb221a1069e73f69954ee610a"
ANCHOR_SL='- **Codex sub-delegation contract (FM-9; mirrors `agents/README.md` → *Codex sub-agent routing*'
COMMIT_PATHS=("$SL_REL" "$RECEIPT_REL" "$INDEX_REL" "$CONSOLIDATED_REL")
COMMIT_MSG="$(printf '%s\n\n%s\n' "RATIFIED: RTG-34 FM-9 Codex delegation contract ($GATE)" 'Operator-Ratified: yes')"
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
for f in "$SL_REL" "$PATCH_REL" "$CHECKER_REL" scripts/operator/ratification_receipt.py scripts/operator/lib/ratify_operator.sh; do
  [[ -f "$ROOT/$f" ]] || die "$f missing under ROOT=$ROOT"
done
source "$ROOT/scripts/operator/lib/ratify_operator.sh"

anchors_present(){
  local n=0
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
  [[ "$(anchors_present)" == 1 ]] || die "policy anchor is not present"
  for f in "$RECEIPT_REL" "$INDEX_REL" "$CONSOLIDATED_REL"; do [[ -f "$ROOT/$f" ]] || die "$f missing"; done
  receipts_match || die "one or more receipts do not attest this gate"
  python3 "$ROOT/$CHECKER_REL" --repo-root "$ROOT"
  say "VERIFIED: $GATE anchors and receipts present."
  exit 0
fi

if [[ "$(anchors_present)" == 1 && -f "$ROOT/$RECEIPT_REL" && -f "$ROOT/$INDEX_REL" && -f "$ROOT/$CONSOLIDATED_REL" ]]; then
  receipts_match || die "amended targets have missing or mismatched receipts; resolve manually"
  say "ALREADY RATIFIED: exact anchor and matching receipts exist; no changes made."
  exit 0
fi
[[ "$(anchors_present)" == 0 ]] || die "target is partially amended; resolve manually"
for f in "$RECEIPT_REL" "$INDEX_REL" "$CONSOLIDATED_REL"; do [[ ! -e "$ROOT/$f" ]] || die "$f already exists"
done
[[ "$(sha "$ROOT/$PATCH_REL")" == "$PATCH_SHA256" ]] || die "patch hash differs; regenerate and review the bundle"
for pair in "$SL_REL:$BASE_SL_BLOB"; do
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
  say "Decision: approve one additive bullet in OPERATING_CONSTRAINTS.md (Codex Delegation & Long-Horizon Throughput): the FM-9 Codex sub-delegation contract, mirroring agents/README.md at ab1f1d38d with FM-7 numbers."
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
  --state "$SL_REL" --out "$TMPD/pre.json"
restore(){
  if [[ -f "$ROOT/$CONSOLIDATED_REL" ]]; then
    refused="$ROOT/artifacts/operator/ratify_fm9_delegation_contract_20261111.refused.$(date -u +%Y%m%dT%H%M%SZ).$$.receipt.json"
    cp -p "$ROOT/$CONSOLIDATED_REL" "$refused"
  fi
    cp "$TMPD/sl.before" "$ROOT/$SL_REL"
  rm -f "$ROOT/$RECEIPT_REL" "$ROOT/$INDEX_REL" "$ROOT/$CONSOLIDATED_REL"
}
cp "$ROOT/$SL_REL" "$TMPD/sl.before"
if ! git -C "$ROOT" apply "$ROOT/$PATCH_REL"; then restore; die "patch application failed; targets restored"
fi
SL_AFTER="$(sha "$ROOT/$SL_REL")"
if ! python3 - "$TMPD/sl.before" "$ROOT/$SL_REL" "$ANCHOR_SL" <<'PY'
import difflib, pathlib, sys
before = [pathlib.Path(p).read_text(encoding="utf-8") for p in sys.argv[1:2]]
after = [pathlib.Path(p).read_text(encoding="utf-8") for p in sys.argv[2:3]]
anchors = sys.argv[3:4]
for old, new, anchor in zip(before, after, anchors):
    diff = list(difflib.unified_diff(old.splitlines(), new.splitlines(), n=0))
    removed = [line for line in diff if line.startswith("-") and not line.startswith("---")]
    if removed: raise SystemExit("refuse: policy amendment removed or rewrote a line")
    if new.count(anchor) != 1: raise SystemExit(f"refuse: anchor count is not exactly one: {anchor}")
print("PASS: file changed additively; amendment anchor occurs once")
PY
then restore; die "postflight failed; targets restored"; fi

receipt_rc=0
python3 "$ROOT/scripts/operator/ratification_receipt.py" emit --repo-root "$ROOT" \
  --pre "$TMPD/pre.json" --protocol-id "RTG34-FM9-DELEGATION-CONTRACT" \
  --ratification-id "$GATE" --script "$SCRIPT_REL" \
  --operator "$RATIFY_OPERATOR" \
  --anchor "$ANCHOR_SL" \
  --no-evidence-reason "workflow doctrine amendment; source is RTG-34 FM-9, agents/README.md at ab1f1d38d and data/fanout_timing/delegation_accounting_report.v1.json" \
  --validation "git diff --check -- $SL_REL" \
  --validation "test \"\$(grep -cF -- '$ANCHOR_SL' '$SL_REL')\" = 1" \
  --out "$ROOT/$CONSOLIDATED_REL" || receipt_rc=$?
if ((receipt_rc != 0)); then restore; die "consolidated receipt refused (exit $receipt_rc); amendment rolled back"; fi

RATIFIED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
if ! python3 - "$ROOT" "$GATE" "$RATIFY_OPERATOR" "$RATIFIED_AT" "$PATCH_REL" "$PATCH_SHA256" "$SCRIPT_REL" "$RECEIPT_REL" "$INDEX_REL" "$CONSOLIDATED_REL" "$SL_REL" "$SL_AFTER" <<'PY'
import json, os, sys
(root, gate, operator, at, patch, patch_sha, script, receipt, index, consolidated,
 sl, sl_after) = sys.argv[1:]
doc = {
  "schema": "epyc.operating_constraints_amendment.v1",
  "decision": "RTG34-FM9-DELEGATION-CONTRACT",
  "gate_id": gate, "operator_decision": "explicit human ratification of the one-file additive amendment",
  "ratified_at": at, "operator": operator, "status": "ratified",
  "targets": [sl],
  "rule": "Codex sub-delegation contract: luna/terra/sol/astra tier ladder, effort before tier, bounded sub-agent length (F = 21.8k Codex / 49.9k Claude), shared brief/return/accounting contracts (FM-7 basis).",
  "not_changed": "one additive bullet only; no lines rewritten or deleted; no human_only_paths.yaml or pin change",
  "patch": {"path": patch, "sha256": patch_sha},
  "state": {sl: {"sha256_after": sl_after}},
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
  # AUD-15 commit-msg hook (scripts/hooks/check_instruction_surface_ratified.py) refuses an
  # agents/shared/*.md commit without this trailer; LR-11's script was blocked by exactly that.
  grep -qxF "Operator-Ratified: yes" <<<"$COMMIT_MSG" || die "commit message lacks the Operator-Ratified trailer"
  GIT_INDEX_FILE="$PIDX" git -C "$ROOT" commit -m "$COMMIT_MSG"
  # The isolated commit index leaves the ordinary index at the old HEAD. Refresh
  # only these preflight-clean paths to the new HEAD; do not touch peer entries.
  git -C "$ROOT" restore --staged --source=HEAD -- "${COMMIT_PATHS[@]}"
  [[ -z "$(git -C "$ROOT" status --porcelain -- "${COMMIT_PATHS[@]}")" ]] || die "committed target paths are not clean in ordinary index/worktree"
else
  say "APPLIED, not committed (--no-commit); exact receipt and two policy targets remain in working tree."
fi
say "Ratification transaction complete locally; no push performed."
