# Memory-Augmented Systems

**Category**: `memory_augmented`
**Confidence**: verified
**Last compiled**: 2026-04-13
**Sources**: 20 documents (1 deep-dive, 15 intake entries, 2 handoffs, 2 cross-referenced deep-dives)

## Summary

Memory-augmented systems are the learning infrastructure that allows the EPYC orchestrator to improve across requests and sessions. The project implements a 3-store memory architecture: an episodic store (FAISS+SQLite) that records per-request outcomes with Q-value weighted retrieval for routing decisions, a strategy store (FAISS+SQLite) that holds LLM-distilled insights from autopilot trials for species proposal guidance, and a skill bank that accumulates reusable task-solving patterns with Q-value weighted selection. These stores are backed by MemRL -- a reinforcement learning system that trains routing Q-values from 3-way evaluation comparisons, updates reward signals based on task outcomes, and uses MLP+GAT classifiers trained on accumulated memories once 500+ entries exist.

The deep-dive research reveals a fundamental design tension in agent memory systems. MemAgent (intake-156, ByteDance/Tsinghua) demonstrates that RL-trained compaction can maintain 70-80% accuracy across 437.5x context extrapolation (8K training to 3.5M test) using a fixed 1,024-token memory buffer with complete overwrite at each segment. The key mechanism is Multi-Conversation DAPO training, where K segments produce K independent conversations but reward comes only from the final answer, with advantage broadcast uniformly. The 14B MemAgent beats 32B QwenLong-L1 at all context lengths, proving that learned memory management can substitute for raw context capacity. However, the sequential processing bottleneck (K inference calls, no parallelism) makes direct adoption infeasible on CPU: a 100K document would take ~24 minutes at EPYC 9655's inference speed, and 3.5M would take ~14 hours.

The broader research landscape (15 intake entries) maps a rich design space for agent memory. The foundational tension is between raw storage (lossless but inert -- all messages verbatim, no curation) and derived storage (compact but drifting -- LLM extracts and summarizes, introducing information loss and semantic drift). Neither works alone. The nine-axis design space from intake-316 provides the analytical framework: write triggers (every turn vs threshold vs explicit), storage backend (flat file vs SQLite vs vector DB vs knowledge graph), retrieval mode (always-injected vs hook-driven vs tool-driven), curation policy (append-only vs LLM-curated vs rule-based), forgetting policy (none vs recency vs importance-weighted), and four more axes. The EPYC system occupies a distinctive position: derived storage with RL-trained curation (Q-value weighting), FAISS vector retrieval with keyword fallback, importance-weighted forgetting via Q-value decay, and hook-driven injection at routing and proposal time.

Two high-relevance entries point toward concrete next steps. MemPalace (intake-326) achieves 96.6% LongMemEval R@5 -- the highest published result for zero-cost offline memory -- using a hierarchical palace architecture (wings for projects/people, rooms for topics, drawers for raw verbatim content) with ChromaDB semantic search on unsummarized text. The key finding: metadata filtering by wing/room provides 34% retrieval improvement over flat search, suggesting that the EPYC strategy store would benefit from hierarchical organization (by species, by optimization target, by model tier) rather than flat FAISS search. Lossless Claw (intake-140) and CMV (intake-141) both demonstrate DAG-based context management that preserves all messages verbatim while providing compact active contexts through hierarchical summarization -- a pattern directly applicable to the orchestrator's context folding pipeline.

The connection between memory and the autopilot is especially significant. Before the strategy store and Evolution Manager were implemented, species operated statelessly: Seeder never read past trial outcomes, NumericSwarm used only Optuna's internal state, PromptForge built mutation prompts without past mutation outcomes, and StructuralLab did not consult experiment history. The experiment journal existed but was passive -- consumed only by the Controller's prompt template as flat text (last 20 entries). EvoScientist's finding that memory-augmented proposals dramatically outperform memoryless ones (ablation: -45.83 gap without evolution) motivated the strategy store implementation. Species now retrieve relevant past insights before making proposals via semantic search against the strategy store.

## Key Findings

