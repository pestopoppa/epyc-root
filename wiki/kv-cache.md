# KV Cache Optimization

**Category**: `kv_cache`
**Confidence**: verified
**Last compiled**: 2026-04-13
**Sources**: 33 documents (3 deep-dives, 5 active handoffs, 2 completed handoffs, 23 intake entries)

## Summary

KV cache is the dominant memory bottleneck for CPU inference on our EPYC 9655 stack. At 256K context, Qwen2.5-Coder-32B's KV cache at f16 consumes approximately 64 GB -- more than the model weights themselves. Since CPU inference is memory-bandwidth-bound during decode, reducing KV cache size directly improves both capacity (more concurrent slots, longer contexts) and throughput (less memory traffic per token). At very long sequences (S >> d_model), attention rises above 50% of total per-token compute time, making KV cache compression a throughput lever, not just a memory lever. Our research has identified four orthogonal compression layers that operate on different dimensions of the KV cache problem, and we have validated or deployed work across all four.

The four layers form a compression stack. **Quantization** (how each KV entry is stored) reduces precision: Hadamard+q4_0 delivers 2-4x compression quality-neutral and is deployed in production since commit `b51c905`, now auto-enabled in v3 upstream. **Compaction** (constructing fewer but more informative KV entries in latent space) uses mathematical optimization: Attention Matching achieves 5x zero-degradation with native ggml NNLS+OLS solvers merged to `production-consolidated-v3` across 3 commits, validated on Qwen2.5-7B-f16, Coder-32B-Q4KM, and Qwen3.5-35B-SSM-hybrid. **Selection** (keeping only important tokens) uses importance scoring: Expected Attention achieves 94.7% RULER at 50% compression on Qwen3-8B and is Flash Attention compatible; TriAttention is the strongest decode-phase scorer with trigonometric Q/K concentration. **Block masking** (removing entire reasoning blocks) leverages model structure: Memento provides 2-3x peak KV reduction by training models to segment reasoning into blocks and retaining only summary KV states; the key finding is that KV states carry implicit information beyond summary text (15pp accuracy penalty when KV states are recomputed without original block context).

Each layer operates on a different dimension -- precision, count, and semantic structure -- making them composable. The theoretical combined ceiling is staggering: quantization 4x times compaction 5x times masking 3x equals 60x. Even the conservative two-layer stack (quantization 4x times compaction 2x) would transform the deployment landscape from "one 256K context slot barely fits" to "eight concurrent slots." The critical unknown is quality interaction under multi-layer compression: each layer claims minimal individual loss, but combined degradation may be multiplicative. Pairwise testing is in progress; three-way testing is a separate gate.

The field is evolving rapidly around closed-form approaches that replace heuristic token eviction with principled optimization. Attention Matching (MIT, 2602.16284) introduced the first closed-form KV compaction decomposition via NNLS for attention mass and OLS for attention output -- no gradient descent, no training, just linear algebra on small matrices that fit in L2 cache. Expected Attention (NVIDIA, KVPress library) uses Gaussian MGF closed-form scoring with Flash Attention compatibility and explicit quantization orthogonality. TriAttention (Song Han lab, MIT/NVIDIA) exploits the intrinsic trigonometric concentration of pre-RoPE Q/K vectors (Mean Resultant Length R approximately 0.98) for scoring. Memento (Microsoft Research) revealed the dual information stream: KV cache states computed while a block is visible carry implicit information recoverable by probing at 23-27% from downstream memento states (vs 10% chance), establishing a fundamental ceiling for all text-level compression approaches.

## Key Findings

### Quantization (Deployed)

- **Hadamard+q4_0 is quality-neutral at production scale**: PPL increase of +0.017 on Qwen2.5-7B at 512 tokens. Needle-in-haystack: 9/9 at 1K/4K/16K on Coder-32B. Walsh-Hadamard rotation smooths outlier distributions before quantization via orthogonal transform that preserves norms while redistributing magnitude across dimensions. Production config: `-ctk q4_0 -ctv f16` for pure-attention models, `-ctk q4_0 -ctv q4_0` for hybrid SSM (validated at PPL 1.2466 vs f16 1.2510 on Q35 frontdoor). [KV cache quantization handoff](../handoffs/completed/kv-cache-quantization.md)

