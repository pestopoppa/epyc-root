# Dive — samereq — intake-ak-1124 (Stage 2b wave 1, expanded from intake-2872 exactpaper)

> SOURCE-QUARANTINE: {url: "https://arxiv.org/abs/2609.04748v3", retrieved: "2026-11-24", sha256: "60ed565bdde9"}

Note: the retained page is v3 (arxiv_meta.json), not v1; all figures below are from v3.

## 1. Stage-1 fields
- **Title:** Same Request, Different Answer: Quantization Amplifies Cache-Induced Divergence in LLM Serving
- **Authors:** Aditi Patodiya (independent researcher). arXiv 2609.04748 v3; IEEE Access, received 10 Oct 2026, accepted 29 Oct 2026 (doi 10.1109/ACCESS.2026.3749922).
- **Setup:** RTX 4090 (sm_89, CUDA 12.6), llama.cpp b10434 (7e4c0a9) and vLLM 0.11.0; Qwen2.5-7B/14B and Llama-3.1-8B, GGUF F16/Q8_0/Q4_K_M/Q3_K_M. Greedy, seed 42, batch size 1, serial requests, 16,384 ctx. **KV cache is 16-bit in every arm** (KV quantization is NOT a variable). Workload: first 80 BFCL multi-turn episodes (about ten requests each); GSM8K as a single-turn bridge. No speculative decoding.
- **Categories:** kv_cache, quantization, inference_serving, benchmark_methodology.
- **Novelty:** medium-high for us. We have per-request cache_prompt/--cache-ram flags and a prefix-cache program (PFXC) but no identity-gate treatment of cache state.
- **Relevance:** high: our served recipes run `--cache-ram 32768`/`65536` and cache_prompt on (CURRENT-CAMPAIGN.md:115-116 @ f74b175), while the SPEC-ID-NOISE-1 floors were measured with cache_prompt false and `--cache-ram 0`.
- **credibility_score: 3.** Arithmetic: peer-reviewed +2 (IEEE Access acceptance stated on the page); <=12 months +1; known lab 0; commercial bias 0; independent corroboration 0 (the paper describes Lorup 2607.28495 as concurrent agreement; I did not read it, so no credit; qnoise cites this paper but measures no cache). Strengths outside the formula: full harness/logs released (not fetched), control arms repeat exactly, restored-state controls, telemetry-verified cache exposure.
- **Verdict: worth_investigating.** The mechanism is well supported at batch 1 on CUDA; its magnitude on our HIP/CPU spec path with q8_0 KV is unmeasured, and one named probe row (SR-2) answers it.

## 2. Key claims
1. **With prefix reuse off, repeated runs are exactly reproducible; with it on, cache-hit and recompute paths diverge.** CONFIRMED (0 of 800 configuration-episode executions divergent with cache off, all ten configs; 277,280 tokens and log-probs identical; path divergence 36.2 to 91.2% of episodes with cache on). Anchor A1.
2. **Weight quantization amplifies the path divergence (llama.cpp GGUF, Qwen2.5-7B): 37.4% F16, 59.5% Q8_0, 82.5% Q4_K_M, 77.1% Q3_K_M over ten histories; odds ratio 2.30 per format step [1.76, 3.15].** CONFIRMED for this engine/model; Q3_K_M is not established above Q4_K_M (CI -15.6 to 5.0 on that difference). The F16 to Q8_0 step alone is +22.1 points [9.9, 34.4]. Authors state it is llama.cpp-kernel specific. Anchor A2.
3. **The amplification sits in the quantized execution path, not in the rounded weight values; near-tie share barely moves (about 1.2x) while the cache-path change in top-two margin grows 4.9x.** CONFIRMED with a caveat: dequantizing Q4_K_M to a 16-bit file left divergence at 33.4% vs 37.5% F16 and 81.9% Q4_K_M (CI for dequant minus F16 -17.8 to 9.7, not equivalence). The kernel account (MMVQ for calls up to eight tokens, tiled MMQ for longer, both round activations to 8-bit blocks) is an interpretation from the code, not an instrumented result. Anchor A3.
4. **llama.cpp's server-level prompt cache (--cache-ram, default 8192 MiB) drives run-to-run divergence: 1.2% with it disabled vs 38.8% at default under the canonical order (+37.5 points); five random orders at default spanned 20.0 to 28.7%.** CONFIRMED (80 episodes, one model/quant, dependence-aware intervals). Disabling it cost 5% latency (0.290 s vs 0.305 s per request) and kept prefix reuse's gain. Anchor A4.
5. **Given cache state the cached path is deterministic; path divergence remains under every control.** CONFIRMED: reset control, all four formats, three sessions each, both paths reproduced on every item; paths still differed on 2, 43, 43, 60 of 100 GSM8K items (F16, Q8_0, Q4_K_M, Q3_K_M). Only turning prefix reuse off, or kernels that compute both paths identically, removes it. Anchor A5.
6. **Path divergence reaches task outcomes as instability without detectable net bias.** CONFIRMED narrowly: GSM8K 20 correctness flips (13 favour cache, 7 recompute), net +0.46 points [-0.15, +1.15]; the agentic workload cannot answer the outcome question (success near floor). This also contradicts the systematic-bias reading of illusion (see that dive). Anchor A6.

