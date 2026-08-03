#!/bin/bash
# DP-2…DP-6 ratification — batched attestation with strikeable items.
#
#   bash artifacts/operator/ratify_measurement_dp2_dp6_20260803.sh --dry-run
#   bash artifacts/operator/ratify_measurement_dp2_dp6_20260803.sh --only DP-2,DP-4
#   bash artifacts/operator/ratify_measurement_dp2_dp6_20260803.sh              # all five
#
# WHY BATCHED, AND WHY STILL SELECTABLE
#   MEASUREMENT_POLICY.md:77-78 asks that queued boundary items be batched into ONE
#   attestation with strikeable lines, to avoid a per-experiment ratification cycle.
#   These five are independent decisions, so --only is the "strikeable" half: take
#   any subset, in any order, and re-run later for the rest. Each item is
#   independently idempotent.
#
# WHAT EACH ITEM DOES
#   DP-2  speedup aggregation: correct-subset harmonic mean; failure-clamped forbidden
#   DP-3  paired CI closed form + MANDATORY small-K correction; no bootstrapping
#   DP-4  right-censoring at a wall-clock cap + Hodges-Lehmann; explicitly NOT eff@k
#   DP-5  Annex K: mechanism-plausibility clause + capability-claim gate
#   DP-6  cross-backend numerical conformance vectors as a first-class instrument
#
#   Full context, options and tradeoffs:
#   artifacts/operator/measurement-decision-packages-20260803.md
#
# NOT COVERED: DP-1, already ratified as MI210-SUBSTRATE-CONSTANTS-1.

set -euo pipefail

ROOT=/mnt/raid0/llm/epyc-root
ORCH=/mnt/raid0/llm/epyc-orchestrator
ANNEX_K="$ROOT/measurement/protocols/kernel-research.md"
DRY_RUN=0
ONLY=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    --only) ONLY="$2"; shift 2 ;;
    -h|--help) sed -n '2,30p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

selected() { [[ -z "$ONLY" ]] || [[ ",$ONLY," == *",$1,"* ]]; }
fail() { printf 'REFUSING: %s\n' "$1" >&2; exit 1; }

[[ -f "$ROOT/MEASUREMENT.md" ]] || fail "MEASUREMENT.md not found"
[[ -f "$ANNEX_K" ]] || fail "Annex K not found at $ANNEX_K"
grep -q 'P-AK-SEARCH-1' "$ANNEX_K" || fail "Annex K lacks P-AK-SEARCH-1; DP-5 has nothing to amend"

emit() {  # id  target_file  marker  body
  local id="$1" target="$2" marker="$3" body="$4"
  selected "$id" || { echo "  SKIP $id (not in --only)"; return 0; }
  if grep -q "$marker" "$target" 2>/dev/null; then
    echo "  ALREADY RATIFIED $id ($marker present) — no change"; return 0
  fi
  if (( DRY_RUN )); then
    echo "  WOULD APPEND $id -> $(basename "$target")"
    printf '%s\n' "$body" | sed 's/^/      | /'
    return 0
  fi
  printf '%s\n' "$body" >> "$target"
  printf -- '- 2026-08-03: %s ratified.\n' "$marker" >> "$ROOT/CHANGELOG.md"
  echo "  RATIFIED $id -> $(basename "$target")"
}

echo "== preconditions =="
# DP-2's amendment asserts an audit result -- that NO site applies a geometric mean
# to SPEEDUPS -- so re-verify it rather than trusting the prose.
#
# A first version of this check flagged file-level CO-OCCURRENCE and fired on 8
# files, all false positives: they pair `completion_probabilities_geomean`
# (confidence calibration) with an unrelated `wall_speedup` ratio, hundreds of lines
# apart, never composed. A crude proxy that blocks wrongly today will pass wrongly
# tomorrow, so this tests PROXIMITY -- what the claim is actually about -- and prints
# what it inspected so the judgement stays reviewable.
PROX_HITS=0
# --include='*.py': .pyc bytecode also matches these tokens and would add noise,
# and binary content could in principle produce a spurious NEAR.
CANDIDATES=$( { grep -rlE --include='*.py' 'geometric_mean|geomean' "$ORCH/src" "$ORCH/scripts" 2>/dev/null || true; } \
              | { xargs -r grep -lE 'speedup' 2>/dev/null || true; } )
