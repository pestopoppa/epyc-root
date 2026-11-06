#!/bin/bash
# human-only: operator ratifies the two token-efficiency doctrine lines (token-audit recs 1-5, agreed 2026-11-06).
# agents/shared/*.md is on coordination/session-bus/human_only_paths.yaml, so no agent edits it.
# Idempotent; refuses if the anchor section moved. Commits with a pathspec; push is printed, not run.
set -euo pipefail

ROOT="${ROOT:-/workspace}"
FILE="$ROOT/agents/shared/OPERATING_CONSTRAINTS.md"
ANCHOR='## Token-Efficiency Operating Rules (operator, 2026-10-05)'
L1='- Every spawn carries model + effort + token budget, or it is a defect.'
L2='- Each wrap-up reports budget fraction per outcome.'

[[ -f "$FILE" ]] || { echo "Refusing: $FILE missing" >&2; exit 1; }
if grep -qxF -- "$L1" "$FILE" && grep -qxF -- "$L2" "$FILE"; then
    echo "Already applied: both lines present."; exit 0
fi
[[ "$(grep -cxF -- "$ANCHOR" "$FILE")" == 1 ]] || { echo "Refusing: anchor heading not found exactly once" >&2; exit 1; }
[[ -z "$(git -C "$ROOT" status --porcelain -- agents/shared/OPERATING_CONSTRAINTS.md)" ]] || {
    echo "Refusing: OPERATING_CONSTRAINTS.md has uncommitted changes" >&2; exit 1; }

python3 - "$FILE" "$ANCHOR" "$L1" "$L2" <<'PY'
import sys
p, anchor, l1, l2 = sys.argv[1:]
lines = open(p).read().split("\n")
i = lines.index(anchor)
j = i + 1
while j < len(lines) and not lines[j].startswith("### "):  # end of the section intro paragraph
    j += 1
lines[j:j] = [l1, l2, ""]
open(p, "w").write("\n".join(lines))
PY

[[ "$(grep -cxF -- "$L1" "$FILE")" == 1 && "$(grep -cxF -- "$L2" "$FILE")" == 1 ]] || { echo "Verify failed" >&2; exit 1; }
[[ "$(git -C "$ROOT" diff --numstat -- agents/shared/OPERATING_CONSTRAINTS.md | awk '{print $1"/"$2}')" == "3/0" ]] || {
    echo "Verify failed: diff is not exactly +3/-0 (2 lines + blank)" >&2; exit 1; }
git -C "$ROOT" commit -m "doctrine: token-efficiency spawn + wrap-up budget lines (operator 2026-11-06, audit recs 1-5)" \
    -- agents/shared/OPERATING_CONSTRAINTS.md
echo "Committed. Push: python3 $ROOT/scripts/coordination/serialized_push.py --agent operator --repo $ROOT --push --fetch"
