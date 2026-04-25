# MoE Optimization

**Category**: `moe_optimization`
**Confidence**: verified
**Last compiled**: 2026-04-25
**Sources**: 25 documents (2 deep-dives, 4 handoffs, 19 intake entries)

## Summary

Mixture-of-Experts models are central to our EPYC 9655 inference stack. The frontdoor (Qwen3-Coder-30B-A3B, 3B active of 30B total), architect_general (Qwen3-235B-A22B), and architect_coding (REAP-246B, 50%-pruned from Qwen3-Coder-480B-A35B) are all MoE architectures. The fundamental characteristic of MoE for CPU inference is that only a fraction of parameters are active per token, but all expert weights must reside in memory for routing. This creates a unique optimization space distinct from dense model compression: reducing the number of stored experts directly reduces model file size and memory bandwidth requirements without affecting per-token active compute.

REAP (Router-weighted Expert Activation Pruning) is the breakthrough technique in this space. Published at ICLR 2026 by Cerebras, REAP permanently removes entire experts based on a saliency score that combines router gate values with expert output norms, computed in a single calibration forward pass over 128-512 samples. No fine-tuning, no gradient computation. The theoretical grounding is clean: expert merging (HC-SMoE, M-SMoE) creates irreducible error proportional to router policy variability because the merged expert loses the router's input-dependent control, while pruning preserves surviving experts unchanged. The empirical evidence is decisive: at 50% compression, REAP achieves 0.557 coding accuracy vs HC-SMoE's 0.379, and on creative writing, merging catastrophically collapses to 0.008 while REAP maintains 0.718.

We deployed REAP in production with striking results. The 480B architect_coding model was replaced by REAP-246B (50% pruning), achieving 82% quality on our Claude-as-Judge benchmark -- a 9 percentage point improvement over the unpruned model at deployment quantization. Throughput improved 14% (8.0 vs 7.0 t/s) and memory dropped 44% (139 vs 250 GB). The improvement is counterintuitive but consistent with findings across the ecosystem: removing noisy/redundant experts reduces routing confusion. Kimi-Linear at 30% pruning gained +10 on AIME25. Cerebras's own 480B at 25% outperforms base on 6/14 benchmarks. The 480B model has been deleted from our system.

The ecosystem around REAP is maturing rapidly. Cerebras has published 30 official pre-pruned models across 7 families (Qwen3-Coder, DeepSeek-V3.2, Kimi-Linear, MiniMax, GLM-4.x, Step-3.5-Flash, GLM-4.5-Air). Community practitioner 0xSero has produced systematic pruning sweeps across GLM-4.7, MiniMax-M2.1, DeepSeek-V3.2, and INTELLECT-3, with validated calibration recipes and stress testing methodology. The CerebrasResearch/reap repository (Apache 2.0) supports direct CLI pruning of all Qwen3 MoE models.

A critical practical finding emerged from 0xSero's stress tests: the "Goldilocks zone" for MoE pruning is 30-40%, not the intuitive 20-25%. At 20%, pruning destabilizes routing without triggering clean redistribution (repetition loops at low temperature on MiniMax-M2.1). At 30%, the router fully adapts to the reduced expert set. At 50%, degradation begins (2 loops in stress test). This counterintuitive result -- that removing more experts can produce better quality than removing fewer -- is one of the most practically important findings for deployment decisions.

Extending techniques include EvoESAP (non-uniform cross-layer budget allocation via evolutionary search), Router Knowledge Distillation (lightweight retraining of router weights post-pruning), and MoNE (replacing pruned experts with constant-vector "novice" approximations). For our Qwen3+REAP stack, EvoESAP is not useful (actually hurts at 25%, negligible at 50% -- the headline +19.6% was on a different model+criterion combination). Router KD is modestly beneficial (16/25 benchmarks improved) and worth the 2-hour investment only at 50%+. MoNE is lower priority than direct pruning (no REAP comparison in the paper, only tested up to 16B models).

