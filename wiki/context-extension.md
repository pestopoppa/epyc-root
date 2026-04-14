# Context Extension

**Category**: `context_extension`
**Confidence**: inferred
**Last compiled**: 2026-04-13
**Sources**: 19 documents (0 dedicated deep-dives, 4 cross-referenced deep-dives, 3 active handoffs, 12 intake entries)

## Summary

Context extension research addresses the fundamental question: how do you process sequences longer than a model's training context? This category spans the spectrum from positional encoding methods (RoPE scaling, YaRN) that stretch the native attention window, through memory-augmented architectures (MemAgent, Memento) that reformulate long-context as iterated short-context, to iterative reasoning approaches (InftyThink, Accordion-Thinking) that interleave compression with generation. Unlike context *management* -- which compresses information within a given window -- context *extension* changes the window itself or works around its limits entirely.

For the EPYC stack running CPU inference on the 9655, context extension is constrained by two hard realities. First, KV cache memory scales linearly with context length: at 256K context with Q4 KV quantization on a 32B model, memory consumption is substantial and eats into the RAM budget shared with model weights. Second, prefill latency on CPU scales roughly linearly with context length, meaning a 512K prompt takes approximately twice as long as 256K to process. These constraints make the "just scale context" approach from the GPU world impractical -- we cannot simply set context to 1M and accept the latency. Instead, the optimal strategy is a composition: use YaRN for modest extension (256K to 512K-1M) when needed for long-document tasks, layer KV compression to reduce the memory cost, and deploy memory-augmented architectures for extreme lengths where native attention is infeasible.

The most striking finding in this domain is that native long-context models consistently fail at extreme lengths while memory-augmented approaches succeed. MemAgent-14B maintains 75-78% accuracy from 7K through 3.5M tokens (a 437x extrapolation from its 8K training window), while Qwen2.5-14B-1M collapses to 0% at 896K and QwenLong-L1-32B drops to 11.7% at 896K. The mechanism is simple: by reformulating long-context as sequential segment processing with a fixed 1K memory buffer, MemAgent achieves O(N) linear complexity versus O(N^2) attention. However, the sequential overhead makes this impractical for CPU inference: 100K documents require ~24 minutes per query on our hardware.

The related research on iterative reasoning compression (InftyThink, InftyThink+, Accordion-Thinking, Memento) operates at the intersection of context extension and context management. These approaches train models to self-compress their reasoning chains into blocks with periodic summaries, achieving 2-4x throughput gains while maintaining accuracy. The most significant contribution is Memento's discovery of a dual information stream: KV cache states computed while attending to reasoning blocks carry implicit information that text-level summaries cannot capture, creating a ~15pp accuracy ceiling for text-only compression on hard reasoning tasks. This finding reshapes the entire context management landscape by demonstrating that KV-level approaches are fundamentally superior for reasoning workloads.

The practical path for EPYC is layered: YaRN for the 256K-to-1M extension case (zero overhead, fully supported in llama.cpp), KV cache quantization (already deployed) and block masking (feasibility confirmed) for memory efficiency at extended lengths, and eventually MemAgent-style chunked processing for extreme-length documents where no native method suffices.

## Key Findings

### Positional Encoding Extension (YaRN)

- **YaRN extends context 2-4x with zero inference overhead**: RoPE dimensions are divided into groups with different linear scaling factors. Fine-tuned mode extends ~2x with 0.1% of pre-training data; dynamic mode extends further at inference time with zero fine-tuning. RoPE embeddings are pre-computed, so there is no per-token cost. [yarn-context-extension-research handoff](../handoffs/active/yarn-context-extension-research.md)

- **llama.cpp fully supports YaRN**: Dedicated CLI flags (`--rope-scaling yarn`, `--rope-scale N`, `--yarn-orig-ctx N`, plus fine-tuning parameters `--yarn-ext-factor`, `--yarn-attn-factor`, `--yarn-beta-slow`, `--yarn-beta-fast`). Our models support extension: Qwen3.5 supports 256K native + YaRN to 1M; Qwen3-Next-80B supports 256K native + YaRN to 1M (RULER 91.8% avg across 4K-1M). [yarn-context-extension-research handoff](../handoffs/active/yarn-context-extension-research.md)

- **Quality degradation at extended lengths is an open question for our specific hardware**: The RULER accuracy curve from 256K to 1M with YaRN on CPU inference has not been measured. KV cache memory at 1M context is the primary concern -- 6x KV compression via TurboQuant-style techniques (intake-191, intake-192, intake-193) could make this practical but is not yet implemented beyond our existing Hadamard+q4_0 quantization.

