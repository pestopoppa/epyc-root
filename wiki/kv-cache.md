# KV Cache Optimization

**Category**: `kv_cache`
**Confidence**: verified
**Last compiled**: 2026-08-23 (**wave-2 research intake — the KIVI "primary quality gap" recorded for months at `kv-cache-quantization.md:320` never existed**: per-token V is structurally guaranteed once V is quantized (quantized V forces flash attention, which sets `v_trans=false`, making V channel-contiguous), the per-channel-K half is a **2-bit-only** prescription by KIVI's own OB 1, and key outliers are handled instead by the in-tree Hadamard rotation — the only residual is symmetric-vs-asymmetric, which is a flag (`q4_1`/`q5_1`), not a code change; **the granularity reading rule**: with `-fa 1` we quantize K and V per token in 32-element blocks along CHANNELS, finer than the Group-64 *mitigation* published in the alignment-collapse study and on the OPPOSITE axis from KIVI, so third-party KV-quant damage numbers are a pessimistic bound for us and must never be transferred unqualified; **VeriCache's algorithmic core is already expressible in frozen v9 with no code change** (`-ctkd`/`-ctvd` set the draft context's KV type independently of the target's and a model can be its own drafter) while its systems contribution depends on an interconnect we do not have; the dual-cache post-mortem is reframed as **a capacity argument applied to a bandwidth problem**; the PCIe "KV streaming is an anti-pattern" line is scoped to *per token*; R9's spec-decode verdict stands on NIAH+PPL while its throughput warrant is void; and llama.cpp slot-restore reuse loss is **conditional, not blanket** — zero only for a DIVERGENT or EXACT-REPEAT prompt, full for a strict continuation, with upstream PR #25592 (live in-memory checkpoint path) outranking #26004 (dormant disk path) for us — see the end of the page; earlier 2026-08-23 note: evening wave-2 compile: the KIVI "no gap" correction + the REAL instrument gap, the dual-cache reframing (capacity vs bandwidth), the group-32/axis granularity correction, and the KV-quant monitoring gates G2-G5 with the massive-activations deprioritisation — see bottom sections; earlier same-day: the orchestrator prefix-cache path now has an owner and a measurement plan: KV-5 closed in the wiki, the three latent defect fixes KV-0a/b/c landed 2026-08-20 — every KV slot save was failing, roles sharing one server silently clobbered each other's slots, and `radix_cache.py` was dead code — and the KV-1/KV-2/KV-3/KV-4/KV-6 rows filed — see the end of the page; earlier 2026-08-22 note: closure fine-structure of the COMPLETED KV-quant handoff — **V-dequant, not K, is the entire CPU flash-attention prefill cost** (q4_0/f16 −1% vs q8_0/q4_0 +71%; q8_0/q8_0 is the worst prefill config measured at 3.3× slower, reconciling the 2026-08-03 memory-optimal reading as a different axis); Hadamard's isolated contribution priced at 70% gap closure (+0.055 → +0.017); TQ3 abandoned on a *fair* 32B retest after its first gate was flagged as failure-zone-unfair; QJL's SNR≈1.13 arithmetic death; spec-decode +3.3% with q8_0/q4_0; the 4-KV-head q4_0-K hazard; and PR #21089 (TurboQuant CPU KV) verified CLOSED UNMERGED upstream 2026-06-02, retiring the 2026-07-20 monitor row — see the end of the page; earlier 2026-08-12 note: a fork SWA slot-reuse patch previously held for review is **DROPped as a correctness regression, not merely redundant** — it deleted upstream's per-sequence check; KV quantization gets its first decision package with an exact parity result; and lazy KV faulting is re-read as *relocating* provisioning cost rather than removing it; earlier 2026-07-20 note: adds the StreamingLLM floor/admission verdict, the TurboQuant/ChunkKV KV-quant monitor status, and the MI210 KV-split residency facts; earlier 2026-07-17 pass retained)
**Sources**: 44 documents (3 deep-dives, 8 active handoffs, 2 completed handoffs, 25 intake entries, 3 progress logs, 2 upstream issue threads)

## Compiled Update — 2026-08-12: a "keep or port?" review that resolves to *neither*, and the first KV-quant decision package

**Confidence: verified** — the fork verdicts are read-only git archaeology with commit SHAs and ancestry checks; the KV-quant numbers are a measured retrieval-parity run.

### The SWA slot-reuse fork commits: DROP, because they subtract a safety check

Two fork commits (`d1c72d7fc`, `603702769`) sat under review as ambiguous keep-or-port candidates. The verdict is **DROP**, and the reason is stronger than redundancy: the fork **deletes** upstream's `cells.seq_get(idx)` lookup and substitutes the incoming batch's position, replacing a per-sequence-aware sliding-window reuse check with a **per-sequence-blind** one. Under multi-slot serving a cell can be judged reusable against the wrong slot's window. Production v6 through v9 correctly retain upstream's original form and were never exposed.

The reusable lesson for fork-reconciliation reviews: **a commit that reads as "our version of upstream's check" may be upstream's check with a lookup removed.** The discriminating question is not *does the fork do the same thing* but *what does the fork's diff delete*.

### KV quantization has a decision package, and q8 is dominated

The first exact-parity KV-quant measurement gives a clean shape: across f16 / q8_0 / q4_0 KV, retrieval parity holds at **51 of 52 on every arm**. `q4_0` buys **10.54 GiB** of KV headroom at **−7.4% decode**; **q8 is dominated** — it neither preserves the f16 operating point nor buys q4_0's memory. One arm (C) aborted invalid. The recommendation is Option A. This is the first result that lets the KV-quant monitor status recorded in the 2026-07-20 pass below be acted on rather than watched.

### Lazy faulting relocates the `-c` provisioning cost, it does not remove it

The old premise for capping context provisioning — that a large `-c` costs at *launch* — is dead: KV pages fault lazily. But the re-read is not "provision maximally and stop worrying". The cost moves from launch to **load**, and the worst case is the sum of full-window KV across all resident roles under concurrent deep-context load, **which is currently uncomputed**. The recommendation is the staged option: raise `-c` only where the lineup's Σ full-window-KV fits RAM with margin, computed mechanically at priors-compile rather than chosen per role. The ruling belongs to the lineup owner plus the operator and is **not settled**.

### Source References (2026-08-12)

- [`llamacpp-v6-consolidation.md`](../handoffs/active/llamacpp-v6-consolidation.md) — the SWA slot-reuse DROP verdict and the deleted per-sequence check.
- [`numa-placement-defect-20260730.md`](../handoffs/active/numa-placement-defect-20260730.md) — the T12 lazy-KV decision package and the uncomputed concurrent-load worst case.
- [`progress/2026-08/2026-08-12.md`](../progress/2026-08/2026-08-12.md) — the KVQuant parity/headroom numbers and the dominated-q8 finding.

## Compiled Update — 2026-07-20

The StreamingLLM baseline — the cluster-wide gate that must precede prioritizing the whole May-2026 KV-reduction cluster (SP-KV / KVP / LU-KV / ForesightKV / PBKV) — reached a pre-v7 verdict, and the MI210 sharpened where KV should physically live. Confidence: `verified` for the CPU floor sweep result; `external` for the KV-quant PRs; `inferred` for the MI210 KV-placement economics.

### Key Findings (2026-07-20)

- **StreamingLLM (attention-sink + sliding-window) is the easy-floor gate, and no simple KV cluster is admitted yet.** The scaffold landed in the fork (`632ce0f92`, default-off, via server context-shift `llama_memory_seq_rm`/`seq_add` + `--kv-streaming-sink/-window` + per-request fields) and was reconciled onto current v7 (`111bff89d`/`cf051d3e1`). The pre-v7 floor/admission sweep (Qwen3-1.7B Q8 CPU, 2026-07-20) ran a context-shift baseline + sink/window clusters `8:128`/`16:192`/`32:256`: all arms exited cleanly but **all failed the prompt-quality/final-marker floor**, and no streaming arm beat baseline speed (0.990–1.011×) → `admit_cluster=false`. This closes the "admit a simple KV cluster *now*?" question negatively; the full 4-axis research sweep (retrieval/reasoning/dialogue × 25/50/75% budget × 2 models) stays open. ([streaming-llm-baseline](../handoffs/active/streaming-llm-baseline.md))
- **KV-quant monitor status:** Hadamard rotation (upstream PR #21038) landed and auto-enables when KV types are quantized — a free KV-quality improvement (custom `--kv-hadamard` removed as redundant). TurboQuant CPU KV kernels (PR #21089, TBQ3_0/TBQ4_0, ~5.2× compression) remain open/monitor; ChunkKV (arXiv:2502.00299, 12% retention, +26.5% throughput) is worth-investigating. TQ3_1S rejection stands (immature, VRAM-savings we don't need, MoE ghost-activation risk). ([tq3-quantization-evaluation](../handoffs/active/tq3-quantization-evaluation.md))
- **Where KV physically lives (MI210):** keeping KV in HBM alongside attention weights is ideal but VRAM-limited; PCIe4 (~64 GB/s) is 7–14× slower than EPYC DDR5, so per-token KV *streaming* is an anti-pattern. GDN-hybrid residents have **O(1) KV**, so long-context ingest is comfortably GPU-served (better than a dense model) and makes teleport KV-copy near-moot — the teleport v1 instead *re-prefills from transcript* to regenerate correct KV at the target quant (a copied KV is wrong under quant-asymmetric transport). ([gpu-acceleration-path](../handoffs/active/gpu-acceleration-path.md), [heterogeneous-slot-fabric-residency](../handoffs/active/heterogeneous-slot-fabric-residency.md))

### Open Questions (2026-07-20)

- Does StreamingLLM at 50% budget preserve ≥95% accuracy on our representative workloads (the 4-axis sweep is still pending)? The answer sets whether LU-KV/KVP/ForesightKV get demoted or LU-KV promoted.
- Does uniform sink+window hide per-head heterogeneity (LU-KV's whole pitch)? Track per-head attention entropy in the sweep.
- Does PR #21089 (TurboQuant CPU KV) merge and beat Hadamard+q4_0 on context extension?

### Source References (2026-07-20)

- [streaming-llm-baseline.md](../handoffs/active/streaming-llm-baseline.md) — cluster-wide floor gate, scaffold, negative pre-v7 admission sweep.
- [tq3-quantization-evaluation.md](../handoffs/active/tq3-quantization-evaluation.md) — TurboQuant/ChunkKV/Hadamard KV-quant monitor list.
- [gpu-acceleration-path.md](../handoffs/active/gpu-acceleration-path.md) — MI210 KV CPU/GPU-split economics + PCIe anti-pattern.
- [heterogeneous-slot-fabric-residency.md](../handoffs/active/heterogeneous-slot-fabric-residency.md) — O(1)-KV GDN residents + re-prefill teleport (KV-copy near-moot).

## Summary

KV cache is the dominant memory bottleneck for CPU inference on our EPYC 9655 stack. At 256K context, Qwen2.5-Coder-32B's KV cache at f16 consumes approximately 64 GB -- more than the model weights themselves. Since CPU inference is memory-bandwidth-bound during decode, reducing KV cache size directly improves both capacity (more concurrent slots, longer contexts) and throughput (less memory traffic per token). At very long sequences (S >> d_model), attention rises above 50% of total per-token compute time, making KV cache compression a throughput lever, not just a memory lever. Our research has identified four orthogonal compression layers that operate on different dimensions of the KV cache problem, and we have validated or deployed work across all four.

The four layers form a compression stack. **Quantization** (how each KV entry is stored) reduces precision: Hadamard+q4_0 delivers 2-4x compression quality-neutral and is deployed in production since commit `b51c905`, now auto-enabled in v3 upstream. **Compaction** (constructing fewer but more informative KV entries in latent space) uses mathematical optimization: Attention Matching achieves 5x zero-degradation with native ggml NNLS+OLS solvers merged to `production-consolidated-v3` across 3 commits, validated on Qwen2.5-7B-f16, Coder-32B-Q4KM, and Qwen3.5-35B-SSM-hybrid. **Selection** (keeping only important tokens) uses importance scoring: Expected Attention achieves 94.7% RULER at 50% compression on Qwen3-8B and is Flash Attention compatible; TriAttention is the strongest decode-phase scorer with trigonometric Q/K concentration. **Block masking** (removing entire reasoning blocks) leverages model structure: Memento provides 2-3x peak KV reduction by training models to segment reasoning into blocks and retaining only summary KV states; the key finding is that KV states carry implicit information beyond summary text (15pp accuracy penalty when KV states are recomputed without original block context).

Each layer operates on a different dimension -- precision, count, and semantic structure -- making them composable. The theoretical combined ceiling is staggering: quantization 4x times compaction 5x times masking 3x equals 60x. Even the conservative two-layer stack (quantization 4x times compaction 2x) would transform the deployment landscape from "one 256K context slot barely fits" to "eight concurrent slots." The critical unknown is quality interaction under multi-layer compression: each layer claims minimal individual loss, but combined degradation may be multiplicative. Pairwise testing is in progress; three-way testing is a separate gate.

The field is evolving rapidly around closed-form approaches that replace heuristic token eviction with principled optimization. Attention Matching (MIT, 2602.16284) introduced the first closed-form KV compaction decomposition via NNLS for attention mass and OLS for attention output -- no gradient descent, no training, just linear algebra on small matrices that fit in L2 cache. Expected Attention (NVIDIA, KVPress library) uses Gaussian MGF closed-form scoring with Flash Attention compatibility and explicit quantization orthogonality. TriAttention (Song Han lab, MIT/NVIDIA) exploits the intrinsic trigonometric concentration of pre-RoPE Q/K vectors (Mean Resultant Length R approximately 0.98) for scoring. Memento (Microsoft Research) revealed the dual information stream: KV cache states computed while a block is visible carry implicit information recoverable by probing at 23-27% from downstream memento states (vs 10% chance), establishing a fundamental ceiling for all text-level compression approaches.

## Key Findings

### Quantization (Deployed)

- **Hadamard+q4_0 is quality-neutral at production scale**: PPL increase of +0.017 on Qwen2.5-7B at 512 tokens. Needle-in-haystack: 9/9 at 1K/4K/16K on Coder-32B. Walsh-Hadamard rotation smooths outlier distributions before quantization via orthogonal transform that preserves norms while redistributing magnitude across dimensions. Production config: `-ctk q4_0 -ctv f16` for pure-attention models, `-ctk q4_0 -ctv q4_0` for hybrid SSM (validated at PPL 1.2466 vs f16 1.2510 on Q35 frontdoor). [KV cache quantization handoff](../handoffs/completed/kv-cache-quantization.md)

- **q4_0 Key cache degrades at extended context on pure-attention models**: At 32K context, q4_0/q4_0 (both K and V quantized) produces garbage output on Qwen2.5-7B; q8_0/q4_0 remains correct. The safe production config uses q4_0 for Keys with Hadamard rotation and f16 for Values on pure-attention models. Hybrid SSM models with 75% recurrent layers absorb the quantization error (validated: PPL identical at 4K context). [KV cache quantization handoff](../handoffs/completed/kv-cache-quantization.md)

- **Upstream auto-enables Hadamard rotation**: llama.cpp v3 upstream PR #21038 (`744c0c731`) auto-enables identical Walsh-Hadamard rotation when KV types are quantized. The `--kv-hadamard` flag from our production branch is superseded. The upstream implementation may be more optimized, potentially reducing the +9% wall time overhead observed at 32K context with dequant during prefill. [v3 rebuild handoff](../handoffs/completed/llama-cpp-v3-upstream-rebuild.md)

- **TurboQuant (TQ3) loses to Hadamard+q4_0 on CPU**: ikawrakow's full implementation on EPYC 9975 shows Hadamard+q4_0 at 1279 tok/s vs TQ3 at 573 tok/s -- 2.2x faster. Even with all four ecosystem fixes (norm correction, S=512 initial layers, fused dequant, 32-block format), TQ3 is slower on CPU due to codebook lookup overhead vs simple q4_0 dequant on AVX-512. TQ3 is on monitor-only status; revisit only if upstream merges natively with fused FA kernel. [TQ3 handoff](../handoffs/active/tq3-quantization-evaluation.md)

- **Hybrid buffer architecture is memory-negative**: The dual-cache design (kv_recent f16 + kv_old q4_0) allocates both at full context size, using MORE memory than a single f16 cache. The standard single-cache with quantized KV types is strictly better. Split attention (separate scoring for old and recent, concat, single softmax) works correctly at 5.2 t/s on 14.5K context but is unnecessary with the single-cache approach. Archived as research. [KV cache quantization handoff](../handoffs/completed/kv-cache-quantization.md)

### Compaction (Active -- L1-L4 Merged to Production)

- **Attention Matching achieves 5x zero-degradation validated on 3 models**: HighestAttnKeys-fast compaction uses three closed-form steps: RMS key selection, NNLS for per-token scalar biases (beta) that reproduce attention mass, and OLS for fitted values that reproduce attention output. Validated at 2x (cosine 1.000, universally lossless), 5x (0.906 average across layers), 10x (0.807). Layer-adaptive compression is the right strategy: 10x for early layers (1.000 cosine at layer 0), 5x for middle (0.878 at layer 14), 2x for deep (1.000 at layer 27). Combined effective ratio approximately 5x with near-lossless quality. [AM deep-dive](../research/deep-dives/kv-compaction-attention-matching-cluster.md), [AM handoff](../handoffs/active/attention-matching-kv-compaction.md)

- **Full native ggml implementation merged to production**: Three production commits: `81c9ad1ec` (L1-L4: beta injection via kq_mask, public API `llama_memory_set_beta()`, NNLS+OLS solvers, server endpoints), `80c72c0c6` (state format versioning for backward compat), `7784b3d9c` (L4b K-norm importance scoring for compact endpoint). Validated on Qwen2.5-7B-f16, Coder-32B-Q4KM, and Qwen3.5-35B-SSM-hybrid at 5x compression with zero degradation. SSM-hybrid support preserves recurrent state tail bytes. [AM handoff](../handoffs/active/attention-matching-kv-compaction.md)

- **AM's decode-side change is minimal**: `score[j] += beta[j]` in the attention inner loop -- one `_mm512_add_ps` per 16 positions, negligible vs memory-bandwidth-bound attention. Plus KV metadata for logical vs physical length. Flash attention path required disabling for compacted slots (Phase 1); CPU flash kernel modification deferred to Phase 2. [AM deep-dive](../research/deep-dives/kv-compaction-attention-matching-cluster.md)

- **CPU timing is well within budget**: NNLS approximately 10ms, OLS approximately 13ms at T=4096 on EPYC. Small dense matrices fit in L2 cache. The 2.2s H200 GPU timing is likely dominated by CUDA kernel launch overhead. CPU may actually be faster for these small linear algebra subproblems. [AM handoff](../handoffs/active/attention-matching-kv-compaction.md)

- **Online compaction enables effective context extension**: 2048 physical KV + 6 repeated 50% compactions = 8192 effective context = 13/30 on AIME, matching uncompacted 8192. Reasoning state preserved across consecutive compactions. This pattern (compact-in-place during generation) composes with all other layers: if live KV is quantized + block-masked, AM compaction dequantizes for scoring, fits compact (K,beta,V), re-quantizes. [AM deep-dive](../research/deep-dives/kv-compaction-attention-matching-cluster.md)

- **Latent Briefing is broken -- do NOT use as reference**: Code audit revealed PGD beta optimization is a no-op (optimizes against kept-only attention pattern, not full-cache pattern -- the target variable is created but never referenced in the loss). Ridge C2 correction ignores V_full. "Cross-model KV transfer" is standard text-passing via Anthropic API. The AM paper is the correct formalization. [AM deep-dive](../research/deep-dives/kv-compaction-attention-matching-cluster.md)

- **Still introduces the missing third compaction category -- amortized synthesis**: Compaction methods now split three ways: token *selection* (keep/evict originals), *per-context synthesis* (optimize a compact cache per input, e.g. Cartridges), and *amortized synthesis* (Still). Still trains a small per-layer Perceiver -- learned latent queries cross-attending the live KV cache -- **once** against a frozen base model via forward-KL distillation from a full-context teacher, then synthesizes compact K/V in a **single forward pass** (not gradient descent per context). This combines selection-method lightness with synthesis-method expressiveness. The trained compactor transfers across model scales (4B-32B) and attention architectures unmodified, and runs iteratively/chunked for streaming. Position-free placement via inverse-RoPE -> latent positioning -> re-rotation. Reported: beats KV-Distill by 8-22 points in 16/18 RULER cells across 8x-200x compression and 8k-128k context; 256k @100x = 40.7% QuALITY. No public code or released compactor weights as of 2026-06-05 -- gated on a one-time GPU distillation pass per base model. [intake-708] Still

- **Our deployed default compactor is Expected-Attention (TriAttention), NOT Attention-Matching**: Despite the AM native ggml work being merged, the production default compactor on the live stack is Expected-Attention (the TriAttention selection scorer); AM K-norm is the *legacy fallback*. Crucially, even AM is selection+beta (keep a key subset, add fitted bias/values), **not synthesis** -- so there is no deployed amortized-synthesis path against which Still could be benchmarked today. The AM handoff/experiment notes still cite the `production-consolidated-v3` branch label, but production has since rebased to v5 (functionality carried forward across rebases). [AM handoff](../handoffs/active/attention-matching-kv-compaction.md)

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

- **Autopilot integration complete (2026-04-14)**: `slot_compact` action dispatch wired into autopilot controller (`autopilot.py:812-849`). Controller can issue compaction commands to production slots, logs pre/post token counts, measures quality via `hybrid_eval()`. Slot memory visibility added: `_query_slot_memory()` queries `/slots` on primary production ports (8070-8084) each trial, showing per-slot context size in the controller prompt. Guideline: compact when any slot exceeds 4000 cached tokens. Validated parameters: keep_ratio=0.3, beta=0.5. Long-context validation (8K-32K production contexts) deferred to AR-3 -- current tests validated up to 2.7K tokens. [bulk-inference-campaign.md Package D]

- **Next validation steps**: P2 Coder-32B coding benchmarks (validates production deployment at scale), P3 comparison vs Expected Attention at 5x/10x/20x (determines whether selection or compaction is primary path at each ratio), P4 AM + Hadamard q4_0 stacking quality test (validates dual compression)

- **KVPress HF path infeasible on CPU; replanned as llama.cpp-first (2026-04-14)**: KVPress runs through HuggingFace transformers, not llama.cpp. On EPYC CPU, even 0.5B at 4K-16K context took >5 min/sample with no results; 7B consumed 65GB and projected hours/sample (~100x slower than llama.cpp on identical hardware). S4 (Expected Attention C++ port to ggml) promoted to critical path. The scorer is a per-layer function (mean/cov of pre-RoPE queries + Gaussian future prediction + V-norm weighting), not an architecture change. Eviction uses `llama_memory_seq_rm()` validated by Memento S1 (5/5 tests, 2026-04-14). Once the scorer runs in llama.cpp, S1's RULER benchmark can execute at production speed. S2 (TriAttention Q/K concentration) and S3 (selection+quantization stacking) depend on S4 completion

- **Memento S1 runtime validation PASSED (2026-04-14)**: Block masking primitive validated end-to-end on Qwen3-1.7B-Q8_0. 5/5 tests passed: basic block eviction, position gap semantics, generation after eviction (no attention corruption), multi-block iterative eviction (4x compression, 200->50 KV entries), and memory reuse. S2 LoRA training now unblocked. OpenMementos dataset downloaded, training design complete. CPU-feasible validation on 1.7B; production 32B requires GPU QLoRA

- **Priority ranking**:
  1. HIGH: Complete AM P2 benchmarks on Coder-32B (validates production deployment for highest-value model)
  2. HIGH: Implement Expected Attention scorer in llama.cpp (S4 — critical path; HF CPU path infeasible, enables S1/S2/S3 eval at production speed)
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
- Does Still's amortized-synthesis quality (RULER wins over KV-Distill) survive the CPU compute-overhead-vs-quality trade vs the deployed Expected-Attention compactor, and can the per-layer Perceiver run cheaply enough on EPYC during decode? Untestable until code/weights release for a served family (Qwen/Gemma) -- tracked as a GPU-CPT-gated watch item in [`summary-token-attention-readiness.md`](../handoffs/active/summary-token-attention-readiness.md)

## Updates — 2026-04-29 (PM)

Three architectural sub-quadratic-attention papers ingested in same-day batch (intake-502 + intake-506 + intake-507) sharing the same first-principle: **sequence-level compression through a tunable ratio**, complexity O(n/k) or O(L·k) instead of O(n²) — preserving linear KV growth but compressing semantic content per position.

- **Kwai Summary Attention (KSA, intake-502)** — Kuaishou OneRec, arxiv:2604.24432. Learnable summary tokens injected at chunk boundaries (default chunk size k=8). 3:1 KSA-to-Full layer ratio. **Persistent summary visibility** — all summary tokens always visible to text. Reports +5.81 RULER-128K vs Full (CPT setting), +16.60 (from-scratch); 2.5× KV cache reduction at 128K (7.5 GB vs Full 18.6 GB); decode 1.06× Full (only sub-quadratic baseline that does NOT lose decode speed in their comparison set). Composable with GQA/MLA: `1/k` × `g/h` ≈ 128× compression at h=128 d=128 g=8 k=8. Three-stage CPT distillation recipe (summary-token adaptation with MSE+KL + parameter annealing via λ schedule + sequence-length extension) makes Qwen3-4B-base retrofittable in 85B tokens. Open-source training scripts at github.com/Kuaishou-OneRec/KSA; no checkpoints yet.

- **DeepSeek Sparse Attention (DSA, intake-506)** — DeepSeek-V3.2, arxiv:2512.02556. Two-stage: **Lightning Indexer** (FP8 head-weighted scorer with block-64 quantized key cache) → top-k=2048 token selection → MLA forward pass on selected subset. Composition is orthogonal: MLA compresses per-token KV dim, DSA selects which tokens to attend. Reports V3.2-Exp ≈ V3.1-Terminus on GSM8K/GPQA-Diamond. **PR #21149 by fairydreaming is an active draft on llama.cpp upstream** (opened 2026-03-29, last commit 2026-04-28; CPU + CUDA + Vulkan backends working); author caveat that long-context speedup not yet realized (sparse path applies to token generation only, not prompt processing — separate follow-on PR flagged). 2-models-for-1 leverage: same DSA infrastructure unlocks GLM-5.1-555B-A14B simultaneously.

- **Gist Sparse Attention (GSA + H-GSA, intake-507)** — Stanford / Emily Fox, arxiv:2604.20920. Same gist-token primitive as KSA but distinct mechanism: hard top-k chunk selection at decode + **selective unfolding** restoring raw KV pairs for selected chunks (unselected chunks fully invisible). Bounded context size at decode = k·(1+L)+M. **Hierarchical H-GSA** (gist-of-gist) achieves log-linear decode complexity — only mechanism in this cluster scaling naturally to 1M+ context on 1.1 TB RAM headroom. Reports LongBench at 32× → 44.07 vs ActivationBeacon 38.30 (+5.77). Stage 1 CPT REQUIRED; tested on Qwen2-7B + Llama3.2-1B (no 30B+, no MoE, no RULER beyond passkey). Code at github.com/yuzhenmao/gist-sparse-attention.

**Mechanism comparison axis**: KSA = persistent summaries, soft compression, larger active context per query. GSA = hard top-k + unfolding, sharp compression, smaller active context. DSA = learned indexer for top-k, integrated rather than retrofit. KSA / GSA / DSA all REQUIRE pretraining or CPT — no retrofit path for our existing Qwen production stack. Compares against our deployed retrofit methods (Attention Matching compaction intake-351, Expected Attention selection intake-288) — the retrofit-vs-integrated trade-off becomes a research question worth testing once any of the architectural mechanisms ships in llama.cpp.

**Tracked at**: [`summary-token-attention-readiness.md`](../handoffs/active/summary-token-attention-readiness.md) (joint KSA + GSA readiness stub) and [`llama-cpp-dsa-contribution.md`](../handoffs/active/llama-cpp-dsa-contribution.md) (active PR #21149 tracker with three contribution sub-tracks).

**DSA fork-side status update (historical 2026-06-20; superseded by the 2026-07-17 closeout)**: pre-fix source had `LLM_ARCH_GLM_DSA` loading tensors and falling back to **dense MLA** (no Lightning Indexer, no sparse flash-attention path), so the blocker really was the DSA path, not storage. Experimental-v7 `3dee86a5a` now routes GLM through `llama_kv_cache_dsa` and the DeepSeek32 DSA graph. The remaining open work is sparse-compute profiling and quality, not cache/runtime wiring. [DSA handoff](../handoffs/active/llama-cpp-dsa-contribution.md)

- **GLM-5.2 current-source DSA cache/runtime wiring is closed (2026-07-17)**: experimental-v7 `3dee86a5a` routes `LLM_ARCH_GLM_DSA` through `llama_kv_cache_dsa`, aliases GLM to the DeepSeek32 DSA graph, and the current-source exact smoke returned `READY` with `Lightning Indexer enabled`. That closes the wiring prerequisite only; sparse-vs-dense attention classification, current-source long-context needle/coherence, and quality remain open. [llama-cpp-dsa-contribution.md](../handoffs/active/llama-cpp-dsa-contribution.md), [glm51-reap-cpu-evaluation.md](../handoffs/completed/glm51-reap-cpu-evaluation.md), [Progress 2026-07-17](../progress/2026-07/2026-07-17.md)

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
- [intake-191](https://research.google/blog/turboquant-redefining-ai-efficiency-with-extreme-compression/) TurboQuant -- Extreme KV cache compression (3-4 bit with Hadamard)
- [intake-192](https://arxiv.org/abs/2502.02617) PolarQuant -- Polar transformation for KV quantization
- [intake-193](https://arxiv.org/abs/2406.03482) QJL -- 1-bit quantized JL transform for KV cache, zero overhead claim
- [intake-256](https://arxiv.org/abs/2604.01178) Multiscreen Attention -- Screening architecture replacing softmax attention
- [intake-284](https://arxiv.org/abs/2604.04921) TriAttention paper -- Trigonometric KV scoring, Song Han lab
- [intake-287](https://arxiv.org/abs/2603.11504) LongFlow -- Attention-weighted value norm scoring (downgraded)
- [intake-288](https://arxiv.org/abs/2510.00636) Expected Attention paper -- Gaussian MGF scoring, KVPress library
- [intake-289](https://github.com/microsoft/memento) Memento paper -- Dual KV stream, block masking, Microsoft Research
- [intake-292](https://arxiv.org/abs/2503.06692) InftyThink (ICLR 2026) -- Iterative reasoning compression
- [intake-293](https://arxiv.org/abs/2602.06960) InftyThink+ -- RL-learned adaptive compression
- [intake-294](https://arxiv.org/abs/2602.03249) Accordion-Thinking -- Fold/unfold runtime toggle
- [intake-350](https://github.com/CuriousCaliBoi/latent-briefing) Latent Briefing -- Broken (PGD no-op, Ridge no-op, do NOT use)
- [intake-351](https://arxiv.org/abs/2602.16284) Attention Matching paper (2602.16284) -- Closed-form KV compaction, MIT
- [intake-352](https://arxiv.org/abs/2510.12872) KVCOMM (NeurIPS'25) -- Cross-context KV sharing for homogeneous pools
- [intake-708](https://www.arxiv.org/html/2606.07878v1) Still: Amortized KV Cache Compaction in a Single Forward Pass (arXiv 2606.07878) -- per-layer Perceiver, forward-KL distillation, amortized synthesis (the third compaction category), position-free via inverse-RoPE; no public code as of 2026-06-05

## KV admission / eviction cluster + cluster-wide gate (2026-05-19)

Five May 2026 papers spanning write-time admission, read-time eviction, per-head budget allocation, workflow-aware residency, and reasoning-domain oracle distillation. Deep-dive verdict: **PBKV is the strongest near-term EPYC fit; SP-KV is empirically refuted; landing a StreamingLLM baseline first is a cluster-wide gate for prioritization**.

**SP-KV** (intake-538, arxiv:2605.14037, FAIR — Jégou/Douze/Yih) — jointly trained lightweight utility predictor decides at write time whether each KV pair is admitted to the long-term cache; recent-window keeps short-range pairs locally available. 3-10× KV cache reduction with little/no validation-loss degradation. **Tier-2b refutation**: arxiv:2601.14279 (Steele) shows a 1.7M-param learned scorer (SIP) fails to beat trivial position-based heuristics (keep first 4 + last N) across 5 seeds × 4 retention levels × 3 tasks. SP-KV is exactly the KV-only, query-agnostic write-time scorer Steele targets. Independent corroboration from ForesightKV (below): pure learned predictor degrades LM loss on low-entropy tokens, hence the two-stage Supervised+GRPO recipe.

**KVP** (intake-551, arxiv:2602.10238, Moschella/Manduchi/Sener) — per-head RL agents trained offline on pre-computed generation traces using only K/V vectors. No LLM weight modification. Generalizes zero-shot to longer contexts and unseen tasks. The ONLY cluster paper that explicitly compares to StreamingLLM (per-head specialization is the axis SP-KV doesn't exploit).

**LU-KV** (intake-552, arxiv:2602.08585, Tang et al.) — global combinatorial optimization for per-head budget allocation via convex-hull relaxation + marginal-utility greedy solver. 80% KV reduction at minimal performance degradation on LongBench/RULER. **Static profile after offline training** — fits our frozen-weights constraint. Strongest frozen-weights attention-kernel candidate.

**ForesightKV** (intake-553, arxiv:2602.03203, Dong et al.) — distills a "Golden Eviction" oracle (future-attention scores) via supervised Pairwise-Ranking, then GRPO RL on LM loss. Outperforms prior eviction methods at half the cache budget on reasoning benchmarks (AIME 2024/2025). Requires LLM fine-tuning — collides with frozen-quant constraint until DGX Spark lands.

**PBKV** (intake-554, arxiv:2605.06472, Zheng et al., CC-BY 4.0) — **standout for EPYC orchestrator**. Operates at the **workflow/orchestrator residency layer**, not the attention kernel. History-conditioned next-agent-invocation predictor drives KV residency decisions. 1.85× over LRU on dynamic workflows, 1.26× over KVFlow on static. Maps directly onto frontdoor → coder/worker hand-off pattern where shared long prompts pay BW-bound re-prefill cost. **No fine-tuning needed.** Requires tiny next-agent predictor + llama.cpp prefix-cache hooks (soft-depends on RadixAttention prefix-tree work in `llama-cpp-fork-rebase.md`).

**KVFlow** (intake-1196#01, arXiv:2507.07400, Pan et al., UCSD + AWS) — **the ORIGIN of workflow-aware KV
residency, and the paper PBKV's 1.26× is measured against.** Recorded here in its own right because our
index previously carried it only as PBKV's denominator, which inverted the reading for our own use case.
Peer-reviewed at **NeurIPS 2025**, with an Apache-2.0 implementation released. An Agent Step Graph yields a
per-agent *steps-to-execution* value propagated into the KV radix tree: the value lands on the last node of
each agent's fixed prompt, internal nodes take the **minimum** across children, dynamic suffixes always get
highest eviction priority, and conflicts at nodes shared between concurrent workflows resolve to the most
conservative priority.

Three things to carry, all from a source-level dive:

- **The camera-ready prices the portable half at 1.11×.** Its optimization breakdown — present only in the
  NeurIPS version — gives workflow-aware eviction *alone* an average **1.11×**; the jump to 1.29× comes from
  overlapped prefetching, which does **not** port to our stack (llama-server slot save/restore runs on the
  shared task loop and a failed restore is destructive). **1.11× is the honest ceiling for us.**
- **An arXiv version check is not a version check.** arXiv has exactly one version of this paper, so a
  freshness check passes while the version of record diverges underneath it. The NeurIPS camera-ready
  deleted a testbed, added a baseline and a limitations section, and changed the body's headline numbers.
  For any paper with a venue, fetch the proceedings separately.
- **PBKV's 1.26× is on STATIC workflows — KVFlow's design centre.** A 1.26× increment there means KVFlow
  retains most of the available gain on *declared* topologies, which is exactly what our delegation path is
  (`compute_waves()` already computes a cycle-checked wave index that **is** a steps-to-execution value).
  Filing KVFlow as "beaten" inverts the reading for the one workload where we would actually use it. Note
  also the asymmetry in what our index recorded: PBKV is an undived preprint, KVFlow is peer-reviewed.

**Do not quote 1.83× or 2.19×** as the value of workflow-aware eviction: 1.83× is the full system on
hardware we do not have and its stated configuration was removed from the version of record, and 2.19× is
an arithmetic ratio (1.25/0.57) against a HiCache version that no longer exists.

**Cluster-wide gate** — [`streaming-llm-baseline.md`](../handoffs/active/streaming-llm-baseline.md) (master P#45 MED): land a clean sink + sliding-window baseline in `epyc-llama` to measure the **easy-floor** any KV reduction method must beat. Of the 5 papers above, only KVP explicitly compares to StreamingLLM. Without an internal floor, LU-KV / KVP / ForesightKV gain rankings are unanchored against the simplest competing technique. Gate criteria flip cluster prioritization: if StreamingLLM at 50% budget preserves ≥95% accuracy on representative workloads, **demote** attention-kernel methods (LU-KV/KVP/ForesightKV) — their incremental gain over the floor is too small to justify kernel work. PBKV stays prioritized because it operates at the orchestrator layer and **composes with** sink+window rather than replacing it.

**Sources**: [intake-538](https://arxiv.org/abs/2605.14037) SP-KV · [intake-551](https://arxiv.org/abs/2602.10238) KVP · [intake-552](https://arxiv.org/abs/2602.08585) LU-KV · [intake-553](https://arxiv.org/abs/2602.03203) ForesightKV · [intake-554](https://arxiv.org/abs/2605.06472) PBKV · [Steele falsification](https://arxiv.org/abs/2601.14279) · [Deep-dive](../research/deep-dives/2026-05-19-kv-admission-cluster.md) · [StreamingLLM baseline gate](../handoffs/active/streaming-llm-baseline.md) · [intake-1196#record](https://arxiv.org/abs/2507.07400) KVFlow (NeurIPS 2025; cite the proceedings, not the preprint) · [prefix-cache ownership + KV rows](../handoffs/active/attention-matching-kv-compaction.md)

## Per-slot context is a hard split, and "safer KV quant" can cost more memory (2026-08-03)

Two measured corrections that change how KV budgets are reasoned about on this fleet.

**`-c` is not what a request gets.** llama.cpp carves the KV cache into `-np` fixed slots at launch,
so the effective per-request limit is `-c / -np`. A single stream does **not** grow into unused slots
on this build (no unified KV cache), and overflow is a hard `HTTP 400
exceed_context_size_error`, never a queue and never a reroute. Verified on three live shapes, with
the server reporting its own limit:

| `-np` | `-c` | c/np | prompt sent | result |
|---:|---:|---:|---:|---|
| 16 | 262144 | 16,384 | 29,121 | 400, `n_ctx=16384` |
| 4 | 262144 | 65,536 | 116,501 | 400, `n_ctx=65536` |
| 8 | 65536 | 8,192 | 14,561 | 400, `n_ctx=8192` |

Consequence: a role with heterogeneous instances has heterogeneous *capability*. The same request
succeeded or failed depending only on which frontdoor instance took it, because `:8070` (`-np 16`)
offered 16,384 tokens while `:8080` (`-np 4`) offered 65,536.

**The safe pure-attention KV config can be a memory REGRESSION.** For a model at 260 KiB/token f16
(split evenly K/V):

| config | K | V | KiB/token |
|---|---:|---:|---:|
| f16 / f16 | 130 | 130 | 260 |
| q8_0 / q8_0 | 65 | 65 | **130** |
| q4_0 / f16 | 32.5 | 130 | **162.5** |
| q4_0 / q4_0 | 32.5 | 32.5 | 65 |

`-ctk q4_0 -ctv f16` is the documented safe production config for pure-attention models, and it uses
**more** memory than `q8_0/q8_0` — quantising K hard while leaving V at f16 costs more than
quantising both moderately. On a VRAM-constrained card the memory-optimal *safe* point is
`q8_0/q8_0`, not the "more aggressive" asymmetric config. Only `q4_0/q4_0` saves further, and that is
the config that produces garbage at 32K on pure-attention models — so the saving is gated on
architecture, not on willingness to trade quality.

_Sources: `progress/2026-08/2026-08-03.md`; `handoffs/active/autopilot-continuous-optimization.md`;
`handoffs/completed/kv-cache-quantization.md`; live probes of `:8070`/`:8080`/`:8083` on
production-consolidated-v8._

## Compiled Update — 2026-08-22: the KV-quant program closed because V-dequant, not K, is the CPU cost — and every exotic lost a fair rematch

**Confidence: verified** — everything below is landed, measured and decided inside the COMPLETED
[`kv-cache-quantization.md`](../handoffs/completed/kv-cache-quantization.md) handoff (closed 2026-03-28: Hadamard Phase 1
cherry-picked to production as `b51c905` on `production-consolidated-v2`, 10 files / +141 lines, later superseded by upstream
PR #21038 auto-rotation; TurboQuant / PolarQuant / QJL / hybrid buffer ABANDONED, each on a measured gate, not by fiat). This
pass compiles the closure fine-structure the page never carried: the headline results (Hadamard+q4_0 quality-neutral, hybrid
buffer memory-negative, the 2.2× ikawrakow speed confirmation) were compiled long ago and are not repeated here.

### V dequantization is the ENTIRE CPU flash-attention prefill cost; K dequantization is free

The page has so far motivated the asymmetric production config (`-ctk q4_0 -ctv f16` on pure-attention models) purely as a
*quality* margin. The handoff's 2026-03-28 root-cause section establishes it is equally a **speed** decision, with a clean
4-config isolation on Coder-32B Q4_K_M at 4K context:

| config | time/chunk | vs f16/f16 | reading |
|---|---:|---:|---|
| f16 / f16 | 37.91 s | baseline | — |
| **q4_0 / f16** | **37.42 s** | **−1%** | K dequant is FREE — bandwidth saving offsets cost |
| q8_0 / f16 | 40.57 s | +7% | q8_0 K simply reads more bytes than q4_0 |
| q8_0 / q4_0 | 64.87 s | **+71%** | **V dequant is the entire bottleneck** |

Mechanism: the K path runs a fused `kq_vec_dot` (dequant+dot in one pass) while the V path runs `v_to_float` → materialized
f32 buffer → `vec_mad_f32`; f16 V instead uses the native single-pass `ggml_vec_mad_f16`. The Phase-0 sweep shows the same
thing at scale — Coder-32B 16K prefill: f16/f16 **111.1** t/s, q4_0/q4_0 46.6, q8_0/q4_0 48.9, **q8_0/q8_0 34.0 t/s
(3.3× slower)** — while *decode* is unaffected in every config (~8.5–9.5 t/s across all cells; at batch-1 the KV read is
tiny next to ~18 GB of weight reads). On the hybrid 35B-A3B (25% attention layers) KV quantization is entirely free at
4K–65K, all configs within noise: the SSM layers amortize the dequant away.

**Reconciliation with the 2026-08-03 section above**: that section is correct that `q8_0/q8_0` is the *memory*-optimal safe
point (130 vs 162.5 KiB/token) — but on the CPU flash-attention path it is also the **worst prefill config measured**,
because it pays V-dequant on every tile, while the "memory-regressive" `q4_0/f16` is prefill-free (−1%). The two sections
answer different objectives (VRAM ceiling vs CPU prefill throughput); neither dominates, and a config choice must name which
axis it is optimizing. The 2026-08-14 GPU falsification on the [Quantization](quantization.md) page (KV-quant −16.7%/−6.9%
at 64k) is the same cast-cost mechanism showing up on the other substrate.

### Hadamard's isolated contribution, quantified — and the exotics' exact causes of death

**Hadamard rotation closes 70% of the bare-q4_0 quality gap.** The page carries the +0.017 endpoint but never the
comparison that prices the rotation itself (Coder-32B, 50 chunks, n_ctx=512): q4_0/q4_0 *plain* is **+0.055** PPL vs f16;
q4_0/q4_0 **+ Hadamard is +0.017** (3.56× K compression); q8_0/q4_0 + Hadamard is **−0.010 — quality-neutral** at 2.46×;
throughput overhead at 4K is zero (11.58 vs 11.45 t/s, within noise).

**TurboQuant was abandoned on a fair test, after the handoff itself flagged its first gate as unfair.** The original
decision gate tested one of four ecosystem fixes (norm correction only) on Qwen2.5-7B — squarely inside TQ3's measured
failure zone, since TQ3 quality is **model-size dependent** (Qwen3-0.6B: PPL **1216** vs f16 13.51, catastrophic; 8B: worse
than Hadamard+q4_0; 35B+: approaches f16 — head_dim=128 only gaussianizes with enough coordinates). The handoff recorded
"why we stopped too early", then re-ran fairly: **Coder-32B with norm correction still lost — TQ3 +5.9% PPL (1.4676) vs
q4_0's +0.001% (1.3875)** — and only then declared ABANDONED. Norm correction itself is real (77% gap reduction on 7B, PPL
9.017 → 2.13; beats q8_0 by 1.17% in spiritbuun's CUDA fork) but insufficient. This is the closure discipline worth copying:
the verdict survives because the gate's own weakness was found and removed before the decision was made final.

**QJL died on arithmetic, not implementation.** The custom XNOR+popcount attention kernel worked mechanically, but the
sign-bit estimator at S=256, d=128 has **SNR ≈ 1.13** — noise ≈ signal for the small Q·K scores that dominate a PPL
aggregate (PPL ~15–16K, unusable). Adding the paper's top-8 outlier correction lifts effective storage to ~6 bits/element,
**at which point plain q8_0 (8 bits, trivial) wins on quality-per-complexity** — the compression advantage evaporates
exactly when the method starts working. The paper's remaining viability path is a full-precision recency buffer for the
most-attended recent tokens — i.e. the hybrid-precision buffer this handoff independently built and measured as
memory-negative. PolarQuant's +0.229 PPL at 3.1 effective bits completes the set.

### Residual validated facts worth keeping on the record

- **Spec-decode composes with quantized KV**: speculative decoding + q8_0/q4_0 measured **19.15 t/s (+3.3% vs f16)** on
  Coder-32B — the R9 interaction risk closed positive, not merely neutral.
- **A standing small-GQA hazard**: q4_0 K on Qwen2.5-7B-f16 (4 KV heads, `n_embd_k_gqa=512`) produces PPL 2642 (garbage) on
  BOTH experimental and production binaries while q8_0 K is fine; all production models (8+ KV heads) are unaffected; root
  cause never found. Any future ≤4-KV-head model must re-run the q4_0-K gate before inheriting the production config.
- **Ecosystem bug watch-list for anyone touching WHT/KV code**: WHT normalization must be `1/sqrt(block)` not `1/block`
  (garbage PPL otherwise); store V non-transposed and transpose in-graph (block-quant crash otherwise); apply WHT during
  quantization (`set_rows`), never graph-side (PPL 23.5 vs 6.2); CPU dequant targets F32 only.
- **Reconciliation — the 2026-07-20 monitor row above is retired**: upstream PR #21089 (TBQ3_0/TBQ4_0 CPU TurboQuant KV),
  listed above as "remain open/monitor" and as an Open Question, was **CLOSED UNMERGED upstream on 2026-06-02** (GitHub API:
  `state closed`, `merged false`, verified 2026-07-29, re-verified 2026-08-21). No TBQ code entered the local tree. The
  question "does #21089 merge and beat Hadamard+q4_0?" is answered: no, and there is nothing left to monitor on that PR.

### Source References

- [`kv-cache-quantization.md`](../handoffs/completed/kv-cache-quantization.md) — the closed handoff: V-dequant root-cause table, Phase-0/1/3b/3c results, TQ3 model-size dependence and fair 32B retest, QJL SNR post-mortem, spec-decode validation, the 4-KV-head q4_0-K bug.
- [`tq3-quantization-evaluation.md`](../handoffs/active/tq3-quantization-evaluation.md) — the verified PR #21089 closed-unmerged state (2026-08-21 re-check) that retires this page's 2026-07-20 monitor row.
- [llama.cpp issue #20977](https://github.com/ggml-org/llama.cpp/issues/20977) — the upstream TurboQuant feature request the revisit criteria were pinned to (cited by the handoff).
- [ik_llama.cpp issue #1509](https://github.com/ikawrakow/ik_llama.cpp/issues/1509) — ikawrakow's independent EPYC 9975 confirmation runs (Hadamard+q4_0 better quality AND 2.2× faster than TQ3), the external anchor for the abandonment.
- [intake-193](https://arxiv.org/abs/2406.03482) QJL — the paper whose S=512 / recency-buffer requirements the SNR post-mortem quantifies against our S=256 implementation.

## Compiled Update — 2026-08-23: the orchestrator prefix-cache path is owned, its three latent defects fixed, and its measurement plan filed

**Confidence: verified** — committed orchestrator fixes with regression tests, read-only artifact archaeology on the slot-save path, and the closed KV-5 row whose wiki correction was already compiled in this page's 2026-05-19 section (not restated below, only pointed to).

### KV-5 closed 2026-08-20 — the KVFlow correction is already on this page

The KV-5 row ("correct `wiki/kv-cache.md`") was closed in the 2026-08-20 wrap-up wiki sweep: KVFlow is recorded above in the 2026-05-19 section as the **ORIGIN of workflow-aware KV residency** — NeurIPS 2025 venue, its own 1.11× eviction-only ablation as the honest portable ceiling, the arXiv-version-check trap, and the PBKV-1.26×-is-on-static-workflows reading. Nothing new to add; the pointer is kept so the row's closure is traceable. [attention-matching-kv-compaction.md](../handoffs/active/attention-matching-kv-compaction.md) §KV-5, commit `508eaeb0`.

### The ownership gap is closed: the prefix-cache path now has an owner

No ACTIVE handoff owned the orchestrator prefix-cache path. The original owner, [`radix-attention.md`](../handoffs/archived/radix-attention.md), is **archived "VERIFIED 2026-01-09"** with its Next Steps stopping at *"Integration testing with live llama-server"* — the integration was never done. `repl-turn-efficiency.md` touched `PrefixRouter` only incidentally. The attention-matching handoff adopted the rows (filed there because nothing else owned them); re-home if a better owner appears.

### Three latent defect fixes (KV-0a/b/c, committed 2026-08-20) — all three were silently wrong in production

- **KV-0a — every KV slot save was failing.** `prefix_cache.py` built the filename with `os.path.join(...)`, producing a `/`-containing string that llama-server rejects via `fs_validate_filename(allow_subdirs=false)` before it concatenates `--slot-save-path`. Proof it never worked: the 75 retained slot artifacts on disk are **all** `kv_migrate_*` from the sibling `concurrency_aware.py` path, with **zero** `slot_<id>_<hash>.bin` files anywhere. Two compounding defects fixed alongside: the restore path did a **client-side** `os.path.exists()` on a **server-side** filename, and both backend methods caught `httpx.RequestError`, which does **not** cover `HTTPStatusError` — so a 4xx propagated instead of returning `False` as documented. Fixed by emitting a bare filename (`_slot_state_filename`, mirroring `concurrency_aware._slot_filename`).
- **KV-0b — roles sharing one llama-server were evicting each other, unobservably.** Under `shared_with`, several roles resolve to one physical server, but the legacy loop built a **separate `PrefixRouter` per role**, each allocating `id_slot` in `[0, num_slots)` from its own private LRU — so two roles both emitted `id_slot=0` and silently clobbered each other. Now one router per physical URL (`_router_for`), matching the shape the fleet layer already had. 3 regression tests added.
- **KV-0c — `radix_cache.py` deleted** (480 lines + shim). Verified dead: its only two importers were the file importing itself. It also carried an unexercised stale-slot bug and a docstring claiming path compression it did not implement. The 20 tests that exercised the unwired module went with it — green tests over dead code manufacture exactly the false confidence this work exists to avoid.

### The measurement plan (KV-1..KV-4, KV-6) — mostly zero-inference, all from existing logs or one-line changes

- **KV-1 (gates everything below): count DISTINCT hot prefixes per window against resolved slot count, per role and per shared server, from existing logs. ZERO INFERENCE.** Production `num_slots` is **2**; `coder_primary` and `coder_escalation` both declare `slots: 1` — **at slots=1 there is no eviction order to improve**, and at 2 it is a coin flip. The row was named in two consecutive passes with an unchanged blocker — by the recurrence rule that is proof it was never blocked. Do it before anything else here.
- **KV-2: pass `role` and `session_id` into `PrefixRouter.get_slot_for_prompt`.** Both are already present at the call site (`model_server.py:91` requires `role`; `inference.py:755-767` attaches the session id) and the router receives **only prompt text** — the router is discarding for free the identity signal KVFlow had to invent a client-ID scheme to recover.
- **KV-3: evaluate llama.cpp's NATIVE token-level LCP slot selection.** It is strictly better than a 256-char SHA-256 exact match, already shipped, and currently **overridden** rather than off: `slot_prompt_similarity` defaults to `0.1f`, but our explicit `id_slot` takes tier-one priority ahead of it (`server-context.cpp:1541` before `:1549`). Config + call-site change, no kernel work. **Gated on KV-1 and on the shared-router fix having landed.** Note our Python hit-rate counter is a proxy for a quantity it does not measure — `n_past` is decided in C++.
- **KV-4: IF KV-1 shows working set > slot count, THEN consider workflow-aware eviction** — replace the LRU victim choice with an argmax over steps-to-execution, sourced from the delegation DAG that already exists (`parallel_step_executor.py:75` `compute_waves()` — the wave index **is** a steps-to-execution value, already cycle-checked; `routes/delegate.py:86-98` enumerates the whole plan at `dry_run=True` for zero LLM calls). **Ceiling recorded on the row: 1.11×** — KVFlow's own eviction-only ablation; the other 1.18× comes from prefetching we cannot port (llama-server slot restore is on the shared task loop and a failed restore is destructive). **NOT the RLM tree and NOT the autopilot loop** — neither materialises children in advance.
- **KV-6 (filed 2026-08-20): measure `canonicalize_prompt` before optimising anything downstream of it.** It makes **SEVEN full-length passes** (3 string scans + 4 `re.sub`) over prompts of tens of KB and then **discards everything past char 256**. It has NEVER been measured: grepping both prefix-cache files for timing primitives returns 3 hits, all docstring prose, zero code. Cheap to instrument, and it may dominate the routing cost the rest of the rows are trying to improve.

### Source References (2026-08-23)

- [attention-matching-kv-compaction.md](../handoffs/active/attention-matching-kv-compaction.md) — the ownership filing, the KV-0a/b/c fixes with their commit record, the KV-1..KV-6 rows, and the KV-5 closure
- [progress/2026-08/2026-08-20-research-intake.md](../progress/2026-08/2026-08-20-research-intake.md) — the intake round that surfaced the prefix-cache findings (KVFlow dive, SGLang Rust tree-core cluster)
- [radix-attention.md](../handoffs/archived/radix-attention.md) — the archived original owner of the prefix-cache path, whose integration step was never done
- Commits `508eaeb0` (KV-5 wiki close) and `c75a2f68` (KV-0a/b/c checkbox record + KV-6 filing) on this repo

---

## Compiled Update — 2026-08-23 (evening): KIVI's "primary quality gap" was never a gap; the real gap is an instrument gap

**Confidence: verified** — the KIVI correction is a read of `llama-kv-cache.cpp` / `llama-context.cpp` at frozen v9 against arXiv:2402.02750 v2 in full; the granularity correction reads the alignment-collapse study (arXiv 2606.09864) against our own layout; the monitoring gates G2-G5 are filed, not run.

### The KIVI "per-channel K / per-token V" gap is closed as a misread — all three load-bearing parts are wrong

The completed KV-quant handoff had claimed llama.cpp's symmetric block quantization leaves KIVI's per-channel-K / per-token-V unimplemented ("the primary quality gap"). The Stage-2b dive (arXiv:2402.02750 v2, read in full) shows that claim wrong on all three parts:

1. **Per-token V is already implemented, and structurally unavoidable.** `llama-kv-cache.cpp:231-232` allocates K and V with dim0 = channels, dim1 = tokens, so a 32-element q4_0/q8_0 block spans 32 contiguous channels *within one token* — exactly KIVI's per-token grouping at G=32. And quantized V forces flash-attention (`llama-context.cpp:3557` refuses to start otherwise), which sets `v_trans = false` — **our quantized V can never be on KIVI's bad axis.**
2. **Per-channel K is outside KIVI's demonstrated scope.** KIVI's own OB 1 says per-token quantization of *both* caches maintains accuracy at INT4; the axis asymmetry is established **only at 2 bits**, and we never run 2-bit KV.
3. **We solve the key-outlier problem a different way.** The orthonormal self-inverse Walsh-Hadamard rotation (`llama-kv-cache.cpp:319-336`) mixes across head channels — the exact dimension KIVI's outliers live on. RotateKV (arXiv 2501.16383, no author overlap) uses per-token keys plus rotation at 2 bits and states verbatim it "offers superior outlier management compared to per-channel approaches".

The one residual difference is real and cheap to test: KIVI's quantizer is **asymmetric** (zero-point + scale) where q4_0/q8_0 are symmetric — but q4_1/q5_1 are supported asymmetric KV types, so it is a flag, not a code change; a rotated distribution is near zero-mean, which predicts the asymmetric quantizer buys nothing (falsifiable in one short A/B).

**THE REAL GAP IS AN INSTRUMENT GAP, NOT AN IMPLEMENTATION ONE.** KIVI reports no perplexity at all and rejects single-decode-step metrics; its own data show why — on Llama-2-7B the same 2-bit damage costs CoQA 7% but collapses GSM8K by 57% (13.50 → 5.76). **Our entire first-party quality case for quantized KV is perplexity plus needle-in-a-haystack — precisely the instrument class that survives multi-step damage. No GSM8K-class generation eval has ever been run against quantized KV in this repo** (gate G3 in `tq3-quantization-evaluation.md`).

### The dual-cache conclusion is REFRAMED: a capacity argument applied to a bandwidth problem

The completed handoff's "dual cache = more bytes resident = wrong" conclusion does not generalise the way it has been read. It is sound only when both copies sit in the **same** memory tier and the cheap copy is **dequantized on the read path** — ours did both, which is why it lost (the ~30% gen-speed gap is the `q4_0 → f16` cast on every decode token: a *dequantization* cost, not a *capacity* cost). **A dual-cache design whose second copy lives in a cheaper tier (host DDR5, slower NUMA node) and is never dequantized into the attention hot path is a different design, not refuted by anything measured here.** Same-tier plus dequantize-on-read is memory-negative AND bandwidth-negative; that is the narrow, citable claim. Do not cite the paragraph to close a tiering proposal.

### Granularity correction — we are FINER than the published mitigation, on the OPPOSITE axis from KIVI

Two facts keep being conflated because both are called "grouping": (1) **granularity** — ours is group-**32** per token (with `-fa 1`, blocks run along the channel dimension, dim0 = channels / dim1 = tokens), while the alignment-collapse study (arXiv 2606.09864) *recommends* Group-**64** as a mitigation; we are already finer than its remedy, by default, everywhere, so **its headline damage figures are a pessimistic bound for us, not a matched estimate**; (2) **axis** — KIVI's prescription is per-channel for K; ours is per-token for both, and quantized V is *structurally incapable* of landing on KIVI's bad axis. Same word "group", orthogonal dimension. Any transfer of a third-party grouping-damage number to this stack must state which axis the grouping runs along (gates G4/G5 in `tq3-quantization-evaluation.md` replace transfers with our own numbers).

### The 2026-08-23 KV-quant monitoring gates (filed, not run — both compute planes were held elsewhere)

- **G2 — measure our actual KV outlier ratio** on the 10 full-attention layers only (a quarter of the frontdoor's 40 layers by construction; report as such): capture K after QK-norm and after RoPE, V at cache-write, ~200 prompts; report per layer and per head, K and V separately, max/median and max/p99.9. A pooled max÷median is NOT the measurement. **Gate:** if V's max/median materially exceeds K's, `-ctv` is the risk surface; if both are < ~50×, close the massive-activations line for this stack as measured-and-negative.
- **G3 — close the instrument gap**: GSM8K-class multi-step generation eval at f16 vs q8_0/q8_0 vs q4_0/q4_0 KV, rotation ON, one pure-attention + one GDN hybrid model, per-question persisted. Gate: reasoning delta outside noise with PPL/NIAH flat = KIVI's instrument finding replicated first-party.
- **G4 — paired behavioural drift (IFEval, FP16-anchored CondFlip)**, N≥250, one model, sweeping `-ctk`/`-ctv` over five configs. CondFlip > 5% while PPL drift < 2% ⇒ a behavioural gate becomes mandatory before any future KV-default change. All configs < 2% ⇒ group-32 granularity is doing the work and PPL+NIAH was retrospectively adequate.
- **G5 — reproduce KIVI's Figure 2/Table 2 on our architecture** (per-channel key magnitudes, with/without `LLAMA_ATTN_ROT_DISABLE=1`, per-group max/RMS at G=32). Gate: near-flat rotated ratio ⇒ redundancy conclusion first-party; surviving outliers make rotation placement (pre- vs post-RoPE, B1) live. Nobody has measured whether key-channel outliers even exist under per-head QK-RMSNorm — KIVI's ablated models all predate QK-norm.
- **H11 (Z, recorded)** — the frozen tree carries **none** of the three mitigations the massive-activations literature assumes: no per-channel scaling (`cpy_k`/`cpy_v` are pure `ggml_set_rows`), no clipping (zero `clip`/`clamp` in `llama-kv-cache.cpp`), no attention-sink special-casing (sinks exist only as a softmax bias in the graph — "llama.cpp has sinks" ≠ "llama.cpp protects sink tokens from quantization"). The one mitigation we carry is the Walsh-Hadamard rotation — exactly the lever G5 probes.
- **Massive-activations deprioritisation (record, not task):** our ρ = 4 hybrid (10 of 40 layers full attention) shows the **smallest** massive activations of every hybrid the paper (arXiv 2608.12149) measured — peak first-token magnitude 30 vs Kimi-Linear 180–240 and Nemotron-H 750–1800, and ratio does not explain the gap: output gating on the full-attention layers is the dominant attenuator, and our family ships it natively (`src/models/qwen35moe.cpp:349-354`). The paper contains no quantization experiment and no median anywhere, so no dynamic-range ratio can be computed from it — that is exactly why G2 exists. Deprioritise, do not close; never re-open this line from an abstract.

### Source References (2026-08-23 evening)

- [`kv-cache-quantization.md`](../handoffs/completed/kv-cache-quantization.md) — the KIVI correction (all three load-bearing parts), the dual-cache capacity-vs-bandwidth reframing, the R9 warrant repair, the group-32/axis granularity correction
- [`tq3-quantization-evaluation.md`](../handoffs/active/tq3-quantization-evaluation.md) — gates G2/G3/G4/G5 and B1/B2 with their named open/close criteria, H11 static read, the massive-activations deprioritisation record, the PR #21089 closed-unmerged re-verification
- [`speculative-decoding-mtp-refresh.md`](../handoffs/active/speculative-decoding-mtp-refresh.md) — G3: quantized-KV spec-decode bandwidth-positive only at `draft_max = 1` on MI210 (see [Speculative Decoding](speculative-decoding.md))
- [KIVI arXiv:2402.02750](https://arxiv.org/abs/2402.02750) / [RotateKV arXiv 2501.16383](https://arxiv.org/abs/2501.16383) / [arXiv 2606.09864](https://arxiv.org/abs/2606.09864) / [arXiv 2608.12149](https://arxiv.org/abs/2608.12149) — the corrected external evidence base

## Compiled Update — 2026-08-23 (wave-2 research intake): the KIVI "primary quality gap" never existed, our KV blocks are finer than the published mitigation, and slot-restore loss is conditional

**Confidence: verified** — every statement below about our own tree is a read-only inspection of frozen
`production-consolidated-v9` (`0db32c06e3e550065b78311a6031ef3dd2c4f27c`) with file:line loci, reproduced
independently by three separate Stage-2b dives. Every third-party figure is dive-verified against its
primary source and is labelled as third-party. Under [MEASUREMENT.md](../MEASUREMENT.md) **no external
number here gates a stack change**; each is a hypothesis, and the tests are filed on
[`tq3-quantization-evaluation.md`](../handoffs/active/tq3-quantization-evaluation.md) and
[`speculative-decoding-mtp-refresh.md`](../handoffs/active/speculative-decoding-mtp-refresh.md).

### The "primary quality gap" at `kv-cache-quantization.md:320` never existed — and it was wrong in three independent ways

The standing first-party claim was: *"llama.cpp's current q4_0/q8_0 KV does symmetric block quantization
— KIVI's per-channel K / per-token V is NOT implemented. This is the primary quality gap."* A Stage-2b
dive read KIVI (arXiv:2402.02750v2, ICML 2024) in full against the frozen tree and **retired it**
(`intake-1286#record`, dive-verified 2026-08-22, credibility 4/HIGH).

- **Per-token V is already implemented, and is structurally unavoidable once V is quantized.**
  `src/llama-kv-cache.cpp:231-232` allocates K and V with **dim0 = channels, dim1 = tokens**, so a
  32-element `q4_0`/`q8_0` block spans 32 contiguous *channels within one token* — precisely KIVI's
  per-token grouping at G=32. `v_trans = !cparams.flash_attn`, and `src/llama-context.cpp:3557` refuses
  to start with *"quantized V cache requires flash_attn to be enabled"*. **So whenever V is quantized,
  `v_trans` is false and V is channel-contiguous: our quantized V can never land on KIVI's bad axis.**
  The only configuration that would transpose V is the one where V is f16 and unquantized. This half of
  the old claim was simply false.
- **The K half is outside KIVI's demonstrated scope.** KIVI's own **OB 1** states that at INT4,
  per-token quantization of *both* caches maintains accuracy; the axis asymmetry is established **only
  at 2 bits**, and the paper runs **no 4-bit and no 8-bit axis ablation** — so it licenses no conclusion
  in either direction at the bit widths we serve. Production runs q8_0/q8_0, q4_0/f16 and q4_0/q4_0,
  never 2-bit. KIVI's own Table 3 4-bit per-token/per-token rows match or exceed FP16 CoQA on three of
  four models (Llama-2-7B 64.82 vs 63.88; Llama-2-13B 66.73 vs 66.37; Mistral-7B 67.80 vs 67.40).
- **We solve the key-outlier problem a different way, and an independent source says that way works.**
  The orthonormal self-inverse Walsh-Hadamard rotation gated at `src/llama-kv-cache.cpp:319-336`
  (`ggml_is_quantized(type)` && `n_embd_head % 64 == 0`, defeatable by `LLAMA_ATTN_ROT_DISABLE`) and
  applied at `src/llama-graph.cpp:2713-2720` mixes across **head channels** — the exact dimension KIVI's
  outliers live on — redistributing a magnitude-*m* outlier as *m*/√n so every 32-channel group ends up
  with comparable dynamic range. RotateKV (arXiv:2501.16383v2, Su et al., **no author or institutional
  overlap with KIVI**) uses **per-token keys plus rotation** at 2 bits and states verbatim that it
  "offers superior outlier management compared to per-channel approaches", reaching <0.3 PPL degradation
  on Llama-2-13B and <1.7% GSM8K degradation. **Per-channel keys are one remedy for channel outliers,
  not a requirement.**

**The one residual difference is real, small and cheap to test.** KIVI's quantizer is **asymmetric**
(zero-point *z* = min X, scale *s* = (max X − min X)/(2^B − 1)) where `q4_0`/`q8_0` are **symmetric**
(scale only). That half of the old sentence was accurate — but `q4_1` and `q5_1` are supported
**asymmetric** KV cache types, so this is a **flag, not a code change**. A Hadamard-rotated distribution
is near zero-mean and near-symmetric, which predicts the asymmetric quantizer buys nothing here; that
prediction is directly falsifiable in one short A/B, filed on the TQ3 handoff.

Two honest limits, neither of which reinstates the gap. First, this is a **mechanism argument plus one
third-party paper**, so it retires a *claim* and licenses no config change. Second, RotateKV's own Table 7
builds its 2-bit result on plain QuaRot rotation **plus** outlier-aware channel reordering **plus**
pre-RoPE rotation, implying a plain rotation is not sufficient *at 2 bits*; our fork applies a plain
**post-RoPE** Hadamard (the K-shift path at `src/llama-kv-cache.cpp:1874-1888` confirms the cache holds
rotated post-RoPE keys: dequantize → rotate back → RoPE → rotate forward → requantize). At 4/8 bits this
is very likely immaterial. Recorded as a caveat, not a defect, because we do not run 2-bit KV.

One correction to how KIVI itself is cited anywhere in this lineage: **the per-token-V prescription is
not an outlier argument.** KIVI's Figure 2 finds *no* value-channel outlier pattern; the per-token V
choice is derived from **84.3% attention sparsity** — the output is a weighted sum over few tokens, so
per-token grouping confines error to unimportant tokens. Anyone citing KIVI for "V is per-token because V
has outliers" is citing it wrongly.

### The granularity finding: the reading rule for every future KV-quant paper against this stack

**With `-fa 1`, llama.cpp quantizes K and V per token in 32-element blocks running along the CHANNEL
dimension.** Two consequences that keep being conflated because both mechanisms are called "grouping":

1. **We are finer than the published *mitigation*, by default, everywhere.** The alignment-collapse study
   (arXiv:2606.09864v2, `intake-1291#record`) lists **Group-64 quantization** among the mitigations it
   recommends and measures. Our group-32 is finer than its remedy. **Its headline damage figures are
   therefore a pessimistic bound for us, not a matched estimate** — any transfer of its numbers to this
   stack must say so, and G4 on the TQ3 handoff exists to replace the transfer with our own number.
2. **This is the OPPOSITE axis from KIVI, not the same one.** KIVI prescribes *per-channel for K*; ours is
   *per-token for both*, and quantized V is structurally locked onto the per-token axis by the
   flash-attention gate above. Same word "group", orthogonal dimension. **Do not read a Group-64 result
   as an upper bound on our group-32 damage without first checking which axis the grouping runs along.**

The behavioural half of the alignment-collapse result — the decoupling from perplexity, the K/V damage
asymmetry, and what our KV write path does *not* protect against — is compiled on the
[Quantization](quantization.md) page, which owns the KV-quant quality-instrument thread.

### Spec-decode over quantized KV: R9's verdict stands, its warrant did not — and VeriCache's algorithm is already expressible in frozen v9

**R9's warrant is repaired, not its verdict.** This page's 2026-08-22 section records "spec-decode
composes with quantized KV: 19.15 t/s (+3.3% vs f16) on Coder-32B — the R9 interaction risk closed
positive". The COMPLETED handoff has since corrected the *reasoning*: **that figure is a speed
observation and cannot evidence "no degradation"** — it logged no acceptance rate and named no
correctness instrument. The clearing evidence is **R11's needle-in-a-haystack result (q8_0/q4_0 = 9/9 at
1K/4K/16K, 10/50/90% depth) together with the R4 perplexity pair**; the throughput number is supportive,
never probative. R9 stays **CLEARED** because its config sits on the protected axis (K = q8_0) at the
safe bit width, but it is right by evidence only after the substitution. Re-measurement with both an
acceptance rate and a named correctness instrument is filed as `speculative-decoding-mtp-refresh.md`
**B5** (itself blocked on that file's G3, so the re-run does not measure a full-cache dequant and report
it as a KV-quant result).

**VeriCache's algorithmic core needs no code from us** (arXiv:2605.17613v1, `intake-1282#record`,
credibility 1/Low — the low tier grades *the paper's own performance claims*, not the tree reads below,
which carry no credibility discount). VeriCache drafts on a compressed KV cache and then **verifies
against the FULL KV cache**, so the target distribution is the real FP16 model rather than a quantized
surrogate. Frozen v9 already ships `--spec-draft-type-k`/`-ctkd` and `--spec-draft-type-v`/`-ctvd`
(`common/arg.cpp:3806-3830`), which set the **draft context's** KV type independently of the target's,
and `common_speculative_are_compatible` (`common/speculative.cpp:70`) checks only vocab type / BOS / EOS
/ token text — **so a model can be its own drafter**. `-ctkd q4_0 -ctvd q4_0` against `-ctk f16 -ctv f16`
with `--model-draft <same GGUF>` *is* draft-on-lossy-KV / verify-on-exact-KV, with no code change.
Nothing in either repo configures those flags **asymmetrically**: no registry entry and no launcher sets
them at all, and the only recorded use is a 2026-07-14 experimental-tree argv that set
`-ctkd q8_0 -ctvd q8_0` mirroring the target, which exercises none of the premise.

Three bounds on that, all load-bearing:

- **It gives us the ALGORITHM, not the SYSTEM.** llama.cpp's draft context prefills its own second
  full-length cache **in the same memory tier**. There is no host-resident full-KV tier, no
  PCIe-overlapped swap-in and no staggering scheduler — which is the entire systems contribution.
- **The headline decomposes, and the arm matching our lever is the weak one.** VeriCache *alone* measures
  **1.92–2.73×** on long-context decoding and 1.33–2.11× on remote prefix caching; the 4.26× is
  **composed with an EAGLE3 drafter**, the 4.35× is a **modelled ideal** from its own Appendix-B analytic
  model, and the **quantization-compressor arm** (KVQuant, RotateKV, ExpectedAttention, SnapKV on
  Mistral-24B) is **1.4–1.9×**. Losslessness is scoped by footnote 1 to *greedy* decoding "except for
  randomness caused by hardware"; the measured residual is KL < 0.01 nats, not zero; sampling is asserted
  in footnote 2 and never evaluated. And "first" is contradicted by TriForce (arXiv:2404.11912, 2024-04)
  and Vegas (arXiv:2602.07223, 2026-02), whose own abstract already describes the mechanism as
  established prior work.
- **Total memory goes UP, and our card sits at the worst end of its own hardware sweep.** VeriCache keeps
  the full KV on CPU *in addition to* the compressed cache on GPU; GPU-resident footprint is
  KV_full·(xc+1)/(x+1), i.e. 0.231·KV_full at its own x=25, c=0.2 — **a tier relocation, not a size
  reduction**. Its sweep runs 1.92× at HBM-to-interconnect ratio 60 up to 3.01× at ratio 10; **our MI210
  ratio is 35.5–56.7** (derived by the dive from MI210 HBM2e 1638 GB/s spec / ~1025 GB/s attained against
  the first-party PCIe4 x16 measurement of **28.89 GB/s H2D, 28.20 D2H, 2026-08-03**), predicting
  **~1.9–2.4×**, not 4×. Note the denominator spread: the [Quantization](quantization.md) page's roofline
  work records **1433.3 GB/s** as MI210 achievable bandwidth, giving ratio 49.6 — inside the same band, so
  the conclusion is insensitive to which attained figure is used. VeriCache's resource model also
  **excludes GPU compute** by its own §5.1, so any CPU-side estimate built on it is optimistic by the
  prefill term.

A first-party correction rode along and matters more than the paper: **the whole-cache dequant "cliff" is
a CUDA/HIP-backend property and must NOT be generalised to our primary CPU serving path.** The CPU
backend takes `kq_vec_dot = ggml_get_type_traits_cpu(k->type)->vec_dot` (`ggml-cpu/ops.cpp:8635`), so K
is consumed **in its quantized form at any q_len**, and V is dequantized **one DV-length row at a time**
into a stack temp (`:8739`). There is no whole-tensor conversion anywhere on the CPU path. On the GPU
path, without `GGML_CUDA_FA_ALL_QUANTS` only Q4_0/Q8_0/F16/BF16/F32 are FA-eligible KV types
(`fattn.cu:340-358`) — exactly our production `-ctk q4_0`/`q8_0`.

**Filed, not run:** measure α for KV-asymmetric self-speculation on our own models — same GGUF as target
and drafter, target `-ctk f16 -ctv f16`, draft `-ctkd q4_0`/`q8_0`, sweeping `--draft-max` ∈ {4, 8, 16},
reporting mean accept length and per-token agreement. Gate opens if q8_0-draft agreement ≥ ~95% at
draft-max 8; closes if q4_0-draft agreement < 90%. The drafter is the full model, so **this measures α,
not speedup**. Rider on `speculative-decoding-mtp-refresh.md`.

### The dual-cache post-mortem was a capacity argument applied to a bandwidth problem

This page's *"Hybrid buffer architecture is memory-negative"* finding — the `kv_recent` f16 + `kv_old`
q4_0 design that allocated both at full context size — is **reframed, not overturned**
(`kv-cache-quantization.md:71`, reframed 2026-08-23). "Dual cache = more bytes resident = wrong" is sound
**only when both copies sit in the same memory tier and the cheap copy is dequantized on the read path.**
Ours did both, which is why it lost: the **~30% gen-speed gap at 14.5K filled context is the cost of the
`q4_0 → f16` cast on every decode token** (~400 MB cast per decode token at 14K positions × 512 elements
× 28 layers × 2), a *dequantization* cost, not a *capacity* cost.

**A dual-cache design in which the second copy lives in a cheaper tier — host DDR5 behind a GPU, or a
slower NUMA node — and is never dequantized into the attention hot path is a different design and is not
refuted by anything measured here.** Cite that post-mortem narrowly: *same-tier plus dequantize-on-read is
memory-negative AND bandwidth-negative.* It establishes nothing about tiered KV, and must not be used to
close a tiering proposal.

### "Per-token KV streaming over PCIe is an anti-pattern" — scope it to *per token*

The 2026-07-20 section above states that PCIe4 is 7–14× slower than EPYC DDR5, "so per-token KV
*streaming* is an anti-pattern". That remains true **per token**, and is now scoped: **amortised over an
x-token draft/verify horizon the effective bandwidth is 28.89·x GB/s**, reaching **EPYC DDR5 parity
(~300 GB/s) at x ≈ 11** and **MI210 HBM parity (1638 GB/s spec) at x ≈ 57**. Those crossovers are
*derived* by the VeriCache dive from the first-party 28.89 GB/s H2D measurement, not measured end-to-end.
The transfer is only an anti-pattern when it is *not* amortised, and the horizons this literature
actually uses (x = 20–50) straddle the DDR5 crossover. The minimum draft length needed to hide a full-KV
reload at c = 0.25, B = 1 is x ≥ 24.8 (spec) / 15.3 (attained) at KV/M = 0.5, rising to 74.3 / 46.0 at
KV/M = 2.0 — i.e. above the 20–50 range once KV exceeds ~0.5× model bytes.

### Slot save/restore: the reuse loss is CONDITIONAL, it is detectable today, and the wrong PR is being watched

Upstream issue **#25913** ("`/slots` save/restore silently loses all prompt reuse on hybrid/recurrent
models") is real, open, unfixed on upstream master as of 2026-08-22, and **present byte-identically in
frozen v9** — the 87-line SLOT_SAVE/SLOT_RESTORE handler block matches upstream b10045 and the 33-line
checkpoint/reset block matches b10045 *and* upstream master `e85caa81`; no EPYC-local commit touches
either locus, so there is neither local mitigation nor local aggravation (`intake-1292#record`,
credibility 3/Medium, five independent reproducers on five backend/model combinations).

**The issue title is too broad in the direction that matters most to us.** Reuse is zero only for a
**DIVERGENT or EXACT-REPEAT** post-restore prompt; **a prompt that strictly extends the restored prefix
reuses fully, with no patch.** This follows from
`pos_min_thold = std::max(0, pos_next - n_swa - (has_new_tokens ? 0 : 1))`
(`tools/server/server-context.cpp:3322`) given that a hybrid's `llama_memory_hybrid::seq_pos_min` returns
the **recurrent cell's position** rather than 0 (`src/llama-memory-hybrid.cpp:172-175`): a strict
continuation leaves `pos_min` below the threshold and skips the reset block entirely, while an exact
repeat or a mid-prefix divergence opens it and forces `n_past = 0`. The PR author states the same thing
in prose, and four independent measurements fit the corrected table. **Our full-to-quarter migration is a
turn-boundary session handover — i.e. exactly the continuation shape — so "every migration costs a full
re-prefill" is NOT the default expectation; it is the failure mode that occurs when something rewrites
the prefix.**

Mechanism, for the record: the save writes **tokens only** (`:2539-2541`); restore calls
`slot->prompt.clear()` (`:2586`), and `server_prompt::clear()` destroys checkpoints
(`tools/server/server-task.h:615-618`); with the checkpoint list empty `do_reset` is always true
(`:3388`) and `pos_next`/`n_past` are forced to 0 (`:3404-3409`), logged only at `SLT_TRC` (level 4).
Scale of the effect where it does fire, third-party: one controlled A/B on a 58,202-token prefix measured
`prompt_n = 58,202 / cache_n = 0 / 181.9 s` on master versus `prompt_n = 516 / cache_n = 57,686 / 4.7 s`
with the candidate patch.

**"Silent" is true of the log and of the restore response, and FALSE of the next completion.**
`slot.n_prompt_tokens_cache = n_past` (`:3434`) reaches the client as `timings.cache_n`, OpenAI
`cached_tokens`, Anthropic `cache_read_input_tokens`, and the `/slots` payload — the instrument already
exists and this repo already documents it. **The operative silence is ours**:
`concurrency_aware.py:148-161` returns `True` on an HTTP 200, `:679` advances to
`MigrationState.VERIFIED` with `detail="restore_confirmed"`, and `:682` then **erases the source KV**.
That is a misnamed state; gating the source erase on measured reuse (compare returned `n_restored`
against `n_saved`, then read `cache_n`) is zero-compute and independent of any benchmark. The same gap
exists in `llama_server.py:1256-1279`, which never parses the body at all.

Three operational facts to carry:

- **The migration path is NOT dormant.** `--slot-save-path` is set on all three frontdoor instances
  (`:8070` at `-np 4`, `:8080`/`:8180` at `-np 1`, all `Qwen3.6-35B-A3B-MTP-Q8_0.gguf`, `--device none`),
  emitted unconditionally by `orchestrator_stack.py:1454-1462`; 75 `kv_migrate_*` artifacts sit on disk
  and live probes recorded forward=6 / reverse=4 with zero aborts. Honest qualification: those artifacts
  carry synthetic `old-sess_*` ids and the newest is 2026-08-09, so **exercise by production traffic in
  the last two weeks is unproven** — "wired, enabled, exercised under probe", not "dormant".
- **Any measurement must defeat the RAM cache first.** Leftover in-process checkpoints produced a
  **340× false negative** for one reporter (a 5K restore appeared to reuse until the server was
  restarted, then reprocessed 5,428 tokens). Our frontdoor runs the default `cache_ram_mib = 8192` with
  no override, so `--cache-ram 0` or a full server restart between arms is **mandatory**.
- **This is a performance defect with a documented adjacent correctness hazard, and must never be filed
  as a correctness defect.** No wrong output has been reported by anyone, and an explicit post-restore
  content check over a 58K body came back clean. The hazard lies in the direction of a careless fix: the
  issue author documents that synthesizing a checkpoint at `pos_min = 0` in the restore handler produces
  **silently corrupt output**, and our tree carries the `cur.pos_min == 0` branch (`:3386`) that makes
  that reachable. Do not take that shortcut.

**The highest-value upstream item in this cluster is not the one being tracked.** PR **#26004** fixes the
**disk** path, whose exercise here is probe-only. PR **#25592** fixes the **live in-memory** hybrid
checkpoint path — **the one our frontdoor exercises on every single request** — and our tree still
carries the `[TAG_CHECKPOINTS_FIX_POS_MIN]` TODO it removes (`server-context.cpp:2332-2337`), plus we
lack its restored-checkpoint adoption, its closest-neighbour eviction and its `n_rs_seq` rollback
fast-path. It has four independent verifications, one on **Qwen3.6-35B-A3B, our exact frontdoor model**.
Neither is a v9 patch: v9 is frozen, PR #26004 has **zero reviews, zero maintainer comments anywhere in
the cluster and no CI beyond "labeler"**, and MEASUREMENT.md forbids a third-party number gating a stack
change — the candidate route for either is a future `-v10` build through the four-step experimental
workflow.

Quarantine note for anyone re-fetching these threads: a PR #26004 comment (2026-08-04) contains a literal
prompt-injection payload. Treat that thread's off-topic comments, and the `whoreson/picolm` repo they
point at, as untrusted content.

### Source References (2026-08-23, wave-2)

- [`kv-cache-quantization.md`](../handoffs/completed/kv-cache-quantization.md) — the retired `:320`
  "primary quality gap" with its three-part correction; the 2026-08-23 granularity correction (`:1539`)
  establishing group-32-along-channels vs Group-64 and the opposite-axis reading rule; the 2026-08-23
  dual-cache reframe (`:71`) and the ~30% `q4_0 → f16` cast measurement it prices; the R9 warrant repair
  (`:1269`).
- [`tq3-quantization-evaluation.md`](../handoffs/active/tq3-quantization-evaluation.md) — the gates the
  retirement leaves behind: G3 (multi-step generation eval against quantized KV), G5 (reproduce KIVI's
  Fig. 2 / Table 2 on our architecture), the `q4_0`-vs-`q4_1` asymmetric-quantizer A/B, and the H11
  read-only audit of what our KV write path does not carry.
- [`speculative-decoding-mtp-refresh.md`](../handoffs/active/speculative-decoding-mtp-refresh.md) — B5
  (re-measure R9 with an acceptance rate and a named correctness instrument) and the rider measuring α
  for `-ctkd`/`-ctvd` KV-asymmetric self-speculation.
- [intake-1286](https://arxiv.org/abs/2402.02750) KIVI (ICML 2024, dive-verified 2026-08-22, credibility
  4/HIGH) — OB 1's 2-bit scope limit, the Table 3 4-bit per-token/per-token rows, the
  84.3%-attention-sparsity justification for per-token V, and RotateKV (arXiv:2501.16383v2) as
  independent evidence that per-channel keys are a remedy rather than a requirement. Cite as
  `intake-1286#record`.
- [intake-1282](https://arxiv.org/abs/2605.17613) VeriCache (arXiv preprint, dive-verified 2026-08-22,
  credibility 1/Low) — draft-on-compressed / verify-on-full architecture; the decomposed headline
  (1.92–2.73× alone, 1.4–1.9× on the quantization arm); the tier-relocation memory direction; the
  HBM-to-interconnect sweep placing our MI210 at its worst end; and the frozen-v9 `-ctkd`/`-ctvd` +
  self-drafting finding, plus the CPU-vs-CUDA dequant-cliff correction. Cite as `intake-1282#record`.
- [intake-1292](https://github.com/ggml-org/llama.cpp/issues/25913) llama.cpp `/slots` save/restore
  (issue #25913 + PR #26004, dive-verified 2026-08-22, credibility 3/Medium) — the divergent /
  exact-repeat / strict-continuation scope derivation from `pos_min_thold`, the byte-identity audit
  against frozen v9, the `cache_n` detectability finding and our `VERIFIED`-on-HTTP-200 gap, the
  `--cache-ram` masking hazard, and PR #25592 as the larger live exposure. Cite as `intake-1292#record`.
- [intake-1291](https://arxiv.org/abs/2606.09864) Alignment Collapse Under KV Cache Quantization (arXiv
  preprint, dive-verified 2026-08-22, credibility 3/Medium) — the Group-64 mitigation our group-32 is
  finer than; behavioural detail compiled on [Quantization](quantization.md). Cite as
  `intake-1291#record`.

(append to the page-level `## Source References` list)

- [intake-1286](https://arxiv.org/abs/2402.02750) KIVI (ICML 2024) -- the warrant behind every "per-channel K / per-token V" citation in this corpus. Dive-verified 2026-08-22: the prescription is measured, not asserted, but OB 1 establishes it **at 2 bits only** and the paper runs no 4-bit or 8-bit axis ablation; it reports **no perplexity anywhere**; and the full-precision residual window, not the axis, does most of the accuracy recovery (Llama-2-7B GSM8K 5.76 -> 12.74 at a fixed axis). Retires the `kv-cache-quantization.md:320` "primary quality gap". Cite as `intake-1286#record`
- [intake-1291](https://arxiv.org/abs/2606.09864) Alignment Collapse Under KV Cache Quantization -- ConditionalFlip as a paired behavioural gate; K carries 76-102% of the damage at 4-bit; **Group-64 is its mitigation, which our group-32 blocks are already finer than**. Unreviewed preprint, NVIDIA-only hardware, no independent replication located. Cite as `intake-1291#record`
- [intake-1282](https://arxiv.org/abs/2605.17613) VeriCache -- draft on the compressed KV cache, verify against the FULL KV cache; the algorithmic core is expressible in frozen v9 via `-ctkd`/`-ctvd` with the model as its own drafter, while the systems contribution needs an interconnect we do not have. Cite as `intake-1282#record`
- [intake-1292](https://github.com/ggml-org/llama.cpp/issues/25913) llama.cpp `/slots` save/restore (issue #25913 + PR #26004) -- post-restore reuse is zero only for a DIVERGENT or EXACT-REPEAT prompt and full for a strict continuation; detectable today via `timings.cache_n`; PR #25592 (live in-memory checkpoint path) is the larger exposure for us. Cite as `intake-1292#record`


## Compiled Update — 2026-08-31 (incremental): GLM-5.2 KILLED; the DSA findings transfer to glm5next

**Confidence: verified** (operator ruling + artifact deletion ledgered; GGUF header read for the successor arch).

The GLM-MoE-DSA evaluation closed with a KILL (OP-8, operator ruling 2026-08-31: GLM-5.3-flash
supersedes any reason to run GLM-5.2); the 223 G UD-IQ2_M artifact is deleted and ledgered. What
survives the model is the DSA layer knowledge, now seeded into the GLM-5.3-Flash handoff (INF-69):

- **GLM-5.3-Flash is arch `glm5next`** (288×10B), NOT `glm-dsa` — but it carries the same
  DSA-family metadata surface (`indexer.{head_count,key_length,top_k}`, a NEW `kpool` field, and
  `nextn_predict_layers`). Arch-support audit is the INF-69 gate; the `3dee86a5a` GLM→DSA-cache
  wiring is the worked precedent, not reusable code.
- **DSA-DENSE-MASK stands as a fork-level finding**: the generic DSA path computes the indexer +
  top-k but final attention masks over FULL KV (no sparse gather) — any glm5next bringup inherits
  it, and the sparse-gather/profiling gate stays owned by `llama-cpp-dsa-contribution.md` (D2/D3).
- **`indexer_top_k` is a correctness cliff, not a tuning knob**: an under-sized cap corrupts exact
  output once prompt length exceeds it (GLM-5.2's safe policy was next-power-of-two ≥ prompt
  tokens). glm5next's `kpool` may change the semantics — re-derive before any quality run.
- **NextN/MTP**: GLM GGUFs preserve the NextN tail, the fork's GLM archs skip it and never
  dispatch `LLM_GRAPH_TYPE_DECODER_MTP`; the smallest credible port is Qwen-style tail-tensor
  loading + a DECODER_MTP graph.
- The GLM-5.2 reviewer-capability program (REV-02) is mooted by the KILL; its retarget-or-close
  disposition is flagged to the reviewer control plane.

### Source References (2026-08-31)

- [`glm51-reap-cpu-evaluation.md`](../handoffs/completed/glm51-reap-cpu-evaluation.md) — the
  completed evaluation: KILL verdict, DSA-DENSE-MASK evidence, top-k schedule records.
- [`glm53-flash-evaluation.md`](../handoffs/active/glm53-flash-evaluation.md) — INF-69: the
  inherited-findings contract and the glm5next arch facts (GGUF header read).
- [`2026-08-31-disk-reclaim-menu.md`](../progress/2026-08/2026-08-31-disk-reclaim-menu.md) —
  OP-31 execution record incl. the GLM-5.2 deletion and disk state (87 G → 480 G).