A newer entrant is Leanstral (Mistral AI), a 119B MoE with 6.5B active parameters using DeepSeek V3-style architecture (MLA + 128 routed experts + 1 shared expert). Leanstral is a near-ideal REAP candidate: 95% of its parameters are routed expert weights. For specialized Lean 4 proof engineering, where expert activation patterns likely cluster on a subset of experts, aggressive pruning at 75% + Q4_K_M could shrink the model from 68 GB to approximately 20 GB with projected 40+ t/s on EPYC. The `deepseek2` architecture is fully supported in llama.cpp, and community GGUFs are available.

## Key Findings

### REAP Core Technique

- **REAP beats merging by a wide margin at all compression levels**: At 50%, REAP achieves 0.557 coding accuracy on Qwen3-30B-A3B vs HC-SMoE 0.379 and M-SMoE 0.413. On creative writing, HC-SMoE catastrophically collapses to 0.008 while REAP maintains 0.718. Theoretical explanation (Theorem 1 in the paper): merging creates irreducible error proportional to Var[r(x)] (router policy variability) because the merged expert cannot produce different outputs for different inputs -- the input-dependent routing is lost. Pruning preserves surviving experts unchanged, maintaining the router's discriminative ability. [REAP deep-dive](../research/deep-dives/0xsero-reap-ecosystem-deep-dive.md)

- **25% pruning is near-lossless and sometimes beneficial**: Qwen3-Coder-30B-A3B REAP-25B scores HumanEval 94.5 vs baseline 92.1 (+2.4), HumanEval+ 89.0 vs 87.8 (+1.2), MBPP 87.3 vs 87.6 (-0.3), LiveCodeBench identical (35.2). Paper-wide mean at 25% is -2.8% on coding. Cerebras 480B at 25% outperforms base on 6/14 benchmarks (agentic tasks up 1.8-2.9 pts). Kimi-Linear at 30% gains +10 AIME25. The mechanism: removing noisy/redundant experts reduces routing confusion, effectively performing implicit regularization. [REAP deep-dive](../research/deep-dives/0xsero-reap-ecosystem-deep-dive.md)

- **The Goldilocks zone is 30-40%, counterintuitively not 20-25%**: 0xSero's MiniMax-M2.1 stress tests across 4 temperatures times 6 prompt types: REAP-20% produced 1 repetition loop (deprecated), REAP-30% zero loops (recommended), REAP-40% zero loops (recommended), REAP-50% 2 loops (deprecated). Low temperature (0.0-0.2) exposes loop failures; temp >=0.7 masks them. `math_word` prompts are most vulnerable. Hypothesis: 20% removes just enough experts to destabilize routing without triggering clean redistribution, while 30% forces the router to fully adapt. [REAP deep-dive](../research/deep-dives/0xsero-reap-ecosystem-deep-dive.md)

- **Calibration data determines which capabilities survive**: If calibration data lacks code, code-specialized experts appear unused and get pruned, destroying coding ability. 0xSero's validated recipe (1,360 samples): 51% evol-codealpaca (code gen), 24% xlam-function-calling (tool use), 24% SWE-smith-trajectories (agentic coding). Cerebras uses a similar composition for Qwen3-Coder models. For our stack, custom calibration from production orchestrator workload (agentic coding + tool calls + multi-turn conversations) would be optimal. [REAP deep-dive](../research/deep-dives/0xsero-reap-ecosystem-deep-dive.md)

- **Gate renormalization (paper v2) improves accuracy**: Simple post-pruning router gate adjustment reduces mean accuracy loss from 2.6% to 1.9% across benchmarks. No re-training required. [REAP handoff](../handoffs/completed/reap-moe-expert-pruning.md)

- **REAP output is standard safetensors**: The pruned model is a standard HuggingFace checkpoint with fewer experts per MoE layer. Direct `convert_hf_to_gguf.py` produces valid GGUF. Standard `qwen3moe` architecture string -- no custom code, compatible with any llama.cpp build b6810+. [REAP deep-dive](../research/deep-dives/0xsero-reap-ecosystem-deep-dive.md)

