# Measurement decision packages — research-intake 2026-08-03

**Status**: awaiting operator decision. Nothing here has been applied.
**Origin**: `/research-intake` Stage-4 on intake-938…990 (Stage-2 dives A–I, Stage-2b dives 2b-A…2b-I).
**Why these are packages and not task lines**: the measurement trust boundary is **human-amendment-only**
(`MEASUREMENT.md`, `agents/shared/MEASUREMENT_POLICY.md`). Each item below changes what a number *means*,
so none of it may be self-applied — including by the AutoKernel loop, which `autokernel-research-loop.md`
§18 rule 6 already bars from writing measurement artifacts at all.

Rendered per the canonical contract (`agents/shared/OPERATING_CONSTRAINTS.md` → *Operator Decision
Requests*): Context · Options · Recommendation · Default. Four packages, independent of one another —
they can be accepted, deferred or declined separately.

---

## DP-1 — MI210 substrate constants and the ridge point as first-class facts

### Context

`autokernel-research-loop.md` §8.3.1 (added 2026-08-03 by the parallel session) defines roofline
utilisation as the normalising metric and requires **two denominators**: datasheet peak, and a *measured*
STREAM-class achievable figure. **Neither denominator exists as a ratified constant anywhere**, and no
peak-FLOPs figure or ridge point existed in any of the six MI210/autokernel handoffs before this batch.
The arithmetic is now derived (intake-960, `mi210-mfma-compute-bound-paths.md`) but it is currently only
handoff prose.

### Options

| Option | Entails | Tradeoffs |
|---|---|---|
| **A. Ratify the derived constants now, marked `[D]`, and the measured denominator later** | Adds 181.0 TFLOPS fp16/bf16 · 181.0 TOPS int8 (no CDNA2 doubling) · fp32 matrix 45.3 / vector 22.6 · **ridge 110.5 FLOP/byte** · `B* = 110.5 × bytes_per_weight / 2`, all tagged derived-from-spec | Cheap and immediately useful; every utilisation figure gets a stated denominator. Risk: a derived constant that is later contradicted by measurement has already been cited. Mitigated by the `[D]` tag and by the fact that `B*` **retro-predicts the already-measured bf16 knee at B≈96–128** |
| **B. Ratify nothing until the STREAM run lands** | Wait for the one-hour achievable-bandwidth measurement (§14 AK1) and ratify both denominators together | Cleanest evidentially. Cost: every roofline claim in flight — including the parallel session's — stays without a denominator until then, and the run needs an operator-approved GPU window it does not yet have |
| **C. Ratify the derived constants AND schedule the STREAM run as its precondition-to-supersede** | A, plus an explicit rule that the measured figure supersedes the spec denominator for optimisation targets once it exists, with both retained | Slightly more ratification text. Removes the "which number do I use" ambiguity permanently |

### Recommendation

**C.** The derived constants are not in doubt — they reproduce AMD's published figures exactly and are
independently checked against a knee we already measured. What *is* in doubt is the denominator, and C is
the only option that names the successor rule up front. It also fixes the specific failure this batch
found in AMD's own KB: their `memory.md` computes a **per-GCD** ridge of 226 FLOP/byte from a **per-OAM**
TFLOPS figure — off by 2× — which is exactly what happens when a constant circulates without a stated
basis.

### Default

No change. The constants stay as `[D]`-marked handoff prose, citable within the kernel handoffs but not
as substrate facts, and §8.3.1's two-denominator rule stays unsatisfiable.

---

## DP-2 — Speedup aggregation: correct-subset harmonic mean, and a prohibition

### Context

We aggregate per-item speedups in several places and have never fixed a rule. Two independent findings in
this batch make the choice consequential rather than stylistic.

### Options

| Option | Entails | Tradeoffs |
|---|---|---|
| **A. `harmonic_mean({s_i : i correct})`, reported beside `correctness_rate`, with harmonic mean over any failure-clamped set FORBIDDEN** | The correct subset is aggregated harmonically; failures are counted, never clamped to a sentinel and folded in | Matches GSO (intake-973), which chose it explicitly over geometric mean citing Jacob & Mudge 1995 and **demonstrated the attack**: "A model achieving speedups of [0.1, 1000] across two tests yields a geometric mean of 10, despite degrading performance on one test ... agents INDEED PERFORM SUCH OPTIMIZATIONS." Cost: two numbers instead of one |
| **B. Keep geometric mean** | Status quo where it is used | Retains a metric with a published gaming demonstration against it |
| **C. Harmonic mean over the full set with failures clamped to a sentinel** | One number, no subset bookkeeping | **This is the specific configuration that must not be used.** SWE-fficiency's headline moved **2.8×** on byte-identical outcomes purely from the choice of clamp constant. A single number whose value is set by a convention rather than by the data |

### Recommendation

