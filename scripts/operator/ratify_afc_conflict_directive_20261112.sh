#!/bin/bash
# ratify_afc_conflict_directive_20261112.sh — ONE operator signature over ONE measured agent-file amendment:
# the "Requests That Conflict With These Standards" section, added to agents/shared/ENGINEERING_STANDARDS.md and its
# three compressed variants (human-only files, AUD-15; agent writes are hook-blocked).
#
#   Why: suite v3d (2026-11-12), deployed aggressive level, production tool sets, paired Newcombe one-sided 95% vs the
#   filed v3c aggressive runs. Qwen3.6-35B compliance +0.220 (LB +0.153); Qwen3.8-Flash compliance +0.080 (LB +0.024),
#   procedure +0.121, recall +0.053; no pool regresses, and both pass non-inferiority vs v3c none. Rows:
#   afc-v3d-{q36_35b,q38_flash}-tools-aggressive-reword-20261112 (filed). Operator asked for the follow-up 2026-11-12.
#   The SAME text is inserted before "## Numerical Parameter Policy" in all four files. The aggressive variant becomes
#   byte-identical to the file both rows measured. The variants are NOT re-compressed, because that would change
#   measured text.
#
#   Review / dry run (default; full trial apply + receipt in a throwaway worktree, pushes nothing, keeps nothing):
#     bash scripts/operator/ratify_afc_conflict_directive_20261112.sh
#   Sign, commit and push to main (the OPERATOR runs this, from a terminal):
#     RATIFY_OPERATOR='<your name>' bash scripts/operator/ratify_afc_conflict_directive_20261112.sh --apply --attest RATIFY-AFC-CONFLICT-DIRECTIVE-20261112
#   Verify origin/main (read-only):
#     bash scripts/operator/ratify_afc_conflict_directive_20261112.sh --verify
#
# ratify-targets: agents/shared/ENGINEERING_STANDARDS.md agents/shared/ENGINEERING_STANDARDS.compressed-mild.md agents/shared/ENGINEERING_STANDARDS.compressed-medium.md agents/shared/ENGINEERING_STANDARDS.compressed-aggressive.md
#
# SAFETY: stages a detached scratch worktree of origin/main; nothing touches your checkout. Refuses unless every
# target's sha256 on the base equals its PRE pin (or all equal POST = ALREADY RATIFIED, exit 0). Prints the exact
# unified diffs before anything is committed. Touches no process.
# ROLLBACK: `git revert <ratify commit>` on a fresh origin/main worktree, pushed through serialized_push.py.
set -euo pipefail
export PATH="/usr/bin:/bin:${PATH}"

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
ROOT="${ROOT:-$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd)}"
SCRIPT_REL="scripts/operator/ratify_afc_conflict_directive_20261112.sh"
STAGE_PARENT="/mnt/raid0/llm/tmp"
LOCK_AGENT="operator-ratify-afc-directive"
SYS_PY="/usr/bin/python3"
GATE_ID="RATIFY-AFC-CONFLICT-DIRECTIVE-20261112"
TARGETS=(
  agents/shared/ENGINEERING_STANDARDS.md
  agents/shared/ENGINEERING_STANDARDS.compressed-mild.md
  agents/shared/ENGINEERING_STANDARDS.compressed-medium.md
  agents/shared/ENGINEERING_STANDARDS.compressed-aggressive.md
)
PRE_SHAS=(
  f319dece71b2c9fde34e07aa56bcf82ea4eab61d79d85ba4c5cfbf37c9fe5db9
  0010c35fe9b8d8f9f14c81fc90fa5910a5c3e8538cd8679bd225cb1738af4dea
  08c1348baf07e10f2f0eb9ec64d7d9cecc3cf4a83df8078c0a837529899611b5
  5d91b805eeb5bb8b33dc82125c7e6e932d9cdec0977ccdfc62b045bf04d712fa
)
POST_SHAS=(
  ad5e8d5f433a514aab5e9f90674f5ca2a4e4a061240d2bd724981341120b2760
  98609a2708980ba1bfdcfe6368a2390cd22ee5b6f8c1184e3c7d15ae63acf140
  108c89a68257e7d2fdf16833434f4ddeb66876445e3ec6e8e232d5ea80c1eec0
  b4dcc85ba882d9307baf6cd13cef540e68d2c6077a5b53475447b33a2dcfc634
)
CHECKER_REL="scripts/validate/check_ratification_receipts.py"
RECEIPT_REL="artifacts/operator/ratify_afc_conflict_directive_20261112.json"
INDEX_REL="artifacts/operator/receipts/$GATE_ID.json"
CONSOLIDATED_REL="artifacts/operator/ratify_afc_conflict_directive_20261112.receipt.json"
PROTOCOL_ID="ENGINEERING-STANDARDS-CONFLICTING-REQUESTS"
ANCHOR1="## Requests That Conflict With These Standards"

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
  for i in "${!TARGETS[@]}"; do
    have="$(g "$ROOT" show "origin/main:${TARGETS[$i]}" | sha256sum | awk '{print $1}')"
    [ "$have" = "${POST_SHAS[$i]}" ] || { say "  FAIL  ${TARGETS[$i]} is ${have:0:12}, post-state is ${POST_SHAS[$i]:0:12}"; exit 1; }
    ok "${TARGETS[$i]} at post-state ${POST_SHAS[$i]:0:12}"
  done
  for f in "$RECEIPT_REL" "$CONSOLIDATED_REL" "$INDEX_REL"; do
    if g "$ROOT" cat-file -e "origin/main:$f" 2>/dev/null; then ok "$f on origin/main"; else say "  FAIL  $f not on origin/main"; exit 1; fi
  done
  say "VERIFIED: $GATE_ID is on origin/main, pinned and receipted."; exit 0