- **q4_0 Key cache degrades at extended context on pure-attention models**: At 32K context, q4_0/q4_0 (both K and V quantized) produces garbage output on Qwen2.5-7B; q8_0/q4_0 remains correct. The safe production config uses q4_0 for Keys with Hadamard rotation and f16 for Values on pure-attention models. Hybrid SSM models with 75% recurrent layers absorb the quantization error (validated: PPL identical at 4K context). [KV cache quantization handoff](../handoffs/completed/kv-cache-quantization.md)

- **Upstream auto-enables Hadamard rotation**: llama.cpp v3 upstream PR #21038 (`744c0c731`) auto-enables identical Walsh-Hadamard rotation when KV types are quantized. The `--kv-hadamard` flag from our production branch is superseded. The upstream implementation may be more optimized, potentially reducing the +9% wall time overhead observed at 32K context with dequant during prefill. [v3 rebuild handoff](../handoffs/active/llama-cpp-v3-upstream-rebuild.md)

- **TurboQuant (TQ3) loses to Hadamard+q4_0 on CPU**: ikawrakow's full implementation on EPYC 9975 shows Hadamard+q4_0 at 1279 tok/s vs TQ3 at 573 tok/s -- 2.2x faster. Even with all four ecosystem fixes (norm correction, S=512 initial layers, fused dequant, 32-block format), TQ3 is slower on CPU due to codebook lookup overhead vs simple q4_0 dequant on AVX-512. TQ3 is on monitor-only status; revisit only if upstream merges natively with fused FA kernel. [TQ3 handoff](../handoffs/active/tq3-quantization-evaluation.md)

- **Hybrid buffer architecture is memory-negative**: The dual-cache design (kv_recent f16 + kv_old q4_0) allocates both at full context size, using MORE memory than a single f16 cache. The standard single-cache with quantized KV types is strictly better. Split attention (separate scoring for old and recent, concat, single softmax) works correctly at 5.2 t/s on 14.5K context but is unnecessary with the single-cache approach. Archived as research. [KV cache quantization handoff](../handoffs/completed/kv-cache-quantization.md)

### Compaction (Active -- L1-L4 Merged to Production)

- **Attention Matching achieves 5x zero-degradation validated on 3 models**: HighestAttnKeys-fast compaction uses three closed-form steps: RMS key selection, NNLS for per-token scalar biases (beta) that reproduce attention mass, and OLS for fitted values that reproduce attention output. Validated at 2x (cosine 1.000, universally lossless), 5x (0.906 average across layers), 10x (0.807). Layer-adaptive compression is the right strategy: 10x for early layers (1.000 cosine at layer 0), 5x for middle (0.878 at layer 14), 2x for deep (1.000 at layer 27). Combined effective ratio approximately 5x with near-lossless quality. [AM deep-dive](../research/deep-dives/kv-compaction-attention-matching-cluster.md), [AM handoff](../handoffs/active/attention-matching-kv-compaction.md)

- **Full native ggml implementation merged to production**: Three production commits: `81c9ad1ec` (L1-L4: beta injection via kq_mask, public API `llama_memory_set_beta()`, NNLS+OLS solvers, server endpoints), `80c72c0c6` (state format versioning for backward compat), `7784b3d9c` (L4b K-norm importance scoring for compact endpoint). Validated on Qwen2.5-7B-f16, Coder-32B-Q4KM, and Qwen3.5-35B-SSM-hybrid at 5x compression with zero degradation. SSM-hybrid support preserves recurrent state tail bytes. [AM handoff](../handoffs/active/attention-matching-kv-compaction.md)

- **AM's decode-side change is minimal**: `score[j] += beta[j]` in the attention inner loop -- one `_mm512_add_ps` per 16 positions, negligible vs memory-bandwidth-bound attention. Plus KV metadata for logical vs physical length. Flash attention path required disabling for compacted slots (Phase 1); CPU flash kernel modification deferred to Phase 2. [AM deep-dive](../research/deep-dives/kv-compaction-attention-matching-cluster.md)