## 3. Reported results (as stated)
RTX 4090, 80-episode BFCL multi-turn, batch 1: run-to-run divergence cache-off 0.0% in all ten configs; cache-on 8.8 to 77.5%; path divergence 36.2 to 91.2%. vLLM 0.11.0: path divergence 62.5% (Qwen2.5-7B BF16) and 53.8% (Llama-3.1-8B BF16). GSM8K single-turn path divergence 3.5% at F16 vs 41.5 to 48.0% quantized. Margin perturbation median 0.028 logits (F16), 0.10 (Q8_0), 0.16 (Q4_K_M), 0.14 (Q3_K_M). First differing request has median index 1 to 4 of roughly ten.

## 4. Performance-principles table (mechanism / cost model)
| Principle | MI210 gfx90a | Zen 5 EPYC |
|---|---|---|
| Cache-hit tokens' KV was written by a different batch shape than a recompute would use, so the later logits differ in low bits | YES: ggml-cuda.cu selects kernels by batch size (`src1->ne[1] <= MMVQ_MAX_BATCH_SIZE`, ggml-cuda.cu:1978, 2175-2183 @ 98ff8a4), plus our own mmq-q8 skinny/mf/wvsk kernels; spec verify batches (2-16 rows), plain decode (1) and prefill (large) all write KV under different kernels | YES (uncited detail): CPU mul_mat paths also switch by row count (`GGML_ROWEXACT_N` exists because 1<ne11<=N rows are not bit-equal to decode, ggml-cpu.c:1505 @ 98ff8a4) |
| Quantized weights multiply the perturbation (activation rounding to 8-bit blocks can cross a step) | YES, presumed: served weights are Q8_0 (27B, A3B); the F16 to Q8_0 step was already +22.1 points here. The paper's KV was F16 so q8_0 KV (our served -ctk/-ctv q8_0) adds an untested second rounding site | YES, presumed: Q8_0/IQ4_XS served; same caveat on KV |
| Server-level prompt cache selects among stored states by LCP similarity, so output depends on traffic history | YES: llama-server `--cache-ram` is in C21 (common/arg.cpp:1637 @ 98ff8a4) and enabled on served roles | YES, same server code |
| Reset/sentinel control restores the cold state | YES: per-request `cache_prompt:false` forces recompute (paper: the erase endpoint returned success while leaving state intact, so verify from cached-token counts) | YES |
| Dequantize-to-F16 control | NO (not worth it): changes the model; interesting only as mechanism proof, which we do not need for a gate | NO, same |

## 5. In-house state
- Protocol §2 (exact-identity regime) lists build, concurrency, width class and measured determinism, with no condition on cache_prompt or --cache-ram (spec-identity-gate-protocol.md §2, grep for cache returns nothing @ f74b175).
- SPEC-ID-NOISE-1 ran every request with `cache_prompt` false and `--cache-ram 0` (GPU job.py lines 10-12, 66, 271; CPU job.py lines 17, 176; under /mnt/raid0/llm/tmp/ak-spec-id-noise-*-20261123), with q8_0 KV on the GPU arm. Its floors are therefore cache-off floors. The protocol does not say so.
- Served config uses caching: frontdoor keeps llama-server `cache_prompt` (harness-program.md:785 @ f74b175), roles run `--cache-ram 32768`/`65536`.
- PFXC-A1 (kernel-champion-and-promotion.md:120-126 @ f74b175) filed pass with "resumed-vs-fresh 0.773 vs C14 floor 1.077" against a pre-registered falsification of |dlogprob| >= 1e-3: the resumed-vs-fresh difference is far above the original bar, and the pass was a comparison to a floor (single baseline measurement as far as the row states). This is exactly the cache-path divergence this paper measures.
- Many existing gates already pin `cache_prompt` false (cpu-decode-roofline-program.md:279; long-context-program.md:1491), consistent with the paper's advice.