### Memory-Augmented Architectures

- **MemAgent achieves 437x context extrapolation**: Trained at 8K, tested at 3.5M. RL-MemAgent-14B maintains 75-78% accuracy across this entire range, while native long-context models (Qwen2.5-14B-1M, QwenLong-L1-32B, DeepSeek-R1-Distill-32B) collapse beyond 224K. A 14B model beats a 32B model at all lengths. [memagent-rl-memory.md](../research/deep-dives/memagent-rl-memory.md)

- **The mechanism is sequential segment processing with overwriting memory**: For each 5K-token segment, the model reads the segment plus accumulated 1K memory, produces a new 1K memory that completely overwrites the previous. Total context per call is ~8K tokens. The simplicity is the strength -- no DAG, no structured store, just free-form prose overwrite. But this is also the weakness: information loss is irreversible, and the sequential chain prevents parallelism. [memagent-rl-memory.md](../research/deep-dives/memagent-rl-memory.md)

- **RL training is critical -- prompted-only memory agents still degrade**: Vanilla Qwen2.5 shows severe degradation beyond 112K. Prompted memory agent (no RL) improves but still declines. Only RL-trained MemAgent achieves near-flat accuracy across the full range. This means simply prompting a model to "summarize and remember" is insufficient -- the compaction policy must be learned from task rewards. [memagent-rl-memory.md](../research/deep-dives/memagent-rl-memory.md)

- **CPU inference makes MemAgent impractical for interactive use**: At Qwen2.5-14B Q4_K_M (~14 t/s on our hardware), each 1K-token memory update takes ~73 seconds. A 100K document (20 segments) requires ~24 minutes; 3.5M requires ~14 hours. The technique is applicable only to offline batch processing on our stack, not interactive queries. [memagent-rl-memory.md](../research/deep-dives/memagent-rl-memory.md)

### Iterative Reasoning and Compression

- **InftyThink+ achieves +21pp on AIME24 via iterative summarization with RL**: Starting from DeepSeek-R1-Distill-Qwen-1.5B baseline of 26.7%, InftyThink+ RL reaches 50.9%. The sawtooth memory pattern (generate reasoning, summarize, continue from summary) enables unbounded reasoning chains within fixed context. Task+efficiency RL variant trades 3.4pp for 60-70% latency reduction (77.6s to 48.4s). [memento-iterative-reasoning-cluster.md](../research/deep-dives/memento-iterative-reasoning-cluster.md)

- **Accordion-Thinking provides a runtime Fold/Unfold toggle**: Same model, same weights, user chooses compressed (Fold, 3-4x throughput) or full (Unfold, maximum accuracy) at request time. After RL training, the accuracy gap vanishes -- Fold matches Unfold at 52.7 vs 52.2 macro score on math benchmarks. This is the ideal interface for difficulty-adaptive routing. [memento-iterative-reasoning-cluster.md](../research/deep-dives/memento-iterative-reasoning-cluster.md)

- **Memento's dual information stream reveals a fundamental limit of text-only extension**: KV cache states computed while a reasoning block is visible carry implicit information. Recomputing KV states without block context drops AIME24 from 66.1% to 50.8% -- a 15.3pp gap from identical text. Probing shows information from masked blocks propagates at 23-27% recovery through memento KV chains, concentrating in deeper layers. This is architectural, not learned. Any text-level context extension (InftyThink, Accordion-Thinking, our context-folding, or even simple summarization) hits this ceiling on hard reasoning tasks. [memento-iterative-reasoning-cluster.md](../research/deep-dives/memento-iterative-reasoning-cluster.md)

- **ReSum shows diminishing returns from summarization at 128K**: At 64K context, summarization yields +5 P@1. At 128K, only +0.9. At large windows, the raw history is mostly usable and compression adds noise. This implies that context extension via YaRN (keeping raw content) may be preferable to compression-based approaches for tasks below the extended context limit. [resum-context-summarization.md](../research/deep-dives/resum-context-summarization.md)

### KV Cache Efficiency at Extended Lengths

- **Multi-layer KV compression makes long context feasible**: Four orthogonal compression layers can compose: (1) Block masking (Memento, 2-3x -- removes entire reasoning blocks), (2) KV quantization (Hadamard+q4_0, 2x -- compresses each KV entry, already deployed), (3) KV compaction (Attention Matching, 10x -- constructs compact latent KV entries), (4) KV selection (TriAttention, 2-10x -- keeps only important tokens). Conservative combined estimate: 40x. Theoretical maximum: 120x. Quality cliff under multi-layer stacking is the key unknown. [memento-iterative-reasoning-cluster.md](../research/deep-dives/memento-iterative-reasoning-cluster.md)

