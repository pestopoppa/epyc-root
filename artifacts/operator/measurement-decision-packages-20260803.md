# Measurement decision packages — research-intake 2026-08-03

**Status (2026-08-03): ALL SIX RATIFIED.** DP-1 as `MI210-SUBSTRATE-CONSTANTS-1`; DP-2…DP-6 as
`AGGREGATION-SPEEDUP-1`, `PAIRED-CI-1`, `CENSORING-1`, `P-AK-SEARCH-1-A1` (Annex K) and
`CONFORMANCE-VECTORS-1`. DP-6's first instrument ships at
`epyc-inference-research/conformance/` (research `1f5f0bfe`).

**One completion outstanding**: Annex K's narrowing carve-out requires the owning annex to carry a
cross-reference *in the same apply*; the DP-5 emit omitted it, so a reader at `P-AK-SEARCH-1` cannot
tell it has been narrowed. Packaged as
`artifacts/operator/ratify_annexk_narrowing_xref_20260803.sh` — a defect in the packaging, not a new
decision.

_(original status: awaiting operator decision, nothing applied)_
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

### UPDATE 2026-08-03 — the measured denominator now EXISTS, which strengthens option C

The STREAM-class run landed the same day this package was written: **achievable = 1433.3 GB/s, 87.5% of
the 1638 GB/s datasheet peak**; correction factor **1.143×**. Receipt
`epyc-inference-research/data/mi210-achievable-bandwidth/20260803T124401Z/receipt.json`, SHA-256
`0aab9c7e135929e72fd3a5c2498eb807dc16d0f80b773f063e1df3524df7b4d3`, committed `328b768d`. Graded
OBSERVATION; three servers resident and idle, autopilot paused, 0 busy slots, 0% GPU use.

So option C is no longer "ratify derived constants and schedule the measurement" — **both denominators
are available now** and can be ratified together. Two things this changes in the ask:

1. **A third constant joins the set: the ridge point has two bases.** 110.5 FLOP/byte against spec
   bandwidth, **126.3 against measured** — and the second is **mixed-basis** (spec FLOPS ÷ measured
   bandwidth), because the matrix units have not been measured. It must be ratified *with that label*, not
   as a cleaner replacement for the first.
2. **A usage rule belongs in the amendment, not just the numbers.** Use the achievable basis for headroom
   and campaign sizing; use the spec basis for any cross-vendor comparison, and always say which. This is
   not pedantry — converting our own figures to an achievable basis while a competitor's stay on a spec
   basis makes the gap look smaller without it being smaller, and that is the exact error found this
   session in AMD's own KB.

### PACKAGED 2026-08-03 — DP-1 is ready to execute

```bash
bash artifacts/operator/ratify_mi210_substrate_constants_20260803.sh --dry-run   # verify, writes nothing
bash artifacts/operator/ratify_mi210_substrate_constants_20260803.sh             # amend
```

Idempotent; refuses on any precondition failure. It checks that all three receipts are **committed**
(an untracked receipt looks identical to a committed one) and that the constants in the script still
**match the receipts**, so the script cannot drift from its own evidence. Dry-run passes as of
2026-08-03. **Peak FLOPS has since been measured too (172.2 TFLOPS), so the ridge is no longer
mixed-basis — the clean measured-basis value is 120.1 FLOP/byte** and the amendment carries both bases
plus the no-mixing rule.

DP-2…DP-6 are **not** covered by this script — independent decisions with their own options.

**Amended recommendation: still C, now executable in one step.** The estimate that preceded the run
(~1.3–1.4 TB/s, a 17–26% rise) was low — recorded here because a ratified constant should carry the fact
that its predecessor guess was wrong in a knowable direction.

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

## DP-5 — two `P-AK-SEARCH-1` / Annex K amendments: a mechanism clause and a capability-claim gate

### Context

`P-AK-SEARCH-1` was ratified 2026-08-03 and is **purely statistical**: pass the e-process, clear φ,
publish the MDE — and you may bank a candidate **nobody can explain**. A third-party kernel program with
a well-designed contract holds two rules we do not, and one of them is directly anti-reward-hacking,
which is our own named C6 differentiator.

### Options

| Option | Entails | Tradeoffs |
|---|---|---|
| **A. Add both clauses** | (i) **Mechanism-plausibility**: a banked result requires an explanation backed by bytes, FLOPs, counters or a clean A/B — *"'It got faster and I don't know why' is a reason to keep measuring, not to land."* (ii) **Capability-claim gate**: do not claim a backend supports a kernel/dtype/quant/perf-tier unless that backend has **both correctness and performance evidence** | Cheap, and (i) is directly anti-reward-hacking. (ii) is a *capability*-claim gate, structurally different from every measurement gate we hold — it governs what we may say a backend does, not how we measure it. Cost: a real result with no mechanism yet becomes unbankable until explained |
| **B. Add the mechanism clause only** | (i) alone | Takes the anti-hacking half; leaves the capability-claim gap open, which is the one this project has actually tripped on (three different answers for one decode edge case across seven backend sites, undetected) |
| **C. Decline both** | Status quo | Keeps a purely statistical bar on a loop whose whole purpose is autonomous search |

### Recommendation

**A.** Both clauses are cheap and they close different holes. **Adopt the SHAPE only, never the source's
numbers** — its thresholds are fixed literals (3% median low-risk, 8–10% with added complexity) with
**no statistical test at all**, only median and p20/p80. That is materially *weaker* than what we already
have; importing the literals would be a downgrade dressed as an adoption.