fi

# ---- stage
STAGE="$(mktemp -d "$STAGE_PARENT/ratify-afc-directive.XXXXXX")"
WT="$STAGE/root"; WT_ADDED=0; KEEP_STAGE=0
cleanup() {
  local rc=$?
  if [ "$WT_ADDED" -eq 1 ] && [ "$KEEP_STAGE" -eq 0 ]; then
    g "$ROOT" worktree remove --force "$WT" >/dev/null 2>&1 || say "WARN: could not remove stage worktree $WT"
  fi
  if [ "$KEEP_STAGE" -eq 0 ]; then
    rm -f "$STAGE"/pre.json "$STAGE"/xform.py "$STAGE"/before/ENGINEERING_STANDARDS.md "$STAGE"/before/ENGINEERING_STANDARDS.compressed-mild.md "$STAGE"/before/ENGINEERING_STANDARDS.compressed-medium.md "$STAGE"/before/ENGINEERING_STANDARDS.compressed-aggressive.md
    rmdir "$STAGE"/before 2>/dev/null || true; rmdir "$STAGE" 2>/dev/null || true
  fi
  exit "$rc"
}
trap cleanup EXIT
g "$ROOT" worktree add -q --detach "$WT" "$BASE_SHA" || die "could not stage a worktree of $BASE"
WT_ADDED=1
ok "staged detached worktree $WT at ${BASE_SHA:0:12}"

# ---- preflight
say "== preflight (mode=$MODE) =="
all_post=1
for i in "${!TARGETS[@]}"; do [ "$(sha "$WT/${TARGETS[$i]}")" = "${POST_SHAS[$i]}" ] || all_post=0; done
if [ "$all_post" -eq 1 ] && [ -f "$WT/$INDEX_REL" ]; then
  say "ALREADY RATIFIED: every target is at its post-state pin and the receipt index is present. Nothing to do."; exit 0
fi
[ ! -e "$WT/$INDEX_REL" ] || die "receipt index exists but the targets are not at their post-state pins (half state). Not touching it."
for i in "${!TARGETS[@]}"; do
  t="${TARGETS[$i]}"
  ! grep -qF -- "$ANCHOR1" "$WT/$t" || die "$t already contains the section without a receipt (partial or manual state). Reconcile by hand."
  have="$(sha "$WT/$t")"
  [ "$have" = "${PRE_SHAS[$i]}" ] || die "$t on $BASE is ${have:0:12}, expected pre-state ${PRE_SHAS[$i]:0:12}. The base changed since this script was prepared; re-derive, do not overwrite."
  ok "$t at pre-state ${PRE_SHAS[$i]:0:12}"
