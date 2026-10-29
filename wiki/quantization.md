# Quantization

**Category**: `quantization`
**Confidence**: verified (CPU quant findings) · observation (2026-07 MI210 gfx90a roofline numbers — single-run, no P-GPU-1 per MEASUREMENT.md)
**Last compiled**: 2026-10-27 (operator wiki sweep, workspace-58): Q38FN arm P2: the expert-only IQ4_XS requant recovers PPL but fails the speed gate; the recipe is preserved and the GGUF reclaimed. Earlier: 2026-10-25 (wrap-up sweep 27, operator /wrap-up workspace-58): EXL3 3.05 bpw stays PPL-non-inferior to UD-IQ4_XS on one binary, and the p1 greedy smoke diverges after the answer. Earlier: 2026-10-24 (wrap-up sweep 9, delta over 2026-10-23). Earlier: 2026-10-23 (wrap-up sweep 19, workspace-58: NEW-13 weight-set handoff PASS but the low-bit decoder is slower; NEW-10 FAIL re-derived on the EAR build). Earlier: 2026-10-22 (wrap-up sweep 15, workspace-58: NEW-10 GSQ IQ3_XXS verdict FAIL). Earlier: 2026-10-22 (wrap-up sweep 12, workspace-58: NEW-10 smoke abort root cause, EAR column accepted). Earlier: 2026-10-22 (wrap-up sweep 10: EAR column, NEW-10 pass rule, quant-gate power). Earlier: 2026-10-22 (wrap-up sweep 7: DS41 MXFP4 weight fidelity, vacuous kernel evidence). Earlier: 2026-10-21 (wrap-up sweep 5: DS41 MXFP4 experts measured: ppl, prefill, repack RAM). Earlier: 2026-10-21 (wrap-up sweep 3: the quant-kernel keeps folded into candidate C, EXL3 CPU, Em). Earlier: 2026-10-20 (wrap-up sweep 2: DeepInfer intake, DS41 1017 swap). Earlier: 2026-10-20 (delta compile of 18 changed sources). Earlier: 2026-10-07 — reviewed source backlog. Previous compilation metadata: 2026-10-03 (wrap-up compile: EXL3 ROI review — nothing EXL3 has ever run on an MI210, the gfx90a kernels are correctness references, and on the dense 27B EXL3 is mainly a VRAM lever that GGUF K-quants already provide; EXL3-X0 bytes-elasticity pre-gate filed and operator-approved); previous: 2026-09-26 (EXL3 standalone implementation: portable artifact/oracle and evidence contracts, qualified EPYC operators, exact-target gfx90a build/static qualification, and remaining MI210 execution gates); earlier: 2026-09-26 (EXL3 throughput closure: native-packed execution contract, independent K4/MCG oracle, c1/c8/c16 attribution grid, and controlled W4A16/NVFP4 admission); earlier: 2026-09-25 (EXL3 CPU/MI210 implementation compile: INF-80 opens the project-owned scalar/AVX-512 and native gfx90a path, separates EXL3 from IQ*_KT and W4A16, preserves the retired Qwen CPU no-go, and requires prospective measurement/verifier receipts); earlier: 2026-09-23 (research-intake jev-exl3: a near-baseline KLD/PPL/top-1 ordering is a FIDELITY ordering, never a quality ordering — the iqk/tq3 trellis port gates now demand a paired-flip task-eval win; flip counts need greedy decoding or a measured flip floor; a "BF16" reference may be a dequantized FP8 upcast; route-set agreement filed as occurrence-only; the DFlash target-quant cause stays a hypothesis, with the two stale cross-reference lines on this page corrected); earlier: 2026-09-15 pm (decode-knee register cost is an unroll multiplier; latent on the live Q8_0/Q4_K GPU stack); earlier: 2026-09-15 (the MI210 low-quant findings were distilled into a public X thread and recorded in the append-only social ledger — no new measurement, the ladder's n=1/speed-only scope carried; earlier: 2026-08-23 (**the flagged KIVI caveat resolves in two halves — the implementation half is RETIRED, the measurement half STANDS and now has a filed gate**: KIVI's per-channel-K prescription is **2-bit-only** by its own OB 1 (no 4-bit or 8-bit axis ablation exists anywhere in the paper), our stack runs 4/8-bit, and per-token V is structurally guaranteed once V is quantized — so the long-standing "primary quality gap" was never a gap, and key outliers are handled by the Hadamard rotation instead; **the granularity reading rule**: with `-fa 1` we quantize K and V per token in 32-element blocks along CHANNELS — finer than the Group-64 *mitigation* published in the alignment-collapse study and on the OPPOSITE axis from KIVI — so every third-party KV-quant damage number is a **pessimistic bound** for us; **behavioural drift decouples from perplexity** (Mistral-7B 15.2% AdvBench flip at 4-bit while PPL moves 5.22 → 5.37, 1.03×; Qwen-2.5-7B IFEval strict-pass 69.50 → 59.89 at **8-bit** with 23.14% CondFlip), K carries **76–102%** of the 4-bit damage in 8 of 9 models, and our KV write path has **NO per-channel scaling, NO clipping and NO attention-sink special-casing** — the rotation is the only mitigation we ship, and sinks exist only as a softmax bias in the graph — see the end of the page; earlier 2026-08-22 note: **the TurboQuant KV monitor is dead upstream — PR #21089 verified CLOSED UNMERGED 2026-06-02, retiring this page's monitor bullet, actionable and open question — and the iqk dispatch whitelist is a quant-SELECTION constraint**: Q2_K/Q3_K are `static_assert`ed out of the iqk path on frozen v8, so never pick them on size grounds (UD-IQ3_XXS over size-matched UD-Q2_K_XL); ChunkKV ruled experimental-candidate-only — the existing `action=compact` endpoint is Expected-Attention, NOT ChunkKV; `eschamoe` W2 closed (CUDA-only, no ROCm); plus a flagged-not-resolved KIVI caveat that our KV-quant quality case rests on PPL/NIAH, an instrument class KIVI shows can stay flat while GSM8K collapses ~57% at 2-bit — see the end of the page; earlier 2026-08-16 note: **the batch-1 decode knee on MI210/gfx90a partitions on kernel REGISTER PRESSURE, not bits-per-weight** — every quant whose `mul_mat_vec_q<_,1,true,false>` fits in ≤64 VGPR reaches 8 waves/SIMD and decodes ≥90.05 t/s, while IQ3_XXS (71 VGPR) and IQ2_XXS (78 VGPR) drop to 6 waves and ≤82.89 t/s despite being 27–46% smaller; IQ4_XS sits on the boundary and is the fastest rung measured; "batching closes the dequant gap" is refuted as stated; `design_prior`-grade, n=1, one model, speed only; plus a 2026-08-14 pair of GPU negatives — KV quantization at 64k single-stream is FALSIFIED as a speed lever on both arms (−16.7% / −6.9%) and weight quantization is inert on embedding encode (bge-m3 Q8_0 ≈ f16 at every sequence point) — see top sections; earlier 2026-08-12 note: a blocker row's *description* was wrong in a load-bearing way — the PR it names is an **ARM NEON ternary kernel that touches no x86 file**, so a naive dependent bench on Zen 5 would have measured a scalar fallback; plus the first KV-quant decision package and the Q4_K MMQ correctness root cause — see below; earlier 2026-07-24 note: adds the RP-1/RP-2 refutation of the 2-bit-EOS-damage hypothesis for the architect's degenerate `\boxed{}` loop, and the CPU A2 Q4 arm's live at-or-above IQ2 reasoning read; earlier 2026-07-20 note: adds the reasoning∝active / 2-bit-asymmetry literature cluster, the architect IQ2-vs-Q4 reasoning-certification gap, and the quant-asymmetric self-spec lane; earlier 2026-07-17 note: adds stale-fork Q2_0 freshness-audit gap, x86 Q8_0 repack/iqk-routing status, and the BF16-vs-F16 KV bench; ⚠️ 2026-07-06 MI210 gfx90a quant-roofline subsection flagged for human review — see Key Findings)
**Sources**: 70 native document references (source review 2026-10-07)

## Compiled Update — 2026-10-25 (wrap-up sweep 27, operator /wrap-up workspace-58): EXL3 3.05 bpw is PPL-non-inferior to UD-IQ4_XS on the same binary, and the greedy smoke FAILs on p1

**Confidence: verified** (predeclared rule, staged logs and digests); the quality reading stays **non-inferiority on PPL only**.

- **INF-80 EXL3-6c5, correctness half re-run (Qwen3.8-Flash-Next, one CPU quarter).** This time both arms ran on the same EXL3-tree binary (`20192b81d`). On 10-04, U ran on the champion build.
- **PPL** (wiki c512 × 40): E 2.8909 ± 0.0591 vs U 2.9925 ± 0.0632, so **−3.40% (QUALITY_NOT_WORSE)**. Both values reproduce the 10-04 run.
  - The standing caveat applies: wikitext overlaps the model's memorised n-gram set, and the Q8_0 KLD floor is 0.022–0.027. Small PPL gaps between 4-bit-class files are therefore not resolvable as quality.
- **Greedy smoke: FAIL by the prefix rule.**
  - p1 shares only 8 characters (minimum 100). Both answer " Paris.", then E explains and opens a `<think>` turn while U lists capitals.
  - p2 (102 characters) and p3 (148 characters) pass.
  - The 10-04 run had p1 identical over 48 tokens, on a different U binary. Whether the divergence is a near-tie is EXL3-6c5b (top-2 margin).
- The `epyc.exl3.measurement.v1` rows are still unemitted (EXL3-6c5a). The evidence is now in research `data/exl3-6c5-quality/`. The 10-04 speed result still stands: pp5 −30.9%.

Sources: [exl3-cpu-mi210-implementation](../handoffs/active/exl3-cpu-mi210-implementation.md) (EXL3-6c5, 6c5a, 6c5b) · [calendar plan 2026-10-25](../docs/reference/calendar-plan-2026-10-25.md) · [cpu-decode-roofline-program](../handoffs/active/cpu-decode-roofline-program.md) (10-04 EXL3 speed) · [2026-10-25 workspace-58 progress](../progress/2026-10/2026-10-25-workspace-58.md)

## Compiled Update — 2026-10-22 (wrap-up sweep 10): EAR column landed for KLD runs, Q38FN GSQ IQ3_XXS download and pass rule pinned, quant-gate power tables

**Confidence: verified** for the landed code, the unit tests and the pinned rules; **inferred** for every quality or speed outcome (the EAR build, the NEW-10 quality pass and the paired task gates have not run).

- **EAR (= 1 - TV, the SLQ cards' quality metric) is added to `llama-perplexity --kl-divergence` (EXL3-EAR1, code landed, NOT built).** Branch `experimental/ear-kld-column-20261022` @ `782c11ae4` (from champion `dd3d9721c`, v10 untouched). Two variants that are not interchangeable: full-vocab EAR = sum_v min(p_base, q) (a strict 1 - TV, so Pinsker applies) and the SLQ evaluation.py top-10 renormalised variant. Output gains an `EAR statistics` block after `Same top p`; every pre-existing line is unchanged. File-scoped g++ unit test passes (EAR(base,base)=1 within one uint16 encoding step of 16/65535 nats, Pinsker, naive reference, ties); a Python cross-check script recomputes both lines from saved base files. The build and a Qwen2.5-Coder-0.5B Q8_0-vs-Q4_K_M smoke are armed but unrun.
- **Quant-comparison receipts are wired into the belief kernel (VB-QUANTCMP-WIRE, landed).** `qwen4exp_quality_capture.py --mode kld-quantcmp` extends the existing receipt with the native EAR rows, a Pinsker line the reader re-derives, and a CPU-or-HIP residency check sampled during the child (HIP needs libggml-hip mapped and at least two non-zero KFD VRAM samples). Same source kind and `claim_tuple.grade()`; no new ladder. 16/16 new tests, 42/42 adapter tests; the reader digest was re-pinned. EAR is never labelled as acceptance.
- **NEW-10 (Q38FN GSQ-RCO IQ3_XXS vs served UD-IQ4_XS): download started, pass rule pinned before any run.** The operator chose IQ3_XXS first; the true size is 75.84 GB, not the ~65 GB estimated (two shards, 47.04 + 28.80 GB). Quality row: perplexity on wiki.test.raw (c512, 40 chunks) with one shared KLD base, then GSQ KLD and a 5-prompt coherence gate. Bars, all required: G1 mean ln(PPL(Q)/PPL(base)) <= 0.005 one-sided; G2 mean KLD <= 0.1045 (1.25 x UD's published 0.0836); G3 same-top-1 >= 88.55% (UD's 89.55% minus 1 pp); G4 zero coherence regressions. G2 and G3 are translations onto a UD base because no high-precision Q38FN base is on disk. PASS authorises only a serving-shape speed bench; FAIL closes the arm and IQ3_S is not pulled. The header predicts 96 native tensors (58 IQ4_NL, 38 Q2_0) plus 12 decode-only IQ3_XXS tensors across 48 layers.
- **The SLQ checkpoints are not servable here, and the lower-byte candidate is a different artifact.** The kaitchup SLQ 27B checkpoints are vLLM/Humming CUDA-only (no ROCm, CPU or GGUF path) and EAR99 is not smaller than our Q8_0, so no speed or quality case; the operator declined the download. The relevant candidate is the ISTA-DASLab Qwen3.8-27B GSQ-RCO GGUF (11-13 native ggml types incl. IQ1; IQ3_S at 0.42x Q8_0 bytes); its card numbers are author-reported single runs, and the roofline estimate is 0.94-1.65x no-draft and 0.6-1.1x with DFlash2 on v10 (indicative). GSQ code has no GGUF/IQ export, so the iqk NEW-10/NEW-11 trigger stays unfired. Operator declined EXL3-X0D ("not worth it"), EXL3-LB1E and EXL3-EAR2, and held NEW-12 (allocation transplant) until NEW-10 reports.
- **Quant task gates now carry a power table (EV-DEGR1, TQ3-PWR1, NEW-14).** `degradation_stats.py` (orchestrator `0993affc`, 9 tests) prints n_discordant, direction and a one-sided exact binomial p, and `size` gives required N = ceil(p_flip x (2.486/delta)^2) at one-sided alpha 0.05, 80% power (our arithmetic from the paper's SNR relation; the paper has no N table). At delta 2 pp, N is 773 / 1546 / 2318 / 3091 for p_flip 5 / 10 / 15 / 20%. G4 at N=250 detects only about 5 pp (4.97 pp at p_flip 10%; power for a 2 pp drop 26% at 10%), so G4 is recorded as a coarse screen. All per-gate p_flip inputs are blank: no flip floor has been measured.
- **Ternary kernel reference noted, no lane opened (K8).** The thrush-ternary-v2 format is readable and a group-128 int8-activation ternary kernel with 16-row interleave exists as a reference for a future TQ2_0 AVX-512-VNNI path; low-bit work stays on the DS41 and Q38FN lanes.
- **Disaggregated-quantization caveat.** The paper's accuracy is BF16-dequantised vLLM, not llama.cpp-native; its untrained higher-precision prefill control helps at IQ1/IQ2 and hurts at 3-bit or more. NEW-13 (prefill with UD-IQ4_XS, decode with IQ3_XXS via sequence-state copy, N=120 passages, gate 0 KLD_A - KLD_C < 0.005 means uninformative) is filed and waits on NEW-10's download.

### Source References (2026-10-22 wrap-up sweep 10)

- [handoffs/active/iqk-iquant-enablement.md](../handoffs/active/iqk-iquant-enablement.md) — NEW-10 download and pinned pass rule, NEW-13, NEW-14, held NEW-12
- [handoffs/active/exl3-cpu-mi210-implementation.md](../handoffs/active/exl3-cpu-mi210-implementation.md) — EXL3-EAR1 and operator declines
- [handoffs/active/tq3-quantization-evaluation.md](../handoffs/active/tq3-quantization-evaluation.md) — TQ3-PWR1 power table, K8 ternary reference
- [progress/2026-10/2026-10-22-ear1-vbquantcmp.md](../progress/2026-10/2026-10-22-ear1-vbquantcmp.md) — EAR implementation and VB-QUANTCMP-WIRE receipts
- [progress/2026-10/2026-10-22-research-intake-ist-slq.md](../progress/2026-10/2026-10-22-research-intake-ist-slq.md) — SLQ/GSQ intake findings and operator rulings
- [progress/2026-10/2026-10-22-gate-stats.md](../progress/2026-10/2026-10-22-gate-stats.md) — degradation_stats helper and required-N grid

## Compiled Update — 2026-10-22 (wrap-up sweep 7): DS41-1017 MXFP4 weights are bit-exact, and the old kernel-side NMSE = 0.0 proved nothing
**Confidence: verified** for the weight-side NMSE and the W8c gate (named artifacts, research `73aab47cc`, `42daa0ac9`); **inferred** for the deferred FP8 QDQ A/B (code written, not built or run).

- **The 1017 experts are natively MXFP4** (HF `I8` packed E2M1 with an `F8_E8M0` scale per 32). In the GGUF the E2M1 codes and E8M0 scales are bit-identical to the source on 4/4 checked expert matrices, so NMSE = 0.0 by construction. Q8_0 non-experts vs their FP8 E4M3 source measure NMSE 2.92e-5 to 2.99e-5 on 4 tensors; F16 vs F32 about 4e-8.
- **The AK served-shape MXFP4 NMSE = 0.0 was VACUOUS**: `test-backend-ops` allocates plain CPU buffers, so it never runs the `CPU_REPACK` `mxfp4_8x8_q8_0` GEMV the server uses, and both arms run the same generic kernel. The replacement real-weight gate compares CPU_REPACK against an independent scalar decode, reports NMSE plus `maxrel` (catches one wrong block scale that aggregate NMSE hides), and proves engagement per case.
- **Gate result (2026-10-22):** max anchor NMSE 2.93e-5, max rel 0.052, repack engaged on all 8 cases, broken-scale fixtures caught. Bound = 3x calibrated, capped at 5e-4 NMSE / 0.25 maxrel.
- **Deferred, not done:** the flag-gated FP8 QDQ of attention output before `wo_a` (W5.1a) and KV fake-quant attribution (T3.2) have code on experimental branch `experimental/ds41-qdq-flag-20261021` but no build or run; cancelled by the 2026-10-22 operator ruling that DS41-1017 tests wait for AutoKernel kernel work.

### Source References (2026-10-22 sweep 7)
- [handoffs/active/deepseek-v41-flash-evaluation.md](../handoffs/active/deepseek-v41-flash-evaluation.md)
- [progress/2026-10/2026-10-21-ak-repack-gate.md](../progress/2026-10/2026-10-21-ak-repack-gate.md)
- [progress/2026-10/2026-10-21-ds41-qdq-tooling.md](../progress/2026-10/2026-10-21-ds41-qdq-tooling.md)

## Compiled Update — 2026-10-21 (wrap-up sweep 3: the quant-kernel keeps folded into candidate C, EXL3 CPU, EmbeddingGemma 2 parity)

**Confidence: verified** for the ledger and parity numbers as recorded; per-keep AutoKernel percentages are 5-pair screening numbers and are **not additive** (aggregate CH-16: 36 per-commit claims compounding to +171.7% against a measured block effect of +8.524%).

- **Q38FN (UD-IQ4_XS) keeps in C:** `akm-cpu-solo-verify-five-rows` +2.158% (the three-row bound widened to five), `akm-cpu-q8-next-tile-prefetch` +0.054% (noise scale), `akm-cpu-iq3s-grid-gather` +0.593%, plus the q38fn-lane served-shape case set `6ed37bec8`; the ds41-lane variant of that case set is not folded (alternate calibration of the same name). Q38FN greedy, frozen prompts p1-p3, 128 tokens, n_probs 2: IDENTICAL 3/3 to the champion. ([autokernel champion aggregate](../handoffs/active/autokernel-champion-aggregate.md); [llama.cpp v11 release manifest](../docs/reference/kernel-manifests/llama-v11-manifest.md))
- **DS41 held keeps (14): 9 applied, 5 subsumed.** Applied: `seed-accum` (+0.373%), `q4k-x4t-zmm-widen` (+0.601%), `bscale-cvtph` (+2.266%), `two-row-tail-tiles` (+1.716%), `zmm-pair-unroll` (+0.706%), `q4k-activation-metadata-reuse` (+0.817%), `q8-rn3-single-pair-loop` (+0.568%), `rmsnorm-eight-double-chains` (+1.258%), `rmsnorm-single-pass-output` (+0.132%). The earlier bundle result that held these out was DS41 -2.51% against a 4.533% floor; the bundle gate on C is staged, not run. ([llama.cpp v11 release manifest](../docs/reference/kernel-manifests/llama-v11-manifest.md); [autokernel champion aggregate](../handoffs/active/autokernel-champion-aggregate.md))
- **GLM Q4_K/kquant kernel keeps were NOT folded.** Eight keeps plus `d2861045f` rewrite the same `mul_mat_qX_K_q8_2_X4_T` Q4_K kernel that the champion's DS41 keeps already rewrote (`ActivationMetadata` hoist): alternative implementations of one loop, the champion's measured on a served model; `d2861045f` applied textually but did not compile (`d8` undeclared), so it was dropped. ([autokernel champion aggregate](../handoffs/active/autokernel-champion-aggregate.md))
- **EXL3 CPU backend folded (additive).** `GGML_TYPE_EXL3_1..8` / `EXL3M_1..8`, `ggml-cpu/exl3.cpp` and the GGUF importer (13 commits, new types only); `test-exl3` ALL PASS with scalar = VNNI = VBMI. Model-level windows are still owed. ([llama.cpp v11 release manifest](../docs/reference/kernel-manifests/llama-v11-manifest.md); [autokernel champion aggregate](../handoffs/active/autokernel-champion-aggregate.md))
- **EmbeddingGemma 2 quant parity (V11-043).** Against the ST FP32 reference: BF16 min cosine 0.999990 (gate 0.99), Q8_0 0.999323 (gate 0.98), 0 non-finite. The operator ruled 2026-10-20 for BM25 + EG2 @256 (FP16 storage) with RRF; recall evidence only, extension-only. ([llama.cpp v11 release manifest](../docs/reference/kernel-manifests/llama-v11-manifest.md))
- **DS41 chat template side-finding for quantization work:** neither DS41 GGUF in use carries `tokenizer.chat_template`, so any DS41 quality or parity run that omits `--jinja --chat-template-file` silently measures the ChatML fallback (see [chat templates](chat-templates.md)). ([DeepSeek-V4.1 Flash evaluation](../handoffs/active/deepseek-v41-flash-evaluation.md))

**Sources (sweep 3):** [autokernel champion aggregate](../handoffs/active/autokernel-champion-aggregate.md); [llama.cpp v11 release manifest](../docs/reference/kernel-manifests/llama-v11-manifest.md); [DeepSeek-V4.1 Flash evaluation](../handoffs/active/deepseek-v41-flash-evaluation.md).

## Compiled Update — 2026-10-20 (wrap-up sweep 2): DeepSeek-V4.1 moves to the 1017 MXFP4-experts build, which retires the Q4_K keep surface

**Confidence: verified** for the operator rulings and artifact facts recorded in the handoff; **inferred** for every plan and every number quoted as public or vendor-reported. No 1017 quality or speed measurement exists yet.

### Key findings

- **Serve the vendor-precision experts directly.** The `1017` finetune is drop-in (identical config and tensor map, all 48 shards changed). Operator ruling: serve antirez's 1017 MXFP4-experts nine-shard build (about 502 GB) rather than requantize to Q4_K, and delete the September Q4 once cutover passes. The MXFP4 experts are a lossless repack of the official FP4 weights; the handoff cites a public DS4-Flash KLD of 0.0102 for native MXFP4 against 0.0290 for the FP4-to-Q4_K requant (public, not locally replicated). No publisher ships a 1017 Q4_K-experts build in the antirez layout, and unsloth's 1017 GGUFs use an upstream layout that does not load in the port. The requant route (with the unsloth imatrix) stays the fallback only if validation fails a gate.
- **The existing AutoKernel keep does not carry over.** The +7.11% DS41 serving keep targets the Q4_K X4_T kernel; MXFP4 experts run the AVX2 `mxfp4_8x8_q8_0` repack, which was about x1.00 at N=1 and x1.04 at N=3 against Q4_K iqk before the keeps. `DS41-W8` therefore re-anchors the campaign on the MXFP4 expert path after validation. This starts a new DS41 measurement era; old Q4 numbers are not comparable. Low-bit performance remains AutoKernel's job, and a dense-4-bit DS41 variant would be EPYC-original and unproven.
- **Validation gates (`DS41-W5`).** Nine-shard load (1046 tensors, 32-byte alignment where the old file was 16 KiB-aligned), ppl against the September record, the coherence gate at production prompt length, NMSE spot checks, DSpark alpha once the new drafter exists, and serving speed.
- **Reference-parity work is quantization work.** The official reference round-trips window KV (FP8), compressed KV (FP4) and indexer K/Q (FP4) before caching, and quantize-dequantizes the attention output to FP8 before `wo_a`; our port has neither. `DS41-T3.2` sizes the reference's own sensitivity with that fake-quant on and off, adds an opt-in op, and labels the re-run `kv_fakequant_matched`; `DS41-W5.1` measures the output-FP8 round trip against Q8_0 activation noise and emulates only if NMSE exceeds it. A T3 divergence is not read as a port defect before these. Sources: intake-2116#record, intake-2117#record, intake-2121#record.
- **KV type A/B (`DS41-KV.1`).** Compressed-plane KV at q8_0 first, then an NVFP4 layout (288 B per 512-dim token with the vendor's per-16 scale rule but different block interleave); stop the NVFP4 arm if NMSE is worse than q4_0. A hybrid MXFP4 placement on the MI210 (16-entry-LUT dequant feeding MFMA) is a dormant trigger, not a task.
- **Context: iqk coverage is unchanged.** The iqk IQ-quant enablement shipped in v8 and is inherited through v10; its residual items stay post-v8 research and are not touched by the swap.

### iqk coverage: what shipped and what is still stubbed (verified from the handoff's recorded gates; static source facts)

- **Shipped in frozen v8, inherited by v10:** the iqk whitelist now accelerates IQ2_XXS, IQ2_XS, IQ2_S, IQ3_XXS, IQ3_S and (via the K-quant kernel) IQ4_XS, with Q2_K/Q3_K rejected before activation quantization and compile-time dispatch assertions. The `*_R4` repacked variants stay ik-only and unreachable from our GGUFs. The campaign-scoped Q8 waiver means v8 made no Q8 performance claim.
- **IQ1 is still stubbed, but the scope audit found it cheap.** `B6` (static, 2026-07-29): the 1-bit kernel file is vendored but omitted from the CPU build list, native IQ1_S/IQ1_M cases exist, and block types and traits are already present, so it is a clean same-shape candidate; it needs a fresh experimental branch and the normal correctness and measurement gates. Hy3-IQ1_M is the only registry model with such tensors (82 IQ1_M tensors).
- **Open post-v8 work (not done):** `NEW-6` prefill headroom (no 16-wide kernels for plain IQ types; the large-batch repack path is disabled over an un-root-caused Zen4 correctness issue; fused MoE up/gate has no caller; the IQ3_XXS small-shape NMSE gate was shape-gated, not root-caused); `NEW-8`, a Q38FN IQ-K/KS self-quant measured first in ik_llama.cpp as an instrument only (ik is not a serving path), allowed by operator ruling only exceptionally; and the trellis (KT) gate, which must be measured in the ik tree before any port, with a 95% of Q4_K_M tg128 plus task-eval-win bar.

### Decisions and rationale

- Fidelity beats a smaller footprint here: direct MXFP4 avoids a requantization step whose damage the quant gates would then have to price.
- Do not land the recipe change before all shards are complete, because every DS41 launcher asserts the pinned artifacts.

### Open questions

- Does MXFP4 CPU decode, without the Q4_K keeps, land near or below the September AK headline?
- Does the output-FP8 and KV fake-quant round trip move NMSE above activation noise?

### Related

[speculative-decoding](speculative-decoding.md) (1017 drafter), [kv-cache](kv-cache.md), [chat-templates](chat-templates.md).

### Source References

- [DeepSeek-V4.1-Flash evaluation](../handoffs/active/deepseek-v41-flash-evaluation.md) — section W, DS41-W5/W5.1/W8, T3.2, KV.1.
- [iqk IQ-quant enablement](../handoffs/active/iqk-iquant-enablement.md) — shipped-in-v8 context.
- [llama.cpp DSA contribution](../handoffs/active/llama-cpp-dsa-contribution.md) — fixed sparse-op interface for the quantized KV path.

## Latest source review — 2026-10-07

## Incremental synthesis — 2026-10-07: low-bit admission is a bundle quality contract

**Confidence: verified** for the landed contract and its documented review; model-quality and champion admission are not established by source acceptance.

The low-bit scope widening replaces route-specific constants with a layered `ppl_contract`: served-shape NMSE, WikiText2 absolute relative perplexity change at most 0.5%, token agreement/coherence on production-length prompts, and a canary of at least 1,000 tokens. The review found that crashes could count as passes, some nominally long prompts were empty, served-shape cases used the wrong model, and throughput-only folds could accumulate numerical drift. Corrected cases use each lane's actual served artifact, including DS41's 384/6 and Q38FN's 512/10 total/used-expert geometries.

The contract separates inexpensive per-candidate operator checks from bundle-level quality checks with bisection. A throughput keep therefore remains an accumulator result until quality and serving gates clear. Low-bit keeps still cannot reach the global champion without the cross-lane quality gate; live token capture, linkage and bisection acceptance were not recorded as completed in the October 6 source. The later served-shape calibration supplies deterministic input evidence, including explicit anchor-relative DS41 exceptions, rather than filling that missing global gate.

### Source References

- [All-device AutoKernel program](../handoffs/active/autokernel-all-devices-all-dimensions.md) — layered contract and cross-lane gate.
- [October 6 DS41 progress](../progress/2026-10/2026-10-06-ak-ds41-main.md) — review defects and executed-versus-open boundaries.
- [DeepSeek evaluation](../handoffs/active/deepseek-v41-flash-evaluation.md) — served-artifact calibration and exceptions.

## Source References

- [All-device AutoKernel program](../handoffs/active/autokernel-all-devices-all-dimensions.md)
- [October 6 DS41 progress](../progress/2026-10/2026-10-06-ak-ds41-main.md)
- [DeepSeek evaluation](../handoffs/active/deepseek-v41-flash-evaluation.md)

## Compiled Update — 2026-09-26: EXL3 standalone CPU and gfx90a operators are implemented

**Confidence: verified** for the portable contract, CPU qualification, evidence projection, and gfx90a host/static qualification. CPU timing is an observation only. MI210 device correctness and performance remain unmeasured.

### Key findings

- **The artifact and oracle boundary is live.** `epyc.exl3.artifact.v1` binds canonical packed inputs, tensor metadata, codebook identity, transforms, and backend repacks to content digests. Independent MUL1 and MCG reconstruction covers synthetic K1–K8 cases and three revision-pinned real fixtures. The portable suite passed 17 tests.
- **EPYC operators passed standalone qualification.** Scalar dense/indexed operators, native and band8 layouts, AVX-512BW/VNNI/VBMI MUL1, and independent vector MCG paths passed 719,096 normal checks and 719,096 ASan/UBSan checks. Preliminary cache-resident mixed-K timing did not establish a runtime-K or grouped-K default, so dispatch selection remains open for protocol-eligible measurement.
- **The gfx90a implementation is ready for device qualification.** Exact `gfx90a:xnack-:sramecc+` builds contain wave64 packed GEMV, a separate FP16-input/FP32-accumulating 16×16×16 MFMA path, and mixed-K MoE plan/bind/run dispatch. Host/static qualification passed 5,579 assertions across 5,120 dispatch cells and reproduced 384 canonical outputs for each of three real fixtures. These checks do not claim GPU execution.
- **Evidence is wired before hardware measurements.** `epyc.exl3.measurement.v1` and `epyc.exl3.verifier.v1` project through the registered Vidya dispatcher into the existing `ClaimTuple` grader. The dispatcher projected 78 native rows into 234 frames without refusals or declines.
- **The remaining gate is an owned MI210 execution window.** `G3`, `G4`, and `G5` require device correctness, MFMA regime, and mixed-K routing/capacity runs. The owner path fails closed while foreign KFD occupancy is present; the implementation record observed about 67.16 GB allocated during review and correctly declined to co-reside.

### Next action

At a safe MI210 drain boundary, run the owner-authorized correctness pass, then the separate MFMA and mixed-K routing microbench observations. Keep `EXL3-3`, `EXL3-4`, and `EXL3-5` open until their device gates pass.

### Source References (2026-09-26 implementation)

- [EXL3 CPU and MI210 implementation](../handoffs/active/exl3-cpu-mi210-implementation.md) — delivered operators, exact gate state, and owner-run requirements.
- [Vidya belief substrate](../handoffs/active/vidya-belief-substrate-program.md) — registered measurement/verifier source kinds and shared grading boundary.
- [EXL3 standalone implementation record](../progress/2026-09/2026-09-26-exl3-implementation.md) — commit lineage, qualification counts, code-object digest, and remaining hardware gate.
- [EXL3 session record](../progress/2026-09/2026-09-26-inference.md) — research-to-implementation transition, wrap-up audit, and next device action.

## Compiled Update — 2026-09-26: EXL3 throughput research closes on a native-packed custom-kernel contract

**Confidence: verified** for the filed implementation and measurement requirements. Published NVIDIA rates remain external workload targets; no local EXL3 CPU or MI210 correctness or performance result exists yet.

### Key findings

- **The next useful work is implementation.** The 88-record throughput follow-up found no CPU, HIP, ROCm, gfx90a, or MI210 EXL3 compute path. Broad research expansion is closed unless a source supplies such a path, changes EXL3 reconstruction or ABI semantics, invalidates a correctness gate, or provides matched raw evidence that changes a decision.
- **Native packing is the execution contract.** Each logical Q/K/V and gate/up/down matrix keeps its own trellis, transform vectors, codebook marker, tensor role, source digest, and expert domain. The runtime exposes `plan`, `bind`, and allocation-free `run` phases over caller-owned persistent scratch. Unknown mappings, codebooks, conflicting MCG/MUL1 markers, capacity overflow, capture fallback, and exhausted scheduler slices fail closed.
- **The first real oracle target is uniform K4/MCG.** A project-owned scalar decoder must establish packed-window and lane placement independently. One real K4/MCG tensor and synthetic K1–K8/MUL1/MCG vectors separately check procedural state, reconstructed tiles, transforms, and full operator output before optimized EPYC or wave64 code is trusted.
- **Throughput is decomposed before it is compared.** The local program measures reconstruction, GEMV/GEMM, one layer, bare target serving, and later speculative serving separately. The serving grid fixes prompts and output IDs and reports c1/c8/c16 decode, prefill, TTFT, full-wall throughput, verifier work, acceptance by position, memory, context capacity, and route distributions. Published CIRU/NVIDIA figures are targets only for reproducible workload envelopes, not universal EPYC/MI210 thresholds.
- **A four-bit comparator must earn admission.** W4A16 and NVFP4 artifacts are separate arms. Codec conclusions require matched teacher, architecture, expert count and pruning plan, module coverage, tokenizer, runtime, KV format, and evaluation panel, plus sampled reconstruction and scale checks. Quality, artifact size, resident memory, capacity, latency, prefill, decode, and serving throughput remain separate directed metrics.

### Next action

Complete `EXL3-1`: freeze the content-addressed packed artifact and metadata schema, independent MCG/MUL1 oracles, real and synthetic fixtures, and prospective measurement/verifier writers. Only then fork into EPYC primitives and native gfx90a wave64 decode.

### Source References (2026-09-26)

- [EXL3 CPU and MI210 implementation](../handoffs/active/exl3-cpu-mi210-implementation.md) — settled throughput findings, packed ABI, kernel gates, comparator admission, and local measurement grid.
- [DFlash2 experimental build](../handoffs/active/dflash2-block-drafter-experimental-build.md) — downstream speculative-serving gate and recurrent-state obligations.
- [EXL3 Stage-4 integration record](../progress/2026-09/2026-09-25.md) — disposition counts, applied owners, and validation boundary.
- [EXL3 full-session wrap-up](../progress/2026-09/2026-09-26-inference.md) — research closure, validation, commit lineage, and implementation start point.

## Compiled Update — 2026-09-25: EXL3 now has a native EPYC and MI210 implementation program

**Confidence: verified** for the implementation boundaries and evidence contract. This update records an approved program; it adds no local EXL3 correctness, quality, or performance result.

### Key findings

- **EXL3 has a project-owned implementation path.** [`INF-80`](../handoffs/active/exl3-cpu-mi210-implementation.md) begins with a content-addressed canonical artifact, independent portable `mul1` and MCG reconstruction, project-owned synthetic fixtures, and revision-pinned real-weight fixtures. CPU work then proceeds from scalar dense and indexed-expert operators to AVX-512BW/VNNI/VBMI kernels. Unified runtime-K and grouped K-specialized dispatch both remain candidates until local EPYC measurements choose per-regime defaults.
- **The old Qwen CPU no-go stays valid within its measured scope.** The completed `INF-71` result ruled out the bytes-only lever for one Qwen CPU operating point. It does not decide dense, MCG, gfx90a, or hybrid execution; those broader paths belong to `INF-80`. Reusing the retired `INF-71` identifier would collapse two different decisions ([CPU roofline successor scope](../handoffs/active/cpu-decode-roofline-program.md)).
- **EXL3 and IQ*_KT are separate formats and programs.** Native EXL3 CPU and MI210 work belongs to `INF-80`; IQ*_KT remains under the iqk program. Existing IQ*_KT throughput or quality gates do not gate EXL3, and the earlier CPU result for the QTIP 3INST family does not establish EXL3 decode cost ([iqk boundary](../handoffs/active/iqk-iquant-enablement.md), [quantization ownership](../handoffs/active/tq3-quantization-evaluation.md)).
- **W4A16 is an alternative deployment family.** A codec comparison is admissible only when teacher revision, architecture, expert count and keep plan, evaluation panel, and storage budget match. A pruned W4A16 production arm can inform a deployment comparison, but it cannot isolate codec quality against a full-width EXL3 arm.
- **Evidence capture is part of the first milestone.** Before any correctness, performance, or quality-producing run, the producer must emit strict `epyc.exl3.measurement.v1` and `epyc.exl3.verifier.v1` records. Adapters project their native fields into `ClaimTuple`; `claim_tuple.grade()` remains the sole grader ([Vidya task](../handoffs/active/vidya-belief-substrate-program.md)).

### Next action

`EXL3-1`: freeze the artifact and metadata contract, portable `mul1` and MCG oracles, real fixtures, and both evidence writers. The critical path then forks into CPU primitives and gfx90a decode before prefill, mixed-K dispatch, llama.cpp experimental integration, local measurement, hybrid execution, the controlled W4A16 study, and a complete regression package.

### Source References (2026-09-25)

- [EXL3 CPU and MI210 implementation](../handoffs/active/exl3-cpu-mi210-implementation.md) — `INF-80`, settled research, tasks, gates, and exclusions.
- [CPU decode roofline program](../handoffs/active/cpu-decode-roofline-program.md) — preserved `INF-71` no-go and successor scope.
- [IQK iquant enablement](../handoffs/active/iqk-iquant-enablement.md) and [TQ3 quantization evaluation](../handoffs/active/tq3-quantization-evaluation.md) — EXL3/IQ*_KT ownership boundary.
- [Vidya belief substrate](../handoffs/active/vidya-belief-substrate-program.md) — prospective EXL3 measurement and verifier contracts.
- [EXL3 intake session record](../progress/2026-09/2026-09-25-codex-exl3-intake.md) — intake counts, decisions, validation, and publication record.

## Compiled Update — 2026-09-23 (research-intake jev-exl3): KLD ranks damage, not quality — and the quant gates now say so

**Confidence: verified** for the gate and wording changes in our own handoffs. **External** for the fidelity-vs-quality evidence: dive-verified with a per-claim second reader, not reproduced on our stack.

### Key findings

- **A KLD/PPL/top-1 ordering among near-baseline quants is a fidelity ordering, not a quality ordering.** Evidence from two GGUF cohorts served on llama.cpp (28 Qwen3.6-35B-A3B quants, 41 Devstral-24B quants):
  - Over the full cohort, headline KL(BF16‖quant) tracks the task composite well: Spearman ρ −0.72 and −0.86.
  - Inside the near-baseline "silent zone" the correlation collapses to +0.00 (n=17) and −0.24 (intake-1510#01).
  - The collapse holds across 14 per-token metric variants, including KLD p99, PPL ratio and top-1 agreement (intake-1510#02).
  - Used as a per-prompt picker ("lower KLD wins"), KLD was right 42.3-49.4% of the time, no better than a coin (intake-1510#04).

  The flips paper makes the same recommendation from the other side: report distance metrics *alongside* capability metrics, never instead of them (intake-1519#05). So a KLD gate can reject damage, but it cannot rank candidates that all pass it.
- **The trellis port gates were rewritten to match.** The IQ4_KT decision-flipper in both [iqk-iquant-enablement](../handoffs/active/iqk-iquant-enablement.md) T3 and [tq3-quantization-evaluation](../handoffs/active/tq3-quantization-evaluation.md) STEP 3 now requires two things. First, ≥95% of Q4_K_M tg128. Second, a measurable **task-eval win**, measured as paired per-item flips against the reference. PPL/KLD are reported beside that as fidelity context only. Previously the gate asked for "a measurable PPL/eval win", which a near-baseline PPL delta could satisfy.
- **The PLE-precision B7 close is re-scoped, not reversed.** "Does not buy quality" now reads as a fidelity statement. The paired KLD/PPL measure *change vs the IQ4_XS-uniform anchor*, not *damage vs BF16*, and cannot rank near-baseline quality ([cpu-decode-roofline-program](../handoffs/active/cpu-decode-roofline-program.md), intake-1510, intake-1519#05).
- **Flip counts need a floor or greedy decoding before they mean anything.** The KV behavioural gate in tq3 gains three rules:
  - count leapfrogs (FP16 fails, quant passes) as well as drops;
  - report C→I and I→C separately, with the net direction;
  - read any flip count only under greedy decoding or against a measured FP16-vs-FP16 flip floor.

  Two sampled 16-bit runs of the same model differ by 23.5% flips (intake-1519#00, intake-1519#record). The same paper's MT-Bench "flips predict downstream quality" headline was OVERTURNED on recount (intake-1519#record). Cite that entry by claim, never bare.
- **A "BF16" reference can be a dequantized upcast.** A tensor-level audit found the official GLM-5.3-Flash BF16 release sitting largely on an FP8-dequantization grid: ~95% weighted exact or near-exact matches (intake-1508#04). DS41-T3 therefore audits DeepSeek-V4.1-Flash's reference before any KLD claim. If the reference is an upcast of the FP8/FP4-native release, the claim names it `dequantized_from_quant` ([deepseek-v41-flash-evaluation](../handoffs/active/deepseek-v41-flash-evaluation.md)).
- **Route-set agreement under weight quantization is filed as occurrence-only.** RT-2 gains a rider. Run the ported routing tap on a reference GGUF (Q8_0/BF16 experts) and on a Q4_K candidate of the same model, over the identical token stream. Emit:
  - per-layer top-k Jaccard;
  - the share of token-layers with at least one replaced expert;
  - a repeat floor and a chance baseline.

  The result is labelled occurrence-only, not damage. The only published weight-domain measurement of this is an occurrence statistic with no interventional attribution (intake-1524#03, intake-1524#record). v10's `llama-quant.cpp:304-307` never quantizes `ffn_gate_inp`, so any flips come from upstream perturbation ([moe-routing-tap-and-locality-measurement](../handoffs/active/moe-routing-tap-and-locality-measurement.md)).
- **DFlash on quantized targets.** The 2026-09-23 correction of this page's Summary and Key Findings, demoting target quantization to a hypothesis, now also covers the two cross-reference lines below. The drafter-side precision priors (4-bit ≈ −1% acceptance, weak) and the filed missing control are in [speculative-decoding](speculative-decoding.md).

### Open questions

- Does any trellis candidate produce a paired-flip task win over Q4_K_M that exceeds a measured flip floor? No such run exists. STEP 2 still needs operator inference approval.
- The P-KLD annex wording that would make "fidelity ordering ≠ quality ordering" constitutional is prepared only. It is the operator's call via OP-38 ([benchmark-methodology](benchmark-methodology.md)).

### Source References (2026-09-23)

- [iqk-iquant-enablement.md](../handoffs/active/iqk-iquant-enablement.md) — T3 gate rewrite.
- [tq3-quantization-evaluation.md](../handoffs/active/tq3-quantization-evaluation.md) — STEP 3 gate rewrite and the flip-counting amendment.
- [cpu-decode-roofline-program.md](../handoffs/active/cpu-decode-roofline-program.md) — the B7 fidelity scope note.
- [moe-routing-tap-and-locality-measurement.md](../handoffs/active/moe-routing-tap-and-locality-measurement.md) — RT-2 route-set agreement rider.
- [p-kld-annex-proposals-20260923.md](../docs/research-intake/p-kld-annex-proposals-20260923.md) — the drafted V6/V8 wording from the same evidence.
- [2026-09-23-intake-jev-exl3.md](../progress/2026-09/2026-09-23-intake-jev-exl3.md) — the DFlash record correction.
- intake-1510#01/#02/#04, intake-1519#00/#03/#05, intake-1508#04, intake-1524#03/#04 — dive-verified external evidence.

## Compiled Update — 2026-09-15 (pm): the sub-4-bpw decode knee's register cost is an unroll multiplier, and it is latent on the live stack

The IQ2_XXS/IQ3_XXS register pressure behind the 2026-08-16 knee is mostly clang fully unrolling the 4-trip sign-unpack loop.
- `#pragma clang loop unroll(disable)` gives 78→44 and 71→44 VGPR statically.
- It regresses Q3_K (88→96), and global flags regress Q8_0/Q4_K.
- The "fewer bits = slower" reading stays a statement about the *shipped* compilation, not an irreducible format property.
- Throughput is untested (AK-QL-7).
- No IQ format is GPU-resident today: Q8_0 25 / Q4_K 44 VGPR are already at 8 waves.

Full account in [hardware-optimization.md](hardware-optimization.md) (Compiled Update 2026-09-15 pm) and [a10_iq2_vgpr_compiler_ab_20260915.md](../artifacts/gpu-aux-baselines/a10_iq2_vgpr_compiler_ab_20260915.md).

## Compiled Update — 2026-09-15: the MI210 low-quant findings were published as a device-level public summary

**Confidence: observation** — this entry adds no new measurement. It records that the 2026-08-16
register-pressure / IQ4_XS-boundary / batching findings on this page were distilled into a public X
thread for a user asking about running low quants on the MI210, with the ladder's n=1, single-model,
speed-only scope carried explicitly.

The conversation is held in the append-only social ledger [`docs/publication/social/`](../docs/publication/social/)
(`x-2026-09-15-mi210-low-quants`), alongside its four recorded soft spots (KV-quant is speed-only;
the MoE batching half is unmeasured; the prefill config wins are nonpromotable candidates; Q3_K at 88
VGPR is the static table, not a measured rung).

### Source References (2026-09-15)

- [2026-09-15-x-mi210-low-quants.md](../docs/publication/social/threads/2026-09-15-x-mi210-low-quants.md) — the posted thread, verbatim, plus its soft spots and evidence index.

## Compiled Update — 2026-09-04: EXL3 mul1 trellis, hybrid KV-quant, and iqk IQ4_XS routing

**Confidence: verified** for the EXL3 format facts and the CPU decode measurement (layout decoded bit-exactly from `exllamav3` `499890c75`, validated against `pack.cu` on 2304/2304 states; decode-cost numbers are exllamav3's own `mul1` CPU GEMV on the real downloaded expert tensors); **verified** for the hybrid KV-cache budget arithmetic and the iqk IQ4_XS mis-routing (every element differing, max abs ~1.2e3). No GGUF exists and nothing on this host runs EXL3 end to end today — EXL3 quality claims are unmeasured and its end-to-end speed figures are bytes-only arithmetic.

### EXL3 `mul1` trellis is the trellis format that IS a speed play on CPU — its decode folds into the integer dot, unlike the KT/QTIP family

The 2026-08-16 verdict on this page — "trellis quantization is a quality-per-bit play, not a speed play" — was measured on the **KT/QTIP family** (`IQ2_KT`/`IQ3_KT`/`IQ4_KT` in ik_llama.cpp), whose QTIP **3INST** decode emits an fp32 per weight and forces an fp32 GEMM (~4.8 t/s vs ~4.6 t/s F16 — no speed). **EXL3's `mul1` codebook is a different decode and that verdict does not transfer**, so the two must not be conflated.

- **The format** (`turboderp/Qwen3.8-Flash-Next-exl3`, 2.05–6.05 bpw, published 2026-08-31; MTP head quantized at 4 bits). A streamlined QTIP: procedural codebook, tail-biting trellis, blockwise Hadamard incoherence processing, Viterbi search over 16-element vectors in **16×16 tiles**, fractional mixed bitrates. Per quantized linear module: `trellis` (packed tiles) + `suh` (input-side sign×scale, per input channel) + `svh` (output-side sign×scale — this is where `out_scales: always` lives) + `mul1` (the int32 codebook multiplier `0x83DCD12D`, identical in every module).
- **Why it is fast: decode is arithmetic, not a lookup, and it fuses into the GEMV the kernel already runs.** `mul1` (cb2) decodes as `w(s) = (bytesum(s·0x83DCD12D) − 510)·k_inv`, `k_inv = fp16(0x1eee) = 1/147.77`. Because the codebook is **affine in a byte-sum**, dequant and the activation product fuse: `Σ_k w_kn·x_k = k_inv·q·(Σ_k bytesum(s_kn·M)·x8_k − 510·Σ_k x8_k)`, so `bytesum(s·M)·x8` is **exactly one `vpdpbusd` per 16 weights**. Roughly four vector uops per 16 weights (bit-field extraction of trellis states via `vpermt2var` + funnel shifts, one 32-bit multiply, one `vpdpbusd`) — IQ4_XS-class, not KT-class.
- **The forward carries a Hadamard on both sides, per GEMV:** `y = svh ⊙ H₁₂₈(Wq · Q8(H₁₂₈(suh ⊙ x)))`, blockwise over 128-element blocks with Q8 activation quantization for the `vpdpbusd`. `suh` differs per (expert, projection), so the input transform **cannot be hoisted out of the expert loop** — but it is O(k) against an O(k·n) GEMV (≈ 1/640 of the work), so it is not the cost. Q8-activation accuracy vs fp32: **0.66–0.98% output RMS** on real expert tensors.
- **Per-class bit widths** (no fractional mix inside a layer): routed experts **K=4** (4.05 branch) / **K=3** (3.05); dense/shared-expert/attention/`lm_head` K=6/5 (`_h` = head bits); the 39 GB n-gram embedding table at K=6/5 (`_ng`, a different row format). Kernel constraints inherited by any ggml port: `k % 128 == 0`, `n % 128 == 0`, `k ≤ 8192`, K ∈ [1,8]; `mul1`-only; `MAX_M = 4` (GEMV, decode-only — prefill needs a dequant-then-GEMM fallback); MoE experts only (no CPU path for attention/dense/head).
- **Measured decode cost on this Zen 5 box** (exllamav3's own kernel, VBMI-swizzled layout ≡ VNNI-native bit-for-bit): **per core the fused decode+dot is compute-bound** (K4 17.3 GB/s of trellis in cache, 16 GB/s from DRAM — trellis extraction dominates; decode-only is 1.5–1.7× faster); **from ~10 threads it is memory-bound** (48T: 110–124 GB/s on random K4 experts, 91–105 K3, 160–172 on sequential sets) — the same ~153 GB/s ceiling every quant hits on this machine; t64/t96 do not help.
- **The bytes lever, and its cap.** Expert stream vs the uniform IQ4_XS artifact (up/gate IQ4_XS 4.25 bpw, down Q5_1 6 bpw = 1.296 GB/token): **K4 1.180 GB (−9%), K3 0.885 GB (−32%).** End to end that is **+2% (K4) / +7% (K3) at today's in-situ efficiency, +11–13% at the 48T rate, +15–18% only at the bandwidth ceiling** — because the expert stream is ~21% of the token and the token is dispatch-bound, not bandwidth-bound. **Parked behind the dispatch-floor work (INF-70 Axis D).**
- **Porting cost and prior art.** No trellis/QTIP/EXL3 support exists anywhere in `ggml`-land. A port is a new `GGML_TYPE_EXL3_MUL1_K{3,4}` — necessarily an **opaque per-matrix blob** (the natural unit is a 16×16 tile spanning 16 rows of `ne[0]`, so it cannot be a row-block type like IQ4_XS) with its own `mul_mat_id` path and a dequant-then-GEMM prefill fallback — plus a `gguf-py` importer; re-estimated at **3–5 sessions**. exllamav3 is MIT but **CUDA-first with no ROCm path** (the MI210 is out of scope regardless), so only the `mul1` decode identity and the swizzled layout are borrowable.

### KV quantization on a 75%-recurrent hybrid is a small lever (qwen4exp / Qwen3.8-Flash-Next)

Only **12 of 48 layers have a KV cache** — the other 36 are Gated-DeltaNet and carry none — with `head_count_kv = 2` and key/value length 256, giving 24.0 KiB/token in f16. KV is therefore only **2.42% of the 4.16 GB/token read budget at ctx 4096** (4.84% at 8k, ~18% at 32k), so q8_0 (which halves it) saves ~1.2% of bytes at 4k; the memory saving is irrelevant on a 1.1 TB box. The measured d0→d4096 decode drop (−7.8%) is mostly attention compute and the FA split path, **not** KV bandwidth, so KV-quant cannot recover it. Predicted gain ~1–2% decode. Two cautions: **q4_0 is contraindicated** — external evidence shows it concentrating damage in long documents (KL 0.581 vs q8_0 < 0.04), exactly this model's workload, with guidance to spend bits on the Key over the Value; and **quantized KV is precisely what activates the `attn_rot_k`/`attn_rot_v` rotation path** (they require `ggml_is_quantized`), which this stack has never exercised on f16 and which a community Flash-Next MTP repo ships a "critical" disable flag for — so a KV-quant arm must run MTP and a coherence check, not just a speed test. Filed as INF-70 B9.

### iqk does not only exclude types — it can silently reroute an included one to a wrong kernel

`iqk_mul_mat.cpp`'s `is_dequant_better()` sends IQ4_XS to a requantized Q8 repack GEMM once a ubatch reaches `nrc_y >= 32`, and on this Zen host that path is grossly wrong (every element differing, max abs ~1.2e3, at row 0) — the same family already excluded IQ2_XXS/IQ2_XS/IQ2_S/IQ3_XXS/IQ3_S "for large-Ny dense and MoE shapes on Zen", with IQ4_XS mistakenly left on it. It corrupted single prompts above ~32 tokens and concurrent short prompts (a 48-row ubatch), and `GGML_IQK=0` was the only correct config until the targeted exclusion landed. So a quant's price includes not just *whether* it is on the iqk path but *which* iqk kernel a wide ubatch routes it to. See `hardware-optimization.md` → *2026-09-03 (INF-70 wave 3)* for the full root-cause and fix.

### Source References (2026-09-04)

- [`exl3-trellis-cpu-kernel.md`](../handoffs/completed/exl3-trellis-cpu-kernel.md) — INF-71: what exists on disk, the measured reference-kernel numbers, the bytes/token ledger, and the phased port plan with gates.
- [`docs/design/exl3-mul1-ggml-type.md`](../docs/design/exl3-mul1-ggml-type.md) — the X0 format spec: tile bit-layout, the `mul1` decode identity validated against `pack.cu`, the forward contract, and the proposed ggml type.
- [`cpu-decode-roofline-program.md`](../handoffs/active/cpu-decode-roofline-program.md) — INF-70's EXL3 trellis lever, now INF-71 (bytes lever parked behind the dispatch floor) and B9 (hybrid KV-quant analysis).
- [`2026-09-02-inf70-audit.md`](../progress/2026-09/2026-09-02-inf70-audit.md) — the drafter/EXL3 research sweep and the X0/X1 measurement wave.
- [`2026-09-03-inf70-audit.md`](../progress/2026-09/2026-09-03-inf70-audit.md) — the IQ4_XS iqk large-Ny mis-routing root-cause and fix.

## Compiled Update — 2026-08-16: on CDNA2 the batch-1 decode knee is kernel REGISTER PRESSURE, not bits-per-weight

**Confidence: observation / `design_prior`** — this is a **non-governed** measurement. It is not an AutoKernel `evaluation_event`, carries no governed receipt, and §19.0 rule 4 forbids promoting it by origin. It proposes; it settles nothing. **n=1 per cell, no A/A band, ONE model (8B dense), SPEED ONLY.** Every number below must be quoted with those caveats — see *Caveats* at the end of this section, and do not quote a number without them.

### The partition, and it is not a bpw trend

An 8-rung ladder was built from ONE f16 source of **Goedel-Code-Prover-8B** through ONE quantizer — the frozen production `llama-quantize`, version **10125** (`0db32c06e`) — and benched on the MI210 (gfx90a/CDNA2) with `-ngl 99`, GPU residency proven during both runs. The VGPR / waves-per-SIMD columns are the **static** register allocation of each quant's `mul_mat_vec_q<_,1,true,false>` instantiation, read out of the shipped code object four days earlier (see [Hardware Optimization](hardware-optimization.md) for the method); they are not measured here.

`%HBM` is against the **measured** 1433.3 GB/s achievable bandwidth, not the 1638 GB/s datasheet peak. `eff GB/s` = t/s × model bytes — the weight stream only, ignoring KV and activations, so it is a floor on achieved bandwidth, not a ceiling.

| rung | GB | tg128 t/s | eff GB/s | %HBM | pp512 t/s | VGPR | waves/SIMD |
|---|---:|---:|---:|---:|---:|---:|---:|
| f16 | 16.38 | 63.97 | 1047.9 | 73.1% | 2880.9 | — | — |
| Q8_0 | 8.70 | 99.09 | 862.5 | 60.2% | 2673.1 | 25 | 8 |
| Q6_K | 6.72 | 90.05 | 605.1 | 42.2% | 2460.0 | 46 | 8 |
| Q5_K_M | 5.85 | 100.93 | 590.0 | 41.2% | 2459.4 | 55 | 8 |
| Q4_K_M | 5.02 | 108.75 | 546.1 | 38.1% | 2462.2 | 44 | 8 |
| **IQ4_XS** | 4.59 | **129.77** | 595.3 | 41.5% | 2440.9 | **64** | **8** |
| IQ3_XXS | 3.36 | 79.44 | 267.2 | 18.6% | 2398.5 | 71 | 6 |
| IQ2_XXS | 2.48 | 82.89 | 205.9 | 14.4% | 2468.1 | 78 | 6 |

**Every rung whose kernel fits in ≤64 VGPR (8 waves/SIMD) decodes at ≥90.05 t/s; both rungs above 64 VGPR (6 waves) decode at ≤82.89 t/s — while being 27–46% *smaller*.** Separation is 7.17 t/s with no overlap. **Below IQ4_XS, shrinking the model makes decode ABSOLUTELY SLOWER.** IQ4_XS sits exactly on the 64-VGPR boundary — the last rung that still reaches maximum occupancy — and is the fastest rung measured, 129.77 t/s against Q4_K_M's 108.75 and IQ2_XXS's 82.89.

**Prefill is flat**: 2398–2881 t/s across the whole ladder, 16.7% total spread, no knee. Whatever the cliff is, it is **specific to the batch-1 GEMV path** and does not touch prompt processing.

### "Batching closes the dequant gap" is REFUTED as stated

The never-before-run quantized batched sweep (`llama-bench -p 128 -n 128`, B ∈ {1,2,4,8,16,32}, all 8 rungs) measures the ratio to IQ4_XS rising but plateauing short of parity: **IQ3_XXS 0.60 → 0.77** and **IQ2_XXS 0.66 → 0.88** across B=1→32, while **Q4_K_M converges to ~0.99**. So batching closes the gap for the 8-wave K-quants and leaves **12–23% on the floor** for the 6-wave IQ formats.

That asymmetry is itself mechanism evidence: a cost that were purely per-weight-read amortizes away as B grows (read once, reuse B times); a cost that tracks a **wave-slot ceiling** does not — which is what the static VGPR table predicts. The premise was reasoned-but-never-measured before 2026-08-16 and is now retired with a receipt, so it is not re-proposed as an argument for low-bit serving.

### What this does to the low-bit programme

Three things change in how sub-4-bit work is valued on this device:

- **The ranked IQ2/IQ3 items are OCCUPANCY levers, not dequant-arithmetic levers.** The `v_perm_b32` sign-expansion work (437-instruction excess), the Q4_K branchless six-bit scale/min decoder, and the VGPR 78→64 target all matter *to the extent they hold live registers*. This is the third independent time the codebook gather has been ruled out as the cost — see [Hardware Optimization](hardware-optimization.md) for the disassembly evidence.
- **The payoff is threshold-shaped, not linear.** Crossing back under 64 VGPR regains the 8th wave; a reduction that lands at 70 buys nothing. Levers whose stated benefit is "fewer instructions" without a register target are currently unrankable and must be re-scoped or declined.
- **Value cases must be weighted against IQ4_XS, not against the format's own baseline.** An IQ2_XXS win that does not clear a **1.57×** deficit produces no production value at any batch size measured.

The prediction was on disk before the ladder ran and was never carried into the campaign that needed it: the Q8_0 roofline work had already established that the gap is achieved-bandwidth/occupancy and NOT dequant-compute, and the per-quant VGPR table published IQ4_XS at exactly 64 → 8 waves with IQ3_XXS/IQ2_XXS at 71/78 → 6 waves. Measured 2026-08-16, the AutoKernel catalogue mentioned **IQ4_XS zero times** (Q4_K 20, IQ2 8, Q8_0 6, Q6_K 4, IQ3 3, Q5_K 0, IQ1 0) — the loop was aimed at the rungs on the wrong side of its own knee.

**The open discriminating test**: the same static table puts **IQ1_S at 42 VGPR → 8 waves**, below IQ4_XS. If the mechanism is register pressure and not bit-width, the *smallest* format on the shelf should land in the fast band, inverting the monotonic "fewer bits = slower below 4 bpw" reading. That is the one place where the occupancy story and the unpacking-cost story disagree in sign, and it is the cheapest test that can falsify the whole mechanism. Unrun as of 2026-08-16. (Scope note: IQ1 is stubbed in the CPU iqk path; this is a GPU MMVQ question and does not depend on that.)

### A unit-confusion correction to the ladder manifest

The ladder's build manifest warns that the pre-existing upstream Q4_K_M and Q8_0 "differ materially in size" from the ladder's (4.68 vs 5.03 GB; 8.11 vs 8.71 GB). That is a **unit-confusion artifact** — it compares upstream in GiB against ladder in GB. Measured 2026-08-16, both pairs are the *same size* (Q4_K_M 4.68 GiB = 5.03 GB; Q8_0 8.11 GiB = 8.71 GB). Same size is not proof of byte-identity, so the manifest's "do not substitute" instruction is still worth obeying on provenance grounds — but not for the reason it gives.

The same hazard bit the analysis itself: an earlier pass reported the `%HBM` figures ~7.4% low by dividing GiB model sizes into a decimal-GB bandwidth. The 1.0737 factor is constant across rungs, so the *shape* survived the error and the absolute percentages did not — exactly the class of error a constant factor hides.

### Caveats a future reader must not skip

- **n=1 per cell, no A/A band.** The **IQ4_XS B=8 cell (408.5 t/s) is a suspected outlier**: it breaks its own monotonic trend (B=4→8 is 1.37×, B=8→16 is 2.14×; every other rung runs ~1.8–1.9× at both steps) and it is the single point where Q4_K_M inverts above IQ4_XS. Do not quote B=8 without replication.
- **One model, 8B dense.** The VGPR figures are model-independent (static kernel allocation); the throughput figures are not. The 122B MoE attribution agrees on *direction* only — see [MoE Optimization](moe-optimization.md).
- **SPEED ONLY — no correctness pairing.** The IQ2/IQ3 rungs were built on a **1.23 MB / 30-chunk imatrix** and are **performance probes, explicitly NOT quality-grade models**. No PPL, no eval. This ladder ranks *throughput* and says nothing about whether IQ4_XS is usable, only that it is fast. **No rung on this ladder may be cited in a promotion argument** until the correctness half runs — the standing project rule is to pair speed with a correctness check.
- **Non-governed.** These are `design_prior`-grade measurements, not AutoKernel `evaluation_events`. Replication with an A/A band is the precondition for quoting any of it as anything stronger.

### Source References (2026-08-16)

- [`artifacts/gpu-aux-baselines/a10_quant_ladder_occupancy_knee_20260816.md`](../artifacts/gpu-aux-baselines/a10_quant_ladder_occupancy_knee_20260816.md) — the receipt: the 8-rung ladder table, the batched sweep, the manifest unit correction, and the caveat list.
- [`autokernel-research-loop.md` §22](../handoffs/active/autokernel-research-loop.md) — the re-aiming of the low-bit lever set, hypotheses AK-H-QL-1/2/3 with their falsifiers, and the format-mention census that found IQ4_XS absent from the catalogue.
- [`artifacts/gpu-aux-baselines/a10_iq2_vgpr_lever_20260812.md`](../artifacts/gpu-aux-baselines/a10_iq2_vgpr_lever_20260812.md) — the per-quant static VGPR table that predicted the knee four days early, and the IQ2_XXS-vs-IQ4_XS disassembly diff.
- [`mi210-q8-dequant-gemv-roofline.md`](../handoffs/active/mi210-q8-dequant-gemv-roofline.md) — the prior establishing that the Q8_0 gap is achieved-bandwidth/occupancy and not dequant-compute, and the measured 1433.3 GB/s achievable-bandwidth denominator.

## Compiled Update — 2026-08-14: two GPU surfaces where the quant lever is negative or inert

**Confidence: observation** — frozen v9 `0db32c06e` / build `10125` on an idle MI210, single runs, no P-GPU-1. Both entries close a previously-open hypothesis with data.

**KV quantization at long context on the GPU is DEAD — the "alive single-stream at long context" hypothesis is falsified.** The standing reasoning was that KV-quant, measured dead at short context and in aggregate, would pay at 64k single-stream where the KV read starts to rival the weight bytes. Measured, `-ctk q8_0 -ctv q8_0` **hurts decode on both arms**: the 35B-A3B GDN hybrid **75.8 → 63.1 t/s (−16.7%)** and the dense 27B **21.7 → 20.2 t/s (−6.9%)**. It fails even on the dense 27B, whose all-full-global KV is the most favourable geometry available — the dequant cast cost exceeds the bandwidth saving. This matches the CPU precedent that the dequant cast *costs* throughput. **KV quantization stays a max-context / VRAM characterization, never a speed lever**, on either substrate. (Distinct from the weight-quantization knee in the section above: that one is register pressure; this one is cast arithmetic.)

**On embedding encode, weight quantization is inert — it buys memory, not speed.** A 13-point GPU baseline sweep on `bge-m3` found **Q8_0 and f16 landing within noise at every sequence point**. Encode is not the regime where a quant lever pays; the compute-bound analog worth testing is VL vision-encoder prefill, which has not been run.

### Source References (2026-08-14)

- [fable5 window-2 findings-05c — lever × category matrix](../handoffs/active/fable5-window2-findings-05c-mi210-lever-category-matrix.md) §4 — the L14 KV-quant falsification on both arms and the A3 BGE-encode baseline result.
- [fable5 window-2 findings-02 — heterogeneous GPU](../handoffs/active/fable5-window2-findings-02-heterogeneous-gpu.md) §5 — the same-batch GPU-lane context, including that the 64 GB binding constraint at long context is the KV allocation and not the weights.
- [`artifacts/gpu-aux-baselines/a3_bge_mi210_20260812.jsonl`](../artifacts/gpu-aux-baselines/a3_bge_mi210_20260812.jsonl) — the 13 GPU encode points behind the inertness claim.

## Compiled Update — 2026-08-12: a blocker cited by the right PR number and the wrong description, and it would have cost a benchmark

**Confidence: verified** — the PR state and file list were re-derived from the GitHub API; the Q4_K numbers are receipted governed runs.

### The mislabelled blocker, and why the label was load-bearing

A tracking row blocked sub-2-bit work on "PR #22836 (AngelSlim kernels)". The **number is right and the description is wrong**: #22836 is the **STQ1_0 / Sherry ternary quantization kernel** (author `sjl623`). There is no llama.cpp PR that adds AngelSlim kernels at all.

The reason this is not a bookkeeping nit: **the PR touches only `arch/arm/` — not a single x86 file.** A dependent benchmark row taken naively on this Zen 5 EPYC host would have landed on the generic scalar `vec_dot` path and measured a fallback while believing it measured the kernel. The mislabel would have produced a number, not an error. Gate status as re-derived on 2026-08-12: #22836 is still `open`, `merged: false` (opened 2026-05-08, last touched 2026-08-10); the CUDA sibling PR #23332 was **closed unmerged** on 2026-05-22.

The generalisable rule: **a citation's identifier and its description are two separate claims, and only the identifier is self-verifying.** Re-derive the description before letting it gate compute — especially when the gated work is architecture-sensitive.

### KV quantization: the first parity-and-headroom package

Measured across f16 / q8_0 / q4_0 KV, retrieval parity holds at **51 of 52 on every arm**. `q4_0` buys **10.54 GiB** at a **−7.4%** decode cost; **q8_0 is dominated** — it gives up the f16 operating point without buying q4_0's memory. Full context and the provisioning consequence are on the [KV Cache](kv-cache.md) page.

### Q4_K on gfx90a: a real correctness defect, root-caused

Stock MMQ Q4_K was failing forced-dispatch correctness at **18/43** (max error ratio 3.0361) while rocBLAS passed 43/43. An independently compiled DP4A arm reproduced the *same* failures, which falsified the MFMA-specific hypothesis and located the defect in shared Q8 activation staging: affine Q4_K reconstruction mixed a **dequantized** Q8 dot term with an **original-float** activation sum in the min correction. Deriving both from the same dequantized population gives **172/172 pass, max error ratio 1.2283**. The fix is uncommitted pending operator approval. The performance side of the same investigation — the retracted "+38–43% single-lever" unpack ceiling, now ~10.5% of which 57% is structurally required — is on [Hardware Optimization](hardware-optimization.md).

### Source References (2026-08-12)

- [`angelslim-techniques-evaluation.md`](../handoffs/active/angelslim-techniques-evaluation.md) — the mislabel correction and the re-derived PR state.
- [`tq3-quantization-evaluation.md`](../handoffs/active/tq3-quantization-evaluation.md) — the mirrored correction and the ARM-only file-scope consequence for Zen 5.
- [`rocm-verify-profile-backend.md`](../handoffs/active/rocm-verify-profile-backend.md) — the Q4_K MMQ correctness matrices and root cause.
- [`progress/2026-08/2026-08-12.md`](../progress/2026-08/2026-08-12.md) — the KV-quant decision package and the "window saved" framing of the mislabel.

## Compiled Update — 2026-07-24

The architect IQ2-vs-Q4 reasoning-certification question (flagged UNDECIDED in the prior compile) advanced on two fronts: a degenerate-repetition defect first suspected as 2-bit EOS damage was refuted as **quant-independent**, and the CPU Q4 arm (A2) ran the same fenced, pinned-item comparison as the GPU IQ2 arm, tracking at-or-above it. Confidence: `verified` for the RP-1/RP-2 measured refutation (McNemar-paired, offline-rescored); `observation` for A2's still-in-progress paired analysis at compile time.

### Key Findings (2026-07-24)

- **The 2-bit-EOS-damage hypothesis is REFUTED: the Qwen3.5-122B-A10B's degenerate `\boxed{}` repetition loop tracks the MODEL, not the quantization.** On `olympiadbench_hard`, the 122B-A10B looped to the token cap on **25% of items at IQ2** — the original evidence for suspecting 2-bit EOS damage — but the **CPU Q4_K_M arm (A2) loops IDENTICALLY on the same item** (item 1: 32768 tokens, tail-uniqueness 0.03, `\boxed{2n-1}`×N repeated at both quants). The Q8 arms (27B-dense, 35B-A3B — different models entirely) never loop (0–1%). One identical Q4 loop is a sufficient counterexample to the quant-attribution hypothesis. Consequence: the fix is a **per-MODEL** repetition-penalty fence (the 122B-A10B, at any quant it is deployed at), never a per-quant or blanket policy — `repeat_penalty 1.1` breaks the loop (truncation ~100%→22%, tokens 32768→10.6k) with accuracy held (22/40 vs baseline 21/40); `1.3` over-penalizes math to ~15% accuracy; DRY (0.8) is inconsistent and sometimes mangles the answer outright. The `\boxed{}` instruction itself is the leading root-cause hypothesis (untested). Because production currently gives the 122B-A10B architect no repetition penalty at either quant, the loop occurs live today, at a real ~2× token/latency operating cost that does **not** distinguish IQ2 from Q4. [architect-model-selection-bench](../handoffs/active/architect-model-selection-bench.md) §RP-1/RP-2, [reasoning-effort-levels](../handoffs/active/reasoning-effort-levels.md) §MODEL-specific repetition-penalty fence

- **The CPU Q4 arm (A2), run fenced overnight on the pinned item sets, is tracking at-or-above the GPU IQ2 arm's reasoning band — the first direct evidence bearing on H1 (does IQ2 preserve the 122B's reasoning relative to Q4?).** With the RP-1 fence applied (`repeat_penalty 1.1`, port 18073, 25.8 tok/s decode): `aime25` 23/30 (76.7%) complete; `olympiadbench_hard` ~72% on the answered items vs A1-IQ2's 68.4% on the same suite. This is a live, not-yet-finalized read — the canonical-extractor paired McNemar analysis was still pending at compile time — but it argues against a large IQ2 reasoning penalty on this model, complementing the knowledge-axis parity already certified (AXA-1 Δ0.0pp, n=212). `gpqa_diamond_cot` was deliberately skipped on this arm (power math: 185 paired items give an MDE of only ~6–7pp, insufficient to detect a subtle 1–2pp degradation, and the +198 in the full set still only reaches ~4pp). [architect-model-selection-bench](../handoffs/active/architect-model-selection-bench.md) §RP-5, [progress 2026-07-24](../progress/2026-07/2026-07-24.md)

### Open Questions (2026-07-24)

- The A2-vs-A1 paired McNemar analysis (canonical rescore) had not landed at compile time — does H1 close as statistical parity, or does a real (if small) IQ2 reasoning penalty emerge once formally tested?
- RP-3 (does the loop occur on real architect planning workloads, or only on `\boxed{}`-style competition-math prompts?) is unresolved and is the leading root-cause lead.
- Should the per-model repetition-penalty fence (RP-4) be added to the production registry now, given production currently runs the 122B-A10B unfenced and the loop is confirmed to occur live?

### Source References (2026-07-24)

- [architect-model-selection-bench.md](../handoffs/active/architect-model-selection-bench.md) §RP series, §A2 — the CPU Q4 arm execution, the quant-attribution refutation, the repetition-penalty probe results.
- [reasoning-effort-levels.md](../handoffs/active/reasoning-effort-levels.md) §MODEL-specific repetition-penalty fence — the per-model (not per-quant) invariant and its production-policy implications.
- [progress 2026-07-23](../progress/2026-07/2026-07-23.md), [progress 2026-07-24](../progress/2026-07/2026-07-24.md) — A2 overnight execution log, RP-1 probe results.

## Compiled Update — 2026-07-20

A five-paper literature cluster (intake-859..863) plus the architect-selection and quant-asymmetric self-spec work reframe low-bit quantization along a **reasoning-vs-knowledge asymmetry**: 2-bit barely touches knowledge but can halve *reasoning* — unless the quant is *dynamic/per-layer*. This directly re-opens the architect-quant question and motivates a new, quality-preserving use of aggressive quant (self-spec drafting). Confidence: `external` for the literature, `verified` for the DR-0 self-spec throughput/quality measurements (observation-grade under `P-GPU-1`), `verified` for the sub-2-bit load/quality failures.

### Key Findings (2026-07-20)

- **Reasoning ∝ ACTIVE params; knowledge ∝ TOTAL params; and 2-bit is asymmetric.** On *our exact toolchain* (llama.cpp GGUF K-quants + Unsloth, DeepSeek-class MoE), MMLU holds ~99% (90.99→89.72) while **uniform Q2_K halves reasoning** (DeepSeek-V3 AIME 38.34→15.41) — but **dynamic per-layer quant holds**: DQ3_K_M ≈ Q4 (75.73 vs 75.79), and Q4 ≈ FP8 (intake-861 `2505.02390`, cred 4). Corroborated: harder tasks (AIME) degrade up to ~4× more than GSM8K, sub-4-bit + activation/KV quant are the danger zones, ≥14B tolerate quant better (intake-863 `2504.04823`, cred 3); low-bit PTQ disproportionately raises *procedural/execution* errors, restorable by a ~332-example recovery-SFT in minutes (intake-860 `2505.11574`, cred 3); reasoning peaks at an optimal active-compute point and is architectural, not rescued by test-time compute or GRPO (intake-859 `2508.18672`, cred 5). ([architect-model-selection-2026-07-20](../docs/reference/architect-model-selection-2026-07-20.md))
- **The architect's IQ2≈Q4 parity is NOT reasoning-certified.** The GPU-resident 122B-A10B UD-IQ2_M candidate's Δ0.0pp parity (212-question paired eval, McNemar p=1.000) was **knowledge/instruction-following-dominated** — the pool was IF (84) + factual QA (72) with only **n≈4 per hard-reasoning suite (~11%)**, and the LLM-rubric gate was deferred. It is a valid *knowledge* parity only; the reasoning axis (exactly what 2-bit erodes) is powerless in that pool. The architect quant choice is therefore **UNDECIDED**, gated behind a full-power AIME'25 + GPQA-Diamond bench: default prior is 122B at **Q4** (safe), IQ2 only if the reasoning re-gate passes, dynamic-3-bit (DQ3) as the mid-precision fallback. ([architect-model-selection-bench](../handoffs/active/architect-model-selection-bench.md))
- **Quant-asymmetric same-model self-spec — a NEW quality-preserving use of aggressive quant.** An aggressive-IQ drafter on the GPU + a high-quant verifier on the CPU is N5-free by construction (identical vocab / M-RoPE / GDN), and the CPU verify **launders quality** (accepted tokens are full-quant). Measured (DR-0e.2, observation-grade): 122B UD-Q4_K_M CPU verifier + 122B UD-IQ2_M MI210 drafter, **K2 = 11.41 t/s (1.61× over 7.08 baseline), alpha 0.90**, 28/28 quality, output byte-stable vs the CPU baseline on every task class. K2 is selected over K4 (K4 adds only +3.85% but alpha drops to 0.787). Default-off research lane; production-named `P-GPU-1` still required. ([quant-asymmetric-self-spec-serving-design](../docs/reference/quant-asymmetric-self-spec-serving-design-2026-07-20.md), [gpu-drafter-control-redesign](../handoffs/active/gpu-drafter-control-redesign.md))
- **Sub-2-bit weight quant is deprioritized (STEERING 2026-07-19).** Bonsai Q1_0 and Ternary Q2_g64 are speed-only and quality-blocked (fail strict instruction/format gates); Ternary Bonsai Q2_0 is a **broken load** (498/498 tensors short, noncanonical PrismML packing ≠ upstream TQ1_0/TQ2_0). Q1_0 (type 41) is already in v6; PrismML Q2_0 landed upstream 2026-07-07, *after* the v6 cutover, so it is **not** in v6. Do not speed-rerun these without a named producer/transcode/loader/prompt fix. ([tq3-quantization-evaluation](../handoffs/active/tq3-quantization-evaluation.md), [model-probe-scoreboard](../docs/reference/model-probe-scoreboard.md))
- **External FP4 / lossless-exponent formats stay non-deployable here.** NVFP4 (intake-756) is GPU-native (no GGUF/MI210 path); its FP8-parity table is an external *bar* for our CPU 4-bit path only. Lossless entropy-coded weight compression (ZipNN/DFloat11/ZipServ, intake-815..818) yields ~11–12 bpw — ~2.5× larger than production Q4_K_M ~4.5 bpw — so it is a storage/download optimization, not an inference win. ([tq3-quantization-evaluation](../handoffs/active/tq3-quantization-evaluation.md))

### Open Questions (2026-07-20)

- Does dynamic UD-IQ2 preserve the 122B-A10B's *reasoning* (not just knowledge)? Only the full-power AIME'25/GPQA bench answers it.
- Is a two-level (per-block FP8 + per-tensor FP32) scale worth emulating in a CPU K-quant variant, or is the accuracy delta below the decision-gating threshold?
- Does the K2 quant-asymmetric self-spec lane survive broader task-class admission and a production-named `P-GPU-1` certification?

### Source References (2026-07-20)

- [architect-model-selection-2026-07-20.md](../docs/reference/architect-model-selection-2026-07-20.md) — reasoning∝active + 2-bit-asymmetry evidence, the Δ0.0pp-parity gap analysis, the decision tree.
- [architect-model-selection-bench.md](../handoffs/active/architect-model-selection-bench.md) — the reasoning re-gate the parity deferred (specced, gated post-v7-promotion).
- [quant-asymmetric-self-spec-serving-design-2026-07-20.md](../docs/reference/quant-asymmetric-self-spec-serving-design-2026-07-20.md) — K2 self-spec design + DR-0e.2 evidence.
- [tq3-quantization-evaluation.md](../handoffs/active/tq3-quantization-evaluation.md) — sub-2-bit stop-list, TurboQuant/ChunkKV monitor, lossless-exponent cluster.
- intake-859 `2508.18672` (cred 5), intake-861 `2505.02390` (cred 4), intake-863 `2504.04823` (cred 3), intake-860 `2505.11574` (cred 3), intake-862 `2604.07035` (cred 2, harness-artifact caveat) — the reasoning-vs-quant literature.

## Summary

Quantization is the foundation of our entire EPYC 9655 inference stack. Every production model runs quantized -- there are no f16 models in the production orchestrator. The standard quant is Q4_K_M, a 4-bit k-quant format in GGUF that reduces model size by approximately 4x (32-bit to 4-bit effective, with mixed-precision block structure) while maintaining quality sufficient for production coding and reasoning tasks. Higher quants (Q6_K, Q8_0) are used for reference benchmarks, and the full range from Q2_K to BF16 is available for most models via community GGUF converters (notably bartowski, who provides 26+ quant variants for popular models).

Our quantization work spans two distinct domains that interact in important ways. **Weight quantization** (model weights stored in GGUF quant types) determines model file size, memory footprint, and per-token compute cost. **KV cache quantization** (key/value cache entries stored at reduced precision during inference) determines context capacity and attention bandwidth. The breakthrough finding in our KV work is that Walsh-Hadamard rotation before quantization eliminates the quality degradation that previously made q4_0 KV unusable: the rotation smooths outlier distributions via orthogonal transform, redistributing magnitude across dimensions so that per-block quantization works uniformly. With Hadamard rotation, q4_0 KV cache achieves PPL +0.017 vs f16 on Qwen2.5-7B -- effectively lossless. This was deployed to production in commit `b51c905` and is now auto-enabled in llama.cpp v3 upstream (PR #21038).

The interaction between weight quantization and other optimization techniques produces some of the most practically important findings in our research. DFlash speculative decoding was closed for our Q4_K_M stack at 27% per-token acceptance (March; no run receipt survives), and the attribution to quantized hidden states corrupting the conditioning signal is a hypothesis, not an established cause: the often-quoted 6.49 is the DFlash paper's tokens-per-round on f16, a different unit, and Laguna on CPU moved only 17.2% (Q4_K_M) to 19.0% (Q8_0) with BF16 targets untested (speculative-decoding-mtp-refresh causal correction 2026-07-29; intake-1505). REAP expert pruning on MoE models produces standard safetensors that feed directly into `convert_hf_to_gguf.py`, enabling a clean "prune then quantize" double compression pipeline that achieves approximately 6.5x total compression. KV cache quantization stacks orthogonally with KV compaction and selection: the theoretical quad-stack ceiling (weight quant + KV quant + compaction + selection) could reach 120x total KV reduction, though pairwise quality validation is still in progress.

The quantization landscape in llama.cpp is evolving. The mainstream path is ggerganov's Hadamard rotation for existing quant types (PR #21038), which auto-applies Walsh-Hadamard transform when KV types are quantized. More exotic approaches -- TQ3_1S (Walsh-Hadamard transform weight quantization at 3.5 bits), TurboQuant (extreme KV cache compression), PolarQuant (polar transformation for KV cache) -- have been evaluated and placed on monitor-only status. TQ3_1S was downgraded due to immaturity (3 commits, 1 contributor, no CPU kernels), wrong benchmarking target (vs Q4_0 not Q4_K_M), and a 2.2x speed disadvantage vs Hadamard+q4_0 on EPYC 9975 even with all ecosystem fixes. TurboQuant and PolarQuant were abandoned after Hadamard+q4_0 matched their quality with zero complexity. The lesson: incremental improvements to existing, well-optimized quant types consistently beat exotic new formats on CPU hardware where AVX-512 dequant throughput dominates.

## Key Findings

### 2026-07-06 — MI210 (gfx90a) quant-roofline: Q8 is the sweet spot, Q4_K is dequant-bound (capacity-only), F16 buys precision at ~30% aggregate — ⚠️ COMPILE-FLAGGED FOR HUMAN REVIEW

> **Review flag (project-wiki writer-evidence policy):** model-compiled from the MI210 GPU campaign; **not adopted until human or measured review**. Every throughput/roofline number is an **OBSERVATION** (single MI210, serial/aggregate, seed 42, no P-GPU-1 per MEASUREMENT.md). Sources: [findings-05c lever × category matrix (Axis-C quant)](../handoffs/active/fable5-window2-findings-05c-mi210-lever-category-matrix.md), [progress 2026-07-06 v7-candidate + GPU levers](../progress/2026-07/2026-07-06-v7-candidate-and-gpu-levers.md), [progress 2026-07-02 MI210 first-touch](../progress/2026-07/2026-07-02-mi210.md).

- **Q8_0 is the gfx90a decode sweet spot; the Q8/Q4_K "roofline gap" is a dequant-boundedness artifact, not general kernel immaturity.** On the MI210, batch-1 quantized decode reaches ~**47% of the ~1.64 TB/s HBM roofline at Q8_0** vs ~**33% at Q4_K_M** vs **~62% at fp16** (no dequant). The residual is specifically the quantized MMQ dequant kernels: **Q8_0's GEMV is already int8-native** (`vec_dot_q8_0_q8_1` = `dp4a` + one fp scale per 32-block — there is no per-element dequant to hide), so the 47→62% gap is BW/occupancy, not dequant cycles; **Q4_K_M is genuinely dequant-bound** (a bigger 33→47% gap). Consequence: **Q4_K on gfx90a is a *capacity-only* quant** — it buys VRAM footprint, not speed, and a Q4_K dequant-efficiency kernel is a separate ~+43%→~47 t/s bet (quality-gated, kernel un-authored). Q8 is the quant to serve at when capacity permits.
  - **⚠ CORRECTED 2026-08-16 — the attainment ordering survives, the serving conclusion does not.** The 8-rung single-model ladder (Goedel-8B, frozen v9 `0db32c06e`; see the top section) reproduces this bullet's *roofline-attainment* ordering — Q8_0 60.2% of achievable bandwidth vs Q4_K_M 38.1% — but **inverts the absolute batch-1 decode ranking: Q4_K_M 108.75 t/s vs Q8_0 99.09 t/s (+9.7% for Q4_K_M), with IQ4_XS fastest at 129.77 t/s.** Roofline-% and absolute t/s are different metrics and rank differently, because a smaller model reads fewer bytes per token; a low attainment figure is not by itself a reason to serve the larger quant. So **"Q4_K on gfx90a is a *capacity-only* quant — it buys VRAM footprint, not speed" is contradicted on absolute decode throughput**, and "Q8 is the quant to serve at when capacity permits" does not hold for batch-1 decode on the model measured. Carry the caveats: the ladder is n=1 per cell, no A/A band, one 8B dense model, speed-only, and `design_prior`-grade; this bullet's own figures are a separate single-run observation on a 27B against the 1638 GB/s *spec* denominator rather than the 1433.3 GB/s *achievable* one, so the two are not a clean A/B. What is settled is that the causal story must change: the sub-4-bit part of the ladder is bounded by **kernel register pressure / occupancy**, not by dequant arithmetic.
- **F16 aggregate throughput costs ~30% vs Q8 — it is a *precision* choice, never a throughput one.** On the v7-candidate aggregate spec sheet, Qwen3.6-27B F16-proxy runs **141 t/s @B32 vs Q8's 199** (−29%) — F16's doubled weight bytes dominate a BW-bound decode. (The batched regime *does* flip for bf16 on a different axis — at B≥16–24 bf16 wins because it runs native on CDNA2 matrix cores with nothing to dequant-amortize while Q8 pays a per-tile dequant tax — but that is HBM-capacity-gated and distinct from the F16-precision cost here; see [Hardware Optimization](hardware-optimization.md) for the bf16↔Q8 crossover.)
- **MTP repays ~4× more on F16 than on Q8 — the more BW-bound the weight read, the more each accepted draft token saves.** On a Qwen3.6-27B Q8→F16 dequant proxy (values preserved so acceptance α≈Q8's, isolating the kernel path): MTP gives **+60.2% on F16 vs +15.6% on Q8** at essentially unchanged α (66.9%). This is a pure bandwidth effect — F16 is 2 bytes/param, so a self-drafted token that lands avoids a fatter weight read — and it is the quantization-level analog of the general "spec-dec pays most where decode is most BW-bound" rule. It does **not** make F16 a throughput choice: absolute F16-MTP 31.0 t/s stays below Q8-MTP+MMQ 40.4; MTP just makes the precision far cheaper. See [Speculative Decoding](speculative-decoding.md).

### 2026-06-26 v6 cutover — iqk AVX-512 GEMM kernels integrated into the production kernel

- **The production kernel is now `production-consolidated-v6`, which integrates ik_llama's `iqk_mul_mat` AVX-512 GEMM kernels (runtime-gated `GGML_IQK=1`), giving ~+11% vs ik_llama on quantized CPU decode for the gemma worker** (and prefill +22–49% / decode +8–9% across the stack's Q4_K_M and Q8_0 patterns). This is the same "AVX-512 throughput dominates" lesson that governs quant-format viability on this CPU (see Related Categories), now realized by faster quantized-matmul kernels rather than a new quant format. The cutover folds the gemma worker's quantized decode path off its former separate ik_llama.cpp binary onto this one kernel — **ik_llama.cpp is fully deprecated**; any remaining `ik_llama.cpp` references on this page (e.g. the `deepseek4`/STQ1_0 port gates) now mean the consolidated v6 kernel.
- The v5 `--kv-hadamard` flag is removed in v6; Walsh-Hadamard KV rotation is auto-applied when KV types are quantized (already noted under KV Cache Quantization). Q8_0 weight decode through the iqk path is non-bit-exact by design — operator-run eval-suite parity is the deploy gate. Status: cutover executed 2026-06-26, live throughput/garbage verification PENDING. Tracking: [v6-iqk-promotion.md](../handoffs/completed/v6-iqk-promotion.md).

### 2026-07-17 — stale-fork quant gap (Q2_0), x86 Q8_0 repack still un-promotable, and BF16 KV is not a win

- **A frozen experimental branch silently *loses* new upstream quant types — "missing Q2_0" is a freshness-audit hit, not a cherry-pick task.** llama.cpp added two sub-2-bit weight types authored by PrismML for Bonsai: **`Q1_0`** (1-bit, merged 2026-04-06) and **`Q2_0`** (ternary group-64, CPU merged 2026-07-07). Verified enum state: both `production-consolidated-v6` and the `experimental-v7-candidate` carried `GGML_TYPE_Q1_0` but **not `GGML_TYPE_Q2_0`**, because Q2_0 merged 11 days *after* the v6 cutover and the v7 branch forked from that pre-Q2_0 tip. The correct remedy is the mandated fresh-pull from a post-2026-07-07 upstream tip (which reinstates Q2_0 and everything else post-cutover, validated together) — **NOT** hot-cherry-picking Q2_0 into frozen v6 or the candidate, which violates the "full build, validated together" rule. This is the same stale-fork class as the 2026-06-22 iqk near-miss; the v7 refresh `8e5c555ab` restored Q2_0 by merging `origin/master`. Sub-2-bit's only near-term consumer is Ternary-Bonsai-27B (contested quality; HF gibberish reports), so refresh for correctness, not for Q2_0 alone. Sources: [speculative-decoding-mtp-refresh.md](../handoffs/active/speculative-decoding-mtp-refresh.md), [gemma-challenge-kernel-techniques-v7.md](../handoffs/active/gemma-challenge-kernel-techniques-v7.md).
- **There is still no promotable *optimized* x86 Q8_0 repack kernel; a generic scalar 8x8 interleave is correctness-feasible but slower, and the default now routes Q8_0 to native rather than iqk.** K27 confirmed x86 has no Q5_0/Q6_0 repack and Q8_0 lacks a promotable interleave. A generic Q8_0 8x8 repack was implemented behind `GGML_REPACK_Q8_0_8X8=1` but **regressed** (Qwen3-4B Q8 prompt `209→17 t/s`, decode `8.10→7.65`), so it was retired; upstream master no longer carries that route either. Separately, `GGML_IQK=1` was changed so `GGML_TYPE_Q8_0` **falls through to native CPU kernels unless `GGML_IQK_Q8_0=1` is set** — on the frontdoor Qwen3.6-35B Q8 the native path (`21.38 t/s`) beat the old iqk Q8 path (`20.98`), while small Qwen3-4B Q8 still favors iqk-opt-in (`9.14` vs `8.90`). So iqk-for-Q8 is now a model-specific opt-in, not the default. All numbers observation-grade (pinned-library CPU smokes). Sources: [gemma-challenge-kernel-techniques-v7.md](../handoffs/active/gemma-challenge-kernel-techniques-v7.md), [progress 2026-07-17](../progress/2026-07/2026-07-17.md).
- **BF16 KV cache is not a throughput win on the MI210 — keep F16 KV; mixed K/V BF16 is a large regression.** K26 benched four KV dtype arms on Qwen3.6-35B-A3B-MTP-Q8_0 (MI210): `llama-bench` decode `f16/f16 100.0` vs `bf16/bf16 80.9` t/s, and the two *mixed* arms (`bf16/f16`, `f16/bf16`) collapsed to ~13 t/s; prompt-processing showed the same pattern (`f16/f16 2256` vs mixed `531–1110` t/s). Server decode had `bf16/bf16` close (`100.2` vs `104.4`) but never faster. Verdict: do not switch KV defaults to BF16; mixed-precision K/V BF16 is a trap. Quality was not gated, so treat as config-performance evidence only. Sources: [gemma-challenge-kernel-techniques-v7.md](../handoffs/active/gemma-challenge-kernel-techniques-v7.md), [progress 2026-07-17](../progress/2026-07/2026-07-17.md).
- **Very-low-bit quant (IQ2) is suspected to degrade *format compliance* (strict instruction-following / typed emission), not just knowledge — treat GBNF grammar-constraint as the expected mitigation, and measure the degradation per capability.** The reviewer-capability track flags that a 122B model at IQ2 scored only `2/11` on strict instruction-following, motivating a schema-valid-emission probe (grammar-constrained vs free-parse-with-retry) before trusting a heavily-quantized model to emit typed decisions; separately, intake-836 warns IQ2 may degrade *why-diagnosis* more than *that-detection*, so the rule is measure-don't-assume per axis. This is a capability×quant interaction that a PPL or knowledge-suite gate would miss. Sources: [glm52-reviewer-capability-gates.md](../handoffs/active/glm52-reviewer-capability-gates.md), [glm51-reap-cpu-evaluation.md](../handoffs/completed/glm51-reap-cpu-evaluation.md).

### Weight Quantization

- **Q4_K_M is the production standard**: 4-bit k-quant with mixed-precision block structure. Used for current production models such as Qwen3-Coder-30B-A3B frontdoor (approximately 18 GB), Qwen2.5-Coder-32B coder escalation (approximately 18.5 GB), and Qwen3.5-122B-A10B architect_general (approximately 69 GB). The retired REAP-246B architect_coding row is historical only. Quality is sufficient for agentic coding, tool calls, multi-turn reasoning, and mathematical problem solving. Q4_K_M was confirmed as the optimal coder quant in March 2026 after sweep testing. [Project memory: project_coder_quant_decision.md]

- **Q4_K_M and the DFlash conditioning signal (hypothesis, not established)**: DFlash speculative decoding extracts hidden states from specific target model layers as conditioning input to the drafter. On Q4_K_M our March run reported 27% per-token acceptance and 1.4% block acceptance; the "6.49" it was compared against is the DFlash paper's tokens-per-round on f16 GPU, a different unit. The original conclusion that quantization noise in the extracted hidden states corrupts the conditioning "beyond recovery" is not supported: no run receipt for the 27% survives, Laguna on CPU moved only 17.2% (Q4_K_M) to 19.0% (Q8_0), BF16/F16 targets are untested, and a published two-stage retrain against a quantized target recovers only ~1% (intake-1505). The missing control is filed in speculative-decoding-mtp-refresh.md. [DFlash deep-dive](../research/deep-dives/dflash-dart-diffusion-speculation.md), [DFlash handoff](../handoffs/completed/dflash-block-diffusion-speculation.md)

- **REAP + quantization is a clean pipeline**: REAP expert pruning outputs standard HuggingFace safetensors with fewer experts per MoE layer. `convert_hf_to_gguf.py` processes these identically to unpruned models. The GGUF files use standard architecture strings (`qwen3moe`, `deepseek2`) and require no custom code. bartowski has produced 26 quant variants for REAP-25B alone. The double compression pipeline (REAP 50% + quantization) achieves approximately 6.5x total compression: 0xSero demonstrated this on GLM-4.7 (700 GB to 92 GB with AutoRound W4A16). [REAP deep-dive](../research/deep-dives/0xsero-reap-ecosystem-deep-dive.md)

- **GGUF ecosystem is the deployment gateway**: All models in our stack go through GGUF conversion as the final deployment step. Community converters (bartowski, unsloth, jackcloudman) provide pre-quantized GGUFs for popular models. For custom models (REAP outputs, Memento LoRA fine-tunes), the `convert_hf_to_gguf.py` and `convert_lora_to_gguf.py` scripts handle conversion. LoRA adapters are loadable at inference with `llama-server --lora adapter.gguf`. The GGUF format supports arbitrary metadata tensors, which is relevant for future extensions like steering vectors or per-token attention biases. [Various handoffs]

### KV Cache Quantization

- **Hadamard+q4_0 is quality-neutral and deployed**: Walsh-Hadamard rotation (orthogonal transform that preserves norms) applied before q4_0 quantization of KV cache entries. PPL increase of +0.017 on Qwen2.5-7B at 512 tokens. Needle-in-haystack: 9/9 correct at 1K/4K/16K on Coder-32B. Zero overhead in speed at short context (within 2% of f16). Production config: `-ctk q4_0 -ctv f16` for pure-attention models (Qwen2.5-Coder-32B), `-ctk q4_0 -ctv q4_0` for hybrid SSM models (Qwen3.5-35B-A3B where 75% recurrent layers absorb quantization error). Deployed since commit `b51c905` on `production-consolidated-v2`. [KV cache quantization handoff](../handoffs/completed/kv-cache-quantization.md)

- **q4_0 Key cache degrades at extended context without Hadamard**: At 32K context on pure-attention Qwen2.5-7B, q4_0/q4_0 (both K and V quantized) produces garbage output; q8_0/q4_0 remains correct. The cumulative quantization error in Key vectors compounds over long sequences, corrupting attention patterns. Hadamard rotation fixes this by distributing magnitude uniformly before quantization, but the safe production config still uses f16 for Values on pure-attention models to maintain quality margin. For hybrid SSM models, q4_0/q4_0 is validated safe because the 75% recurrent layers provide an alternative information path. [KV cache quantization handoff](../handoffs/completed/kv-cache-quantization.md)

- **Upstream auto-enables Hadamard rotation in v3**: llama.cpp v3 upstream PR #21038 by ggerganov (`744c0c731`) auto-applies Walsh-Hadamard rotation when KV types are quantized. The `--kv-hadamard` flag from our production branch is superseded. Quality improvements reported: Q4_0 KV PPL improves 25-77% on small models, Q8_0 with rotation matches f16 on reasoning benchmarks. This is a free upgrade on rebuild -- no model re-quantization needed. [TQ3 monitor handoff](../handoffs/active/tq3-quantization-evaluation.md), [v3 rebuild handoff](../handoffs/completed/llama-cpp-v3-upstream-rebuild.md)

- **At long context, KV quantization provides throughput gain beyond memory savings**: At short context (4K or less), attention is 7-12% of per-token time -- KV quantization saves memory only. At 16K+, attention rises to 25-35% and becomes compute-bound. At very long sequences (S >> d_model), attention exceeds 50%. Fewer KV bytes means faster attention matmuls, so KV compression delivers a throughput improvement proportional to the attention fraction. The +9% wall time increase observed at 32K (q8_0/q4_0 with dequant overhead) likely reflects dequant cost offsetting the attention speedup -- upstream's auto-rotation may be more optimized. [KV cache quantization handoff](../handoffs/completed/kv-cache-quantization.md)

### Sub-2-bit Weight Quantization (Tencent AngelSlim cluster, 2026-05-21)

- **Sherry 1.25-bit ternary quantization via 3:4 fine-grained sparsity (ACL 2026)**: Tencent's AngelSlim toolkit introduces a 1.25-bit weight regime by packing 4 ternary weights ({-1, 0, +1}) into 5 bits with power-of-two SIMD alignment, resolving the prior ternary-quant dilemma between 2-bit aligned packing (bit-wasteful) and 1.67-bit irregular packing (slow inference). Pairs with "Arenas" annealing-residual-synapse to prevent representational collapse during QAT. Reported: zero accuracy loss vs SOTA ternary baselines on LLaMA-3.2-1B, 25% bit savings, 10% inference speedup on Intel i7-14700HX. **Key constraint — Sherry is QAT, not PTQ**: applying it to an arbitrary post-trained worker requires ~10B tokens of QAT training on UltraFineWeb-style data. Today the only public Sherry-QAT'd weights are `AngelSlim/Hy-MT1.5-1.8B-1.25bit`, `AngelSlim/HY-1.8B-2bit`, and `AngelSlim/Hy-MT2-1.8B-1.25bit-GGUF` (440 MiB). [AngelSlim techniques handoff](../handoffs/active/angelslim-techniques-evaluation.md), [Sherry arxiv:2601.07892](https://arxiv.org/abs/2601.07892), [AngelSlim toolkit arxiv:2602.21233](https://arxiv.org/abs/2602.21233)

- **STQ1_0 llama.cpp PR #22836 is the load-bearing kernel**: Tencent submitted a sub-2-bit weight-quant kernel that decodes the Sherry 3:4-packed format. This is the directly mergeable artifact for `epyc-llama` — generic at inference, independent of who produced the weights. Hy-MT2-1.8B-1.25bit reference weights downloaded 2026-05-21 to `/mnt/raid0/llm/models/hy-mt2-1.8b/1.25bit/`. **Generalization to EPYC's BW-bound regime is unverified**: Sherry's 10% speedup was measured on a single-CPU laptop (Intel i7-14700HX, 2-channel DDR5); EPYC 9655's CPU decode is DRAM-bandwidth-bound (12-channel DDR5), so the speedup pattern may not transfer. [llama.cpp PR #22836](https://github.com/ggml-org/llama.cpp/pull/22836), [llama-cpp kernel push handoff](../handoffs/completed/llama-cpp-kernel-push-rebase.md)

- **The kernel is generic; the algorithm is not** (correction logged 2026-05-21): Unlike GPTQ / AWQ / Q4_K_M which are post-training calibration passes applicable to any pretrained model, Sherry requires running QAT from scratch (or QAT fine-tune). Without a QAT pipeline (which EPYC operating constraints preclude), STQ1_0 is "a decoder for weights only Tencent currently produces, and only at 1.8B class." Real EPYC adoption is gated on either Tencent (or another party) releasing Sherry-QAT'd checkpoints of an EPYC-stack base model, or us acquiring training infrastructure. [Mid-intake correction note in handoff](../handoffs/active/angelslim-techniques-evaluation.md#important-scope-correction-2026-05-21)

- **Tequila trapping-free ternary QAT (arxiv:2509.23809) — same QAT-gating limitation as Sherry**: Identifies "deadzone trapping" as the root cause of ternary-quant accuracy loss and proposes repurposing trapped weights as dynamic biases (continuous forward signal + meaningful gradients during backprop). Claims >4% ARC gain over SOTA ternary, within <1% of full-precision, 3.0x inference speedup. Training-time only; adoption blocked on the same QAT-pipeline gate. Deferred. [Tequila arxiv](https://arxiv.org/abs/2509.23809), [TQ3 quant handoff](../handoffs/active/tq3-quantization-evaluation.md)

- **DAQ delta-aware PTQ (arxiv:2603.22324) — data-free, but FP8-only evidence at intake time**: Replaces reconstruction-error PTQ with Sign-Preservation-Rate + Cosine-Similarity-of-ΔW metrics to preserve post-training capabilities (RL / DPO / instruction-tune deltas) that standard PTQ over-attenuates. The load-bearing question (does DAQ help at INT4 / INT2 where standard PTQ breaks?) is unanswered in the abstract — FP8 testing only, where standard PTQ is already near-lossless. Becomes relevant only if/when we move below Q4_K_M. [DAQ arxiv](https://arxiv.org/abs/2603.22324)

- **AngelSlim toolkit license inconsistency**: GitHub README declares custom Tencent proprietary license; arxiv paper (2602.21233) claims CC-BY-4.0. Blocks wholesale toolkit adoption. The llama.cpp STQ1_0 PR sidesteps via MIT-licensed upstream — cherry-pick individual algorithms via PRs only. [AngelSlim techniques handoff](../handoffs/active/angelslim-techniques-evaluation.md)

### Exotic Quantization (Evaluated and Rejected/Deferred)

- **TQ3_1S is on monitor-only -- do NOT merge**: 3.5-bit Walsh-Hadamard transform weight quantization. Downgraded from "evaluate" to "monitor" due to: immaturity (3 commits, 1 contributor, no CPU kernels, undocumented conversion tool), wrong benchmarking target (only vs Q4_0, no Q4_K_M comparison, no Qwen2.5 tests, author warns smaller models are "much less forgiving"), our capacity is not constrained (ample RAM on EPYC 9655, Q4_K_M fits comfortably, bottleneck is throughput not capacity), and upstream divergence (ggerganov working on Hadamard for existing types via PR #21038, no new types needed). MoE risk: WHT rotation creates approximately 367K ghost activations per forward pass, potentially shattering sparse routing on MoE models. [TQ3 monitor handoff](../handoffs/active/tq3-quantization-evaluation.md)

- **TQ3 is 2.2x slower than Hadamard+q4_0 on EPYC even with all fixes**: ikawrakow's full implementation (all four ecosystem fixes: norm correction, S=512 initial layers, fused dequant, 32-block format) on EPYC 9975 shows Hadamard+q4_0 at 1279 tok/s vs TQ3 at 573 tok/s. Even with fused dequant that bypasses per-element dequantization via codebook dot product, the fundamental overhead of codebook lookup vs simple q4_0 dequant on AVX-512 is too large. Revisit only if upstream merges TQ3 natively with fused flash attention kernel AND comparison on 32B+ models shows both quality AND speed parity. [TQ3 monitor handoff](../handoffs/active/tq3-quantization-evaluation.md), [KV cache quantization handoff](../handoffs/completed/kv-cache-quantization.md)

- **TurboQuant (TBQ3_0/TBQ4_0) for KV cache deferred to upstream**: PR #21089 proposes 3-bit and 4-bit KV cache quantization with CPU kernels, claiming 5.2x KV cache compression with minimal PPL loss. Under review upstream. Our Hadamard+q4_0 achieves similar results with proven quality and zero new types. Monitor for merge; evaluate if it offers throughput advantage via native kernel optimization. [TQ3 monitor handoff](../handoffs/active/tq3-quantization-evaluation.md)

- **PolarQuant abandoned**: 5.12x compression with PPL +0.229 on Qwen2.5-7B. Working end-to-end in experimental but quality gap vs Hadamard+q4_0 (+0.017 PPL) makes it non-competitive. The polar coordinate transformation adds complexity without proportional quality benefit. [KV cache quantization handoff](../handoffs/completed/kv-cache-quantization.md)

- **QJL (1-bit Quantized JL Transform) evaluated**: Gaussian Johnson-Lindenstrauss projection for KV cache compression with zero-overhead claim. Attention kernel wired into `ops.cpp` with outlier correction. Abandoned as part of the TurboQuant/PolarQuant/QJL cluster after Hadamard+q4_0 proved sufficient. The JL approach is theoretically elegant but practically unnecessary when Hadamard rotation makes standard q4_0 work. [KV cache quantization handoff](../handoffs/completed/kv-cache-quantization.md)

- **Hybrid precision buffer architecture is memory-negative**: The experimental dual-cache design (kv_recent at f16 + kv_old at q4_0+Hadamard) with ISWA-style split attention allocates BOTH caches at full context size, using MORE memory than a single f16 cache. Split attention works correctly (separate QK scoring for old and recent, concat scores, single softmax, combined V weighted sum) at 5.2 t/s on 14.5K context, but the standard single-cache with quantized KV types is strictly better for production use. Archived as research on `hadamard-kv-smoothing` branch. [KV cache quantization handoff](../handoffs/completed/kv-cache-quantization.md)

### Quantization Interactions with Other Techniques

- **KV quantization stacks with KV compaction (validated pairwise)**: Attention Matching compaction validated on Coder-32B-Q4KM at 5x compression with zero degradation. The compaction step operates on dequantized attention scores, fits compact representations, and the results can be re-quantized. Theoretical combined ceiling: 4x (quantization) times 5x (compaction) = 20x. Triple-stack with block masking: up to 120x. Quality under multi-layer compression is the key unknown -- each layer claims minimal individual loss but combined degradation may be multiplicative. [AM handoff](../handoffs/active/attention-matching-kv-compaction.md)

- **Hadamard rotation preserves properties needed by KV selection**: TriAttention's trigonometric scoring uses pre-RoPE Q/K centers (offline calibrated) and current K norms (online). Hadamard rotation is an orthogonal transform that preserves norms, so the online K norm signal should survive Hadamard. However, q4_0 quantization introduces norm error after rotation. The net effect on selection scoring is untested -- this is the critical gate for the selection+quantization stacking hypothesis. Expected Attention's paper explicitly claims orthogonality with quantization methods. [TriAttention deep-dive](../research/deep-dives/triattention-kv-selection-cluster.md)

- **Control vector / steering vector transfer across quant levels is unvalidated**: FlowSteer and S3-CoT reasoning compression techniques compute steering vectors from f16 model activations. When applied to Q4_K_M quantized models, the vectors are added to the f32 residual stream (which exists during forward pass even with quantized weights). The operation is mechanically feasible but quality transfer is unvalidated -- no published work tests steering vector efficacy across quantization levels. This blocks adoption of activation steering for reasoning compression. [FlowSteer deep-dive](../research/deep-dives/flowsteer-concise-reasoning.md), [S3-CoT deep-dive](../research/deep-dives/reasoning-compression-s3cot-adaptive.md)

- **LoRA fine-tunes convert cleanly to GGUF via llama.cpp tooling**: Memento LoRA adapters (rank=16, alpha=32, targeting q/k/v/o/gate/up projections, approximately 393K trainable params for 1.7B model) convert via `convert_lora_to_gguf.py`, loadable at inference with `llama-server --lora adapter.gguf`. Whether quantized base models retain the quality of Memento's implicit KV information channel (the dual stream finding) after LoRA application is an open question. [Memento handoff](../handoffs/active/memento-block-reasoning-compression.md)

## Actionable for EPYC

- **Deployed**: Hadamard+q4_0 KV cache quantization (production since `b51c905`, auto-enabled in v3 upstream). Q4_K_M weight quantization across all production models. REAP+Q4_K_M double compression for the retired architect_coding (246B) experiment.

- **Monitor and rebuild**: When llama.cpp v3 upstream PR #21038 merges, rebuild production binary for automatic Hadamard rotation. Remove `--kv-hadamard` from orchestrator config -- rotation becomes automatic. Potential optimization over our manual implementation

- **Validate dual compression stack**: AM + Hadamard q4_0 pairwise quality test (P4 in AM handoff). This directly validates the 8-20x combined KV reduction promise at production scale. If quality holds, the deployment impact is transformative (256K context from 64 GB to 3-8 GB KV)

- **Evaluate upstream TBQ3_0/TBQ4_0**: When PR #21089 merges, test on Coder-32B. Compare KV cache PPL and decode throughput against current Hadamard+q4_0. If TBQ offers better throughput via native kernel, it may replace our current KV quant config

- **Revisit TQ3 weight quant only if**: upstream merges natively + multi-model benchmarks exist + Q4_K_M comparison available + CPU kernels optimized for AVX-512. Do not invest effort until these conditions are met

- **Priority**: LOW for new quantization work. Hadamard+q4_0 is deployed and quality-neutral. The primary quantization-related action items are stacking validation (with compaction and selection) rather than new quantization formats. Further KV compression gains come from compaction (AM) and selection (Expected Attention/TriAttention), not from squeezing more bits out of quantization

## Open Questions

- Does the KV quantization + compaction stack maintain quality on coding benchmarks at production-length contexts (32K+)? The AM P4 test is the critical validation
- Can the triple-stack (quantization + compaction + block masking) achieve the theoretical 120x ceiling without catastrophic quality collapse? Each pair needs testing before three-way
- Does Hadamard rotation interact with Expected Attention's Gaussian scoring or TriAttention's trigonometric scoring? The rotation preserves norms but changes the distribution shape -- selection algorithms may need recalibration
- Will upstream TBQ3_0/TBQ4_0 offer throughput advantages over Hadamard+q4_0 via native kernel optimization? The quality should be similar but throughput may differ due to different dequant paths
- Can steering vectors computed from f16 models transfer cleanly to Q4_K_M for reasoning compression? No published validation exists
- Does Memento's implicit KV information channel survive quantization? If KV states carry information beyond text (the 15pp dual-stream finding), does quantizing those states degrade the implicit channel?
- What is the practical quality floor for ChunkKV (arXiv:2502.00299), which claims 12% KV retention matching full cache quality? If validated, this would be the most aggressive training-free compression
- Does Sherry 1.25-bit scale beyond 3B params? Paper explicitly caps eval at 3B as "primary candidates for local edge deployment." EPYC workers are 26-122B class — generalization unverified
- Does Sherry's 10% laptop-CPU speedup transfer to EPYC's BW-bound regime? Sherry's measurement on Intel i7-14700HX (2-channel DDR5) was likely ALU-limited; EPYC 9655 (12-channel DDR5) is DRAM-bandwidth-bound, where the bit-rate advantage matters more than the SIMD packing
- Will any party release Sherry-QAT'd or Tequila-trained checkpoints of an EPYC-stack base model (Qwen3.6, gemma4-26B-A4B, Qwen3.5-122B-A10B, Qwen3-Next-80B)? Until they do, STQ1_0 kernel is a decoder without weights

## Related Categories

- [KV Cache Optimization](kv-cache.md) -- KV quantization is the first deployed layer of the four-layer KV compression stack. Hadamard+q4_0 provides the foundation that compaction (AM), selection (Expected Attention/TriAttention), and block masking (Memento) build upon
- [Speculative Decoding](speculative-decoding.md) -- Weight quantization (Q4_K_M) determines verification cost profile (f16: 1.69x at N=64 vs Q4_K_M: 4-5x). Hidden-state quantization as the cause of DFlash's low acceptance is a hypothesis, not established (our 27% per-token vs the paper's 6.49 tokens-per-round are different units; corrected 2026-09-23)
- [MoE Optimization](moe-optimization.md) -- REAP pruning produces standard safetensors compatible with GGUF quantization. Double compression pipeline (prune + quantize) achieves approximately 6.5x total
- [Hardware Optimization](hardware-optimization.md) -- AVX-512 dequant throughput determines which quant formats are viable on CPU. TQ3's codebook lookup is 2.2x slower than q4_0 dequant despite theoretical bit-rate advantage

## Source References

- [KV Cache Quantization Handoff](../handoffs/completed/kv-cache-quantization.md) -- Hadamard Phase 1 deployed, hybrid buffer archived, TurboQuant/PolarQuant/QJL abandoned, split attention working but unnecessary, long-context degradation analysis, production validation results
- [TQ3 Monitor Handoff](../handoffs/active/tq3-quantization-evaluation.md) -- TQ3_1S on monitor-only status, PR #21038 Hadamard auto-rotation, PR #21089 CPU TurboQuant, ChunkKV tracking
- [AM Handoff](../handoffs/active/attention-matching-kv-compaction.md) -- Compaction validated on Q4KM Coder-32B, stacking hypothesis
- [TriAttention Handoff](../handoffs/active/triattention-kv-selection.md) -- Selection + quantization stacking gates (S3)
- [REAP Handoff](../handoffs/completed/reap-moe-expert-pruning.md) -- Double compression pipeline, bartowski GGUF availability
- [DFlash Deep-Dive](../research/deep-dives/dflash-dart-diffusion-speculation.md) -- the Q4_K_M hidden-state degradation hypothesis (paper 6.49 tokens-per-round vs our 27% per-token — different units; the causal reading is not established, corrected 2026-09-23)
- [REAP Deep-Dive](../research/deep-dives/0xsero-reap-ecosystem-deep-dive.md) -- bartowski 26 quant variants, double compression pipeline, GGUF conversion path
- [TriAttention Deep-Dive](../research/deep-dives/triattention-kv-selection-cluster.md) -- Quantization interaction unknown for trigonometric/Gaussian scoring
- [Memento Deep-Dive](../research/deep-dives/memento-iterative-reasoning-cluster.md) -- KV quantization + block masking + selection triple-stack ceiling, LoRA-to-GGUF conversion
- [Leanstral Analysis](../research/deep-dives/leanstral-architecture-analysis.md) -- GGUF availability (Q4_K_M approximately 68 GB), community converters
- [v3 Rebuild Handoff](../handoffs/completed/llama-cpp-v3-upstream-rebuild.md) -- PR #21038 auto-Hadamard
- [intake-191](https://research.google/blog/turboquant-redefining-ai-efficiency-with-extreme-compression/) TurboQuant -- Extreme KV cache compression (abandoned)
- [intake-192](https://arxiv.org/abs/2502.02617) PolarQuant -- Polar transformation KV quantization (abandoned)
- [intake-193](https://arxiv.org/abs/2406.03482) QJL -- 1-bit JL transform for KV cache (evaluated, abandoned)
- [intake-194](https://github.com/spiritbuun/llama-cpp-turboquant-cuda) llama-cpp-turboquant-cuda -- CUDA TurboQuant fork (GPU-only, not applicable)
- [intake-195](https://github.com/ggml-org/llama.cpp/discussions/20969) TurboQuant llama.cpp discussion -- Community discussion on KV compression
- [intake-590](https://arxiv.org/abs/2602.21233) AngelSlim -- Tencent model-compression toolkit unifying Sherry / Tequila / DAQ / SpecExit / Eagle3. License inconsistency between GitHub and arxiv blocks toolkit-level adoption; cherry-pick individual algorithms via PRs
- [intake-591](https://arxiv.org/abs/2601.07892) Sherry -- 1.25-bit hardware-efficient ternary via 3:4 sparsity (ACL 2026). QAT-only; STQ1_0 kernel at llama.cpp PR #22836. Reference weights `AngelSlim/Hy-MT2-1.8B-1.25bit-GGUF` (440 MiB) on disk
- [intake-593](https://arxiv.org/abs/2509.23809) Tequila -- Trapping-free ternary QAT; deadzone-bias repurposing
- [intake-594](https://arxiv.org/abs/2603.22324) DAQ -- Delta-aware PTQ via Sign-Preservation-Rate + Cosine-Similarity-of-ΔW; FP8-only evidence at intake
- [AngelSlim Techniques Handoff](../handoffs/active/angelslim-techniques-evaluation.md) -- Umbrella for cherry-picking Sherry / SpecExit / Tequila / DAQ; tracks STQ1_0 PR #22836; "kernel is generic, algorithm is not" correction
- [intake-246](https://github.com/turbo-tan/llama.cpp-tq3) llama.cpp-tq3 -- TQ3_1S weight quantization (monitor only)
- [intake-187](https://huggingface.co/bartowski/cerebras_Qwen3-Coder-REAP-25B-A3B-GGUF) bartowski GGUF quants -- 26 variants of REAP-25B
- [intake-182](https://arxiv.org/abs/2309.05516) AutoRound/SignRound -- Not applicable for llama.cpp/GGUF stack
- [intake-165](https://arxiv.org/abs/2504.12285) BitNet b1.58 -- Ternary quantization, worth investigating for future architectures
- [gemma-challenge-kernel-techniques-v7.md](../handoffs/active/gemma-challenge-kernel-techniques-v7.md) -- v7 quant surface: stale-fork Q2_0 gap (fresh-pull not cherry-pick); K27 x86 Q8_0 repack un-promotable + `GGML_IQK_Q8_0` opt-in routing; K26 BF16-vs-F16 KV bench (keep F16, mixed K/V BF16 large regression)
- [speculative-decoding-mtp-refresh.md](../handoffs/active/speculative-decoding-mtp-refresh.md) -- Bonsai-27B / upstream Q1_0+Q2_0 sub-2-bit ternary lineage; v7-candidate lacked Q2_0 (merged 11 days post-cutover) → freshness-audit hit
- [findings-05c lever × model-category matrix (Axis-C quant)](../handoffs/active/fable5-window2-findings-05c-mi210-lever-category-matrix.md) -- MI210 quant-roofline: Q8 47% vs Q4_K 33% vs fp16 62% of the ~1.64 TB/s HBM roofline; Q8_0 GEMV already int8-native (no dequant to hide) so Q4_K is the dequant-bound/capacity-only quant; bf16↔Q8 batched crossover; MTP-F16 +60.2% vs Q8 +15.6% proxy
- [Progress 2026-07-06 — v7-candidate + GPU speed levers](../progress/2026-07/2026-07-06-v7-candidate-and-gpu-levers.md) -- F16-proxy aggregate 141 vs Q8 199 @B32 (~30% precision cost); MTP-on-F16 +60.2% (BW-bound confirmed); fp16 download DEFERRED (Q8 quality-lossless)
- [Progress 2026-07-02 — MI210 first-touch](../progress/2026-07/2026-07-02-mi210.md) -- first gfx90a quant-roofline points (Q4_K 33% / Q8 47% / fp16 62%), the dequant-MMQ-artifact framing

## Asymmetric MoE quantization recipe — DeepSeek-V4-Flash (intake-637, 2026-05-28)

**The recipe.** antirez's community GGUF repack of DeepSeek-V4-Flash (284B / 13B-active MoE on the new `deepseek4` arch) ships Q2 (80.8 GiB) and Q4 (153.3 GiB) variants using explicit asymmetric per-tensor-role precision:
- **Routed experts** (dominate parameter count, each token uses only a fraction): IQ2_XXS gate/up + Q2_K down (Q2 variant) OR Q4_K (Q4 variant)
- **Shared experts + attention projections + output**: Q8_0
- **Router/embed**: F16
- **Norms / sinks / router-bias / indexer / compressor / Hyper-Connection blocks**: F32

**Independently re-derived.** The recipe matches the APEX/MoE quant literature (APEX paper, MxMoE) — both warn that downgrading shared experts costs measurable PPL while routed experts have spare bits to give. Antirez stays Q8_0 on shared, which aligns. The recipe is transferable to other native `deepseek*` MoE arches but NOT to dense DeepSeek-R1-Distill-* Llama/Qwen derivatives.

**Caveats:**
- Upstream V4 weights ship mixed FP4+FP8, so sub-Q4 conversion is bounded — Q4 is the conservative target, Q2 is opportunistic.
- `llama-imatrix` originally segfaulted on V4 activation collection; antirez's published GGUFs use a patched binary (`v4-port-I-imatrix`).
- `deepseek4` arch is NOT in llama.cpp or ik_llama.cpp yet (zero `grep` hits as of 2026-05-28); upstream ggml-org issue #22319 + discussion #22376 track 4+ community WIP forks, no merged PR.

**Port path.** User authorized 2026-05-28: experimental branch `feature/deepseek4-port` off ik_llama production tree with explicit dual quality + throughput merge gates ([`deepseek-v4-flash-cpu-port.md`](../handoffs/completed/deepseek-v4-flash-cpu-port.md)) — 20-prompt × 5-category quality set with per-prompt MAD ≤ 0.05 nats + ≥ 15/20 token-1 exact-match; throughput floors Q4 ≥ 18 t/s solo, Q2 ≥ 35 t/s solo on canonical NPS4 stack.

Sources: `research/intake_index.yaml` intake-637 + APEX/MxMoE cross-refs · [`handoffs/completed/deepseek-v4-flash-cpu-port.md`](../handoffs/completed/deepseek-v4-flash-cpu-port.md) · [`handoffs/active/large-moe-expert-parallelism.md` §2026-05-28](../handoffs/active/large-moe-expert-parallelism.md) · `progress/2026-05/2026-05-28.md` §research-intake-batch.

### New (2026-07-21, iqk acceleration silently skipped IQ-quant tensors)

> **Review flag (project-wiki writer-evidence policy):** model-compiled, not adopted until human or measured review. Unbuilt and unvalidated — see the handoff for the gating tasks.

- **`GGML_IQK=1` accelerated only K-quants and legacy quants, so models whose weight bulk is IQ2/IQ3 got nothing.** iqk kernels dispatch per quant type via `iqk_typeA_supported` (`ggml/src/ggml-cpu/iqk/iqk_dispatch.cpp:58`), whose whitelist contained Q4_K/Q5_K/Q6_K/Q2_K/Q3_K/Q8_0/Q4_0/Q5_0/Q4_1/Q5_1 and no IQ types; `iqk_set_kernels_iquants` and `iqk_convert_iquants_q80_r8` were linker stubs returning `false`. GLM-5.2 UD-IQ2_M is the motivating case: its **221 routed-expert tensors (148 IQ2_XXS + 71 IQ3_XXS + 2 IQ2_S)** are the bulk of a 256-expert/8-active MoE and dominate decode bandwidth and prefill FLOPs, while only its attention and shared-expert tensors (Q8_0/Q5_K/Q6_K) were being accelerated. This is exactly the condition the port's own comment predicted at `iqk_stubs.cpp:8-12` — *"do not leave them stubbed for a quant we deploy."* Sources: [iqk-iquant-enablement.md](../handoffs/active/iqk-iquant-enablement.md), [tq3-quantization-evaluation.md](../handoffs/active/tq3-quantization-evaluation.md), [iqk-port.md](../handoffs/completed/iqk-port.md).

- **Enabling IQ-quants is cheap; enabling the KT/trellis family is not — and the distinction is the enum.** `IQ2_XXS=16`, `IQ3_XXS=18`, `IQ2_S=22` are native ggml enum values, so no type registration, `type_traits` growth, GGUF change, requant or download is needed; the 202KB kernel file was already vendored and simply not compiled. By contrast the QTIP/trellis KT types are **synthetic casts at 153-158 against `GGML_TYPE_COUNT = 43` with no `type_traits` row**, so a KT GGUF cannot load at all, `iqk_gemm_ktquants.cpp` is absent from `CMakeLists.txt`, and the `block_iq2_kt`/`block_iq4_kt` structs do not exist in the tree — a 3-6 day port, not a flag flip. Sources: [tq3-quantization-evaluation.md](../handoffs/active/tq3-quantization-evaluation.md), [iqk-iquant-enablement.md](../handoffs/active/iqk-iquant-enablement.md), [progress 2026-07-21](../progress/2026-07/2026-07-21.md).

- **Trellis quantization is a quality-per-bit play, not a speed play, at our operating points.** `block_iq2_kt` is 68 B per 256 weights = **2.125 bpw**, versus **IQ2_XXS at 2.0625 bpw** — i.e. trellis is *larger* than what GLM-5.2 already uses, saving zero bandwidth while adding per-weight arithmetic. Against Q4_K_M the saving is ~17.5%, but our own iqk measurements (+7.9-8.8% on Q4_K, ~0% on Q8_0) show we are not fully bandwidth-saturated at 4-bit, so added arithmetic eats into it. The nearest local precedent is TurboQuant at 573 t/s vs Hadamard+q4_0 at 1279 t/s (2.2x slower) on EPYC 9975. Sources: [tq3-quantization-evaluation.md](../handoffs/active/tq3-quantization-evaluation.md), [kv-cache-quantization.md](../handoffs/completed/kv-cache-quantization.md), [iqk-iquant-enablement.md](../handoffs/active/iqk-iquant-enablement.md).

- **Selective-precision carve-outs for large MoEs are already standard practice, not an untaken opportunity.** Two independent practitioners (intake-870 vLLM-Moet, intake-871 GLM-5.2-NVFP4-TR3) converged on holding attention, shared experts, the DSA indexer and early-layer MLPs above 4-bit while pushing routed experts low. Parsing the six GLM-5.2 UD-IQ2_M shard headers shows **Unsloth already implements all four, more aggressively than either describes**: attention KV path at Q8_0, `indexer.proj`/`k_norm` at F32 with indexer projections at Q8_0, shared experts at Q5_K/Q6_K, and layers 0-2 (`leading_dense_block_count=3`) at Q5_K/Q6_K. A corollary worth recording: the historical GLM-5.2 `indexer_top_k` corruption was a runtime parameter bug, and this tensor map rules quantization out as a repeat cause. Sources: [glm52-reviewer-capability-gates.md](../handoffs/active/glm52-reviewer-capability-gates.md), [tq3-quantization-evaluation.md](../handoffs/active/tq3-quantization-evaluation.md), [progress 2026-07-21](../progress/2026-07/2026-07-21.md).

## Compiled Update — 2026-08-22: the TurboQuant KV monitor is dead upstream, and the iqk dispatch whitelist is now a quant-SELECTION constraint

**Confidence: verified** — the PR state is re-derived from the GitHub API (2026-08-21), the ChunkKV verdict is a
source-checked feasibility ruling, and the `static_assert` constraint was read out of the frozen production tree. One
external caveat at the end is flagged, not resolved.

### PR #21089 (TBQ3_0/TBQ4_0 CPU TurboQuant KV) was CLOSED UNMERGED upstream on 2026-06-02 — the monitor row is retired

Re-verified against the GitHub API 2026-08-21: `state closed`, `merged false`, `merged_at null`, last update 2026-06-03.
No TBQ code ever entered the local tree, and no build, benchmark or runtime action was taken. **This retires three items on
this page**: the "TurboQuant (TBQ3_0/TBQ4_0) for KV cache deferred to upstream … monitor for merge" bullet under Exotic
Quantization, the "Evaluate upstream TBQ3_0/TBQ4_0 when PR #21089 merges" Actionable, and the matching Open Question. The
next revisit trigger is a *new* upstream PR or a merged successor — there is nothing left to monitor on #21089.

The meta-lesson doubles the 2026-08-12 finding above (the #22836 ARM-only mislabel): **a monitor row rots even inside its
own file.** The TQ3 handoff's status paragraph still read "still open — no movement since last review" on 2026-08-21 while
its own checklist, four screens down, had recorded the verified closure on 2026-07-29. A citation's identifier is
self-verifying; its *state description* is a separate claim that must be re-derived from the API before it gates anything.

### ChunkKV has a feasibility ruling: experimental-candidate only, and the existing compact endpoint is NOT ChunkKV

The 2026-07-29 assessment settles what ChunkKV (arXiv:2502.00299) would take here: **technically implementable as an
experimental llama.cpp candidate; never an existing-server toggle or a production patch.** The production tree's adjacent
substrate — `src/llama-kv-compress.cpp` plus the server's `POST /slots/{id}?action=compact` idle-slot eviction — is
**Expected-Attention** eviction (a future-attention proxy derived from raw K/V), while faithful ChunkKV requires the
*actual observed attention scores from the final prefill queries* plus ordered contiguous-chunk top-k selection. Summing
the existing per-token proxy into chunks would be a useful *ChunkEA* derivative but **must not be reported as reproducing
the paper**. Also settled: server eviction leaves positions gapped and creates reusable KV capacity, not an
allocated-buffer shrink or immediate logical-context extension. Any faithful build starts from fresh production on
`llama.cpp-experimental` and compares Full KV / Expected Attention / ChunkKV at equal cache budgets.

### The iqk dispatch whitelist is a quant-selection constraint: never pick Q2_K/Q3_K on size grounds

Verified read-only against frozen `production-consolidated-v8` (`ggml/src/ggml-cpu/iqk/iqk_dispatch.cpp:73-74`):

```
static_assert(!iqk_typeA_supported(GGML_TYPE_Q2_K));
static_assert(!iqk_typeA_supported(GGML_TYPE_Q3_K));
```

Q2_K and Q3_K are **statically asserted out of the iqk path**, so a Q2_K build forfeits iqk acceleration entirely — on
workloads where iqk is worth +33–43% prefill. The concrete case that surfaced it: if `Qwen3.6-35B-A3B` is ever benched as
a `worker_general` candidate, the size-matched arm to the Escha 2-bit build is `UD-Q2_K_XL` — and taking it would be a
mistake; `UD-IQ3_XXS` (13.2 GB, on the five-type native IQ whitelist from the 2026-07-21 section above) keeps the
acceleration for ~1 GB more. **The general rule: a candidate quant's dispatch-path membership is part of its price, not a
detail** — this page's 2026-07-21 iqk section documented which types the whitelist *includes*; the `static_assert` pair is
the complementary, compiler-enforced *exclusion* list. Also closed 2026-08-03: the `eschamoe` W2 format itself is unusable
here (closed CUDA sm_80–120, no ROCm path — the same wall as ZipServ, EXL3 and the rest of the quantization×kernel
co-design school, now recorded corpus-wide so it is not re-derived source by source).

### Flagged, not resolved: our first-party KV-quant quality case rests on the instrument class KIVI shows can miss

A 2026-08-22 Stage-2b dive on KIVI (arXiv:2402.02750, verified against the primary source) records that KIVI reports **no
perplexity anywhere** and rejects single-decode-step metrics for compressed-KV study; its own data show the same 2-bit KV
damage costing CoQA ~7% while **collapsing GSM8K by ~57%** (13.50 → 5.76) on Llama-2-7B. Our deployed
"quality-neutral" KV-quant case (PPL +0.017, NIAH 9/9 — see KV Cache Quantization above) is built **exactly** on the
instrument class that can stay flat through such damage. This does not overturn the deployed config — the multi-step
reasoning eval that would test it (GSM8K-class, f16 vs q8_0/q8_0 vs q4_0/q4_0, rotation ON) is specced but **unrun**, so
the parity claims stand *as PPL/NIAH claims* with this caveat attached until that gate runs.

### Source References

- [`tq3-quantization-evaluation.md`](../handoffs/active/tq3-quantization-evaluation.md) — the 2026-08-21 re-verified #21089 closure and self-contradiction correction, the ChunkKV feasibility memo, the Escha/`eschamoe` ruling, and the KIVI Stage-2b instrument-gap entry.
- [llama.cpp PR #21089](https://github.com/ggml-org/llama.cpp/pull/21089) — the closed-unmerged upstream PR itself (state re-derived via the GitHub API, not the tracking row).
- [`iqk-iquant-enablement.md`](../handoffs/active/iqk-iquant-enablement.md) — owner of the iqk whitelist/un-stub work the Q2_K/Q3_K exclusion constraint complements.
- [`architect-model-selection-bench.md`](../handoffs/active/architect-model-selection-bench.md) — the role-level context for the Escha-vs-UD-IQ3_XXS worker-candidate quant choice.
- [intake-945/946/956](../handoffs/active/tq3-quantization-evaluation.md) (`EschaLabs/Qwen3.6-35B-A3B-Escha-W2`) — the Stage-2 intake cluster behind the `eschamoe` closure.
- [KIVI arXiv:2402.02750](https://arxiv.org/abs/2402.02750) — the verified external result behind the flagged PPL/NIAH instrument caveat.

## Compiled Update — 2026-08-23: KIVI's axis prescription is 2-bit-only, our KV blocks are finer than the published mitigation, and behavioural drift decouples from perplexity

**Confidence: verified** — the tree facts are read-only inspections of frozen `production-consolidated-v9`
(`0db32c06e3e550065b78311a6031ef3dd2c4f27c`) with file:line loci, audited 2026-08-23. The external results
are dive-verified against their primary sources and labelled as third-party throughout. **No figure below
is a first-party measurement of behavioural damage on this stack, and under
[MEASUREMENT.md](../MEASUREMENT.md) none of them gates a config change** — the point of this pass is that
the measurement does not exist yet, and is now filed.

### The 2026-08-22 KIVI caveat resolves in two halves: the implementation half is retired, the measurement half stands

The previous pass flagged, unresolved, that our KV-quant quality case rests on PPL/NIAH — an instrument
class KIVI shows can stay flat while GSM8K collapses ~57%. The full Stage-2b dive (`intake-1286#record`,
arXiv:2402.02750v2 read in full, credibility 4/HIGH) splits that flag cleanly.

**The implementation half is retired. KIVI's axis prescription is 2-bit-only and does not reach our
operating regime.** Its own **OB 1** states that at INT4, per-token quantization of *both* caches
maintains accuracy; the axis asymmetry is established **only at 2 bits**; and the paper runs **no 4-bit
and no 8-bit axis ablation**, so it licenses no conclusion in either direction at the bit widths we serve.
Its 4-bit per-token/per-token rows match or exceed FP16 CoQA on three of four models (Llama-2-7B 64.82 vs
63.88; Llama-2-13B 66.73 vs 66.37; Mistral-7B 67.80 vs 67.40). Production runs q8_0/q8_0, q4_0/f16 and
q4_0/q4_0 — never 2-bit. Two further scope limits ride along: the axis ablation contains **no
GQA-at-scale, no MLA, no QK-normed and no hybrid-SSM model** (all four ablated models predate per-head
QK-RMSNorm), and by KIVI's own numbers the **full-precision residual window, not the axis**, does most of
the recovery on hard generation tasks (Llama-2-7B GSM8K **5.76 → 12.74 at a fixed axis**). Citing KIVI for
the axis while omitting the window misattributes most of the effect.

Consequently the "primary quality gap" recorded for months at `kv-cache-quantization.md:320` **was never a
gap**: per-token V is structurally guaranteed once V is quantized (quantized V forces flash attention,
which sets `v_trans = false`, making V channel-contiguous — `src/llama-context.cpp:3557`,
`src/llama-kv-cache.cpp:231-232`), the K half is out of KIVI's demonstrated scope, and key outliers are
addressed instead by the in-tree orthonormal Walsh-Hadamard rotation. The only residual difference is
**symmetric (`q4_0`/`q8_0`) vs asymmetric (KIVI)** — and `q4_1`/`q5_1` are supported asymmetric KV types,
so that is **a flag, not a code change**. Mechanism and the independent RotateKV corroboration are
compiled on the [KV Cache](kv-cache.md) page.

**The measurement half stands, unchanged, and is now gated.** KIVI reports **no perplexity anywhere** and
explicitly rejects single-decode-step closed-ended metrics as unsuitable for studying compressed KV. Our
entire first-party quality case for quantized KV remains **perplexity plus needle-in-a-haystack**
(q4_0+Hadamard PPL +0.017; q8_0/q4_0+Hadamard −0.010; NIAH 9/9 at 1K/4K/16K). **No GSM8K-class multi-step
generation eval has ever been run against quantized KV in this repo.** That is the real gap; it is a
*measurement* gap, not an implementation one, and it is now G3 on the TQ3 handoff.

### The granularity reading rule: group-32 along CHANNELS, finer than the published mitigation and on the opposite axis from KIVI

**With `-fa 1`, llama.cpp quantizes K and V per token in 32-element blocks running along the CHANNEL
dimension** (`src/llama-kv-cache.cpp:231-232` allocates dim0 = channels, dim1 = tokens; `QK4_0 = QK8_0 =
32`). Two consequences, and together they are the lens for reading any future KV-quant paper against this
stack:

1. **We are already finer than the alignment-collapse study's own Group-64 mitigation, by default,
   everywhere.** That study lists **Group-64 quantization** among the remedies it recommends and measures.
   **Its headline damage figures are therefore a pessimistic bound for us, not a matched estimate** — and
   any transfer of its flip rates onto this stack must say so.
2. **This is the OPPOSITE axis from KIVI.** KIVI groups *per channel for K*; we group *per token* for
   both, and quantized V is structurally locked onto that axis. Same word "group", orthogonal dimension.
   **Never read a Group-64 result as an upper bound on our group-32 damage without first checking which
   axis the grouping runs along.**

### Behavioural drift decouples from perplexity — and INT8 is exonerated on safety but not on instruction-following

`intake-1291#record` (arXiv:2606.09864v2, **unreviewed preprint**, credibility 3/Medium; 11
instruction-tuned models 3.8B–72B, 5 benchmarks, 1,894 prompts; **all measurements NVIDIA** — RTX 3090 /
A100 / 8×GPU, HuggingFace-simulated quantization plus vLLM). Dive-verified 2026-08-22; **no independent
replication was located and the replication sweep never ran**, so absence of criticism is
unverified-in-stage2, never a negative finding.

- **The headline decoupling.** Mistral-7B loses **15.2% of AdvBench refusals at 4-bit while perplexity
  rises only 1.03×** (5.22 → 5.37). Collapse onsets span four bits across models (Qwen at 6-bit,
  Gemma/LLaMA only at 2-bit) — **there is no universal safe bit width**, and the paper's own thesis (its
  PCR diagnostic is a per-model property with no cross-model prior) forbids extrapolating any of it from
  one model to another.
- **Do NOT cite this paper against an INT8 KV cache on the safety axis.** At 8-bit simulated uniform,
  ConditionalFlip is **≤3.2% for all eleven models** (max Mixtral 3.2%; Qwen, the most fragile, 0.2%), and
  real `torch.int8` storage flips 1/19. The paper uses uniform INT8 as its *favourable* comparator. The
  sole 8-bit exception is a **format** finding, not a bit-width finding: vLLM `fp8_e5m2` causes **30.3%**
  flip and `fp8_e4m3` **7.1%** — 35× worse than uniform INT8 — because mantissa bits, not nominal width,
  set effective resolution.
- **The genuine perplexity-blind INT8 failure is on the capability axis, and it is one model on one
  benchmark.** Qwen-2.5-7B IFEval strict-pass falls **69.50 → 59.89 at 8-bit KV with 23.14% CondFlip**,
  and to 16.82 / 77.39% at 6-bit. The authors describe this axis explicitly as **"steep but continuous"**,
  *not* a phase transition — so the phase-transition framing that fits the safety axis does not
  generalise. (The 7-bit row carries an author-disclosed separate-container baseline caveat.)
- **K and V are not equally risky.** K-projection quantization accounts for **76–102% of alignment damage
  in 8 of 9 primary models at 4-bit**; Qwen-2.5-7B is **92.2% (K-only) vs 0.6% (V-only) — a 154×
  asymmetry** — with Phi-3.5 the sole exception. Direction only: **third-party direction to test against,
  never to adopt as a baseline.**
- **Standard telemetry gives no warning under speculative decoding.** With target-side 4-bit KV
  (Qwen-0.5B draft / Qwen-7B target, greedy): refusal **63.2% → 0.0%** while acceptance (23.5%) and
  throughput (17.0 tok/s) stay in plausible ranges; at 3-bit acceptance *rises* to 43.4% and throughput
  recovers to 24.2 tok/s at 0.0% refusal. **Verifier entropy (1.29 → 2.28) is the only telemetry that
  moves.** This is the direct counterexample to clearing a spec-decode × quantized-KV interaction on a
  throughput figure — see the R9 warrant repair on [KV Cache](kv-cache.md).
- **The 10²–10³× subspace-vulnerability figure is mechanism, not measurement.** It is a theoretical
  estimate from α ≈ 10⁻³–10⁻² offered to explain the observed decoupling; cite it as an explanation, never
  as a measured quantity. And **PCR is not runnable on our serving stack** at all: llama.cpp exposes no
  per-layer KV precision and no per-channel-key mode.

**Two live registry roles sit on the axis this paper identifies as the damaging one**: `architect_critic`
(q4_0/f16 on Qwen3.5-122B-A10B-MTP, **with a `draft_model`** — structurally the paper's spec-decode
configuration) and `ingest_long_context` (q4_0/q4_0 on Qwen3-Next-80B). `frontdoor`, `worker`,
`worker_vision` and `architect_general` are all q8_0/q8_0, i.e. both the safe bit width and the protected
axis. The registry is **frozen**: any `-ctk`/`-ctv` change routes through the operator-gated registry
path, never a hand edit — and nothing here licenses one, because the paper's numbers are NVIDIA,
unreplicated, and measured against a coarser grouping than ours.

### What our KV write path does NOT have — audited read-only, 2026-08-23

The massive-activations and alignment-collapse literatures both assume mitigations our tree does not
carry. Verified by static read of the canonical frozen tree; nothing built, nothing run:

- **No per-channel scaling.** `llama_kv_cache::cpy_k` (`src/llama-kv-cache.cpp:1311-1344`) and `cpy_v`
  (`:1346-1400`) are pure `ggml_set_rows` into the cache tensor. There is no scale tensor, no calibration
  pass and no per-channel state anywhere in the path — **the only transform between the attention output
  and the stored bytes is the block quantizer for `type_k`/`type_v`.**
- **No clipping.** Zero occurrences of `clip` or `clamp` in `src/llama-kv-cache.cpp`. An outlier is stored
  at whatever the block scale can represent; nothing bounds it first.
- **No attention-sink special-casing.** Zero occurrences of `sink` in `src/llama-kv-cache.cpp`. Attention
  sinks *do* exist in this tree — but **only as a softmax bias in the graph**
  (`ggml_flash_attn_ext_add_sinks`, `src/llama-graph.cpp:2497`; `ggml_soft_max_add_sinks`, `:2554`). They
  never exempt a token from KV quantization. **Do not read "llama.cpp has sinks" as "llama.cpp protects
  sink tokens from KV quantization" — different mechanisms, different files.**

**The orthonormal self-inverse Walsh-Hadamard rotation is the whole of our outlier defence** — gated at
`src/llama-kv-cache.cpp:319-336` (`attn_rot_k`/`attn_rot_v`, requiring `ggml_is_quantized(type)` and
`n_embd_head % 64 == 0`, defeatable by `LLAMA_ATTN_ROT_DISABLE`). Both papers are silent on it: the
alignment-collapse study's Related Work explicitly lists SmoothQuant- and QuaRot-style rotation as
**untested** for safety, and that is exactly the class we ship. Whether the collapse mechanism survives
our rotation is **genuinely open in both directions**, and only a measurement on our stack can close it.

### The gates this pass leaves behind — all filed, none run

Both compute planes were held elsewhere during wave 2; every row below is filed on
[`tq3-quantization-evaluation.md`](../handoffs/active/tq3-quantization-evaluation.md) for whoever holds a
plane next.

- **G3 — close the instrument gap.** GSM8K-class multi-step generation at f16 KV vs production q8_0/q8_0
  vs q4_0/q4_0, rotation ON, one pure-attention model and one Qwen3.x GDN hybrid, paired questions,
  exact-match scored, persisted per question. **Gate:** any config showing a reasoning delta outside noise
  *while perplexity and NIAH stay flat* replicates KIVI's instrument finding first-party; a flat result
  retires the concern permanently.
- **G4 — paired behavioural drift, on the axis we actually serve.** IFEval subset **N ≥ 250**, greedy
  `t = 0` seed 42, one model held constant, sweeping `-ctk`/`-ctv` over
  {f16/f16, q8_0/q8_0, q8_0/q4_0, q4_0/q8_0, f16/q4_0}, scored as **FP16-anchored paired
  ConditionalFlip** — not aggregate pass rate; the two are different quantities and are not
  interchangeable. Report perplexity drift beside CondFlip on every arm, because the decoupling is the
  point. **Gate:** any config with **CondFlip > 5% while PPL drift < 2%** reproduces the decoupling and
  makes a behavioural gate mandatory before any future KV-default change; **all configs < 2% ⇒ our
  group-32 granularity is doing the work** and perplexity-plus-NIAH was retrospectively adequate. A
  refusal/safety benchmark suite is an explicit **decline** for a single-operator research stack —
  CondFlip on IFEval carries the transferable lesson without one.
- **G5 — reproduce KIVI's Fig. 2 / Table 2 on our architecture.** Per-channel key magnitudes from a
  production Qwen3.x GGUF at a fixed prompt, with and without `LLAMA_ATTN_ROT_DISABLE=1`, per-group
  max/RMS at G=32. **Gate:** a near-flat rotated ratio establishes the redundancy conclusion *first-party*
  and deprioritises the rest. Scope caveat that bounds the whole result: **only 10 of 40 frontdoor layers
  are full attention**, so a per-channel key dump covers a quarter of the stack by construction and must
  be reported as such.
- **G2 — our actual KV outlier ratio**, per layer and per head, K and V separately (`max/median`,
  `max/p99.9`); a pooled ratio is not the measurement. **Gate:** if both are unremarkable (< ~50×), close
  the massive-activations line for this stack as measured-and-negative.
- **B1 (blocked on G5)** — pre-RoPE vs post-RoPE rotation placement; a **permanent decline**, not a
  deferral, if G5's rotated ratio is near-flat. **B2 (blocked on G4)** — confirm the K/V asymmetry
  direction on our own arms (`q4_0/q8_0` vs `q8_0/q4_0` is the decisive pair), and only then generalise it
  into a standing "quantize V before K" selection rule written into the registry's KV defaults. **If our
  arms disagree with the third-party direction, ours governs.**
- **Cheap A/B** — `-ctk q4_0` (symmetric) vs `-ctk q4_1` (asymmetric), rotation ON, same group size, plus
  `llama-bench` decode t/s to price the extra scale word. A tie — the prediction, since a rotated
  distribution is near zero-mean — closes KIVI's asymmetry question permanently for one short bench.

### Source References (2026-08-23)

- [`tq3-quantization-evaluation.md`](../handoffs/active/tq3-quantization-evaluation.md) — the H11
  read-only audit (no per-channel scaling, no clipping, no sink special-casing) and the G2/G3/G4/G5,
  B1/B2 gate rows with their open/close criteria.
- [`kv-cache-quantization.md`](../handoffs/completed/kv-cache-quantization.md) — the retired `:320`
  "primary quality gap" with its three-part correction, and the 2026-08-23 granularity correction
  (`:1539`) establishing group-32-along-channels versus Group-64 and the opposite-axis reading rule.
- [intake-1286](https://arxiv.org/abs/2402.02750) KIVI (ICML 2024, dive-verified, credibility 4/HIGH) —
  OB 1's 2-bit scope limit, the absent 4-bit/8-bit axis ablation, "no perplexity anywhere", the
  residual-window attribution (GSM8K 5.76 → 12.74 at a fixed axis), and the
  CoQA-flat-while-GSM8K-collapses instrument argument. Cite as `intake-1286#record`.
- [intake-1291](https://arxiv.org/abs/2606.09864) Alignment Collapse Under KV Cache Quantization
  (unreviewed preprint, dive-verified, credibility 3/Medium, NVIDIA-only) — the 15.2%-flip-at-1.03×-PPL
  decoupling, the INT8 exoneration on safety, the IFEval 8-bit CondFlip 23.14%, the K/V 154× asymmetry,
  the spec-decode telemetry blindness, and Group-64 as its own mitigation. Cite as `intake-1291#record`.
- [`model_registry.yaml`](../repos/epyc-orchestrator/orchestration/model_registry.yaml) — the two live
  4-bit-K roles (`architect_critic` q4_0/f16 with a `draft_model`; `ingest_long_context` q4_0/q4_0) and
  the q8_0/q8_0 majority. Frozen; changes route through the operator-gated registry path.

(append to the page-level `## Source References` list)

- [intake-1286](https://arxiv.org/abs/2402.02750) KIVI (ICML 2024) -- the warrant every "per-channel K / per-token V" citation inherits. Dive-verified 2026-08-22: measured, not asserted, but **2-bit-only** by its own OB 1, with no 4-bit or 8-bit axis ablation anywhere; reports **no perplexity at all** and rejects single-decode-step metrics; the full-precision residual window, not the axis, does most of the recovery. Retires the `kv-cache-quantization.md:320` "primary quality gap". Cite as `intake-1286#record`
- [intake-1291](https://arxiv.org/abs/2606.09864) Alignment Collapse Under KV Cache Quantization -- behavioural drift decouples from perplexity (15.2% AdvBench flip at 4-bit, PPL 1.03x); INT8 exonerated on the safety axis (CondFlip <=3.2% across 11 models) but **not** on instruction-following (Qwen-2.5-7B IFEval 69.50 -> 59.89 at 8-bit, CondFlip 23.14%); K carries 76-102% of 4-bit damage; **Group-64 is its mitigation and our group-32 blocks are finer**. Unreviewed preprint, NVIDIA-only, no independent replication located. Cite as `intake-1291#record`
- [intake-1282](https://arxiv.org/abs/2605.17613) VeriCache -- KV-quantization-adjacent: draft on the compressed cache, verify against the FULL cache so the target is the real FP16 model. Its quantization-compressor arm is its weakest (1.4-1.9x). Expressible in frozen v9 via `-ctkd`/`-ctvd`; detail on [KV Cache](kv-cache.md). Cite as `intake-1282#record`


## Compiled Update — 2026-10-03: EXL3 on the 27B — answer the bytes question first (X0)

**Confidence: verified** for the inventory: no device execution, no EXL3 weights on disk at review time, and the
kernels' shapes. The decode-cost estimate is **inferred arithmetic, not a measurement**. External quality and speed
comparisons are **external** (one vendor, one model), cited as records only.

- **Nothing EXL3 has ever run on an MI210, here or anywhere found.**
  - Our standalone gfx90a kernels compile and pass host checks, with zero device executions (G3/G4/G5 open).
  - The wave64 GEMV is one lane per output column, with a serial per-weight decode loop. The MFMA path decodes B one
    element at a time from global memory.
  - No INF-80 task covers performance-grade kernels, although EXL3-7 assumes they exist. This is the plan's largest
    hidden cost.
- **On the dense production 27B, EXL3 is mainly a VRAM lever.**
  - On gfx90a, llama.cpp quantized decode is limited by unpack cost, not bytes. Q4_K reaches 35.1% of roofline,
    against Q8_0's 50.2%. Halving the bytes bought only +14.6% tg128 on Qwen3.6-27B.
  - EXL3 decode costs more ALU per weight than Q4_K.
  - A back-of-envelope estimate (inference, unmeasured) puts a tuned batch-1 decode near 50–75 tok/s without a draft.
    A first tuned kernel would land nearer Q8's ~31.
  - External data cuts both ways. Same-harness GGUF Q5_K_M beats EXL3 4.0 bpw on KLD at equal file size, and EXL3
    5.0 roughly ties Q6_K (intake-1509#record). Tuned NVIDIA EXL3 trails 4-bit rounding formats at batch 1
    (intake-1528#record).
  - EXL3's real advantage is quality at 2–3.5 bpw, for fitting bigger MoE models. There is no current target.
- **GGUF K-quants give the same VRAM saving today.** The EXL3 4.0 27B would free about 11 GiB; GGUF Q4_K_M is similar.
- **EXL3-X0, operator-approved 2026-10-03, ahead of EXL3-6.**
  - **Arms:** in one exclusive :8083 window, run unsloth UD-Q4_K_M against the incumbent Q8_0 through the
    DFlash2-np4 serving recipe at the production shape: 3 launches per arm, ABA, plus KLD of Q4_K_M against Q8_0.
  - **Decision rule (fixed in advance):** under +10% serving speed means EXL3 has no speed case on the 27B, so park
    EXL3-6/7 and settle VRAM with GGUF. At or above +10%, fund a performance-grade wave64 kernel (EXL3-P) with a
    5-agent-day kill.
  - EXL3-3/4/5 device correctness runs in the same window, using turboderp `Qwen3.8-27B-exl3` 4.00bpw, which is on
    disk for real-tensor correctness.
  - The window (2–3 h exclusive :8083) was granted to workspace-89, to run immediately after the KV-pool proof.
- **The review's other recommendations:**
  - park EXL3-8 until a GPU model larger than 128 GB is named;
  - kill the EXL3-7 CPU half, which collides with DS41 windows;
  - reframe EXL3-9 as EXL3 vs GGUF at equal file bytes;
  - park EXL3-5 beyond correctness until a MoE target exists.
- **A correction to the review.** It says DS41 competes for the MI210. Since 2026-09-30 DS41's planner and critic are
  external, so it no longer does.

### Source References

- [EXL3 ROI review](../docs/reviews/exl3-roi-20261003.md) — inventory, ROI table, recommendation, uncertainties.
- [EXL3 CPU/MI210 implementation](../handoffs/active/exl3-cpu-mi210-implementation.md) — EXL3-X0 and its decision rule.
- [2026-10-03 ak-ds41-main progress](../progress/2026-10/2026-10-03-ak-ds41-main.md) — X0 filed; the operator wants EXL3 taken seriously, including building the missing kernels if X0 is positive.
- [2026-10-03 workspace-ec progress](../progress/2026-10/2026-10-03-workspace-ec.md) — the X0 window grant and its production handling.


### Existing IQ-family wiring in frozen v10 — 2026-10-07

[INF54's four-blob source adjudication](../artifacts/ni08/inf54-current-iq-source-adjudication-20261007/README.md) finds the requested IQ2_XXS/IQ3_XXS/IQ2_S wiring already present in frozen v10: the real iquant implementation is registered, entrypoints are no longer stubs, and dispatch supports those types. IQ4_XS is also supported, superseding the historical instruction to leave it on the native path. This closes the source-port checklist item without kernel changes. Compiled identity, runtime performance/quality and the trellis measurement/port decisions remain independent gates in the [quantization owner](../handoffs/active/tq3-quantization-evaluation.md).

## Compiled Update — 2026-10-20: the uniform IQ4_XS trunk is retired, the artifact changed under every CPU headline, and DS41 serves MXFP4 experts directly

**Confidence: verified** for the recorded operator rulings, the recipe change and the byte census; the expected size of the re-bench shift is an inference from those bytes, not a measurement.

On 2026-10-20 the operator retired the `IQ4_XS-uniform` Qwen3.8-Flash-Next trunk and named UD-IQ4_XS as the keeper, to reclaim disk. The research recipe (`qwen38_flash_next_recipe.py`, rev 2026-10-20) now pins `TRUNK_*` to the UD-IQ4_XS 3-shard set with a per-shard path, byte count and sha256, and keeps the uniform file as `MEASURED_TRUNK` so that every historical headline still names the artifact it was measured on. The retired path now raises a `RecipeViolation`. A gguf-py census of the UD shard headers gives 5.839 GB per token, 7.002 bpw and 6.671 B active parameters, against 4.166 GB, 4.995 bpw and the same 6.671 B for the uniform file; the same script reproduces the uniform numbers exactly.

The consequence for this page is a measurement-epoch reset. Every INF-70 CPU-decode headline (23.16, 33.370, 43.281 / 27.893 t/s) was taken on the uniform file. The UD file streams about 40% more bytes per token and the earlier OP-32 run measured UD at -13% decode, so a re-bench on the served artifact is expected to read lower. That gap is an artifact fact, not a regression, and the headlines must carry `measured_on_artifact`. Two corrections to the old precondition: the uniform file was never on HF, and it is a quant-from-quant that `llama-quantize --allow-requantize` on the UD shards regenerates, with bit-identity of a regeneration unproven. The same ruling removed the uniform arm from the iqk Step 3 KLD comparison and retired the "zero-port file swap" admission criterion, because the 2026-10-04 EXL3 window had already measured the uniform file at +17.8% PPL against UD; UD is now the only reference for EXL3-6c5.

DeepSeek-V4.1-Flash takes the opposite route. For the 1017 finetune the operator ruled that antirez's MXFP4-experts build is served directly ("if we can run the MXFP4 quant directly that would be best"), and the planned FP4-to-Q4_K requant (DS41-W3/W4) became a fallback only. The handoff cites a public KLD of 0.0102 for native MXFP4 against 0.0290 for the FP4-to-Q4_K requant on DS4-Flash (DS41-C114); that is a public figure on a sibling model, not an EPYC measurement. The CPU path for MXFP4 experts is the AVX2 `mxfp4_8x8_q8_0` repack, not iqk, and measured x1.00 at N=1 and x1.04 at N=3 against Q4_K iqk before the DS41 keeps. The existing DS41 keeps (+7.11% serving) target the Q4_K X4_T kernel and do not carry over, so DS41-W8 re-anchors AutoKernel on the MXFP4 expert path.

Two smaller records. The TQ3 monitor list gained a LittleBit / LittleBit-2 entry as a QAT-only sub-1-bit reference, monitor only, with no run attached. INF37-IQ-4 files a documentation-only comparison of Magnitude's planar IQ2/IQ3 GEMV layout (one 16-byte packet load per 32 elements, factored scale*dot+bias*sum(x)) against ggml-cuda's decode on gfx90a, to be read at the IQ-residency reprice; it claims no benefit and makes no IQ role resident.

### Source References (2026-10-20 quantization delta)

- [CPU decode roofline program](../handoffs/active/cpu-decode-roofline-program.md) — PROD-3 retirement ruling, epoch reset and the uniform-file provenance correction.
- [iqk IQ-quant enablement](../handoffs/active/iqk-iquant-enablement.md) — Step 3 arm dropped and the zero-port criterion retired.
- [EXL3 CPU and MI210 implementation](../handoffs/active/exl3-cpu-mi210-implementation.md) — EXL3-6c5 now references UD only.
- [DeepSeek-V4.1-Flash evaluation](../handoffs/active/deepseek-v41-flash-evaluation.md) — section W, MXFP4-direct ruling and W8 AutoKernel re-point.
- [TQ3 quantization evaluation](../handoffs/active/tq3-quantization-evaluation.md) — LittleBit monitor entry.
- [MI210 Q8 dequant-GEMV roofline](../handoffs/active/mi210-q8-dequant-gemv-roofline.md) — INF37-IQ-4 layout record.
- [Retire IQ4_XS-uniform progress note](../progress/2026-10/2026-10-20-retire-iq4xs-uniform.md) — recipe revision, census and the epoch consequence.
- [DS41 1017 swap progress note](../progress/2026-10/2026-10-20-ds41-1017-swap.md) — operator rulings.

## Compiled Update — 2026-10-21 (sweep 5): what serving the DS41 MXFP4 experts directly costs and buys

**Confidence: verified** for the recorded runs. Timing is **indicative** only (operator ruling); see the local-inference page for the full ABA table.

- **Quality.** ppl on wiki.test.raw (c=512, 32 chunks) is 2.6675 ± 0.0675 for 1017 MXFP4 against 2.6122 ± 0.0655 for Sept Q4, +2.1% and inside one sigma. This is not a quantization-only delta. It mixes the 1017 finetune with the move from Q4_K experts to native MXFP4, and it lacks the reference's FP8 attention-output round trip. On that path, FP8 QDQ before `wo_a` measures NMSE ~7e-4 against a Q8_0 noise floor of ≤1.25e-4, which is why DS41-W5.1a was filed.
- **Speed.** Under identical conditions, served decode is +8.1% (15.01 vs 13.89 t/s). The llama-bench pair (tg128 −5.1%, pp512 −29.9%, 87.94 vs 125.39) is **INVALID as a comparison** (note 2026-10-23). The Sept run took llama-bench's hardened protocol without asking for it (the uninitialised `autokernel_harden` defect) while the 1017 run was ordinary, so DS41-W5-LBR must re-measure it. The MXFP4 experts do run on the AVX2 `mxfp4_8x8_q8_0` repack, not on iqk Q4_K; whether that prefill path is the slower one is still open.
- **Memory.** The repack makes each server hold about 276 GiB of private RAM on top of about 463 GiB mapped. A quantized GGUF here is not just a page-cache tenant. Two concurrent servers exhausted MemAvailable and set off the earlyoom kills (INC-20261021-earlyoom-session-kills).
- **Recovery path.** The DS41 decode floor is now an AutoKernel campaign on the 1017 surface, `ak-ds41-1017-cpu-decode-20261021`. It uses a served-shape oracle calibrated with 360 + 8 routed cases, with two IQ3_XXS cases held anchor-relative. Low-bit performance stays AutoKernel's job.

### Source References

- [DeepSeek V4.1-Flash evaluation](../handoffs/active/deepseek-v41-flash-evaluation.md) — W5 serving-speed note, W5.1a, W8 oracle.
- [Progress workspace-58](../progress/2026-10/2026-10-21-workspace-58.md) — W5/W5.1/W8 table.
- [Progress ds41-w5](../progress/2026-10/2026-10-21-ds41-w5.md) — ppl and coherence gates.
- [Incident report INC-20261021-earlyoom-session-kills](../artifacts/incidents/INC-20261021-earlyoom-session-kills/REPORT.md) — the memory consequence.

## Compiled Update — 2026-10-22 (wrap-up sweep 12, workspace-58): a GSQ IQ4_NL tensor broke the fused decode path, and the EAR column is built

**Confidence: verified** for the root-cause chain (traced on the real GGUF; RCA notes kept), the job fix and the EAR acceptance results; **open** for the NEW-10 quality verdict (re-run booked) and for whether the same cause explains FD-DIV-1's synthetic-weight divergence.

- **NEW-10 keeps strict bars.** The operator kept the predeclared G1-G4 bars (pin `1a5e5ca9…` unchanged); the GSQ-RCO Q38FN IQ3_XXS download (75.84 GB, pinned `ed59f920`) verified against the HF lfs oids.
- **The first quality run died in its smoke step, and the cause was a quant type the fused path never met.** GSQ stores `ffn_down_shexp` as IQ4_NL where UD-IQ4_XS uses Q8_0. Under `GGML_IQK=1` CPU_REPACK interleaves IQ4_NL (`iq4_nl_8x8`); the qwen4exp fused single-token decode reads rows with a plain `vec_dot` and ignores the repack, so layer 0 goes NaN, the layer-1 router is all-NaN, `best` stays -1 and `probs[-1]=-INF` corrupts the heap ("double free or corruption"). A second latent bug: an F16 `ple_conv1d` read through `float*`. This is also FD-DIV-1's double free.
- **The job's own defect was the environment.** Q38FN serves with `GGML_FUSED_DECODE_OFF=1` (registry); the job ran without it. With the serving env added (addendum `e4aade94…`, bars unchanged), perplexity and KLD never enter the fused path. Lesson: a quality comparison inherits the role's serving env, not just its binary.
- **Patch, unbuilt:** `14c57cbe9` refuses the fused path for repacked or non-F32 raw-pointer weights (one warning, falls through to the graph), widens `ple_conv1d`, aborts cleanly on `best < 0`, and gates the v10 bring-up debug prints and per-token `/tmp` dumps (CH-24 for v11).
- **EXL3-EAR1 accepted.** The EAR column in `llama-perplexity --kl-divergence` built and passed: EAR(base, base) 99.998%; Q4_K_M vs Q8_0 base on Qwen2.5-Coder-0.5B EAR full 91.21% / top-10 renormalized 92.82%, above the Pinsker floor 85.70%; every pre-existing output line byte-identical to the champion binary; Python cross-check pass. The NEW-10 re-run uses the v10 store binary, so its first real EAR numbers come from a later quantcmp pass on the experimental build.

### Source References (2026-10-22 wrap-up sweep 12)

- [handoffs/active/iqk-iquant-enablement.md](../handoffs/active/iqk-iquant-enablement.md) — NEW-10 evening note
- [handoffs/active/cpu-fused-decoder-blocks.md](../handoffs/active/cpu-fused-decoder-blocks.md) — FD-DIV-1 chain, FD-DIV-1a
- [handoffs/active/exl3-cpu-mi210-implementation.md](../handoffs/active/exl3-cpu-mi210-implementation.md) — EXL3-EAR1 acceptance
- [handoffs/active/autokernel-champion-aggregate.md](../handoffs/active/autokernel-champion-aggregate.md) — CH-24
- [progress/2026-10/2026-10-22-workspace-58.md](../progress/2026-10/2026-10-22-workspace-58.md) — sections 17.1 and 17.7

## Compiled Update — 2026-10-22 (wrap-up sweep 15, workspace-58): NEW-10 GSQ-RCO IQ3_XXS fails the strict bars, so the arm is closed

**Confidence: verified** for the gate values (one predeclared run, v10 store binaries, pin `1a5e5ca9…` + addendum `e4aade94…`), refuted for serving GSQ IQ3_XXS in place of UD-IQ4_XS. G4 is incomplete (4 needs_review texts not eyeballed).

- **Result.** The run used one shared UD-IQ4_XS logits base (wiki.test.raw, c512/b512/40 chunks, `GGML_FUSED_DECODE_OFF=1` as served).
  - G0 load passes.
  - G1 mean ln-PPL ratio is 0.0150 ± 0.0100 against a bar of ≤ 0.005.
  - G2 mean KLD is 0.322 ± 0.007 nats against ≤ 0.1045.
  - G3 same-top-1 is 82.9% ± 0.4 against ≥ 88.55%.
  - G4 coherence shows 0 regressions with 4 needs_review, so it is INCOMPLETE.
  - PPL (lower = better) is UD 2.9925 against GSQ 3.0346.
  - Median KLD is 0.062 and max is 9.73, so a heavy tail carries the mean.
- **Reading.** The GSQ-RCO IQ3_XXS build misses all three distributional bars by wide margins. G2 is about 3x the bar and G3 about 6 pp short. The miss is not a near-pass that a larger n would rescue.
- **Consequences, by the predeclared rule.**
  - No serving-shape speed bench is run, and no NEW-14 task gate.
  - **IQ3_S is not pulled**: NEW-11 made it conditional on IQ3_XXS clearing PPL/KLD.
  - The weights stay on disk for NEW-13 only (operator ruling), and are then deleted (NEW-13-RM).
  - NEW-13 still runs. It asks whether a UD prefill rescues a weak decode set, so a weak D is the case under test.
- **Fallback census.** 96 tensors are native (non-iqk: 58 IQ4_NL, 38 Q2_0) and 12 are decode-only iqk IQ3_XXS, exactly as the GGUF header predicted.
- **Belief-kernel lesson.** The job hand-wrote its receipt (`epyc.quantcmp.receipt.v0`), and the VB-QUANTCMP-WIRE strict reader refuses it (unsupported schema). That reader accepts only receipts from `qwen4exp_quality_capture.py`, which proves residency while the child runs. A quant-comparison job must call the capture tool. VB-QUANTCMP-NEW10 re-captures this run before the weights go.

### Source References (2026-10-22 wrap-up sweep 15)

- [handoffs/active/iqk-iquant-enablement.md](../handoffs/active/iqk-iquant-enablement.md) — NEW-10 verdict block, NEW-11 IQ3_S note, NEW-13 / NEW-13-RM
- [handoffs/active/vidya-belief-substrate-program.md](../handoffs/active/vidya-belief-substrate-program.md) — VB-QUANTCMP-NEW10
- [progress/2026-10/2026-10-22-workspace-58.md](../progress/2026-10/2026-10-22-workspace-58.md) — section 18.1

## Compiled Update — 2026-10-23 (wrap-up sweep 19, workspace-58): a high-bit prefill rescues ~28% of a low-bit decoder's KLD gap, but the low-bit decoder is ~27% slower

**Confidence: verified** for the NEW-13 verdict against its predeclared rule and for the belief-ledger ingest; **descriptive only** for every tok/s figure (teacher-force throughput inside the probe, not a serving bench).

- **NEW-13 PASS (Q38FN, CPU, 0-95).** The probe prefilled with the served UD-IQ4_XS (P), copied the sequence state (KV plus recurrent) into a context holding GSQ-RCO IQ3_XXS (D), and teacher-forced 256 tokens on 120 held-out passages against one shared reference (P alone, chosen by the operator). Mean KLD (nats/token): D alone 0.213, P→D 0.153, P alone 0, D→P 0.101. R = (KLD_A − KLD_B)/KLD_A = **0.283, paired-bootstrap CI [0.246, 0.322]**, above the predeclared R ≥ 0.25 with CI_low > 0.10; Gate 0 informative (0.213 ≫ 0.005); coherence 0 regressions. Same-top-1 vs P: 84.2% / 85.9% / 90.0% (A / B / D).
- **It is a quality-transfer result, not a speed result.** Teacher-force decode: D alone 15.9 tok/s, P→D 15.8, P alone 21.9, D→P 22.6. On this CPU the IQ3_XXS decoder is ~27% slower than UD-IQ4_XS, so a P→D handoff is both slower and lower quality than serving P alone. Any follow-on (C-L3, a 27B-class IQ2_XXS pair) must report decode tok/s beside KLD and name a capacity or speed case before kernel work. The ODP-port trigger (C-L4) is not met for that reason.
- **The NEW-10 FAIL is now in the belief ledger, re-derived on a different binary.** The capture tool's `kld-quantcmp` mode needs the native EAR rows, which only the EAR build prints, and anchor and candidate must share one binary. The re-capture therefore ran on `experimental/ear-kld-column-20261022` @ `782c11ae4` at `-t 96`, not on the v10 store binary at `-t 24`. Values moved within the native ±1σ spread (G1 0.0215 vs 0.0150, G2 0.3206 vs 0.3222, G3 82.77% vs 82.88%), and the FAIL is unchanged. 21 rows and 63 frames were ingested (`--only-new`, idempotent). Lesson: a quant-comparison number is specific to its producer binary and thread count at the second decimal; compare within one binary, or carry the spread.
- **Receipts.** NEW-13's own `handoff_receipt.json` is hand-written and has no reader, so it is not in the ledger and is never backfilled. VB-NEW13-WIRE puts a capture-written receipt in place before C-L3 runs.

### Source References (2026-10-23 wrap-up sweep 19)

- [handoffs/active/iqk-iquant-enablement.md](../handoffs/active/iqk-iquant-enablement.md) — NEW-13 verdict, C-L3, NEW-13-RM
- [handoffs/active/vidya-belief-substrate-program.md](../handoffs/active/vidya-belief-substrate-program.md) — VB-QUANTCMP-NEW10 (ingested), VB-NEW13-WIRE
- [progress/2026-10/2026-10-23-workspace-58.md](../progress/2026-10/2026-10-23-workspace-58.md) — section 19 (19.4, 19.5)

## Compiled Update — 2026-10-24 (wrap-up sweep 9, delta over 2026-10-23)

- **27B IQ2 pair dropped; the low-bit follow-on is Q38FN only (C-L3-Q38FN).** Operator ruling: the 27B runs Q8 on the GPU, so C-L3 closed superseded. Evidence for the live task: prefill from UD-IQ4_XS into GSQ IQ3_XXS decode recovers 28% of the KLD gap (R 0.28 [0.25, 0.32]) but GSQ IQ3_XXS decode is about 28% slower (15.8-15.9 vs 21.9-22.6 tok/s). Step 1 profiles why: iqk fast-path coverage for these shapes (NEW-10 recorded 12 decode-only iqk fallback tensors) and Q2_0 `ffn_down_exps`. The 75.84 GB GSQ weights are kept instead of deleted.
- **AutoKernel hardened-row check is strict where new claims are gated.** `strict_unknown=True` at `microbench.py:4389` and `screening_baseline.py:202`, so a row with no `autokernel_hardened` field is refused (could-not-check is not a pass); 1190 execution tests pass with 3 pre-existing failures identical on a clean checkout.

Sources: [iqk iquant enablement](../handoffs/active/iqk-iquant-enablement.md), [autokernel rebuild program](../handoffs/active/autokernel-rebuild-program.md).

## Compiled Update — 2026-10-27 (operator wiki sweep, workspace-58)

**Confidence: verified** for PPL and coherence; the speed A/B is INDICATIVE (one quarter).

- **The uniform requant's +17.8% PPL came from degrading UD's Q8_0 tensors.** UD keeps attn/ssm/shexp/hc at Q8_0, down_exps at IQ4_NL/Q8_0, output at Q6_K, and gate/up mostly at IQ3_S. Arm P requantizes **only** `ffn_gate_exps`/`ffn_up_exps` to IQ4_XS (346 tensors, dry-run asserted); P2 additionally pins Q8_0 attn/ssm/shexp 2D weights with ncols%256==0 to Q6_K. ([iqk-iquant-enablement](../handoffs/active/iqk-iquant-enablement.md) C-L3-Q38FN arm P; [arm-P2 PREDECLARED](../docs/reference/agent-config/recipes/q38fn-armP2-20261024/PREDECLARED.md))
- **PPL (lower is better):** P 2.979 +/- 0.062 vs a paired UD re-run of 2.9868 +/- 0.063 (bar <= 3.10), against step-1 uniform 3.5244. The -0.26% delta is inside the standard error (wikitext c512 x 40 chunks, not KLD). The UD control and coherence (llama-server chat, think off, temp 0, recipe serving env) PASS. ([arm-P2 VERDICT](../docs/reference/agent-config/recipes/q38fn-armP2-20261024/VERDICT.md); [2026-10-27 harvest](../progress/2026-10/2026-10-27-workspace-58.md))
- **Speed gate FAIL:** pp256 +31.91% (bar +27%) but pp5 -6.12% (bar +19%) and tg128 -8.85% (bar -2.0%). P2 does not ship; the parent C-L3-Q38FN stays open. The 101 GB GGUF was reclaimed on 2026-10-27, and it can be rebuilt from the preserved recipe (job.sh, pins.txt, genpins.py, launcher.cmd). ([iqk-iquant-enablement](../handoffs/active/iqk-iquant-enablement.md); [2026-10-27 harvest](../progress/2026-10/2026-10-27-workspace-58.md); [recipe dir](../docs/reference/agent-config/recipes/q38fn-armP2-20261024/PREDECLARED.md))
- **A v1 harness lesson:** v1 ran without the serving env, so the default-ON fused decode made even the UD control incoherent (VOID). PPL and coherence must use the codified recipe env (AMENDMENT 1). ([iqk-iquant-enablement](../handoffs/active/iqk-iquant-enablement.md); [arm-P2 PREDECLARED](../docs/reference/agent-config/recipes/q38fn-armP2-20261024/PREDECLARED.md))

Sources: [iqk-iquant-enablement](../handoffs/active/iqk-iquant-enablement.md), [arm-P2 PREDECLARED](../docs/reference/agent-config/recipes/q38fn-armP2-20261024/PREDECLARED.md), [arm-P2 VERDICT](../docs/reference/agent-config/recipes/q38fn-armP2-20261024/VERDICT.md), [2026-10-27 harvest](../progress/2026-10/2026-10-27-workspace-58.md)

## Compiled Update — 2026-10-29 (operator wiki sweep, workspace-58)

**Confidence: verified** for the artifact-derived path-participation facts; the throughput cause is explicitly **unmeasured**.

- **C-L3-Q38FN existing-artifact profile: IQK path participation confirmed, cause not.** NEW-13's one-token teacher-forced log shows IQK MoE engaged for IQ3_XXS weights with Q8_K activation. Frozen v10 dispatch allows that path for one token and routes wider calls to the NMSE-guarded native fallback. NEW-10's type census records 38 Q2_0 and 58 IQ4_NL native tensors beside 12 decode-only IQ3_XXS IQK tensors. No per-kernel timings were captured, so neither the cause nor the share of the ~27% lower throughput is established. The causal profile stays open; arm-P/P2 probes were not rerun.
- **Arm P2 closed as no-ship, artifact reclaimed.** The 101 GB `q38fn-armP2.gguf` was reclaimed 2026-10-27; the recipe (job.sh, pins, VERDICT.md) is preserved in the repo and the file can be rebuilt from it. Verdict unchanged: PPL 2.979 vs UD 2.9868 but speed gate FAIL (pp5 -6.12%, tg128 -8.85%).
- **MI210 Q8 dequant-GEMV Item C retargeted (operator, 2026-10-28):** Qwen3.5-122B is deprecated and no longer serves; the IQ2_XXS kernel work is format-level and is to be re-measured on a current IQ-format target (DS41 or Q38FN low-bit lanes, or the GPU-resident IQ role), not the 122B.

Sources: [iqk-iquant-enablement](../handoffs/active/iqk-iquant-enablement.md) · [mi210-q8-dequant-gemv-roofline](../handoffs/active/mi210-q8-dequant-gemv-roofline.md) · [2026-10-29 codex refactor](../progress/2026-10/2026-10-29-codex-refactor-01a16fc3.md) · [2026-10-28 workspace-58](../progress/2026-10/2026-10-28-workspace-58.md)