### REAP Production Deployment

- **246B deployed as architect_coding, replacing 480B**: REAP-246B (50% pruning of Qwen3-Coder-480B-A35B): 82% quality on Claude-as-Judge (+9pp over unpruned at deployment quant), 8.0 t/s throughput (+14%), 139 GB memory (-44%). Math improved +3, thinking improved +5 -- removing noisy experts helped reasoning. Only IP suite regressed (prompt leakage, -3). The 480B model was deleted. Deployed since 2026-03-29. [REAP handoff](../handoffs/completed/reap-moe-expert-pruning.md)

- **REAP-363B (25% pruned 480B) is NOT compelling for single-model deployment**: 93% of 480B speed at 6.54 t/s, 31 GB savings irrelevant at 1.13 TB RAM. Tree and lookup both harmful (approximately -22%). REAP on large MoE is a GPU VRAM optimization; our CPU RAM budget is not the bottleneck. Only valuable in concurrent-model RAM budgeting scenarios. [REAP handoff](../handoffs/completed/reap-moe-expert-pruning.md)

- **REAP-25B GGUF available off-the-shelf**: bartowski's `cerebras_Qwen3-Coder-REAP-25B-A3B-GGUF` in 26 quant variants. Q4_K_M at 15.19 GB (vs approximately 18 GB base = -16% memory, same 3B active params). Downloaded and benchmarked: dm=24 linear at 39.62 t/s (101% of base 30B), baseline without speculation at 33.21 t/s (15% faster than unpruned baseline). [REAP deep-dive](../research/deep-dives/0xsero-reap-ecosystem-deep-dive.md), [REAP handoff](../handoffs/completed/reap-moe-expert-pruning.md)

- **REAP replaces runtime expert reduction -- do NOT stack**: REAP permanently removes experts from the model file. Download the pre-pruned GGUF and skip `--override-kv n_expert` entirely. Stacking REAP with runtime expert reduction would double-prune and degrade quality. [REAP handoff](../handoffs/completed/reap-moe-expert-pruning.md)

### Extending Techniques

- **EvoESAP is not useful for Qwen3+REAP**: At 25% pruning, EvoESAP (non-uniform cross-layer budget via evolutionary search) actually hurts Qwen3 (Code Avg 0.580 vs 0.629 uniform REAP). At 50%, gains are only +0.010 Code Avg. The headline +19.6% MATH-500 result was ERNIE + Frequency criterion (weakest ranker), not REAP. REAP's uniform allocation is already near-optimal for Qwen3's 128-expert architecture. Not worth the 5-hour search cost. [REAP deep-dive](../research/deep-dives/0xsero-reap-ecosystem-deep-dive.md)

- **Router Knowledge Distillation: modest for REAP, worth 2h at 50%+**: Tested directly on Qwen3-30B-A3B at 62.5% retention (128 to 80 experts): 16/25 benchmarks improved but gains are small for REAP (the router already routes well post-pruning). Cost is only approximately 2h on A100 with 3000 samples and 0.04% of parameters updated. Larger gains for weaker compression methods (CFES, MoBE). Fine-grained MoEs with 128 experts (1.43T routing combinations) benefit most from re-training, so Qwen3 is in the right category. [REAP deep-dive](../research/deep-dives/0xsero-reap-ecosystem-deep-dive.md)

- **MoNE is lower priority than REAP**: Novice experts are constant vectors (mean expert output), not learned networks. Memory savings are essentially identical to REAP (expert FFN weights removed, novice overhead negligible). No direct REAP comparison in the paper. Only tested on models up to 16B. The "0.14 performance drop at 25%" claim was not from this paper (correction noted in deep dive). [REAP deep-dive](../research/deep-dives/0xsero-reap-ecosystem-deep-dive.md)

