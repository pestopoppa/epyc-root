#!/bin/bash
# ratify_trust_boundary_receipts_fix_20260926.sh — ONE operator signature for the 2026-09-26 repair of
# the MEASUREMENT.md section-5 receipt gate (scripts/validate/check_ratification_receipts.py).
#
#   Review (default, writes nothing):    bash scripts/operator/ratify_trust_boundary_receipts_fix_20260926.sh
#   Apply + receipts + commit (ONE):     bash scripts/operator/ratify_trust_boundary_receipts_fix_20260926.sh --apply --attest RATIFY-TRUST-BOUNDARY-RECEIPTS-FIX-20260926
#   Apply + receipts, no commit:         ... --apply --attest RATIFY-TRUST-BOUNDARY-RECEIPTS-FIX-20260926 --no-commit
#   Verify the post-state (read-only):   bash scripts/operator/ratify_trust_boundary_receipts_fix_20260926.sh --verify
#
# OPERATOR DIRECTIVE (2026-09-26, "shouldn't this be fixed?" — yes). The receipt checker that W7 added on
# 2026-08-02 was never wired to anything, could not see a write made through a variable, misread op60's
# quoting as a missing receipt, and scanned /workspace whatever checkout it was run from. The code fix is
# ordinary code on lane/fix-ratify-checker-20260926 and needs no signature. ONE thing does:
#
# WHAT YOU ARE SIGNING
#   1. The historical exemption list, scripts/validate/ratification_receipt_exemptions.json, AT THE
#      EXACT CONTENT pinned below. Each entry excuses one script from the section-5 receipt:
#        historical            already executed before it was compliant; the checker re-verifies at every
#                              run that the cited commit is in history, touches the boundary path the
#                              script writes, and that the script is byte-identical to its pin.
#        superseded            never run, replaced by a compliant/exempt successor.
#        not-a-boundary-write  a reviewed false positive: it names a boundary file and writes another.
#      No receipt is backfilled or invented for any of them; section 5 has no backfill clause.
#   2. Making that list HUMAN-ONLY: one entry appended to coordination/session-bus/human_only_paths.yaml
#      (artifacts/operator/trust-boundary-receipt-exemptions-20260926.patch, additions only) and the
#      .sha256 pin rewritten to match. From then on the PreToolUse hook refuses agent edits to the list,
#      so no agent can excuse its own unreceipted amendment by adding an entry.
#
# WHAT IT DOES NOT DO. It changes no protocol, no MEASUREMENT.md text, no annex, no doctrine file. It
# runs no ratification it exempts. It starts no process and takes no compute.
#
# PINS. Any mismatch is refused. If a target has moved, REGENERATE the bundle; never force or fuzz.
#   patch                             see PATCH_SHA256
#   human_only_paths.yaml pre/post    see YAML_PRE_SHA256 / YAML_POST_SHA256
#   exemption list (what you sign)    see EXEMPTIONS_SHA256
#   checker (what enforces it)        see CHECKER_SHA256
#
# The bundle emits the MEASUREMENT.md section-5 consolidated receipt over its own amendment, then the
# decision receipt and keyed index, and commits exactly five paths through a private index seeded from
# HEAD. Pushing is left to you; the command is printed.
#
# ROOT defaults to the checkout this script lives in. Override it with ROOT=<epyc-root checkout>.
set -euo pipefail

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
ROOT="${ROOT:-$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd)}"
SCRIPT_REL="scripts/operator/ratify_trust_boundary_receipts_fix_20260926.sh"