- **CPU timing is well within budget**: NNLS approximately 10ms, OLS approximately 13ms at T=4096 on EPYC. Small dense matrices fit in L2 cache. The 2.2s H200 GPU timing is likely dominated by CUDA kernel launch overhead. CPU may actually be faster for these small linear algebra subproblems. [AM handoff](../handoffs/active/attention-matching-kv-compaction.md)

- **Online compaction enables effective context extension**: 2048 physical KV + 6 repeated 50% compactions = 8192 effective context = 13/30 on AIME, matching uncompacted 8192. Reasoning state preserved across consecutive compactions. This pattern (compact-in-place during generation) composes with all other layers: if live KV is quantized + block-masked, AM compaction dequantizes for scoring, fits compact (K,beta,V), re-quantizes. [AM deep-dive](../research/deep-dives/kv-compaction-attention-matching-cluster.md)

- **Latent Briefing is broken -- do NOT use as reference**: Code audit revealed PGD beta optimization is a no-op (optimizes against kept-only attention pattern, not full-cache pattern -- the target variable is created but never referenced in the loss). Ridge C2 correction ignores V_full. "Cross-model KV transfer" is standard text-passing via Anthropic API. The AM paper is the correct formalization. [AM deep-dive](../research/deep-dives/kv-compaction-attention-matching-cluster.md)

### Selection (Active -- Scaffold Ready)

- **TriAttention's trigonometric scoring is the strongest decode-phase method**: On AIME25 at 2048 KV budget: TriAttention 32.9%, SnapKV 20.0%, R-KV 17.5% (full attention: 40.8%). Q/K concentration is a real intrinsic model property: Mean Resultant Length R = 0.977-0.980 across 5 architectures including MLA with 940 heads. Calibration is robust -- works with 50K-960K tokens of any data, even "Google homepage HTML." Ablation validates the trig series: removing S_trig collapses AIME24 from 42.1% to 18.8% (-23.3pp). [TriAttention deep-dive](../research/deep-dives/triattention-kv-selection-cluster.md)

- **Expected Attention is more practically deployable**: Flash Attention compatible (SnapKV and H2O require materializing the full attention matrix -- incompatible with Flash Attention). Explicitly orthogonal to quantization (validated claim: "quantization methods orthogonal to Expected Attention... making it possible to integrate them"). GQA/MQA supported with per-head adaptive compression. KVPress library includes 20+ methods with standardized benchmarking and public HuggingFace leaderboard. RULER 4K accuracy: 94.7% at 50% compression vs SnapKV 55.7% (+39pp). [TriAttention deep-dive](../research/deep-dives/triattention-kv-selection-cluster.md)

- **Selection vs compaction: AM subsumes selection at high ratios**: At 20x+, Attention Matching (latent-space construction with fitted biases and values) outperforms all token-selection baselines (H2O, SnapKV, PyramidKV, KVzip). At 5-10x, the gap narrows and selection may be sufficient and simpler (no attention biases needed). Selection and compaction are redundant to stack -- AM constructs better compact representations than keeping original tokens. The crossover point depends on model architecture. [AM handoff](../handoffs/active/attention-matching-kv-compaction.md)

- **LongFlow's 11.8x headline is misleading**: Measures system-level throughput vs vanilla (no compression), not accuracy-matched like TriAttention's 2.5x. Scoring degrades under "abrupt distribution shifts (topic switches, tool-use interleaving, highly stochastic decoding)" -- exactly our orchestrator's workload pattern. Downgraded to LOW priority. [TriAttention deep-dive](../research/deep-dives/triattention-kv-selection-cluster.md)

