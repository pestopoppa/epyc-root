#!/bin/bash
# ratify_op63_region_lock_scope_20260926.sh — OP-63: the CPU region-lock rule in
# agents/shared/OPERATING_CONSTRAINTS.md covers processes that run inference THEMSELVES, never traffic
# sent through the orchestrator API.
#
#   Review (default, writes nothing):    bash scripts/operator/ratify_op63_region_lock_scope_20260926.sh
#   Apply + receipts + commit (ONE):     bash scripts/operator/ratify_op63_region_lock_scope_20260926.sh --apply --attest RATIFY-OP63-REGION-LOCK-SCOPE-20260926
#   Apply + receipts, no commit:         ... --apply --attest RATIFY-OP63-REGION-LOCK-SCOPE-20260926 --no-commit
#   Verify the post-state (read-only):   bash scripts/operator/ratify_op63_region_lock_scope_20260926.sh --verify
#
# OPERATOR DECISION OP-63 (approved 2026-09-26, session workspace-8d). Tracked as OP-63 in
# handoffs/active/master-handoff-index.md and HYG-5 in handoffs/active/non-inference-backlog.md.
#
# WHY. The first bullet of "Inference and Benchmarks" says never to launch "inference/benchmark runs
# (... eval suites)" without a held CPU-region claim. It reads as if it covers traffic sent THROUGH the
# orchestrator API. HS-4 P0.4 run 1 (2026-09-26) followed it literally: its runner wrapped an
# OpenCode -> /v1 client in an outer `region-lock run` over q0-q3. That claim starved the orchestrator's
# own per-call placement, and every frontdoor call failed with
#   placement timeout role=frontdoor reason=race_lost holders=[] after 60.0s   (503 contention_denied)
# with 0 tool calls. The run was a method error, not a product defect
# (handoffs/active/harness-selection-and-integration.md, P0.4; r1's run dir was not preserved).
#
# WHAT THE AMENDMENT DOES (artifacts/operator/op63-region-lock-scope-20260926.patch)
#   - rewrites ONE line: the rule now names processes that run inference ITSELF (llama-bench/cli, a
#     self-launched llama-server, run_benchmark.py, an eval suite driving its own server). The lock
#     command, bench_canonical.sh's automatic claim and the "claim, not a human" sentence are unchanged;
#   - adds ONE sub-bullet: API traffic (:8000) is placed and region-claimed by the orchestrator per call,
#     so an outer region-lock over the same regions must never wrap it; a quiet window for API traffic
#     is coordinated with the session that owns the measurement. It cites the incident.
#
# WHAT IT DOES NOT DO. No code, no measurement rule, no other file. The section heading is unchanged, so
# the CLAUDE.md link to "Inference and Benchmarks" still resolves. It does not touch
# coordination/session-bus/human_only_paths.yaml. Nothing here starts a process or takes compute.
#
# WHY IT NEEDS YOU. agents/shared/*.md is human-amendment-only (coordination/session-bus/
# human_only_paths.yaml). An agent prepared this bundle; only the operator applies it.
#
# PINS. Any mismatch is refused. If the target has moved, REGENERATE the bundle; never force or fuzz.
#   patch                                   see PATCH_SHA256
#   OPERATING_CONSTRAINTS.md   pre-state    see OC_PRE_SHA256   (epyc-root origin/main 1175b2ba)
#   OPERATING_CONSTRAINTS.md   post-state   see OC_POST_SHA256
#
# The bundle emits the MEASUREMENT.md section-5 consolidated receipt over its own amendment (a doctrine
# amendment anchors in its own target), then the decision receipt and keyed index, and commits exactly
# four paths through a private index seeded from HEAD. Pushing is left to you; the command is printed.
#
# IDEMPOTENT. When the target is at its post-state pin and all three receipts exist, a re-run prints
# ALREADY RATIFIED and exits 0. Every other partial state is refused.
#
# ROOT defaults to the checkout this script lives in. Override it with ROOT=<epyc-root checkout>.
set -euo pipefail

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
ROOT="${ROOT:-$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd)}"
SCRIPT_REL="scripts/operator/ratify_op63_region_lock_scope_20260926.sh"