GATE_ID="RATIFY-TRUST-BOUNDARY-RECEIPTS-FIX-20260926"
PATCH_REL="artifacts/operator/trust-boundary-receipt-exemptions-20260926.patch"
YAML_REL="coordination/session-bus/human_only_paths.yaml"
PIN_REL="coordination/session-bus/human_only_paths.sha256"
EXEMPTIONS_REL="scripts/validate/ratification_receipt_exemptions.json"
CHECKER_REL="scripts/validate/check_ratification_receipts.py"
RECEIPT_REL="artifacts/operator/ratify_trust_boundary_receipts_fix_20260926.json"
INDEX_REL="artifacts/operator/receipts/$GATE_ID.json"
CONSOLIDATED_REL="artifacts/operator/ratify_trust_boundary_receipts_fix_20260926.receipt.json"
NEW_GLOB_LINE='    glob: "scripts/validate/ratification_receipt_exemptions.json"'
COMMIT_PATHS=("$YAML_REL" "$PIN_REL" "$RECEIPT_REL" "$INDEX_REL" "$CONSOLIDATED_REL")
COMMIT_MSG="RATIFIED: section-5 receipt exemptions are human-only; the pinned historical exemption list is signed (${GATE_ID})"

PATCH_SHA256="dd840e1b82e0efb109984ee2b7d813d62908760def2ddbeb2b3af5b1fb8273cb"
YAML_PRE_SHA256="db36527c289634b86d5298f4b9686043f74d7bc1e7c53c764ea9fa9bfcc3f0c3"
YAML_POST_SHA256="1a7b576f6b7d4dff291079e9418b0f07d24d3eab9fdd586b5a76d4b91362ef69"
EXEMPTIONS_SHA256="6be4c31be3ca90f68488b3a34b521d8a000163367a8fb93e44dd0ef6e49ab2ad"
CHECKER_SHA256="a9ee2d501c0f31870273b3e1a954d0152c57b727a4b7ea4666116e4e81c91f31"

MODE="review"; DO_COMMIT=1; ATTEST=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run|--review) MODE="review" ;;
    --apply)     MODE="apply" ;;
    --verify)    MODE="verify" ;;
    --no-commit) DO_COMMIT=0 ;;
    --attest)    shift; ATTEST="${1:-}" ;;
    *) echo "usage: $0 [--review | --verify | --apply --attest $GATE_ID [--no-commit]]" >&2; exit 64 ;;
  esac
  shift
done
# The signer is TYPED, never defaulted: unset, system-account (node, root, id -un) and
# agent-id names are refused before anything is written (2026-09-27 governance repair).
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/lib/ratify_operator.sh"
[ "$MODE" != "apply" ] || ratify_require_operator

say() { printf '%s\n' "$*"; }
die() { printf 'REFUSING: %s\n' "$*" >&2; exit 65; }
sha() { sha256sum "$1" | awk '{print $1}'; }

command -v python3   >/dev/null || die "python3 not on PATH"
command -v sha256sum >/dev/null || die "sha256sum not on PATH"
command -v git       >/dev/null || die "git not on PATH"
for f in "$YAML_REL" "$PIN_REL" "$EXEMPTIONS_REL" "$CHECKER_REL" "$PATCH_REL" \
         scripts/operator/ratification_receipt.py; do
  [ -f "$ROOT/$f" ] || die "$f not found under ROOT=$ROOT"
done

yaml_now="$(sha "$ROOT/$YAML_REL")"
pin_now="$(tr -d '[:space:]' < "$ROOT/$PIN_REL")"

# ---------------------------------------------------------------- verify (read-only)
if [ "$MODE" = "verify" ]; then
  ok=1
  [ "$yaml_now" = "$YAML_POST_SHA256" ] || { say "  FAIL  $YAML_REL is ${yaml_now:0:12}, expected post-state ${YAML_POST_SHA256:0:12}"; ok=0; }
  [ "$pin_now" = "$yaml_now" ]          || { say "  FAIL  $PIN_REL does not match $YAML_REL"; ok=0; }
  for f in "$RECEIPT_REL" "$INDEX_REL" "$CONSOLIDATED_REL"; do
    [ -f "$ROOT/$f" ] || { say "  FAIL  $f missing"; ok=0; }
  done
  if [ -f "$ROOT/$CONSOLIDATED_REL" ]; then
    v="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("verdict"))' "$ROOT/$CONSOLIDATED_REL")"
    [ "$v" = "RATIFIED" ] || { say "  FAIL  consolidated receipt verdict is $v"; ok=0; }
  fi
  python3 "$ROOT/$CHECKER_REL" --repo-root "$ROOT" >/dev/null || { say "  FAIL  $CHECKER_REL does not exit 0"; ok=0; }
  [ "$ok" -eq 1 ] && { say "VERIFIED: $GATE_ID is applied, pinned, receipted, and the checker is clean."; exit 0; }
  exit 1
