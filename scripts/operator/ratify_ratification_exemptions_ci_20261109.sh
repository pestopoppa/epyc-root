#!/bin/bash
# ratify_ratification_exemptions_ci_20261109.sh — ONE operator signature over 8 operator-approved exemption entries added to the
# human-only file scripts/validate/ratification_receipt_exemptions.json `.exemptions` (trust boundary; agent writes are hook-blocked).
#
#   The 8 entries are `.entries` of artifacts/operator/staged/ratification-exemptions-add-20261109.json (all kind
#   not-a-boundary-write: archived compute-artifact sources the text heuristic mistakes for boundary writes). The
#   operator approved applying them 2026-11-09. Each is appended at the END of `.exemptions`; the stage refuses a
#   duplicate, a changed pre-existing entry, or a staged file that is not the pinned one.
#
#   Review / dry run (default; full trial apply + receipt + checker + checker tests in a throwaway worktree, pushes nothing, keeps nothing):
#     bash scripts/operator/ratify_ratification_exemptions_ci_20261109.sh
#   Sign, commit and push to main (the OPERATOR runs this, from a terminal, AFTER this script is on origin/main):
#     RATIFY_OPERATOR='<your name>' bash scripts/operator/ratify_ratification_exemptions_ci_20261109.sh --apply --attest RATIFY-RATIFICATION-EXEMPTIONS-CI-20261109
#   Same, but leave the signed commit unpushed in the stage worktree:   ... --apply --attest ... --no-push
#   Verify origin/main (read-only):
#     bash scripts/operator/ratify_ratification_exemptions_ci_20261109.sh --verify
#
# ratify-targets: scripts/validate/ratification_receipt_exemptions.json
#
# Also emits the MEASUREMENT.md section-5 consolidated receipt (the checker classifies this script as a boundary writer).
# SAFETY: stages a detached scratch worktree of origin/main; nothing touches your checkout. Refuses unless the target's
# sha256 on the base equals the PRE pin (or already equals the POST pin = ALREADY RATIFIED, exit 0). Prints the exact
# unified diff before anything is committed. Runs scripts/validate/check_ratification_receipts.py and
# tests/validate/test_check_ratification_receipts.py on the staged tree and refuses on failure. Touches no process.
# ROLLBACK: `git revert <ratify commit>` on a fresh origin/main worktree, pushed through serialized_push.py.
set -euo pipefail
export PATH="/usr/bin:/bin:${PATH}"

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
ROOT="${ROOT:-$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd)}"
SCRIPT_REL="scripts/operator/ratify_ratification_exemptions_ci_20261109.sh"
STAGE_PARENT="/mnt/raid0/llm/tmp"
LOCK_AGENT="operator-ratify-exemptions-ci"
SYS_PY="/usr/bin/python3"
GATE_ID="RATIFY-RATIFICATION-EXEMPTIONS-CI-20261109"
TARGET="scripts/validate/ratification_receipt_exemptions.json"
STAGED_REL="artifacts/operator/staged/ratification-exemptions-add-20261109.json"
STAGED_SHA="746a79e5be900ca67d85a318fc1d0376ee0f39774970adf62d4325f0b10b1a3c"
EXPECT_N=8
PRE_SHA="a2306bbb077dc2768af7a18760ae5e6836c271b3ab362a72145b3a972fb8897c"
POST_SHA="1ca24d8c409af038cd4805033dd446e51fa3bed8d0b674606f679080cd76b55e"
CHECKER_REL="scripts/validate/check_ratification_receipts.py"
TEST_REL="tests/validate/test_check_ratification_receipts.py"
RECEIPT_REL="artifacts/operator/ratify_ratification_exemptions_ci_20261109.json"
INDEX_REL="artifacts/operator/receipts/$GATE_ID.json"
CONSOLIDATED_REL="artifacts/operator/ratify_ratification_exemptions_ci_20261109.receipt.json"
PROTOCOL_ID="RATIFICATION-RECEIPT-EXEMPTIONS-CI-20261109"
ANCHOR1="artifacts/compute/inf22-m4-q38-recipe-r4-20261104/source/scripts/vidya/adapters/confidence_source_capture.py"
ANCHOR2="artifacts/compute/vidya-r18-gfx-source-20261101/run.py"

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
STAGE="$(mktemp -d "$STAGE_PARENT/ratify-exemptions-ci.XXXXXX")"
WT="$STAGE/root"; WT_ADDED=0; KEEP_STAGE=0
cleanup() {
  local rc=$?
  if [ "$WT_ADDED" -eq 1 ] && [ "$KEEP_STAGE" -eq 0 ]; then
    g "$ROOT" worktree remove --force "$WT" >/dev/null 2>&1 || say "WARN: could not remove stage worktree $WT"
  fi
  if [ "$KEEP_STAGE" -eq 0 ]; then rm -f "$STAGE"/pre.json "$STAGE"/xform.py "$STAGE"/before.json "$STAGE"/after.json; rmdir "$STAGE" 2>/dev/null || true; fi
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
  die "an entry is already present without a receipt (partial or manual state). Reconcile by hand; not touching it."
fi
[ "$have" = "$PRE_SHA" ] || die "$TARGET on $BASE is ${have:0:12}, expected pre-state ${PRE_SHA:0:12}. The base changed since this script was prepared; re-derive, do not overwrite."
ok "$TARGET at pre-state ${PRE_SHA:0:12}"
[ -f "$WT/$STAGED_REL" ] || die "$STAGED_REL is not on $BASE"
[ "$(sha "$WT/$STAGED_REL")" = "$STAGED_SHA" ] || die "$STAGED_REL on $BASE is $(sha "$WT/$STAGED_REL"), expected pin ${STAGED_SHA}."
ok "staged entries file at pin ${STAGED_SHA:0:12}"
[ ! -e "$WT/$RECEIPT_REL" ] || die "$RECEIPT_REL already exists"
# This script must be part of the tree the checker scans (it is a boundary writer that emits a receipt).
if g "$ROOT" cat-file -e "$BASE_SHA:$SCRIPT_REL" 2>/dev/null; then
  [ "$(g "$ROOT" show "$BASE_SHA:$SCRIPT_REL" | sha256sum | awk '{print $1}')" = "$(sha "$SCRIPT_PATH")" ] \
    || die "$SCRIPT_REL on $BASE differs from the script being run; run the copy that is on $BASE."
  ok "$SCRIPT_REL is on $BASE and identical to this copy"
else
  [ "$MODE" = "review" ] || die "$SCRIPT_REL is not on $BASE. Push the script to main first; --apply refuses to sign a script the checker cannot scan."
  cp -- "$SCRIPT_PATH" "$WT/$SCRIPT_REL"
  say "  note  $SCRIPT_REL is not yet on $BASE; dry run copied this script into the stage so the checker scans it"
fi
# Before the amendment the checker is EXPECTED to fail on exactly the scripts being exempted; record the count, do not require 0.
pre_fail="$("$SYS_PY" "$WT/$CHECKER_REL" --repo-root "$WT" 2>&1 | grep -c 'FAIL' || true)"
say "  info  receipt checker before the amendment: ${pre_fail} FAIL line(s) (expected: the $EXPECT_N scripts this exempts)"

# ---- apply (in the stage only) and show exactly what changes
XFORM="$STAGE/xform.py"
cat >"$XFORM" <<'PYEOF'
import json, sys
target, staged, expect_n = sys.argv[1], sys.argv[2], int(sys.argv[3])
doc = json.load(open(target, encoding="utf-8"))
new = json.load(open(staged, encoding="utf-8"))["entries"]
if len(new) != expect_n:
    sys.exit(f"staged file has {len(new)} entries, expected {expect_n}")
want = {"script", "kind", "script_sha256", "evidence", "reason"}
seen = {e["script"] for e in doc["exemptions"]}
for e in new:
    if set(e) != want:
        sys.exit(f"entry {e.get('script')!r} has fields {sorted(e)}, expected {sorted(want)}")
    if e["script"] in seen:
        sys.exit(f"duplicate exemption for {e['script']}")
    seen.add(e["script"])
doc["exemptions"] = doc["exemptions"] + new
sys.stdout.write(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
PYEOF
cp "$WT/$TARGET" "$STAGE/before.json"
"$SYS_PY" "$WT/scripts/operator/ratification_receipt.py" capture --repo-root "$WT" --state "$TARGET" --out "$STAGE/pre.json" \
  || die "could not snapshot the pre-amendment state"
"$SYS_PY" "$XFORM" "$STAGE/before.json" "$WT/$STAGED_REL" "$EXPECT_N" >"$STAGE/after.json" || die "transform failed"
cp "$STAGE/after.json" "$WT/$TARGET"
say "== exact change to $TARGET =="
diff -u --label "a/$TARGET" --label "b/$TARGET" "$STAGE/before.json" "$WT/$TARGET" || true
removed="$(diff "$STAGE/before.json" "$WT/$TARGET" | grep -c '^<' || true)"
# The only permitted removed line is the closing "  ]" / "}" shuffle: a trailing comma added to the last old entry.
[ "$removed" -le 1 ] || die "postflight: $removed lines removed; only the last old entry's closing line (trailing comma) may change."
n_after="$("$SYS_PY" -c 'import json,sys; print(len(json.load(open(sys.argv[1]))["exemptions"]))' "$WT/$TARGET")"
n_before="$("$SYS_PY" -c 'import json,sys; print(len(json.load(open(sys.argv[1]))["exemptions"]))' "$STAGE/before.json")"
[ "$((n_after - n_before))" -eq "$EXPECT_N" ] || die "postflight: exemptions went $n_before -> $n_after, expected +$EXPECT_N."
"$SYS_PY" - "$STAGE/before.json" "$WT/$TARGET" "$EXPECT_N" <<'PYEOF' || die "postflight: pre-existing entries changed, or duplicates present."
import json, sys
a = json.load(open(sys.argv[1])); b = json.load(open(sys.argv[2])); n = int(sys.argv[3])
assert b["exemptions"][:-n] == a["exemptions"], "old entries changed"
assert {k: v for k, v in b.items() if k != "exemptions"} == {k: v for k, v in a.items() if k != "exemptions"}, "non-exemption keys changed"
s = [e["script"] for e in b["exemptions"]]
assert len(s) == len(set(s)), "duplicate script"
PYEOF
[ "$(grep -cF -- "$ANCHOR1" "$WT/$TARGET")" -eq 1 ] && [ "$(grep -cF -- "$ANCHOR2" "$WT/$TARGET")" -eq 1 ] || die "postflight: each anchor entry must occur exactly once."
[ "$(sha "$WT/$TARGET")" = "$POST_SHA" ] || die "postflight: post-state sha $(sha "$WT/$TARGET") != pin ${POST_SHA}."
ok "$EXPECT_N entries appended, none duplicated, old entries unchanged; post-state ${POST_SHA:0:12}"

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
  --no-evidence-reason "governance amendment to the human-only exemption list, not a measured claim; each entry cites its own 2026-11-09 CI-red review evidence and is sha-pinned, which ${CHECKER_REL} re-verifies at every run" \
  --validation "python3 $CHECKER_REL --repo-root ." \
  --validation "python3 -m pytest -q $TEST_REL" \
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
STAGED_REL="$STAGED_REL" STAGED_SHA="$STAGED_SHA" N="$EXPECT_N" \
OPERATOR="$OPERATOR_NAME" TS="$RATIFIED_AT" BASE_SHA="$BASE_SHA" SCRIPT_SHA="$(sha "$SCRIPT_PATH")" SCRIPT_REL="$SCRIPT_REL" \
"$SYS_PY" - <<'PYEOF' || die "could not write the receipts. Nothing committed or pushed."
import json, os
e = os.environ
doc = {
    "schema": "epyc.ratification_exemptions_amendment.v1",
    "gate_id": e["GATE_ID"],
    "status": "ratified",
    "ratified_at": e["TS"],
    "operator": e["OPERATOR"],
    "signature_channel": "operator-run script (--attest typed confirmation)",
    "operator_decisions": {
        "1": "2026-11-09: apply the 8 not-a-boundary-write exemption entries staged in " + e["STAGED_REL"] + " to " + e["TARGET"] + " .exemptions",
    },
    "origin": "2026-11-09 CI-red review (ni/ci-red-20261109)",
    "base_origin_main": e["BASE_SHA"],
    "entries_added": int(e["N"]),
    "staged_entries_file": {"path": e["STAGED_REL"], "sha256": e["STAGED_SHA"]},
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

# ---- checker + its tests on the staged tree (refuse on failure)
say "== checker and checker tests on the staged tree =="
if "$SYS_PY" "$WT/$CHECKER_REL" --repo-root "$WT" >"$STAGE/checker.out" 2>&1; then ok "receipt checker exits 0 after the amendment"
else tail -20 "$STAGE/checker.out" >&2; rm -f "$STAGE/checker.out"; die "receipt checker fails after the amendment. Nothing committed or pushed."; fi
rm -f "$STAGE/checker.out"
if (cd "$WT" && PYTHONDONTWRITEBYTECODE=1 "$SYS_PY" -m pytest -q -p no:cacheprovider "$TEST_REL" >"$STAGE/tests.out" 2>&1); then
  ok "$TEST_REL passes on the staged tree (includes test_live_repository_is_clean): $(tail -1 "$STAGE/tests.out")"
else tail -30 "$STAGE/tests.out" >&2; rm -f "$STAGE/tests.out"; die "$TEST_REL fails on the staged tree. Nothing committed or pushed."; fi
rm -f "$STAGE/tests.out"

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
  -m "RATIFIED $GATE_ID: 8 not-a-boundary-write exemptions added (signed by $RATIFY_OPERATOR)" \
  -m "ratification_receipt_exemptions.json .exemptions += the 8 entries of $STAGED_REL (operator-approved 2026-11-09). Receipts: $RECEIPT_REL, $CONSOLIDATED_REL, $INDEX_REL. No process touched." \
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
