#!/bin/bash
# RATIFICATION — measurement amendment: OPTIMUM / BASELINE / CANDIDATE
#
# Applies artifacts/operator/measurement-amendment-baseline-category-20260731.md
# (Annex A, diffs A1-A5) to the human-amendment-only measurement constitution.
#
# RUN BY THE OPERATOR ONLY. MEASUREMENT.md and measurement/protocols/* are
# human-amendment-only (MEASUREMENT.md:4, :101-105, :117-119); an agent proposing
# these edits may not apply them. Running this script IS the act of ratification.
#
# What it changes:
#   A1  MEASUREMENT.md §3   — adds the required `category=` claim-grammar field
#   A2  MEASUREMENT.md §5   — promotion decided on production-optimal alone
#   A3  bench-cpu.md :91-92 — non-production-recipe cells RECORD, do not BLOCK
#   A4  MEASUREMENT.md CHANGELOG entry
#   A5  MEASUREMENT_POLICY.md — the digest gains the rule (it had none)
#
# Idempotent: re-running detects existing markers and skips. Verifies before and
# after, and refuses to write anything if any anchor is missing.
set -euo pipefail

cd /workspace
M=MEASUREMENT.md
B=measurement/protocols/bench-cpu.md
D=agents/shared/MEASUREMENT_POLICY.md
MARK="category=OPTIMUM"

for f in "$M" "$B" "$D"; do
  [ -f "$f" ] || { echo "ABORT: missing $f"; exit 1; }
done

if grep -q "$MARK" "$M" 2>/dev/null; then
  echo "Already ratified — '$MARK' present in $M. Nothing to do."
  exit 0
fi

# MEASUREMENT.md §5 — snapshot before amending. The A1 edit below inserts after a
# line matched by `startswith`, and on 2026-07-31 that line was the FIRST physical
# line of a wrapped bullet: the insert landed inside the bullet and stranded its
# continuation 16 lines away. Nothing in this script could see that, because its
# verification grepped for the marker it had just inserted. The receipt's
# coherence section compares whole blocks before/after and catches it.
ROOT=/workspace
source "$ROOT/scripts/operator/lib/ratify_receipt.sh"
receipt_capture MEASUREMENT.md measurement/protocols/bench-cpu.md agents/shared/MEASUREMENT_POLICY.md

python3 - <<'PY'
import re, sys

def edit(path, anchor, insert, where="after"):
    s = open(path, encoding="utf-8").read()
    if anchor not in s:
        sys.exit(f"ABORT: anchor not found in {path}:\n  {anchor[:90]}")
    if where == "after":
        s = s.replace(anchor, anchor + insert, 1)
    else:
        s = s.replace(anchor, insert + anchor, 1)
    open(path, "w", encoding="utf-8").write(s)
    print(f"  applied -> {path}")

# ---------- A1: MEASUREMENT.md §3 claim grammar ----------
A1_ANCHOR = "- Comparisons only within a protocol + instrument version"
s = open("MEASUREMENT.md", encoding="utf-8").read()
line = [l for l in s.split("\n") if l.startswith(A1_ANCHOR)]
if not line:
    sys.exit("ABORT: A1 anchor bullet not found in MEASUREMENT.md §3")
A1 = "\n" + """- **Category (required)**: every reported measurement declares exactly one of
  `category=OPTIMUM` · `category=BASELINE` · `category=CANDIDATE`.
  - `OPTIMUM` — the best configuration AVAILABLE for that model/role. If no
    speculative draft path exists for the model, the unaccelerated run IS its
    OPTIMUM (e.g. Qwen3-Next-80B-A3B `--spec-type none`); such a row is a headline
    row, NOT a baseline.
  - `BASELINE` — an optimization the model HAS, deliberately switched off.
    Diagnostic only. Appears only under *Addendum — baselines*. Never a headline.
  - `CANDIDATE` — measured, not adopted. Must be labelled so it is never mistaken
    for what production runs.
  An unlabelled measurement is not decision-grade.
  ✅ `ingest_long_context decode 10.12 tok/s, category=OPTIMUM (no draft path exists;
  spec none is optimal) [P-BENCH-1, n=5, 2026-07-31, attest …]`
  ❌ `frontdoor decode 24.92 tok/s, spec-dec off` (no category; reads as a headline,
  is a BASELINE)"""
edit("MEASUREMENT.md", line[0], A1)

# ---------- A2: MEASUREMENT.md §5 governance ----------
A2_ANCHOR = "scoring contracts are read-only for autonomous optimization processes (program.md)."
A2 = "\n" + """- **Promotion is decided on the production-optimal configuration alone.** A regression in a
  `BASELINE`-category measurement is NOT a promotion blocker and MUST NOT be cited as one;
  a `BASELINE` improvement is NOT a promotion argument. Baselines are recorded to quantify
  what an already-adopted optimization buys, and appear only in an addendum. A gate that
  blocks on a non-production arm is defective and is repaired, not waived. Where an
  instrument cannot exercise the role's registered production recipe (e.g. `llama-bench`
  cannot drive speculative decoding), its cells are RECORDED and reported alongside and
  MUST NOT by themselves block promotion. Supersedes the protocol-scoped statement at
  `measurement/protocols/bench-cpu.md:216-220`, which is generalised by this clause."""