**A**, and record the prohibition on C explicitly rather than only choosing A — a future session
reaching for "harmonic mean" without the correct-subset qualifier lands on C by default. Harmonic mean's
asymmetric sensitivity is the property we want (per GSO Appendix E: "we do not want symmetric treatment —
large wins on minor tests shouldn't hurt, only significant regressions matter"), and it is *only* sound
once failures have been removed from the set rather than encoded into it.

### Default

No change. Aggregation stays site-specific and unstated, and the 2.8×-from-a-clamp-constant failure mode
remains available to us.

---

## DP-3 — Paired CI estimators, with a mandatory correction and a named scope limit

### Context

**We compute no variance at all on paired comparisons.** Every model-ladder A/B, kernel arm and config
arm currently reports a point estimate. intake-982 supplies an adoptable closed-form paired-CI recipe.
Two conditions ride with it, and both are load-bearing.

### Options

| Option | Entails | Tradeoffs |
|---|---|---|
| **A. Adopt the closed-form paired CI WITH the small-K correction, composed with intake-939's affine drift correction** | Closed-form intervals on paired comparisons; the `b` correction applied always; arms interleaved in one environment window | Closes a real hole cheaply. **The small-K correction is mandatory, not optional**: without it relative error is ~70% *even at N=2000*, because a 1/(K−1) per-question bias does not average away as N grows — and at our typical K=3–5 it makes the estimate worthless. **Scope limit:** the source models only two noise sources (data, prediction); our dominant hazard is a **third**, environment/machine drift, which pairing does not remove. Adopting it without the affine correction is adopting half the instrument |
| **B. Adopt the closed form and add bootstrapping for safety** | A, plus resampling machinery | Unnecessary: the source's §E **proves** the empirical-variance z, the bootstrap and the sign test agree. Pure cost |
| **C. Decline** | Status quo | Keeps point estimates with no intervals |

### Recommendation

**A**, with both conditions written into the amendment text rather than into a commentary note — the
correction and the scope limit are the parts a later reader will drop.

**A provenance caveat that must ride with adoption and does not affect the choice:** the source's author
is FAIR at Meta *and* a direct SWE-RL co-author of intake-939's senior author. It is adoptable as an
instrument; it may **never** be counted as an independent corroborating leg for intake-939.

### Default

No change. Paired comparisons keep reporting point estimates without intervals.

---

## DP-4 — Right-censoring as a scoring primitive for capped-wall-clock benches

### Context

Every wall-clock-capped bench we run has an implicit and unexamined answer to "what score does a run that
hit the cap get". intake-970 (ENAMEL, ICLR 2025) supplies an explicit one we hold nowhere.

### Options

| Option | Entails | Tradeoffs |
|---|---|---|
| **A. Adopt right-censoring: score → 0 at the cap, never impute the censored value** | The score's dependence on the measurement **vanishes at exactly the point the measurement becomes uninformative** — once the observed time reaches the cap, the clamp makes the score 0 "regardless of the exact value" | Principled and small. Discharges the unknowable magnitude rather than guessing it. **Blocking precondition:** the shipped evaluator runs untrusted generated code in bare subprocesses with a documented inability to kill try/except infinite loops — on a host shared with other sessions' `llama-server` processes that is not runnable as delivered. Adopt the metric, run it under our own isolation |
| **B. Adopt right-censoring AND `eff@k` as the score** | A, plus the unbiased order-statistic estimator (Var ≤ (k/n)·Var[naive]; measured SD 0.02/0.08 vs vanilla 0.20/0.25) | Better variance. But **`eff@k` SATURATES** — a caveat derived from its Eq. 1 and *not stated in the paper*: on the hardest level the ceiling is α/(α−1) = 2 at α=2, so **a 2× and a 1000× score identically**. Unusable where magnitude matters, which for kernel work it does |
| **C. Adopt the Hodges–Lehmann aggregator only** | Median of pairwise means over R repeats, no censoring change | A drop-in with no constitutional implication. Independent of A and can be taken alongside it |

### Recommendation

**A plus C**, and explicitly **not B**. Censoring and robust aggregation are both primitives we lack;
`eff@k`'s saturation makes it the wrong scoring function for anything where we care how much faster.
If A is accepted, the isolation precondition is part of the acceptance, not a follow-up.

### Default

No change. Capped runs keep whatever per-site handling they currently have, unexamined.

---

## Provenance

| Package | Primary source | Verification |
|---|---|---|
| DP-1 | intake-960 (GEAK `perf_knowledge`), intake-964 (LLVM oracle) | dive-verified; constants marked `[D]`, derived not measured |
| DP-2 | intake-973 (GSO), intake-953 (SWE-fficiency clamp sensitivity) | dive-verified / dive-overturned |
| DP-3 | intake-982, composed with intake-939 | dive-verified |
| DP-4 | intake-970 (ENAMEL) | dive-verified |

No number quoted above comes from a `stage1-unverified` entry.