- **Double compression pipeline (prune + quantize) achieves approximately 6.5x**: 0xSero demonstrated REAP 50% + AutoRound W4A16 on GLM-4.7: 700 GB to 92 GB, running at 375 tok/s prefill and 38.5 tok/s gen on 8x RTX 3090. The pipeline preserves standard HuggingFace safetensors at every step, so each stage uses standard tooling. [REAP deep-dive](../research/deep-dives/0xsero-reap-ecosystem-deep-dive.md)

### Leanstral and New MoE Architectures

- **Leanstral is a near-ideal REAP candidate**: 95% of its 119B parameters (116B of 122B) are routed expert weights (128 experts, 2048 FFN each). At 75% pruning (32 experts retained) + Q4_K_M, the model shrinks from 68 GB to approximately 20 GB with projected 40+ t/s on EPYC. The key hypothesis: Lean 4 proof engineering is extremely specialized -- if expert activation patterns cluster on 20-30 experts (plausible for a narrow domain), aggressive pruning has minimal quality impact. Needs profiling with `--moe-expert-stats` on representative Lean 4 workloads. [Leanstral deep-dive](../research/deep-dives/leanstral-architecture-analysis.md)

- **Leanstral uses DeepSeek V3 architecture (MLA + MoE)**: `deepseek2` architecture string in llama.cpp, fully supported. Multi-head Latent Attention (MLA) with 256 kv_lora_rank reduces KV cache requirements independently of expert pruning. 32 standard attention heads, 1024 q_lora_rank, 64 qk_rope_head_dim. Community GGUFs at `jackcloudman/Leanstral-2603-GGUF` (Q4_K_M approximately 68 GB, Q8_0 approximately 126 GB). Vision encoder (Pixtral) is dead weight for proof tasks and could be stripped. [Leanstral deep-dive](../research/deep-dives/leanstral-architecture-analysis.md)

- **Leanstral beats Claude on FLTEval at 15x lower cost**: pass@2 of 26.3 vs Claude Sonnet 4.6's 23.7, at $36 vs $549 per run. FLTEval tests repo-scale proof engineering (completing FLT PRs), not function-level verification. Complementary to Goedel-Code-Prover-8B which is a prover (takes goal, produces tactic proof) while Leanstral is an agent (uses lean-lsp-mcp tool, reads repo context). [Leanstral deep-dive](../research/deep-dives/leanstral-architecture-analysis.md)

### Hybrid Models and MoE

- **Qwen3.5 hybrid is NOT supported by REAP officially**: Only `Qwen3MoeForCausalLM` in the REAP model registry. 0xSero applied REAP to Qwen3.5-35B-A3B (intake-236) but PPL increased +39% at only 20% pruning vs near-lossless on pure MoE. Hybrid models with 75% recurrent layers are much less tolerant because MoE layers interact with recurrent state -- pruning experts disrupts the recurrent-attention interplay more severely. Custom model_util mapping would be needed. [REAP deep-dive](../research/deep-dives/0xsero-reap-ecosystem-deep-dive.md)

- **REAP-pruned models enable speculative decoding where hybrids cannot**: REAP-25B is pure MoE (`qwen3moe` arch), so all speculation approaches work (dm=24 linear at 39.62 t/s, lookup safe at 37.91 t/s, tree hurts at 30.83 t/s). If the frontdoor role shifts from hybrid Qwen3.5-35B-A3B to REAP-25B, speculation becomes viable for the highest-volume role in the orchestrator. [REAP handoff](../handoffs/completed/reap-moe-expert-pruning.md)

### GLM-5.1 REAP and Expert Pruning Thresholds

- **GLM-5.1-555B-A14B-REAP GGUF is the first 555B MoE with published GGUF benchmarks.** 325GB Q4_K_M, 14B active parameters from 192 experts (top-8 routing), 88% Terminal-Bench, 66% SWE-bench Pro, 0% repetition loops. CPU-deployable via llama.cpp. Evaluation handoff created: glm51-reap-cpu-evaluation.md. [intake-427]

