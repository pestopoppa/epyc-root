# Agent Architecture

**Category**: `agent_architecture`
**Confidence**: verified
**Last compiled**: 2026-04-13
**Sources**: 22 documents (3 deep-dives, 15 intake entries, 4 handoffs)

## Summary

The EPYC orchestrator is a pydantic_graph-based multi-agent system running on a single AMD EPYC 9655 (192 threads, 2 NUMA nodes) with llama.cpp as the inference backend. It uses 7 typed node classes across 4 model tiers (frontdoor, coder, architect, worker), a 180+ field mutable TaskState, and compile-time safe transitions via Union return types. Routing decisions are made by a MemRL learned routing system with MLP+GAT classifiers, Q-value weighted voting, and a factual-risk scorer. A 3-tier escalation ladder (worker to coder to architect) handles complexity beyond the initial role's capability, while a 5-layer context management pipeline (hard preview, stale clearing, session log, compaction/virtual memory, solution file persistence) ensures context window pressure stays manageable on the 8K-32K windows available to local quantized models.

Three deep-dives map the design space against external architectures. Paperclip (intake-115) represents the hierarchical org-chart model: N-level reporting chains with `reportsTo` self-referential foreign keys, heartbeat-driven agent invocation, PostgreSQL-backed issue tracking with atomic checkout and full goal ancestry, and a three-tier cost governance layer (visibility, soft alerts, hard ceiling with auto-pause). Its coordination is task-centric -- all inter-agent communication flows through issue creation and status updates, with no separate messaging system. AgentRxiv (intake-131) represents the peer-to-peer model: independent research labs operating autonomously and sharing findings through a preprint server indexed by SentenceTransformer embeddings. Coordination emerges from shared knowledge rather than explicit orchestration, achieving 13.7% improvement on MATH-500 through iterative accumulation, though with a critical weakness -- no quality control on shared findings, leading to hallucinated papers polluting the knowledge base. OpenGauss (intake-172/173) represents the production agent shell: a CLI-first multi-agent orchestrator forked from hermes-agent and specialized for Lean 4 theorem proving, with managed backend spawning, protected-zone context compression with tool-pair sanitization, prompt injection scanning, ACP (Agent Client Protocol) server, and ShareGPT-format trajectory export.

The EPYC orchestrator's tiered pipeline sits between these topologies. It has stronger coordination than AgentRxiv's peer-to-peer approach (explicit routing decisions, escalation chains, safety gates) but less rigid hierarchy than Paperclip's org chart (no persistent issue database, request-scoped lifecycle). Where it genuinely leads the field is in three areas: (1) learned routing intelligence that no surveyed framework matches -- MemRL Q-value weighted routing, factual-risk scoring, difficulty signal classification, 9 production routing subsystems that coordinate without conflicting; (2) 5-layer context management versus basic message trimming (LangGraph) or no management at all (Paperclip, AgentRxiv); and (3) production safety infrastructure with 43+ feature flags, quality floor gates, per-suite regression guards, consecutive failure auto-rollback, and a think-harder ROI calculation that regulates compute spend on escalation.

The key architectural tension is between the current pydantic_graph's flat 7-node structure and the need for composable subgraphs as the system grows. LangGraph's subgraph composition, checkpoint granularity with time-travel debugging, and `interrupt()` flexibility at any node represent genuine capability gaps. However, migration carries significant risk: 180+ state fields, 120+ tests, and deep domain-specific features (MemRL, think-harder ROI, budget enforcement, 5-layer context) have no LangGraph equivalents and would require porting. The recommended path is hybrid -- build new capabilities as LangGraph subgraphs alongside the existing pydantic_graph, migrating nodes incrementally.

## Key Findings

- **Cost governance is the largest identified gap.** Paperclip's three-tier model (visibility via real-time dashboards, soft alerts at configurable thresholds, hard ceiling with atomic auto-pause when `spentMonthlyCents >= budgetMonthlyCents`) is directly adoptable. Cost events track provider, model, input/output tokens, cost in cents, and full goal ancestry for attribution. The orchestrator currently tracks token usage but has no budget enforcement, no per-request cost attribution, and no auto-throttle. For CPU inference, cost maps to wall-clock compute time per NUMA node rather than API billing, so per-role time budgets may be more appropriate than per-token budgets. [agent-architectures-paperclip-agentrxiv.md](../research/deep-dives/agent-architectures-paperclip-agentrxiv.md)

