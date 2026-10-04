#!/bin/bash
# ratify_scratch_lifecycle_20261004.sh — scratch lives under the owning handoff's declared roots and is
# cleaned at the wrap-up / /log boundary; downloads go through safe_download.py; subagent briefs name
# their scratch root. Amends agents/shared/OPERATING_CONSTRAINTS.md (human-amendment-only).
#
#   Review (default, writes nothing):    bash scripts/operator/ratify_scratch_lifecycle_20261004.sh
#   Apply + receipts + commit (ONE):     RATIFY_OPERATOR='<your name>' bash scripts/operator/ratify_scratch_lifecycle_20261004.sh --apply --attest RATIFY-SCRATCH-LIFECYCLE-20261004
#   Apply + receipts, no commit:         ... --apply --attest RATIFY-SCRATCH-LIFECYCLE-20261004 --no-commit
#   Verify the post-state (read-only):   bash scripts/operator/ratify_scratch_lifecycle_20261004.sh --verify
#
# OPERATOR DIRECTIVES (2026-10-04, relayed by the coordinator to the leak-robustness subagent):
#   "dispatch a subagent to investigate making workflows more robust to leakage";
#   worktree/scratch cleanup must be "a STEP OF THE WRAP-UP ROUTINE (and the /log checkpoint skill), not a
#   cron job"; "handoff plans should have strict scratch usage requirements so that wrap-up cleanup is as
#   simple and straightforward as possible to verify and execute".
#
# WHY. /mnt/raid0/llm/tmp/disk-audit-20261003/: 265 worktrees in 10 days (215 landed+clean+idle>7d,
# 233 GiB), 9.2 GB of .incomplete stubs, a 35.9 GB joined-but-kept .part2. 2026-10-04: an approved sweep
# removed a landed, clean worktree that a DS41 launcher exported as EPYC_ROOT_REPO; the campaign crashed
# until it was restored.
#
# WHAT THE AMENDMENT DOES (artifacts/operator/scratch-lifecycle-20261004.patch) — ADDS three bullets,
# rewrites nothing:
#   - Filesystem and Storage: scratch lives under the handoff's declared **Scratch** roots and is removed by
#     scripts/system/scratch_cleanup.py at wrap-up Step 7b / /log (worktrees only through
#     scripts/system/worktree_gate.py, plain scratch to the trash); load-bearing paths are DECLARED;
#   - Filesystem and Storage: downloads go through scripts/utils/safe_download.py;
#   - Parallel Subagent Fan-Out: every subagent brief names its scratch root.
# The code, the wrap-up step, the /log note and the authoring-guide contract landed with branch
# lane/leak-robustness-20261004; this bundle lands only the doctrine half.
#
# WHY IT NEEDS YOU. agents/shared/*.md is human-amendment-only (coordination/session-bus/
# human_only_paths.yaml). An agent prepared this bundle; only the operator applies it.
#
# PINS. Any mismatch is refused. If the target has moved, REGENERATE the bundle; never force or fuzz.
#   patch                                   see PATCH_SHA256
#   OPERATING_CONSTRAINTS.md   NOT hash-pinned: another pending bundle (ratify_ak_ds41_lessons_20261004.sh)
#                              inserts into other sections of the same file, and either may land first. The
#                              guard is instead: `git apply --check` (exact context, no fuzz), each anchor
#                              absent before and present exactly once after, and a diff that only ADDS lines.
#
# The bundle emits the MEASUREMENT.md section-5 consolidated receipt over its own amendment (a doctrine
# amendment anchors in its own target), then the decision receipt and keyed index, and commits exactly
# four paths through a private index seeded from HEAD. Pushing is left to you; the command is printed.
#
# IDEMPOTENT. When the target carries all three anchors and all three receipts exist, a re-run prints
# ALREADY RATIFIED and exits 0. Every other partial state is refused.
#
# ROOT defaults to the checkout this script lives in. Override it with ROOT=<epyc-root checkout>.
set -euo pipefail

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
ROOT="${ROOT:-$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd)}"
SCRIPT_REL="scripts/operator/ratify_scratch_lifecycle_20261004.sh"

GATE_ID="RATIFY-SCRATCH-LIFECYCLE-20261004"
PATCH_REL="artifacts/operator/scratch-lifecycle-20261004.patch"
OC_REL="agents/shared/OPERATING_CONSTRAINTS.md"
CHECKER_REL="scripts/validate/check_ratification_receipts.py"
RECEIPT_REL="artifacts/operator/ratify_scratch_lifecycle_20261004.json"
INDEX_REL="artifacts/operator/receipts/$GATE_ID.json"
CONSOLIDATED_REL="artifacts/operator/ratify_scratch_lifecycle_20261004.receipt.json"
COMMIT_PATHS=("$OC_REL" "$RECEIPT_REL" "$INDEX_REL" "$CONSOLIDATED_REL")
COMMIT_MSG="RATIFIED: scratch lives under declared handoff roots and is cleaned at the wrap-up boundary; downloads via safe_download.py (${GATE_ID})"

# The three bullets the amendment ADDS; each must exist exactly once afterwards. Nothing is rewritten.
ANCHOR_SCRATCH="- **Scratch lives under the owning handoff's declared roots, and is cleaned at the boundary.**"
ANCHOR_DOWNLOAD='- **Download through `scripts/utils/safe_download.py`**, never a bare `hf download`/`curl`/`wget`:'
ANCHOR_FANOUT="- **Every subagent brief names its scratch root** — the owning handoff's declared \`**Scratch**:\`"

