# Quantization

**Category**: `quantization`
**Confidence**: verified
**Last compiled**: 2026-04-13
**Sources**: 25 documents (0 dedicated deep-dives, 4 handoffs, 2 active handoffs, 19 intake entries + cross-references from 6 deep-dives)

## Summary

Quantization is the foundation of our entire EPYC 9655 inference stack. Every production model runs quantized -- there are no f16 models in the production orchestrator. The standard quant is Q4_K_M, a 4-bit k-quant format in GGUF that reduces model size by approximately 4x (32-bit to 4-bit effective, with mixed-precision block structure) while maintaining quality sufficient for production coding and reasoning tasks. Higher quants (Q6_K, Q8_0) are used for reference benchmarks, and the full range from Q2_K to BF16 is available for most models via community GGUF converters (notably bartowski, who provides 26+ quant variants for popular models).

Our quantization work spans two distinct domains that interact in important ways. **Weight quantization** (model weights stored in GGUF quant types) determines model file size, memory footprint, and per-token compute cost. **KV cache quantization** (key/value cache entries stored at reduced precision during inference) determines context capacity and attention bandwidth. The breakthrough finding in our KV work is that Walsh-Hadamard rotation before quantization eliminates the quality degradation that previously made q4_0 KV unusable: the rotation smooths outlier distributions via orthogonal transform, redistributing magnitude across dimensions so that per-block quantization works uniformly. With Hadamard rotation, q4_0 KV cache achieves PPL +0.017 vs f16 on Qwen2.5-7B -- effectively lossless. This was deployed to production in commit `b51c905` and is now auto-enabled in llama.cpp v3 upstream (PR #21038).

The interaction between weight quantization and other optimization techniques produces some of the most practically important findings in our research. DFlash speculative decoding achieves 6.49 accepted tokens per round on f16 GPU but drops to 27% per-token acceptance on Q4_K_M because quantized hidden states corrupt the conditioning signal -- the single biggest factor in our DFlash conclusion. REAP expert pruning on MoE models produces standard safetensors that feed directly into `convert_hf_to_gguf.py`, enabling a clean "prune then quantize" double compression pipeline that achieves approximately 6.5x total compression. KV cache quantization stacks orthogonally with KV compaction and selection: the theoretical quad-stack ceiling (weight quant + KV quant + compaction + selection) could reach 120x total KV reduction, though pairwise quality validation is still in progress.

The quantization landscape in llama.cpp is evolving. The mainstream path is ggerganov's Hadamard rotation for existing quant types (PR #21038), which auto-applies Walsh-Hadamard transform when KV types are quantized. More exotic approaches -- TQ3_1S (Walsh-Hadamard transform weight quantization at 3.5 bits), TurboQuant (extreme KV cache compression), PolarQuant (polar transformation for KV cache) -- have been evaluated and placed on monitor-only status. TQ3_1S was downgraded due to immaturity (3 commits, 1 contributor, no CPU kernels), wrong benchmarking target (vs Q4_0 not Q4_K_M), and a 2.2x speed disadvantage vs Hadamard+q4_0 on EPYC 9975 even with all ecosystem fixes. TurboQuant and PolarQuant were abandoned after Hadamard+q4_0 matched their quality with zero complexity. The lesson: incremental improvements to existing, well-optimized quant types consistently beat exotic new formats on CPU hardware where AVX-512 dequant throughput dominates.

## Key Findings

### Weight Quantization

- **Q4_K_M is the production standard**: 4-bit k-quant with mixed-precision block structure. Used for all production models: Qwen3-Coder-30B-A3B frontdoor (approximately 18 GB), Qwen2.5-Coder-32B coder escalation (approximately 18.5 GB), REAP-246B architect_coding (139 GB), Qwen3-235B-A22B architect_general (approximately 140 GB). Quality is sufficient for agentic coding, tool calls, multi-turn reasoning, and mathematical problem solving. Q4_K_M was confirmed as the optimal coder quant in March 2026 after sweep testing. [Project memory: project_coder_quant_decision.md]

- **Q4_K_M degrades DFlash conditioning signal**: DFlash speculative decoding requires extracting hidden states from specific target model layers as conditioning input to the drafter. On Q4_K_M, per-token acceptance drops from 6.49 (f16 GPU) to 27%, yielding only 1.4% block acceptance. The quantization noise in extracted hidden states -- which are dequantized f32 approximations of what would be exact f32 in an f16 model -- is sufficient to corrupt the DFlash conditioning beyond recovery. This was the decisive factor in concluding DFlash is not viable for our Q4_K_M stack. [DFlash deep-dive](../research/deep-dives/dflash-dart-diffusion-speculation.md), [DFlash handoff](../handoffs/completed/dflash-block-diffusion-speculation.md)

- **REAP + quantization is a clean pipeline**: REAP expert pruning outputs standard HuggingFace safetensors with fewer experts per MoE layer. `convert_hf_to_gguf.py` processes these identically to unpruned models. The GGUF files use standard architecture strings (`qwen3moe`, `deepseek2`) and require no custom code. bartowski has produced 26 quant variants for REAP-25B alone. The double compression pipeline (REAP 50% + quantization) achieves approximately 6.5x total compression: 0xSero demonstrated this on GLM-4.7 (700 GB to 92 GB with AutoRound W4A16). [REAP deep-dive](../research/deep-dives/0xsero-reap-ecosystem-deep-dive.md)

- **GGUF ecosystem is the deployment gateway**: All models in our stack go through GGUF conversion as the final deployment step. Community converters (bartowski, unsloth, jackcloudman) provide pre-quantized GGUFs for popular models. For custom models (REAP outputs, Memento LoRA fine-tunes), the `convert_hf_to_gguf.py` and `convert_lora_to_gguf.py` scripts handle conversion. LoRA adapters are loadable at inference with `llama-server --lora adapter.gguf`. The GGUF format supports arbitrary metadata tensors, which is relevant for future extensions like steering vectors or per-token attention biases. [Various handoffs]

### KV Cache Quantization

- **Hadamard+q4_0 is quality-neutral and deployed**: Walsh-Hadamard rotation (orthogonal transform that preserves norms) applied before q4_0 quantization of KV cache entries. PPL increase of +0.017 on Qwen2.5-7B at 512 tokens. Needle-in-haystack: 9/9 correct at 1K/4K/16K on Coder-32B. Zero overhead in speed at short context (within 2% of f16). Production config: `-ctk q4_0 -ctv f16` for pure-attention models (Qwen2.5-Coder-32B), `-ctk q4_0 -ctv q4_0` for hybrid SSM models (Qwen3.5-35B-A3B where 75% recurrent layers absorb quantization error). Deployed since commit `b51c905` on `production-consolidated-v2`. [KV cache quantization handoff](../handoffs/completed/kv-cache-quantization.md)

- **q4_0 Key cache degrades at extended context without Hadamard**: At 32K context on pure-attention Qwen2.5-7B, q4_0/q4_0 (both K and V quantized) produces garbage output; q8_0/q4_0 remains correct. The cumulative quantization error in Key vectors compounds over long sequences, corrupting attention patterns. Hadamard rotation fixes this by distributing magnitude uniformly before quantization, but the safe production config still uses f16 for Values on pure-attention models to maintain quality margin. For hybrid SSM models, q4_0/q4_0 is validated safe because the 75% recurrent layers provide an alternative information path. [KV cache quantization handoff](../handoffs/completed/kv-cache-quantization.md)

- **Upstream auto-enables Hadamard rotation in v3**: llama.cpp v3 upstream PR #21038 by ggerganov (`744c0c731`) auto-applies Walsh-Hadamard rotation when KV types are quantized. The `--kv-hadamard` flag from our production branch is superseded. Quality improvements reported: Q4_0 KV PPL improves 25-77% on small models, Q8_0 with rotation matches f16 on reasoning benchmarks. This is a free upgrade on rebuild -- no model re-quantization needed. [TQ3 monitor handoff](../handoffs/active/tq3-quantization-evaluation.md), [v3 rebuild handoff](../handoffs/active/llama-cpp-v3-upstream-rebuild.md)

- **At long context, KV quantization provides throughput gain beyond memory savings**: At short context (4K or less), attention is 7-12% of per-token time -- KV quantization saves memory only. At 16K+, attention rises to 25-35% and becomes compute-bound. At very long sequences (S >> d_model), attention exceeds 50%. Fewer KV bytes means faster attention matmuls, so KV compression delivers a throughput improvement proportional to the attention fraction. The +9% wall time increase observed at 32K (q8_0/q4_0 with dequant overhead) likely reflects dequant cost offsetting the attention speedup -- upstream's auto-rotation may be more optimized. [KV cache quantization handoff](../handoffs/completed/kv-cache-quantization.md)

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

- **Deployed**: Hadamard+q4_0 KV cache quantization (production since `b51c905`, auto-enabled in v3 upstream). Q4_K_M weight quantization across all production models. REAP+Q4_K_M double compression for architect_coding (246B)

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

## Related Categories

- [KV Cache Optimization](kv-cache.md) -- KV quantization is the first deployed layer of the four-layer KV compression stack. Hadamard+q4_0 provides the foundation that compaction (AM), selection (Expected Attention/TriAttention), and block masking (Memento) build upon
- [Speculative Decoding](speculative-decoding.md) -- Weight quantization (Q4_K_M) determines verification cost profile (f16: 1.69x at N=64 vs Q4_K_M: 4-5x). Hidden state quantization kills DFlash acceptance (27% vs 6.49)
- [MoE Optimization](moe-optimization.md) -- REAP pruning produces standard safetensors compatible with GGUF quantization. Double compression pipeline (prune + quantize) achieves approximately 6.5x total
- [Hardware Optimization](hardware-optimization.md) -- AVX-512 dequant throughput determines which quant formats are viable on CPU. TQ3's codebook lookup is 2.2x slower than q4_0 dequant despite theoretical bit-rate advantage

## Source References

- [KV Cache Quantization Handoff](../handoffs/completed/kv-cache-quantization.md) -- Hadamard Phase 1 deployed, hybrid buffer archived, TurboQuant/PolarQuant/QJL abandoned, split attention working but unnecessary, long-context degradation analysis, production validation results
- [TQ3 Monitor Handoff](../handoffs/active/tq3-quantization-evaluation.md) -- TQ3_1S on monitor-only status, PR #21038 Hadamard auto-rotation, PR #21089 CPU TurboQuant, ChunkKV tracking
- [AM Handoff](../handoffs/active/attention-matching-kv-compaction.md) -- Compaction validated on Q4KM Coder-32B, stacking hypothesis
- [TriAttention Handoff](../handoffs/active/triattention-kv-selection.md) -- Selection + quantization stacking gates (S3)
- [REAP Handoff](../handoffs/completed/reap-moe-expert-pruning.md) -- Double compression pipeline, bartowski GGUF availability
- [DFlash Deep-Dive](../research/deep-dives/dflash-dart-diffusion-speculation.md) -- Q4_K_M hidden state degradation (6.49 to 27% acceptance)
- [REAP Deep-Dive](../research/deep-dives/0xsero-reap-ecosystem-deep-dive.md) -- bartowski 26 quant variants, double compression pipeline, GGUF conversion path
- [TriAttention Deep-Dive](../research/deep-dives/triattention-kv-selection-cluster.md) -- Quantization interaction unknown for trigonometric/Gaussian scoring
- [Memento Deep-Dive](../research/deep-dives/memento-iterative-reasoning-cluster.md) -- KV quantization + block masking + selection triple-stack ceiling, LoRA-to-GGUF conversion
- [Leanstral Analysis](../research/deep-dives/leanstral-architecture-analysis.md) -- GGUF availability (Q4_K_M approximately 68 GB), community converters
- [v3 Rebuild Handoff](../handoffs/active/llama-cpp-v3-upstream-rebuild.md) -- PR #21038 auto-Hadamard
- [intake-191](https://research.google/blog/turboquant-redefining-ai-efficiency-with-extreme-compression/) TurboQuant -- Extreme KV cache compression (abandoned)
- [intake-192](https://arxiv.org/abs/2502.02617) PolarQuant -- Polar transformation KV quantization (abandoned)
- [intake-193](https://arxiv.org/abs/2406.03482) QJL -- 1-bit JL transform for KV cache (evaluated, abandoned)
- [intake-194](https://github.com/spiritbuun/llama-cpp-turboquant-cuda) llama-cpp-turboquant-cuda -- CUDA TurboQuant fork (GPU-only, not applicable)
- [intake-195](https://github.com/ggml-org/llama.cpp/discussions/20969) TurboQuant llama.cpp discussion -- Community discussion on KV compression
- [intake-246](https://github.com/turbo-tan/llama.cpp-tq3) llama.cpp-tq3 -- TQ3_1S weight quantization (monitor only)
- [intake-187](https://huggingface.co/bartowski/cerebras_Qwen3-Coder-REAP-25B-A3B-GGUF) bartowski GGUF quants -- 26 variants of REAP-25B
- [intake-182](https://arxiv.org/abs/2309.05516) AutoRound/SignRound -- Not applicable for llama.cpp/GGUF stack
- [intake-165](https://arxiv.org/abs/2504.12285) BitNet b1.58 -- Ternary quantization, worth investigating for future architectures