- **Quantization interaction is the critical unknown for selection**: Neither TriAttention nor Expected Attention tested on Hadamard-rotated q4_0-quantized K vectors. Hadamard preserves norms (orthogonal transform) but q4_0 introduces norm error. TriAttention scoring uses pre-RoPE centers (offline) and current K norms (online) -- the norm signal degrades under quantization. Expected Attention's Gaussian approximation may be more robust to quantization noise but has not been tested. [TriAttention deep-dive](../research/deep-dives/triattention-kv-selection-cluster.md)

### Block Masking (Active -- Feasibility Confirmed)

- **Memento's dual information stream is the most important theoretical finding**: KV cache states computed while a reasoning block is visible carry implicit information beyond what the summary text captures. Recomputing memento KVs without block context: AIME24 drops from 66.1% to 50.8% (-15.3pp). Probing with injected 5-digit passcode: direct memento recovers at 60-70%, masked memento at 23-27% (vs 10% chance), signal concentrates in deeper layers (26.5% at layer 36 vs 10.8% at layer 4 for Qwen3-8B). Confirmed on toy transformer at 24.9% masked accuracy. This is **architectural, not learned**. [Memento deep-dive](../research/deep-dives/memento-iterative-reasoning-cluster.md)

- **Text-level compression has a fundamental approximately 15pp ceiling vs KV-retaining approaches**: Any method that discards KV and keeps only text summaries (InftyThink, Accordion-Thinking, our context-folding) loses the implicit KV channel. This establishes Memento's KV-retaining block masking as strictly superior to text-level compression for reasoning tasks. [Memento deep-dive](../research/deep-dives/memento-iterative-reasoning-cluster.md)

- **Accuracy gap is consistency, not capability**: Pass@64 Jaccard similarity between Base and Memento solved sets is 96.4%. The model can solve the same problems, just less reliably. Majority voting at k=3 recovers base accuracy without RL. Combining Memento KV savings with our short-m@k voting infrastructure yields 2-3x KV reduction at zero accuracy cost. Scale helps: gap narrows from -6.3pp at 8B to -3.5pp at 32B. MATH-500 is near-lossless (<1pp) across all scales. [Memento deep-dive](../research/deep-dives/memento-iterative-reasoning-cluster.md)

- **Accordion-Thinking provides runtime fold/unfold toggle**: Same model, same weights, user chooses at request time between compressed (Fold, 3-4x throughput) and full (Unfold, max accuracy). After RL training, accuracy gap vanishes (Fold 52.7 macro vs Unfold 52.2). Maps directly to our difficulty routing: easy problems to Fold, hard to Unfold. [Memento deep-dive](../research/deep-dives/memento-iterative-reasoning-cluster.md)

- **InftyThink+ demonstrates RL-learned adaptive compression**: +21pp on AIME24 vs SFT baseline (largest single improvement in the cluster). Task+efficiency RL trades 3.4pp accuracy for 60-70% latency reduction. Key finding: after RL, internal summaries outperform external (GPT-4) summaries -- the model learns summary strategy coupled to its own reasoning. Implies our context-folding Phase 2 (external 7B summarizer) should eventually move summarization into the reasoning model itself. [Memento deep-dive](../research/deep-dives/memento-iterative-reasoning-cluster.md)

- **llama.cpp block masking uses existing API**: `llama_memory_seq_rm()` at `include/llama.h:733` provides the eviction primitive. Block boundaries tracked via special tokens (`<|block_start|>`, `<|block_end|>`, `<|summary_start|>`, `<|summary_end|>`). Freed cells are immediately reusable. Position gaps must NOT be closed with `seq_add` -- the dual information stream requires preserving original RoPE phases. Feasibility confirmed 2026-04-13. Test skeleton written. [Memento handoff](../handoffs/active/memento-block-reasoning-compression.md)

- **OpenMementos dataset available for fine-tuning**: 228K examples, 4.7 GB, MIT licensed. Approximately 9 blocks/response median, approximately 12K tokens/response. Two-stage LoRA training design: Stage 1 (format learning, full attention, 2 epochs), Stage 2 (compression learning, custom memento attention mask removing approximately 59% of causal positions, 1 epoch). CPU-feasible validation path: Qwen3-1.7B in approximately 54h. Production 32B requires GPU QLoRA. [Memento handoff](../handoffs/active/memento-block-reasoning-compression.md)