- **LangGraph's checkpoint granularity enables time-travel debugging that our resume_tokens cannot match.** Our system captures ~10 fields in <500 bytes at resume points; LangGraph checkpoints full state at every node transition with pluggable backends (Postgres, Redis, in-memory). If a worker produces bad output at turn 3 that cascades to a coder failure at turn 7, we cannot replay from turn 3 with a different approach. The incremental recommendation: log TaskState snapshots at each node transition (~50 lines in persistence.py) for post-hoc debugging without full migration. [langgraph-ecosystem-comparison.md](../research/deep-dives/langgraph-ecosystem-comparison.md)

- **The orchestrator's domain-specific features are substantially more sophisticated than any surveyed framework.** LangGraph offers basic message trimming and manual lambda routing; Paperclip has no context management or learned routing; AgentRxiv operates on fixed-format LaTeX with no quality control. EPYC's 5-layer context management, MemRL learned routing, error taxonomy with 3-tier escalation ladder, think-harder ROI regulation, and 43+ feature flags with live toggle represent production-hardened capabilities that no framework provides out of the box. [langgraph-ecosystem-comparison.md](../research/deep-dives/langgraph-ecosystem-comparison.md)

- **OpenGauss's tool-pair sanitization solves a critical context compression bug.** When context is compressed, orphaned tool calls (call without result) or orphaned tool results (result without call) cause API rejections and can break downstream processing. OpenGauss's `_sanitize_tool_pairs()` pattern -- stub results for orphaned calls, removal of orphaned results -- with protected-zone parameters (first 3 + last 4 turns preserved, 50% trigger, ~2500 token summary target) is directly portable to session_log.py. [opengauss-architecture-analysis.md](../research/deep-dives/opengauss-architecture-analysis.md)

- **Paperclip's request depth tracking prevents infinite escalation loops.** A simple integer `requestDepth` counter on issues tracks delegation hops. When Agent A creates a task for Agent B, depth increments. This is trivially adoptable as an `escalation_depth` field on EscalationContext (~2 hours). Our escalation chain currently has no depth counter. [agent-architectures-paperclip-agentrxiv.md](../research/deep-dives/agent-architectures-paperclip-agentrxiv.md)

- **Meta-harness optimization shows execution trace feedback provides +15 points over score-only feedback** for automated harness optimization (34.6% median accuracy with scores only, 50.0% with full filesystem access to traces). This is implemented as Tier 1 in the autopilot: inference_tap.log traces are fed back to PromptForge's mutation step. Tier 2 extends the search space to Python orchestration code (not just prompt templates), with an allowlist of 4 mutable files and ast.parse() syntax validation. [intake-244, meta-harness-optimization.md handoff]

- **Reasoning chain compression is an active research front with direct CPU inference applicability.** FlowSteer (intake-126) uses nonlinear activation steering to transform verbose reasoning into concise chains with input-dependent control enabling per-request reasoning budget allocation. S3-CoT (intake-125) uses self-sampled succinct reasoning via activation steering with no teacher model required. Both address the fundamental tension on CPU inference: thorough reasoning burns scarce tokens in constrained 8K-32K context windows. [intake-125, intake-126]

- **REPL tool invocations hurt accuracy on 7/10 evaluation suites** (the "Omega problem"). Direct mode outperforms REPL on agentic (-54pp), coder (-44pp), and general (-26pp) suites. Only hotpotqa (+12pp) and gpqa (+6pp) benefit from tool use. This motivates both prompt-side fixes (tighter tool-use policy) and structural fixes (frecency discovery, combined operations, contextual suggestions) to make each tool invocation more valuable. [repl-turn-efficiency.md handoff]

