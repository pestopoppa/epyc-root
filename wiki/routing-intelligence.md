# Routing Intelligence

**Category**: `routing_intelligence`
**Confidence**: verified
**Last compiled**: 2026-04-13
**Sources**: 17 documents (0 dedicated deep-dives, 13 intake entries, 2 handoffs, 2 cross-referenced deep-dives)

## Summary

Routing intelligence is the subsystem that decides which model role handles each incoming request on the EPYC 9655. Unlike the academic routing literature -- which typically studies model selection for API-based services with hundreds of cloud-hosted endpoints -- the EPYC orchestrator routes across 4 locally-hosted model tiers on a single 192-thread CPU server with 2 NUMA nodes. Routing decisions must account for NUMA topology (which model is hot-loaded on which node), speculative decoding compatibility, context window capacity per model, and the sequential loading constraint (concurrent mlock crashes the system). A bad routing decision does not just cost money -- it blocks scarce inference capacity on a shared machine.

The routing architecture has evolved from 9 brittle keyword heuristics scattered across route modules (`_is_summarization_task`, `_should_use_direct_mode`, `_detect_output_quality_issue`, etc.) to a layered classification and routing pipeline. The unified `src/classifiers/` module provides three classifier categories: Input classifiers (prompt intent detection, summarization/vision/direct-mode/factual-risk classification backed by MemRL embeddings with keyword fallback), Output classifiers (verdict parsing, stub detection, tool noise stripping via config-driven regex from YAML), and Quality classifiers (repetition detection, garble detection, quality issues, factual-risk scoring with per-role adjustment). All configuration is YAML-driven in `orchestration/classifier_config.yaml` -- new categories require YAML edits, not code changes.

The factual-risk scorer represents the most significant routing innovation in the current pipeline. It operates at the input stage, extracting features including date questions, entity questions, citation requests, claim density, uncertainty markers, and factual keyword ratio. Per-role adjustment accounts for model capability tiers (0.6x for 122B+ architects, 0.8x for 30-35B frontdoor/coder, 1.0x for 3-7B workers). The scorer runs in shadow mode with confirmed p95 overhead <5ms, logging risk scores on every request since 2026-03-15. Enforcement mode is pending A/B testing (RI-7) that requires production stack + orchestrator API running.

The broader routing stack comprises 9 production subsystems that must coordinate without conflicting: RoutingClassifier MLP, GraphRouter+GAT, BindingRouter, FailureGraph veto, conformal prediction risk gate, think-harder in EscalationPolicy, cost-aware Q-scoring, plan review gate, and SkillAugmentedRouter. The conformal prediction gate operates on output uncertainty while factual-risk operates on input characteristics -- complementary signals that must not double-gate. The difficulty_signal.py classifier produces the first routing gate, determining whether a request can be handled by a cheap model (worker) or needs escalation to more capable tiers.

The 13 intake entries tagged as routing_intelligence are predominantly `already_integrated` foundational papers from the mixture-of-experts (arXiv:2206.01855), speculative decoding (arXiv:2207.10342), and learned routing (arXiv:2305.05176, arXiv:2309.11495) literatures. These informed the original MemRL design. The one `worth_investigating` entry is Reason-ModernColBERT (intake-174), a 150M-parameter late-interaction retriever that outperforms 7B+ dense retrievers on reasoning-intensive BRIGHT benchmarks by +7.3 NDCG@10 using MaxSim scoring on a ModernBERT backbone. This could improve the classification retriever's embedding quality for routing decisions.

## Key Findings

- **The 9-heuristic problem is solved.** All brittle keyword heuristics now delegate to the unified `src/classifiers/` module with YAML-driven configuration. New classification categories require YAML edits, not code changes. 61 unit tests cover the classifiers. The original functions in chat_utils.py and chat_review.py remain as thin delegating wrappers for zero import breakage. [routing-intelligence.md handoff, Phase 1]

