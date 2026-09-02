# CPU Decode Roofline Program — non-speculative single-stream qwen4exp

**Status**: NEW — directed by the operator 2026-09-02. Supersedes the single-bet framing of INF-67:
the fused decoder becomes one axis of a roofline program, not the program.
**Created**: 2026-09-02
**Priority**: HIGH — the measured gap is ~10x to roofline and it is not a hardware gap
**Categories**: hardware_optimization, local_inference, moe_optimization, kernel_architecture
**Workstream**: Inference Acceleration
**Parent index**: [`inference-research-index.md`](inference-research-index.md) (row INF-70)
**Related**:
- [`cpu-fused-decoder-blocks.md`](cpu-fused-decoder-blocks.md) (INF-67) — Axis A lives there; this
  handoff owns the framing, the roofline gate, and Axes B/C
- [`cpu-shape-specialized-gemv-decode.md`](cpu-shape-specialized-gemv-decode.md) (INF-10) — the
  four refuted fusion arms and the `GGML_PERF` profile that was prescribed and never run
- [`batched-decode-measurement.md`](batched-decode-measurement.md) — the canonical NUMA recipe
- [`../completed/qwen4exp-uniform-iq4xs-baseline-control.md`](../completed/qwen4exp-uniform-iq4xs-baseline-control.md)
  (INF-68, ratified OP-32) — the artifact rule and the +15.2% quant-mix result

## Scope — read this first

