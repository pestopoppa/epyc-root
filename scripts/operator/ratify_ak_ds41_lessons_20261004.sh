#!/bin/bash
# ratify_ak_ds41_lessons_20261004.sh — two pointer bullets in agents/shared/OPERATING_CONSTRAINTS.md that
# turn session ak-ds41-main's private-memory lessons into shared doctrine.
#
#   Review (default, writes nothing):  bash scripts/operator/ratify_ak_ds41_lessons_20261004.sh
#   Apply + section-5 receipt:         RATIFY_OPERATOR=<your-name> bash scripts/operator/ratify_ak_ds41_lessons_20261004.sh --apply
#   Commit:                            printed by --apply (nothing is staged or committed by this script)
#
# ratify-targets: agents/shared/OPERATING_CONSTRAINTS.md
#
# OPERATOR DIRECTIVE (2026-10-04): "your memories provide no value to the project unless they're persisted
# in agent knowledge for all agent sessions." The procedures already landed in agent-writable guides:
#   - docs/guides/agent-workflows/cleanup-reference-check.md   (new; INC-20261004-cleanup-removed-load-bearing-worktree)
#   - docs/guides/agent-workflows/benchmark-analyst.md          → "Your own load, and what counts as noise"
#   - docs/guides/agent-workflows/agent-loop-design.md          → "Campaign scope, hypothesis seeds and
#                                                                  per-model kernels" (needs no doctrine line)
# agents/shared/*.md is human-amendment-only, so the two rules that belong in shared doctrine land here as
# short pointer bullets. Additions only; nothing is removed or rewritten.
#
# THE TWO INSERTIONS (each placed directly after one exact anchor line, which must occur exactly once)
#
#   A. "Destructive operations — mandatory pre-flight", step 1, after the line
#        "     a symlink/bind alias adds nothing."
#      → a "Reference check — idle is not unused" sub-bullet. Origin: INC-20261004-cleanup-removed-load-bearing-worktree — the 2026-10-04 ~02:25Z
#        disk cleanup removed /mnt/raid0/llm/worktrees/root-main-epyc-root-repo (landed, clean, idle 7+ days,
#        no cwd/fd inside), which DS41's launch and watchdog scripts export as EPYC_ROOT_REPO; DS41's next
#        batch claim and two watchdog relaunches died (restored 02:30, relaunched 02:36).
#
#   B. "Inference and Benchmarks", after the line
#        "  print what it saw. (origin: INC-20260929-dry-run-missed-live-checks)"
#      → a "Your own subagents are load; light foreign load is metadata" bullet. Origin: 2026-09-26 and
#        2026-09-30 (subagent pytest during a DS41 floor calibration verified the floor at 4.533% instead of
#        ~1.9%), and the operator's 2026-10-04 ruling that cloud-hosted agent traffic is not poisoning.
#
# IDEMPOTENT. Each insertion is keyed on a marker string. Both present → ALREADY RATIFIED, exit 0. One present
# → that one is skipped and only the other is applied. A missing or duplicated anchor is refused (the target
# has drifted: fast-forward the checkout or re-derive the anchor; never fuzz).
#
# RECEIPT. --apply captures the pre-state, inserts, then emits the MEASUREMENT.md section-5 consolidated
# receipt (scripts/operator/ratification_receipt.py: exact state diff, block-coherence check, validation) to
# artifacts/operator/ratify_ak_ds41_lessons_20261004.receipt.json. A refused receipt restores the target and
# is kept as .refused-<stamp>.receipt.json. It then writes the keyed index
# artifacts/operator/receipts/RATIFY-AK-DS41-LESSONS-20261004.json (refused if it already exists).
#
# WHAT IT DOES NOT DO. No code, no measurement rule, no other file; MEASUREMENT.md, CLAUDE.md and
# human_only_paths.yaml are untouched. It never runs `git add` or `git commit`: in the shared clone a
# whole-file add would sweep a peer's unstaged edit into this amendment, so it saves the isolated hunk and
# prints the exact `git apply --cached` staging command. Nothing starts a process or takes compute.
#
# ROOT defaults to the checkout this script lives in. Override with ROOT=<epyc-root checkout>.
set -euo pipefail

SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
ROOT="${ROOT:-$(cd "$(dirname "$SCRIPT_PATH")/../.." && pwd)}"
SCRIPT_REL="scripts/operator/ratify_ak_ds41_lessons_20261004.sh"
OC_REL="agents/shared/OPERATING_CONSTRAINTS.md"
OC="$ROOT/$OC_REL"
GATE_ID="RATIFY-AK-DS41-LESSONS-20261004"
RECEIPT_TOOL="$ROOT/scripts/operator/ratification_receipt.py"
RECEIPT_REL="artifacts/operator/ratify_ak_ds41_lessons_20261004.receipt.json"
INDEX_REL="artifacts/operator/receipts/$GATE_ID.json"
PATCH_REL="artifacts/operator/ak-ds41-lessons-20261004.applied.patch"
GUIDE_A="docs/guides/agent-workflows/cleanup-reference-check.md"
GUIDE_B="docs/guides/agent-workflows/benchmark-analyst.md"
COMMIT_MSG="RATIFIED: cleanup reference check and own-subagent load rule in OPERATING_CONSTRAINTS (INC-20261004-cleanup-removed-load-bearing-worktree)"

ANCHOR_A='     a symlink/bind alias adds nothing.'
MARKER_A='**Reference check — idle is not unused.**'
BLOCK_A=$(cat <<'EOF'
   - **Reference check — idle is not unused.** Before removing a worktree, checkout, store or
     model, also search live process environments and argv (`/proc/*/environ`, `cmdline`), recent
     launch and watchdog scripts, crontab and campaign state for its path, honour KEEP markers, and
     hold a live run's watchdog first. Procedure: `docs/guides/agent-workflows/cleanup-reference-check.md`.
     (origin: INC-20261004-cleanup-removed-load-bearing-worktree — an approved cleanup removed a landed, clean, 7-day-idle worktree that
     DS41's launchers export as `EPYC_ROOT_REPO`, and DS41's next relaunches died)
EOF
)

ANCHOR_B='  print what it saw. (origin: INC-20260929-dry-run-missed-live-checks)'
MARKER_B='**Your own subagents are load; light foreign load is metadata.**'
BLOCK_B=$(cat <<'EOF'
- **Your own subagents are load; light foreign load is metadata.** Before any measurement,
  including an AutoKernel loop's own floor calibration and A/B phases, pause your subagents' tests
  and builds, wait for their PIDs to exit and confirm quiet with a live `top -bn2`; a pause message
  lands only at the agent's next tool round. A preflight refuses only on heavy local compute (builds,
  benchmarks, local inference, `test-backend-ops`, test suites) and records lighter load, such as
  agent-harness traffic, as run metadata. Procedure: `docs/guides/agent-workflows/benchmark-analyst.md`
  → *Your own load, and what counts as noise*. (origin: 2026-09-30 — subagent pytest during a DS41
  floor calibration verified the floor at 4.533% instead of ~1.9%; operator ruling 2026-10-04)
EOF
)

MODE="dry-run"
for arg in "$@"; do
  case "$arg" in
    --dry-run) MODE="dry-run" ;;
    --apply)   MODE="apply" ;;
    *) echo "usage: $0 [--dry-run | --apply]   (default: --dry-run, writes nothing)" >&2; exit 64 ;;
  esac
done

say() { printf '%s\n' "$*"; }
die() { printf 'REFUSING: %s\n' "$*" >&2; exit 65; }
sha() { sha256sum "$1" | awk '{print $1}'; }

command -v python3   >/dev/null || die "python3 not on PATH"
command -v sha256sum >/dev/null || die "sha256sum not on PATH"
command -v git       >/dev/null || die "git not on PATH"
[ -f "$OC" ] || die "$OC_REL not found under ROOT=$ROOT"
for g in "$GUIDE_A" "$GUIDE_B"; do
  [ -f "$ROOT/$g" ] || die "$g is missing under ROOT=$ROOT; the bullets would point at nothing. Land the guide first."
done
grep -qF "## Your own load, and what counts as noise" "$ROOT/$GUIDE_B" \
  || die "$GUIDE_B lacks the section 'Your own load, and what counts as noise' that insertion B points at."