- **MemRL-backed classification provides Q-value weighted voting for routing decisions.** The `ClassificationRetriever` (315 lines) in `src/classifiers/classification_retriever.py` uses episodic memory with Q-value weighted voting and keyword fallback. It provides `classify_prompt()`, `classify_for_routing()`, and `should_use_direct_mode()` methods. Exemplar seeding from YAML happens automatically on first startup. This represents a fundamentally more sophisticated approach than any surveyed framework -- LangGraph has only manual lambda routing, Paperclip routes via org-chart hierarchy, AgentRxiv has no routing at all. [routing-intelligence.md handoff, Phase 2; langgraph-ecosystem-comparison.md]

- **Factual-risk scoring is implemented and logging but not yet enforcing.** The regex-only scorer in `src/classifiers/factual_risk.py` (280 lines, 43 tests) has confirmed p95 overhead <5ms in shadow mode. Per-role adjustment scales the risk score by model capability tier. The 2000-example calibration dataset (RI-1) is built. Enforcement requires wiring into cheap-first bypass, plan review gate, escalation policy, failure graph veto, and review objective. [routing-intelligence.md handoff, Phase 3-4]

- **Nine production routing subsystems must coordinate without conflicting.** The integration map documents how each subsystem interacts: the difficulty signal gates cheap-first, the MLP classifier handles role selection, the GAT router uses graph-based features, the BindingRouter handles forced assignments, the FailureGraph vetoes known-bad routes, conformal prediction gates output uncertainty, think-harder regulates escalation compute, cost-aware Q-scoring adjusts for NUMA load, the plan review gate validates generated plans, and the SkillAugmentedRouter adjusts for tool availability. No unified priority scheme exists for the full stack when all are enabled simultaneously. [routing-intelligence.md handoff, Integration Map]

- **The difficulty signal classifier is the first routing gate.** Located in `difficulty_signal.py`, it produces a difficulty score and band that determine whether a request can be handled by a cheap model (worker) or needs escalation. When difficulty > 0.7, the system routes to higher-capability models. This feeds directly into the cheap-first policy in `_try_cheap_first()`, which is the primary cost-saving mechanism. [Cross-reference from langgraph-ecosystem comparison]

- **Species budget rebalancing dynamically adjusts optimization effort across routing dimensions.** The MetaOptimizer in the autopilot tracks stagnation per species and reallocates trial budgets. With GEPA integration, 30% of PromptForge trials now use evolutionary Pareto-optimal search for prompt mutations, including routing prompt templates. [autopilot-continuous-optimization.md handoff]

- **Foundational routing research (intake-012 through intake-095) is already integrated.** 12 papers on mixture-of-experts routing, speculative decoding, and learned routing informed the original MemRL design. No new adoption needed from these entries. [intake entries]

- **Late-interaction retrieval could improve classification quality.** Reason-ModernColBERT (intake-174) uses a 150M-parameter ColBERT model with MaxSim late-interaction scoring that outperforms 7B+ dense retrievers on reasoning benchmarks. The CachedContrastive training loss is efficient. This architecture could replace the current dense embedding model in the classification retriever with better semantic matching on reasoning-intensive routing decisions. [intake-174]

- **OPSDC's difficulty adaptation is a zero-cost routing signal.** The reasoning compression research (intake-110) shows that comparing output length with vs without a conciseness prompt produces a difficulty ratio: large ratio = easy problem (route to fast model), small ratio = hard problem (escalate). This KL divergence between concise-prompted and base model is available without any additional training. [reasoning-compression.md handoff]

## Actionable for EPYC

### High Priority (next compute session)
1. **RI-7 A/B test** -- run factual-risk enforce vs off on 500+ questions to validate risk-aware routing. Blocked on production stack + orchestrator API running.
2. **Phase 4 enforcement wiring** -- integrate risk outputs into cheap-first bypass, plan review gate, escalation policy, failure graph veto, and review objective. The shadow data should now have weeks of accumulated scores for threshold calibration.

