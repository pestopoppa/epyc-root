# Dive — divloc — intake-ak-1124

> SOURCE-QUARANTINE: {url: "https://arxiv.org/abs/2608.13756v2", retrieved: "2026-11-24", sha256: "d89880809a0b"}

Stage 2b wave 1 light dive. Bearing entry: exactpaper (intake-2872). Note: arxiv_meta.json and page.txt are v2 (18 Aug 2026), not v1.

## 1. Stage-1 fields

- title: The Integer Alibi: Localizing Cross-Kernel Divergence in INT8-Quantized LLM Inference
- authors: Teng-Ruei Chen (Krixvon, Taipei)
- version/date: arXiv 2608.13756v2, 18 Aug 2026
- categories: quantization, benchmark_methodology, hardware_optimization
- novelty: medium. The phenomenon is known; the contribution is an exact-integer control for one kernel swap with a pre-registered per-layer prediction list.
- relevance: low-medium. It is a localization METHOD for a two-kernel comparison on a W8A8 per-channel-scale INT8 GEMM. Our Q8_0 path is block-scaled with a float cross-block sum, so the central alibi covers only part of it (section 4). It is not a bisection tool and does not replace replicas for gating.
- credibility_score: 1. +1 (<=12 months); +0 not peer-reviewed; +0 known lab; +0 independent corroboration (the closest same-argument result is an ARM dispatch-variant preprint the author cites as concurrent, not read here). Single consumer GPU, vLLM 0.27.1, pre-registered protocol.
- verdict: adopt_patterns. Adopt two patterns: shared-operand per-op replay to localize, and teacher-forced margin analysis. Do not adopt the alibi or the power-of-two probe as such.

## 2. Key claims

0. **INT32 accumulation is exact and order-independent under a no-overflow bound, so the accumulator cannot be the source of a cross-kernel difference (CONFIRMED for per-channel/per-token scaled INT8).** Bound used: 16256*K < 2^31, valid for K <= 132,104. Anchor: page, abstract, "the INT32 dot product is exact and order-independent, so the accumulator cannot be the source of any difference".
1. **Per-layer localization works: identical operands into CUTLASS vs Triton INT8 kernels give bit-identical outputs under power-of-two scales (196/196 layers at 1.7B, 252/252 at 8B) and at most one bf16 spacing under real scales (CONFIRMED; 8B list pinned not blind).** At real scales 188 of 196 layers differ in at least one element. Anchors: page, abstract, "we find bit-identical outputs under power-of-two scales, confirming a pinned prediction list 196/196 and 252/252"; section XII, "188 of 196 layers at least one output element differs".
2. **Two deterministic kernels still disagree end to end: each arm reproduces itself across cold restarts, yet the arms agree on no sequence (0/8, 0/16, 0/64) (CONFIRMED, narrowed).** 1.7B only for the restart check; the 8B and 64-prompt runs were not repeated. Anchor: page, abstract, "the arms agree on no sequence in any end-to-end comparison we ran (0/8, 0/16, and 0/64)".
3. **Logit margin predicts flip risk, ROC-AUC 0.942 on 16,384 teacher-forced positions (CONFIRMED, workload-specific).** Table IV calls it ranked-and-calibrated per workload with no bound implied. Anchor: page, section I contribution 5, "the logit margin predicts flips with ROC-AUC 0.942".
4. **The "localization procedure" is shared-operand differential replay, NOT a per-layer bisection (steering premise OVERTURNED in part).** The method needs two named kernels, captured identical int8 operands per layer, and a seven-check conformance table; there is no automated search for the first diverging op. The authors say first-divergence instrumentation "reached its engine glue and stopped" and a 2.9% same-arm residual is unattributed; the layer-level test uses a single prefill-like tile (M=512) and the decode regime is untested at layer level. Anchors: page, section XI, "the decode regime is untested at layer level"; "None of the conformance checks has been exercised against a deliberately faulty kernel".
5. **Scope limits (CONFIRMED).** The alibi covers the integer GEMM stage only; attention, normalization, rotary and the head stay floating point. One sm_89 GPU, one model family, one engine version. Anchor: page, section XI, "The alibi covers the integer GEMM stage only; attention, normalization, rotary embeddings, and the unquantized head remain floating point".

## 3. Reported results

- Platform: pinned vLLM 0.27.1 (and SGLang by digest), one RTX 4090, Qwen3-1.7B (196 linear layers) and 8B (252).
- Swap: CUTLASS vs Triton INT8 scaled-MM via one env var. End to end: 0/8, 0/16, 0/64 sequences agree at default scales.
- Probe checkpoint (pow2 scales): 8/8 and 16/16 sequences bitwise equal; 2.9% same-arm regime variance residual unattributed.
- Real scales: per-layer diffs at most one bf16 spacing; accumulator observed max 2,374,517 (about 900x below 2^31).
- FP8 contrast: float-accumulator FP8 differences grow with reduction depth (percent level); INT8 stays at parts per million over a 64x K range (one unreplicated sweep).
- Margin: ROC-AUC 0.942 on 16,384 positions (cluster CI over 64 prompts); held-out Brier 0.035.

## 4. Performance-principles table (mechanism and cost model)