### Default

No change. A candidate may be banked on statistics alone with no mechanism, and capability claims stay
ungated.

---

## DP-6 — cross-backend numerical conformance vectors as a new instrument

### Context

A dive found, live in our own tree, **three different answers for the same quantization edge case across
seven backend sites** — CPU yields a finite value, HIP/Metal/SYCL/Vulkan/OpenCL yield +Inf, CUDA ≥ 12.8
yields NaN. Nothing had compared them **because nothing ran**. A ~8 KB MIT artifact (four JSON files)
pins decoders **bit-exactly** rather than to a tolerance, and its central design decision is the one we
would need: the same format appears **twice as two separate contracts** — spec behaviour and ggml
behaviour — *"kept as a separate contract so a backend cannot satisfy one by breaking the other."*

This is an **operator decision, not a task line**, because conformance vectors are a **new instrument**,
and instruments touch the measurement trust boundary.

### Options

| Option | Entails | Tradeoffs |
|---|---|---|
| **A. Adopt cross-backend conformance vectors as a first-class instrument** | Committed edge-weighted vectors (codes 0/1/2/126/127/128/253/254/255), each case carrying the decoded value **and its exact hex bit pattern**; per-format dual contracts; a companion matrix distinguishing **VERIFIED from ASSERTED per row** (each row names the test file that consumes it, or says `not yet checked`) | Catches a defect class we demonstrably have. Its own anti-reward-hacking argument transfers to C6: block positions are pinned because *"swapping the halves leaves the value multiset and the block norm almost unchanged, so a norm-only check passes a wrong decoder."* Cost: a new instrument to maintain, and the source self-indicts — *"until then it is hand-written and will drift, the same failure mode it exists to document"* |
| **B. Adopt the vectors as a test fixture only, with no instrument status** | Same files, run in CI, no trust-boundary implication | Cheaper and needs no amendment. But a fixture nobody registers is a fixture nobody notices has stopped running — which is how the original divergence survived |
| **C. Decline** | Status quo | The three-way divergence stays undetected and legitimate-divergence stays indistinguishable from a bug |

### Recommendation

**A**, and specifically **keep the dual-contract design** — it is what lets the ggml-compat path be
recorded as *documented-divergent* rather than failed, which is the honest description of it. The
`VERIFIED`-vs-`ASSERTED` column is the part that makes the instrument self-reporting: a claim is
conformant only if a test actually consumes the vectors, and everything else is marked as a reading of
the source.

### Default

No change. The divergence remains recorded in the intake index only, where nothing executes against it.

---

## PACKAGED 2026-08-03 — DP-2…DP-6 are ready to execute

```bash
bash artifacts/operator/ratify_measurement_dp2_dp6_20260803.sh --dry-run          # verify, writes nothing
bash artifacts/operator/ratify_measurement_dp2_dp6_20260803.sh --only DP-3,DP-5   # any subset
bash artifacts/operator/ratify_measurement_dp2_dp6_20260803.sh                    # all five
```

**Batched with strikeable items**, per `MEASUREMENT_POLICY.md:77-78` — one attestation rather than a
per-decision ratification cycle, but `--only` takes any subset in any order and each item is
independently idempotent. DP-2/3/4/6 append to `MEASUREMENT.md`; **DP-5 appends to Annex K**
(`measurement/protocols/kernel-research.md`) as a narrowing of `P-AK-SEARCH-1`.

**Two audit findings changed the amendment text before packaging**, and both are recorded in the
amendments themselves rather than only here:

- **DP-2 is PROSPECTIVE, not corrective.** The package said "retire geometric mean where we use it".
  An audit found **zero** sites applying a geometric mean to speedups — the `geomean` hits in the
  orchestrator are all `completion_probabilities_geomean` for *confidence calibration*, a different
  quantity. The amendment now scopes itself explicitly so a future sweep cannot "retire geomean" by
  grepping the token and break calibration.
- **DP-3's scope limit is sharper than stated.** The affine drift correction that handles our dominant
  hazard **is not implemented anywhere**. So the amendment permits paired CIs for arms interleaved in
  one environment window and **forbids** using them to rank close variants across windows until that
  half exists.

The script's own precondition went through the same correction: a first version flagged file-level
co-occurrence of `geomean` and `speedup` and fired on 8 false positives. It now tests **proximity**,
prints every file it inspected, and excludes bytecode. *A crude proxy that blocks wrongly today will
pass wrongly tomorrow.*

## Provenance

| Package | Primary source | Verification |
|---|---|---|
| DP-1 | intake-960 (GEAK `perf_knowledge`), intake-964 (LLVM oracle) | dive-verified; constants marked `[D]`, derived not measured |
| DP-2 | intake-973 (GSO), intake-953 (SWE-fficiency clamp sensitivity) | dive-verified / dive-overturned |
| DP-3 | intake-982, composed with intake-939 | dive-verified |
| DP-4 | intake-970 (ENAMEL) | dive-verified |
| DP-5 | intake-959 (QuixiCore-ROCm perf ledger), intake-944 | dive-verified; adopt the shape, explicitly not the 3% / 8–10% literals |
| DP-6 | intake-944 (conformance vectors), plus the divergence found in our own tree | dive-verified |

No number quoted above comes from a `stage1-unverified` entry.
