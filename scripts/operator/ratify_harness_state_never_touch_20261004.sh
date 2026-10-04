#!/bin/bash
# ratify_harness_state_never_touch_20261004.sh — Claude/Codex backup logs and session transcripts, and every
# third-party agent harness's own state, are never a cleanup candidate. Amends agents/shared/OPERATING_CONSTRAINTS.md
# → Destructive operations (human-amendment-only).
#
#   Review (default, writes nothing):    bash scripts/operator/ratify_harness_state_never_touch_20261004.sh
#   Apply + receipts + commit (ONE):     RATIFY_OPERATOR='<your name>' bash scripts/operator/ratify_harness_state_never_touch_20261004.sh --apply --attest RATIFY-HARNESS-STATE-NEVER-TOUCH-20261004
#   Apply + receipts, no commit:         ... --apply --attest RATIFY-HARNESS-STATE-NEVER-TOUCH-20261004 --no-commit
#   Verify the post-state (read-only):   bash scripts/operator/ratify_harness_state_never_touch_20261004.sh --verify
#
# OPERATOR DIRECTIVE (2026-10-04, hard rule): "Claude/codex backup logs should NOT BE TOUCHED UNDER ANY
# CIRCUMSTANCES. They are historical transcripts used by a root filesystem project far more senior to anything
# performed in this project repo." Extended the same day to "opencode and any other 3rd party harness really".
#
# WHAT THE AMENDMENT DOES (artifacts/operator/harness-state-never-touch-20261004.patch) — ADDS one sub-bullet to
# Destructive operations step 1, next to the reference check. It rewrites nothing. The code enforcement already
# landed (root 722b7196 codex_retention_reaper apply permanently disabled; 722b7196 + b639dc8e scratch_cleanup
# NEVER_TOUCH), and so did the agent-writable docs (cleanup-reference-check.md → "Never a candidate",
# autokernel-disk-hygiene-20260915.md §3 item 6, handoff-index-authoring.md § Scratch roots). This bundle lands only
# the doctrine half.
#
# WHY IT NEEDS YOU. agents/shared/*.md is human-amendment-only (coordination/session-bus/human_only_paths.yaml).
# An agent (ak-ds41-main wrap-up subagent) prepared this bundle; only the operator applies it.
#
# PINS. Any mismatch is refused. If the target has moved, REGENERATE the bundle; never force or fuzz.
#   patch                                   see PATCH_SHA256
#   OPERATING_CONSTRAINTS.md   NOT hash-pinned (other bundles may land first); the guard is `git apply --check`
#                              (exact context, no fuzz), the anchor absent before and present exactly once after,
#                              and a diff that only ADDS lines.
#
# IDEMPOTENT. When the target carries the anchor and all three receipts exist, a re-run prints ALREADY RATIFIED and
# exits 0. Every other partial state is refused.
#
# ROOT defaults to the checkout this script lives in. Override it with ROOT=<epyc-root checkout>.
set -euo pipefail

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
ROOT="${ROOT:-$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd)}"
SCRIPT_REL="scripts/operator/ratify_harness_state_never_touch_20261004.sh"

GATE_ID="RATIFY-HARNESS-STATE-NEVER-TOUCH-20261004"
PATCH_REL="artifacts/operator/harness-state-never-touch-20261004.patch"
OC_REL="agents/shared/OPERATING_CONSTRAINTS.md"
CHECKER_REL="scripts/validate/check_ratification_receipts.py"
RECEIPT_REL="artifacts/operator/ratify_harness_state_never_touch_20261004.json"
INDEX_REL="artifacts/operator/receipts/$GATE_ID.json"
CONSOLIDATED_REL="artifacts/operator/ratify_harness_state_never_touch_20261004.receipt.json"
COMMIT_PATHS=("$OC_REL" "$RECEIPT_REL" "$INDEX_REL" "$CONSOLIDATED_REL")
COMMIT_MSG="RATIFIED: Claude/Codex transcripts and every third-party harness state are never a cleanup candidate (${GATE_ID})"

# The one sub-bullet the amendment ADDS; it must exist exactly once afterwards. Nothing is rewritten.
ANCHOR_NEVER="   - **Harness state and session transcripts are never a candidate.** Claude and Codex backup logs and"

PATCH_SHA256="eedb61a000aea875a2a1e25a9b11dc66ab294966302628e6a9d6906545605ff0"
anchors_present() { # prints how many of the anchors occur in the target (0 or 1)
  grep -qF -- "$ANCHOR_NEVER" "$ROOT/$OC_REL" && echo 1 || echo 0
}

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
for f in "$OC_REL" "$PATCH_REL" "$CHECKER_REL" scripts/operator/ratification_receipt.py; do
  [ -f "$ROOT/$f" ] || die "$f not found under ROOT=$ROOT"
done

oc_now="$(sha "$ROOT/$OC_REL")"