- **Expert count threshold finding confirms 25-30% as the pruning sweet spot.** 192/256 experts (25% prune) = stable with 0% degeneration; 154/256 experts (40% prune) = BROKEN with 29% degeneration. This aligns with the Goldilocks zone finding from 0xSero's MiniMax-M2.1 stress tests, independently confirming that 25-30% pruning is near-lossless while 40%+ risks catastrophic quality collapse on large-expert-count architectures. [intake-427]

### Inter-process Expert Parallelism (CPU15 Phase 3, 2026-04-25)

After REAP made REAP-246B production-viable in absolute terms, the open question shifted to whether *single-stream* throughput on large MoE could exceed the 6.16 t/s Phase 0 baseline by sharding active expert compute across NUMA nodes. Phase 1/2 intra-process attempts (per-CCD expert sharding inside one llama.cpp process) all D3-failed: the fundamental limitation is ggml's sequential-per-op graph executor — even with sharding, all threads still execute op N together with global barriers, so per-NUMA parallelism isn't achievable inside one process. **Phase 3 escapes that constraint by running N independent llama.cpp processes connected via shared-memory IPC, each computing 1/N of experts at every MoE op.** The IPC primitive (`ep_dispatcher` library, [Phase 3.1 prototype](../../cpu-ep-prototype/)) achieves 0.73 μs RTT for 4 NUMA-pinned workers — ~200× under the viability threshold.

The integration into `llama.cpp-experimental:feature/cpu-ep-inter-process` landed 13 commits in one day: bootstrap fork at `ggml_cpu_init`, IPC harness inside `ggml_compute_forward_mul_mat_id`, expert slicing with parallel sum-reduce + merged broadcast, NUMA pinning, worker drone mode (workers skip non-MoE ops and receive src1+ids from master at each MoE op), multi-node pinning, lazy expert-tensor sharding (`ggml-ep-shard.{h,cpp}`), `GGML_EP_MASTER_ALL_NODES` for bandwidth-bound configs, plus a critical `#ifndef GGML_USE_OPENMP` guard fix that exposed earlier "throughput numbers" as measurement artifacts.

#### Production results

| Model | Total / Active | Baseline (96t, --numa distribute) | EP best | Δ | Verdict |
|-------|---------------|----------------------------------|---------|---|---------|
| gemma-4-26B-A4B-it Q4_K_M | 26B / 4B | 28.5 t/s | 30.3 (N=2 drone+shard) | +6% | Bit-exact ✓ |
| **Qwen3.6-35B-A3B Q8_0** | 35B / 3B | 9.93 t/s | **19.90** (N=2 drone+shard 48t) | **+100%** | Bit-identical PPL ✓ |
| REAP-246B-A35B Q4_K_M | 246B / 35B | 6.89 t/s | 0.1 (N=4 master-all-nodes) | −98% | EP doesn't help ✗ |
| MiniMax-M2.7 Q8_0 | 230B / 10B | 9.98 t/s | 7.72 (N=2 shard) | −23% | EP doesn't help ✗ |

The 32-chunk WikiText-2 PPL gate confirmed bit-identical perplexity between baseline and EP+drone+shard on Qwen3.6-35B-A3B (`[1]4.3289...[32]5.7225` in both runs). Visible token-level divergence in `llama-cli` was sampling-argmax jitter on FP-rounding-equivalent logits — the underlying probability distribution is identical.

#### Why EP wins on medium MoE but fails on >150B-class

**Wins on Qwen3.6-35B-A3B class** because compute, not bandwidth, dominates. With 3B active params and ~35 GiB Q8_0 model size, single-instance at 96t under-utilises the 4-NUMA bandwidth profile; EP at N=2 with each instance spanning 2 nodes lets master handle non-MoE compute fully while workers parallelise MoE — net 2× throughput.