fi

# ---------------------------------------------------------------- idempotence / partial states
if [ "$yaml_now" = "$YAML_POST_SHA256" ]; then
  if [ -f "$ROOT/$RECEIPT_REL" ] && [ -f "$ROOT/$INDEX_REL" ] && [ -f "$ROOT/$CONSOLIDATED_REL" ]; then
    say "ALREADY RATIFIED: $YAML_REL is at its post-state pin and all three receipts exist. Nothing to do."
    exit 0
  fi
  die "half-applied state: $YAML_REL is amended but a receipt is missing. Resolve by hand."
fi
for f in "$RECEIPT_REL" "$INDEX_REL" "$CONSOLIDATED_REL"; do
  [ -f "$ROOT/$f" ] && die "$f already exists but $YAML_REL is not amended. Resolve by hand."
done

# ---------------------------------------------------------------- preflight
say "== preflight (ROOT=$ROOT, mode=$MODE, commit=$DO_COMMIT) =="
fail=0
pin() { # pin <label> <expected> <found>
  if [ "$2" != "$3" ]; then
    printf '  FAIL  %-44s expected %s\n        %-44s found    %s\n' "$1" "$2" "" "$3"; fail=1
  else
    printf '  ok    %-44s (%s)\n' "$1" "${3:0:12}"
  fi
}
pin "patch hash"                         "$PATCH_SHA256"      "$(sha "$ROOT/$PATCH_REL")"
pin "human_only_paths.yaml pre-state"    "$YAML_PRE_SHA256"   "$yaml_now"
pin "human_only_paths.sha256 matches"    "$YAML_PRE_SHA256"   "$pin_now"
pin "exemption list (what you sign)"     "$EXEMPTIONS_SHA256" "$(sha "$ROOT/$EXEMPTIONS_REL")"
pin "checker (what enforces it)"         "$CHECKER_SHA256"    "$(sha "$ROOT/$CHECKER_REL")"
dirty="$(git -C "$ROOT" status --porcelain -- "${COMMIT_PATHS[@]}" "$EXEMPTIONS_REL" "$CHECKER_REL" 2>/dev/null || echo 'GIT-STATUS-FAILED')"
if [ -n "$dirty" ]; then printf '  FAIL  %-44s\n%s\n' "commit paths clean in git" "$dirty"; fail=1
else printf '  ok    %-44s\n' "commit paths clean in git"; fi
if git -C "$ROOT" apply --check "$ROOT/$PATCH_REL" 2>/dev/null; then
  printf '  ok    %-44s\n' "patch applies cleanly (no fuzz)"
else
  printf '  FAIL  %-44s\n' "patch applies cleanly (no fuzz)"; fail=1
fi
if python3 "$ROOT/$CHECKER_REL" --repo-root "$ROOT" >/dev/null; then
  printf '  ok    %-44s\n' "receipt checker exits 0 before the amendment"
else
  printf '  FAIL  %-44s\n' "receipt checker exits 0 before the amendment"; fail=1
fi
[ "$fail" -eq 0 ] || die "preflight failed: $ROOT is not in the state this bundle was prepared against. Stale checkout: fast-forward it. Moved target: regenerate the bundle. Nothing written."
say "  preflight clean"

if [ "$MODE" = "review" ]; then
  say ""
  say "== amendment diff ($PATCH_REL) =="
  cat "$ROOT/$PATCH_REL"
  say ""
  say "== the exemption list you are signing ($EXEMPTIONS_REL, ${EXEMPTIONS_SHA256:0:12}) =="
  python3 - "$ROOT/$EXEMPTIONS_REL" <<'PYEOF'
