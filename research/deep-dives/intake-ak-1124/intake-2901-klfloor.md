# Dive — klfloor — intake-ak-1124

> SOURCE-QUARANTINE: {url: "https://arxiv.org/abs/2611.12634v1", retrieved: "2026-11-24", sha256: "9c00cc124155"}

authors: Dezhen Lu (Tubingen), Zixiang Ni (Xi'an Jiaotong); arXiv v1, cs.CL, 9 Nov 2026

## 1. Stage-1 fields
- title: How Far Does Second-Order Linear Response Predict Quantization Mismatch? Pre-Registered Measurements on Five Language Models
- authors/version: Lu and Ni, arXiv 2611.12634v1. CONFIRMED to be the paper qnoise (intake-2893) cited as "Lu and Ni": the abstract states a floor of 0.17-0.22 nats per sequence from reduction-order changes.
- categories: quantization, benchmark_methodology, inference_serving. novelty: low-medium (floor section is a side result). relevance: medium method / low numbers.
- credibility_score: 1 (not peer-reviewed 0; <=12 months +1; no major lab 0; no independent corroboration found 0).
- verdict: adopt_patterns. Take the A/A reduction-order floor as a measured denominator; import no magnitude.

## 2. Key claims
0. Floor 0.17-0.22 nats/sequence (4 pre-registered comparisons 0.17-0.21), teacher-forced Qwen3-8B, 256 x 768 tokens, GH200, vLLM, same on H100 - PARTIAL (units and scope; anchors 0,1).
1. Same kernel selection reruns are bitwise identical; batch size barely matters under a shared autotune cache - CONFIRMED (anchor 2).
2. Differences below ~0.2 nats per sequence are unresolvable unless kernel selection is fixed - CONFIRMED (anchor 3).
3. Units: KL is summed per sequence (int4 29.7 nats per 256-token sequence) - PARTIAL, inferred from magnitude (anchor 4). Floor at 768 tokens vs quantisation KL at 256 tokens: not same length.
4. Batch-invariant kernels cost 0.55x throughput (32 concurrent), 0.81x teacher-forced - CONFIRMED (anchor 5), GPU vLLM only.
5. "One number" across engines - NARROWED: floor shown on Qwen3-8B only.

## 3. Reported results
vLLM, GH200: see claims. Screener on Mistral-7B-v0.3: 6/6 within band [0.75,1.50], ratios 1.03-1.12, budgets 3/3, throughput within 0.4%. No llama.cpp, HIP or CPU measurement in source.

## 4. Performance-principles table
| Principle | MI210 gfx90a | Zen 5 EPYC | Reason |
|---|---|---|---|
| Floor = KL between two reduction-order variants of the same weights | YES | YES | Needs only two builds/env toggles (e.g. GGML_HIP_Q8IP_MMVQ_MAX, GGML_ROWEXACT_N) on the gate's corpus; device independent method |
| Fixed kernel selection removes the floor | PARTIAL | PARTIAL | llama.cpp has no autotune; selection is fixed by build/env, so same-binary reruns are bit-identical (qnoise A1) except GPU DFlash2 np1 (SPEC-ID-NOISE-1); the floor appears across builds, which is what fold gates compare |
| Batch-invariant kernels as a cost trade | NO (not measured) | NO (not measured) | 0.55x is vLLM GPU; a local equivalent would be ROWEXACT-type paths whose cost is measured elsewhere |
| Floor magnitude 0.17-0.22 | NO | NO | engine, device and model specific; spec-identity-gate-protocol s2 forbids imported floors |

## 5. In-house state
- Identity bands are in top-2 margin nats at the first divergence (docs/guides/agent-workflows/spec-identity-gate-protocol.md s3, class tau default 0.5, SPEC-ID-NOISE-1 tau 0.22-0.60 on GPU @ f74b175). That is a per-token margin currency, not summed KL: the paper's floor does NOT change identity-band currency (QN-1 as proposed stands). Coincidence of 0.22 appears in both; they measure different things and must not be equated.
- Fold gates use KLD<=0.003, |dPPL|<=0.5%, top-1 (kernel-champion-and-promotion.md:L28 C17-FOLD-GATES @ f74b175), a per-token quality gate between a candidate and its predecessor build. Reduction order differs between those builds, so a floor is inside every measured KLD. If the 0.2 nats were summed over 768 tokens, it is about 2.2e-4 to 2.9e-4 per token (derived), roughly 7-10% of the 0.003 gate; at that size the gate is not floor-limited. Our own floor for 27B Q8_0 is NOT-FOUND (never measured as a KLD A/A).
- No llama.cpp source involved (no anchor @ 98ff8a4).

## 6. Derived-actionables ledger
1. refines qnoise QN-1: Draft: "Measure a KLD A/A floor for the fold-gate corpus: KLD between two reduction-order variants of the same weights (candidate binary with one MMVQ/row-exact toggle flipped) on 27B Q8_0 and Q38FN, and add 'candidate KLD / A/A KLD floor' to the fold-gate result header." Owner: kernel-champion-and-promotion.md (new box beside the ticked C17-FOLD-GATES; check not a frozen section) with QN-3's env recording in speculative-decoding.md. Compute: one GPU KLD row + one CPU KLD row on retained logits (reuse the fold gate's reference logits first; if the retained C16-vs-C17 KLD already sits at the floor magnitude, that is the answer offline). Decision rule: if floor <= 10% of the gate (0.003) keep the gate and report the ratio; if floor >= 30% make the gate relative to the floor. Question: is 0.003 floor-limited on our builds? Stop-on-answer when both devices have a floor value or the offline check answers it; futility-only until formal-gate decisions land.
2. Decline: importing 0.17-0.22 nats or the 0.55x throughput as a threshold or cost; reason: vLLM bf16 GH200 Qwen3-8B, summed per 768-token sequence; protocol s2 forbids imported floors.
3. Decline: adopting the Fisher/second-order quantization screener; reason specific to this entry: it is a weight-format selection tool for vLLM checkpoints and our lane is fixed-format kernel gating; the paper itself finds it fails for MoE routing and int4 at 32B (diagonal 5.18x under-prediction).

## 7. Dive-surfaced sources
None to ingest. No further source would change row 1 (floor must be measured on our builds).

## 8. Contradiction / adversarial pass
- Authors: floor measured on one model; the shared autotune cache means they cannot separate kernel-selection from batching effects (they say so). Per-sequence sum vs per-token mean is the main hazard for misuse. 0.22 here and 0.22 in our SPEC-ID-NOISE-1 are unrelated quantities.

9. read_depth: PARTIAL (see draft). lane_head: f74b1759ccae8f76ba3d41146d47e687717954a9.
10. artifact audit: clean (6 anchors verified).