done
[ ! -e "$WT/$RECEIPT_REL" ] || die "$RECEIPT_REL already exists"
if "$SYS_PY" "$WT/$CHECKER_REL" --repo-root "$WT" >/dev/null 2>&1; then ok "receipt checker exits 0 before the amendment"
else die "receipt checker does not exit 0 before the amendment"; fi

# ---- apply (in the stage only) and show exactly what changes
XFORM="$STAGE/xform.py"
cat >"$XFORM" <<'PYEOF'
import sys
p = sys.argv[1]
t = open(p, encoding="utf-8").read()
D = (
    "\n## Requests That Conflict With These Standards\n\n"
    "- Decide from the request alone: a conflict with a rule here does not need repo access, files, or more context.\n"
    "- Refuse first, and quote the exact rule you apply, verbatim from this file.\n"
    "- Ask for files or context only after the refusal, and only if the request has a compliant alternative.\n"
    "- Never answer \"Understood\" or proceed with a request that breaks a rule here.\n"
)
anchor = "\n## Numerical Parameter Policy"
assert t.count(anchor) == 1, p
t = t.replace(anchor, D + anchor, 1)
open(p, "w", encoding="utf-8").write(t)
PYEOF
mkdir -p "$STAGE/before"
STATE_ARGS=()
for t in "${TARGETS[@]}"; do STATE_ARGS+=(--state "$t"); cp "$WT/$t" "$STAGE/before/$(basename "$t")"; done
"$SYS_PY" "$WT/scripts/operator/ratification_receipt.py" capture --repo-root "$WT" "${STATE_ARGS[@]}" --out "$STAGE/pre.json" \
  || die "could not snapshot the pre-amendment state"
for i in "${!TARGETS[@]}"; do
  t="${TARGETS[$i]}"
  "$SYS_PY" "$XFORM" "$WT/$t" || die "transform failed on $t"
  say "== exact change to $t =="
  diff -u --label "a/$t" --label "b/$t" "$STAGE/before/$(basename "$t")" "$WT/$t" || true
  removed="$(diff "$STAGE/before/$(basename "$t")" "$WT/$t" | grep -c '^<' || true)"
  [ "$removed" -eq 0 ] || die "postflight: $removed lines removed from $t; additions only expected."
  [ "$(grep -cF -- "$ANCHOR1" "$WT/$t")" -eq 1 ] || die "postflight: the section must occur exactly once in $t."
  [ "$(sha "$WT/$t")" = "${POST_SHAS[$i]}" ] || die "postflight: $t post-state sha $(sha "$WT/$t") != pin ${POST_SHAS[$i]}."
  ok "$t: additions only; section once; post-state ${POST_SHAS[$i]:0:12}"
done

# ---- receipts
say "== MEASUREMENT.md section-5 consolidated receipt =="
receipt_rc=0
"$SYS_PY" "$WT/scripts/operator/ratification_receipt.py" emit \
  --repo-root "$WT" \
  --pre "$STAGE/pre.json" \
  --protocol-id "$PROTOCOL_ID" \
  --anchor "$ANCHOR1" \
  --ratification-id "$GATE_ID" \
  --script "$SCRIPT_PATH" \
  --operator "${RATIFY_OPERATOR:-DRY-RUN-PREVIEW}" \
  --no-evidence-reason "agent-file wording; measured by suite v3d rows afc-v3d-{q36_35b,q38_flash}-tools-aggressive-reword-20261112 (filed verdicts, paired Newcombe one-sided 95% vs v3c aggressive and none); handoff engineering-hygiene-backlog.md AFC-Q36-AGENTFILE-CTX-REFUSAL" \
  --validation "python3 $CHECKER_REL --repo-root ." \
  --validation "test \"\$(sha256sum agents/shared/ENGINEERING_STANDARDS.compressed-aggressive.md | cut -d' ' -f1)\" = ${POST_SHAS[3]}" \
  --out "$WT/$CONSOLIDATED_REL" || receipt_rc=$?