import json, sys
for e in json.load(open(sys.argv[1], encoding="utf-8"))["exemptions"]:
    tail = e.get("applied_in") or e.get("superseded_by") or ""
    print(f"  {e['kind']:<21s} {e['script']}  {tail}")
    print(f"  {'':<21s}   {e['reason'][:150]}")
PYEOF
  say ""
  say "REVIEW ONLY: nothing written. Apply with ONE command:"
  say "    ROOT=$ROOT bash $SCRIPT_PATH --apply --attest $GATE_ID"
  exit 0
fi

[ "$ATTEST" = "$GATE_ID" ] || die "--apply needs --attest $GATE_ID (the single attestation token). Nothing written."

# ---------------------------------------------------------------- apply
RATIFIED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
TMPD="$(mktemp -d)"
trap 'rm -rf "$TMPD"' EXIT
cp "$ROOT/$YAML_REL" "$TMPD/yaml.bak"
cp "$ROOT/$PIN_REL"  "$TMPD/pin.bak"
PRE="$TMPD/pre.json"
restore() {
  cp "$TMPD/yaml.bak" "$ROOT/$YAML_REL"
  cp "$TMPD/pin.bak"  "$ROOT/$PIN_REL"
  rm -f "$ROOT/$RECEIPT_REL" "$ROOT/$INDEX_REL"
}

say ""
say "== apply =="
python3 "$ROOT/scripts/operator/ratification_receipt.py" capture --repo-root "$ROOT" \
  --state "$YAML_REL" --state "$PIN_REL" --out "$PRE" \
  || die "could not snapshot the pre-amendment state; nothing written"
git -C "$ROOT" apply "$ROOT/$PATCH_REL" || { restore; die "git apply failed; targets restored. Nothing changed."; }
sha "$ROOT/$YAML_REL" > "$ROOT/$PIN_REL"

# ---------------------------------------------------------------- postflight
say ""
say "== postflight =="
pf=0
got="$(sha "$ROOT/$YAML_REL")"
if [ "$got" = "$YAML_POST_SHA256" ]; then say "  ok    human_only_paths.yaml post-state (${got:0:12})"
else say "  FAIL  human_only_paths.yaml post-state: expected $YAML_POST_SHA256 found $got"; pf=1; fi
if [ "$(tr -d '[:space:]' < "$ROOT/$PIN_REL")" = "$got" ]; then say "  ok    .sha256 pin rewritten to match"
else say "  FAIL  .sha256 pin does not match the amended list"; pf=1; fi
if python3 - "$TMPD/yaml.bak" "$ROOT/$YAML_REL" "$ROOT/$CHECKER_REL" "$ROOT" <<'PYEOF'
import difflib, importlib.util, sys
from pathlib import Path
a = open(sys.argv[1], encoding="utf-8").read().split("\n")
b = open(sys.argv[2], encoding="utf-8").read().split("\n")
removed = [l for l in difflib.unified_diff(a, b, lineterm="", n=0) if l.startswith("-") and not l.startswith("---")]
spec = importlib.util.spec_from_file_location("crr", sys.argv[3]); m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
globs, errors = m.boundary_tokens(Path(sys.argv[2]))
ok = not removed and not errors and "scripts/validate/ratification_receipt_exemptions.json" in globs
print(f"  {'ok  ' if ok else 'FAIL'}  additions only ({len(removed)} removed); list parses; exemption list now in the boundary")
sys.exit(0 if ok else 1)
PYEOF
then :; else pf=1; fi
if [ "$pf" -ne 0 ]; then restore; die "postflight failed: targets restored from backup. Nothing changed."; fi
say "  postflight clean"

