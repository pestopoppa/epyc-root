# 2026-11-25 — AutoKernel overnight churn (2026-11-24 → 25), wrap-up

Session: autokernel (operator-invoked `/wrap-up`). Lever rows: `/mnt/raid0/llm/tmp/ak-lever-rows-20261124.txt`.
C22 keep inputs: `/mnt/raid0/llm/tmp/c22-keep-list-20261125.md`. No fold was started.

## Keeps
- **i8pc**, the HIP int8 per-channel GEMM (`ak-c22-i8pc-gate-gpu-20261124-r6`): served e2e 1.0565 [1.038, 1.076] over 9 rounds (+5.7 %). Op geomean 1.088, KLD 0.000919.
- **Q38FN draft window r6** (`ak-q38fn-draftwin-c22-cpu-20261124-r6`): +16.2 % at 64k context.
- **mmid-n10**, the `mm_ids_helper<10>` (`ak-mmid-n10-gate-gpu-20261124-r2`): the helper is 0.365x (2.7x faster), and pp N10/C21 is 1.026-1.06.
  - The +1.2 % info PPL needed a KLD check. KLD row `ak-mmid-n10-kld-gpu-20261125` filed FAIL_KLD under the fixed 0.003 rule.
  - N10 is still at the noise floor: the C21 A/A KLD is higher than N10's on both models (A3B 0.00495 vs 0.00322; Q38FN 0.0321 vs 0.0313).
  - The fold is blocked until an A/A-relative KLD gate exists. This is not a drop.
- **q8wp in-place** (`ak-c22-q8wp-e2e-gpu-20261125`): tok/s 1.0095 [1.003, 1.016], about +1 % served. The op gate showed 1.32x, but it was measured against stock q8wv, not V5I.

## Small keeps
- **conv-state** (`GGML_CONV_STATE_FWD=1`): about +0.5 %. r4 is queued to confirm it.
- **barrier-elide** (`GGML_TINY_SOLO_MAX=32768`, `ak-cpu-a3b-barrier-elide-20261125-r3`): +0.64 % [+0.36, +0.92], digests identical.
  - r3 ended FUTILITY_HARNESS_CONTENTION. The contention was real memory pressure: four concurrent 88 GB non-mmap Q38FN dry runs at 09:52Z.
  - r4 is rerunning.

## Negatives
- **RF5 and RF6 verify attention** (filed FUTILITY_OP_BELOW_1_2 and _1_5): the plateau is about 350-400 GB/s at kv >= 32k, 21-24 % of the 1638 GB/s peak. The Little's-law in-flight-bytes model is refuted.
- **Other levers that did not pay:** actquant fuse, stochastic acceptance, qmatch, and q4_0 KV.
- **Q8 w8 GEMV designs 1-4:** design 4 is FUTILITY_OP_BELOW_1_05, at MW2 0.478x and MW4 0.304x.
- **Checkpoint pinned copy:** the copy takes 19 ms, so it is not the cause of the stall.
- **27B tail-fuse2 r3:** FUTILITY_WITNESS. Only G3 fuses; G2 and G6 never fire.
- **Q38FN ROWEXACT variants** (`ak-q38fn-rowexact-variants-cpu-20261125`): COST_FAIL. RX32 and RX64 are lossless but run spec at 0.937x and 0.946x.

## Findings
- **Served-decode profile:** weights are 44 % of the step and real idle is about 6 %. The served V5I q8mf already runs at about 62 % of peak.
- **Served API trace** (`ak-27b-served-api-trace-gpu-20261125-r2`, ATTRIBUTION_COMPLETE):
  - Boundary gaps per verify step are 1.69 ms (target to drafter, mostly D2H memcpy), 1.28 ms (drafter to target) and 0.65 ms (drafter to drafter).
  - There is also a 57 ms pre-first-verify gap per request.
- **ROWEXACT_N=32** makes Q38FN spec greedy-lossless at a cost of about -6 to -14 % spec speed. **Operator 2026-11-25: FASTER, not lossless.** Q38FN-ROWEXACT-SPEC-COST-1 is closed.
- **ub sweep:** ub512 stays. An arrival-rate sweep is queued.
- **np4 slot reuse** is clean (`ak-df2-np4-slot-reuse-confirm-gpu-20261125`).
- **Q6K qdec bound** is merged.
- **A3B CPU KLD floor** (`ak-a3b-cpu-kld-floor-20261124-r2`): the A/A and noop floor is 0.0, so the gate stays at 0.003. C21 vs v10 reads 0.003024.

## Process lessons
- **Measure the served baseline before kernel work.** The w8 designs targeted stock q8wv, but production serves V5I, which was already about 62 % of peak.
- **Fix a bug class across all sibling rows in one pass,** not row by row.
- **Never ack a resumable row's own pause.** An rc=75 resume is not a terminal receipt.
- **Watch for priority inversions.** Long quiet rows starved short decisive gates.
- **Concurrent measuring rows must sit on opposite IO-die halves** (q0/q1 vs q2/q3), and builds stay off a measuring half. This is now in `docs/guides/agent-workflows/agent-loop-design.md`.

## Wrap-up bookkeeping
- **Filed:** ak-27b-tail-fuse2-gate-gpu-20261124-r3, ak-a3b-cpu-kld-floor-20261124-r2, ak-q38fn-rowexact-variants-cpu-20261125, ak-27b-served-api-trace-gpu-20261125-r2 and ak-mmid-n10-kld-gpu-20261125.
- **Re-anchored:** the c21-fold-a3b-gpu-20261124-r2 register row is now rev 2 at bc14b481a, on main.