# ---------------------------------------------------------------- idempotence / anchors
has_a=0; has_b=0
grep -qF "$MARKER_A" "$OC" && has_a=1
grep -qF "$MARKER_B" "$OC" && has_b=1
if [ "$has_a" -eq 1 ] && [ "$has_b" -eq 1 ]; then
  say "ALREADY RATIFIED: both insertions are present in $OC_REL. Nothing to do."
  exit 0
fi
count_line() {  # exact whole-line matches
  python3 - "$OC" "$1" <<'PYEOF'
import sys
lines = open(sys.argv[1], encoding="utf-8").read().split("\n")
print(sum(1 for l in lines if l == sys.argv[2]))
PYEOF
}
say "== preflight (ROOT=$ROOT, mode=$MODE) =="
say "  $OC_REL sha256 $(sha "$OC" | cut -c1-12)"
if [ "$has_a" -eq 0 ]; then
  n="$(count_line "$ANCHOR_A")"; [ "$n" = "1" ] || die "anchor A found $n time(s) in $OC_REL, expected exactly 1: '$ANCHOR_A'. The target has drifted; fast-forward ROOT or re-derive the anchor."
  say "  ok    anchor A unique (Destructive operations, step 1)"
else
  say "  skip  insertion A already present"
fi
if [ "$has_b" -eq 0 ]; then
  n="$(count_line "$ANCHOR_B")"; [ "$n" = "1" ] || die "anchor B found $n time(s) in $OC_REL, expected exactly 1: '$ANCHOR_B'. The target has drifted; fast-forward ROOT or re-derive the anchor."
  say "  ok    anchor B unique (Inference and Benchmarks)"
else
  say "  skip  insertion B already present"
fi

# ---------------------------------------------------------------- build the post-state in a temp file
TMPD="$(mktemp -d)"
trap 'rm -rf "$TMPD"' EXIT
cp "$OC" "$TMPD/before.md"
python3 - "$TMPD/before.md" "$TMPD/after.md" "$has_a" "$ANCHOR_A" "$BLOCK_A" "$has_b" "$ANCHOR_B" "$BLOCK_B" <<'PYEOF'
import sys
src, dst, has_a, anchor_a, block_a, has_b, anchor_b, block_b = sys.argv[1:9]
lines = open(src, encoding="utf-8").read().split("\n")
for present, anchor, block in ((has_a, anchor_a, block_a), (has_b, anchor_b, block_b)):
    if present == "1":
        continue
    idx = [i for i, l in enumerate(lines) if l == anchor]
    if len(idx) != 1:
        sys.exit(f"REFUSING: anchor matched {len(idx)} lines after the earlier insertion: {anchor!r}")
    lines[idx[0] + 1:idx[0] + 1] = block.rstrip("\n").split("\n")
open(dst, "w", encoding="utf-8").write("\n".join(lines))
PYEOF
python3 - "$TMPD/before.md" "$TMPD/after.md" <<'PYEOF' || die "transform check failed; $OC_REL untouched."
import sys, difflib
a = open(sys.argv[1], encoding="utf-8").read().split("\n")
b = open(sys.argv[2], encoding="utf-8").read().split("\n")
removed = [l for l in difflib.unified_diff(a, b, lineterm="", n=0) if l.startswith("-") and not l.startswith("---")]
if removed or len(b) <= len(a):
    sys.exit(f"  FAIL  additions only expected; {len(removed)} line(s) removed")
print(f"  ok    additions only (+{len(b) - len(a)} lines)")
PYEOF
diff -u --label "a/$OC_REL" --label "b/$OC_REL" "$TMPD/before.md" "$TMPD/after.md" > "$TMPD/amend.patch" || true

if [ "$MODE" = "dry-run" ]; then
  say ""
  say "== amendment diff =="
  cat "$TMPD/amend.patch"
  say ""
  say "DRY RUN: nothing written. Apply with:"
  say "    RATIFY_OPERATOR=<your-name> ROOT=$ROOT bash $SCRIPT_PATH --apply"
  exit 0
fi