GATE_ID="RATIFY-OP63-REGION-LOCK-SCOPE-20260926"
PATCH_REL="artifacts/operator/op63-region-lock-scope-20260926.patch"
OC_REL="agents/shared/OPERATING_CONSTRAINTS.md"
CHECKER_REL="scripts/validate/check_ratification_receipts.py"
RECEIPT_REL="artifacts/operator/ratify_op63_region_lock_scope_20260926.json"
INDEX_REL="artifacts/operator/receipts/$GATE_ID.json"
CONSOLIDATED_REL="artifacts/operator/ratify_op63_region_lock_scope_20260926.receipt.json"
COMMIT_PATHS=("$OC_REL" "$RECEIPT_REL" "$INDEX_REL" "$CONSOLIDATED_REL")
COMMIT_MSG="RATIFIED: region-lock covers self-run inference only; API traffic is claimed per call by the orchestrator (OP-63, ${GATE_ID})"

# The one line the amendment rewrites, and the anchors that must exist exactly once afterwards.
OLD_RULE_HEAD='- Never launch inference/benchmark runs (llama-bench/cli/server, run_benchmark.py, eval suites) without a held CPU-region claim'
NEW_RULE_HEAD='- Never launch a process that runs inference ITSELF (llama-bench/cli, a self-launched llama-server, run_benchmark.py, an eval suite driving its own server) without a held CPU-region claim'
NEW_SUB_HEAD='  - **Traffic sent through the orchestrator API (`:8000`) is not such a run, and an outer `region-lock` must never wrap it.**'

PATCH_SHA256="8f5cabb06bf811a584ab1fb14893c885541d5c924764c5c3df5cbd7292d6cf38"
OC_PRE_SHA256="c66ff747a7e235d442fcd72e8dceca23190335624b9237ef339d928acf7359ab"
OC_POST_SHA256="8bfaa03228aac79d6ac34c9f635a0f3529d75e57ffc759fb283be5837518eab8"

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

say() { printf '%s\n' "$*"; }
die() { printf 'REFUSING: %s\n' "$*" >&2; exit 65; }
sha() { sha256sum "$1" | awk '{print $1}'; }

command -v python3   >/dev/null || die "python3 not on PATH"
command -v sha256sum >/dev/null || die "sha256sum not on PATH"
command -v git       >/dev/null || die "git not on PATH"
for f in "$OC_REL" "$PATCH_REL" "$CHECKER_REL" scripts/operator/ratification_receipt.py; do
  [ -f "$ROOT/$f" ] || die "$f not found under ROOT=$ROOT"
done

oc_now="$(sha "$ROOT/$OC_REL")"

# ---------------------------------------------------------------- verify (read-only)
if [ "$MODE" = "verify" ]; then
  ok=1
  [ "$oc_now" = "$OC_POST_SHA256" ] || { say "  FAIL  $OC_REL is ${oc_now:0:12}, expected post-state ${OC_POST_SHA256:0:12}"; ok=0; }
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
if [ "$oc_now" = "$OC_POST_SHA256" ]; then
  if [ -f "$ROOT/$RECEIPT_REL" ] && [ -f "$ROOT/$INDEX_REL" ] && [ -f "$ROOT/$CONSOLIDATED_REL" ]; then
    say "ALREADY RATIFIED: $OC_REL is at its post-state pin and all three receipts exist. Nothing to do."
    exit 0
  fi
  die "half-applied state: $OC_REL is amended but a receipt is missing. Resolve by hand."
fi
[ -f "$ROOT/$INDEX_REL" ] && die "keyed index $INDEX_REL already exists, so this gate is already spent. Double-signing is refused."
for f in "$RECEIPT_REL" "$CONSOLIDATED_REL"; do
  [ -f "$ROOT/$f" ] && die "$f already exists but $OC_REL is not amended. Resolve by hand."
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
pin "patch hash"                              "$PATCH_SHA256"  "$(sha "$ROOT/$PATCH_REL")"
pin "OPERATING_CONSTRAINTS.md pre-state hash" "$OC_PRE_SHA256" "$oc_now"
dirty="$(git -C "$ROOT" status --porcelain -- "${COMMIT_PATHS[@]}" 2>/dev/null || echo 'GIT-STATUS-FAILED')"
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
[ "$fail" -eq 0 ] || die "preflight failed: $ROOT is not in the state this bundle was prepared against (epyc-root origin/main 1175b2ba). Stale checkout: fast-forward it. Moved target: regenerate the bundle. Nothing written."
say "  preflight clean"

if [ "$MODE" = "review" ]; then
  say ""
  say "== amendment diff ($PATCH_REL) =="
  cat "$ROOT/$PATCH_REL"
  say ""
  say "REVIEW ONLY: nothing written. Would amend $OC_REL (post-state pin ${OC_POST_SHA256:0:12}),"
  say "emit the section-5 consolidated receipt, the decision receipt and the keyed index, and commit those four paths."
  say "Apply with ONE command:"
  say "    ROOT=$ROOT bash $SCRIPT_PATH --apply --attest $GATE_ID"
  exit 0
