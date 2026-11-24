# Dive — illusion — intake-ak-1124 (Stage 2b wave 1, expanded from intake-2872 exactpaper)

> SOURCE-QUARANTINE: {url: "https://arxiv.org/abs/2604.15409v1", retrieved: "2026-11-24", sha256: "fe422d88c778"}

## 1. Stage-1 fields
- **Title:** The Illusion of Equivalence: Systematic FP16 Divergence in KV-Cached Autoregressive Inference
- **Authors:** Ranjith Chodavarapu, Lei Xu (Kent State University). arXiv 2604.15409 v1 (April 2026 by id; exact date not stated in the retained page).
- **Setup:** single H100 NVL, PyTorch 2.5.1, HuggingFace Transformers 4.53.0, hand-written token-by-token loop; LLaMA-2-7B, Mistral-7B-v0.3, Gemma-2-2B in FP16; 700 GSM8K problems x 5 seeds, 128 new tokens, greedy/top-k/top-p; "cache-OFF" re-forwards the whole prefix at each step, "cache-ON" is HF KV caching; CUBLAS deterministic mode on. This is NOT llama.cpp, not HIP, no quantization.
- **Categories:** kv_cache, benchmark_methodology, inference_serving.
- **Novelty:** low-medium (mechanism is the standard non-associativity account; samereq, a better-controlled study, supersedes it for magnitude).
- **Relevance:** medium: it gives the mechanism vocabulary (KV written under a different accumulation order), but its magnitudes cannot be used and its bias claim is contradicted.
- **credibility_score: 2.** Arithmetic: peer-reviewed 0; <=12 months +1; known lab 0; commercial bias 0; independent corroboration +1 (samereq independently finds cache-path divergence exists, but contradicts rate and direction, so credit is for existence only). Internal inconsistencies below weigh against it outside the formula.
- **Verdict: adopt_patterns** (mechanism and gate-control checklist only). Existence of cache-path divergence is confirmed by samereq; the headline numbers are not.

## 2. Key claims
1. **Cache-ON and cache-OFF decoded sequences diverge in 100% of cases, including greedy.** PARTIAL / not a general rate. Reported for 31,500 pairs at 128 new tokens with HF defaults. samereq measured 3.5% of single-turn items at F16 and 36 to 40% of ~10-request agentic episodes, with cache-off exactly reproducible. Also internal tension: Table 1 gives 100% divergence while Table 2 gives an FP16 flip rate of 1.03 to 1.15% (unit not stated on the page; n=600 examples, 32 decode steps). Anchor A1.
2. **FP32 removes the divergence (flip rate 0.0, KL floor ~2.5e-8), so FP16 non-associativity is the sole cause.** PARTIAL. The FP32 falsification is consistent with a rounding mechanism and is a useful control idea. "Sole" is not shown (the cache-ON/OFF paths also differ in layout and kernels), and the "more than eight orders of magnitude" figure uses an FP16 KL of order 10 from Table 1; Table 2's own FP16 KL is 0.112 to 0.122 (ratio about 4e6, roughly six and a half orders, from 0.113 / 2.8e-8). A mean KL of 10 to 13 nats in Table 1 is not what rounding-level differences produce (judgement; our own gate data show 94% of first divergences at margin <=0.1 nat). Anchor A2.
3. **Cache-ON yields higher accuracy than cache-OFF in 8 of 9 conditions, so the direction is systematic.** OVERTURNED as a general claim. The protocol's accuracy is 1.1 to 6.6% on GSM8K (128-token truncation plus few-shot format; the authors warn it is "an indicator of execution-path bias, not a measure of absolute reasoning ability"), Gemma greedy is not significant, and samereq (cache-hit vs recompute, GSM8K, five configs) found 13 vs 7 flips, net +0.46 points [-0.15, +1.15], i.e. instability with no detectable direction. Anchor A3.
4. **GQA broadcasts one FP16 rounding error to R query heads, so a larger sharing ratio amplifies divergence.** NOT SUPPORTED by the evidence: three models differ in size, head dimension, sliding window and training; the authors list "formal quantifying of the GQA amplification factor across various sharing ratios" as future work. Treat as hypothesis. Anchor A4.
5. **Residual-stream activation patching fails to recover the cache-free trajectory, localizing the divergence to the KV cache state.** PARTIAL: authors state it is "localization by elimination", direct KV patching is future work. Consistent with samereq's restored-state control (given state, each path reproduces exactly) and with our own redecode result below. Anchor A5.
6. **Behavioural flips happen where the model is near a decision boundary, not where the numerical drift is largest.** CONFIRMED qualitatively here (early flips go with higher KL jointly caused by uncertainty) and corroborated by samereq's margin hazard (at Q4_K_M 2 of 3 positions with margin <0.01 flipped, none of 8,038 above 3). Anchor A6.