| Principle | MI210 gfx90a | Zen 5 EPYC |
|---|---|---|
| Exact INT32 accumulator acquits the reduction stage | PARTIAL: ggml Q8_0 dp4a dots are int32-exact per 32-element block, but each block is scaled by float d_w*d_a and summed in fp32 across blocks and across warps (`mmvq.cu:838` calls it an "fp cross-warp reduction"; skinny adds f32 atomics) (@ 98ff8a4). The accumulation across blocks is a FLOAT accumulator, which is the paper's FP8-like case where differences grow with depth. The alibi acquits only the inner per-block dot | PARTIAL: same block-scaled structure on iqk/AVX-512 VNNI (general knowledge, uncited) |
| Power-of-two scale probe restores bit equality | NO for Q8_0: per-block scales still multiply into an fp32 sum whose order differs between kernels; pow2 scales make products exact but not the cross-block sum once exponents differ. Not an equality restorer here | NO, same reason |
| Shared-operand per-op replay (capture each op's inputs, run reference and candidate kernel, diff outputs) | YES: `examples/eval-callback` and `cb_eval` (`common/common.h:529` @ 98ff8a4) already expose per-node tensors; `test-backend-ops` compares ops (mmvq.cu comment cites MUL_MAT 1103/1103 pass). Port cost: a script that dumps node inputs/outputs and re-executes one node per kernel route | YES, same hook on the CPU backend |
| Teacher-forced replay to separate single-step flips from cascades | YES, ALREADY IN USE: SPEC-ID-NOISE-1 is teacher-forced width-1 vs width-W (`speculative-decoding.md:908 @ f74b175`) | YES, same |
| Margin predicts flip | YES: supports the existing margin-class gate (`spec-identity-gate-protocol.md` section 3 @ f74b175); AUC is workload-specific so not a transferable threshold | same |
| Record which kernel served a result | YES: kernel route per width is env- and shape-dependent (`GGML_HIP_Q8_SKINNY*`, mmvq tables); a verdict should carry it | YES (`GGML_ROWEXACT_N`, iqk routes) |

## 5. In-house state

- No equivalent localization tool in the lane. Identity-gate failures are today attributed by replicas and margin classes (spec-identity-gate-protocol.md sections 2-6 @ f74b175).
- Divergence structure here differs from the paper's: the DFlash2 27B Q8_0 M1-vs-M2 drift is run-to-run on the SAME build (20/64), so the cause is within one kernel set (atomic flush order, parallel_blocks, route) rather than a cross-kernel swap. The paper's cross-kernel replay does not apply; its per-op bitwise diff idea does.
- Kernel route is width-dependent by design (mmvq nwarps by ncols_dst, mmvq.cu:813-850; skinny n 5..16) so width-1 vs width-W comparison always crosses kernels on GPU.
- Not read: mmq bodies, whether an in-tree node-hash dump exists.

## 6. Derived-actionables ledger

| # | Task line | Owner (lane) | Compute | Stop / decision rule |
|---|---|---|---|---|
| D1 (refines exactpaper A7; feeds tmblog T1/T2) | Build a node-hash first-divergence probe: using `cb_eval`, hash every graph node output for two launches of the same 27B DFlash2 np1 config on 3 prompts known to diverge, and report the first node (op name, type, kernel route) whose hash differs | `speculative-decoding.md` (SPEC-ID-NOISE follow-up) | code plus a small GPU row | Question: which op first differs between two launches of the same build, i.e. where the 20/64 launch-to-launch drift enters. Stop-on-answer: same first node in >=2 of 3 prompts. Stop-on-futility: all node hashes equal in every prompt, which would place the drift outside the graph (sampler, argmax, scheduling) and rules out kernel fixes |
| D2 (refines exactpaper A7 / ledger context) | Add the served kernel route (env knobs plus per-width route) to every identity-gate and A/A verdict record | `kernel-champion-and-promotion.md` fold gates (or `speculative-decoding.md` SPEC-ID-GATE protocol) | code/doc-only | Question: can two verdicts be compared only when they ran the same routes. Done when verdict.json carries the route fields |

Declines:
- Decline: the power-of-two scale probe and the INT32 alibi as an equality control for our Q8_0/IQ paths. Specific reason: our scales are per-32 block floats summed in fp32 across blocks and warps, so the accumulator the alibi acquits is only the inner block dot; the paper itself shows the float-accumulator case behaves differently (FP8 contrast).
- Decline: replacing replica-based gating with this method. Specific reason: it localizes where two named kernels differ; it produces no floor and was never exercised against a faulty kernel (limitation 6).

## 7. Dive-surfaced sources

Index grepped unbounded: `2608.13756` 0 hits, `2605.19537` 0 hits (this wave).
- ARM dispatch-variants INT8 equivalence preprint (cited as [27] by the paper) and MarginGate (cited as [28], margin-triggered verification for batch-invariant serving): ABSENT from the index, ids not given in the retained page text. Neither would change D1 or D2. Decline.
- 2611.15671, 2609.04748, 2608.06564, 2604.15409 were surfaced by the exactpaper dive and are not re-surfaced here.

## 8. Contradiction / adversarial pass

- Authors' limitations: one GPU generation, one engine, two kernels, no positive control, decode regime untested at layer level, 2.9% residual unattributed, probe not a validated mitigation.
- The headline "alibi" is a property of the INT8 per-channel scheme; the paper states float-accumulator paths behave differently. Applying it to block-scaled GGUF quantization is an extrapolation by this dive, marked PARTIAL.
- Pre-registration is real for the 1.7B list; the 8B list is pinned after an earlier result was known (authors say so).

## 9. Read depth

read_depth: FULL for sections I-III, X-XII and the abstract; PARTIAL for V-IX tables (layer-level tables read through text only). lane_head: f74b1759ccae8f76ba3d41146d47e687717954a9.

## 10. Artifact audit

artifact audit: clean