- **TurboQuant achieves 6x+ KV memory reduction to 3-4 bits**: Combining PolarQuant (polar coordinate compression) and QJL (1-bit Johnson-Lindenstrauss transform) for data-oblivious KV quantization. 8x attention speedup on H100, perfect needle-in-haystack accuracy. At 1M context, KV cache dominates RAM; this level of compression would make YaRN extension to 1M practical on our hardware. [intake-191, intake-192, intake-193]

- **Context rot compounds at extended lengths**: intake-273 (Chroma research) confirms performance degrades non-linearly with input length. Distractors (topically related but incorrect content) amplify degradation. This means that naively extending context with YaRN without also improving the model's ability to attend selectively is counterproductive for certain task types. Sparse attention or selective retrieval becomes more important as context grows. [intake-273]

### Recursive and Infinite-Horizon Approaches

- **Recursive Language Models (intake-153) provide the theoretical foundation**: The EPYC orchestrator implements approximately 80% of the RLM architecture -- multi-model delegation, context management through summarization, tool-augmented generation. The remaining 20% (learned compaction policies, process rewards for compression quality) maps to the context-folding Phase 3 roadmap. [intake-153]

- **RTK achieves 60-90% token reduction across 100+ commands**: A practical tool-level approach to context extension -- by compressing tool outputs before they enter context, the effective context window is extended by 60-90% for tool-heavy sessions without any model-level changes. Security concerns (shell injection, telemetry, CI trust bypass) preclude direct adoption, but the compression strategies inform our native Phase 2 implementation. [intake-259]

## Actionable for EPYC

### Implemented (Production)

- **KV cache quantization (Hadamard+q4_0)**: Deployed in production (`b51c905`). 2x KV compression, orthogonal to all other techniques. This is the foundation layer for long-context support.
- **Tool output compression**: 7 command handlers achieving 60-90% reduction. Effectively extends context by reducing the token cost of tool-heavy sessions.
- **Session compaction at 75% threshold**: Externalizes context to disk with structured index when approaching window limits. Configurable trigger ratio.

### In Progress

- **Memento block masking in llama.cpp**: Feasibility confirmed 2026-04-13. `llama_memory_seq_rm()` supports mid-sequence removal with correct position gap semantics. Training script for OpenMementos-228K ready with two-stage LoRA design. Would compose with existing KV quantization for 4x+ combined compression. Blocked on model fine-tuning compute (CPU training of 1.7B is feasible at ~54 hours; 32B requires GPU).
- **Context-folding two-level condensation**: Phase 1 complete. Granular blocks plus deep consolidation at boundaries. Extends effective context by reducing the token cost of conversation history -- complementary to positional extension.

### Planned

- **YaRN evaluation on our hardware**: Measure RULER accuracy degradation from 256K through 1M with YaRN on Qwen3.5 and Qwen3-Next-80B. Key questions: KV cache memory at 1M, speed impact on generation, quality curve shape.
- **KV compaction (Attention Matching)**: Constructs compact latent KV entries with fitted biases/values. 10x compression potential. Currently in planning stage (attention-matching-kv-compaction handoff). Would compose with quantization and block masking.
- **TriAttention KV selection**: Importance-based token selection for KV cache. 2-10x additional compression. Under evaluation (triattention-kv-selection handoff). Note: at 20x+ compaction via Attention Matching, selection becomes redundant.
- **Accordion-Thinking Fold/Unfold toggle**: Runtime choice between compressed (3-4x throughput) and full modes. Maps naturally to our difficulty-band routing: easy problems get Fold mode, hard problems get Unfold. Requires model fine-tuning with RL.

### Not Actionable

- **MemAgent for interactive use on CPU**: Sequential chain with ~73 seconds per 1K-token segment makes this viable only for offline batch processing. A 100K document takes ~24 minutes. However, the RL-trained compaction policy concept informs our session compaction quality improvements.
- **Native 1M context without KV compression**: KV cache memory at 1M tokens is prohibitive on our 384GB RAM budget shared with model weights. Requires TurboQuant-level KV compression (6x+) first.
- **InftyThink/InftyThink+ direct adoption**: Requires SFT+RL training pipeline with verl framework. The iterative summarization pattern is implementable at the orchestrator level without model training (our context-folding approximates this), but the learned compression quality is not replicable without RL.
- **MSA (Memory Sparse Attention, intake-245)**: End-to-end memory model scaling approach. Not applicable to our serving-only stack.
- **In-Place Test-Time Training (intake-285)**: Requires gradient computation during inference. Incompatible with GGUF serving.

