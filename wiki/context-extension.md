# Context Extension

**Category**: `context_extension`
**Confidence**: inferred
**Last compiled**: 2026-10-28 (HELMET restoration and fresh Oolong cohort approved, not run). Earlier: 2026-10-27 19:06Z (YaRN extension arms remain NOT-FAIL-underpowered; HELMET restoration is preparation only). Earlier: 2026-10-27 (operator wiki sweep, workspace-58): YaRN extension arms are NOT-FAIL-underpowered, Oolong-synth@400k reads 0.093, and the YaRN K-shift fix passes its test. Earlier: 2026-10-22 (wrap-up sweep 10: native-window answer change is not regression, agent-made judge labels). Earlier: 2026-10-22 (wrap-up sweep 9: the native-window gate reads NOT-FAIL on 2 discordant pairs). Earlier: 2026-10-21 (wrap-up sweep 5: YARN-AGG-1/JUDGE-1 spec, Oolong adapter, K-shift fix queued). Earlier: 2026-10-06 (incremental root-wrap synthesis; prior compilation history: 2026-04-18 (+ 2026-05-20 incremental: intake-569 RoPE bounds + deep-dive))
**Sources**: 23 documents (0 dedicated deep-dives, 5 cross-referenced deep-dives, 3 active handoffs, 15 intake entries)

## Compiled Update — 2026-10-27 19:06Z: extension-arm verdict remains underpowered

**Confidence: verified for the predeclared native-zone sample; no equivalence claim.** The final YaRN extension-arm comparison contains 74 native-window pairs (`b=2`, `c=1`, one-sided exact McNemar `p=0.5`, mean paired A1−A0 score difference `−0.022`). The result is `NOT-FAIL-underpowered`, not a pass of equivalence or safety. Beyond-native A1-only rows are descriptive; Oolong-synth at 400K has 54 observations and mean score 0.093. HELMET KILT `nq`/`hotpotqa` cells were absent, so they provide no result. The 120-pair Oolong GPU packet and HELMET restoration are prospective preparation only; the historical 1f/1g power tasks remain open and runs must not be pooled across the prior plans.

Sources: [YaRN context-extension handoff](../handoffs/active/yarn-context-extension-research.md), [2026-10-27 workspace-58 evidence](../progress/2026-10/2026-10-27-workspace-58.md), [accepted-scope record](../progress/2026-10/2026-10-27-full-wrap-1850.md).

## Compiled Update — 2026-10-23 (wrap-up sweep 15, 3c4ca599): the YaRN native-window gate is FINAL: NOT-FAIL-underpowered

**Confidence: verified** for the decision file; the result is a no-harm-detected reading, **not** an equivalence claim.

- **Final decision** (`/mnt/raid0/llm/tmp/yarn-native-gate-out/decision.json`, 2026-10-23T13:02:40Z, plan `native-gate`, protocol `YARN-AGG-1/native-gate/net-paired-mcnemar/v1`): pooled native 185 pairs, b (A0 right / A1 wrong) = 1, c = 1, n_discordant = 2, one-sided exact McNemar p = 0.75, mean score diff A1-A0 = +0.004. This supersedes the 18-pair first pass in sweep 9 above.
- **Per cell.** oolong_synth@131072: 152 pairs, 1/1. ruler mk_2, mk_3 and mv at 32k, 64k and 124k: 0/0 each (2-6 items per cell).
- **Reading.** With two discordant pairs the gate cannot show a regression, and cannot show equivalence either. The handoff has no prescribed rule for NOT-FAIL-underpowered; YARN-AGG-1f (optional) proposes adding discordant-prone items (more Oolong at 64K-128K, harder multi-key items) and re-freezing a plan, done when n_discordant >= 10 or the operator declines.
- **Process note.** The gate's first scratch-server run OOM'd from the v10 GPU build's per-request VRAM leak; the gate lib now recycles the server at 60 GiB (see GPU-LEAK-1 in the inference-serving page). Beliefs were ingested into the vidya ledger (30 rows, 90 frames).

### Source References (2026-10-23 wrap-up sweep 15)

- [yarn-context-extension-research](../handoffs/active/yarn-context-extension-research.md) — YARN-AGG-1e, YARN-AGG-1f
- [3c4ca599 progress, 2026-10-23](../progress/2026-10/2026-10-23-3c4ca599.md) — gate FINAL and OOM root cause
- [gpu-serving-tie-in-program](../handoffs/active/gpu-serving-tie-in-program.md) — GPU-LEAK-1

---
## Compiled Update — 2026-10-22 (wrap-up sweep 10): a native-window answer change is not a quality regression, and the judge labels are agent-produced, not human

**Confidence: verified** for the judge agreement figures (n=50, pinned cloud judge) and the gate-plan contents; **inferred** for what the native-window and extension arms will show, since only 18 native pairs have run.

