#!/bin/bash
# ratify_actor_seat_wire_test_20260926.sh — make "wire-test a new actor seat before any live call" binding
# doctrine in agents/shared/OPERATING_CONSTRAINTS.md.
#
#   Review (default, writes nothing):   bash scripts/operator/ratify_actor_seat_wire_test_20260926.sh
#   Apply + receipt + commit (ONE):     bash scripts/operator/ratify_actor_seat_wire_test_20260926.sh --apply
#   Apply + receipt, no commit:         bash scripts/operator/ratify_actor_seat_wire_test_20260926.sh --apply --no-commit
#
# WHY THIS EXISTS. The operator directed on 2026-09-26 that "project knowledge (not just your Claude
# memories) MUST learn from" the AutoKernel local-planner bring-up (INC-20260926-local-actor-bringup,
# docs/design/autokernel-local-actor-bringup-retro-20260926.md).
#
# What the bring-up cost:
#   - 57.5 h from the first local-planner launch (2026-09-23 18:06Z) to the first measurement (09-26 15:32Z);
#   - 11 run directories, 10 of which scored nothing.
# ~11 of the ~26 incidents were opencode harness semantics, and a scripted fake model server finds each of
# them in seconds with no GPU. Examples: pipe truncation; argv quoting; `prompt:` replacing the system
# prompt; a silent 32000 max_tokens clamp; and a read-only session that ENDS on any `ask`-class permission.
# That fake-server technique was eventually used, live, to find the last of them (research b8d6a046).
#
# The advisory checklist is agent-writable and already landed (docs/guides/agent-workflows/
# agent-loop-design.md → "Bringing up a new actor model or backend"). This amendment makes its first two
# items binding for every autonomous loop, not only AutoKernel. It can only land here, because
# agents/shared/*.md is human-amendment-only.
#
# WHAT THE AMENDMENT DOES (artifacts/operator/actor-seat-wire-test-20260926.patch)
# It adds one new section, "New actor seats — wire-test before any live call", between "The Single Champion"
# and "Retry Policy". Additions only; 0 lines removed or rewritten. The section says:
#   - a new model, backend kind, harness or CLI, or a changed seat config (permissions, prompt transport,
#     limits) takes no live call until its EXACT invocation passes (1) a fake-model wire test and (2) one
#     stub end-to-end dry iteration that covers stop, resume and continuation past a keep;
#   - until the gate exists in code (INF-78 OAB-29/OAB-30), the session bringing the seat up runs both by
#     hand and records the result in the owning handoff.
#
# WHAT IT DOES NOT DO. It changes no code, no measurement rule, and no other file.
# It does not touch MEASUREMENT.md, so it emits no MEASUREMENT.md section-5 consolidated receipt:
# scripts/operator/ratification_receipt.py verifies protocol ids against MEASUREMENT.md, and this is
# operating doctrine, not a measurement protocol. It writes a decision receipt and a keyed index instead,
# as the other doctrine ratifications do.
# It does not touch coordination/session-bus/human_only_paths.yaml, so that file's pin needs no update.
# Nothing here starts a process or takes compute.
#
# PINS. Any mismatch is refused. If the target has moved, REGENERATE the bundle; never force or fuzz.
#   patch                                   bca4267fec385bb7b00b54f9265f2383f9f5e6d7e9a60ce00aa6dc5b87916b9d
#   OPERATING_CONSTRAINTS.md   pre-state    84a7ca73bff7fce2a249ae64c71b0e8e3b42c6153cf1ecc73aca793697f6e8bd
#   OPERATING_CONSTRAINTS.md   post-state   c66ff747a7e235d442fcd72e8dceca23190335624b9237ef339d928acf7359ab
# The pre-state pin matches epyc-root origin/main 5302d271. A stale checkout is refused: fast-forward it first.
#
# COMMIT. --apply commits exactly the three paths below on ROOT's current branch. It commits through a
# private index seeded from HEAD, after re-hashing the staged target against the post-state pin, so nothing
# a peer has staged rides along. Pushing is left to you; the command is printed.
#
# IDEMPOTENT. When the target is at its post-state pin and the receipt and keyed index exist, a re-run
# prints ALREADY RATIFIED and exits 0. Every other partial state is refused.
#
# ROOT defaults to the checkout this script lives in. Override it with ROOT=<epyc-root checkout>.
set -euo pipefail

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
ROOT="${ROOT:-$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd)}"
SCRIPT_REL="scripts/operator/ratify_actor_seat_wire_test_20260926.sh"