### Cross-Instance Sharing

- **KVCOMM eliminates redundant prefill across homogeneous worker pools**: When 3+ coder-32B instances share the same codebase context (10K-50K tokens), KVCOMM reduces 3 independent 50K-token prefills to approximately 1.3x one prefill. Anchor-based offset estimation works within same-model same-quant boundaries. Compounds with AM compaction: AM compresses shared context, KVCOMM shares the compressed result. Triple hard blocker for heterogeneous stack (Claude+Qwen3 at mixed quants), but valid for homogeneous NUMA pools. Open questions: q4_0 offset estimation untested, cross-NUMA IPC for anchor pool, AIME 8-11pp drop on hard reasoning. [AM deep-dive](../research/deep-dives/kv-compaction-attention-matching-cluster.md)

## Actionable for EPYC

- **Deployed**: Hadamard+q4_0 KV quantization (2-4x, production since `b51c905`, auto-enabled in v3 upstream via PR #21038)

- **Merged to production branch**: Attention Matching L1-L4+L4b -- native ggml NNLS+OLS, K-norm importance scoring, server endpoints (`set-beta`, `seq-rm`, `compact`), SSM-hybrid support. Three production commits on `production-consolidated-v3`

- **Next validation steps**: P2 Coder-32B coding benchmarks (validates production deployment at scale), P3 comparison vs Expected Attention at 5x/10x/20x (determines whether selection or compaction is primary path at each ratio), P4 AM + Hadamard q4_0 stacking quality test (validates dual compression)

- **Scaffold ready, awaiting model server**: KVPress Expected Attention evaluation on Qwen2.5-7B. S1 gate: >=90% RULER at 50% compression. S2: TriAttention Q/K concentration validation (expect R>=0.95). S3: selection+quantization stacking quality test

- **Feasibility confirmed, awaiting infrastructure**: Memento block masking via `llama_memory_seq_rm()`. OpenMementos dataset downloaded. LoRA training design complete. CPU-feasible validation on 1.7B; production 32B requires GPU QLoRA

- **Priority ranking**:
  1. HIGH: Complete AM P2 benchmarks on Coder-32B (validates production deployment for highest-value model)
  2. HIGH: Run KVPress S1/S2/S3 evaluation gates (determines selection method and stacking viability)
  3. MEDIUM: AM P4 dual compression test (AM + Hadamard q4_0 stacking -- validates the 8-40x combined promise)
  4. MEDIUM: Prototype llama.cpp block masking for Memento (builds on ISWA work and existing `llama_memory_seq_rm()`)
  5. LOW: KVCOMM for parallel worker pools (Phase F in dynamic-stack-concurrency, only relevant when running 3+ same-model instances)

## Open Questions

- Does Attention Matching maintain 5x quality on coding benchmarks (Coder-32B at production-length contexts)? Information-dense content degrades faster than narrative in the paper. Short-prompt P2 results (0.807 at 10x) may improve significantly at 32K+ context where AM has more attention structure to exploit
- Can Expected Attention and quantization stack without quality cliff? The paper's explicit orthogonality claim needs validation on our specific models with Hadamard rotation
- Does TriAttention's trigonometric scoring work on Hadamard-rotated q4_0 K vectors? Hadamard preserves norms but q4_0 introduces error -- the net effect on the Q/K concentration property is untested
- What is the real-world quality under triple-stack compression (quant + compaction + masking)? Each pair tested independently but three-way interaction is unknown and may be multiplicative in degradation
- Can Memento-style models be created via LoRA fine-tuning on OpenMementos with GGUF-quantized base models, or does quantization degrade the implicit KV information channel?
- At what compression ratio does AM compaction subsume selection? The handoff estimates 20x+ but the crossover depends on model architecture and context length
- Does the L4c true NNLS attention scoring (deferred -- requires graph modification to retain attention weights during inference) offer meaningful quality improvement over L4b K-norm approximation?

## Related Categories

- [Speculative Decoding](speculative-decoding.md) -- Speculative decoding increases KV pressure; KV compression enables larger speculation budgets. The verification wall on hybrid models makes KV optimization even more critical (speculation cannot help, so other levers matter more)
- [Quantization](quantization.md) -- Weight quantization (Q4_K_M) and KV quantization (Hadamard+q4_0) are orthogonal. KV quantization is the first deployed layer of the compression stack
- [MoE Optimization](moe-optimization.md) -- MoE models have different KV patterns than dense; MLA (Leanstral's DeepSeek V3 architecture) reduces KV cache independently of expert pruning via low-rank latent attention
- [Context Management](context-management.md) -- Context folding and session compaction are text-level compression; Memento's dual information stream shows KV-level approaches are strictly superior for reasoning

## Source References

- [KV Compaction Attention Matching Deep-Dive](../research/deep-dives/kv-compaction-attention-matching-cluster.md) -- AM closed-form decomposition (NNLS+OLS), 50x compression on narrative QA, Latent Briefing code audit (broken corrections), KVCOMM analysis (valid for homogeneous pools), LRAgent rejection (LoRA-specific)
- [TriAttention KV Selection Deep-Dive](../research/deep-dives/triattention-kv-selection-cluster.md) -- Trigonometric scoring validated on 5 architectures, Expected Attention upgraded (Flash compatible, quantization orthogonal), LongFlow downgraded (topic-switch failure), In-Place TTT rejected (incompatible with GGUF)
- [Memento Iterative Reasoning Deep-Dive](../research/deep-dives/memento-iterative-reasoning-cluster.md) -- Dual information stream (15pp ceiling for text compression), Accordion fold/unfold toggle, InftyThink+ efficiency reward (+21pp AIME24), OpenMementos pipeline (228K MIT dataset), quad-stack analysis
- [AM Handoff](../handoffs/active/attention-matching-kv-compaction.md) -- L1-L4+L4b merged to production, P2 layer-adaptive results, server endpoints, SSM-hybrid support
- [TriAttention Handoff](../handoffs/active/triattention-kv-selection.md) -- KVPress scaffold, evaluation gates S1-S4, composability analysis with AM and Memento
- [Memento Handoff](../handoffs/active/memento-block-reasoning-compression.md) -- Block masking feasibility confirmed, llama.cpp API mapping, LoRA training design, OpenMementos downloaded
- [KV Cache Quantization Handoff](../handoffs/completed/kv-cache-quantization.md) -- Hadamard Phase 1 deployed, hybrid buffer archived, TurboQuant/PolarQuant/QJL abandoned, split attention working but unnecessary
- [TQ3 Monitor Handoff](../handoffs/active/tq3-quantization-evaluation.md) -- TQ3_1S on monitor-only, PR #21038 Hadamard auto-rotation, PR #21089 CPU TurboQuant KV cache
- [intake-191] TurboQuant -- Extreme KV cache compression (3-4 bit with Hadamard)
- [intake-192] PolarQuant -- Polar transformation for KV quantization
- [intake-193] QJL -- 1-bit quantized JL transform for KV cache, zero overhead claim
- [intake-256] Multiscreen Attention -- Screening architecture replacing softmax attention
- [intake-284] TriAttention paper -- Trigonometric KV scoring, Song Han lab
- [intake-287] LongFlow -- Attention-weighted value norm scoring (downgraded)
- [intake-288] Expected Attention paper -- Gaussian MGF scoring, KVPress library
- [intake-289] Memento paper -- Dual KV stream, block masking, Microsoft Research
- [intake-292] InftyThink (ICLR 2026) -- Iterative reasoning compression
- [intake-293] InftyThink+ -- RL-learned adaptive compression
- [intake-294] Accordion-Thinking -- Fold/unfold runtime toggle
- [intake-350] Latent Briefing -- Broken (PGD no-op, Ridge no-op, do NOT use)
- [intake-351] Attention Matching paper (2602.16284) -- Closed-form KV compaction, MIT
- [intake-352] KVCOMM (NeurIPS'25) -- Cross-context KV sharing for homogeneous pools