- **RL-trained compaction can maintain near-flat accuracy across 437.5x context extrapolation.** MemAgent's 14B model achieves 84.4% at 28K and 78.1% at 3.5M on RULER-HotpotQA, with only 5.47pp degradation. All baselines (QwenLong-L1-32B, Qwen2.5-14B-1M, DS-R1-Distill-32B) collapse beyond 224K. The mechanism is surprisingly simple: a fixed 1,024-token memory buffer completely overwritten at each 5,000-token segment, trained with Multi-Conversation DAPO where reward from the final answer broadcasts uniformly across all segment conversations. However, the approach has critical failure modes: irreversible information loss from overwrite, memory capacity ceiling at 1,024 tokens, single-question bias (must reprocess entire document for a different query), and no streaming or backtracking. [memagent-rl-memory.md](../research/deep-dives/memagent-rl-memory.md)

- **MemAgent is not viable for direct CPU inference adoption but its concepts are extractable.** Per-segment overhead on EPYC 9655 (Qwen2.5-14B at Q4_K_M, ~14 t/s) is ~73 seconds per segment. A 100K document (20 segments) takes ~24 minutes; 3.5M (700 segments) takes ~14 hours. The sequential chain allows no parallelism. For the orchestrator's 32K-128K native windows, YaRN RoPE scaling is the right tool. MemAgent concepts worth extracting: RL-trained compaction quality (train compaction model where reward = downstream task success), fixed-size memory buffer (target fixed token budget rather than percentage-based compaction), question-guided compaction (guide by relevance when task type is known), and multi-conversation advantage broadcasting (applicable to MemRL routing training). [memagent-rl-memory.md](../research/deep-dives/memagent-rl-memory.md)

- **The raw vs derived storage tension is the foundational design question.** Raw storage preserves everything but retrieval over inert text is unreliable. Derived storage is compact and semantically organized but drifts from ground truth as LLM extraction introduces errors. MemPalace (intake-326) sidesteps this by storing raw verbatim content in "drawers" while organizing via semantic metadata in a hierarchical structure -- achieving 96.6% LongMemEval R@5, the highest published zero-cost offline result. Mem0 (intake-346, $24M funded) achieves ~85% with derived LLM extraction. The EPYC system uses derived storage (Q-value weighted, LLM-distilled strategy insights) which risks drift but enables compact retrieval. [intake-316, intake-326, intake-346]

- **Hierarchical memory organization provides 34% retrieval improvement over flat search.** MemPalace's palace architecture (wings/rooms/drawers) with metadata filtering by wing/room demonstrates that hierarchical organization is not just organizational convenience -- it materially improves retrieval accuracy. The EPYC strategy store currently uses flat FAISS search. Adding hierarchical organization (by species, by optimization target, by model tier) as metadata filters would improve retrieval relevance when species query for past insights. [intake-326]

- **DAG-based context management can be structurally lossless.** Lossless Claw (intake-140) implements an immutable store (all messages verbatim) plus an active context (summaries + recent messages) with deterministic three-level compaction escalation. CMV (intake-141) extends this with version-controlled state using DAG structure -- snapshot/branch/trim primitives and three-pass structurally lossless trimming that removes mechanical overhead while preserving all user/assistant content. Both are directly applicable to the orchestrator's context folding pipeline, which currently uses summarization that loses information. [intake-140, intake-141]

- **Agent-native memory (LLM as curator) eliminates external infrastructure dependency.** ByteRover (intake-267) uses the LLM itself to curate, structure, and retrieve knowledge through a Hierarchical Context Tree (Domain to Topic to Subtopic to Entry) with importance scoring and recency decay. No external vector DB or graph DB required. While less scalable than FAISS-backed stores, this pattern could be useful for per-session working memory where the LLM maintains a structured scratchpad of current task state. [intake-267]

- **In-context RL can internalize skills into model parameters.** Skill0 (intake-261) presents the first RL framework where agents internalize external skills (documentation, examples) into model weights during training, then operate without skill access at inference. The Helpfulness-Driven Dynamic Curriculum adjusts skill exposure based on demonstrated competence. Applicable to the orchestrator's SkillBank: if skills could be internalized via fine-tuning, the SkillBank's context overhead would be eliminated. Blocked on GPU access for training. [intake-261]

- **Optical self-compression is a novel approach to agent history management.** AgentOCR (intake-262) converts observation-action histories to compact rendered images for token reduction, with segment optical caching via hashable decomposition. While exotic, the compression quality threshold finding (c_t <= 1.2 = "free zone" where compression has no task impact) is applicable to the context folding pipeline's compaction quality evaluation. [intake-262]