PATCH_REL="artifacts/operator/actor-seat-wire-test-20260926.patch"
PATCH="$ROOT/$PATCH_REL"
OC_REL="agents/shared/OPERATING_CONSTRAINTS.md"
GATE_ID="RATIFY-ACTOR-SEAT-WIRE-TEST-20260926"
RECEIPT_REL="artifacts/operator/ratify_actor_seat_wire_test_20260926.json"
INDEX_REL="artifacts/operator/receipts/$GATE_ID.json"
RECEIPT="$ROOT/$RECEIPT_REL"
INDEX="$ROOT/$INDEX_REL"
COMMIT_PATHS=("$OC_REL" "$RECEIPT_REL" "$INDEX_REL")
COMMIT_MSG="RATIFIED: new actor seats are wire-tested against a fake model before any live call (INC-20260926-local-actor-bringup)"

PATCH_SHA256="bca4267fec385bb7b00b54f9265f2383f9f5e6d7e9a60ce00aa6dc5b87916b9d"
OC_PRE_SHA256="84a7ca73bff7fce2a249ae64c71b0e8e3b42c6153cf1ecc73aca793697f6e8bd"
OC_POST_SHA256="c66ff747a7e235d442fcd72e8dceca23190335624b9237ef339d928acf7359ab"

MODE="dry-run"; DO_COMMIT=1
for arg in "$@"; do
  case "$arg" in
    --dry-run)   MODE="dry-run" ;;
    --apply)     MODE="apply" ;;
    --no-commit) DO_COMMIT=0 ;;
    *) echo "usage: $0 [--dry-run | --apply [--no-commit]]   (default: --dry-run, writes nothing)" >&2; exit 64 ;;
  esac
done

say() { printf '%s\n' "$*"; }
die() { printf 'REFUSING: %s\n' "$*" >&2; exit 65; }
sha() { sha256sum "$1" | awk '{print $1}'; }

command -v python3   >/dev/null || die "python3 not on PATH"
command -v sha256sum >/dev/null || die "sha256sum not on PATH"
command -v git       >/dev/null || die "git not on PATH"
[ -f "$ROOT/$OC_REL" ] || die "$OC_REL not found under ROOT=$ROOT"

# ---------------------------------------------------------------- patch pin
[ -f "$PATCH" ] || die "patch not found at $PATCH"
got="$(sha "$PATCH")"
[ "$got" = "$PATCH_SHA256" ] || die "patch hash mismatch: expected $PATCH_SHA256, found $got. The text you reviewed is not the text that would be applied."

# ---------------------------------------------------------------- idempotence / partial states
oc_now="$(sha "$ROOT/$OC_REL")"
if [ "$oc_now" = "$OC_POST_SHA256" ]; then
  if [ -f "$RECEIPT" ] && [ -f "$INDEX" ]; then
    say "ALREADY RATIFIED: $OC_REL is at its post-state pin and $RECEIPT_REL and $INDEX_REL exist. Nothing to do."
    exit 0
  fi
  die "half-applied state: $OC_REL is amended, but the receipt ($([ -f "$RECEIPT" ] && echo present || echo MISSING)) or the keyed index ($([ -f "$INDEX" ] && echo present || echo MISSING)) is not. Resolve by hand."
fi
[ -f "$RECEIPT" ] && die "$RECEIPT_REL already exists, but the target is not amended. Resolve by hand."
[ -f "$INDEX" ]   && die "keyed index $INDEX_REL already exists, so this gate is already spent. Double-signing is refused."

# ---------------------------------------------------------------- preflight
say "== preflight (ROOT=$ROOT, mode=$MODE, commit=$DO_COMMIT) =="
fail=0
if [ "$oc_now" != "$OC_PRE_SHA256" ]; then
  printf '  FAIL  %-44s expected %s\n        %-44s found    %s\n' "OPERATING_CONSTRAINTS.md pre-state hash" "$OC_PRE_SHA256" "" "$oc_now"; fail=1
else
  printf '  ok    %-44s (%s)\n' "OPERATING_CONSTRAINTS.md pre-state hash" "${oc_now:0:12}"
