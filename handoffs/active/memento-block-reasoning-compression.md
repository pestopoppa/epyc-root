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

### Composability — Quad-Stack KV Compression
- **Block masking (Memento)**: 2-3x — removes entire reasoning blocks (WHICH semantic blocks survive)
- **KV quantization (Hadamard+q4_0)**: 2-4x — compresses each surviving KV entry (deployed, `b51c905`) (HOW tokens stored)
- **KV compaction (Attention Matching)**: 10x — constructs compact latent KV entries with fitted biases/values (planning, [attention-matching-kv-compaction.md](attention-matching-kv-compaction.md)) (HOW MANY entries exist)
- **KV selection (TriAttention/Expected Attention)**: 2-10x — keeps only important tokens (evaluating, triattention-kv-selection.md). Note: AM compaction subsumes selection at 20x+; redundant to stack both.
- Theoretical combined (quant × compaction × masking): **up to 120x**. Conservative: **40x** (quant × compaction alone, no selection or masking needed). Quality cliff under multi-layer compression is the key unknown — each pair tested independently.

### Serving Throughput
- Memento vLLM: 4,290 vs 2,447 tok/s at full concurrency (1.75x), B200 GPU
- Mechanism: block masking frees KV entries mid-generation → higher effective batch size
- For our single-user llama.cpp stack: benefit is faster generation at long contexts (less memory bandwidth for KV attention)

## Implementation Path

### S1: llama.cpp Block Masking Feasibility (prerequisite) — FEASIBILITY CONFIRMED (2026-04-13)

**API correction**: The handoff originally referenced `llama_kv_self_seq_rm()` — this does NOT exist. The correct API is:
- **Public**: `llama_memory_seq_rm(llama_memory_t mem, llama_seq_id seq_id, llama_pos p0, llama_pos p1)` at `include/llama.h:733`
- **C++ virtual**: `llama_memory_i::seq_rm()` at `src/llama-memory.h:103`
- **Concrete**: `llama_kv_cache::seq_rm()` at `src/llama-kv-cache.cpp:388`

**Feasibility assessment**: YES — `llama_memory_seq_rm()` can serve as the Memento block eviction primitive.

**Call chain**: `llama_memory_seq_rm()` → `mem->seq_rm()` (virtual dispatch) → `llama_kv_cache::seq_rm()` → iterates `v_cells[stream]`, checks `cells.pos_in(i, p0, p1)`, calls `cells.seq_rm(i, seq_id)` → clears seq bit, if no sequences remain: frees cell (`pos[i] = -1`, removed from `used` set)

**Key findings**:
1. **Mid-sequence removal**: Fully supported. Any contiguous position range [p0, p1) can be removed. Always succeeds (returns true).
2. **Position gap**: After removal, remaining cells keep original positions. No automatic shifting. This is CORRECT for Memento — the dual information stream requires preserving original RoPE phases.
3. **Cell freeing**: Freed cells are immediately reusable by `find_slot()`. Data buffers are pre-allocated/static (not freed), so benefit is effective context extension, not peak memory reduction.
4. **ISWA**: Transparent — `llama_kv_cache_iswa::seq_rm()` delegates to both base and SWA caches.
5. **Block tracking gap**: Partial sequence removal does NOT deallocate paged attention blocks. This is a metadata leak (blocks logically empty but still allocated). Only matters if paged attention is enabled.

**DO NOT close the position gap with `seq_add`**: The KV states after the evicted block carry implicit information from attending to the reasoning block during their original computation. Shifting RoPE positions would corrupt this encoding.

**Test skeleton**: Written at `tests/test-memento-block-masking.cpp` in llama.cpp-experimental. 5 test functions: basic eviction, gap semantics, post-eviction generation, multi-block iterative eviction, memory usage check. Compiles against current headers; requires `--model <path>` at runtime.

**Next**: S1 runtime validation (requires model server) — run the test skeleton with a loaded model to verify attention correctness after mid-sequence eviction.

**Builds on**: Our hybrid-precision buffer work (split attention, eviction from recent→old in `kv-cache-quantization.md`). Block masking is architecturally simpler — straight eviction, no demotion/requantization.

### S2: Model Fine-Tuning (requires S1 success) — DESIGN COMPLETE (2026-04-13)

**Dataset**: OpenMementos-228K downloaded at `/mnt/raid0/llm/data/openmementos/` (228,557 examples, 4.7 GB). Default config (20 shards) has training-ready block/summary formatted responses. Full config (39 shards, 9.2 GB) includes intermediate pipeline outputs (sentences, block boundaries, block summaries).

**Dataset stats**: ~9 blocks/response median, ~12K response tokens mean, 54% math / 27% science / 19% code. Special tokens: `<|block_start|>`, `<|block_end|>`, `<|summary_start|>`, `<|summary_end|>` — all balanced, 100% have `<think>` wrapper + answer section.

**Training script**: `/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/memento_sft.py` — dry-run validated.

**Two-stage LoRA design**:
1. **Stage 1 (full attention, format learning)**: Standard causal attention. Model learns to generate block/summary token structure. 2 epochs, lr=2e-4, seq_len=4096.
2. **Stage 2 (memento attention, compression learning)**: Custom 2D attention mask that blocks future tokens from attending to completed block content (only summaries persist). Teaches the model that block content is transient. 1 epoch, lr=5e-5, seq_len=4096. The memento mask removes ~59% of causal attention positions.

**LoRA config**: rank=16, alpha=32, dropout=0.05, targets=[q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj]. ~393K trainable params for 1.7B model (0.02% of base).

**Model ladder** (CPU-feasible validation path):
| Model | BF16 Mem | LoRA Params | Est. Time/Epoch | Feasible? |
|-------|----------|-------------|-----------------|-----------|
| Qwen3-0.6B | 1.2 GB | 197K | ~19h | Yes (smoke test) |
| Qwen3-1.7B | 3.4 GB | 393K | ~54h | Yes (validation target) |
| Qwen3-8B | 16 GB | 786K | ~11 days | Marginal |
| Qwen3-32B | 64 GB | 983K | ~42 days | No — requires GPU QLoRA |

**Blockers**: `peft`, `trl` packages not installed (pip install). 32B requires GPU — CPU training is infeasible at production scale. Recommend: validate on 1.7B (CPU), then rent GPU time for 32B QLoRA.

**GGUF conversion path**: Trained LoRA adapter converts to GGUF via `llama.cpp/convert_lora_to_gguf.py`, loadable at inference with `llama-server --lora adapter.gguf`.

**Validation plan**:
1. MATH-500 accuracy (memento vs base)
2. Format compliance (block/summary token pairing)
3. Compression ratio (block tokens vs memento tokens)
4. Integrate with S1 block masking for end-to-end KV savings test

### S3: Deployment Integration (requires S1 + S2)

1. Wire block masking into `orchestrator_stack.py` as inference-time feature flag
2. Implement Fold/Unfold toggle (from Accordion-Thinking) gated by difficulty_signal band
3. Combine with `short-m@k` voting for zero-accuracy-cost operation
4. Stack with existing Hadamard+q4_0 quantization

## Open Questions

- ~~Can block masking be implemented in llama.cpp via existing `llama_memory_seq_rm()`?~~ **YES** — confirmed 2026-04-13, mid-sequence removal works, position gap semantics are correct for Memento
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