### Medium Priority
3. **Risk fields on RoleResult** in `seeding_types.py` -- claimed complete 2026-03-06 but verification shows fields absent. Must re-add before Phase 5 seeding integration.
4. **Structured review objective** -- replace `answer[:100]` proxy with `{"task_type": str, "risk_band": str, "key_claims": list[str], "verification_focus": str}` for the review trigger.
5. **Risk-aware reward shaping** -- high-risk prompts that produce correct answers should get a Q-value reward bonus in `q_scorer.py`. This trains the routing to prefer capable models for factual queries.
6. **Unified routing priority scheme** -- document and implement the priority ordering and blend formula for all 9 routing subsystems when running simultaneously.

### Lower Priority
7. **Evaluate Reason-ModernColBERT** (intake-174) as a replacement for the classification retriever's current embedding model. Late-interaction retrievers are optimized for reasoning tasks, and the 150M parameter size is CPU-friendly.
8. **GAT risk feature injection** -- when the GraphRouter+GAT is enabled, factual-risk band should be an input feature, not a post-hoc filter.
9. **Skill-augmented risk attenuation** -- when web_search skill is available, factual-risk score should be attenuated (the model can verify claims externally).
10. **OPSDC difficulty signal** -- integrate conciseness-ratio difficulty estimation as an auxiliary input to the difficulty_signal.py classifier.

### Blocked
11. **Phase 6 controlled rollout** -- progressive enforcement from frontdoor canary (25%) through global. Blocked on Phase 4 + RI-7 results.

## Open Questions

- What is the optimal interaction between conformal prediction (output uncertainty) and factual-risk scoring (input characteristics)? Currently documented as "complementary, do not double-gate," but the optimal combination formula is unknown.
- Should the FailureGraph veto threshold be modulated by factual-risk band? Currently hardcoded at `risk > 0.5`. The handoff proposes lower thresholds for high factual-risk prompts (more conservative routing).
- When all 9 routing subsystems are enabled, what is the priority ordering and blend formula? Currently documented individually but no unified priority scheme exists for the full stack.
- Can the factual-risk scorer benefit from embedding-based features beyond regex? Current p95 <5ms with regex-only. Adding embedding features would increase accuracy but also latency.
- How does routing interact with the Omega problem (REPL tools hurting accuracy on 7/10 suites)? Should routing decisions include a "mode recommendation" (direct vs REPL) alongside role selection?
- Is the classification retriever's embedding model (sentence-transformers) the bottleneck for routing quality, and would a ColBERT-style late-interaction model (intake-174) materially improve routing decisions?

## Related Categories

- [Agent Architecture](agent-architecture.md) -- routing intelligence is a core subsystem of the multi-agent orchestrator
- [Memory Augmented](memory-augmented.md) -- MemRL episodic memory provides the Q-value signals that train routing decisions
- [Autonomous Research](autonomous-research.md) -- the autopilot's Seeder species generates 3-way eval data that trains routing classifiers
- [Cost-Aware Routing](cost-aware-routing.md) -- cost dimension of routing decisions, budget enforcement

## Source References

- [routing-intelligence.md](../handoffs/active/routing-intelligence.md) -- primary handoff tracking Phases 0-6 of the unified classifier and factual-risk scorer
- [autopilot-continuous-optimization.md](../handoffs/active/autopilot-continuous-optimization.md) -- species budget rebalancing, GEPA integration for routing prompt evolution
- [LangGraph ecosystem comparison](../research/deep-dives/langgraph-ecosystem-comparison.md) -- documents EPYC routing as "fundamentally more sophisticated" than LangGraph's manual lambda routing
- [Paperclip & AgentRxiv deep dive](../research/deep-dives/agent-architectures-paperclip-agentrxiv.md) -- comparison of routing approaches (task-centric vs learned vs peer-to-peer)
- [reasoning-compression.md](../handoffs/active/reasoning-compression.md) -- OPSDC difficulty adaptation as zero-cost routing signal
- [intake-012 through intake-095] Foundational routing papers -- mixture-of-experts, speculative decoding, learned routing (all `already_integrated`)
- [intake-174] Reason-ModernColBERT -- 150M late-interaction retriever, +7.3 NDCG@10 over dense retrieval on reasoning benchmarks (worth_investigating)