fi

[ "$ATTEST" = "$GATE_ID" ] || die "--apply needs --attest $GATE_ID (the single attestation token). Nothing written."

# ---------------------------------------------------------------- apply
RATIFIED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
TMPD="$(mktemp -d)"
trap 'rm -rf "$TMPD"' EXIT
cp "$ROOT/$OC_REL" "$TMPD/oc.bak"
PRE="$TMPD/pre.json"
restore() {
  cp "$TMPD/oc.bak" "$ROOT/$OC_REL"
  rm -f "$ROOT/$RECEIPT_REL" "$ROOT/$INDEX_REL"
}

say ""
say "== apply =="
python3 "$ROOT/scripts/operator/ratification_receipt.py" capture --repo-root "$ROOT" \
  --state "$OC_REL" --out "$PRE" \
  || die "could not snapshot the pre-amendment state; nothing written"
# Working tree only, never --index: staging happens below, into a private index, after postflight.
git -C "$ROOT" apply "$ROOT/$PATCH_REL" || { restore; die "git apply failed; target restored. Nothing changed."; }

# ---------------------------------------------------------------- postflight
say ""
say "== postflight =="
oc_after="$(sha "$ROOT/$OC_REL")"
if [ "$oc_after" != "$OC_POST_SHA256" ]; then
  restore; die "post-state hash mismatch (expected ${OC_POST_SHA256:0:12}, found ${oc_after:0:12}); target restored. Nothing changed."
fi
printf '  ok    %-44s (%s)\n' "OPERATING_CONSTRAINTS.md post-state hash" "${oc_after:0:12}"
if python3 - "$TMPD/oc.bak" "$ROOT/$OC_REL" "$OLD_RULE_HEAD" "$NEW_RULE_HEAD" "$NEW_SUB_HEAD" <<'PYEOF'
import difflib, sys
a = open(sys.argv[1], encoding="utf-8").read().split("\n")
b = open(sys.argv[2], encoding="utf-8").read().split("\n")
old_head, new_head, sub_head = sys.argv[3:6]
diff = list(difflib.unified_diff(a, b, lineterm="", n=0))
removed = [l[1:] for l in diff if l.startswith("-") and not l.startswith("---")]
added = [l[1:] for l in diff if l.startswith("+") and not l.startswith("+++")]
text = "\n".join(b)
ok = True
if len(removed) != 1 or not removed[0].startswith(old_head):
    print(f"  FAIL  expected exactly ONE line rewritten (the region-lock rule); {len(removed)} removed"); ok = False
if len(added) != 2 or not added[0].startswith(new_head) or not added[1].startswith(sub_head):
    print(f"  FAIL  expected exactly the rewritten rule plus one sub-bullet; {len(added)} added"); ok = False
for needle in (new_head, sub_head, "## Inference and Benchmarks\n",
               "`bench_canonical.sh` acquires it automatically and refuses to run unlocked"):
    if text.count(needle) != 1:
        print(f"  FAIL  expected exactly one occurrence of: {needle.strip()[:80]!r}"); ok = False
if old_head in text:
    print("  FAIL  the old rule text is still present"); ok = False
if ok:
    print("  ok    one line rewritten, one sub-bullet added; heading and lock mechanics intact")
sys.exit(0 if ok else 1)
PYEOF
then :; else restore; die "postflight failed: target restored. Nothing changed."; fi
say "  postflight clean"

# ---------------------------------------------------------------- consolidated receipt (MEASUREMENT.md section 5)
say ""
say "== section-5 consolidated receipt =="
receipt_rc=0
python3 "$ROOT/scripts/operator/ratification_receipt.py" emit \
  --repo-root "$ROOT" \
  --pre "$PRE" \
  --protocol-id OPERATING-CONSTRAINTS-REGION-LOCK-SCOPE \
  --anchor "$NEW_RULE_HEAD" \
  --anchor "$NEW_SUB_HEAD" \
  --ratification-id "$GATE_ID" \
  --script "$SCRIPT_PATH" \
  --operator "${RATIFY_OPERATOR:-${USER:-unknown}}" \
  --no-evidence-reason "doctrine scope clarification, not a measured claim; the incident (HS-4 P0.4 run 1, 503 contention_denied under an outer region-lock) is recorded in handoffs/active/harness-selection-and-integration.md P0.4, and r1's run dir was not preserved" \
  --validation "python3 $CHECKER_REL --repo-root ." \
  --validation "test \"\$(sha256sum $OC_REL | cut -d' ' -f1)\" = $OC_POST_SHA256" \
  --validation "test \"\$(grep -c '^## Inference and Benchmarks\$' $OC_REL)\" = 1" \
  --out "$ROOT/$CONSOLIDATED_REL" || receipt_rc=$?