## 3. Reported results (as stated; H100 NVL, HF Transformers 4.53, FP16, 128 new tokens, GSM8K 700 problems x 5 seeds)
Table 1: token divergence 100% in all nine model-strategy conditions; mean KL 10.68 to 12.83; cache-ON vs cache-OFF accuracy e.g. LLaMA-2 greedy 3.3% vs 2.0%, Mistral greedy 6.6% vs 2.0%, Gemma greedy 1.9% vs 2.1% (non-significant). Table 2 (n=600, 32 steps): FP16 KL 0.113 / 0.122 / 0.112 (LLaMA-2, Mistral, Gemma), FP32 KL 2.8e-8 / 2.5e-8 / 2.78e-8, FP16 flip 1.15 / 1.14 / 1.03%, FP32 flip 0.0%. Mean relative FP16 accumulation error about 0.036%, flat over 16 to 128 tokens. Residual-stream patching recovers a median under 1%.

## 4. Performance-principles table (mechanism / cost model)
| Principle | MI210 gfx90a | Zen 5 EPYC |
|---|---|---|
| KV tensors written under one accumulation order are read under another (cache-ON vs recompute) | YES, with a twist: llama.cpp has no no-cache decode mode, but KV for a token is produced by a mul_mat whose kernel depends on the batch size (ggml-cuda.cu:1978, 2175-2183 @ 98ff8a4), so KV written by a 2-16-row verify batch, a 1-row decode and a prefill ubatch differ in low bits; our q8_0 KV then rounds K/V to int8 blocks, where a tiny difference can cross a step (hypothesis, untested) | YES (uncited detail): CPU row-count-dependent mul_mat paths (`GGML_ROWEXACT_N` exists for this reason, ggml-cpu.c:1505 @ 98ff8a4) |
| FP32 control arm removes the divergence | PARTIAL: an f32-compute/f32-KV arm on a small model is a cheap mechanism audit (support for f32 KV with FA on HIP is uncited, check) | YES: CPU f32 path exists for small models; cheapest place to run it |
| GQA ratio predicts divergence | NO evidence: n=3 confounded models; Qwen3.5/3.6/3.8 hybrids have few attention layers, so any effect would sit in those layers (uncited) | same |
| Decision-boundary proximity governs flips | YES: matches the margin-class gate design (gt0.5 defect candidate) | YES |

## 5. In-house state
- SPEC-ID-NOISE-1's `redecode` arm was pre-registered to fail "because redecode reuses verify-written KV and GDN state" and did (REDECODE_FAIL_CONFIRMED, prompts 2, 11, 52; speculative-decoding.md:908 @ f74b175): KV and recurrent state written under verify shape differs from serial. This is the in-house instance of the illusion/samereq mechanism, and it says serial does not restore width-1 identity on GPU (protocol §2 @ f74b175).
- Protocol §2/§3 control build, concurrency, width class, determinism and margin classes; they do not list KV dtype, KV-writing path, cache_prompt or --cache-ram (see samereq dive SR-1). The noise runs used q8_0 KV, cache_prompt false, `--cache-ram 0`.
- llama.cpp f16 KV on HIP is not the served config (served: -ctk/-ctv q8_0, SPEC-ID-NOISE-1 job.py line 12), so the paper's FP16-cache premise applies to our stack only as "KV precision/rounding differs by writer path".