**IN scope**: making a single non-speculative token cheaper on CPU.
**OUT of scope, by operator direction 2026-09-02**:
- **GPU / expert offload** — deferred, not refuted. Do not spend on it.
- **Speculative decoding, MTP, drafters** — the operator's position: *"We can always tack on the
  speculative drafter and get that performance bump. That's easy. I want the agent to tackle
  hard-to-get gains."* A spec-dec multiplier applied to a slow token is still a slow token; this
  program lowers the number it multiplies. (Standing fact for whoever eventually does it: the
  shipped GGUF has **zero `nextn` tensors** and `nextn_predict_layers` is absent — the MTP head was
  dropped in conversion, so spec-dec is not merely untuned but structurally unavailable on this
  artifact. Not this program's problem.)

## The gap, in the only terms that matter

| | measured | source |
|---|---|---|
| decode, **required comparison baseline** (OP-32 opt. B) | **~95 ms/token (10.52 t/s)** | INF-68, uniform IQ4_XS, current box |
| decode, UD-IQ4_XS on the same box | ~110 ms/token (9.13 t/s) | INF-68, same window (+15.2% for uniform) |
| ~~74 ms/token (13.46 t/s)~~ | **DOES NOT REPRODUCE — do not cite** | INF-67 progress 2026-08-31: "needs re-anchoring before any perf claim" |
| of which gemv | ~28 ms | in-situ profiler — directly measured, but on the pre-re-anchor run; carry the build id |
| ~~of which non-gemv ~46 ms~~ | **INVALID — was 74 minus 28** | dies with the anchor; against ~95 ms it would be ~67 ms, but neither is measured. C5 must produce the split directly |
| active bytes/token | ~2.8-3.4 GB | 6B active of 125B, 512 experts / 10 used, ~4.25 bpw |
| **machine DRAM traffic, measured** | **~425 GB/s** | STREAM copy 212 GB/s = 425 GB/s traffic (read+write), progress 2026-08-28 |
| theoretical | 460 GB/s | 12 channels x 4800 MT/s |
| **implied roofline** | **~7.5 ms/token (~133 t/s)** | 3.2 GB read / 425 GB/s |
| **achieved fraction** | **~8%** | 7.5 / 95 (vs the ratified baseline) |

**We convert about a TENTH of this machine's memory bandwidth into tokens.** Decode is a read-only
weight stream, so the denominator is the ~425 GB/s of real traffic the machine demonstrably
sustains — NOT the 212 GB/s STREAM *copy* figure, which counts only the bytes copied and hides the
read half. The operator flagged this margin on 2026-08-28 and it was never pursued: *"clean-room
q8_0 gemv at 79.5GB/s vs the machine's ~425GB/s traffic — plenty of margin."*

**This box has MORE memory bandwidth than a DGX Spark** (~425 GB/s vs ~273 GB/s). On a
bandwidth-bound workload we should be comfortably faster than one, not slower. There is no hardware
excuse anywhere in this gap.

Two independent multipliers, and the previous program pursued only the second:
- **the arithmetic runs far under roofline** (28 ms for 3.2 GB ≈ 114 GB/s aggregate — and the
  expert path is far worse than that, see Axis B);
- **the non-gemv remainder** (Axis A) — its *size* is now unknown: it was 74-28=46, and the 74 is
  retired. Against the re-anchored ~95 ms it is nearer ~67 ms. C5 settles it; until then treat the
  non-gemv cost as "large and unmeasured", not as 46.

Perfect elimination of the non-gemv remainder alone lands at ~28 ms ≈ 36 t/s **if the 28 ms holds
at the re-anchored baseline** — an arithmetic sketch, not a projection, since its input was a
partition of the retired 74. What does NOT depend on the anchor: the arithmetic sits at **27% of
roofline** (28 ms for 3.2 GB = 114 GB/s of 425), because that ratio uses only the profiled gemv
and the measured bandwidth. Both axes together
approach 7.5-15 ms ≈ 66-133 t/s. **Neither axis alone reaches the original 20-60 t/s ambition, and
Axis B is the one with the larger ceiling.**

## Axis A — finish the fused decoder's viability test (INF-67, in flight)

The go/no-go was answered 2026-09-01: the batched `mul_mat` is callable on staged tensors, so the
per-row `vec_dot` in `FusedMM::dot` is a fixable implementation error, not a structural one.

- [ ] **A1 — batched `mul_mat` substitution in `lora_mm`/`FusedMM`** (in flight). **Judge it on the
      gemv column ALONE**: 1141 ms → ~300 ms at 1T is success. Do NOT judge on total —
      see the warning below, it will look like a refutation when it is not.
- [ ] **A2 — scratch arena.** Replace the per-layer `ggml_init`/free (~2.5 GB/token of churn — an
      UNSOURCED estimate from a read of `qwen4exp-fused.cpp`, not a measurement; the sources describe
      the ~215 ms "other" cost only qualitatively, so measure it before quoting it) with
      one reusable arena sized once. This is now HALF the viability case, not a Phase-4 nicety.
- [ ] **A3 — strip the debug I/O** before any timing is reported (112 `fprintf`/`fopen` sites, 67
      `getenv`, several in expert inner loops).
- [ ] **A4 — the safety contract** before any serving exposure: hook becomes OPT-IN
      (`supports_fused_decode()` is unconditionally `true` today with no residency checks), all
      persistent state commits atomically at end-of-token, repack guards on `tensor->extra` + type,
      and remove the `t_logits` write that relies on allocation-ordering luck.

**⚠ The measurement trap on A1, stated because a correct result will look wrong.** With the churn
still present, a *perfect* gemv fix reads: fused ≈ 300 (gemv) + 215 (other) = **~515 ms at 1T vs
the graph's 350 ms** — still 1.5x slower, because the graph's own 1T overhead is only ~50 ms.
Both A1 and A2 are individually fatal; the design needs both. With both, in a CLEAN build at 48
threads: ~28 ms gemv + ~5-15 ms other ≈ **33-43 ms ≈ 23-30 t/s**, which is the original target —
a target computed from pre-re-anchor inputs, so treat it as the ambition to test, never as a
predicted result.
Note the fused/graph ratio is ~3.9x at 1T in the same build and roughly stable across thread
counts — so a same-build 48T comparison is the honest interim check, and the clean-build
projection above is a target, not a measurement.

- [ ] **A-GATE**: fused ≤ graph at 1T on BOTH the gemv column and the other column, **both arms in
      the SAME build**, then re-measure at 48 threads — again same-build — before comparing to the
      re-anchored clean-build baseline from C5 — NOT the 74 ms figure, which does not reproduce.
      Only then does the bit-exactness hunt resume.

## Axis B — the expert path's bandwidth deficit (THE hard gain)

This is independent of the fused decoder and applies to the **graph** as it stands today. It is the
larger of the two multipliers and the least explored.

The record already contains the smoking gun (progress 2026-08-28): the batch-1 `mul_mat_id` expert
gemv was measured at **~5.6-17 GB/s**, and the expert gemv elsewhere at **~40-100 GB/s**, against a
machine that sustains **~425 GB/s**. That is **1.3-4% of roofline on the expert path** — two orders
of magnitude down, which no bandwidth argument can explain. Dense `mul_mat` is far closer. **The MoE gather
is where the bandwidth goes to die**, and 10-of-512 expert selection per token is exactly the
access pattern that would do it.

- [ ] **B1 — split the gemv cost by path and report achieved GB/s, not just ms.** Measure the split
      on the C5 re-anchored run rather than assuming the ~28 ms carries over. Dense `mul_mat` vs
      expert `mul_mat_id`, bytes touched per path per token, achieved GB/s each, against 425. Until
      this exists every other number in this axis is unanchored. (This is INF-10's prescribed
      `GGML_PERF`/symbol profile, still never run.)
- [ ] **B2 — decide the binding constraint: bandwidth or LATENCY?** The 5.6-17 GB/s figure is far
      below any bandwidth explanation, which points at scattered-gather latency, not throughput.
      Test: vary `expert_used_count` (10 → 4 → 2) and see whether time scales with bytes. Scales →
      bandwidth-bound and B3/B4 are wasted effort. Does NOT scale → latency-bound, and the whole
      axis opens up.
- [ ] **B3 — prefetch the selected experts.** The router picks the 10 experts *before* the FFN
      needs them; there is a real window during attention. Issue `__builtin_prefetch` /
      `madvise(WILLNEED)` on the selected expert rows at router time and measure. This is the
      highest-value item if B2 says latency-bound.
- [ ] **B4 — expert weight locality.** Establish whether a single expert's rows are contiguous in
      the GGUF/mapped layout or interleaved with other experts. If interleaved, a 10-expert gather
      touches far more pages than bytes needed, and a per-expert-contiguous repack is worth
      measuring. Note the interaction with `--numa interleave`: page-level striping is right for
      aggregate bandwidth and may be wrong for gather latency — that is a measurable question, not
      a settled one.
- [ ] **B5 — quant choice ON THE EXPERT TENSORS SPECIFICALLY.** Uniform IQ4_XS beat the UD mix by
      **+15.2%** (INF-68) purely by removing dequant-heavy IQ3_S experts from the IQK path. That is
      direct evidence dequant cost is on the critical path. Measure whether an expert-only repack
      (IQ4_NL 8x8 / Q4_0) buys more at equal bpw.

## Axis C — measurement discipline (cheap, and it makes the other two legible)

- [ ] **C1 — report every decode result as achieved GB/s against 425, alongside ms/token.** A
      percentage-of-roofline makes "is this optimization worth it" answerable; a t/s number alone
      does not.
- [ ] **C2 — every instrument gets a sanity assertion before its output is believed.** This
      campaign has produced FOUR self-observation failures: post-compute dumps reading freed
      memory, an eval-callback matching the wrong node, a debug print dereferencing NULL and
      costing a multi-hour crash hunt, and a profiler mis-attributing 90% of what it named. The
      assertion `component <= total && duration >= 0` would have caught the fourth for free.
- [ ] **C3 — hold the BUILD constant, not just the artifact.** OP-32 ratified the rule that a delta
      is measured with the *artifact* identical on both arms; this campaign shows the same applies to
      the *build*. The INF-67 session's own wrap-up records the graph at **8.00 t/s (~125 ms) at -t 48
      in the debug build**. The instrumented build is clearly slower than a clean one, but **the size of
      that penalty is NOT yet measured** — see the correction below. Any fused-vs-graph or
      before-vs-after number that crosses a build boundary is not a measurement.

      What IS safe, and is the model to copy: the session's own **same-build, same-thread control arm**
      — graph 350 ms vs fused 1350 ms, both at `-t 1` in the one debug build. Their progress record
      states the principle exactly: *"same-window ratios are safe."* Ratios inside one window; never
      across two.

      **Worked example, and it is mine.** I told the session the graph gains "4.7x from 1 thread
      (350 ms) to 48 (74 ms)" and used it to extrapolate. That divided a DEBUG-build 1T number by a
      CLEAN-build 48T number. The same-build scaling is **2.8x** (350 → 125 ms, both debug).

      **Then I did it again inside the correction.** My first fix asserted a "1.7x debug penalty" from
      8.00 vs 13.46 t/s — but 13.46 is the very figure the INF-67 record flags as not reproducing on
      this box, so that ratio crossed *both* a build boundary and a dead anchor. On the current box the
      measured baselines are 9.13 t/s (UD) and 10.52 t/s (uniform), so even the direction of a
      "1.7x" is unsupported. **The rule was right and I broke it twice while writing it down.**
      That is why C5 exists: no build-crossing ratio gets asserted until someone measures one.

      What survives, all same-build and same-thread: fused/graph **3.86x** at 1T, and graph thread
      scaling **2.8x** from 1T to 48T. Cite build id and thread count on every row, always.
- [ ] **C5 — RE-ANCHOR THE BASELINE. This gates every absolute number in this program.** The
      74 ms / 13.46 t/s figure is quoted throughout INF-67 and does not reproduce; INF-68 measured
      9.13 t/s (UD) and 10.52 t/s (uniform IQ4_XS) on the current box, and OP-32 option B made the
      uniform artifact the required comparison baseline. Until this is settled, **no absolute
      before/after claim is admissible** — only same-window ratios. Produce, in ONE clean build,
      one thread sweep: graph at `-t 1` and `-t 48`, on the OP-32 uniform artifact, canonical
      recipe (interleave + no-mmap). That single run yields the honest clean baseline, the true
      thread scaling, and — paired with the existing debug numbers — the first *measured*
      instrumentation penalty. Report all three with build id and artifact SHA.
- [ ] **C4 — a control arm for every claim.** The fused path's "84% gemv" was uninterpretable until
      the graph was measured at the same thread count; the control took one run and inverted the
      conclusion. No same-conditions control, no claim.

## Reporting

Non-claims (no protocol id, no attestation) are welcome and expected while exploring — label them.
Anything that gates a keep/revert decision needs the codified recipe and an attestation per
`agents/shared/MEASUREMENT_POLICY.md`, including its **artifact rule** (ratified OP-32): an
absolute headline is the served artifact's number; a delta is measured with the artifact held
identical on both arms. The uniform IQ4_XS file is the required comparison baseline for this model.