if [ "$receipt_rc" -ne 0 ]; then
  refused="$ROOT/${CONSOLIDATED_REL%.receipt.json}.refused-$(date -u +%Y%m%dT%H%M%SZ).receipt.json"
  [ -f "$ROOT/$CONSOLIDATED_REL" ] && mv "$ROOT/$CONSOLIDATED_REL" "$refused"
  restore
  die "consolidated receipt returned $receipt_rc (1 REFUSED, 2 COULD-NOT-CHECK). Amendment rolled back; the receipt is kept at ${refused#"$ROOT"/} for reading."
fi

# ---------------------------------------------------------------- decision receipt + keyed index
if ! python3 - "$ROOT" "$RATIFIED_AT" "$GATE_ID" "$RECEIPT_REL" "$INDEX_REL" "$CONSOLIDATED_REL" \
     "${RATIFY_OPERATOR:-${USER:-unknown}}" "$PATCH_REL" "$PATCH_SHA256" "$SCRIPT_REL" \
     "$OC_PRE_SHA256" "$OC_POST_SHA256" <<'PYEOF'
import json, os, sys
(root, ts, gate, receipt_rel, index_rel, consolidated_rel, operator, patch_rel, patch_sha, script_rel,
 oc_pre, oc_post) = sys.argv[1:13]
doc = {
  "schema": "epyc.operating_constraints_amendment.v1",
  "decision": "REGION-LOCK-COVERS-SELF-RUN-INFERENCE-NOT-API-TRAFFIC",
  "gate_id": gate,
  "operator_decision": "OP-63, approved 2026-09-26 (session workspace-8d)",
  "ratified_at": ts,
  "operator": operator,
  "status": "ratified",
  "target": "agents/shared/OPERATING_CONSTRAINTS.md",
  "section": "Inference and Benchmarks",
  "rule": "region-lock is for processes that run inference themselves (benches, llama-bench/cli, self-launched servers); traffic sent through the orchestrator API (:8000) is placed and region-claimed by the orchestrator per call, so an outer region-lock over the same regions must not wrap it; quiet windows for API traffic are coordinated with the session that owns the measurement",
  "origin": "HS-4 P0.4 run 1, 2026-09-26: outer region-lock over q0-q3 around an OpenCode->/v1 client; every frontdoor call failed 'placement timeout role=frontdoor reason=race_lost holders=[] after 60.0s' (503 contention_denied)",
  "evidence": "handoffs/active/harness-selection-and-integration.md P0.4 (r1 run dir not preserved)",
  "not_changed": "no code, no measurement rule, no other file; section heading unchanged",
  "patch": {"path": patch_rel, "sha256": patch_sha},
  "state": {"agents/shared/OPERATING_CONSTRAINTS.md": {"sha256_before": oc_pre, "sha256_after": oc_post}},
  "consolidated_receipt": consolidated_rel,
  "tracking": {"operator_queue": "handoffs/active/master-handoff-index.md OP-63",
               "handoff_task": "handoffs/active/non-inference-backlog.md HYG-5"},
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
  say "APPLIED, NOT STAGED, NOT COMMITTED (--no-commit). Commit exactly these four paths:"
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
staged_oc="$(GIT_INDEX_FILE="$PIDX" git -C "$ROOT" show ":$OC_REL" | sha256sum | awk '{print $1}')"
[ "$staged_oc" = "$OC_POST_SHA256" ] \
  || die "the staged $OC_REL (${staged_oc:0:12}) does not match its post-state pin: something edited it after postflight. NOT committed."
staged_list="$(GIT_INDEX_FILE="$PIDX" git -C "$ROOT" diff --cached --name-only HEAD | sort)"
expected_list="$(printf '%s\n' "${COMMIT_PATHS[@]}" | sort)"
[ "$staged_list" = "$expected_list" ] \
  || die "the private index holds an unexpected path set; NOT committed. Staged: $(echo $staged_list)"
if GIT_INDEX_FILE="$PIDX" git -C "$ROOT" commit -q -m "$COMMIT_MSG"; then
  git -C "$ROOT" reset -q -- "${COMMIT_PATHS[@]}" \
    || say "  WARNING: 'git reset -q -- <four paths>' failed; run it by hand so the index matches HEAD."
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
  say "    git -C $ROOT push origin $BRANCH     # then land $BRANCH on main"
fi
