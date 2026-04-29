# Multiscreen Attention — Evaluation for EPYC Inference

**Status**: active (literature survey complete 2026-04-14, priority ranking established)
**Created**: 2026-04-04 (via research intake)
**Updated**: 2026-04-21 (monitoring confirmed — no new pretrained checkpoints; priority ranking unchanged from 2026-04-14 survey)
**Categories**: kv_cache, inference_serving, ssm_hybrid
**Scope note**: This handoff expanded beyond Multiscreen evaluation into a comprehensive sub-quadratic attention mechanism survey. Multiscreen-specific evaluation is Section 1. Log-Linear GDN readiness tracked in [log-linear-gated-deltanet-readiness.md](log-linear-gated-deltanet-readiness.md).

## Status as of 2026-04-21

Backburner survey — awaiting pretrained weight releases for the prioritized architectures (Diff Attn V2, MoBA, Multiscreen). No upstream movement detected since 2026-04-14 survey. Section 1 (Multiscreen evaluation) remains gated on Section 2 priority items shipping weights first.

## Objective

Evaluate the Multiscreen architecture (arXiv:2604.01178) as a potential next-generation attention mechanism for EPYC inference. Multiscreen replaces softmax attention with absolute query-key screening, achieving 40% parameter savings and 2.3-3.2x latency reduction at 100K contexts.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-256 | Screening Is Enough — Multiscreen Architecture | high | new_opportunity |
| intake-464 | FlashAttention-3 (arXiv:2407.08608) | medium | worth_investigating — canonical Hopper attention paper (added 2026-04-26). DGX Spark prep + CPU producer/consumer thread-split analog candidate. |

## Key Claims to Verify

- 40% parameter savings at comparable validation loss
- 2.3-3.2x inference latency reduction at 100K context
- Near-perfect retrieval at context lengths far beyond training
- Stable training at learning rates where Transformers diverge

## Relevance to EPYC

1. **vs Delta Net**: Our Qwen3.5 hybrid models use Delta Net (gated linear attention). Multiscreen preserves the attention paradigm but makes it sub-quadratic — potentially compatible with existing KV cache and speculation infrastructure (unlike Delta Net which broke all tree speculation)
2. **Parameter efficiency**: 40% fewer parameters for same quality would shift model selection calculus — smaller models could replace larger ones
3. **Long context**: Our models degrade at long context; Multiscreen claims stable performance beyond training length
4. **llama.cpp compatibility**: Key blocker — no GGUF support exists. Would require implementing screening mechanism in ggml

## Open Questions

- Will any major model provider (Google, Meta, Qwen) adopt Multiscreen architecture?
- Can screening be implemented efficiently in ggml/llama.cpp?
- Is the 2.3-3.2x speedup achievable on CPU (EPYC) or only GPU?
- How does Multiscreen interact with KV cache quantization (Hadamard)?
- Does screening mechanism support speculative decoding?

## Blockers

- No pretrained Multiscreen models available for download
- No GGUF/llama.cpp implementation exists
- Paper is very new (April 2026) — needs community validation

## Notes

This is a WATCH item, not an implementation item. Monitor for:
1. Community reproduction of results
2. Model releases using Multiscreen architecture
3. llama.cpp PRs implementing screening mechanism

## Expanded Attention Mechanism Cluster (2026-04-12 research intake)

Three additional cross-head attention mechanisms identified during deep-dive. Together with Multiscreen, these form a 2025-2026 cluster of alternatives to standard MHA. All require pretraining — no retrofit possible.

| Mechanism | Intake | FlashAttention | Key Benefit | EPYC Notes |
|-----------|--------|----------------|-------------|------------|
| **IHA** (Interleaved Head Attention) | intake-333 | YES (mixes before attention) | +112% RULER at 16K multi-key retrieval. MHA ⊂ IHA strictly. | **Priority watch** — FlashAttention-compat is key for our llama.cpp stack |
| **MEA** (Explicit Multi-head Attention) | intake-342 | YES (HLC on K/V) | 50% KV cache reduction via virtual heads. GroupNorm critical. | KV compression directly useful for memory-constrained inference |
| **KHA** (Knocking-Heads Attention) | intake-343 | YES (absorbed at inference) | **Zero inference overhead** (linear variant absorbed into projections). V-only interaction. | Prefer KHA-trained models when available — zero cost at inference |

**Ranking for EPYC**: IHA (most expressive, FlashAttention-compat) > MEA (KV compression bonus) > KHA (zero inference cost, but lower expressivity) > Multiscreen (most radical, no implementations)

**Monitor for**: GGUF implementations of models trained with any of these mechanisms. None currently available.