## Open Questions

- What is the RULER accuracy degradation curve for YaRN extension of Qwen3.5 from 256K to 1M on our hardware? Does it mirror the model card claims, or does CPU-specific numerical behavior affect quality?
- How much KV cache memory does 1M context consume with our current Hadamard+q4_0 quantization? Is it feasible within our 384GB RAM budget, or does it require TurboQuant-level compression?
- Does the 15pp Memento dual-information-stream ceiling apply equally to code generation and factual QA, or is it specific to competition math reasoning?
- What is the quality cliff when stacking 3+ KV compression layers (quantization + block masking + compaction)? Each pair tested independently, but triple-stacking has no published evaluation.
- Can MemAgent's RL-trained compaction policy be distilled into our session compaction without the full sequential architecture -- extracting the "what to remember" signal without the "process segment by segment" overhead?
- For the hybrid approach (YaRN for first 128K, chunked processing for overflow): what is the optimal segment size and memory buffer size for our specific models, and does the transition introduce artifacts?
- How does context extension interact with speculative decoding at long contexts? Acceptance rates may change as the draft model's effective context diverges from the target's.

## Related Categories

- [Context Management](context-management.md) -- Compression within a given window; complementary to extension which changes the window. Many techniques (Memento, Accordion-Thinking, InftyThink) straddle both categories.
- [Cost-Aware Routing](cost-aware-routing.md) -- Extended context changes the cost calculus for routing; difficulty-adaptive budgets interact with context length (hard problems may need both more reasoning and more context)
- [LLM Prompting](llm-prompting.md) -- The computational buffer finding (dummy tokens improve accuracy) interacts with context extension: longer context provides more computation budget even if content is low-information

## Source References

- [MemAgent RL-Trained Memory](../research/deep-dives/memagent-rl-memory.md) -- 437x context extrapolation, sequential segment processing, RL critical for compaction quality, CPU overhead analysis
- [Memento Iterative Reasoning Cluster](../research/deep-dives/memento-iterative-reasoning-cluster.md) -- Dual information stream (15pp KV vs text ceiling), InftyThink/InftyThink+/Accordion-Thinking comparison, quad-stack KV compression opportunity, Fold/Unfold toggle
- [ReSum Context Summarization](../research/deep-dives/resum-context-summarization.md) -- Diminishing returns at 128K, compaction timing for extended windows
- [Context-Folding / FoldGRPO](../research/deep-dives/context-folding-foldgrpo.md) -- 32K beats 327K finding demonstrates that compression can outperform raw extension
- [yarn-context-extension-research handoff](../handoffs/active/yarn-context-extension-research.md) -- YaRN CLI flags, model support, open research questions
- [memento-block-reasoning-compression handoff](../handoffs/active/memento-block-reasoning-compression.md) -- Block masking feasibility in llama.cpp, SFT training design, composability analysis
- [intake-153] Recursive Language Models -- Theoretical foundation; EPYC implements ~80% of RLM architecture
- [intake-154] Context-Folding -- Branch/fold call stack; sub-linear context growth
- [intake-155] AgentFold -- Two-level proactive folding; 92% context reduction; sub-linear growth
- [intake-156] MemAgent -- 437x extrapolation; O(N) complexity; RL-trained memory policy
- [intake-157] ReSum -- Periodic summarization; diminishing returns at 128K; summarizer quality threshold
- [intake-191] TurboQuant -- 6x+ KV compression via PolarQuant + QJL; makes 1M context practical
- [intake-192] PolarQuant -- 4.2x KV compression via polar coordinate transformation
- [intake-193] QJL -- 5x KV reduction to 3 bits; zero overhead; AAAI 2025
- [intake-259] RTK -- 60-90% tool output compression; security concerns preclude direct adoption
- [intake-273] Context Rot -- Performance degrades with input length; validates selective attention at long context
- [intake-274] The Complexity Trap -- Observation masking matches LLM summarization; validates compression over extension for tool outputs
- [intake-289] Memento -- Block-level KV masking; dual information stream; 2-3x peak KV reduction
- [intake-292] InftyThink -- Iterative reasoning with periodic summarization; ICLR 2026
- [intake-293] InftyThink+ -- RL-enhanced iterative reasoning; +21pp AIME24; efficiency reward
- [intake-294] Accordion-Thinking -- Fold/Unfold runtime toggle; 3x throughput; accuracy gap vanishes with RL
