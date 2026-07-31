#!/bin/bash
# REPAIR — MEASUREMENT.md §3, torn bullet at line 83.
#
# RUN BY THE OPERATOR ONLY. MEASUREMENT.md is human-amendment-only.
#
# THIS IS A RESTORATION, NOT AN AMENDMENT. It changes no rule, adds no rule and
# removes no rule. It moves one orphaned continuation line back to the sentence it
# belongs to. Diff after running: the file should differ only by that line moving.
#
# WHAT HAPPENED
#   artifacts/operator/ratify_measurement_amendment_20260731.sh inserted the
#   `category=` block after the line starting with
#       "- Comparisons only within a protocol + instrument version"
#   but that bullet WRAPS onto a second line ("  analysis, labeled as such."). The
#   insert landed between the two, so §3 now reads:
#
#       - Comparisons only within a protocol + instrument version. Cross-protocol comparisons are
#       - **Category (required)**: ...
#         ... 15 lines of category grammar ...
#         analysis, labeled as such.          <-- orphan, 16 lines from its sentence
#
#   The ratification's own verification passed because it grepped for
#   "category=OPTIMUM" — it confirmed the insertion ARRIVED and never checked that
#   the document remained coherent. A check that can only see its own edit cannot
#   detect what that edit broke.
#
# Idempotent: detects the repaired state and exits 0.
set -euo pipefail
cd /workspace
M=MEASUREMENT.md
[ -f "$M" ] || { echo "ABORT: $M not found"; exit 1; }

TORN='- Comparisons only within a protocol + instrument version. Cross-protocol comparisons are'
ORPHAN='  analysis, labeled as such.'

python3 - "$M" "$TORN" "$ORPHAN" <<'PY'
import sys
path, torn, orphan = sys.argv[1], sys.argv[2], sys.argv[3]
lines = open(path, encoding="utf-8").read().split("\n")

try:
    i = next(n for n, l in enumerate(lines) if l == torn)
except StopIteration:
    sys.exit("ABORT: torn bullet not found — file may already differ from the expected state")

if lines[i + 1] == orphan:
    print("  already repaired — orphan already follows its sentence. Nothing to do.")
    sys.exit(0)

try:
    j = next(n for n, l in enumerate(lines) if l == orphan and n > i)
except StopIteration:
    sys.exit("ABORT: orphan line not found; refusing to guess")

if j <= i + 1:
    sys.exit("ABORT: unexpected ordering; refusing to edit")

print(f"  torn bullet at line {i+1}; orphan stranded at line {j+1} ({j-i-1} lines adrift)")
lines.pop(j)
lines.insert(i + 1, orphan)
open(path, "w", encoding="utf-8").write("\n".join(lines))
print("  orphan restored to its sentence")
PY

echo
echo "=== verification (checks COHERENCE, not just presence) ==="
python3 - "$M" <<'PY'
import sys, re
s = open(sys.argv[1], encoding="utf-8").read()
lines = s.split("\n")
ok = True

# 1. the sentence is whole again
i = next((n for n, l in enumerate(lines)
          if l.startswith("- Comparisons only within a protocol")), None)
if i is None or lines[i+1].strip() != "analysis, labeled as such.":
    print("  FAIL: bullet still torn"); ok = False
else:
    print("  OK   §3 comparison bullet is whole")

# 2. the amendment we ratified is still intact
for marker in ("category=OPTIMUM", "category=BASELINE", "category=CANDIDATE",
               "Promotion is decided on the production-optimal"):
    if marker in s: print(f"  OK   amendment intact: {marker}")
    else: print(f"  FAIL: amendment marker LOST: {marker}"); ok = False

# 3. no OTHER orphaned continuation: a top-level bullet must never be immediately
#    followed by a top-level bullet whose predecessor ends in a dangling connective
dangling = re.compile(r"\b(are|is|the|a|an|of|to|and|or|with|that|which|by|for)\s*$")
for n, l in enumerate(lines[:-1]):
    if l.startswith("- ") and dangling.search(l) and lines[n+1].startswith("- "):
        print(f"  WARN line {n+1} may be another torn bullet: {l[-60:]!r}"); ok = False

sys.exit(0 if ok else 1)
PY

echo
echo "REPAIRED. Review with:  git -C /workspace diff -- MEASUREMENT.md"
echo "Expected diff: ONE line moved. Nothing else."
echo "Then:"
echo "  git -C /workspace add -- MEASUREMENT.md"
echo "  git -C /workspace commit -m 'MEASUREMENT: repair torn bullet in §3 (operator)'"
echo "  git -C /workspace push"