# ---------------------------------------------------------------- apply
source "$(dirname "$SCRIPT_PATH")/lib/ratify_operator.sh"
ratify_require_operator
[ -f "$RECEIPT_TOOL" ] || die "section-5 receipt tool missing at $RECEIPT_TOOL; nothing written."
[ -e "$ROOT/$RECEIPT_REL" ] && die "$RECEIPT_REL already exists, but the target is not fully amended. Resolve by hand."
[ -e "$ROOT/$INDEX_REL" ]   && die "keyed index $INDEX_REL already exists, so this gate is spent. Double-signing is refused."
python3 "$RECEIPT_TOOL" capture --repo-root "$ROOT" --state "$OC_REL" --out "$TMPD/pre.json" \
  || die "could not snapshot the pre-amendment state; nothing written."
# The target must not have moved since the temp post-state was built from it.
[ "$(sha "$OC")" = "$(sha "$TMPD/before.md")" ] || die "$OC_REL changed during preflight; nothing written. Re-run."

cat "$TMPD/after.md" > "$OC"
say "APPLIED to $OC_REL (sha256 $(sha "$OC" | cut -c1-12))."

restore() { cat "$TMPD/before.md" > "$OC"; }
receipt_rc=0
anchors=()
[ "$has_a" -eq 0 ] && anchors+=(--anchor "$MARKER_A")
[ "$has_b" -eq 0 ] && anchors+=(--anchor "$MARKER_B")
python3 "$RECEIPT_TOOL" emit --repo-root "$ROOT" --pre "$TMPD/pre.json" \
  --protocol-id AK-DS41-LESSONS-20261004 "${anchors[@]}" \
  --ratification-id ak-ds41-lessons-20261004 \
  --script "$SCRIPT_PATH" \
  --no-evidence-reason "operating-doctrine pointers to agent-writable guides ($GUIDE_A; $GUIDE_B); origin incidents cited inline (INC-20261004-cleanup-removed-load-bearing-worktree in docs/reference/agent-config/INCIDENT_LOG.md); not a measured claim" \
  --validation "grep -cF '$MARKER_A' $OC_REL" \
  --validation "grep -cF '$MARKER_B' $OC_REL" \
  --operator "$RATIFY_OPERATOR" \
  --out "$ROOT/$RECEIPT_REL" || receipt_rc=$?
if [ "$receipt_rc" -ne 0 ]; then
  refused="$ROOT/${RECEIPT_REL%.receipt.json}.refused-$(date -u +%Y%m%dT%H%M%SZ).receipt.json"
  [ -f "$ROOT/$RECEIPT_REL" ] && mv "$ROOT/$RECEIPT_REL" "$refused"
  restore
  printf 'REFUSING: section-5 receipt returned %s (1 REFUSED, 2 COULD-NOT-CHECK). %s restored; receipt kept at %s.\n' \
    "$receipt_rc" "$OC_REL" "${refused#"$ROOT"/}" >&2
  exit 70
fi

if ! python3 - "$ROOT/$INDEX_REL" "$GATE_ID" "$ROOT/$RECEIPT_REL" <<'PYEOF'
import json, os, sys
index, gate, receipt = sys.argv[1:4]
os.makedirs(os.path.dirname(index), exist_ok=True)
with open(index, "x", encoding="utf-8") as fh:
    json.dump({"gate_id": gate, "indexed_by": "ratify", "receipt": receipt,
               "schema_version": "session_bus.receipt_index.v1", "status": "ratified"},
              fh, indent=2, sort_keys=True)
    fh.write("\n"); fh.flush(); os.fsync(fh.fileno())
PYEOF
then
  restore
  mv "$ROOT/$RECEIPT_REL" "$ROOT/${RECEIPT_REL%.receipt.json}.refused-index-$(date -u +%Y%m%dT%H%M%SZ).receipt.json"
  die "could not write the keyed index; $OC_REL restored and the receipt set aside."
fi
cp "$TMPD/amend.patch" "$ROOT/$PATCH_REL"

say ""
say "Receipt:      $RECEIPT_REL"
say "Keyed index:  $INDEX_REL"
say "Isolated hunk saved: $PATCH_REL"
say ""
say "NOTHING IS STAGED. Stage only this amendment (the index keeps any peer edit to the file out):"
say "    git -C $ROOT apply --cached $PATCH_REL"
say "    git -C $ROOT add -- $RECEIPT_REL $INDEX_REL $PATCH_REL"
say "    git -C $ROOT diff --cached --stat      # expect exactly these four paths, additions only"
say "    git -C $ROOT commit -m '$COMMIT_MSG'"