- **CoT reasoning expands factual recall but introduces hallucination risks.** Two mechanisms drive recall improvement: computational buffer (extra forward passes) and factual priming (semantic associations). However, generative self-retrieval creates fabricated intermediate facts that propagate through the reasoning chain. This informs the factual-risk scorer design: high-risk factual queries should route to larger models with better parametric knowledge. [intake-103](https://arxiv.org/abs/2603.09906)

- **Agentic Critical Training (ACT) shows RL-based self-reflection outperforms imitation by +5.07 points** and transfers across model sizes (4B trained with 8B trajectories reaches 92.14% on ALFWorld). ACT also improves general reasoning (MATH-500 87.73%) without reasoning-specific training data. This validates the autopilot's approach of using GRPO-based training for routing model improvement. [intake-106](https://arxiv.org/abs/2603.08706)

- **Agent context files can hurt performance.** ETH Zurich research (intake-272) found context files reduce task success rates and increase inference cost by 20%+. The thin-map architecture used by EPYC's agent files may be near-optimal, but requires empirical validation via instruction token budget tracking (AP-16). [intake-272](https://arxiv.org/abs/2602.11988)

- **Harness engineering, not model capability, is the primary performance differentiator.** The "Skill Issue" practitioner study (intake-271) showed ~28 rank positions on TerminalBench-2 from harness changes alone on the same Opus model. The "Mismanaged Geniuses" hypothesis (intake-312) extends this: frontier LLMs are already superhuman on hardest exams (IMO, IOI), and the bottleneck is orchestration, not model power. A 4B RLM achieved 100% on MRCRv2 via composition. [intake-271, intake-312]

## Actionable for EPYC

### High Priority
1. **Add cost event logging to the inference path** -- per-role/per-request cost tracking with configurable monthly budgets per model tier. Auto-degrade to cheaper model rather than hard-stop when budget exceeded. Effort: ~2 days. Source: Paperclip cost governance model.
2. **Port tool-pair sanitization** from OpenGauss's `context_compressor.py` into session_log.py. Critical for context compression reliability. Effort: ~4 hours.
3. **Continue AR-3 autopilot run** with GEPA integration, short-term memory, and self-criticism loop. All infrastructure is implemented and verified. State at trial_counter=46.

### Medium Priority
4. **Add escalation depth counter** to EscalationContext -- increment on each escalation, hard cap at configurable max (e.g., 3). Effort: ~2 hours.
5. **Thread request_id through all cost events** for per-request cost attribution. Effort: ~4 hours.
6. **Instruction token budget tracking** (AP-16) -- count tokens in all loaded .md templates, alert if ratio > 20%. Prerequisite for structural pruning experiments.
7. **State history snapshots at node transitions** for post-hoc debugging (~50 lines in persistence.py).
8. **Address the Omega problem** -- REPL turns hurting accuracy on 7/10 suites requires both prompt-side (tighter tool policy) and structural (frecency, combined ops) interventions.

### Deferred
9. **LangGraph migration assessment** -- strongest argument is subgraph composition for heterogeneous agent types, but migration cost is high. Recommended: hybrid approach, building new capabilities as LangGraph subgraphs alongside existing graph.
10. **Approval gates before production deployment** -- adopt Paperclip's board approval pattern for autopilot configuration changes affecting live traffic.
11. **Agent Protocol / ACP naming alignment** -- align API naming with Runs/Threads/Store standard for future interop. ACP (OpenGauss) extends Agent Protocol with session forking and structured callbacks.
12. **Multi-backend abstraction** -- OpenGauss's `ManagedWorkflowSpec` pattern shows how to abstract over multiple backends (llama-server, vLLM, TGI) with per-backend config generation.

## Open Questions

- Should the orchestrator migrate to LangGraph or evolve pydantic_graph incrementally? The subgraph composition argument is strong, but 180+ state fields, 120+ tests, and deep domain-specific features create migration risk. The recommended path is hybrid: build new capabilities as LangGraph subgraphs alongside the existing graph.
- What is the right cost model for CPU inference? Paperclip's per-token pricing assumes API billing. For local inference, cost maps to wall-clock compute time per NUMA node. Per-role time budgets may be more appropriate than per-token budgets.
- How should cross-layer preferences propagate in the Hermes outer shell architecture? User preferences expressed to Hermes reach the orchestrator as text in the prompt unless deterministic override flags (`routing_override`, `max_escalation`, `force_model`) are used via API parameters.
- Can a 32B local model do diagnostic reasoning from execution traces, or does this require Opus-class capability? The Meta-Harness paper only tested Opus.
- How does reasoning chain compression (FlowSteer, S3-CoT) interact with speculative decoding acceptance rates? Shorter reasoning chains may change the distribution of draft token acceptance.
- What is the optimal balance between tool availability and the Omega problem? 7/10 suites perform worse with REPL tools, but some tasks genuinely need them.

## Related Categories

- [Routing Intelligence](routing-intelligence.md) -- MemRL learned routing is the core input classifier for agent role selection
- [Memory Augmented](memory-augmented.md) -- episodic, strategy, and skill memory stores that inform routing decisions
- [Autonomous Research](autonomous-research.md) -- the autopilot system that continuously optimizes agent configuration
- [Tool Implementation](tool-implementation.md) -- GitNexus codebase intelligence for coding agent context
- [Context Management](context-management.md) -- 5-layer context pipeline is a core architectural subsystem

## Source References

- [Paperclip & AgentRxiv deep dive](../research/deep-dives/agent-architectures-paperclip-agentrxiv.md) -- cost governance model (3-tier enforcement), ticket system with atomic checkout, shared knowledge accumulation, request depth tracking, heartbeat-driven invocation
- [LangGraph ecosystem comparison](../research/deep-dives/langgraph-ecosystem-comparison.md) -- checkpoint granularity gap, subgraph composition need, interrupt() flexibility, state immutability + reducers, domain advantages assessment (EPYC leads in 7 categories)
- [OpenGauss architecture analysis](../research/deep-dives/opengauss-architecture-analysis.md) -- tool-pair sanitization, protected-zone context compression, multi-backend abstraction, ACP server, prompt injection scanning, session analytics, trajectory export
- [intake-103](https://arxiv.org/abs/2603.09906) Thinking to Recall -- CoT reasoning expands factual recall via computational buffer and factual priming; hallucination risk from generative self-retrieval
- [intake-105](https://arxiv.org/abs/2603.08640) PostTrainBench -- agents can surpass official baselines in targeted scenarios (BFCL 89% vs 67%) but substantially underperform on general post-training (23.2% vs 51.1%)
- [intake-106](https://arxiv.org/abs/2603.08706) Agentic Critical Training -- GRPO-based self-reflection for quality-aware agents; transfers across model sizes
- [intake-115](https://github.com/paperclipai/paperclip) Paperclip -- org-chart multi-agent orchestration with cost governance (~23k GitHub stars)
- [intake-117](https://github.com/NousResearch/hermes-agent) Hermes Agent -- self-improving agent with learning loop, FTS5+LLM summarization memory; validates outer-shell architecture
- [intake-120](https://openai.com/index/reasoning-models-chain-of-thought-controllability/) Reasoning Models Struggle to Control CoT -- 0.1-15.4% controllability, lower controllability correlates with higher monitorability
- [intake-125](https://arxiv.org/abs/2602.01982) S3-CoT -- self-sampled succinct reasoning via activation steering, no teacher model
- [intake-126](https://arxiv.org/abs/2602.05539) FlowSteer -- nonlinear activation steering for concise reasoning with input-dependent per-request budget
- [intake-131](https://arxiv.org/abs/2503.18102) AgentRxiv -- collaborative autonomous research, shared preprint server, 13.7% improvement on MATH-500
- [intake-133](https://arxiv.org/abs/2603.08462) Reasoning as Compression -- information bottleneck view of budget forcing; theoretical grounding for think-harder ROI
- [intake-271](https://www.humanlayer.dev/blog/skill-issue-harness-engineering-for-coding-agents) Skill Issue -- harness engineering drives ~28 rank positions on TerminalBench-2
- [intake-272](https://arxiv.org/abs/2602.11988) Evaluating AGENTS.md -- context files reduce success rates +20% cost; thin-map may be optimal
- [intake-312](https://alexzhang13.github.io/blog/2026/mgh/) Mismanaged Geniuses Hypothesis -- orchestration, not model power, is the bottleneck; 4B RLM achieves 100% MRCRv2
- [meta-harness-optimization.md](../handoffs/active/meta-harness-optimization.md) -- execution trace feedback (+15pts), code mutation search space, GEPA integration
- [repl-turn-efficiency.md](../handoffs/active/repl-turn-efficiency.md) -- Omega problem (7/10 suites worse with REPL), frecency discovery, combined operations
- [tool-output-compression.md](../handoffs/active/tool-output-compression.md) -- 7-handler output compression, 60-90% token reduction per tool output
- [autopilot-continuous-optimization.md](../handoffs/active/autopilot-continuous-optimization.md) -- 4-species architecture, safety gates, evolution manager, GEPA optimizer
- [claude-code-local-constellation-routing.md](../handoffs/active/claude-code-local-constellation-routing.md) -- MCP tool delegation, deterministic routing overrides
- [hermes-outer-shell.md](../handoffs/active/hermes-outer-shell.md) -- two-layer architecture with deterministic routing override flags, cross-layer preference propagation