**Fails on REAP-246B / M2.7** because single-instance with `--numa distribute` already saturates 100% of system DDR bandwidth across all 4 nodes. EP at N=4 with master spanning all nodes (`GGML_EP_MASTER_ALL_NODES=1`) creates **thread oversubscription**: 96 master threads + 24×3 worker threads = 168 simultaneous threads on 96 physical cores during MoE ops. OS scheduler thrashing dominates, per-token time blows out 70× vs baseline.

The fundamental issue: ggml's threadpool is fixed-size per process, so it can't dynamically resize between non-MoE phase (master-only active) and MoE phase (all instances active in parallel). Architectural fix would require dynamic threadpool resizing or phase-aware spin-parking — real engineering, deferred indefinitely.

#### Production deployment routing

| Total params | Mode | Reason |
|--------------|------|--------|
| < 50B MoE | EP N=2 drone+shard, 48t per instance | Compute-bound, parallelism wins |
| 50–150B MoE | EP N=2 drone+shard (validate first) | Likely benefits, bandwidth-edge |
| > 150B MoE | single-instance --numa distribute 96t | Bandwidth-saturated; oversubscription |
| Dense | single-instance | No MoE ops to parallelise |

#### Deferred memory and latency optimisations

- **Eager shard allocation (3.2(g.1))**: pre-allocate compact expert buffers at model-load time instead of lazily on first `mul_mat_id` call. Improves first-token latency on medium-MoE deployments. ~3-4 hours work.
- **`MADV_DONTNEED` on post-copy mmap pages (3.2(g.2))**: after `ggml_ep_shard_lookup` memcpys experts into the local anon buffer, `madvise(MADV_DONTNEED)` on the source mmap region releases the now-redundant page-cache pages. ~138 GB savings on REAP-246B-class. ~30 minutes work + PPL re-verify.

#### Architecture summary

The IPC machinery (`ep_dispatcher` 0.73 μs RTT, env-var bootstrap, NUMA pinning, drone mode, lazy shard) is **complete and correct**. The 13 commits constituting Phase 3.2 deliver a deployable EP capability for medium-MoE. The negative result on REAP-246B-class is a clean closure — bandwidth math doesn't favour partitioning when single-instance already uses 100% of available DDR bandwidth, and on EPYC NPS4 specifically that crossover happens around 150B total params.

[CPU15 handoff](../handoffs/active/large-moe-expert-parallelism.md), [progress 2026-04-25](../progress/2026-04/2026-04-25.md)

### MoE Serving and Offloading Research