## 6. Derived-actionables ledger
| # | Task line | Owner (lane file; status) | Compute | Stop / decision rule |
|---|---|---|---|---|
| SR-1 | Add a cache-state condition to the exact-identity regime (§2) and to §6 fold gates: every arm runs `cache_prompt:false` and `--cache-ram 0`, or both arms carry the same verified cache state; retain `cache_n` per request and make a nonzero cache_n in a cold-labelled arm INCONCLUSIVE; state that SPEC-ID-NOISE-1 floors are cache-off floors | speculative-decoding.md, new box under SPEC-ID-GATE-1 ([x]); doc plus `spec_dist_gate.py` | code/doc-only | Done when the doc states the rule and the checker rejects an unlabelled-cache result. Answers: can a gate result be reproduced from the request alone |
| SR-2 | Run a cache-hit vs cold-recompute identity probe on the served recipe: N prompts with a shared >=2k-token prefix, C21 q8_0 KV, margin-class classify the first divergence of cache-hit vs cold (with a same-run A/A on each path) | kernel-champion-and-promotion.md (PFXC family; check not frozen at apply); GPU row 27B Q8_0 + DFlash2 np1 and CPU row A3B/Q38FN np1 | GPU + CPU rows | Question: does the cache-hit path stay inside margin-class NOISE (<=0.5 nats) and what share of prompts diverge, per device? Stop-on-answer after one 64-prompt pass per device; futility-only stop on residency-proof failure (`verify_ggml_linkage.sh`, nonzero VRAM sampled during the run). Decision: if any gt0.5 or the share exceeds the cache-off floor by the paired d test, every identity gate that runs on the served cache configuration must label cache state; if not, SR-1 stays doc-only |
| SR-3 | Replace PFXC-A1's single-baseline floor comparison ("0.773 vs 1.077") with a replica floor: repeat the C14 resumed-vs-fresh baseline on >=3 launches and report the largest pair | kernel-champion-and-promotion.md PFXC-A1 (filed [x]; add a follow-up box) | CPU/GPU small row | Question: was 0.773 inside the floor or luck of one baseline? Same stop rule as QN-1 |

Declines: (a) dequantized-weights control and the vLLM lane: mechanism proof, no decision of ours changes; (b) the BFCL agentic harness: success rates sit near floor for models this size (paper's own admission), so it cannot rank anything for us; (c) turning prefix caching off in production: the paper itself finds no net accuracy loss and a 2.9x latency gain, and the PFXC program exists for hit rate.

## 7. Dive-surfaced sources
- 2607.28495 (Lorup, stage-replay divergence follows the KV cache; fixed-prefix precision controls and bidirectional cache transplantation): ABSENT from the index (grep unbounded). Settles whether divergence is attributable to the cache state vs the prompt path via transplantation and an FP32 falsification. Would not change SR-1/SR-2 decisions. Decline.
- vllm-project issue numbers cited by the paper (78% to 60% accuracy drop; ROCm-only identical-request divergence): not in the page as URLs I can verify; the ROCm-only report is relevant to MI210 but cannot be retrieved here. Decline until a URL is given.
- 2606.09864 and 2506.09501 already present in the index (not re-listed).

## 8. Contradiction / adversarial pass
- Single machine per comparison group but three machines/drivers overall; the authors checked reproduction between them. vLLM lane is directional only (its two sessions differ in launch script and memory fraction; 8.8% vs 27.5% for the same model).
- 80 ordered episodes are not exchangeable; intervals are block-bootstrap/Wilson envelopes, which the authors call approximate; the replicated sweep carries the quantization claim. Q3_K_M vs Q4_K_M order is not established.
- Mechanism (accumulation order, kernel switch) was not instrumented; "we did not isolate whether the 8-bit rounding or the kernel switch enlarges the perturbation".
- Not tested: KV quantization, GQA/hybrid recurrent models, speculative verification, HIP. Generalisation to our stack is an open probe (SR-2), not a result.
- Restatement vs corroboration: Lorup is described by this paper as concurrent agreement; that is the same author's characterisation, not independent corroboration here.

## 9. read_depth
FULL for abstract, design, results through Table VII and the discussion of practitioner consequences; PARTIAL for the remainder of Section V-B onward and the reference list (not needed for the settled questions). Harness/logs not fetched. lane_head: f74b1759ccae8f76ba3d41146d47e687717954a9.

## 10. Artifact audit
artifact audit: clean