while IFS= read -r f; do
  [[ -n "$f" ]] || continue
  near=$(awk '/geomean|geometric_mean/{g[++ng]=NR} /speedup/{s[++ns]=NR}
    END{m=1000000; for(i=1;i<=ng;i++) for(j=1;j<=ns;j++){d=g[i]-s[j]; if(d<0)d=-d; if(d<m)m=d}
        print (m<=20)?1:0}' "$f")
  if [[ "$near" == "1" ]]; then
    echo "  NEAR  $f  (geomean and speedup within 20 lines)"
    PROX_HITS=$((PROX_HITS+1))
  else
    echo "  far   $(basename "$f")  (tokens co-occur but are not composed)"
  fi
done <<< "$CANDIDATES"

if [[ "$PROX_HITS" != "0" ]]; then
  fail "DP-2 asserts no geometric mean is applied to SPEEDUPS, but $PROX_HITS site(s) compose them within 20 lines. Inspect the NEAR lines above and re-audit before ratifying."
fi
echo "  OK  DP-2 audit holds: geomean and speedup never composed (the confidence-calibration geomean is a different quantity)"
echo "  OK  Annex K present with P-AK-SEARCH-1 (DP-5 target)"

echo; echo "== items =="

emit DP-2 "$ROOT/MEASUREMENT.md" "AGGREGATION-SPEEDUP-1" '
## AGGREGATION-SPEEDUP-1 — speedup aggregation (RATIFIED 2026-08-03)

**Rule.** Aggregate per-item speedups as `harmonic_mean({s_i : i correct})`, reported **beside**
`correctness_rate`, never instead of it.

**Forbidden:** a harmonic mean over any set containing failure-clamped sentinel values. Failures are
counted in `correctness_rate`; they are never encoded as a speedup and folded into the aggregate. A
published headline in this literature moved **2.8× on byte-identical outcomes** purely from the choice
of clamp constant — a single number whose value is set by a convention rather than by the data.

**Why harmonic and not geometric.** Harmonic mean punishes slowdowns heavily and nearly ignores large
speedups, which is the asymmetry we want: large wins on minor items should not offset a regression.
Geometric mean is the documented attack surface — `[0.1, 1000]` across two items yields a geometric
mean of 10 while one item regresses, and agents have been shown to perform exactly that optimization.

**SCOPE — this governs speedup and ratio aggregation ONLY.** It does **not** reach the
completion-probability geometric mean used for confidence calibration in the autopilot RLVR path, which
is a different quantity with a different justification. An audit on 2026-08-03 found **zero** sites
applying a geometric mean to speedups, so this rule is **prospective**: it prevents a future choice
rather than correcting a present one. Do not let a future sweep "retire geomean" by grepping the token.
'

emit DP-3 "$ROOT/MEASUREMENT.md" "PAIRED-CI-1" '
## PAIRED-CI-1 — paired confidence intervals (RATIFIED 2026-08-03)

**Rule.** Paired comparisons report a closed-form paired confidence interval, computed **with the
small-K correction**.

**The small-K correction is mandatory, not advisory.** Without it, relative error is roughly **70% even
at N=2000**, because a `1/(K−1)` per-question bias does not average away as N grows. At the K=3–5 reps
this project typically runs, omitting it makes the interval worthless — worse than reporting none,
because it looks like rigour.

**Do not add bootstrapping.** The empirical-variance z statistic, the bootstrap and the sign test are
proven equivalent for this estimator; resampling machinery would add cost and no information.

**What this closes.** Before this rule, paired comparisons reported point estimates with no interval.
`llm_primitives/stat_tests.py` provides `wilson_interval` (a binomial proportion CI) and **no paired
CI** — so this is a genuine gap, not a restatement.

**SCOPE LIMIT, binding.** The estimator models two noise sources: data and prediction. **This
project’s dominant hazard is a third — environment/machine drift — which pairing does NOT remove**
unless both arms are interleaved within one environment window. The affine drift correction that
handles that third source **is not implemented anywhere in this project as of 2026-08-03**. Therefore:
a paired CI computed under this rule is valid for arms interleaved in one window, and **may not be used
to rank close variants across windows** until the drift correction exists. Adopting this alone is half
the instrument, and the half that is missing is the one that bites hardest here.
'

emit DP-4 "$ROOT/MEASUREMENT.md" "CENSORING-1" '
## CENSORING-1 — right-censoring and robust aggregation of repeats (RATIFIED 2026-08-03)

**Rule 1 — right-censoring.** For any benchmark with a wall-clock cap, a run that reaches the cap
scores **0**. The censored magnitude is **never imputed, extrapolated, or replaced by the cap value**.
The principle generalises: *make the score’s dependence on the measurement vanish at exactly the point
the measurement stops being informative.*

**Rule 2 — robust aggregation of repeats.** Aggregate R repeated timings with the **Hodges–Lehmann**
estimator (median of pairwise means) rather than the arithmetic mean. Drop-in, no other implication.

**Explicitly NOT adopted: `eff@k` as a scoring function.** It saturates — a caveat derivable from its
own defining equation and not stated in its source: on the hardest level the ceiling is
`α/(α−1) = 2` at `α = 2`, so **a 2× and a 1000× score identically**. It is unusable wherever magnitude
matters, which for kernel and serving work it does.

**BLOCKING PRECONDITION on any harness adopted to implement Rule 1.** The reference implementation in
the literature executes untrusted generated code in bare subprocesses with a documented inability to
kill `try`/`except` infinite loops. On a host shared with live inference servers that is not runnable
as delivered. **Adopt the rule; run it under our own isolation.**
'

emit DP-5 "$ANNEX_K" "P-AK-SEARCH-1-A1" '
## P-AK-SEARCH-1-A1 — mechanism and capability clauses (RATIFIED 2026-08-03)

Appended to Annex K as a narrowing of `P-AK-SEARCH-1`, which it does not restate or replace.

**Clause 1 — mechanism plausibility.** A banked candidate requires an explanation backed by bytes,
FLOPs, counters, or a clean A/B. *“It got faster and I don’t know why” is a reason to keep measuring,
not to land.* `P-AK-SEARCH-1` as ratified is purely statistical — pass the e-process, clear φ, publish
the MDE — which permits banking a candidate nobody can explain. This clause is directly
anti-reward-hacking and is the cheapest available strengthening of the C6 differentiator.

**Clause 2 — capability-claim gate.** Do not claim that a backend supports a kernel, dtype, quant or
performance tier unless that backend has **both correctness and performance evidence**. This governs
what may be *said* about a backend, not how it is measured — structurally different from every other
gate in this constitution, and the gap this project has actually tripped on: three different answers
for one decode edge case across seven backend sites, undetected because nothing compared them.

**Adopted as SHAPE, not as thresholds.** The source of these clauses pairs them with fixed literal
thresholds (land at ≥3% median, or ≥8–10% with added complexity) and **no statistical test at all** —
median and p20/p80 only. That is materially weaker than `P-AK-SEARCH-1`’s anytime-valid e-processes and
published MDE. **Importing those literals would be a downgrade dressed as an adoption.** They are
explicitly not adopted.
'

emit DP-6 "$ROOT/MEASUREMENT.md" "CONFORMANCE-VECTORS-1" '
## CONFORMANCE-VECTORS-1 — cross-backend numerical conformance vectors (RATIFIED 2026-08-03)

**Decision.** Cross-backend numerical conformance vectors are adopted as a **first-class instrument**.
Instruments touch the measurement trust boundary, which is why this is a ratified decision rather than
a task.

**What the instrument is.** Committed, edge-weighted test vectors that pin a decoder **bit-exactly**
rather than to a tolerance: each case carries the decoded value **and** its exact bit pattern, weighted
to boundaries and to the step either side of them.

**Two design requirements, both load-bearing.**

1. **Dual contracts per format.** Where a spec behaviour and our implementation behaviour legitimately
   differ, they are recorded as **two separate contracts**, so a backend cannot satisfy one by breaking
   the other. This is what lets a compatibility path be recorded as *documented-divergent* rather than
   as a bug.
2. **VERIFIED vs ASSERTED, per row.** Every row names the test that consumes it, or is marked
   `not yet checked`. A backend is conformant only if a test actually consumes the vectors; anything
   else is an observation from reading source and is marked as such.

**What motivated it.** An audit on 2026-08-03 found **three different answers for the same
quantization edge case across seven backend sites** in our own tree — CPU finite, HIP/Metal/SYCL/Vulkan
/OpenCL +Inf, CUDA ≥12.8 NaN. Nothing had compared them **because nothing ran**.

**Known limitation, recorded at adoption.** Hand-written vectors drift — that is the same failure mode
they exist to document. The `VERIFIED`/`ASSERTED` column is what makes the drift visible rather than
silent.
'

echo
if (( DRY_RUN )); then
  echo "--dry-run: nothing written."
else
  echo "Review with:  git -C $ROOT diff"
  echo "Then commit. Re-run with --only to ratify any items skipped this pass."
fi