# ---------------------------------------------------------------- consolidated receipt (MEASUREMENT.md section 5)
say ""
say "== section-5 consolidated receipt =="
receipt_rc=0
python3 "$ROOT/scripts/operator/ratification_receipt.py" emit \
  --repo-root "$ROOT" \
  --pre "$PRE" \
  --protocol-id TRUST-BOUNDARY-RECEIPT-EXEMPTIONS \
  --anchor "$NEW_GLOB_LINE" \
  --ratification-id "$GATE_ID" \
  --script "$SCRIPT_PATH" \
  --operator "$RATIFY_OPERATOR" \
  --no-evidence-reason "governance amendment to the human-only list, not a measured claim; every exemption it protects cites its own commit, which ${CHECKER_REL} re-verifies at each run" \
  --validation "python3 $CHECKER_REL --repo-root ." \
  --validation "test \"\$(sha256sum $YAML_REL | cut -d' ' -f1)\" = \"\$(tr -d '[:space:]' < $PIN_REL)\"" \
  --validation "test \"\$(sha256sum $EXEMPTIONS_REL | cut -d' ' -f1)\" = $EXEMPTIONS_SHA256" \
  --out "$ROOT/$CONSOLIDATED_REL" || receipt_rc=$?
if [ "$receipt_rc" -ne 0 ]; then
  refused="$ROOT/${CONSOLIDATED_REL%.receipt.json}.refused-$(date -u +%Y%m%dT%H%M%SZ).receipt.json"
  [ -f "$ROOT/$CONSOLIDATED_REL" ] && mv "$ROOT/$CONSOLIDATED_REL" "$refused"
  restore
  die "consolidated receipt returned $receipt_rc (1 REFUSED, 2 COULD-NOT-CHECK). Amendment rolled back; the receipt is kept at ${refused#"$ROOT"/} for reading."
fi

# ---------------------------------------------------------------- decision receipt + keyed index
if ! python3 - "$ROOT" "$RATIFIED_AT" "$GATE_ID" "$RECEIPT_REL" "$INDEX_REL" "$CONSOLIDATED_REL" \
     "$RATIFY_OPERATOR" "$PATCH_REL" "$PATCH_SHA256" "$SCRIPT_REL" \
     "$YAML_PRE_SHA256" "$YAML_POST_SHA256" "$EXEMPTIONS_REL" "$EXEMPTIONS_SHA256" \
     "$CHECKER_REL" "$CHECKER_SHA256" <<'PYEOF'
import json, os, sys
(root, ts, gate, receipt_rel, index_rel, consolidated_rel, operator, patch_rel, patch_sha, script_rel,
 yaml_pre, yaml_post, ex_rel, ex_sha, checker_rel, checker_sha) = sys.argv[1:17]
entries = json.load(open(os.path.join(root, ex_rel), encoding="utf-8"))["exemptions"]
doc = {
  "schema": "epyc.trust_boundary.amendment.v1",
  "gate_id": gate,
  "decision": "SECTION-5-RECEIPT-EXEMPTIONS-HUMAN-ONLY",
  "operator_directive": "2026-09-26: fix the measurement trust-boundary ratification tooling; everything needing the operator in ONE package",
  "ratified_at": ts,
  "operator": operator,
  "status": "ratified",
  "signed": {
    "exemption_list": {"path": ex_rel, "sha256": ex_sha, "entries": len(entries),
                       "by_kind": {k: sum(1 for e in entries if e["kind"] == k)
                                   for k in sorted({e["kind"] for e in entries})}},
    "boundary_amendment": {"path": "coordination/session-bus/human_only_paths.yaml",
                           "sha256_before": yaml_pre, "sha256_after": yaml_post,
                           "adds_glob": ex_rel, "pin_rewritten": True},
    "enforcer": {"path": checker_rel, "sha256": checker_sha},
  },
  "not_granted": "no protocol, constitution, annex or doctrine text changes; no exempted ratification is re-run or re-certified; no receipt is backfilled",
  "patch": {"path": patch_rel, "sha256": patch_sha},
  "consolidated_receipt": consolidated_rel,
  "applied_by": script_rel,
}
with open(os.path.join(root, receipt_rel), "x", encoding="utf-8") as fh:
    json.dump(doc, fh, indent=2, ensure_ascii=False); fh.write("\n")