- **Operator correction on the native-window rule (2026-10-22).** "Changing answers within native windows and regressing quality are not necessarily the same thing." The 7/20 greedy divergence of static YaRN is NOT itself a quality regression; the speed costs still fail the "YaRN must not regress inside native window" rule, and quality is decided by the scored net-paired gate YARN-AGG-1(i). The handoff wording was fixed accordingly.
- **Gate power caveat.** NOT-FAIL is harm-detection only; an equivalence claim needs a pre-registered margin (M15 / DP-E). `decision.json` carries `n_discordant`, `min_losses_to_fail_given_discordant`, `power_note` and `interpretation` (underpowered = fewer than 10 discordant pairs); the verdict rule is unchanged.
- **The 50 judge-validation labels are agent-produced under operator delegation, not human.** Operator ruling: build the labels yourself. The coordinator then required a different model family from the judge so agreement is not inflated by shared blind spots: 19 labels by deterministic rule (6 no-answer, 5 exact match, 1 yes/no, 7 numeric mismatch) and 31 by `codex-luna-low`; none by a Claude model. Result: 10 correct, 40 incorrect, 0 undecided. The logged prompt was cut at 200 characters, so hotpotqa's question had to be re-resolved from the dataset (50 of 50 resolved).
- **Judge of record is the pinned cloud judge `sonnet-5-5-low`, superseding the local-judge design.** Against the 50 labels: accuracy 0.98 (49/50, Wilson 95% 0.895 to 0.996), Cohen kappa 0.940 (95% CI 0.823 to 1.0 analytic, 0.766 to 1.0 bootstrap), confusion 39 / 1 / 0 / 10, 0 unparsed, 50 calls, $0.2156. The one disagreement (j008) is cut-off meta-reasoning that names a candidate but commits no final answer. This is agreement between two model families, not with humans, and is relative to this pinned judge only; the task set no numeric threshold, so the clause is met by reporting agreement with the pin.
- **YARN-JUDGE-1 stays open on one clause.** No plan contains a judged HELMET category, so a cell must be generated in a GPU window before `helmet_judged_cell.py --judge-backend cloud` can score "one judged HELMET cell end to end".
- **Gate and arm plumbing exists.** The native-gate plan is frozen at 185 items (Oolong 131072 x 8 contexts; RULER NIAH mk_2/mk_3/mv at 32K/64K/124K, generated locally). Extension-arm builders cover HELMET (a validated 240K local config; nq and hotpotqa optional because the 10.5 GiB RAG data is not on disk) and LongBioBench. The RULER suite was added to the belief-kernel schema so those items are no longer excluded from decision records. Grant-polling jobs refuse when production :8083 is listening or a foreign KFD tenant holds VRAM; a dirty pinned research tree is not yet refused (YARN-DIRTY-TREE-REFUSE open).

### Source References (2026-10-22 wrap-up sweep 10)

- [handoffs/active/yarn-context-extension-research.md](../handoffs/active/yarn-context-extension-research.md) — operator correction, power caveat, AGG-1a-d and JUDGE-1a-d records
- [progress/2026-10/2026-10-22-yarn-judge1-labels.md](../progress/2026-10/2026-10-22-yarn-judge1-labels.md) — label provenance and judge agreement figures
- [progress/2026-10/2026-10-22-yarn-ruler-schema.md](../progress/2026-10/2026-10-22-yarn-ruler-schema.md) — RULER suite added to the belief-kernel schema
- [handoffs/active/CURRENT-CAMPAIGN.md](../handoffs/active/CURRENT-CAMPAIGN.md) — operator decisions of 2026-10-22 including the delegation

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

- **RoPE base-extension trades position-fidelity for token-fidelity provably (intake-569, Du et al. 2026)**: Closed-form proofs of four RoPE failure modes (Position Inversion → 0.5 prob at long M; Position Aliasing → 100% exponentially in M; Token Inversion → 0.5 at m ≥ 20K; Token Aliasing ≈ 5% positions at BF16 h=64). Critical asymmetry: raising the RoPE base B (the YaRN move) **helps** token modes F3/F4 but **hurts** position modes F1/F2 — no single B preserves both. Empirically all tested 7B–405B models collapse to chance (~0.25) on a 4-element position-indexing task by 4K–8K tokens. **Operational implication for EPYC**: 32K is the operational hard line for reliable position discrimination; above 32K, YaRN-style extension preserves content fidelity but degrades position fidelity, so YaRN's `yarn-context-extension-research.md` gate now requires workload tolerance for degraded position-discrimination. Triangulates mechanistically with intake-547#02 (Wang RLM reproduction): depth-2 96× wallclock cliff is the predicted symptom of long-context attention over depth-1 children's outputs. [2026-05-20-rope-long-context-bounds.md](../research/deep-dives/2026-05-20-rope-long-context-bounds.md), [yarn-context-extension-research handoff](../handoffs/active/yarn-context-extension-research.md), [intake-569]

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

- **Context rot compounds at extended lengths**: intake-273 (Chroma research) confirms performance degrades non-linearly with input length. Distractors (topically related but incorrect content) amplify degradation. This means that naively extending context with YaRN without also improving the model's ability to attend selectively is counterproductive for certain task types. Sparse attention or selective retrieval becomes more important as context grows. [intake-273](https://research.trychroma.com/context-rot)

### Recursive and Infinite-Horizon Approaches