- **The strategy store closes the "memoryless optimizer" gap.** Before implementation, the experiment journal was comprehensive but passive -- consumed only by the Controller as flat text. Seeder never read past trial outcomes, NumericSwarm used only Optuna internal state, PromptForge built mutation prompts without past outcomes. EvoScientist's ablation (-45.83 gap without evolution) motivated the strategy store. Species now retrieve relevant past insights before proposals, and the Evolution Manager distills knowledge every 5 trials. [evoscientist-multi-agent-evolution.md, autopilot-continuous-optimization.md]

- **Long-term conversational memory remains an unsolved problem.** The intake-316 survey identifies nine axes of the design space and concludes that no existing system adequately handles all of them. The most promising approaches combine raw and derived storage (MemPalace's drawers + rooms, EPYC's episodic + strategy stores). Forgetting policies are the least explored axis -- most systems either never forget or use simple recency, while the EPYC system uses Q-value decay which is more principled but still simplistic. [intake-316]

## Actionable for EPYC

### High Priority
1. **Hierarchical strategy store organization** -- add species, optimization_target, and model_tier metadata to strategy store entries. Filter by metadata during retrieval (MemPalace finding: +34% retrieval accuracy). Low effort: metadata already partially present in JournalEntry; needs FAISS index partitioning or pre-filter.
2. **Fixed-size compaction target** -- replace percentage-based compaction trigger (current: 60% of context window) with a fixed token budget for the compacted summary (MemAgent insight). The target budget should vary by role: worker context is more expendable than architect context. Aligns with context-folding-progressive.md Phase 2.
3. **Question-guided compaction** -- when task type is known (coding, QA, review), guide compaction by task-type relevance rather than generic summarization. The difficulty_signal.py classifier already produces task type; feed this to the compaction model. [memagent-rl-memory.md]

### Medium Priority
4. **Hybrid retrieval for episodic/strategy stores** -- add BM25 lexical matching alongside FAISS semantic search, using Reciprocal Rank Fusion (k=60) as demonstrated by GitNexus. Improves retrieval for exact function names, model names, and configuration keys that semantic search handles poorly.
5. **RL-trained compaction quality** -- train a compaction model (could reuse existing worker_explore Qwen2.5-7B) where the reward signal is downstream task success, not just summary quality. MemAgent's DAPO training achieves this for segment reading; the same principle applies to session compaction. Depends on having a fast evaluation loop.
6. **DAG-based session history** -- evaluate Lossless Claw/CMV patterns for the session_log. An immutable store (all turns verbatim, stored to disk) plus active context (summaries + recent turns) would enable lossless recovery of any prior turn while keeping the active context compact. Currently, compacted turns are lost.
7. **Strategy store cross-species fertilization** -- when a PromptForge insight is relevant to NumericSwarm's parameter search (e.g., "higher temperature helps creative tasks"), the strategy store should surface it. Currently, retrieval is species-scoped.

### Lower Priority
8. **Multi-conversation advantage broadcasting for MemRL** -- MemAgent's DAPO training pattern (broadcast final-answer reward uniformly across all segment conversations) is applicable to MemRL routing training, where a single task outcome should inform routing decisions at multiple points in the escalation chain.
9. **Per-session working memory via LLM curation** -- ByteRover's agent-native memory pattern (LLM maintains structured scratchpad) could replace or supplement the current in-memory TaskState for long-running REPL sessions. Lower priority because TaskState already serves this role.
10. **Skill internalization research** -- Skill0's ICRL framework for internalizing SkillBank entries into model weights via fine-tuning. Eliminates SkillBank context overhead at inference. Blocked on GPU access.

### Blocked
11. **RL-trained compaction** -- requires fast eval loop + GPU for training. Possible via RLVR formalization of eval tower (AP-27).
12. **Skill internalization** -- requires GPU for fine-tuning.

## Open Questions