os.makedirs(os.path.dirname(os.path.join(root, index_rel)), exist_ok=True)
with open(os.path.join(root, index_rel), "x", encoding="utf-8") as fh:
    json.dump({"gate_id": gate, "indexed_by": "ratify", "receipt": "/workspace/" + receipt_rel,
               "schema_version": "session_bus.receipt_index.v1", "status": "ratified"},
              fh, indent=2, sort_keys=True)
    fh.write("\n"); fh.flush(); os.fsync(fh.fileno())
print(f"  decision receipt: {receipt_rel}")
print(f"  keyed index:      {index_rel}")
PYEOF
then
  restore; rm -f "$ROOT/$CONSOLIDATED_REL"
  die "could not write the decision receipt or keyed index. Amendment rolled back."
fi

BRANCH="$(git -C "$ROOT" rev-parse --abbrev-ref HEAD)"
if [ "$DO_COMMIT" -eq 0 ]; then
  say ""
  say "APPLIED, NOT STAGED, NOT COMMITTED (--no-commit). Commit exactly these five paths:"
  say "    git -C $ROOT add -- ${COMMIT_PATHS[*]}"
  say "    git -C $ROOT commit -m '$COMMIT_MSG'     # only if nothing else is staged in this index"
  exit 0
fi

# ---------------------------------------------------------------- commit (private index)
say ""
say "== commit on $BRANCH =="
PIDX="$TMPD/private.index"
commit_manual="git -C $ROOT add -- ${COMMIT_PATHS[*]} && git -C $ROOT commit -m '$COMMIT_MSG'"
GIT_INDEX_FILE="$PIDX" git -C "$ROOT" read-tree HEAD \
  || die "could not seed a private index from HEAD. The amendment and receipts ARE applied (not rolled back). Commit by hand: $commit_manual"
GIT_INDEX_FILE="$PIDX" git -C "$ROOT" add -- "${COMMIT_PATHS[@]}" \
  || die "could not stage into the private index. The amendment and receipts ARE applied (not rolled back). Commit by hand: $commit_manual"
staged_yaml="$(GIT_INDEX_FILE="$PIDX" git -C "$ROOT" show ":$YAML_REL" | sha256sum | awk '{print $1}')"
[ "$staged_yaml" = "$YAML_POST_SHA256" ] \
  || die "the staged $YAML_REL (${staged_yaml:0:12}) does not match its post-state pin: something edited it after postflight. NOT committed."
staged_list="$(GIT_INDEX_FILE="$PIDX" git -C "$ROOT" diff --cached --name-only HEAD | sort)"
expected_list="$(printf '%s\n' "${COMMIT_PATHS[@]}" | sort)"
[ "$staged_list" = "$expected_list" ] \
  || die "the private index holds an unexpected path set; NOT committed. Staged: $(echo $staged_list)"
if GIT_INDEX_FILE="$PIDX" git -C "$ROOT" commit -q -m "$COMMIT_MSG"; then
  git -C "$ROOT" reset -q -- "${COMMIT_PATHS[@]}" \
    || say "  WARNING: 'git reset -q -- <five paths>' failed; run it by hand so the index matches HEAD."
  say "  committed $(git -C "$ROOT" rev-parse --short HEAD) on $BRANCH:"
  git -C "$ROOT" show --stat --format='  %s' HEAD | sed 's/^/  /'
else
  die "the commit failed. The amendment and receipts ARE applied in the working tree (not rolled back). Commit by hand: $commit_manual"
fi

say ""
say "RATIFIED and committed. Not pushed. Publish:"
if [ "$BRANCH" = "main" ]; then
  say "    python3 $ROOT/scripts/coordination/serialized_push.py --agent operator --repo $ROOT --fetch --push"
else
  say "    git -C $ROOT push origin $BRANCH"
fi