if [ "$receipt_rc" -ne 0 ]; then
  [ ! -f "$WT/$CONSOLIDATED_REL" ] || { cp "$WT/$CONSOLIDATED_REL" "$STAGE/refused.receipt.json"; KEEP_STAGE=1; say "  refused receipt kept: $STAGE/refused.receipt.json"; }
  die "consolidated receipt returned $receipt_rc (1 REFUSED, 2 COULD-NOT-CHECK). Nothing committed or pushed."
fi
ok "consolidated receipt: $CONSOLIDATED_REL"

RATIFIED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
OPERATOR_NAME="${RATIFY_OPERATOR:-DRY-RUN-PREVIEW}"
TJ="$("$SYS_PY" -c 'import json,sys;print(json.dumps(sys.argv[1:]))' "${TARGETS[@]}")"
PJ="$("$SYS_PY" -c 'import json,sys;print(json.dumps(sys.argv[1:]))' "${PRE_SHAS[@]}")"
QJ="$("$SYS_PY" -c 'import json,sys;print(json.dumps(sys.argv[1:]))' "${POST_SHAS[@]}")"
WT="$WT" RECEIPT_REL="$RECEIPT_REL" INDEX_REL="$INDEX_REL" CONSOLIDATED_REL="$CONSOLIDATED_REL" GATE_ID="$GATE_ID" TJ="$TJ" PJ="$PJ" QJ="$QJ" \
OPERATOR="$OPERATOR_NAME" TS="$RATIFIED_AT" BASE_SHA="$BASE_SHA" SCRIPT_SHA="$(sha "$SCRIPT_PATH")" SCRIPT_REL="$SCRIPT_REL" \
"$SYS_PY" - <<'PYEOF' || die "could not write the receipts. Nothing committed or pushed."
import json, os
e = os.environ
ts, pre, post = json.loads(e["TJ"]), json.loads(e["PJ"]), json.loads(e["QJ"])
doc = {
    "schema": "epyc.agent_file_amendment.v1",
    "gate_id": e["GATE_ID"],
    "status": "ratified",
    "ratified_at": e["TS"],
    "operator": e["OPERATOR"],
    "signature_channel": "operator-run script (--attest typed confirmation)",
    "operator_decisions": {
        "1": "2026-11-12: operator asked for the agent-file rewording follow-up to be tackled; adopted on measured benefit for both serving models",
    },
    "evidence": {
        "rows": ["afc-v3d-q36_35b-tools-aggressive-reword-20261112", "afc-v3d-q38_flash-tools-aggressive-reword-20261112"],
        "q36_compliance_vs_v3c_aggressive": {"d": 0.220, "lb": 0.1525},
        "q38_compliance_vs_v3c_aggressive": {"d": 0.080, "lb": 0.0238},
        "regressions": "none (every pool LB > -0.10 vs v3c none for both models)",
    },
    "base_origin_main": e["BASE_SHA"],
    "consolidated_receipt": e["CONSOLIDATED_REL"],
    "state": {t: {"sha256_before": a, "sha256_after": b} for t, a, b in zip(ts, pre, post)},
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

COMMIT_PATHS=("${TARGETS[@]}" "$RECEIPT_REL" "$CONSOLIDATED_REL" "$INDEX_REL")
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
  -m "RATIFIED $GATE_ID: 'Requests That Conflict' section in ENGINEERING_STANDARDS + variants (signed by $RATIFY_OPERATOR)" \
  -m "Suite v3d: Qwen3.6-35B compliance +0.220 (LB +0.153), Qwen3.8-Flash +0.080 (LB +0.024), no regressions. Aggressive variant byte-identical to the measured file. Receipts: $RECEIPT_REL, $CONSOLIDATED_REL, $INDEX_REL. No process touched." \
  -m "Operator-Ratified: yes" \
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