- **Flash-MoE (intake-166)**: Pure C/Metal inference engine for Qwen3.5-397B on MacBook Pro -- relevant as reference for memory-efficient MoE serving on consumer hardware. The architecture insights about expert caching may inform our NUMA expert placement strategy. [intake-166](https://github.com/danveloper/flash-moe)

- **FlashMoE SSD offloading (intake-167)**: ML-based cache replacement for SSD-offloaded experts. Not directly applicable (our models fit in RAM) but relevant if we need to run models exceeding 768 GB. Cache replacement strategies for hot/cold experts could inform NUMA-aware expert placement. [intake-167](https://arxiv.org/abs/2601.17063)

- **SpecMoEOff (intake-168)**: Hides offloading latency by overlapping expert loading with speculative decoding. Interesting architecture but not applicable -- our models are fully RAM-resident. The principle of overlapping expert loading with drafting could be relevant for future ultra-large models. [intake-168](https://arxiv.org/abs/2508.21706)

## Actionable for EPYC

- **Deployed**: REAP-246B as architect_coding (50% prune of 480B). In production since 2026-03-29. 82% quality (+9pp), 8.0 t/s (+14%), 139 GB (-44%)

- **Ready to benchmark further**: REAP-25B Q4_K_M (15.19 GB, downloaded, initial benchmarks done). Run at temperatures 0.0/0.3/0.7 per 0xSero's loop-detection methodology. Test NUMA 4-way (fits trivially at 15 GB per quarter-machine). Verify quality gap vs frontdoor hybrid closes with 512+ max_tokens (Phase 2 showed 13pp gap was primarily truncation at 256 tokens)

- **Run REAP ourselves**: Use CerebrasResearch/reap CLI on Qwen3-Coder-30B-A3B at 25%/30%/40% with custom calibration from production orchestrator workload (agentic coding + tool calls + multi-turn). Convert each to GGUF Q4_K_M and benchmark. If 30-40% is safe on our workload, push to 50% + Router KD post-processing (2h investment)

- **Profile Leanstral expert activation**: Run Leanstral Q4_K_M with `--moe-expert-stats` on representative Lean 4 proof workloads. If activation clusters on 20-30 experts, REAP-75% is viable (68 GB to approximately 20 GB). Contingent on Lean 4 proving pipeline maturity

- **Apply REAP to architect_general**: Qwen3-235B-A22B is not in the official Cerebras inventory but is likely supported as Qwen3 family. Even 25% pruning would reduce from approximately 140 GB to approximately 105 GB Q4_K_M, potentially enabling better NUMA fit or concurrent loading

- **Priority**: MEDIUM. The big production win (246B deployment) is done. Further gains from REAP-25B quality validation, custom calibration, and Leanstral profiling are incremental. The highest-value next steps are in KV cache optimization (compaction and selection) rather than further MoE pruning

## Open Questions

- Does REAP-25B quality hold at low temperature (0.0-0.2) on our production workloads? The Goldilocks zone finding suggests low temp is the critical stress test for routing stability
- Can custom calibration from production orchestrator data improve over generic code datasets? Our workload mix (agentic coding, tool calls, multi-turn reasoning) differs from standard code benchmarks
- What is Leanstral's expert activation distribution on Lean 4 proofs? If highly clustered, REAP-75% is viable; if distributed, even 50% may degrade proof quality
- Does stacking REAP-25B with speculative decoding (dm=24) plus NUMA 4-way yield compound gains? 4x15GB instances = 60GB total, well within quarter-machine budget
- Can REAP be applied to Qwen3-235B-A22B (architect_general)? Not in Cerebras inventory but likely supported
- Will Cerebras publish REAP models for future Qwen3.5 hybrid architectures with improved hybrid tolerance?
- At what pruning level does Router KD become cost-effective? Currently "worth it at 50%+" but the exact crossover needs measurement on our models
- Can the double compression pipeline (REAP + quantization) be extended with KV cache compression for a triple stack (expert pruning + weight quantization + KV compression)?

## Related Categories

- [Speculative Decoding](speculative-decoding.md) -- REAP-pruned pure MoE models enable speculation where hybrid models cannot. REAP-25B at dm=24 achieves 39.62 t/s vs hybrid frontdoor at 19.6 t/s with no viable speculation
- [Quantization](quantization.md) -- REAP output is standard safetensors, directly compatible with GGUF quantization via `convert_hf_to_gguf.py`. Double compression pipeline (prune then quantize) achieves approximately 6.5x
- [KV Cache Optimization](kv-cache.md) -- MoE models have different KV patterns than dense; MLA (Leanstral's DeepSeek V3 architecture) reduces KV cache independently of expert pruning via low-rank latent attention
- [Hardware Optimization](hardware-optimization.md) -- NUMA 4-way parallelism delivers larger throughput gains than MoE pruning for models that fit in quarter-machine memory. REAP makes more models fit

## Source References

- [REAP Ecosystem Deep-Dive](../research/deep-dives/0xsero-reap-ecosystem-deep-dive.md) -- REAP algorithm and Theorem 1, Goldilocks zone (30-40%), 0xSero stress testing, calibration recipes, 30 Cerebras models, EvoESAP downgrade, Router KD assessment, MoNE rejection, double compression pipeline
- [Leanstral Architecture Analysis](../research/deep-dives/leanstral-architecture-analysis.md) -- 119B MoE (95% routed expert weights), MLA + DeepSeek V3 architecture, REAP candidacy at 75%, FLTEval results, CPU deployment estimates, complementary to Goedel-Code-Prover
- [REAP Handoff](../handoffs/completed/reap-moe-expert-pruning.md) -- 4-phase evaluation, 246B deployment (+9pp/+14%/-44%), REAP-25B benchmarks, 363B not compelling, answered 6 open questions, gate renormalization v2
- [GPU Acceleration Handoff](../handoffs/active/gpu-acceleration-path.md) -- Grouped GEMM for MoE on GPU (Stream-K, rocWMMA) for future GPU acceleration path
- [Lean Proving Pipeline Handoff](../handoffs/active/lean-proving-pipeline.md) -- Leanstral deployment context and Lean 4 integration
- [Inference Acceleration Index](../handoffs/active/inference-acceleration-index.md) -- REAP in context of broader inference optimization landscape
- [intake-181](https://arxiv.org/abs/2510.13999) REAP paper (arXiv:2510.13999, ICLR 2026) -- Core algorithm, pruning vs merging theorem
- [intake-183](https://github.com/0xsero) 0xSero GitHub -- 196 repos, community REAP practitioner, systematic sweeps
- [intake-184](https://huggingface.co/0xSero) 0xSero HuggingFace -- 28 REAP/AutoRound models, 216 followers
- [intake-185](https://github.com/CerebrasResearch/reap) CerebrasResearch/reap repository -- Apache 2.0, CLI for all Qwen3 MoE models
- [intake-186](https://huggingface.co/cerebras/Qwen3-Coder-REAP-25B-A3B) Cerebras pre-pruned Qwen3-Coder-REAP-25B-A3B -- 128 to 103 experts
- [intake-187](https://huggingface.co/bartowski/cerebras_Qwen3-Coder-REAP-25B-A3B-GGUF) bartowski GGUF quants -- 26 variants including Q4_K_M at 15.19 GB
- [intake-188](https://arxiv.org/abs/2603.06003) EvoESAP (arXiv:2603.06003) -- Non-uniform pruning, helps ERNIE not Qwen3
- [intake-189](https://arxiv.org/abs/2603.02217) Router Knowledge Distillation (arXiv:2603.02217) -- Lightweight router re-training
- [intake-190](https://arxiv.org/abs/2507.00390) MoNE (arXiv:2507.00390, ICLR 2026) -- Novice expert replacement
- [intake-235](https://mistral.ai/news/leanstral) Leanstral 119B (Mistral AI, Apache 2.0) -- MoE+MLA for Lean 4 proofs
- [intake-152](https://docs.vllm.ai/projects/recipes/en/latest/Qwen/Qwen3.5.html) Qwen3.5 serving recipe -- Hybrid MoE+Delta Net configuration
- [intake-166](https://github.com/danveloper/flash-moe) Flash-MoE -- Pure C/Metal inference for MoE on consumer hardware
- [intake-167](https://arxiv.org/abs/2601.17063) FlashMoE SSD offloading -- ML-based expert cache replacement
- [intake-168](https://arxiv.org/abs/2508.21706) SpecMoEOff -- Overlapping expert loading with speculation
- [intake-427] GLM-5.1-555B-A14B-REAP GGUF -- 325GB Q4_K_M, 14B active from 192 experts, 88% Terminal-Bench, 66% SWE-bench Pro, expert count threshold (25% safe / 40% broken)
- [intake-449] OpenAI Privacy Filter (huggingface.co/openai/privacy-filter) -- 2026-04-23: **aggressive small-MoE sparsity reference**. 128 experts with top-4 routing in a 1.5B-total / **50M-active (3.3%)** bidirectional encoder — ~2.6× sparser than our Qwen3.5/3.6-35B-A3B (8.6% active). 96% F1 on PII-Masking-300k. Not for deployment (PII task is off-roadmap), but design reference if `project_learned_routing_controller` upgrades from dense MLP to MoE router. [Deep-dive](../research/deep-dives/openai-privacy-filter-pii-preprocessor.md)
