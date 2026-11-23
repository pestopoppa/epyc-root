# Dive — llm42 — intake-ak-1123

> SOURCE-QUARANTINE: {url: "https://arxiv.org/abs/2601.17768v2", retrieved: "2026-11-23", sha256: "ba4dfbab4114"}

Expanded from intake-2830 (vegafafnir), section 7. The arXiv HTML render read is v2 (30 Jan 2026), title confirmed by the arXiv API. Extra reading, not used for anchors: the authors' repo `github.com/microsoft/llm-42` README at commit `814fb397c43d` (Apache-2.0, built on SGLang v0.5.3, with a "SOSP 2026 Artifact Evaluation" badge and the description "[Accepted to SOSP 2026] Fast Deterministic LLM Inference").

## 1. Stage-1 fields

- **Title**: LLM-42: Enabling Determinism in LLM Inference with Verified Speculation
- **Authors**: Raja Gond, Aditya K Kamath, Ramachandran Ramjee, Ashish Panwar (Microsoft Research; University of Washington)
- **Version**: arXiv 2601.17768v2, 30 Jan 2026, cs.LG. SOSP 2026 acceptance is stated by the authors' repo, not in the v2 text.
- **Categories**: inference_serving, speculative_decoding, benchmark_methodology
- **Novelty**: medium. Batch-invariant kernels (He et al. / Thinking Machines; adopted by vLLM and SGLang, cf. intake-656 #40408) are the incumbent. LLM-42 replaces them with scheduling: fast-path decode, then a fixed-shape replay verifier that commits, rolls back and overwrites the KV cache. It also gives the first cost accounting of batch invariance.
- **Relevance**: medium. It bears directly on what our `GGML_DETERMINISTIC` knob should and should not try to be, and on the KV-provenance point behind intake-2830 A4. It does not bear on serving: production samples at T > 0 and is always speculative, and LLM-42 does not integrate with speculative decoding.
- **credibility_score**: 4. SOSP 2026 acceptance per the authors' repo: +2. I count it, but note it is not stated in the arXiv text. v2 is 10 months old: +1. Microsoft Research: +1. No commercial bias (Apache-2.0 research code): 0. No independent replication of the cost figures found: 0.
- **Verdict**: adopt_patterns. Three patterns transfer: (a) the position-invariance definition, as a cheap unit test for our deterministic reductions; (b) the rule that the reference pass must also own the KV/state it leaves behind; (c) fixed-shape determinism as a weaker but cheaper target than width-1 equality. The DVR system is not adopted (see the decline in §6).

## 2. Key claims

0. **Batch-invariant GEMM costs up to 63% of GEMM throughput: CONFIRMED, as stated.** cuBLAS reaches up to 527 TFLOPS against a 194 TFLOPS peak for the Triton batch-invariant kernel, on Llama-3.1-8B down-projection shapes on their GPU (the evaluation platform is H100 PCIe). The stated cause is that the batch-invariant kernel drops split-K, TMA and warp specialization. RMSNorm: Triton batch-invariant up to 50% slower than fused CUDA, and the Python version up to 7x slower.
   - page §2.3: "On our GPU, cuBLAS (via torch.mm ) reaches up to 527 TFLOPS, whereas the batch-invariant kernel peaks at 194 TFLOPS, a slowdown of 63%"
   - page §1: "the batch-invariant GEMM kernels provided by He et al. do not use the split-K strategy"
1. **"56% end-to-end": PARTIAL (narrowed).** The 56% is one decode-throughput scenario: 11 concurrent requests, where a single deterministic request forces the whole batch onto batch-invariant kernels, giving 931 → about 415 tok/s. LLM-42 serves the same mix at 911 tok/s (2.2x SGLang-deterministic, within 3% of non-deterministic). The general offline penalty for SGLang-deterministic is 24-36%.
   - page §2.3: "causing throughput to collapse by 56% to about 415 tokens/s"
   - page §5.1: "Enabling deterministic inference in SGLang incurs a substantial throughput penalty, ranging from 24% (in=2048, out=512) to 36% (ShareGPT)"
2. **Decode-verify-rollback design: CONFIRMED.** The fast path decodes with dynamic batching. The verifier replays a fixed-size window under a fixed shape (end-of-sequence windows are padded to exactly T), commits matching tokens plus one verifier token, and rolls back from the first mismatch. Decode-written KV entries are always overwritten with the verifier's entries. Prefill is made deterministic by not batching it across requests. Grouped verification (default 8 requests × 64 tokens) amortizes verify cost.
   - page Abstract: "The verifier replays candidate tokens under a fixed-shape reduction schedule, commits those that are guaranteed to be consistent across runs, and rolls back those violating determinism"
   - page §4.2: "we overwrite the KV cache entries produced during decoding with the corresponding entries from the verification pass"
   - page §4.1: "We handle this by padding with dummy tokens so that the verifier always processes exactly T tokens"
3. **The guarantee rests on position-invariant (shape-consistent) kernels and excludes atomic reductions: PARTIAL.** It is confirmed as the paper's premise. As a general fact it is overturned for our stack. The paper asserts that forward-pass kernels use no atomic reductions. On our MI210, the Q8_MF V5 matmul flushes split half-tiles with `global_atomic_add_f32`, and `mmq-q8-skinny.cu:242` uses an unordered `unsafeAtomicAdd` (design doc §1a, §5 @ d785b6d). So LLM-42's O2 does not hold on our GPU until the `GGML_DETERMINISTIC` fixes are on.
   - page §3 fn 3: "Note that such guarantees do not hold for kernels that implement reductions via atomic operations. Fortunately, kernels used in the LLM forward pass do not use atomic reductions"
   - page §3: "Position invariance implies that, with a fixed total batch size, an input element’s output is independent of its position in the batch"
4. **Verify and recompute cost model: CONFIRMED.** Profiled on Llama-3.1-8B, H100-PCIe. Per-token verify cost is up to 0.75 ms at small windows and 0.05 ms at window 512 (15x). Recompute overhead is 6.81% at window 32 and 46.41% at window 256. Offline worst case, 100% deterministic traffic: ArXiv 10.97% recomputed tokens and 3351 rollbacks over 4096 requests.
   - page §4.3: "the verification cost is high—up to 0.75 ms per-token"
   - page §4.3: "recomputation overhead is 6.81% at a window size of 32 and increases roughly linearly, reaching 46.41% at a window size of 256"
   - page Table 4 caption: "grouped verification over 8 requests, 64 tokens each"
5. **Determinism is not equivalence: CONFIRMED (stated limitations).** LLM-42 makes repeated runs consistent; it does not make output equal to batch-1 decoding. Prefill and decode use different reductions, so the system is not prefill-decode invariant: no prefix-cache sharing. It is not integrated with speculative decoding.
   - page §5.3 Limitations: "A second limitation is that prefill and decode use different reduction strategies in LLM-42 , making the system non–prefill-decode invariant"
   - page §5.3 Limitations: "Our implementation also does not currently integrate with speculative decoding–based LLM inference"

## 3. Reported results (as stated; Llama-3.1-8B-Instruct, 4× H100 PCIe 80 GB, SGLang 0.5.3rc0, FA-3 with num_splits=1 in verify)

- GEMM: cuBLAS up to 527 TFLOPS vs batch-invariant Triton peak 194 TFLOPS (63% slowdown). RMSNorm: Triton batch-invariant up to 50% slower than fused CUDA; Python up to 7x slower.
- Decode throughput: 10 non-deterministic requests 845 tok/s; 11 requests 931 tok/s; 11 requests with 1 deterministic under SGLang about 415 tok/s (−56%); LLM-42 911 tok/s (2.2x, within 3% of non-deterministic).
- Offline (4096 requests per configuration): SGLang-deterministic penalty 24% (in=2048, out=512) to 36% (ShareGPT). LLM-42 at 100% deterministic beats SGLang-deterministic in all but ShareGPT, where it is 6% slower. On ArXiv LLM-42 is within 8%/2%/1%/1% of non-deterministic at 5/10/20/50% deterministic traffic, and up to 41% faster than SGLang-deterministic.
- Rollbacks and recompute (8 × 64 grouping, 100% deterministic): ArXiv 3351 rollbacks, 89248 tokens (10.97%); ShareGPT 96 rollbacks, 0.32%.
- Online, ShareGPT, 12 QPS: SGLang-deterministic P50/P99 4.64/28 s vs non-deterministic 2.15/13.2 s; LLM-42 at 2% deterministic P50 2.21 s. 18 QPS: P90 TTFT 101.2 ms (LLM-42 at 100%) vs 171.6 ms (SGLang-deterministic).
- Ablation (online, 12 QPS, all deterministic): without grouping, P99 615 s at window 16, 56.18 s at 128, 99.94 s at 512; recompute 3.44% at 16 vs 42.33% at 512. The best grouped configurations verify 256 tokens per step and reach P99 34-35 s.
- First-divergence observation (350 ShareGPT requests, 512 tokens, batch-1 reference vs dynamic batching at 6 QPS): the first consistent span is often hundreds of tokens, and the second consistent span is near zero for most requests.

## 4. Performance-principles table

| Principle | MI210 gfx90a | Zen 5 EPYC |
|---|---|---|
| P1. Position-invariant, shape-consistent kernels are enough for run-to-run determinism; batch invariance is not needed | PARTIAL. Not true today: the Q8_MF V5 atomic tail, the q8_skinny `unsafeAtomicAdd` and rocBLAS default atomics are order-nondeterministic (design doc §1a, §5). With `GGML_DETERMINISTIC` (`bef2e4c7d`, fork only) A/A is 0/16, but at 2.415x. Once atomics are fixed-order, a fixed split-K count per shape is position-invariant, which is exactly what LLM-42 needs. | YES. Work-stealing assigns whole output chunks, so per-element sums do not depend on thread (design doc §1b, `ggml-cpu.c:620/754`). CPU run-to-run noise comes from KV-cell layout history, not kernels. |
| P2. Batch-invariant kernels are expensive because they forgo split-K and shape-aware tiling (63% GEMM) | YES as a warning. Our knob is not batch invariance: it keeps per-shape dispatch and only fixes the reduction order. The 2.415x comes from the ticket-chain serialisation (design doc §5), not from forgoing split-K. The LLM-42 number therefore does not predict our cost. It argues for GGML-DETERMINISTIC-REDUCE-SCRATCH (per-WG scratch plus fixed-order fixup keeps split-K), whose ≤1.1x target is consistent with LLM-42's view. | NO direct transfer: ggml-cpu has no split-K atomics. ROWEXACT costs 6% on MTP n-max 4 (`ggml-cpu.c:1714-1718 @ a6a32c1`), a different property (width-1 equality). |
| P3. The reference pass must own the cache it leaves behind (overwrite decode-written KV with the verifier's) | YES. This is the design statement of intake-2830's P2 (a stale width-1 fallback over wide-written KV is not exact) and of INF-70 E2a (redecode fails at verified rows). On HIP it applies to both KV and GDN recurrent state written by the batched verify. | YES, same. In-house `LLAMA_SPEC_EXACT=redecode` re-decodes one token but keeps the verify-written KV (`server-context.cpp:50-51 @ a6a32c1`), which is why it is not exact. |
| P4. Verify window trade-off: memory-bound small windows (0.75 ms/token) vs recompute with large windows (46% at 256); grouped verification across requests | PARTIAL. The shape of the trade-off transfers (verify slope ≥ ~1 ms/row on 27B, per intake-2830's dive). The numbers are H100/8B and do not. | PARTIAL, same reasoning. CPU decode is bandwidth-bound, so a fixed window of W rows costs close to one pass for small W (uncited). |
| P5. Selective, per-request determinism flag (`is_deterministic`) | NO value for us. Our only determinism consumers are identity gates on dedicated scratch servers (design doc §3.1: fresh server per identity request). Serving samples at T > 0. A process-global env knob is enough. | NO, same. |

## 5. In-house state

- `GGML_DETERMINISTIC`: **absent from C19 `a6a32c1`** (`git grep` returns zero hits in ggml/src, src, common and tools/server). It exists on fork `llama.cpp-experimental-determ-20261122` @ `bef2e4c7d` (V5 ticket reduction, q8_skinny disabled under the knob, rocBLAS no-atomics). Measured A/A ON 0/16 vs OFF 7/16 at 2.415x ms/round (design doc §5a, L159-168 @ d785b6d).
- Open box: GGML-DETERMINISTIC-REDUCE-SCRATCH (`handoffs/active/autokernel-loop.md:4956 @ d785b6d`), target ≤1.1x OFF while keeping ON A/A 0/16.
- `GGML_ROWEXACT_N` (CPU, opt-in, default 0) gives width-1 equality, which is stronger than LLM-42's determinism (`ggml/src/ggml-cpu/ggml-cpu.c:1708-1727 @ a6a32c1`).
- `LLAMA_SPEC_EXACT` modes (`tools/server/server-context.cpp:42-77 @ a6a32c1`). serial is the only exact one. redecode inherits verify-written KV.
- The design doc already states that determinism makes A/A exact but not A/B (L82-84). LLM-42's own limitation (claim 5) agrees.
- Upstream LLM-42 code (SGLang-based) is not present and has no llama.cpp analogue. Nothing on the served path reaches it.

## 6. Derived-actionables ledger

- **L1 (refines GGML-DETERMINISTIC-REDUCE-SCRATCH, autokernel-loop.md:4956; code + unit test).** Task: add a position-invariance unit test to that box's done-when. Under `GGML_DETERMINISTIC=1` on ROCm0, for Q8_0 matmul at fixed M ∈ {2, 4, 8, 16} and the 27B dims, permute the input rows and require each row's output to be bitwise identical at every batch position. Also assert that the split count chosen by the V5 and scratch paths depends only on (M, N, K), not on occupancy or CU availability. Owner: autokernel-loop.md (exists, not frozen; AK owns it). Compute: a test-backend-ops-scale run, seconds on the MI210, no row. Decision: it answers whether the deterministic Q8 path is shape-consistent (LLM-42 O2). Fixed-shape A/A gates, and any future fixed-width replay oracle, depend on that. A failure means the knob is deterministic per launch but not per position, and the A/A 0/16 result could break under np>1.
- **L2 (refines intake-2830 A1 and kernel-champion-and-promotion.md:53 C18-REPLAY-Q4X-CONC-BISECT; analysis-only).** Task: in identity rows that compare arms under concurrent np4 serving, report first-divergence events per token-at-risk (verified tokens emitted before the first divergence, summed over requests) next to per-request mismatch counts. The ON-vs-OFF2 excess (r7: ON 31 vs OFF2 23) should be tested as a rate ratio with a Poisson or Wilson interval. Reason: one flip makes the rest of a request diverge (LLM-42 Fig. 6, second consistent span near zero), so per-request counts saturate and lose power. Owner: kernel-champion-and-promotion.md (autokernel). Compute: none; re-analysis of r6/r7 `results.jsonl` plus the bisect row's output. Decision: whether the r7 excess is significant once exposure is controlled. If not, it is a TIE_FLIPS prior before the bisect runs.
- **L3 (refines intake-2830 A4; folded into A4, no new row).** A4's redecode-vs-serial GPU arm separates query-shape noise from state noise. LLM-42 P3 predicts redecode will fail because it reuses verify-written KV and GDN state. Record that prediction as A4's pre-registered hypothesis: redecode divergence ≈ plain verify divergence means cache/state noise dominates. Owner: speculative-decoding.md (DF2-13 track). Compute: inside A4.
- **Decline: build LLM-42's DVR (fast-path decode plus fixed-shape replay verifier) in llama-server.** Entry-specific reasons. (1) LLM-42 is not integrated with speculative decoding (claim 5), and our production is always speculative. Composing DVR with a draft-verify loop adds a second verify per window on top of the k+1-row verify. (2) Our determinism consumers are identity gates that already run one request per fresh server (design doc §3.1), so the dynamic-batching nondeterminism DVR targets does not occur in gates. (3) On the MI210, DVR's premise (O2) fails until the atomics are fixed-order, which is the `GGML_DETERMINISTIC` work itself. Once that lands, fixed-shape gates get determinism without DVR.
- **Decline: per-request determinism flag.** No serving consumer (P5).

## 7. Dive-surfaced sources

- **github.com/microsoft/llm-42** (code, SOSP 2026 artifact; not in the index). Decline as a separate entry. It is this paper's implementation (SGLang/CUDA), and no ledger row needs its code.
- **Thinking Machines, "Defeating nondeterminism in LLM inference"** (the origin of batch-invariant kernels; not in the index by URL). Decline. LLM-42 already quantifies its cost, and our knob is not batch invariance, so it would not change L1-L3.
- **SGLang deterministic-inference blog (lmsys 2025-09-22)** (not in the index). Decline. It is the baseline LLM-42 measures; there is no llama.cpp/HIP delta.
- **arXiv 2601.07239** ("Stochastic chaos", argues against determinism; not in the index). Decline. It is a position paper with no measurement bearing on gates.

## 8. Contradiction / adversarial pass

- **The atomics premise** (claim 3) is false for our GPU kernels. The paper's own footnote concedes that the guarantee does not hold under atomic reductions.
- **"56% end-to-end" is a microscenario** (claim 1). The broader offline penalty is 24-36%. LLM-42 itself has higher latency than SGLang-deterministic at low QPS with 100% deterministic traffic, which the authors attribute to a global verification pause and unbatched prefill.
- **Online recompute is much higher than offline** (typically more than 6% vs below 2%), correlated with batch-size variability, per the authors.
- **Single model reported for performance** (Llama-3.1-8B). Correctness only is claimed for Qwen3 4B/14B/30B-A3B and 1-4 GPU TP.
- **Restatements**: arXiv 2510.22876 v4 cites LLM-42 (Gond et al. 2026) for "batch-dependent floating-point effects". That is a citation, not a replication.

## 9. read_depth

FULL for the v2 HTML body (§1-7 and the references read). Figures were not viewed as images; their in-text numbers were used. The repo README was read; repo code was not. lane_head: d785b6d9792e18b29dad1929a15fdc2b971d3c0e

## 10. Artifact audit

artifact audit: clean. page.txt (70821 bytes, sha256 ba4dfbab4114…) is retained (artifact=yes, arXiv v2). All 19 quotes used are verified substrings. The repo README was saved to `llm42/repo/README.md` as reading material only.

**Bearing on intake-2830 / quotability:** LLM-42 anchors no Vega-Fafnir number. It anchors the cost of batch invariance (63% GEMM, 24-36% offline, the 56% microscenario), the KV-overwrite design rule that intake-2830's stale-cache result implies, and the qualitative "rare first flip, then full divergence" observation. It cannot anchor the 60%/68% rates.