- **Recursive Language Models (intake-153) provide the theoretical foundation**: The EPYC orchestrator implements approximately 80% of the RLM architecture -- multi-model delegation, context management through summarization, tool-augmented generation. The remaining 20% (learned compaction policies, process rewards for compression quality) maps to the context-folding Phase 3 roadmap. [intake-153](https://arxiv.org/abs/2512.24601)

- **RTK achieves 60-90% token reduction across 100+ commands**: A practical tool-level approach to context extension -- by compressing tool outputs before they enter context, the effective context window is extended by 60-90% for tool-heavy sessions without any model-level changes. Security concerns (shell injection, telemetry, CI trust bypass) preclude direct adoption, but the compression strategies inform our native Phase 2 implementation. [intake-259](https://github.com/rtk-ai/rtk)

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
- **EM-LLM episodic memory for infinite context (intake-409)**: EM-LLM (arXiv 2407.09450, ICLR 2025) integrates Bayesian-surprise event segmentation + dual-stage retrieval (k-NN + temporally contiguous) to handle 10M+ token contexts with no fine-tuning. Outperforms InfLLM by 4.3% on LongBench. However, full integration requires deep llama.cpp surgery: per-layer KV pair access, unified softmax across local + retrieved attention scores, and per-token logprobs during prefill — estimated 4-8 weeks of C++ work in ggml. RAM blocker: episodic memory stores FP16 KV cache across all layers (10M tokens = ~1.2TB, 1M tokens = ~125GB). Quantized model weights don't help — KV cache is still FP16. YaRN remains better ROI. **Salvageable insight**: surprisal-based chunking (detect event boundaries from logprob spikes) can improve existing ColBERT retrieval pipeline without any model modification — proposed as S7 in colbert-reranker-web-research handoff. [intake-409, yarn-context-extension-research.md]
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
- **Tulving episodic memory benchmark as quality gate** (intake-408): Existing long-context eval (RULER, NIAH, LongBench) tests retrieval. The Tulving benchmark (arXiv 2501.13121, 200ch/100K variant) tests episodic memory — entity tracking and temporal ordering across extended narratives. Sharp cliff: most models lose 30-60% recall from 10K→100K. Chronological awareness degrades faster than recall at every scale. Proposed as a YaRN quality gate alongside RULER — if YaRN-extended models pass NIAH but fail Tulving temporal ordering, it signals attention distribution problems YaRN doesn't compensate. [research-evaluation-index.md P3b/P4]

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
- [intake-153](https://arxiv.org/abs/2512.24601) Recursive Language Models -- Theoretical foundation; EPYC implements ~80% of RLM architecture
- [intake-154](https://arxiv.org/abs/2510.11967) Context-Folding -- Branch/fold call stack; sub-linear context growth
- [intake-155](https://arxiv.org/abs/2510.24699) AgentFold -- Two-level proactive folding; 92% context reduction; sub-linear growth
- [intake-156](https://arxiv.org/abs/2507.02259) MemAgent -- 437x extrapolation; O(N) complexity; RL-trained memory policy
- [intake-157](https://arxiv.org/abs/2509.13313) ReSum -- Periodic summarization; diminishing returns at 128K; summarizer quality threshold
- [intake-191](https://research.google/blog/turboquant-redefining-ai-efficiency-with-extreme-compression/) TurboQuant -- 6x+ KV compression via PolarQuant + QJL; makes 1M context practical
- [intake-192](https://arxiv.org/abs/2502.02617) PolarQuant -- 4.2x KV compression via polar coordinate transformation
- [intake-193](https://arxiv.org/abs/2406.03482) QJL -- 5x KV reduction to 3 bits; zero overhead; AAAI 2025
- [intake-259](https://github.com/rtk-ai/rtk) RTK -- 60-90% tool output compression; security concerns preclude direct adoption
- [intake-273](https://research.trychroma.com/context-rot) Context Rot -- Performance degrades with input length; validates selective attention at long context
- [intake-274](https://arxiv.org/abs/2508.21433) The Complexity Trap -- Observation masking matches LLM summarization; validates compression over extension for tool outputs
- [intake-289](https://github.com/microsoft/memento) Memento -- Block-level KV masking; dual information stream; 2-3x peak KV reduction
- [intake-292](https://arxiv.org/abs/2503.06692) InftyThink -- Iterative reasoning with periodic summarization; ICLR 2026
- [intake-293](https://arxiv.org/abs/2602.06960) InftyThink+ -- RL-enhanced iterative reasoning; +21pp AIME24; efficiency reward
- [intake-294](https://arxiv.org/abs/2602.03249) Accordion-Thinking -- Fold/Unfold runtime toggle; 3x throughput; accuracy gap vanishes with RL

## Incremental synthesis — 2026-10-06 root wrap

**Confidence: mixed, with quality and memory gates reported separately.** The post-manifest Qwen3.8-27B GPU YaRN ×2 run matched the native arm at 128K/240K (10/10 needles) and retrieved 5/5 at both 400K and 500K. A2's negative control did not run, so discrimination beyond native length remains unshown. The run failed its memory gate: A1 peaked at 63.9 GiB against a 55 GiB limit, with a similar unexplained overshoot in A0. Memory attribution is the open dependency; this does not authorize static YaRN flags on production servers.

The new CPU Qwen3.6-35B-A3B leg reached 323K with 5/5 retrieval; native and YaRN ×2 matched at 133K and 253K. At matched depth, YaRN's decode cost was at most 4%, while decode fell with depth in both arms and 8K append cost grew to about 600 seconds around 351K. DCA beat raw extrapolation in one-window 64K PPL runs, but DCA-vs-YaRN remains suggestive only and the CPU/GPU offset is unresolved.

Sources: [YaRN context-extension research](../handoffs/active/yarn-context-extension-research.md), [AutoKernel all-devices/all-dimensions](../handoffs/active/autokernel-all-devices-all-dimensions.md), [GPU serving tie-in program](../handoffs/active/gpu-serving-tie-in-program.md), [KV unified stack rollout](../handoffs/active/kv-unified-stack-rollout.md).

### Supplemental changed-source coverage — Oct 3–6

The post-manifest CPU YaRN progress distinguishes native-window cost from extension quality: Qwen3.6-35B-A3B reached 323K with 5/5 tested needles; native and static YaRN ×2 matched at 133K and 253K, while static ×2 failed the native-window inertness rule (decode loss 1.3% at depth 0 and 7.6% at 34K; MTP acceptance 53% to 48%). Dynamic per-request YaRN/DCA remains the acceptable direction in that test record; it does not establish a general context-extension quality win. The GPU tie-in handoff adds only an open memory-attribution task for the +15 GiB E1 overshoot already recorded here, not a new result.

Sources: [Oct 5 workspace-ec progress](../progress/2026-10/2026-10-05-workspace-ec.md), [Oct 6 workspace-ec progress](../progress/2026-10/2026-10-06-workspace-ec.md), [GPU serving tie-in program](../handoffs/active/gpu-serving-tie-in-program.md), [YaRN context-extension research](../handoffs/active/yarn-context-extension-research.md).

## Incremental synthesis — 2026-10-06 workspace-ec wrap (native-window inertness, K-shift, Jet-Long)

**Confidence: verified for the native-window regression (one CPU recipe, 20 prompts) and for the three K-shift defects (unit fixtures on CPU, no model run); source-read only for the mscale mechanism and the design options; planned for everything gated on the mscale A/B.**

- **Static YaRN fails the operator's "no regression inside the native window" rule.** On the canonical :8070 recipe (Qwen3.6-35B-A3B, CPU, MTP on, 2026-10-05), YaRN x2 cost 1.3% decode at depth 0 and 7.6% at 34k, MTP acceptance fell 53% to 48%, and greedy output stayed byte-identical on only 13/20 short prompts. Acceptable mechanisms are therefore ones that are inert at or below the native length: per-request or per-sequence YaRN, or DCA.
- **Mechanism (source read, not measured).** On the champion tree the YaRN kernel multiplies cos and sin by `1 + 0.1 ln 2 = 1.0693` at every position, which sharpens the rotated part of the Q.K logit by about 1.143x, including at position 0. This is consistent with the acceptance drop. Separately, the frequency ramp leaves slow pairs with an angle error near 1 rad at 30K tokens, which is why drift grows with depth. Neutralising mscale alone cannot give bit-identity; only switching the YaRN branch off for in-window tokens can. A cparams defect was also found: a user `--yarn-attn-factor` is discarded whenever `ext_factor != 0` (`llama-context.cpp:220-228`). No per-request or "dynamic" rope mode exists in llama.cpp today.
- **Prior-art correction.** "Nobody re-ropes cached K at the crossing" is false for llama.cpp itself: `llama_memory_seq_div` plus the K-shift graph (`build_rope_shift`) re-rope cached K for Self-Extend, in completion and passkey only (llama-server does not use it). Jet-Long instead keeps base-roped K and rotates distant K on the fly, avoiding a cache rewrite.
- **K-shift is not safe as a re-rope primitive at v10 (`ffc1bac82`).** Three source-then-unit probes (CTX-KSHIFT, experimental branch only) CONFIRMED all three hypotheses: (H1) the shift re-applies YaRN mscale each time (norm grows as 1.0693^n); (H2) `pos_div` records the shift with the wrong sign (`kv-cells.h:478`, max-abs error 4.7 against a 1.4e-6 control floor); (H3) under quantized K the Hadamard width comes from the full head dim but is applied to the n_rot-wide view (84.7x rms error), and the shipped graph aborts on the CPU backend for a non-contiguous q8_0 destination. Fixes exist on the probe branch and are unit-verified only; a model-level shift test is still required before any adoption.
- **Jet-Long (cost not yet measured).** In-window exactness is reported by the paper on Qwen3, but the uncached correction costs roughly 5x the attention K+V bytes per decode step (derived estimate), the fused kernel is SM90-only, and there is no MTP or DFlash2 support. Decision gating: CTX-JETLONG-COST (arithmetic plus CPU microbenchmark; passes at <= 10% decode cost at 262K and <= 25% at 1M), then a bit-exact in-window prototype, with YARN-MSCALE-AB deciding how cheap inertness can be. The interim recommendation is a length-routed second server (D) with its RAM stated as a number, F as target, Jet-Long cached as the stretch; DCA is off the in-window path (identity only below chunk_size minus local window, refuses MTP in v1, roughly 2x attention cost).
- **YaRN is not a short-context identity, and CPU YaRN is cost-neutral beyond that:** the same session's CPU leg (323K, 5/5 needles; decode cost at most 4% at matched depth) is recorded in the section above; its limit at depth is CPU attention cost, not the scaling method.

Sources: [YaRN context-extension research](../handoffs/active/yarn-context-extension-research.md), [native-window summary](../artifacts/yarn-native-window-20261005/summary.md), [Oct 5 workspace-ec progress](../progress/2026-10/2026-10-05-workspace-ec.md), [Oct 6 workspace-ec progress](../progress/2026-10/2026-10-06-workspace-ec.md), [GPU serving tie-in program](../handoffs/active/gpu-serving-tie-in-program.md). Study notes (scratch, not durable): `/mnt/raid0/llm/tmp/yarn-inert-design-20261006/{OPTIONS,CTX2_KSHIFT,STAGE3_PLAN}.md`.

## Incremental synthesis — 2026-10-06 evening (Jet-Long gate A PASS, the small-ubatch abort, CPU prefill scaling)

**Confidence: verified for gate A (real model, CPU, 41 requests per arm, text-level identity) and for the prefill-rate table (derived from server logs); verified-as-observed for the abort (reproduced at two ubatch sizes, cause unproven); everything above native length is still unmeasured on quality.**

- **Jet-Long gate A PASSES in-window.** Production binary (S), Jet-Long binary with no flag (JOFF) and Jet-Long ON (window 2048, native 262144) produced byte-identical text, identical token counts, identical finish reasons and identical per-request MTP `draft_n` and `draft_n_accepted` on all 41 records (40 short prompts plus the 34k probe); totals 4217 drafted, 2866 accepted in every arm. This clears the in-window rule at text level. It is not the logit max-abs check named in the decision package, and nothing above native length ran. Evidence: [GATE_A](../artifacts/yarn-ctx-20261006/jetlong/GATE_A.md). The decision record [DECISION_CTX4](../artifacts/yarn-ctx-20261006/DECISION_CTX4.md) keeps the order: D as interim, J as target conditional on gate A plus needle recall, F as the fall-back; the operator still owns that choice.
- **Small-model recall (partial).** Qwen3-0.6B Q8_0 at 30k: Jet-Long 6/6 needles, equal to the production binary (same prompt_n 28914); prefill 73 tok/s at `-ub 32` against 197. The 65k arm was killed at 84% and the above-native comparison against static YaRN was not run. Evidence: [SMALL_MODEL_RECALL](../artifacts/yarn-ctx-20261006/jetlong/SMALL_MODEL_RECALL.md).
- **Jet-Long small-ubatch bug.** With Jet-Long ON (window 256, native 1024) the CPU server aborts on `GGML_ASSERT(i01 >= 0 && i01 < ne01)` in `ggml_compute_forward_get_rows` (`ggml-cpu/ops.cpp:5350`) for any ubatch smaller than the window at positions past native: ub 16 crashed at about 1280 tokens, ub 256 ran clean to 9145 tokens and crashed on the final 4-token ubatch. Checkpoints, cache-ram and the drafter were each ruled out (crash with `--ctx-checkpoints 0 --cache-ram 0`, and with no drafter); `-ub 256` removed it only for full ubatches. By extension decode (n=1) beyond native is exposed, and the GPU run (ub 16, window 2048) shares the exposure. Hypothesis, unproven: the grouped-position path builds an out-of-range row index when the ubatch is smaller than the window. Slot save/restore under Jet-Long was never reached (see the checkpoint rule in [ssm-hybrid](ssm-hybrid.md)). Evidence: [SAVE_RESTORE_TEST](../artifacts/yarn-ctx-20261006/jetlong/SAVE_RESTORE_TEST.md).
- **CPU long-context prefill scaling (35B-A3B MTP Q8_0, 96 threads, `-ub 256`).** Instantaneous prefill rate falls about 10x by 100k tokens: Jet-Long 374 tok/s at 1.7k, 198 at 12k, 97 at 32k, 70 at 53k, 43 at 94k, 39 at 104k; static YaRN 321 at 2.2k, 128 at 23k, 62 at 64k, 41.5 at 105k. The cumulative average falls from about 490 tok/s (4.8k) to 70 (109k). The two arms track each other, so below native Jet-Long adds no visible slope penalty; the cost is attention over a growing KV on CPU. Both logs end near 109k of a roughly 288k prompt (progress 0.38), so the shape beyond 109k is extrapolation, and a 1M prefill is hours. Evidence: [PREFILL_SCALING](../artifacts/yarn-ctx-20261006/jetlong/PREFILL_SCALING.md).

Sources: [YaRN context-extension research](../handoffs/active/yarn-context-extension-research.md), [Oct 6 workspace-ec progress](../progress/2026-10/2026-10-06-workspace-ec.md), [GATE_A](../artifacts/yarn-ctx-20261006/jetlong/GATE_A.md), [SAVE_RESTORE_TEST](../artifacts/yarn-ctx-20261006/jetlong/SAVE_RESTORE_TEST.md), [PREFILL_SCALING](../artifacts/yarn-ctx-20261006/jetlong/PREFILL_SCALING.md).

## Incremental synthesis — 2026-10-07 workspace-ec pre-pause wrap (the Jet-Long hybrid-input bug)

- **The small-ubatch abort was a missing input, not a size limit.** Root cause (fixed at `e6ea79421`, branch llama.cpp-experimental-jetlong-hip-20261006): `llm_graph_input_mem_hybrid::set_input` never filled the Jet-Long inputs and `can_reuse` never blocked graph reuse, so on qwen35/qwen35moe above native the attention read uninitialised indices. The visible symptom was the `get_rows` assert; the dangerous one is **silently wrong attention**. Every pre-fix above-native result on hybrid models is therefore INVALID. New T4 tests (ub 1/4/16/64, tail, decode, IMRoPE+NeoX, q8_0+f16) pass and a real 27B at `-ub 16` no longer crashes. Gap: the synthetic harness bypassed the hybrid input class, which is why it never saw this.
- **Small-model recall (Qwen3-0.6B, native 32k; NeoX path, no repro of the bug).** 1x: N 6/6, J 6/6. 2x: J 6/6, static YaRN 5/6, X 5/6. 4x: Y 3/6, X 0/6, J not run (CPU too slow). The 4x J arm remains open.

Sources: [YaRN context-extension research](../handoffs/active/yarn-context-extension-research.md), [pre-pause progress](../progress/2026-10/2026-10-07-workspace-ec.md), [JETLONG_SMALL_RESULTS](../artifacts/ec-wrapup-20261007/JETLONG_SMALL_RESULTS.md), [SAVE_RESTORE_TEST](../artifacts/ec-wrapup-20261007/SAVE_RESTORE_TEST.md).

## Compiled Update — 2026-10-22 (wrap-up sweep 9): the native-window gate reads NOT-FAIL on 2 discordant pairs, and the gate now says so

**Confidence: verified** for the gate arithmetic and the offline recompute; the run itself is an INTERIM reading.

- **What the gate is.** YARN-AGG-1(i) is a one-sided exact McNemar test on native-zone discordant pairs: FAIL iff p <= 0.05. It detects harm; it does not establish equivalence, and it needs at least 5 losses with 0 wins to fail, so with few discordants it almost always reads NOT-FAIL.
- **First reading.** The native gate ran 13:25-14:18Z on the MI210 gap: 18 pairs, 2 discordant (b=1, c=1), interim NOT-FAIL, underpowered.
- **Power fields.** Research `7e7d5ef7f` adds `n_pairs`, `n_discordant`, `b_a0right_a1wrong`, `c_a0wrong_a1right`, `min_losses_to_fail_given_discordant`, a `power_note` and an `interpretation` (FAIL, NOT-FAIL-underpowered when n_discordant < 10, or NOT-FAIL) to every pooled and per-cell block, `decision.json` and the claim tuple. The `verdict` and its rule are unchanged, and the root adapter `yarn_gate_agg.py` mirrors the fields without touching `claim_tuple.grade()` (88 research and 16 root tests).
- **Operator correction, verbatim:** "changing answers within native windows and regressing quality are not necessarily the same thing. Don't be overly strict please". The handoff wording was relaxed: a changed answer inside a native window is a discordant pair to count, not by itself a regression.

### Source References (2026-10-22 wrap-up sweep 9)

- [progress/2026-10/2026-10-22-yarn-gate-power-note.md](../progress/2026-10/2026-10-22-yarn-gate-power-note.md)
- [progress/2026-10/2026-10-22-yarn-native-gate-runner.md](../progress/2026-10/2026-10-22-yarn-native-gate-runner.md)
- [handoffs/active/yarn-context-extension-research.md](../handoffs/active/yarn-context-extension-research.md)

## Compiled Update — 2026-10-21 (sweep 5): the YaRN gate is specified, the Oolong adapter exists, and the K-shift fix is queued

**Confidence: verified** for the code, the tests and the offline token counts. **No YaRN gate cell has run.** Everything below was built against an in-process fake endpoint, and the arms wait for inference windows.

- **OOL-1: the Oolong adapter** (research `a1ed3633a`, `scripts/benchmark/oolong_adapter.py`). 11/11 unit tests pass.
  - **The labelled column is refused.** `test_labelled_column_is_refused` covers it: `context_window_text_with_labels` raises `LabelledColumnError`. A regex scores near 100% on the labelled text, so `labels_given` records are excluded from any gate.
  - **The scorer is vendored, not rewritten.** `eval_helpers.py` @ `0bb7eabe8` is vendored unmodified, and its sha256 is verified on import.
  - **Pinned datasets.** `oolong-synth@81d2f8d9...` and `oolong-real@3ae6ab58...`.
  - **Belief-kernel row.** VB-OOLONG-WIRE was added in the same change.
- **YARN-AGG-1: the gate spec.**
  - **Comparisons.** A0 vs A1 (GPU 27B) and CN vs CY2 (CPU 35B-A3B hybrid). All arms are greedy, thinking off and paired on the same item ids.
  - **Arms.** Oolong-synth (counting, user), with a HoloBench info_amount control that attributes a long-length drop to length only if it persists inside a constant-relevant-amount band. HELMET recall/RAG (`ruler_niah_mk_2/3`, `ruler_niah_mv`, `json_kv`, `nq`, `hotpotqa`; HELMET configs stop at 128K, so the 240K config is a local copy recorded by sha). LongBioBench (standard, multi_standard, paraphrase).
  - **Zone labels.** They come only from the measured real-token count (served `/tokenize` or `prompt_n + cache_n`). With N = 262,144 and 4,096 tokens reserved, native means real + 4,096 <= N and beyond-native means real > N. Anything between counts as neither.
  - **Margin rule.** Net-paired McNemar (see the benchmark-methodology page).
- **The Oolong subset was re-measured offline with the Qwen3.8-27B tokenizer, and real tokens run below nominal.**
  - **The buckets.** 131072 → 89,419 / 110,768 / 122,120 (min / median / max, native); 262144 → 179,722 / 222,455 / 239,818 (native); 524288 → 371,962 / 447,286 / 472,304 (beyond-native).
  - **Constructible.** 240K (9 contexts) and 400K (10).
  - **Not constructible.** 128K and 500K. The beyond-native cells are about 400K to 470K, not 500K.
  - **Still owed.** The served-server `/tokenize` cross-check in the first window supersedes these counts.
- **YARN-JUDGE-1: a local judge only.**
  - **How it is served.** On `localhost:{port}/v1`; a non-localhost endpoint is refused.
  - **What is pinned.** The model id, prompt sha, temperature 0, seed 0 and max_tokens ride in the claim tuple.
  - **Window separation.** The client refuses to run while `YARN_TIMING_WINDOW_ACTIVE=1`.
  - **Unparsed replies.** They are listed as `unjudged` and never scored 0.
  - **Validation.** A blind 50-item labelling sheet waits for operator labels. Results are relative to the pinned local judge and never comparable to published figures.
- **V11-100, the YaRN K-shift pure-rotation fix** (`experimental/yarn-kshift-fix-20261021` @ `b67a5b9bc`), folds into the consolidation after the C2 CAS (CH-23). Its test travels with the commit. The native-window non-regression gate (YaRN must not regress inside the native window) remains a hard gate on the champion.

Sources: [YaRN context extension research](../handoffs/active/yarn-context-extension-research.md), [RAO/ReDel substrate spike](../handoffs/active/rao-redel-substrate-spike.md), [Progress dpf-sample-yarn](../progress/2026-10/2026-10-21-dpf-sample-yarn.md), [AutoKernel champion aggregate](../handoffs/active/autokernel-champion-aggregate.md), [Vidya belief-substrate program](../handoffs/active/vidya-belief-substrate-program.md)

## Compiled Update — 2026-10-26 (wrap-up, workspace-58)

- **YaRN scope is Qwen3.8-27B factor 2 (524,288) as an np 1 MI210 mode.** E1 quality PASS to 500K but FAIL on C4 memory (A1 63.9 GiB vs 55 limit); next is YARN-E1-MEM. v10 traps: the server clamps every slot to `n_ctx_train`, so `--override-kv qwen35.context_length` plus a mandatory `--yarn-orig-ctx 262144` are required. The native-window gate remains NOT-FAIL-underpowered, and the K-shift fix shipped in champion C3. ([yarn-context-extension-research](../handoffs/active/yarn-context-extension-research.md), [week outcomes](../docs/reference/inference-outcomes-week-2026-10-18-to-25.md))

## Compiled Update — 2026-10-27 (operator wiki sweep, workspace-58)

**Confidence: verified** for the recorded decisions; beyond-native cells are report-only.

- **YARN-AGG-1(ii) extension arms: NOT-FAIL-underpowered, not an equivalence claim.** On native-zone pairs the one-sided exact McNemar has n_pairs 74, b=2 (A0 right / A1 wrong), c=1, p=0.5, mean paired diff A1-A0 -0.022. A0 ran 80/80 and A1 139/139 planned items. Cell means are tiny-n and report-only (oolong_synth@240k n=61: A1 0.138 vs A0 0.149). This follows the native-gate rule that YaRN must not regress the native window; with 3 discordant items it cannot detect a regression either way. ([yarn-context-extension-research](../handoffs/active/yarn-context-extension-research.md); [2026-10-27 harvest](../progress/2026-10/2026-10-27-workspace-58.md); `/mnt/raid0/llm/tmp/yarn-extension-arms-out/decision.json`)
- **Beyond native, A1 only (no A0, no gate):** Oolong-synth@400k n=54 mean 0.093 (CI 0.071-0.133); helmet_json_kv, longbio_standard and ruler_mv @400k are 1/1; ruler_mk_2 @400k and @480k are 0/1. HELMET nq/hotpotqa 128k were dropped because the KILT data is missing; YARN-AGG-1g restores it and folds the discordant items into the 1f power run. ([yarn-context-extension-research](../handoffs/active/yarn-context-extension-research.md); [2026-10-27 harvest](../progress/2026-10/2026-10-27-workspace-58.md))
- **CH-23 YaRN K-shift: the champion fails `test-yarn-kshift` and fix `b67a5b9bc` passes it.** On `dd3d9721c` the YaRN x4 round-trip K NMSE is 8.79e-2 (shifted vs fresh 1.92e-2; non-YaRN `attn_factor` 1.1 round trip 4.41e-2). With the fix, all are <= 2e-9, non-YaRN digests are bit-identical and CPU ROPE is 448/448; HIP ROPE was not run. Correctness-only. ([autokernel-champion-aggregate](../handoffs/active/autokernel-champion-aggregate.md) CH-23; [2026-10-27 harvest](../progress/2026-10/2026-10-27-workspace-58.md); `/mnt/raid0/llm/tmp/yarn-kshift-fix-20261021/prefix_run.log`)
- **M12 long-context reader recipe re-measured on C5 (CH-26a): PASS 9/9** with warm cache share >= 0.98 on 35B-MTP and 27B-DFlash2; cold legs reprocess 100% (104,698 to 191,447 tokens). See [kv-cache](kv-cache.md). ([autokernel-champion-aggregate](../handoffs/active/autokernel-champion-aggregate.md); [2026-10-26 log](../progress/2026-10/2026-10-26-workspace-58.md))

Sources: [yarn-context-extension-research](../handoffs/active/yarn-context-extension-research.md), [autokernel-champion-aggregate](../handoffs/active/autokernel-champion-aggregate.md), [2026-10-27 harvest](../progress/2026-10/2026-10-27-workspace-58.md), [2026-10-26 log](../progress/2026-10/2026-10-26-workspace-58.md)

## Compiled Update — 2026-10-28 (operator wiki sweep, workspace-58)

**Confidence: verified** (preparation records; no new YaRN measurement).

- **HELMET data restoration (YARN-AGG-1g) is approved but not run.** A bounded CPU launcher reserves 32 GiB total, keeps the 150 GiB free floor, pins the archive digest, inventories and hashes the four KILT files, and resumes per-file extraction; five model-free fixture tests passed. No dataset was downloaded and no model ran. ([yarn-context-extension-research](../handoffs/active/yarn-context-extension-research.md); [YaRN restore](../progress/2026-10/2026-10-27-ni-yarn-restore.md))
- **A fresh 120-pair native Oolong cohort is approved as a GPU observation.** It records model, store-library, template, source and arm-recipe digests before each window's first load and uses the existing native McNemar rule; it does not pool or regrade historical windows. Historical windows lack some content digests, so the pooling task stays open, and the finite cohort may be underpowered. ([yarn-context-extension-research](../handoffs/active/yarn-context-extension-research.md))
- **YaRN CPU fixed120 s0-s3 all ended rc1** ("captured process did not exit"); a YaRN s3 correctness run was co-tenant with a 42 s preflight on revoked CPUs, ruled no invalidation by the owner because co-tenancy cannot change a correctness verdict. ([2026-10-28 workspace-58](../progress/2026-10/2026-10-28-workspace-58.md))

Sources: [yarn-context-extension-research](../handoffs/active/yarn-context-extension-research.md) · [YaRN restore](../progress/2026-10/2026-10-27-ni-yarn-restore.md) · [2026-10-28 workspace-58](../progress/2026-10/2026-10-28-workspace-58.md)

## Compiled Update — 2026-10-29 (operator wiki sweep, workspace-58)

**Confidence: verified** for the recorded failed-run facts; the harness causes are as stated in the filing, the fixes are not yet measured.

- **The CPU fixed-120 v3 native Oolong run produced zero scored pairs: FAILED-RUN, harness class, no verdict.** Shards s0/s1/s3 spent the whole ~8 h window on their first A0 item (`oolong_synth@131072`) and hit `TimeoutError` at window end; s2 never scored because the worker died on `ModuleNotFoundError: No module named 'dateutil'`. Coverage is 0/120, so the predeclared one-sided exact McNemar rule is not evaluable. Nothing here is evidence for or against the extension arms.
- **Follow-on harness work is filed, not done (YARN-CPU-V3-HARNESS):** an import preflight so a missing module fails at dry-run, bounding per-item wall (a single 128k A0 item does not fit an ~8 h CPU-quarter window; moving 128k items to GPU is the alternative), and resumable (rc75) window-end exits.
- **The standing extension-arms read is unchanged:** NOT-FAIL-underpowered (74 native pairs, McNemar p=0.5), explicitly not an equivalence claim; HELMET nq/hotpotqa 128k remain dropped (KILT data missing).
- **FA-INT64-OFFSET fold is reconciled:** the three commits are recorded as present in the champion, a precondition for any run past 512K (audit-reconciliation, not a new measurement).

Sources: [yarn-context-extension-research](../handoffs/active/yarn-context-extension-research.md) · [2026-10-28 workspace-58 progress](../progress/2026-10/2026-10-28-workspace-58.md) · [2026-10-29 workspace-58 progress](../progress/2026-10/2026-10-29-workspace-58.md) · [2026-10-28 codex C3 prep](../progress/2026-10/2026-10-28-codex-c3-prep.md)
