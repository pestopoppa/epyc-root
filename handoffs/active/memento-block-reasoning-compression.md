# Memento: Block-Level Reasoning Compression with KV Cache Masking

**Status**: active — research evaluation + llama.cpp feasibility assessment
**Created**: 2026-04-08 (via research intake)
**Updated**: 2026-04-09 (deep-dive completed)
**Categories**: kv_cache, training_distillation, context_extension, inference_serving
**Deep-dive**: `research/deep-dives/memento-iterative-reasoning-cluster.md`

## Objective

Investigate Memento-style block reasoning compression for EPYC stack — training models to segment reasoning into blocks, compress each block into a dense summary (memento), and mask original block KV states while retaining memento KV states. This could reduce peak KV cache 2-3x during reasoning while preserving accuracy, composing with our existing Hadamard+q4_0 KV quantization.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-289 | Memento: Teaching LLMs to Manage Their Own Context | high | new_opportunity |
| intake-290 | OpenMementos-228K (MIT, 13.9GB) | high | new_opportunity |
| intake-292 | InftyThink (ICLR 2026, arxiv:2503.06692) | high | new_opportunity |
| intake-293 | InftyThink+ (arxiv:2602.06960) | high | new_opportunity |
| intake-294 | Accordion-Thinking (arxiv:2602.03249) | high | new_opportunity |

## Key Findings (Deep Dive 2026-04-09)

### Dual Information Stream (Memento's unique contribution)
- KV cache states computed while a block is visible carry **implicit information** beyond the summary text
- Recomputing KVs without block context: 66.1% → 50.8% AIME24 (-15.3pp)
- Probing: passcode injected into masked block is recoverable from downstream memento KV states at 23-27% (vs 10% chance), signal concentrates in deeper layers
- This is **architectural, not learned** — confirmed on toy transformer, persists across training checkpoints
- **Implication**: Text-level compression approaches (InftyThink, Accordion, our context-folding) have a fundamental ~15pp ceiling vs. KV-retaining approaches for reasoning tasks

### Accuracy Gap Is Consistency, Not Capability
- Pass@64 Jaccard similarity: **96.4%** between Base and Memento solved sets
- Majority voting at **k=3** recovers base accuracy without RL
- **EPYC opportunity**: Combine Memento KV savings + existing `short-m@k` voting (intake-129) = 2-3x KV reduction at ZERO accuracy cost

### Scale Helps
- Accuracy gap: -6.3pp at 8B → -3.5pp at 32B (averaged across 5 benchmark groups)
- Our production 32B architect would see minimal accuracy loss
- MATH-500 is near-lossless (<1pp gap) across all scales

### Composability — Triple-Stack KV Compression
- **Block masking (Memento)**: 2-3x — removes entire reasoning blocks
- **KV quantization (Hadamard+q4_0)**: 2x — compresses each surviving KV entry (deployed, `b51c905`)
- **KV selection (TriAttention/Expected Attention)**: 2-10x — keeps only important tokens (evaluating, triattention-kv-selection.md)
- Theoretical combined: 8-60x. Conservative estimate: 4x even without selection.

### Serving Throughput
- Memento vLLM: 4,290 vs 2,447 tok/s at full concurrency (1.75x), B200 GPU
- Mechanism: block masking frees KV entries mid-generation → higher effective batch size
- For our single-user llama.cpp stack: benefit is faster generation at long contexts (less memory bandwidth for KV attention)

## Implementation Path

### S1: llama.cpp Block Masking Feasibility (prerequisite)

Evaluate whether `llama_kv_self_seq_rm()` in v3 upstream can serve as block eviction primitive:
1. Inject special tokens (`<|block_start|>`, `<|block_end|>`, `<|summary_start|>`, `<|summary_end|>`) into generation
2. After `<|summary_end|>`: call `llama_kv_self_seq_rm()` for the token range of the preceding block
3. Verify attention correctness — future tokens should not attend to evicted positions

**Builds on**: Our hybrid-precision buffer work (split attention, eviction from recent→old in `kv-cache-quantization.md`). Block masking is architecturally simpler — straight eviction, no demotion/requantization.

**Critical dependency**: llama.cpp v3 upstream KV eviction API maturity (tracked in `llama-cpp-v3-upstream-rebuild.md`)

### S2: Model Fine-Tuning (requires S1 success)

1. Download OpenMementos-228K (MIT, HuggingFace)
2. LoRA SFT on Qwen3-32B (our architect) — small compute footprint
3. Two-stage: Stage 1 full attention (format learning), Stage 2 memento attention (compression learning)
4. Validate on MATH-500/GPQA-D (our production benchmark suites)

### S3: Deployment Integration (requires S1 + S2)

1. Wire block masking into `orchestrator_stack.py` as inference-time feature flag
2. Implement Fold/Unfold toggle (from Accordion-Thinking) gated by difficulty_signal band
3. Combine with `short-m@k` voting for zero-accuracy-cost operation
4. Stack with existing Hadamard+q4_0 quantization

## Open Questions

- Can block masking be implemented in llama.cpp via existing `llama_kv_self_seq_rm()`?
- Does Memento compose with speculative decoding? Block masking changes attention patterns and KV cache layout.
- Is SFT on OpenMementos sufficient for GGUF-quantized models, or does quantization degrade memento quality?
- How does the 7K block length cap interact with our difficulty-band token budgets?
- Can InftyThink+'s efficiency reward replace our regex-based difficulty signal for reasoning budget allocation?

## Relationship to Existing Handoffs

- **reasoning-compression.md**: Memento is a new Tier 3+ approach. Updated 2026-04-08 with Memento cluster section.
- **context-folding-progressive.md**: OpenMementos data pipeline (boundary scoring + iterative refinement) validates Phase 2 methodology and could generate Phase 3 training data.
- **kv-cache-quantization.md**: Memento KV masking is orthogonal to quantization — multiplicative when stacked.
- **triattention-kv-selection.md**: Third KV compression layer — all three compose.
- **llama-cpp-v3-upstream-rebuild.md**: KV eviction API is the critical dependency.

## Failure Modes

1. **Excessive generation**: Block masking can induce 3x more tokens on some problems (Figure 5c). Mitigation: block length cap (7K) + reasoning length alarm (Action 9).
2. **Sliding-window incompatibility**: Models with sliding-window attention (Olmo-3) see minimal KV savings (0.85-0.93x). Our Qwen2.5/Qwen3 models use full attention — not affected.
3. **SFT quality risk**: Fine-tuning already-trained reasoning models always risks degradation. Memento control runs (SFT on OpenThoughts without block annotations) show 2-5pp drops.