---

## Literature Survey: Sub-Quadratic Attention for CPU Inference (2025-2026)

Compiled 2026-04-14. Target: AMD EPYC 9655 (192 threads), all-CPU inference via llama.cpp.

### 1. Mechanisms Requiring Pretraining (Architecture Changes)

**Native Sparse Attention (NSA)** — DeepSeek, Feb 2025 (arXiv:2502.11089)
ACL 2025 Best Paper. Three parallel branches: compressed attention (coarse), selected attention (fine-grained), sliding window (local). Sub-quadratic scaling; substantial speedups on 64K sequences. Foundation for DeepSeek V3.2's DSA. vLLM/SGLang have GPU kernel support (SM90+ only). No llama.cpp support; GPU-centric design (block-sparse CUDA kernels).
- CPU applicability: **low** (hardware-aligned to GPU tensor cores)
- llama.cpp compat: **unlikely** without major porting
- Verdict: **monitor_only** — wait for CPU-friendly reformulation

**MoBA (Mixture of Block Attention)** — MoonshotAI, Feb 2025 (arXiv:2502.13189)
Applies MoE routing to attention blocks. Queries dynamically select relevant KV blocks. 6.5x prefill speedup at 1M tokens, 16x at 10M. Llama-8B-1M-MoBA model exists (128K-1M context). Deployed in Kimi production. FlashMoBA kernel achieves 14.7x over FA2 for small blocks. Open source: github.com/MoonshotAI/MoBA.
- CPU applicability: **medium** (block-sparse structure amenable to CPU, but kernels are CUDA)
- llama.cpp compat: **possible** — standard transformer weights, block selection could be implemented in ggml
- Verdict: **worth_investigating** — Llama-8B-1M-MoBA model could be converted to GGUF for testing

**Differential Transformer V2** — Microsoft, 2026 (HuggingFace blog)
Computes attention as difference of two softmax maps, canceling noise. V2 matches baseline decoding speed, uses standard FlashAttention (no custom kernels). 0.02-0.03 lower loss at 1T tokens. Needs ~65% of baseline params/tokens for equivalent quality.
- CPU applicability: **high** (standard attention ops, just doubled query heads with subtraction)
- llama.cpp compat: **possible** — requires new head-pairing logic in ggml, but ops are standard
- Verdict: **worth_investigating** — FlashAttention compatibility makes ggml port feasible

**Multiscreen** — Apr 2026 (arXiv:2604.01178)
Replaces softmax with absolute query-key screening. 40% param savings, 2.3-3.2x latency reduction at 100K. Very new (2 weeks old); no reproductions, no community benchmarks, no implementations outside the paper. No models available.
- CPU applicability: **unknown** (screening op simplicity suggests potential, but unverified)
- llama.cpp compat: **unlikely** near-term — requires novel ggml op
- Verdict: **monitor_only** — too early, no artifacts to test

### 2. Training-Free / Retrofit Methods (Apply to Existing Models)

**CSAttention (Centroid-Scoring)** — Apr 2026 (arXiv:2604.08584)
Training-free sparse attention for reusable contexts. Pre-computes centroid scores offline, applies sparse selection at decode time. 4.6x speedup at 128K context over best accurate baseline. GPU-optimized score accumulation.
- CPU applicability: **low** (GPU-friendly design, prefill/decode split less relevant for CPU)
- llama.cpp compat: **possible** but niche — most useful for batched GPU serving
- Verdict: **monitor_only**

**HiP Attention** — 2024 (arXiv:2406.09827)
Hierarchical pruning of attention scores, sub-quadratic. Older but more mature. Applicable as drop-in during inference.
- CPU applicability: **medium** (pruning reduces compute, but overhead of hierarchy unclear on CPU)
- llama.cpp compat: **possible**
- Verdict: **monitor_only**

### 3. llama.cpp Attention Support Status (as of Apr 2026)

| Feature | Status |
|---------|--------|
| GQA (Grouped Query Attention) | **Supported** — default for Llama 3, Mistral, Qwen |
| MQA (Multi-Query Attention) | **Supported** |
| Flash Attention (CPU) | **Limited** — no improvement for text gen (memory-bound); helps prefill. Head size 64/128 only |
| Sliding Window Attention | **Partial** — basic SWA works; interleaved SWA (Gemma 2/3) is open issue #12637 |
| MLA (Multi-head Latent Attention) | **Supported** — for DeepSeek V2/V3 models |
| NSA / MoBA / Diff Attention | **Not supported** — no PRs found |
| Multiscreen | **Not supported** — no implementations anywhere |

