#!/bin/bash
# Completes the DP-5 apply: the cross-reference Annex K's own admission test requires.
#
#   bash artifacts/operator/ratify_annexk_narrowing_xref_20260803.sh --dry-run
#   bash artifacts/operator/ratify_annexk_narrowing_xref_20260803.sh
#
# WHY THIS EXISTS — a defect in the DP-5 packaging, not a new decision.
#   Annex K's narrowing carve-out (test 3) requires that when a rule is narrowed,
#   "the owning annex receives an appended cross-reference IN THE SAME APPLY
#   recording that its rule has been narrowed and by what."
#
#   P-AK-SEARCH-1-A1 landed correctly, but it appears exactly once in the file —
#   in its own heading, 388 lines below the rule it narrows. A reader arriving at
#   P-AK-SEARCH-1 cannot tell it has been narrowed, which is precisely the failure
#   the carve-out exists to prevent. The DP-5 emit should have carried this line;
#   it did not, so the apply is incomplete by the annex's own test.
#
#   This adds ONLY the cross-reference. No rule text changes.

set -euo pipefail

ROOT=/mnt/raid0/llm/epyc-root
ANNEX_K="$ROOT/measurement/protocols/kernel-research.md"
DRY_RUN=0
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

fail() { printf 'REFUSING: %s\n' "$1" >&2; exit 1; }

[[ -f "$ANNEX_K" ]] || fail "Annex K not found"
grep -q '^## P-AK-SEARCH-1 ' "$ANNEX_K" || fail "P-AK-SEARCH-1 heading not found"
grep -q '^## P-AK-SEARCH-1-A1 ' "$ANNEX_K" || fail "P-AK-SEARCH-1-A1 not present — run the DP-5 apply first"

XREF='**NARROWED 2026-08-03 by `P-AK-SEARCH-1-A1`** (this annex, below): a banked candidate additionally requires a mechanism explanation backed by bytes, FLOPs, counters or a clean A/B; and a backend-capability claim additionally requires both correctness and performance evidence. This protocol as stated below is purely statistical and does not carry either requirement on its own.'

if grep -q 'NARROWED 2026-08-03 by' "$ANNEX_K"; then
  echo "Cross-reference already present. No files changed."
  exit 0
fi

if (( DRY_RUN )); then
  echo "WOULD INSERT under the P-AK-SEARCH-1 heading:"
  printf '   | %s\n' "$XREF"
  exit 0
fi

python3 - "$ANNEX_K" "$XREF" <<'PY'
import sys
path, xref = sys.argv[1], sys.argv[2]
s = open(path, encoding='utf-8').read()
h = '## P-AK-SEARCH-1 — Kernel-candidate search authority (RATIFIED 2026-08-03)\n'
assert s.count(h) == 1, 'heading not uniquely found'
s = s.replace(h, h + '\n' + xref + '\n', 1)
open(path, 'w', encoding='utf-8').write(s)
print('cross-reference inserted under the P-AK-SEARCH-1 heading')
PY

printf -- '- 2026-08-03: Annex K narrowing cross-reference added under P-AK-SEARCH-1, completing the P-AK-SEARCH-1-A1 apply per the annex admission test.\n' >> "$ROOT/CHANGELOG.md"
echo "Review with:  git -C $ROOT diff"