## 6. Derived-actionables ledger
| # | Task line | Owner (lane file; status) | Compute | Stop / decision rule |
|---|---|---|---|---|
| IL-1 (refines samereq SR-1) | Add a KV-provenance condition to protocol §2: identity-gate arms must write KV by the same path (same prefill ubatch, same verify width class, same KV dtype), record `-ctk/-ctv`, `-ub`, spec width in RESULT.json, and label `redecode`/resume-from-verified-KV paths as outside the exact regime | speculative-decoding.md, same new box as SR-1 | code/doc-only | Done when the doc and checker carry the fields; cites SPEC-ID-NOISE-1 REDECODE_FAIL_CONFIRMED as the in-house example |
| IL-2 (refines exactpaper A7) | Run a precision-escalation audit arm: the same spec-vs-serial and resumed-vs-fresh comparisons on a small hybrid/attention model with f32 compute and f32 KV (CPU first); expect 0 divergences | kernel-champion-and-promotion.md or speculative-decoding.md (new box); CPU small row, then GPU if f32 KV is supported there | CPU row (tiny model), GPU optional | Question: is the residual divergence rounding or a logic defect? Stop-on-answer: 0/64 at f32 means the f16/q8 divergence is rounding (gate classes stand); any nonzero at f32 is a defect candidate to investigate. Futility-only stop if f32 KV is unsupported on the path (record and fall back to f32 compute with f16 KV) |

Declines: (a) the GQA-ratio amplification claim and the activation-patching method: n=3 confounded models and elimination-only localization; no decision of ours changes; (b) FP32 as a production mitigation: 2x memory and bandwidth on a bandwidth-bound decode is not a serving option, and divergence is already classified by margin; (c) the systematic cache-ON accuracy advantage: contradicted by samereq (see claim 3).

**What an identity gate must control for (settled):** (1) which batch shape wrote each KV entry (prefill ubatch, decode, verify width); (2) KV dtype; (3) cache state: cache_prompt, `--cache-ram`, slot history and request order (samereq); (4) concurrency and width class (already in protocol); (5) a same-run replica arm per path. FP16 itself is not the control variable on our stack, which serves q8_0 KV.

## 7. Dive-surfaced sources
- 2607.28495 (Lorup): see samereq dive; ABSENT, decline (would not change IL-1/IL-2).
- 2506.09501 and 2510.22876 already present in the index.
- No new source would change a ledger row. Decline all others.

## 8. Contradiction / adversarial pass
- samereq (IEEE Access, cache-hit vs recompute with replica controls) contradicts the 100% rate (3.5% single-turn at F16; 36 to 40% of episodes) and the systematic direction (13 vs 7 flips, net +0.46 [-0.15, +1.15]). samereq cites this paper and treats it as a single-turn arithmetic result.
- Internal inconsistencies: Table 1 mean KL 10.68 to 12.83 vs Table 2 FP16 KL 0.112 to 0.122; "eight orders of magnitude" relies on the former; Table 1 100% divergence vs Table 2 flip rate about 1.1% (unit unstated). Absolute accuracy 1.1 to 6.6% under truncation, so accuracy deltas are on a near-floor metric.
- No deterministic-kernel reconciliation of the cache-OFF path (full re-forward uses a different attention kernel than cached decode); "sole causal driver" is asserted from the FP32 arm alone. Localization is by elimination only.
- Three models, one benchmark, one device, no quantization, no llama.cpp. Authors' limitations section agrees on scope.

## 9. read_depth
PARTIAL: abstract, introduction, background, analysis framework, setup, Table 1, 6.3 (Table 2), discussion and limitations read; layer-drift (6.2), decision-boundary tables (6.4) and patching (6.5) detail, references not read. lane_head: f74b1759ccae8f76ba3d41146d47e687717954a9.

## 10. Artifact audit
artifact audit: clean
