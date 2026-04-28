# Context Management

**Category**: `context_management`
**Confidence**: verified
**Last compiled**: 2026-04-28
**Sources**: 24 documents (6 deep-dives, 3 active handoffs, 15 intake entries)

## Summary

Context management is the most research-dense area in the EPYC knowledge base, driven by a fundamental constraint: CPU inference on the EPYC 9655 makes every context token expensive. Prefill cost scales linearly with sequence length, KV cache pressure limits effective concurrency, and the multi-turn REPL sessions at the core of the orchestrator grow context unboundedly unless actively managed. This is not a theoretical concern -- it determines whether a 15-turn debugging session completes in 3 minutes or 20.

Six independent research papers, spanning four institutions and three continents, converge on a shared empirical finding: agent trajectories are 80-92% redundant. The redundancy breaks into three categories: mechanical overhead (tool outputs, formatting, metadata -- 20-86% of session tokens per CMV analysis), stale observations (superseded by later tool calls, validated by "The Complexity Trap" showing observation masking matches LLM summarization), and verbose reasoning chains (less than 10% of reasoning tokens carry meaningful information per SEER's compression analysis). The research validates aggressive compression with one critical caveat: compression quality matters far more than compression aggressiveness. ReSum's central finding is that an untrained 30B model produces summaries that are *worse* than keeping raw history, while a specialized 3B-active SFT model matches 671B general-purpose models. Quality gates are mandatory.

The research landscape is converging on a spectrum from text-level to KV-level compression. On the text side, AgentFold demonstrates 92% context reduction via proactive two-level folding (granular per-turn blocks plus deep consolidation at boundaries). Context-Folding's FoldGRPO proves that structured compression within a 32K window outperforms uncompressed ReAct at 327K by 8 percentage points -- empirical proof that more context is not always better. On the KV side, Memento's dual information stream reveals that KV cache states carry implicit information beyond what summary text captures, creating a fundamental ~15pp accuracy ceiling for text-only approaches on hard reasoning tasks. Between these extremes sit latent compression methods like CoLaR (2-5x chain reduction by replacing token sequences with continuous embeddings) and iterative reasoning approaches like InftyThink and Accordion-Thinking (sawtooth memory patterns with periodic summarization).

The EPYC orchestrator implements a 5-layer context management stack that predates much of this research but aligns well with the emerging consensus. Active development is upgrading it to a multi-tier condensation system informed by AgentFold (two-level architecture), ReSum (compaction timing), CMV (structural trimming), and the Memento cluster (KV-retaining compression). The implementation is phased: Phase 0 (compaction trigger raised to 75%) and Phase 1 (two-level condensation) are complete, Phase 2 (summarizer quality evaluation) is substantially done, and Phase 3 (process reward signals) is in design.

## Key Findings

### New Finding (2026-04-21)

- **Claude Code's five-layer compaction pipeline provides an external taxonomy for EPYC's L1-L5 tiers.** "Dive into Claude Code" (arxiv:2604.14228, intake-426) documents Anthropic's own production compaction pipeline: **budget reduction → snip → microcompact → context collapse → auto-compact**. Each layer operates at a different timescale and granularity. This is directly comparable to our 5-layer stack and worth mapping one-to-one to identify coverage gaps. The paper's caveat matters more than the taxonomy: Anthropic's own harness-design blog observes "context anxiety" in Sonnet 4.5 where compaction alone became insufficient — compaction silently discards provenance and load-bearing intermediate conclusions. Context resets (hard clears) are sometimes the right tool. This is a data point for EPYC's Phase 3 quality-monitoring work: detect and log the kind of provenance loss that triggered Anthropic's context-reset fallback. [context-folding-progressive.md 2026-04-21 update] `external`

- **Claude Code five-layer compaction pipeline mapped against EPYC's L1-L5 tiers.** Budget Reduction (gap -- we have no equivalent), Snip ~ Phase 0 hard preview limits, Microcompact ~ Phase 1+ tool output compression, Context Collapse ~ Phase 2 deep consolidation, Auto-Compact ~ Phase 1 deep consolidation at boundaries. The mapping reveals a concrete coverage gap: Budget Reduction enforces per-message output size caps, replacing oversized tool outputs with content references before they enter context. EPYC has no equivalent mechanism -- tool outputs are truncated after generation, not capped during generation. [intake-426]

- **Budget Reduction gap identified as a new optimization target.** Claude Code replaces oversized tool outputs with content references (file paths, summaries) at the output generation layer, preventing large payloads from ever entering the context window. EPYC's spill-and-truncate operates post-hoc -- the model has already generated the full output and it is truncated before the next turn. A pre-generation size budget (analogous to `--max-tokens` but for tool output) would reduce wasted generation compute. [intake-426]

- **Simple embedding retrieval outperforms LLM reranking for memory-augmented context -- validates FAISS approach.** Memory Transfer Learning (arxiv:2604.14004, intake-425) shows that cosine similarity retrieval with N=3 candidates on `text-embedding-3-small` outperforms both LLM-based reranking and adaptive rewriting for cross-domain memory retrieval. This directly validates the FAISS-based retrieval in `strategy_store.py` over more complex retrieval pipelines. The finding reinforces the "simple retrieval, curated content" principle: 431 curated insight-format memories outperform 5,899 raw memories by +1.7%. [intake-425]

### Compression Architecture

- **92% context reduction achievable**: AgentFold demonstrates proactive two-level folding (granular per-turn plus deep at boundaries) keeping context at ~7,000 tokens at turn 100 versus ~91,000 for ReAct baseline, with sub-linear growth that sometimes decreases as dead-end branches are pruned. A 30B-A3B model matches proprietary o3 on WideSearch (62.1% vs 60.0%). [agentfold-proactive-context.md](../research/deep-dives/agentfold-proactive-context.md)

- **32K beats 327K with structural compression**: Context-Folding's FoldGRPO, trained on Seed-OSS-36B, proves that call-stack-style folding within 32K outperforms uncompressed ReAct at 327K by +8pp on BrowseComp+. The key mechanisms are learned branch/fold operations where the model decides when to spawn sub-trajectories and when to collapse them. Training increases tool calls from 12.9 to 19.2 per task -- the model explores more within less context. [context-folding-foldgrpo.md](../research/deep-dives/context-folding-foldgrpo.md)

- **Two compression levels serve different functions**: AgentFold's granular condensation (fold only latest interaction into fine-grained summary) preserves maximum resolution and accumulates without re-processing. Deep consolidation (fuse multiple summary blocks into single coarse summary) prevents linear context growth. The combination yields sub-linear growth because only deep consolidation is lossy -- granular blocks are exempt from re-processing, avoiding the information survival decay (36.6% at step 100 under full re-summarization). [agentfold-proactive-context.md](../research/deep-dives/agentfold-proactive-context.md)

### Compaction Timing and Quality

- **Compaction timing is critical -- not too early, not too late**: ReSum confirms that at 64K context, summarization yields +5 P@1 on BrowseComp-zh. At 128K, the benefit drops to +0.9 because the raw history is mostly usable at that window size. The production implication: compaction should trigger at 70-80% of the context window, not on a fixed turn count. Our trigger was raised from 60% to 75% based on this finding. [resum-context-summarization.md](../research/deep-dives/resum-context-summarization.md)

- **Summarizer quality is the single most important variable**: ReSum shows an untrained Qwen3-30B (3B active params) achieves 6.9% on BrowseComp-zh -- *worse* than no summarization at 8.2%. A specialized SFT-trained 3B-active model (ReSumTool-30B) matches DeepSeek-R1-671B (13.7% vs 13.0%). Quality dominates scale by an order of magnitude. Our Phase 2a evaluation confirmed 30B-A3B as minimum viable summarizer (3.0/3.0 retention score), with L3 compression as the sweet spot: 82% compression at 2.84/3 retention. [resum-context-summarization.md](../research/deep-dives/resum-context-summarization.md)

- **MEM1's constant-window approach destroys structured reasoning**: ReSum's comparison shows MEM1 (training-free fixed-window consolidation) drops GAIA accuracy by 11.7 P@1 -- too aggressive for tasks requiring structured reasoning chains. ReSum's full-context-reset approach preserves structured reasoning at the cost of ~2x token overhead from re-searching known information. [resum-context-summarization.md](../research/deep-dives/resum-context-summarization.md)

### Mechanical Bloat and Structural Trimming

- **20-86% of session tokens are mechanical overhead**: CMV's analysis of 76 Claude Code sessions shows tool-heavy sessions (those with 15%+ tool result bytes) average 39% reduction from structural trimming alone, with peaks at 86%. The key insight: raw tool outputs are consumed once by the model and synthesized into assistant responses. Keeping both the raw output and the synthesis is redundant -- CMV keeps the synthesis and stubs the raw output. [cmv-structural-trimming-repl.md](../research/deep-dives/cmv-structural-trimming-repl.md)

- **Simple observation masking matches LLM summarization**: intake-274 (The Complexity Trap, arXiv:2508.21433) finds that stripping older tool outputs achieves the same performance as expensive LLM-based summarization for agent context management, at 50% of the cost. The hybrid approach (masking plus summarization) yields only 7-11% further gains. This directly validates our pattern-based tool output compression architecture. [intake-274](https://arxiv.org/abs/2508.21433)

- **Tool output compression achieves 60-90% per command type**: Our Phase 2 native compression module implements 7 command-specific handlers (pytest, cargo test, git status/diff/log, ls, build compilers), each applying domain-appropriate strategies -- failure-focus for test runners, stats extraction for git status, error-focus for compilers. This layers upstream of the existing spill-and-truncate mechanisms for multiplicative benefit. [tool-output-compression handoff](../handoffs/active/tool-output-compression.md)

- **Progressive-disclosure retrieval is the right pattern for compressed tool outputs**: Claude-Mem (intake-395) implements a 3-layer retrieval stack (search → timeline → get_observations) with hybrid FTS5+Chroma over AI-summarized observations, claiming ~10x token savings via batched-ID full-detail fetch only after index filtering. The architectural pattern -- index filtering before bulk fetch -- directly parallels the existing truncation+peek() architecture. The component itself is not adopted (AGPL-3.0, Bun/Node stack). [tool-output-compression handoff](../handoffs/active/tool-output-compression.md)

- **Durable-workflow and snapshot-resume patterns address tool output loss on disconnect**: Open Agents (intake-397) uses Vercel Workflow SDK step persistence with stream-reconnect so tool outputs belong to sandbox state rather than agent context -- outputs survive disconnects and compaction. The pattern (control-plane / execution-sandbox separation, snapshot-based hibernate/resume) is architecturally analogous to the spill-to-file + peek() mechanism but makes sandbox state durable across long-horizon sessions. Pattern-only relevance (TS/Vercel stack). [tool-output-compression handoff](../handoffs/active/tool-output-compression.md) [repl-turn-efficiency handoff](../handoffs/active/repl-turn-efficiency.md)

- **Minimal atomic tool surfaces reduce per-turn context inflation**: GenericAgent (intake-399) operates with 9 atomic tools and a <30K context budget, using dynamic tool creation via `code_run` rather than growing the tool surface. Layered L0-L4 memory replaces full-context scanning. The design principle -- prefer lazy-loaded tool outputs and skill crystallization of repeat tasks -- reinforces the existing compression-first architecture and the REPL turn efficiency goal. [tool-output-compression handoff](../handoffs/active/tool-output-compression.md) [repl-turn-efficiency handoff](../handoffs/active/repl-turn-efficiency.md)

### Reasoning Chain Compression

- **Reasoning chains are 90%+ filler**: SEER's GPT-4o compression analysis reveals most CoT content is padding. DeepSeek-Qwen-7B retains only 5.71% of tokens as meaningful reasoning. QwQ-32B retains 9.36%. gpt-oss-20b retains 31.11% -- models with lower filler ratios are also the most accurate. Failed outputs are consistently ~1,193 tokens longer than successful ones across 7B, 14B, and 32B scales. [reasoning-compression-s3cot-adaptive.md](../research/deep-dives/reasoning-compression-s3cot-adaptive.md)

- **SEER's MAD-based filtering doubles naive compression**: Best-of-N sampling (N=3, which saturates -- marginal returns beyond 3 are negligible) combined with Median Absolute Deviation outlier filtering achieves 39.8% compression versus 18.2% for naive BoN, while matching or exceeding accuracy. The MAD approach is more robust than mean/stddev because it handles skewed length distributions. Loop elimination is dramatic: 73-97% of n-gram repetition loops removed. [reasoning-compression-s3cot-adaptive.md](../research/deep-dives/reasoning-compression-s3cot-adaptive.md)

- **S3-CoT discovers a latent "length direction" in activations**: A Variable-Length Direction (VL-D) emerges in the residual stream around layer 8-14 (model-dependent). Steering this direction with moderate alpha values produces shorter reasoning traces suitable for self-distillation training data. Combined with progressive compression curriculum, Qwen2.5-7B achieves 37% token reduction on GSM8K with +1.3pp accuracy. The approach is architecturally incompatible with quantized GGUF serving and Qwen3.5 hybrid SSM. [reasoning-compression-s3cot-adaptive.md](../research/deep-dives/reasoning-compression-s3cot-adaptive.md)

### Latent and KV-Level Compression

- **CoLaR compresses reasoning 2-5x via continuous embeddings**: At compression factor c=2, reasoning chains shrink 53.3% with only 4.8% accuracy drop on grade-school math. The 1/sqrt(c) scaling (not mean pooling) for embedding compression is critical -- it preserves activation variance, outperforming mean pooling by 2-3%. However, latent generation is fundamentally incompatible with speculative decoding (no rejection sampling in continuous space), only tested at 1B-1.5B scale, and requires ~1,200 LOC of llama.cpp C++ changes with no pre-trained GGUF models available. [colar-latent-compression.md](../research/deep-dives/colar-latent-compression.md)

- **KV-retaining approaches are fundamentally superior to text compression**: Memento's ablation shows recomputing KV states without block context drops AIME24 accuracy from 66.1% to 50.8% -- a 15.3pp gap from identical summary text. Probing confirms the mechanism: information from masked blocks propagates through memento KV chains at 23-27% recovery rate, concentrating in deeper layers. This is architectural (confirmed on toy transformers), not learned. Text-level compression has a ceiling that KV masking does not. [memento-iterative-reasoning-cluster.md](../research/deep-dives/memento-iterative-reasoning-cluster.md)

- **Context rot degrades performance non-linearly with length**: intake-273 (Chroma research) confirms LLMs do not process context uniformly. Performance degrades as input length increases, with distractors (topically related but incorrect content) amplifying degradation more than random content. Semantic similarity between question and context modulates the effect -- high-similarity distractors are worst. This validates aggressive pruning of stale but topically related context. [intake-273](https://research.trychroma.com/context-rot)

## Actionable for EPYC

### Implemented (Production)

- **5-layer context management stack**: (1) Hard preview limits at 1500/500 chars for output/error, (2) stale tool output clearing keeping 2 most recent blocks, (3) session log summarization every 2 turns via worker model, (4) context externalization at 75% threshold writing full context to disk with structured index, (5) solution file persistence to external storage with peek-on-demand.
- **Output spill with retrieval pointers**: `_spill_if_truncated()` writes full content to `/mnt/raid0/llm/tmp/` and appends `peek()` instruction when output exceeds preview limits. Gives the model agency to retrieve full output on demand. Feature-flagged, 9 tests.
- **Tool output compression**: 7 command-specific handlers achieving 60-90% reduction. Layers upstream of spill-and-truncate for multiplicative benefit. Feature-flagged `tool_output_compression`.
- **Tool definition compression**: 55% reduction in `DEFAULT_ROOT_LM_TOOLS` (647 to 290 words), instruction token ratio from 29.8% to 16.0%. Removed duplicates, merged related tools, flattened verbose sections.
- **Compaction trigger raised to 75%**: Configurable via `ORCHESTRATOR_SESSION_COMPACTION_TRIGGER_RATIO`. Validated by ReSum (compaction at 70-80% is optimal) and AgentFold (delay preserves critical context).
- **N-gram loop detection**: `detect_think_block_loop()` in `quality_detector.py` catches repetition loops within reasoning traces. SEER parameters inform threshold calibration.

### In Progress

- **Two-level condensation** (Phase 1 complete): Granular per-turn blocks accumulate without re-summarization (deterministic formatting from structured turn data, no LLM call). Deep consolidation fires at escalation boundaries, sub-task completion, or when 15+ blocks accumulate, using 7B model for a single bounded-window LLM call. Feature-flagged `two_level_condensation`. Replaces the previous every-2-turn full re-summarization.
- **Compression quality evaluation** (Phase 2a/2b done): 30B-A3B validated as minimum viable summarizer (3.0/3.0 retention). 5-level compression ladder tested: L3 is the sweet spot at 82% compression with 2.84/3 retention. L5 and Phase 3c (process reward signals) pending.
- **Segment retention scoring**: ConsolidatedSegment with access_count, importance_score (accumulates +3 per access, +5 per update, decays at 0.995 per turn delta), and maturity tiers (draft at creation, validated at score 65+, core at 85+, demotion below 35/60).
- **Memento KV block masking feasibility**: Confirmed 2026-04-13 that `llama_memory_seq_rm()` can serve as the block eviction primitive in llama.cpp. Mid-sequence removal works; position gap semantics are correct (RoPE phases preserved). Training script for OpenMementos-228K ready with two-stage LoRA design. Blocked on model fine-tuning compute.
- **REPL turn efficiency: S6 bug fixes + observability (2026-04-16, done)**: Three systemic bugs accounting for ~25% wasted specialist REPL turns (810/3227 calls) fixed: (a) `extract_code_from_response` dropping bare `"""` lines causing 473 NameErrors; (b) `CALL("run_python_code")` routing through registry instead of REPL globals causing 182 ValueErrors; (c) dedup guard `continue → break` causing 63 wasted turns. Added `repl_turn_errors` tracking and `specialist_repl_errors` anomaly signal. Added `web_search()` REPL global and role-aware specialist prompts. S4 (A/B benchmark) and S5 Gap 1-3 implementations (workspace_scan, STUCK signal, llm_batch combined-op) remain pending inference. [repl-turn-efficiency handoff](../handoffs/active/repl-turn-efficiency.md)

### SEAL Control Vector Multi-Role Results

- **SEAL control vectors validated for MoE and dense models, blocked on SSM-hybrid**: Multi-role regression test (2026-04-13) trained a conciseness control vector on Coder-32B Q4_K_M (production quant). Worker 30B-A3B Q4KM: -7.5% tokens with NO accuracy regression (7/7 preserved). Coder 32B Q4KM: +2.2% tokens (neutral), NO regression. Frontdoor 35B SSM-hybrid: BLOCKED -- heterogeneous block architecture (alternating SSM/attention blocks, loader expects uniform). REAP 246B: deferred (too slow for cvector training). The experiment was parked in favor of AM KV compaction which delivers 5x compression at zero degradation on factual/science prompts. [reasoning-compression.md](../handoffs/active/reasoning-compression.md)
- **Branching density as compression quality signal**: intake-378 identifies Propose step ratio as a quantitative metric for evaluating which reasoning traces to compress vs keep. Convergent traces (deduction-heavy, 74.6% Deduce steps) should be preserved; divergent branches (33.3% Propose steps in R1 traces) are safe to prune. Random 10% step deletion from R1 data causes minimal/no degradation, directly validating TrimR and inference-time reasoning pruning. [reasoning-compression.md](../handoffs/active/reasoning-compression.md)

### Planned

- **Error trace intelligence** (P2): Parse Python tracebacks to extract line number and exception type before truncation. The last frame plus exception line is almost always the actionable information. ~40 lines.
- **Structured tool result stubs**: When clearing stale tool outputs, preserve metadata (tool name, key arguments, approximate size) instead of bare `[Tool result cleared]`. ~15 lines.
- **Process reward signals** (Phase 3): FoldGRPO-style penalties for unfolded tokens, out-of-scope branching, and tool call failures. Position-weighted advantage broadcasting from ReSum. Requires RL infrastructure not yet in production.

### Not Actionable

- **CoLaR latent reasoning compression**: Requires model training, tested only at 1B-1.5B scale, incompatible with speculative decoding, no GGUF ecosystem. Revisit when providers release CoLaR-trained variants of 7B+ models.
- **S3-CoT activation steering via llama.cpp**: VL-D extraction requires full-precision activations; quantization transfer is unvalidated. Incompatible with Qwen3.5 hybrid SSM architecture (Mamba2 blocks lack standard residual streams). ~2-3 weeks C++ work.
- **Context-Folding FoldGRPO training**: Requires verl framework, vLLM rollout infrastructure, and GPT-5-nano as out-of-scope judge. Research-grade approach we can approximate via SFT on simpler fold triggers.

## Open Questions

- Does the ~15pp accuracy ceiling from text-only compression (vs. KV-retaining Memento) apply to non-reasoning workloads (code generation, general QA), or is it specific to competition math where reasoning chains carry dense information?
- What is the quality threshold for our 7B `worker_explore` as a session summarizer? ReSum shows even 30B untrained models fail. Can prompt engineering compensate, or is SFT specialization mandatory?
- How does segment retention scoring interact with observation masking? intake-274 suggests masking old observations is equivalent to high recency weight -- should we collapse these into a single mechanism?
- Bullet-list vs. narrative consolidation format: intake-273 (context rot) finds shuffled content outperforms structured content for retrieval tasks, but this may reverse for reasoning. A/B test needed.
- What is the break-even point for multi-layer compression stacking (KV quantization + block masking + compaction)? Each pair tested independently; quality cliff under triple stacking is the key unknown. Theoretical combined: up to 120x; conservative estimate: 40x.
- Can AgentFold's two-level approach be replicated with prompt engineering alone (no SFT), or does the model need fine-tuning to reliably produce structured folding directives?
- Does the progressive-disclosure retrieval pattern from intake-395 (Claude-Mem) apply to tool-output retrieval in our spill-to-file architecture? The FTS5+Chroma index-before-fetch design could reduce peek() round-trips when models need to scan multiple spilled outputs.
- S6 fixed ~25% wasted REPL turns via bug fixes (S6a-c). After these fixes, does the Omega metric (7/10 suites show tools hurt accuracy) change materially, or does the fundamental direct-vs-REPL accuracy gap persist even with correct tool routing?

## Related Categories

- [Context Extension](context-extension.md) -- Fundamental methods (RoPE scaling, YaRN, sparse attention) that determine the raw context budget within which management techniques operate
- [Cost-Aware Routing](cost-aware-routing.md) -- Routing decisions determine which models handle compression and how much context each tier receives; difficulty bands modulate compression aggressiveness
- [LLM Prompting](llm-prompting.md) -- Conciseness prompting is a zero-cost context reduction technique; CoT controllability research bounds its effectiveness on RL-trained reasoning models

## Source References

- [Reasoning Chain Compression (S3-CoT + SEER)](../research/deep-dives/reasoning-compression-s3cot-adaptive.md) -- VL-D activation steering, SEER MAD-based filtering, n-gram loop detection, progressive compression curriculum
- [Context-Folding / FoldGRPO](../research/deep-dives/context-folding-foldgrpo.md) -- Branch/fold call-stack architecture, 32K beats 327K finding, process reward signals for folding quality
- [ReSum Context Summarization](../research/deep-dives/resum-context-summarization.md) -- Compaction timing (70-80% trigger), summarizer quality threshold, diminishing returns at 128K, MEM1 failure mode
- [CoLaR Latent Compression](../research/deep-dives/colar-latent-compression.md) -- Latent reasoning embeddings, 1/sqrt(c) scaling, KV cache implications, llama.cpp ~1200 LOC estimate
- [AgentFold Proactive Context](../research/deep-dives/agentfold-proactive-context.md) -- Two-level condensation architecture, 92% context reduction, sub-linear growth, information survival analysis
- [CMV Structural Trimming](../research/deep-dives/cmv-structural-trimming-repl.md) -- Three-pass trimming algorithm, synthesis-over-raw principle, gap analysis vs EPYC 5-layer stack
- [Memento Iterative Reasoning Cluster](../research/deep-dives/memento-iterative-reasoning-cluster.md) -- Dual information stream, 15pp KV vs text ceiling, block masking feasibility, quad-stack KV compression
- [intake-273](https://research.trychroma.com/context-rot) Context Rot (Chroma) -- Performance degradation with input length; semantic similarity modulates distractor impact
- [intake-274](https://arxiv.org/abs/2508.21433) The Complexity Trap (arXiv:2508.21433) -- Observation masking matches LLM summarization at 50% cost; validates tool output compression
- [intake-259](https://github.com/rtk-ai/rtk) RTK Rust Token Killer -- 60-90% token reduction across 100+ commands; security concerns preclude direct adoption
- [intake-301](https://axi.md/) AXI Agent Experience Interface -- TOON format achieves ~40% token savings; progressive disclosure mirrors truncation+peek architecture
- [intake-302](https://arxiv.org/abs/2603.29919) SkillReducer -- 48% tool description compression via adversarial delta debugging; complements output compression
- [context-folding-progressive handoff](../handoffs/active/context-folding-progressive.md) -- Multi-phase production implementation: Phase 0-1 complete, Phase 2a/2b done, Phase 3 in design
- [tool-output-compression handoff](../handoffs/active/tool-output-compression.md) -- 7 command handlers, 60-90% reduction, Phase 3 definition compression done; 2026-04-17 update: intake-395 (Claude-Mem progressive-disclosure), intake-397 (Open Agents durable workflow), intake-399 (GenericAgent minimal tool surfaces)
- [memento-block-reasoning-compression handoff](../handoffs/active/memento-block-reasoning-compression.md) -- llama.cpp block masking feasibility confirmed, SFT training design complete
- [Reasoning Compression handoff](../handoffs/active/reasoning-compression.md) -- SEAL multi-role regression results, branching density metrics from intake-378, training data strategy synthesis
- [repl-turn-efficiency handoff](../handoffs/active/repl-turn-efficiency.md) -- S1-S3/S5-S6 done; S6 fixed 3 bugs causing ~25% wasted specialist REPL turns (810/3,227 calls); 2026-04-17 update: intake-397 (durable-reconnect patterns), intake-399 (minimal tool surface design pressure)
- [intake-395](https://github.com/thedotmack/claude-mem) Claude-Mem -- 3-layer progressive-disclosure retrieval (FTS5+Chroma, ~10x token savings); pattern applicable to tool-output retrieval surfaces
- [intake-397](https://github.com/vercel-labs/open-agents) Open Agents -- durable workflow + stream-reconnect + control-plane/sandbox separation; patterns for long-running tool output survival
- [intake-399](https://github.com/lsdefine/GenericAgent) GenericAgent -- 9 atomic tools + <30K context + L0-L4 memory; design pressure toward minimal tool surfaces and lazy-loaded outputs
- [intake-413](https://arxiv.org/abs/2601.10402) HCC Cognitive Accumulation -- L1/L2/L3 tiered distillation for agent memory; 56.44% MLE-Bench medal rate. Deep dive: maps to AutoPilot strategy_store upgrade (adopt_patterns)
- [intake-414](https://github.com/mibayy/token-savior) Token Savior Recall -- RRF hybrid retrieval (BM25+FAISS), content-hash staleness detection, MDL convention promotion, progressive disclosure. Deep dive: 4 extractable patterns for strategy_store.py (adopt_patterns)
- [intake-415](https://github.com/mksglu/context-mode) Context Mode -- subprocess sandbox (99% output reduction), 5KB threshold gating, FTS5 indexing, PreCompact session snapshots. Deep dive: solves PostToolUse hook limitation, 30-50% context reduction (adopt_patterns)
- [intake-418](https://arxiv.org/abs/2604.08224) Externalization in LLM Agents -- survey: weights→context→harness era progression; validates meta-harness optimization thesis (worth_investigating)
- [intake-425](https://arxiv.org/abs/2604.14004) Memory Transfer Learning -- simple embedding retrieval (cosine, N=3) outperforms LLM reranking; 431 curated insight-format memories beat 5,899 raw memories; validates FAISS-based strategy_store approach
- [intake-426](https://arxiv.org/abs/2604.14228) Dive into Claude Code -- five-layer compaction pipeline (budget reduction → snip → microcompact → context collapse → auto-compact); Budget Reduction gap identified for EPYC; "context as scarce resource" design principle

## Updates — 2026-04-28

This update consolidates progressive folding L1–L4 status, corrects two earlier framings (SLIDERS as parallel architecture not folding evolution; Flywheel `memory(action=brief)` as read-side assembler not promote-to-persistent), and confirms pi-agent-core's `transformContext` / `convertToLlm` two-stage pattern as the boundary where progressive folding belongs.

### Progressive folding L1–L4 status (consolidated)

Per [`context-folding-progressive.md`](../handoffs/active/context-folding-progressive.md), the consolidated status as of 2026-04-28:

- **Phase 0 (compaction trigger raised to 75%) — done.** Configurable via `ORCHESTRATOR_SESSION_COMPACTION_TRIGGER_RATIO`. Validated by ReSum 70-80% optimal range and AgentFold delay-preserves-context evidence.
- **Phase 1 (two-level condensation) — done.** Granular per-turn blocks (deterministic formatting, no LLM) plus deep consolidation at boundaries (single bounded-window LLM call). Feature-flagged `two_level_condensation`.
- **Phase 1+ (segment dedup) — code complete.** Cosine-similarity dedup on consolidated segments; gated behind feature flag pending production rollout decision.
- **Phase 2c (quality evaluation) — done.** 30B-A3B validated as minimum viable summarizer (3.0/3.0 retention). 5-level compression ladder tested; L3 sweet spot at 82% compression with 2.84/3 retention.
- **Phase 3a/3b — code done.** Maturity tiers (draft/validated/core), importance scoring with decay, demotion thresholds.
- **L5+ scope deferred.** L5 (cross-session synthesis) and L6+ are out of scope until L4 production data emerges.
- **Phase 3c (process reward signals) — deferred.** FoldGRPO-style penalties for unfolded tokens, out-of-scope branching, tool-call failures. Requires RL infrastructure not yet in production.

### SLIDERS as parallel architecture, NOT folding evolution (intake-494)

Earlier intake framing positioned SLIDERS as a "L5+ candidate" for the progressive-folding pipeline. **This was inaccurate.**

- **SLIDERS targets cross-document aggregation** via DB+SQL — the workload is "aggregate facts across N documents into a single answer" (typical N = 3.9M-36M tokens per corpus).
- **Progressive folding targets cross-turn compression** — the workload is "fit M turns of conversation into a fixed context budget."
- The two share the *aggregation bottleneck framing* but the **failure regimes are different**. Folding fails on summarizer drift and context-rot under semantic similarity. SLIDERS fails on schema mismatch and join cost.
- **Track SLIDERS as parallel architecture** for the cross-source aggregation problem (cross-link to `wiki/rag-alternatives.md`). NOT as a folding-pipeline upgrade. Closure-inflation note: the earlier "L5+ candidate" framing would have absorbed an unrelated architecture into the folding category, hiding the actual cross-source aggregation gap from the project map.

### Flywheel `memory(action=brief)` correctly framed as read-side assembler (intake-492)

Earlier intake framing positioned Flywheel's `memory(action=brief)` as a "promote to persistent memory" action. **This was inaccurate.**

- `memory(action=brief)` is **read-side**: token-budgeted brief assembly with confidence decay, over already-persisted vault content. It assembles a query-scoped brief from existing storage; it does NOT write anything new.
- Persistence in Flywheel happens via separate write tools (vault append, atomic-undo write contract). The `brief` action consumes those persisted entries.
- **Portable pattern for progressive-folding**: token-budgeted brief-assembly with confidence decay, applied as a *read-side query API over already-folded summaries*. NOT a promotion primitive. Useful as design reference for how a folded-summary side-car could be queried by per-turn `transformContext` (see next).

### Pi-agent-core `transformContext` / `convertToLlm` two-stage pattern (intake-473)

Per the pi-agent-core deep-dive, the two-stage message pipeline is exactly the boundary where progressive folding belongs:

- **`transformContext`** runs every turn at the **agent-message level**. Custom types are still in scope here (TaskState, ConsolidatedSegment, ToolResultMetadata). This is where folding/condensation logic should sit — it has access to typed segment objects, importance scores, and maturity tiers.
- **`convertToLlm`** runs after `transformContext` and produces the **LLM-strict** `user|assistant|toolResult` payload. By this point, all custom typing has been collapsed into the strict three-role schema. Folding decisions cannot be made here without losing fidelity.
- **Boundary lift, not code port.** The factoring is the value: separating *decide what context to keep* (typed, agent-level) from *coerce to LLM payload* (strict, prompt-level) prevents the bug class where folding logic accidentally reads strings that have already lost their provenance metadata. Naming + factoring lift; no TypeScript code is being ported.

### Sources

- [`handoffs/active/context-folding-progressive.md`](../handoffs/active/context-folding-progressive.md) — L1-L4 status consolidated, L5+ deferred, Phase 3c deferred
- intake-494 (SLIDERS) — parallel architecture, cross-link to `wiki/rag-alternatives.md`
- intake-492 (Flywheel) — read-side `memory(action=brief)` token-budgeted assembler with confidence decay; corrected from earlier "promote-to-persistent" framing
- [intake-473](https://github.com/badlogic/pi-mono/tree/main/packages/agent) pi-agent-core — `transformContext` / `convertToLlm` two-stage pattern as boundary for folding logic