fi
printf '  ok    %-44s (%s)\n' "patch hash" "${PATCH_SHA256:0:12}"
# The commit paths must carry no unrelated edits, staged or unstaged (shared-clone hazard).
dirty="$(git -C "$ROOT" status --porcelain -- "${COMMIT_PATHS[@]}" 2>/dev/null || echo 'GIT-STATUS-FAILED')"
if [ -n "$dirty" ]; then printf '  FAIL  %-44s\n%s\n' "commit paths clean in git" "$dirty"; fail=1
else printf '  ok    %-44s\n' "commit paths clean in git"; fi
if git -C "$ROOT" apply --check "$PATCH" 2>/dev/null; then
  printf '  ok    %-44s\n' "patch applies cleanly (no fuzz)"
else
  printf '  FAIL  %-44s\n' "patch applies cleanly (no fuzz)"; fail=1
fi
[ "$fail" -eq 0 ] || die "preflight failed: $ROOT is not in the state this bundle was prepared against (epyc-root origin/main 5302d271). Stale checkout: fast-forward it first. Moved target: regenerate the bundle. Nothing written."
say "  preflight clean"

if [ "$MODE" = "dry-run" ]; then
  say ""
  say "== amendment diff (${PATCH_REL}) =="
  cat "$PATCH"
  say ""
  say "DRY RUN: would apply the diff above to $OC_REL (post-state pin ${OC_POST_SHA256:0:12}),"
  say "write $RECEIPT_REL and $INDEX_REL, and commit those three paths. Nothing written."
  say "Apply with: ROOT=$ROOT bash $SCRIPT_PATH --apply"
  exit 0
fi

# ---------------------------------------------------------------- apply
RATIFIED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
TMPD="$(mktemp -d)"
trap 'rm -rf "$TMPD"' EXIT
cp "$ROOT/$OC_REL" "$TMPD/OPERATING_CONSTRAINTS.md.bak"
restore() { cp "$TMPD/OPERATING_CONSTRAINTS.md.bak" "$ROOT/$OC_REL"; rm -f "$RECEIPT" "$INDEX"; }

say ""
say "== apply =="
# Working tree only, never --index: staging happens below, into a private index, after postflight.
git -C "$ROOT" apply "$PATCH" || { restore; die "git apply failed; target restored. Nothing changed."; }

# ---------------------------------------------------------------- postflight
say ""
say "== postflight =="
oc_after="$(sha "$ROOT/$OC_REL")"
if [ "$oc_after" != "$OC_POST_SHA256" ]; then
  restore; die "post-state hash mismatch (expected ${OC_POST_SHA256:0:12}, found ${oc_after:0:12}); target restored. Nothing changed."
fi
printf '  ok    %-44s (%s)\n' "OPERATING_CONSTRAINTS.md post-state hash" "${oc_after:0:12}"
if python3 - "$TMPD/OPERATING_CONSTRAINTS.md.bak" "$ROOT/$OC_REL" <<'PYEOF'
import sys, difflib
a = open(sys.argv[1], encoding="utf-8").read().split("\n")
b = open(sys.argv[2], encoding="utf-8").read().split("\n")
removed = [l for l in difflib.unified_diff(a, b, lineterm="", n=0) if l.startswith("-") and not l.startswith("---")]
text = "\n".join(b)
ok = not removed
if removed:
    print(f"  FAIL  {len(removed)} line(s) removed or rewritten; additions only expected")
for needle in ("## New actor seats — wire-test before any live call", "## The Single Champion", "## Retry Policy"):
    if text.count(needle) != 1:
        print(f"  FAIL  expected exactly one occurrence of: {needle!r}"); ok = False
if ok:
    print("  ok    additions only; new section present once; neighbours intact")
sys.exit(0 if ok else 1)
PYEOF
then :; else restore; die "postflight failed: target restored. Nothing changed."; fi
say "  postflight clean"

# ---------------------------------------------------------------- decision receipt + keyed index
if ! python3 - "$RECEIPT" "$INDEX" "$RATIFIED_AT" "$GATE_ID" "$RECEIPT_REL" \
     "${RATIFY_OPERATOR:-${USER:-unknown}}" "$PATCH_SHA256" "$PATCH_REL" "$SCRIPT_REL" \
     "$OC_PRE_SHA256" "$OC_POST_SHA256" <<'PYEOF'