edit("MEASUREMENT.md", A2_ANCHOR, A2)

# ---------- A3: bench-cpu.md narrow the blocking semantics ----------
A3_OLD = """- Every required cell must pass before promotion; a failed cell blocks pending repair or an
  explicit operator waiver."""
A3_NEW = """- Every required cell must pass before promotion **where that cell's configuration is the
  role's registered production recipe**. Cells measured under a non-production configuration
  (including any instrument that cannot exercise the role's registered acceleration) are
  RECORDED and reported alongside, and MUST NOT by themselves block promotion; a regression
  confined to such cells is a disclosed observation, not a gate failure. A failed
  production-recipe cell blocks pending repair or an explicit operator waiver."""
s = open("measurement/protocols/bench-cpu.md", encoding="utf-8").read()
if A3_OLD in s:
    open("measurement/protocols/bench-cpu.md", "w", encoding="utf-8").write(s.replace(A3_OLD, A3_NEW, 1))
    print("  applied -> measurement/protocols/bench-cpu.md")
else:
    # tolerate whitespace/wrap drift
    loose = re.compile(r"- Every required cell must pass before promotion;.*?operator waiver\.", re.S)
    if not loose.search(s):
        sys.exit("ABORT: A3 anchor not found in bench-cpu.md")
    open("measurement/protocols/bench-cpu.md", "w", encoding="utf-8").write(loose.sub(A3_NEW, s, count=1))
    print("  applied (loose match) -> measurement/protocols/bench-cpu.md")

# ---------- A4: CHANGELOG ----------
s = open("MEASUREMENT.md", encoding="utf-8").read().rstrip("\n")
s += "\n" + """- 2026-07-31 — AMENDMENT: measurement categories `OPTIMUM`/`BASELINE`/`CANDIDATE` added to §3
  claim grammar; promotion-on-production-optimal clause added to §5 Governance, superseding the
  protocol-scoped rule at `measurement/protocols/bench-cpu.md:216-220`; `bench-cpu.md:91-92`
  narrowed so non-production-recipe cells record but do not block. Origin: repeated wasted
  measurement runs from conflating a spec-off BASELINE with a no-draft-path OPTIMUM.\n"""
open("MEASUREMENT.md", "w", encoding="utf-8").write(s)
print("  applied -> MEASUREMENT.md CHANGELOG")

# ---------- A5: agent digest ----------
A5_ANCHOR = "never for keep/revert/deploy/promote/buy/close decisions."
A5 = "\n" + """
## Category — declare one, always

Every number you report declares exactly one category. Conflating these is the single most
expensive recurring measurement defect in this project.

| Category | What it is | Where it may appear |
|---|---|---|
| `OPTIMUM` | Best config AVAILABLE for that model. **If no draft path exists, the unaccelerated run IS the optimum** (Qwen3-Next-80B: `--spec-type none`). | Headline tables. The ONLY category a promotion may be decided on. |
| `BASELINE` | An optimization the model HAS, switched off. Diagnostic. | *Addendum — baselines* only. Never a headline. |
| `CANDIDATE` | Measured, not adopted. | Labelled as such, never as "what production runs". |

**Promotion is decided on the production-optimal configuration alone.** A BASELINE regression
is not a blocker and must not be cited as one; a BASELINE improvement is not an argument.
If an instrument cannot run the production recipe, its numbers are recorded, not enforced.

Do not exclude a role from a headline because "speculation is off" — check first whether a
draft path exists at all. If none does, that row is an OPTIMUM and belongs in the table."""
edit("agents/shared/MEASUREMENT_POLICY.md", A5_ANCHOR, A5)
PY

echo
echo "=== presence floor (necessary, NOT sufficient) ==="
# Kept as a floor: an amendment whose text did not land is a failure worth
# naming. It is no longer the verification — a presence check passes on a torn
# document, which is precisely what happened here on 2026-07-31.
for pair in "$M:category=OPTIMUM" "$M:Promotion is decided on the production-optimal" \
            "$B:registered production recipe" "$D:Category — declare one, always"; do
  f="${pair%%:*}"; pat="${pair#*:}"
  if grep -qF "$pat" "$f"; then echo "  OK   $f  <- $pat"; else echo "  MISS $f  <- $pat"; exit 1; fi
done

echo
echo "=== consolidated receipt (the verification) ==="
receipt_emit measurement-category-amendment-20260731 "MEASUREMENT.md §3 + §5" \
    --anchor "category=OPTIMUM" \
    --anchor "Promotion is decided on the production-optimal" \
    --script artifacts/operator/ratify_measurement_amendment_20260731.sh

echo
echo "RATIFIED. Review with:  git -C /workspace diff -- MEASUREMENT.md measurement/protocols/bench-cpu.md agents/shared/MEASUREMENT_POLICY.md"
echo "Then commit:"
echo "  git -C /workspace add -- MEASUREMENT.md measurement/protocols/bench-cpu.md agents/shared/MEASUREMENT_POLICY.md artifacts/operator/"
echo "  git -C /workspace commit -m 'MEASUREMENT: ratify OPTIMUM/BASELINE/CANDIDATE amendment (operator)'"
echo "  git -C /workspace push"
