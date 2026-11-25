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

---

# Wrap-up 2 — ~10:05Z onward (autokernel)

## Keeps
- **Small-op fusion** `ak-c22-smallop-fuse-gate-gpu-20261125`: **KEEP_ALL+F1**. Served 27B ms/round 1.031x (95 % CI 1.024-1.039) for ALL (F1 CPY_BATCH + G1 ADD_RMS_NORM + G3 TF2_G3), F1 alone 1.011x (CI 1.003-1.020), KLD 0.0004 (A/A 0.0005, bar 0.003). Added to `/mnt/raid0/llm/tmp/c22-keep-list-20261125.md`; not folded.

## Negatives and corrections
- **Barrier-elide is NOT a gain.** The earlier +0.6-0.7 % was OFF-arm bias. The conv-state +0.5 % is not established.
- **Harness bias found and fixed.** The paired gate ran one resident server per arm, so a +-0.4-0.8 % per-instance offset was confounded with the arm. Fix: a fresh server per visit, warm-up, a parity gate, a balance diagnostic and foreign-pid recording. It was applied to all sibling rows.
- **Checkpoint fast copy closed.** The copy takes 19 ms and the pinned copy is slower. The 0.9 s stall did not reproduce: the API trace shows 57 ms.
- **KV head-contiguous repack not built.** Fetched/useful bytes are 1.00-1.01, so there is nothing to recover.
- **iqk-q8 A3B: FAIL_DIGEST.** mmid-n10 KLD is at the noise floor (the A/A is higher), so its fold waits on an A/A-relative gate.
- **Devhandoff (DEV-INJECT / DEV-SELECT).** The identity failures trace to drafter nondeterminism across a second in-process context (AA diag DIAG_DRAFTER_NONDET). Inject is not the cause. Per the operator's drafter policy, the r6 gate uses output identity. r6 filed FUTILITY_HARNESS_WITNESS (inconclusive) because the d-draft-off arm witnessed the knobs active, so no speed was scored. Its units: sel 200/200; inj output mismatch 2/4 at 54.005 vs 54.267 ms/round; inj+sel 1/4 at 54.055 vs 53.387.

## Findings
- **API trace per-step gaps:** 1.69 ms target to drafter, 1.28 ms drafter to target, 0.65 ms drafter to drafter.
- **Bandwidth straggler review:** `/mnt/raid0/llm/tmp/bw-straggler-review-20261125.md`.
- **Flash-Next weight types** are IQ3_S / IQ4_NL, not uniform IQ4_XS.
- **ub512 vs 2048:** tradeoff analysis done. ub512 stays; the arrival sweep decides.
- **Q38FN host depth** (`ak-q38fn-cpu-hostdepth-perf-20261125`, ATTRIBUTED): host time is 4.13 ms/step at d1k and 11.38 at d32k. The culprit is `llama_kv_cache::get_prev_tokens`, 0.07 -> 3.73 ms/step.

## Operator decisions
- Q38FN ROWEXACT: faster, not lossless.
- The A3B GPU rows are dropped to candidate.
- The MI210 ceiling is 1638 GB/s everywhere.

## Built and queued
- RF7 verify attention (`ak-c22-vattn-rf7-op-gpu-20261125`).
- Q38FN MoE CPU levers: upgate-slab and skinny-balance, greedy and MTP.
- Q38FN host-depth: perf is attributed; the fix is in progress.
- Tail-fuse2 r4. The G2/G6 "never fired" was a test-backend-ops abort, not a non-firing fusion.
- Q38FN served-shape census rows (full and q0q2).
- Arrival sweep r2, now resumable.
- Second-context nondeterminism bisect.

## Process lessons
- Fix a bug class across all sibling rows at once (the harness bias fix).
- Profile the served config before kernel work.
- Make long rows resumable.
- **Incident to note:** a subagent fast-forwarded the shared `/workspace` checkout without the operator's OK. Shared-checkout moves need explicit operator approval; wrap-ups run in a fresh worktree.