# ---------------------------------------------------------------- verify (read-only)
if [ "$MODE" = "verify" ]; then
  ok=1
  [ "$(anchors_present)" = 1 ] || { say "  FAIL  $OC_REL does not carry the amendment anchor"; ok=0; }
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
if [ "$(anchors_present)" = 1 ]; then
  if [ -f "$ROOT/$RECEIPT_REL" ] && [ -f "$ROOT/$INDEX_REL" ] && [ -f "$ROOT/$CONSOLIDATED_REL" ]; then
    say "ALREADY RATIFIED: $OC_REL carries the anchor and all three receipts exist. Nothing to do."
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
printf '  ok    %-44s (%s, not pinned — see PINS)\n' "OPERATING_CONSTRAINTS.md pre-state" "${oc_now:0:12}"
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
[ "$fail" -eq 0 ] || die "preflight failed: $ROOT is not in the state this bundle was prepared against (epyc-root origin/main b639dc8e). Stale checkout: fast-forward it. Moved target: regenerate the bundle. Nothing written."
say "  preflight clean"

if [ "$MODE" = "review" ]; then
  say ""
  say "== amendment diff ($PATCH_REL) =="
  cat "$ROOT/$PATCH_REL"
  say ""
  say "REVIEW ONLY: nothing written. Would amend $OC_REL (one sub-bullet added),"
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
printf '  ok    %-44s (%s)\n' "OPERATING_CONSTRAINTS.md post-state" "${oc_after:0:12}"
if python3 - "$TMPD/oc.bak" "$ROOT/$OC_REL" "$ANCHOR_NEVER" <<'PYEOF'
import difflib, sys
a = open(sys.argv[1], encoding="utf-8").read().split("\n")
b = open(sys.argv[2], encoding="utf-8").read().split("\n")
anchor = sys.argv[3]
diff = list(difflib.unified_diff(a, b, lineterm="", n=0))
removed = [l for l in diff if l.startswith("-") and not l.startswith("---")]
text = "\n".join(b)
ok = True
if removed:
    print(f"  FAIL  the amendment must only ADD lines; {len(removed)} removed"); ok = False
for needle in [anchor, "### Destructive operations — mandatory pre-flight and the trash-first rule\n"]:
    if text.count(needle) != 1:
        print(f"  FAIL  expected exactly one occurrence of: {needle.strip()[:80]!r}"); ok = False
if ok:
    print("  ok    one sub-bullet added, nothing removed; section heading intact")
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
  --protocol-id OPERATING-CONSTRAINTS-HARNESS-STATE-NEVER-TOUCH \
  --anchor "$ANCHOR_NEVER" \
  --ratification-id "$GATE_ID" \
  --script "$SCRIPT_PATH" \
  --operator "$RATIFY_OPERATOR" \
  --no-evidence-reason "operator hard rule stated in chat 2026-10-04, not a measured claim; the code enforcement is root 722b7196 and b639dc8e" \
  --validation "python3 $CHECKER_REL --repo-root ." \
  --validation "test \"\$(sha256sum $OC_REL | cut -d' ' -f1)\" = $oc_after" \
  --validation "test \"\$(grep -c '^### Destructive operations' $OC_REL)\" = 1" \
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
     "$oc_now" "$oc_after" <<'PYEOF'
import json, os, sys
(root, ts, gate, receipt_rel, index_rel, consolidated_rel, operator, patch_rel, patch_sha, script_rel,
 oc_pre, oc_post) = sys.argv[1:13]
doc = {
  "schema": "epyc.operating_constraints_amendment.v1",
  "decision": "HARNESS-STATE-AND-TRANSCRIPTS-NEVER-A-CLEANUP-CANDIDATE",
  "gate_id": gate,
  "operator_decision": "operator hard rule 2026-10-04: Claude/codex backup logs and session transcripts are never touched; extended to every third-party harness state",
  "ratified_at": ts,
  "operator": operator,
  "status": "ratified",
  "target": "agents/shared/OPERATING_CONSTRAINTS.md",
  "section": "Dangerous Operations / Destructive operations, step 1",
  "rule": "Claude/Codex backup logs and session transcripts and every third-party agent harness state (opencode, hermes, Claude share, harness codex homes) are never deleted, moved, truncated, vacuumed or reaped; growth is reported, never reclaimed; the only exception is the operator-approved opencode event-table reaper",
  "origin": "2026-10-04 leak-robustness pass: a codex retention reaper (NIB2-84) would have deleted Codex history; the operator ruled the transcripts serve a senior project outside this repo",
  "evidence": "root 722b7196, b639dc8e (code enforcement)",
  "not_changed": "adds one sub-bullet only; no line rewritten; section heading unchanged",
  "patch": {"path": patch_rel, "sha256": patch_sha},
  "state": {"agents/shared/OPERATING_CONSTRAINTS.md": {"sha256_before": oc_pre, "sha256_after": oc_post}},
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
[ "$staged_oc" = "$oc_after" ] \
  || die "the staged $OC_REL (${staged_oc:0:12}) does not match the postflight state: something edited it after postflight. NOT committed."
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