import sys, json, os
(receipt, index, ts, gate, receipt_rel, operator, patch_sha, patch_rel, script_rel, oc_pre, oc_post) = sys.argv[1:12]
doc = {
  "schema": "epyc.operating_constraints_amendment.v1",
  "decision": "NEW-ACTOR-SEATS-WIRE-TESTED-BEFORE-LIVE",
  "gate_id": gate,
  "operator_directive": "2026-09-26: project knowledge (not just Claude memories) MUST learn from the AutoKernel local-planner bring-up retrospective",
  "ratified_at": ts,
  "operator": operator,
  "status": "ratified",
  "target": "agents/shared/OPERATING_CONSTRAINTS.md",
  "section": "New actor seats — wire-test before any live call",
  "rule": "a new model, backend kind, harness/CLI or changed seat config takes no live call until its EXACT invocation passes a fake-model wire test and one stub end-to-end dry iteration (stop, resume, continuation past a keep); until coded (INF-78 OAB-29/OAB-30) the bringing-up session runs both by hand and records the result in the owning handoff",
  "origin": "INC-20260926-local-actor-bringup",
  "evidence": "docs/design/autokernel-local-actor-bringup-retro-20260926.md",
  "not_changed": "no code, no measurement rule, no other file; MEASUREMENT.md untouched, so no section-5 consolidated receipt applies",
  "patch": {"path": patch_rel, "sha256": patch_sha},
  "state": {"agents/shared/OPERATING_CONSTRAINTS.md": {"sha256_before": oc_pre, "sha256_after": oc_post}},
  "tracking": {"handoff_tasks": "handoffs/active/autokernel-orchestrator-actor-backend.md OAB-29, OAB-30"},
  "applied_by": script_rel,
}
with open(receipt, "x", encoding="utf-8") as fh:
    json.dump(doc, fh, indent=2, ensure_ascii=False); fh.write("\n")
os.makedirs(os.path.dirname(index), exist_ok=True)
with open(index, "x", encoding="utf-8") as fh:
    json.dump({"gate_id": gate, "indexed_by": "ratify",
               "receipt": "/workspace/" + receipt_rel,
               "schema_version": "session_bus.receipt_index.v1", "status": "ratified"},
              fh, indent=2, sort_keys=True)
    fh.write("\n"); fh.flush(); os.fsync(fh.fileno())
print(f"  decision receipt: {receipt}")
print(f"  keyed index:      {index}")
PYEOF
then
  restore
  die "could not write the decision receipt or keyed index. Amendment rolled back."
fi

BRANCH="$(git -C "$ROOT" rev-parse --abbrev-ref HEAD)"
if [ "$DO_COMMIT" -eq 0 ]; then
  say ""
  say "APPLIED, NOT STAGED, NOT COMMITTED (--no-commit). Commit exactly these three paths:"
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
  || die "could not seed a private index from HEAD. The amendment and receipt ARE applied (not rolled back). Commit by hand: $commit_manual"
GIT_INDEX_FILE="$PIDX" git -C "$ROOT" add -- "${COMMIT_PATHS[@]}" \
  || die "could not stage into the private index. The amendment and receipt ARE applied (not rolled back). Commit by hand: $commit_manual"
staged_oc="$(GIT_INDEX_FILE="$PIDX" git -C "$ROOT" show ":$OC_REL" | sha256sum | awk '{print $1}')"
[ "$staged_oc" = "$OC_POST_SHA256" ] \
  || die "the staged target does not match its post-state pin (${staged_oc:0:12}): something edited it after postflight. NOT committed; the amendment and receipt are applied in the working tree."
staged_list="$(GIT_INDEX_FILE="$PIDX" git -C "$ROOT" diff --cached --name-only HEAD | sort)"
expected_list="$(printf '%s\n' "${COMMIT_PATHS[@]}" | sort)"
[ "$staged_list" = "$expected_list" ] \
  || die "the private index holds an unexpected path set; NOT committed. Staged: $(echo $staged_list)"
if GIT_INDEX_FILE="$PIDX" git -C "$ROOT" commit -q -m "$COMMIT_MSG"; then
  git -C "$ROOT" reset -q -- "${COMMIT_PATHS[@]}" \
    || say "  WARNING: 'git reset -q -- <three paths>' failed; run it by hand so the index matches HEAD."
  say "  committed $(git -C "$ROOT" rev-parse --short HEAD) on $BRANCH:"
  git -C "$ROOT" show --stat --format='  %s' HEAD | sed 's/^/  /'
else
  die "the commit failed. The amendment and receipt ARE applied in the working tree (not rolled back). Commit by hand: $commit_manual"
fi

say ""
say "RATIFIED and committed. Not pushed. Publish:"
if [ "$BRANCH" = "main" ]; then
  say "    python3 $ROOT/scripts/coordination/serialized_push.py --agent operator --repo $ROOT --fetch --push"
else
  say "    git -C $ROOT push origin $BRANCH     # then land $BRANCH on main"
fi