- What is the optimal forgetting policy for the strategy store? Current Q-value decay is simple but may preserve outdated strategies that were optimal under old configurations. Should strategies have a "staleness" field that increases when the underlying config changes?
- How should the raw vs derived tension be resolved for episodic memory? Currently fully derived (Q-value weighted summaries). Adding a raw layer (verbatim request/response pairs) would enable post-hoc re-analysis but increases storage. MemPalace's approach (raw in drawers, derived in room structure) is a viable hybrid.
- Can MemAgent's multi-conversation DAPO training be adapted for MemRL routing training without GPU access? The training requires multiple conversation rollouts per sample, which is expensive on CPU.
- What is the right compaction quality threshold for "free zone" compression? AgentOCR (intake-262) found c_t <= 1.2 has no task impact. Does this transfer to text summarization, and does it vary by task type?
- Should the context folding pipeline adopt DAG-based management (Lossless Claw/CMV) or continue with the current summarization approach? DAGs preserve information but add complexity. The context-folding-progressive.md handoff explores multi-tier condensation as a middle ground.
- How does memory capacity interact with the Omega problem (REPL tools hurting accuracy)? If episodic memory provides better tool-use strategies from past successful sessions, it could guide more effective tool use rather than naive exploration.

## Related Categories

- [Agent Architecture](agent-architecture.md) -- memory stores are a core subsystem of the multi-agent orchestrator
- [Routing Intelligence](routing-intelligence.md) -- MemRL episodic memory provides Q-value signals that train routing decisions
- [Autonomous Research](autonomous-research.md) -- strategy store and Evolution Manager are the autopilot's learning infrastructure
- [Context Management](context-management.md) -- session compaction and context folding are the interface between memory and active context
- [Tool Implementation](tool-implementation.md) -- BM25+semantic hybrid search pattern applicable to memory retrieval

## Source References

- [MemAgent deep dive](../research/deep-dives/memagent-rl-memory.md) -- fixed-size buffer with complete overwrite, Multi-Conversation DAPO training, 437.5x extrapolation, O(N) complexity, CPU infeasibility analysis, extractable concepts (RL-trained compaction, fixed-size budget, question-guided compaction)
- [EvoScientist deep dive](../research/deep-dives/evoscientist-multi-agent-evolution.md) -- Evolution Manager's three knowledge distillation channels, strategy store motivation, ablation evidence (-45.83 gap without evolution)
- [Paperclip & AgentRxiv deep dive](../research/deep-dives/agent-architectures-paperclip-agentrxiv.md) -- retrieval-augmented iteration (AgentRxiv: plateau without retrieval, continued improvement with N=5), knowledge accumulation protocol
- [autopilot-continuous-optimization.md](../handoffs/active/autopilot-continuous-optimization.md) -- strategy store implementation, Evolution Manager species, species retrieval integration
- [context-folding-progressive.md](../handoffs/active/context-folding-progressive.md) -- multi-tier condensation, compaction quality evaluation methodology, RL-trained compaction roadmap
- [intake-117] Hermes Agent -- FTS5+LLM summarization memory, periodic knowledge reinforcement (worth_investigating)
- [intake-140] Lossless Claw -- DAG-based hierarchical summarization, immutable store + active context, deterministic three-level compaction (worth_investigating)
- [intake-141] CMV -- DAG-based context versioning with snapshot/branch/trim, three-pass structurally lossless trimming (worth_investigating)
- [intake-144] Deep Agents -- automatic conversation summarization, sub-agent isolation with separate contexts (worth_investigating)
- [intake-156] MemAgent -- segment-based reading with memory overwrite, Multi-Conversation DAPO, 437.5x extrapolation (worth_investigating)
- [intake-261] Skill0 -- in-context RL for skill internalization, helpfulness-driven dynamic curriculum (worth_investigating)
- [intake-262] AgentOCR -- optical self-compression, segment optical caching, compression quality threshold c_t <= 1.2 (worth_investigating)
- [intake-265] Omni-SimpleMem -- autoresearch-guided memory framework discovery, 23-stage autonomous pipeline (worth_investigating)
- [intake-267] ByteRover -- agent-native memory, hierarchical context tree, importance scoring with recency decay (worth_investigating)
- [intake-291] Rowboat -- knowledge graph as persistent memory, Markdown+backlinks (Obsidian-compatible) (worth_investigating)
- [intake-316] Long-Term Memory survey -- nine-axis design space, raw vs derived tension, unsolved forgetting policies (worth_investigating, high relevance)
- [intake-326] MemPalace -- 96.6% LongMemEval R@5, palace hierarchical architecture (wings/rooms/drawers), +34% from metadata filtering (new_opportunity, high relevance)
- [intake-346] Mem0 -- $24M cloud memory platform, ~85% LongMemEval, LLM-based extraction (worth_investigating)