### 4. KV Cache Compatibility Assessment

| Mechanism | KV quant (q4/q8 + Hadamard) | Speculative decoding | KV eviction |
|-----------|----------------------------|---------------------|-------------|
| NSA | Incompatible (custom KV layout) | Unknown | Built-in (sparse selection) |
| MoBA | Compatible (standard KV, sparse routing) | Likely compatible | Compatible (block-level eviction natural) |
| Diff Attn V2 | Compatible (standard KV) | Compatible (standard decode loop) | Compatible |
| Multiscreen | Unknown (novel KV access pattern) | Unknown | Unknown |
| CSAttention | Compatible (standard KV) | Incompatible (offline prefill assumption) | N/A (own sparsity) |

### 5. Priority Ranking for EPYC CPU Inference (REVISED 2026-04-29 PM)

1. **DSA (DeepSeek V3.2 + GLM-5.1)** — **TOP PRIORITY (active)**. PR #21149 by fairydreaming is an active draft with CPU/CUDA/Vulkan backends working. Tracked in [`llama-cpp-dsa-contribution.md`](llama-cpp-dsa-contribution.md) with three contribution sub-tracks (D1 smoke test, D2 prompt-processing follow-on PR, D3 AVX-512BW indexer). 2-models-for-1 leverage.
2. **Lightning Attention (Ant Group Ring-mini/flash-linear-2.0)** — **ACTIVE PORT**. Tracked in [`lightning-attention-port.md`](lightning-attention-port.md). 3-5 day v1 effort using existing `GGML_OP_GATED_LINEAR_ATTN`. Ring-mini 957M-active opens drafter territory.
3. **Diff Attn V2** — Highest priority among "awaiting pretrained" mechanisms. Standard ops, FlashAttention-compatible, no custom kernels. When pretrained models ship, GGUF conversion should work with minor ggml additions. KV cache and speculation compatible.
4. **MiMo-V2-Flash** — Already supported in upstream llama.cpp (PR #18328 merged Dec 2025). Sizing-blocked (309B/15B-active estimates ~10 t/s on EPYC, below deployment threshold), but MTP-as-drafter pattern is independently transferable. Track PR #22493 (V2.5) — if it ships smaller, becomes immediately deployable.
5. **MoBA** — Llama-8B-1M-MoBA exists now. Block-sparse structure could be implemented in ggml. Standard KV layout preserved. Test GGUF conversion of existing model.
6. **IHA/MEA/KHA** (from existing stub) — FlashAttention-compatible variants that preserve standard inference stack.
7. **Summary-Token cluster (KSA + GSA)** — Readiness tracker only. [`summary-token-attention-readiness.md`](summary-token-attention-readiness.md). All require CPT; gated on checkpoint release or GPU acquisition.
8. **NSA** — Monitor only for CPU. GPU-aligned design; wait for CPU-friendly derivative.
9. **Multiscreen** — Monitor only. No artifacts, no reproductions, too early.

### Key Finding

No sub-quadratic attention mechanism has a llama.cpp implementation today, but **we have full fork control** (`production-consolidated-v3`) and can implement custom ggml ops.

### Custom ggml Implementation Feasibility

| | Diff Attn V2 | MoBA | Multiscreen |
|---|---|---|---|
| **Spec clarity** | Yes (full pseudocode) | Yes (open-source code) | Partial (no ref impl) |
| **New ggml ops** | 0 (all ops exist) | 2 (top-k, online softmax merge) | 2-3 (TanhNorm, trim-square, cos mask) |
| **Patch size** | ~200-400 LOC | ~500-800 LOC | ~800-1200 LOC |
| **Models available** | No (Microsoft pending) | No (requires cont. training from Llama) | No |
| **Risk** | Low | Medium | High |

**Diff Attn V2 implementation path** (priority #1):
- Q projected to 2h heads (doubled), K/V remain standard
- After standard FlashAttention: split outputs into even/odd pairs per GQA group
- `out = attn1 - sigmoid(lambda) * attn2` where lambda is a small W_lambda projection (d_model → h)
- Changes: GGUF converter (new W_lambda tensor), model loader, attention forward pass
- All ops already exist in ggml (matmul, softmax, sigmoid, subtract, multiply, strided view)
- **Can build now, test when models ship**

**MoBA implementation path** (priority #2):
- Router scores blocks by `dot(q, mean(K_block))`, selects top-k + causal block
- Full attention on selected blocks, results combine via online softmax
- Needs two new primitives: top-k selection, online softmax merge
- Performance gains demonstrated at 1M+ tokens — unclear benefit at our 8K-32K range

**Multiscreen** — monitor only. No reference implementation, partial spec, high risk.

## Research Intake Update — 2026-04-14

### New Related Research
- **[intake-354] "Memory Caching: RNNs with Growing Memory"** (arxiv:2602.24281)
  - Relevance: Bridges fixed-memory RNNs (O(L)) and quadratic Transformers (O(L²)) via cached state checkpoints. Maps the growing-memory RNN design space (O(L) fixed → O(NL) segmented → O(L²) full attention)
  - Key technique: Gated Residual Memory (GRM) — input-dependent gating over cached segment checkpoints. Also: Sparse Selective Caching (MoE-style top-k checkpoint retrieval)
  - Reported results: +12.8pp S-NIAH-2 on Titans at 16K; +20pp SWDE/FDA retrieval; 0.9 ppl improvement at 760M scale
  - Delta from current approach: Training-time modification only. **Deep dive correction**: state copy is ~5% of speculation round-trip cost (50-100ms); the real bottleneck is 220ms/token sequential verification through 30 Delta Net layers. MC's segmented caching would save ~25-50ms against ~1320ms verification for 6 tokens — marginal. Value is architectural context, not a practical optimization path for current models.

- **[intake-356] "Log-Linear Attention"** (arxiv:2506.04761) — **HIGH RELEVANCE**
  - Relevance: **ICLR 2026** paper applying log-linear complexity directly to Gated DeltaNet (75% of our production stack). Authored by Songlin Yang (DeltaNet creator) + Tri Dao (FlashAttention creator) + Yoon Kim
  - Key technique: Replaces fixed-size hidden state with logarithmically growing set of hidden states; O(L log L) complexity; <0.4% parameter overhead
  - Reported results: Log-Linear Gated DeltaNet outperforms standard Gated DeltaNet in perplexity and reasoning benchmarks; outperforms layer-matched Transformer across all metrics
  - EPYC inference impact: (1) State size 4-10x reduction (~2GB → ~200-500MB) enables sequential replay approach for speculation; (2) O(log L) growth makes 1M+ context feasible on same hardware; (3) matmul-rich form maps to existing ggml infrastructure — no GPU-centric sparse kernels needed
  - Reference implementation: github.com/HanGuo97/log-linear-attention (278 stars, Python/Triton, training-only)
  - llama.cpp effort: ~2-3 weeks (new model variant class, new ggml ops, GGUF metadata). Blocked on pretrained model availability.

### Updated Priority Ranking (incorporating deep dive)

1. **Diff Attn V2** — Highest near-term priority. All ops exist in ggml, can build now. Standard attention models.
2. **Log-Linear Gated DeltaNet** — Highest strategic priority for EPYC specifically. Directly upgrades 75% of our production stack's architecture. CPU-friendly (matmul-rich, no sparse kernels). Blocked on pretrained models. Tracked in: [log-linear-gated-deltanet-readiness.md](log-linear-gated-deltanet-readiness.md).
3. **MoBA** — Existing model available for GGUF testing. Benefit unclear at our 8K-32K context range.
4. **IHA/MEA/KHA** — FlashAttention-compatible, standard inference stack preserved.
5. **NSA** — GPU-only. Monitor.
6. **Multiscreen** — Too early. Monitor.

## Research Intake Update — 2026-04-28

### New Related Research

- **[intake-488] "Speculative Decoding with Mamba (companion to 'The Mamba in the Llama')"** (github.com/itsdaniele/speculative_mamba; arxiv:2408.15237)
  - Relevance: Pure-Mamba target + Mamba draft spec-dec (mamba-2.8b target, mamba-130m draft). Closest existing reference for SSM-on-SSM speculation, but our hybrid SSM targets (Qwen3.5, Qwen3-Next) use Delta-Net not Mamba2.
  - Key technique: K-step lookahead drafting with frozen recurrent state; CUDA-graph-on-draft to amortize launch overhead.
  - Reported results: ~68% acceptance on a single English-prose example with K=3, fp16 (anecdotal, not benchmarked).
  - Delta from current approach: CUDA-only, pure-Mamba (not Delta-Net hybrid) — no kernel ports to llama.cpp CPU. Verdict: not_applicable for current EPYC hardware.

- **[intake-489] "SpecMamba: Accelerating Mamba Inference on FPGA with Speculative Decoding"** (arxiv:2509.19873)
  - Relevance: First FPGA accelerator co-designing Mamba SSM with spec-dec; algorithmic core (memory-aware hybrid backtracking for SSM hidden-state rollback) addresses the central pain point that has blocked spec-dec on hybrid SSMs in our stack.
  - Key technique: Memory-aware hybrid backtracking + FIFO-based tree verification with tiling + parallel-linear/serial-SSM dataflow.
  - Reported results: 2.27× over GPU baseline, 2.85× over prior FPGA Mamba (LightMamba), 5.41× higher energy efficiency vs GPU on AMD Versal VHK158/VCK190.
  - Delta from current approach: FPGA hardware-bound; no CPU port path. Filed for awareness — confirms SSM-rollback is the right algorithmic frame for if/when hybrid-SSM spec-dec is reopened.

- **[intake-490] "Hybrid Models Meet SGLang: More than Full Attention"** (pytorch.org blog, Dec 2025)
  - Relevance: Engineering recipe for serving hybrid SSM+attention models with prefix caching + spec-dec. Multiscreen-class architectures with linear-attention layers face the same KV-pool-vs-state-pool sizing problem that this blog catalogs. Verdict: **adopt_patterns**.
  - Key technique: HybridReqToTokenPool, HybridLinearKVPool (skip KV alloc for linear layers), MambaRadixCache (hybrid prefix-tree), Elastic Memory Pool via CUDA VMM, EAGLE/MTP rollback over SSM state.
  - Reported results: 324.57 tok/s with 4.231 avg acceptance length on Qwen3-Next-80B-A3B-FP8 (H200, bs=1, MTP-4 + topk=4 + draft_tokens=8).
  - Delta from current approach: Pure CUDA-/H200-targeted; kernels do not port to llama.cpp CPU. Architectural lessons (per-layer skip-KV remap, elastic Mamba/KV pool, in-place-state rollback workaround) are directly applicable when scoping llama.cpp-side support for hybrid SSM serving.
  - Caveats (Tier 2b): per-request memcpy cost for in-place state snapshots not benchmarked; agentic-workload cache pressure (sgl-project/sglang #20144) — Mamba states can be 1000× larger than KV states and trigger evictions; multi-tenant numbers under contention not published.

- **[intake-491] "Mamba Drafters for Speculative Decoding"** (arxiv:2506.01206; Findings of EMNLP 2025)
  - Relevance: External Mamba drafter for Transformer target — constant-memory drafter that beats Pythia drafters of equal/larger size at long context. Worth investigating whether the principle generalizes to hybrid-SSM targets in our stack.
  - Key technique: Mamba-130M external drafter + MAB-optimized tree-shape selector for test-time tree-search drafting.
  - Reported results: GSM-8K 149.46 tok/s (vs Pythia-410M 119.67); MT-Bench accept length 3.91 (vs EAGLE 3.85); LongBench 8k accept length 2.80 with throughput preserved while Transformer drafters degrade.
  - Delta from current approach: SSM-drafter-for-Transformer-target principle is novel for our stack; MAB tree-shape selector is immediately applicable to existing tree spec-dec infra without the SSM piece. Caveats: Mamba hidden-state backtracking limitation; tree verification requires workarounds; hyperparameter-sensitive.

## Research Intake Update — 2026-04-29

### New Related Research

- **[intake-502] "Kwai Summary Attention Technical Report"** (arxiv:2604.24432, Kuaishou OneRec team, submitted 2026-04-27 — full extraction via local LightOnOCR pipeline 2026-04-29) → **READINESS TRACKER**: [`summary-token-attention-readiness.md`](summary-token-attention-readiness.md) (joint with intake-507 GSA)
  - Relevance: Architectural sub-quadratic attention in the Section-1 cluster (NSA / MoBA / Diff Attn V2 / Multiscreen / Log-Linear GDN). "Intermediate path" between Full attention (linear KV, quadratic compute) and minimal-KV linear-attention (constant state): maintains linear KV growth but compresses historical context into learnable summary tokens at chunk size k=8. Complexity O(n/k).
  - Key technique: Summary tokens injected at chunk boundaries; summary tokens see only their own chunk; text tokens see local **Sliding Chunk Attention** (SCA — chunk-aligned, distinct from token-level SWA) plus distant summary tokens. Hybrid-KSA = 3:1 KSA-to-Full layer ratio. Decode KV cache uses contiguous-tensor layout (Current Chunk + Sliding Chunk Text + Summary Token Buffer) avoiding gather/concat in hot path.
  - **Open-source training scripts released**: [github.com/Kuaishou-OneRec/KSA](https://github.com/Kuaishou-OneRec/KSA). No model checkpoints yet.
  - Reported results (CPT setting, init from Qwen3-4B-base, 85B tokens):
    - RULER-4K **92.97**, RULER-32K **86.65**, RULER-128K **71.67** — Hybrid-KSA wins all lengths
    - RULER-128K: Hybrid-KSA beats Full by **+5.81**, beats Hybrid-SWA by **+5.40**
    - MMLU 70.73 / CMMLU 73.29 (vs Full 71.83 / 75.00; Hybrid-Linear collapses to 64.33 / 68.41)
    - MBPP 62.20 — best across all configs **including Full**
    - NIAH-128K: Multivalue **98.75 vs Full 88.12 (+10.63)**, VT **90.50 vs 60.50 (+30.00)**, FWE **65.84 vs 51.66 (+14.18)**, SQuAD **42.50 vs 30.00 (+12.50)**
  - Reported results (from-scratch, 1.9B params, 400B tokens at 8K→32K→64K→128K):
    - RULER-128K: Hybrid-KSA **65.35 vs Full 48.75 (+16.60)**, vs Hybrid-GDN 59.87 (+5.48), vs Hybrid-SWA 56.64 (+8.71)
    - GSM8K **59.14 vs Full 48.29 (+10.85)**, MATH **36.92 vs Full 23.38 (+13.54)**
    - HumanEval **31.71** (best), MBPP **36.40** (best); average across all benchmarks: Hybrid-KSA **54.80 vs Full 49.44**
    - End-of-training loss: Hybrid-KSA **1.524** < Hybrid-GDN 1.534 < Hybrid-SWA 1.550 < Full 1.572
  - Inference efficiency (Figure 10): KV cache at 128K **7.5 GB vs Full 18.6 GB (2.5× smaller)**. Decode throughput at 16K: **1.06× Full** (Hybrid-SWA 0.73×, Hybrid-Ring-Linear 0.81× — KSA is the only sub-quadratic baseline that does NOT lose decode speed).
  - Per-token KV cache cost (Table 1, h=128 d=128 g=8 d_c=512 d_r=64): KSA at k=8 → **12.5%** of MHA size (8× compression); **KSA + GQA → 0.78%** (~128× compression); **KSA + MLA → 0.22%** (~455× compression). Composability with GQA / MLA is fully orthogonal.
  - Ablations (Table 7): default N=128 chunks, S=8 chunk size, KSA:Full=3:1 ratio. N>128 yields diminishing returns at long context (RULER-64K drops to 65.73 at N=256 vs 76.35 at N=128). S=32 best for general reasoning, S=8 best for long-context.
  - **Three-stage CPT recipe** (genuinely actionable, even decoupled from KSA): (1) summary token adaptation with layer-wise MSE + distribution-wise KL distillation from full-attention teacher; (2) parameter annealing via λ-schedule that interpolates independent summary weights into shared LLM weights, then drops them; (3) staged sequence-length extension (32K→64K→128K). Read for ideas if/when we run our own continual-pretraining work.
  - Delta from current approach: Same architectural blocker class as Multiscreen/MoBA/NSA — needs pretraining or full CPT. CPT is feasible with released scripts BUT compute-bound (no CPU path; ~85B tokens). On EPYC today: monitor only. Distinct from our deployed retrofit methods (AM compaction, Expected Attention) which work on pretrained transformers without architecture change. Closest training-time cousin: **Log-Linear GDN** (intake-356, sub-linear state growth) — both are "intermediate path" architectures with matmul-rich CPU-friendly forms.
  - Tier 2b caveats: (1) authors' own ablations show N=256 hurts long-context — chunk count is workload-dependent; (2) Hybrid-Linear baseline collapse on MMLU confirms general criticism that fixed-size linear state loses general capability — KSA mitigates this with growing summary state but is still in the same lineage; (3) no head-to-head comparison vs MoBA / NSA / Diff Attn V2 / Log-Linear GDN — only vs Hybrid-GDN (standard, not log-linear); (4) generalization to LongBench-v2 / non-RULER tasks not reported; (5) numbers entirely self-claimed, no third-party reproduction (paper is 2 days old).
  - Verdict: **monitor_only** (worth_investigating). Slot below Multiscreen in priority for *EPYC actionability* but **above** Multiscreen for *training-recipe value* (CPT distillation pattern is reusable). No new handoff stub — fits this section. Activation gates: (a) Kuaishou releases pretrained checkpoint, OR (b) llama.cpp port emerges, OR (c) GPU acquisition unlocks running their CPT recipe ourselves.
  - Adjacent paper surfaced during expansion (NOT yet ingested): **arxiv:2604.20920 "Forget, Then Recall: Learnable Compression and Selective Unfolding via Gist Sparse Attention"** — closest conceptual analog ("gist tokens" = "summary tokens" same paradigm, also April 2026). Recommend separate intake invocation if the cluster is to be expanded.

### Same-day expansion (2026-04-29) — 3 sibling papers ingested via Tier 1 reference-chasing from intake-502

- **[intake-503] "Every Attention Matters: An Efficient Hybrid Architecture for Long-Context Reasoning"** (arxiv:2510.19338, Ling Team / Ant Group, October 2025) → **ACTIVE PORT** tracked in [`lightning-attention-port.md`](lightning-attention-port.md) (created 2026-04-29 PM after audit revealed `GGML_OP_GATED_LINEAR_ATTN` already exists in our fork)
  - Relevance: **HIGH**. Hybrid Lightning-Attention + softmax architecture with empirically-tuned linear:softmax ratios (M=4 for 16B Ring-mini, M=7 for 104B Ring-flash). Direct competitor framing to KSA's hybrid-KSA. Open weights on HuggingFace + open-source FP8 LingHe kernels.
  - Key claim: ~1/10 inference cost vs 32B dense; AIME-25 86.51% / GPQA-D 74.49% (Ring-flash). Training efficiency +50% via FP8 LingHe.
  - Caveats: pure linear attention underperforms on recall-heavy tasks (authors acknowledge); BF16 KV-state precision drift requires FP32 accumulation in recurrent path — non-trivial in our quantized KV path; performance brittle to decay-coefficient choice; **NO RULER/NIAH/LongBench results published** — long-context claims rest on indirect reasoning benchmarks.
  - **Active-port verdict (CORRECTED 2026-04-29 PM)**: prior framing "no llama.cpp kernel today, defer adoption" was wrong — `GGML_OP_GATED_LINEAR_ATTN` already exists in our experimental fork (`ggml/src/ggml-cpu/ops.cpp:10605`); Lightning Attention is mechanically a constant-`g` GLA. v1 port is 3-5 days using existing infrastructure. Ring-mini 16B/957M-active is Q-scorer-territory; a working port unlocks a candidate small drafter for spec-dec experiments. Tracked at [`lightning-attention-port.md`](lightning-attention-port.md) with phases L1-L5.
  - Credibility: 4. Open-weight + open-kernel release at industrial scale.

- **[intake-505] "MiMo-V2-Flash Technical Report"** (arxiv:2601.02780, Xiaomi LLM-Core Team, January 2026)
  - Relevance: **MEDIUM**. 309B total / 15B active MoE with hybrid 5:1 SWA-to-Global ratio (128-token window) + learnable attention-sink bias. ~6× KV cache + attention compute reduction at matched quality across 32K-256K. **MTP head as spec-decoding drafter** is the most directly transferable finding (3.6 acceptance length, 2.6× speedup, mirrors DeepSeek-MTP).
  - Key claim: 73.4% SWE-Bench Verified, 71.7% Multilingual; NIAH-Multi 96.7% at 256K with 128-token SWA window.
  - Caveats: 309B too large for our stack at FP/BF16 (Q4 ~155 GB feasible only with heavy KV compression); 5:1 SWA + sink-bias scheme not in llama.cpp; community reports inconsistent instruction-following / unreliable tool-calling; 15B-active knowledge-capacity ceiling vs DeepSeek-V3.2/Kimi-K2; authors caveat "preliminary" architectural exploration; reward-hacking documented on SWE-Bench (Appendix B).
  - Verdict: **worth_investigating** — Tier-1 read for the attention/KV handoffs; MTP-as-drafter pattern reusable. Not adopt_component (model too large + custom attention not in llama.cpp), not new_opportunity (no novel mechanism we'd port wholesale).
  - Credibility: 3. Open-weight release + open repo (github.com/XiaomiMiMo/MiMo-V2-Flash).

- **[intake-506] "DeepSeek-V3.2: Pushing the Frontier of Open Large Language Models"** (arxiv:2512.02556, DeepSeek-AI, December 2025) — **CRITICAL CROSS-REFERENCE: KSA explicitly cites V3.2 as following "the same first-principle of sequence-level KV-cache compression"** → **ACTIVE TRACKER**: [`llama-cpp-dsa-contribution.md`](llama-cpp-dsa-contribution.md) (PR #21149 stabilization + 3 contribution sub-tracks)
  - Relevance: **MEDIUM** (capped by hardware blockers, not by intellectual relevance — this is one of the most important entries in the cluster).
  - Technique: **DeepSeek Sparse Attention (DSA)** — two-stage attention combining a Lightning Indexer (FP8, head-weighted scoring, block-64 quantized key cache) with fine-grained top-k=2048 token selection on top of MLA. Changes core attention cost from O(L²) to ~O(L·k). MLA + DSA composition (MLA-DSA) is orthogonal: MLA compresses per-token KV dim, DSA selects which tokens to attend.
  - Key claim: V3.2-Exp matches V3.1-Terminus on GSM8K/GPQA-Diamond (vLLM validation); V3.2-Speciale claims gold-medal at IMO 2025 + IOI 2025, comparable to GPT-5 / Gemini-3.0-Pro on reasoning.
  - Caveats: (1) llama.cpp DSA forward-pass kernel does NOT exist — indexer tensors load but C++ falls back to dense MLA, erasing speedup (same blocker as GLM-MoE-DSA, PR#19460 merged dense-only); (2) FP8 block-quantized key cache is CPU-unfriendly compute pattern; (3) RoPE-in-indexer implementation discrepancy reported in early versions; (4) V3.2-Exp slightly regresses on Humanity's Last Exam vs V3.1; (5) DSA top-k=2048 is fixed hyperparameter — generalization to short-context/non-retrieval workloads not characterized; (6) 671B-class MoE — Q4_K_M ~380 GB only feasible local quant.
  - Verdict: **worth_investigating** — high-leverage monitor target. Three reasons: (a) we already have V3.2 chat template upstreamed in our fork (llama-cpp-fork-rebase.md commit 1c0d9081f); (b) any DSA implementation effort simultaneously unlocks GLM-5/5.1; (c) cross-reference target for KSA + GLM-MoE-DSA work. Action: track llama.cpp DSA indexer PR as highest-leverage external event.
  - Credibility: **5** (highest in this expansion). Open-weight + DeepSeek track record + KSA cites + GLM-5 cites.

### Sibling not_applicable (recorded for completeness)

- **[intake-504] "LongCat-Flash-Thinking-2601"** (arxiv:2601.16725, Meituan, January 2026) — 560B MoE with ~27B active; Domain-parallel expert training + DORA RL framework + Heavy Thinking. **Not applicable** for EPYC: 560B too large for our 1.1 TB CPU even at 27B active; no quantization/kernel/serving contribution; Heavy Thinking and DORA are training-side techniques. Logged for completeness — no handoff updates from this entry.

### Late-day expansion (2026-04-29 PM) — Gist Sparse Attention (closest KSA sibling)

- **[intake-507] "Forget, Then Recall: Learnable Compression and Selective Unfolding via Gist Sparse Attention"** (arxiv:2604.20920, Mao / Li / Fox — Stanford, April 2026) → **READINESS TRACKER**: [`summary-token-attention-readiness.md`](summary-token-attention-readiness.md) (joint with intake-502 KSA)
  - Position: same April-2026 gist-token cluster as KSA (intake-502), but distinct mechanism. Where KSA keeps **all** summary tokens visible to text, GSA hard-selects **top-k chunks** and "unfolds" them to restore the raw KV pairs alongside the gists. Unselected chunks are entirely invisible — a sharper compression/fidelity trade-off.
  - Hierarchical variant **H-GSA** (gist-of-gist) achieves **log-linear decode complexity** — the only mechanism in this cluster that scales naturally to 1M+ context on EPYC's 1.1 TB RAM headroom.
  - Reported wins at high compression: LongBench at 32× → GSA 44.07 vs ActivationBeacon 38.30 (+5.77). RAG with KV-cache reuse on Llama3.2-1B at 8× → GSA 48.07 vs KVLink 41.20 (+6.87). 8× finetuned: GSA on some HotpotQA tasks **surpasses Full-FT** (selective unfolding as inductive bias filtering distractors).
  - Code released: github.com/yuzhenmao/gist-sparse-attention. Tested only on Qwen2-7B and Llama3.2-1B (no 30B+, no MoE, no RULER beyond passkey).
  - Caveats: Stage 1 CPT REQUIRED; no zero-shot retrofit; Selective Unfolding's hard top-k starves the model on queries needing many-chunks-weakly retrieval (KSA's persistent-summary fallback handles this softer); hardware-efficiency caveat — irregular memory access at decode erases theoretical FLOP savings on real GPUs and is even worse on CPU without KSA's contiguous-tensor decode layout.
  - **vs KSA mechanism summary**: KSA = persistent summaries, all visible, soft compression. GSA = hard top-k + selective unfolding, restores raw on selected, sharp trade-off. Different points in the same design space.
  - Verdict: **monitor_only** alongside KSA. Activation gates identical: (a) checkpoint released on a model we serve, OR (b) GPU compute path for CPT, OR (c) llama.cpp general support for dynamic top-k chunk masking + raw-KV restoration. No new handoff stub.