PATCH_SHA256="164711786bc93f19dfb30e7bd8d8e0329c6407e79544406b5ddf317573b148c7"
anchors_present() { # prints how many of the three anchors occur in the target
  local n=0 a
  for a in "$ANCHOR_SCRATCH" "$ANCHOR_DOWNLOAD" "$ANCHOR_FANOUT"; do
    grep -qF -- "$a" "$ROOT/$OC_REL" && n=$((n + 1))
  done
  echo "$n"
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
  [ "$(anchors_present)" = 3 ] || { say "  FAIL  $OC_REL carries $(anchors_present)/3 amendment anchors"; ok=0; }
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
if [ "$(anchors_present)" = 3 ]; then
  if [ -f "$ROOT/$RECEIPT_REL" ] && [ -f "$ROOT/$INDEX_REL" ] && [ -f "$ROOT/$CONSOLIDATED_REL" ]; then
    say "ALREADY RATIFIED: $OC_REL carries all three anchors and all three receipts exist. Nothing to do."
    exit 0
  fi
  die "half-applied state: $OC_REL is amended but a receipt is missing. Resolve by hand."
fi
[ "$(anchors_present)" = 0 ] || die "half-applied state: $OC_REL carries $(anchors_present)/3 anchors. Resolve by hand."
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
[ "$fail" -eq 0 ] || die "preflight failed: $ROOT is not in the state this bundle was prepared against (epyc-root origin/main ab84e579). Stale checkout: fast-forward it. Moved target: regenerate the bundle. Nothing written."
say "  preflight clean"

if [ "$MODE" = "review" ]; then
  say ""
  say "== amendment diff ($PATCH_REL) =="
  cat "$ROOT/$PATCH_REL"
  say ""
  say "REVIEW ONLY: nothing written. Would amend $OC_REL (three bullets added),"
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
if python3 - "$TMPD/oc.bak" "$ROOT/$OC_REL" "$ANCHOR_SCRATCH" "$ANCHOR_DOWNLOAD" "$ANCHOR_FANOUT" <<'PYEOF'
import difflib, sys
a = open(sys.argv[1], encoding="utf-8").read().split("\n")
b = open(sys.argv[2], encoding="utf-8").read().split("\n")
anchors = sys.argv[3:6]
diff = list(difflib.unified_diff(a, b, lineterm="", n=0))
removed = [l for l in diff if l.startswith("-") and not l.startswith("---")]
text = "\n".join(b)
ok = True
if removed:
    print(f"  FAIL  the amendment must only ADD lines; {len(removed)} removed"); ok = False
for needle in list(anchors) + ["## Filesystem and Storage\n",
                               "## Parallel Subagent Fan-Out — the default working mode of every main\n"]:
    if text.count(needle) != 1:
        print(f"  FAIL  expected exactly one occurrence of: {needle.strip()[:80]!r}"); ok = False
if ok:
    print("  ok    three bullets added, nothing removed; section headings intact")
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
  --protocol-id OPERATING-CONSTRAINTS-SCRATCH-LIFECYCLE \
  --anchor "$ANCHOR_SCRATCH" \
  --anchor "$ANCHOR_DOWNLOAD" \
  --anchor "$ANCHOR_FANOUT" \
  --ratification-id "$GATE_ID" \
  --script "$SCRIPT_PATH" \
  --operator "$RATIFY_OPERATOR" \
  --no-evidence-reason "workflow doctrine, not a measured claim; the disk audit is /mnt/raid0/llm/tmp/disk-audit-20261003/ (outside the repo) and the DS41 EPYC_ROOT_REPO crash is recorded in the 2026-10-04 coordinator relay" \
  --validation "python3 $CHECKER_REL --repo-root ." \
  --validation "test \"\$(sha256sum $OC_REL | cut -d' ' -f1)\" = $oc_after" \
  --validation "test \"\$(grep -c '^## Filesystem and Storage\$' $OC_REL)\" = 1" \
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
  "decision": "SCRATCH-UNDER-DECLARED-HANDOFF-ROOTS-CLEANED-AT-WRAP-UP",
  "gate_id": gate,
  "operator_decision": "operator directives 2026-10-04 (leakage robustness; cleanup is a wrap-up step, not a cron job; strict per-handoff scratch roots)",
  "ratified_at": ts,
  "operator": operator,
  "status": "ratified",
  "target": "agents/shared/OPERATING_CONSTRAINTS.md",
  "section": "Filesystem and Storage; Parallel Subagent Fan-Out",
  "rule": "scratch lives under the owning handoff's declared **Scratch** roots and is removed at wrap-up Step 7b / /log by scripts/system/scratch_cleanup.py (worktrees only via worktree_gate.py, plain scratch to the trash, load-bearing paths declared); downloads go through scripts/utils/safe_download.py; every subagent brief names its scratch root",
  "origin": "2026-10-03 disk audit (265 worktrees in 10 days, 215 landed+clean+idle>7d = 233 GiB; 9.2 GB .incomplete stubs) and the 2026-10-04 DS41 crash after a sweep removed a worktree a launcher exported as EPYC_ROOT_REPO",
  "evidence": "/mnt/raid0/llm/tmp/disk-audit-20261003/ (outside the repo)",
  "not_changed": "adds three bullets only; no line rewritten; section headings unchanged",
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