## Wrap-up bookkeeping
- **Filed:** `ak-c22-df2-devhandoff-gate-gpu-20261125-r6` (inconclusive) and `ak-q38fn-cpu-hostdepth-perf-20261125` (pass).
- **Ticked:** Q8-SERVED-SMALLOP-FUSE-1.
- **Annotated, not ticked:** DEV-INJECT-1 and DEV-SELECT-1 (their gate lines now point at r6) and Q38FN-CPU-HOST-DEPTH-1.
- **Not filed (no RESULT):** `ak-opperf-cal-27b-gpu-20261125-r3` ended without a RESULT. The other unfiled rows have not ended yet.

Next: autokernel — fix the devhandoff d-draft-off witness leak and re-gate; land the host-depth get_prev_tokens fix and its gate.

---

# Wrap-up 3 — ~11:15Z onward (autokernel, subagent)

## Rows filed this window
| Row | Verdict |
|---|---|
| ak-q38fn-cpu-skinny-balance-greedy-20261125 | KEEP +0.4 % [1.0006, 1.0074], digests identical (C22 keep list, not folded) |
| ak-q38fn-cpu-upgate-slab-greedy / -mtp, ak-q38fn-cpu-skinny-balance-mtp | DROP (CIs straddle 1) |
| ak-q38fn-cpu-conv-state-fwd-20261125 | DROP by rule, effectively inconclusive (sd 0.128, host contention) |
| ak-cpu-a3b-barrier-elide-20261125-r5 | DROP 0.9993 [0.9962, 1.0024]: old +0.6-0.8 % was harness arm bias |
| ak-27b-tail-fuse2-gate-gpu-20261124-r4 | FUTILITY_WITNESS (row witness-parser bug); lever paused (two-strike) |
| ak-c22-q8ip-det-gate-gpu-20261125-r2 | FAIL_PERF_REGRESS: 0 vs 9 mismatches but -6.1 % |
| ak-27b-served-ub-arrival-sweep-gpu-20261125-r2 | SCREENED, ub2048 wins Poisson headlines; replay: max stall 6.87 vs 3.87 s, 127 vs 6 gaps > 2 s; do NOT apply pending ak-27b-served-ub-deepctx-gpu-20261125 |
| ak-q8-hbm-knee-map-gpu-20261125 | LEVER_THROTTLE_NEEDS_KERNEL: knee 16 KB/CU, 89 % at 67 MB, WG count does not help |
| ak-q38fn-cpu-hostdepth-perf-20261125 | ATTRIBUTED to get_prev_tokens (O(context)) |

## Findings
- V5 nondeterminism = float atomics with >= 3 contributors (`/mnt/raid0/llm/tmp/q8ip-second-ctx-mechanism-20261125.md`); "second context" was a red herring. DET for identity/AA arms only.
- HBM knee and the q8wt / knee-batch road: `/mnt/raid0/llm/tmp/q8-gemv-85pct-strategy-20261125.md`.
- Gate-harness lesson: hand-built rows failed most smokes; shared `ak_gate` + `mk_ak_row gate new` now generates gate rows.

## Journal
- epyc-inference-research `a289cbcb6`: `scripts/kernel_rnd/autokernel/loop/program.md` "Learnings 2026-11-25" + 12 unkeyed negatives in `seeds/negatives.json` (unkeyed cap 12 -> 24, operator-approved).

## Handoffs
- Ticked (belief cc): AK-CPU-A3B-BARRIER-ELIDE, Q38FN-CPU-MOE-GEMV-1, SERVED-27B-UB-ARRIVAL-SWEEP, Q8-GEMV-85PCT-1, GPU-27B-SECOND-CONTEXT-NONDET.
- Added: Q8-GEMV-Q8WT-1, Q8-GEMV-KNEE-BATCH-1 (rocm-kernel-authoring), Q8IP-DET2-GATE-1 (kv-cache-program), SERVED-27B-UB-DEEPCTX-1 (akx-program), AK-GATE-HELD-DECLS-1 (autokernel-loop).
- Stale gates fixed: DEV-SELECT-1 / DEV-INJECT-1 gate r6 -> r7; tail-fuse2 note now names r4 and the pause.
- In flight: smallop-fuse2 r2, q8ipdet2, ub deepctx, dtree-headroom-replay, two contamination r2 rows, iqk-q8-decode r3; q8wt and knee-batch kernels building.

Next: autokernel — file the in-flight rows as they end; fold the C22 keep list once every lever row is filed.
