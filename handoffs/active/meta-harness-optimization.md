# Meta-Harness: Automated Harness Optimization

**Status**: Tier 1 + Tier 2 implemented. Ready for live validation via AR-3 autopilot run.
**Created**: 2026-04-01 (via research intake)
**Updated**: 2026-04-01 (Tier 1 + Tier 2 implemented)
**Categories**: agent_architecture, benchmark_methodology

## Objective

Apply Meta-Harness (arXiv:2603.28052) approach to automatically optimize our orchestrator's harness components — prompt templates, tool definitions, routing logic, and escalation pipeline — using an agentic search over harness code rather than text-only prompt optimization.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-244 | Meta-Harness: End-to-End Optimization of Model Harnesses | high | new_opportunity |
| intake-240 | GEPA: Reflective Prompt Evolution | medium | worth_investigating |

## Key Findings from Deep-Dive

### Critical Ablation (Table 3 — the core insight)
| Feedback Mode | Median Accuracy |
|---|---|
| Scores only | 34.6% |
| Scores + text summaries | 34.9% |
| **Full filesystem access (traces)** | **50.0%** |

Full execution traces provide +15 points over score-only feedback. This directly maps to our PromptForge gap.

### Results on Agent Tasks
- TerminalBench-2 (89 CLI tasks): **76.4% (Opus), 37.6% (Haiku)** — #1-#2 on leaderboard
- RAG math (200 IMO-level): +4.7 points avg across 5 held-out models
- Text classification: +7.7 points over SOTA with 4x fewer context tokens

## Implementation Status

### Tier 1: Execution Trace Feedback — DONE (2026-04-01)

**What**: Feed `inference_tap.log` traces from evaluation runs back to PromptForge mutation step.

**Implementation**:
- `eval_tower.py`: Added `capture_recent_traces(n_lines=50)` — reads tail of `/mnt/raid0/llm/tmp/inference_tap.log`
- `autopilot.py`: After each eval, stores `state["last_traces"]`; passes to `dispatch_action()` for prompt_mutation branch
- `autopilot.py` dispatch: Traces prepended as `## Recent Execution Traces` section in PromptForge failure_context

Per the ablation, this accounts for most of Meta-Harness's improvement (+15 pts over score-only).

### Tier 2: Code Mutation Search Space — DONE (2026-04-01)

**What**: Extend PromptForge so it can mutate Python orchestration code, not just `.md` templates.

**Implementation**:
- `prompt_forge.py`: Added `CodeMutation` dataclass, `propose_code_mutation()`, `apply_code_mutation()`, `revert_code_mutation()` methods
- `prompt_forge.py`: `_build_code_mutation_prompt()` with code-specific system prompt + safety constraints
- `prompt_forge.py`: `_validate_syntax()` via `ast.parse()` — mutations that fail syntax check are rejected
- `autopilot.py`: Added `code_mutation` action type in `dispatch_action()` with full safety gate + simplicity criterion
- `autopilot.py`: Added to controller prompt's Available Actions

**Safety boundary** (eval trust boundary):
```python
CODE_MUTATION_ALLOWLIST = [
    "src/prompt_builders/resolver.py",      # Prompt resolution logic
    "src/escalation.py",                     # Escalation policy
    "src/graph/escalation_helpers.py",       # Role cycle detection
    "src/tool_policy.py",                    # Tool access control
]
```

Files NOT on this list are immutable. Eval/scoring/safety code cannot be touched.

**Safety mechanisms**:
1. Allowlist enforcement (ValueError on unlisted files)
2. `ast.parse()` syntax validation before acceptance
3. Git commit before mutation (rollback safety net)
4. Safety gate evaluation after application
5. Simplicity criterion (reject >20% size increase for <2% quality gain)
6. Optuna epoch invalidation on accepted code mutations

### Tier 2b: Upgraded Search and Telemetry (intake-338/345)

Source: Agent Lightning (Microsoft Research, intake-338/344) + GEPA Full Program Adapter (intake-345). Agent Lightning provides trace collection infrastructure; GEPA provides a stronger search algorithm than our current LLM-guided mutation.

- [x] MH-4: GEPA search algorithm eval — ✅ **Folded into AR-3 Package D** (2026-04-12). GEPA integrated into PromptForge as `gepa` mutation type (30% of trials). AR-3 journal collects Pareto frontier contributions by mutation source (GEPA vs LLM). Comparison data resolves the key question after ~50 trials. See `scripts/autopilot/species/gepa_optimizer.py`.
- [x] MH-5: Adopt Agent Lightning trace collection pattern for autopilot telemetry — ✅ 2026-04-12. `telemetry.py` module: `TelemetryCollector` class with `record_transition()` + `record_trial()`. `TransitionRecord` dataclass with OTLP-compatible `to_otlp_span()`. JSONL export to `orchestration/autopilot_telemetry.jsonl`. Per-step decomposition: controller_reasoning → action_execution → safety_gate.

### Tier 3: Full Outer Loop Rebuild — DEFERRED

**What**: Build Meta-Harness-style filesystem of candidates + evaluation runner + agentic proposer.

**Why deferred**: The outer search loop is not open-sourced. Building from scratch requires significant infrastructure (candidate directory management, per-candidate filesystem isolation, 82 files/iteration access). Current Tier 1+2 captures the core insight (execution traces + code mutations) without the operational overhead.

**Revisit when**: AR-3 data shows diminishing returns from Tier 2 code mutations, indicating the search needs to be more systematic.

## Open Questions

- Can a 32B local model (Qwen2.5-Coder-32B) do diagnostic reasoning from traces, or does this require Opus-class? The paper only tested Opus.
- What's the right trace granularity? Current approach sends raw last-50-lines. Filtered traces (errors + slow turns + escalations only) may be better.
- For Tier 3: Docker per-candidate vs git worktree isolation?

## Dependencies

- ~~Autopilot AR-1 baseline must be working~~ DONE (2026-03-30)
- ~~EvalTower T0 must produce reliable scores~~ DONE (sentinel questions validated)
- ~~inference_tap.log must be capturing during evaluation~~ DONE (TUI already reads it)

## Operator Guide

See [docs/guides/meta-harness-operator-guide.md](/mnt/raid0/llm/epyc-orchestrator/docs/guides/meta-harness-operator-guide.md) for runtime operation, monitoring, and intervention procedures.

## Notes

Chelsea Finn + Omar Khattab (DSPy creator) co-authored. The TerminalBench-2 result is particularly relevant — they optimized an *agent scaffold*, which is exactly what our orchestrator is.

## Research Intake Update — 2026-04-04

### New Related Research
- **[intake-254] "Goose — Open Source Autonomous AI Coding Agent"** (github.com/block/goose)
  - Relevance: Rust-based autonomous coding agent with multi-model cost optimization and MCP integration
  - Key technique: Multi-model routing for performance/cost balance, MCP-based tool extensibility
  - Delta from current approach: Goose is end-to-end autonomous (builds, executes, debugs) vs our orchestrator's guided pipeline. Their MCP integration pattern is a reference for our tool surface
- **[intake-255] "Clido — Multi-Provider CLI Coding Agent"** (github.com/clido-ai/clido-cli)
  - Relevance: Profile-based multi-provider routing with per-session cost tracking and budget management
  - Key technique: Real-time cost tracking per session, declarative YAML workflows, 16 provider backends
  - Delta from current approach: Clido's per-session budget management implements the TOKEN_BUDGET concept from CC analysis (intake-249). Their profile-based provider switching maps to our routing intelligence

## Research Intake Update — 2026-04-06

### New Related Research
- **[intake-271] "Skill Issue: Harness Engineering for Coding Agents"** (humanlayer.dev)
  - Relevance: Practitioner synthesis validating that harness config, not model capability, drives coding agent performance
  - Key technique: Progressive disclosure, context firewalls (sub-agent isolation), instruction budget management, back-pressure loops
  - Reported results: TerminalBench-2 rank delta of ~28 positions from harness alone (same Opus 4.6 model)
  - Delta from current approach: Our PromptForge does mutation but lacks systematic back-pressure loops feeding specific failure signals to harness components. The instruction budget concept (14-22% token overhead) is not tracked in our eval tower.
- **[intake-272] "Evaluating AGENTS.md" (arXiv:2602.11988)** — ETH Zurich
  - Relevance: Context files REDUCE task success rates and increase inference cost by 20%+
  - Key technique: Empirical evaluation of AI-generated vs human-written agent context files on SWE-bench
  - Delta from current approach: Direct threat to PromptForge code mutations that add instructions. Our thin-map architecture may be optimal, but needs empirical validation. **Action**: add instruction token budget tracking to eval tower; consider "minimal context" ablation in PromptForge.
- **[intake-338] "Agent Lightning"** (Microsoft Research) — Zero-code agent optimization
  - Relevance: Framework-agnostic agent optimization with RL, prompt optimization, and SFT
  - Key technique: LightningRL hierarchical credit assignment for per-request reward attribution
  - Delta from current approach: Meta-Harness optimizes harness code via agentic search. Agent Lightning optimizes the underlying LLM behavior via RL. Complementary approaches — Meta-Harness changes the harness, Agent Lightning trains the model to use the harness better.
- **[intake-345] "GEPA Full Program Adapter"** (DSPy)
  - Relevance: 93% MATH (vs 67% base) by evolving entire program structure, not just prompts
  - Key technique: GEPA evolving signatures, modules, control flow with as few as 3 examples
  - Delta from current approach: Meta-Harness searches over harness code. GEPA Full Program Adapter could be the search algorithm — replacing or augmenting our current LLM-guided mutation with evolutionary Pareto-optimal search. The +26pp result suggests this is a significantly stronger optimizer.

## Research Intake Update — 2026-04-17

### New Related Research

- **[intake-394] "Evolver: GEP-Powered Self-Evolution Engine for AI Agents"** (repo: EvoMap/evolver)
  - Relevance: auditable protocol-bound evolution (Gene/Capsule/EvolutionEvent JSONL assets) as a reference design for meta-harness mutation governance.
  - Key technique: strategy-preset intent mixer (innovate/optimize/repair weights), log-signal selector-driven prompt routing, protected source files.
  - Delta: adds a packaging/governance pattern to compare against our own harness-search artifact representation; not a new search algorithm.

- **[intake-397] "Open Agents — Vercel-Labs Reference App for Background Coding Agents"** (repo: vercel-labs/open-agents)
  - Relevance: agent-control-plane-separate-from-execution-sandbox pattern as a reference for the meta-harness search runtime separation from the orchestrator it optimizes.
  - Key technique: durable workflow execution with reconnect-to-stream semantics (Vercel Workflow SDK), snapshot-based sandbox hibernate/resume, explicit contract between control plane and execution environment.
  - Delta: TypeScript/Vercel-locked stack is not adoptable as a component, but the durable-workflow-reconnect and snapshot-resume design patterns are worth mining for long-running harness search sessions.

- **[intake-399] "GenericAgent: A minimal self-evolving autonomous agent framework"** (repo: lsdefine/GenericAgent)
  - Relevance: extreme-minimalism constraint (~3K LOC, ~100-line loop, 9 atomic tools, <30K context) as a design target for the meta-harness search space upper bound.
  - Key technique: 5-tier memory taxonomy (L0 Meta Rules / L1 Insight Index / L2 Global Facts / L3 Task Skills/SOPs / L4 Session Archive); skill-crystallization from solved tasks into reusable SOPs.
  - Delta: gives a concrete reference architecture for "how small can a useful agent loop be" — useful lower-bound anchor when proposing new harness variants. No benchmarks; single-user Chinese-market desktop agent.

## Research Intake Update — 2026-04-20

### New Related Research
- **[intake-413] "Toward Ultra-Long-Horizon Agentic Science: Cognitive Accumulation for ML Engineering"** (arxiv:2601.10402)
  - Relevance: HCC architecture demonstrates that tiered knowledge distillation (execution traces → phase knowledge → cross-task wisdom) yields SOTA on autonomous ML engineering — directly validates the meta-harness memory layer design.
  - Key technique: Hierarchical Cognitive Caching with L1/L2/L3 cache analogy; cross-task wisdom consolidation; 56.44% medal rate on MLE-Bench.
  - Delta from current approach: the distillation pipeline converting raw experiment logs into structured reusable knowledge could improve AutoPilot's strategy_store and PromptForge mutation quality.

- **[intake-414] "Token Savior Recall — 97% Token Reduction MCP Server"** (repo: mibayy/token-savior)
  - Relevance: 105-tool AST-level structural codebase navigation reduces context injection by 97% — relevant to harness search space for tool-surface minimization.
  - Key technique: content-hash symbol staleness detection for automatic memory invalidation; MDL convention promotion (notes→conventions auto-upgrade); Bayesian validity tracking.
  - Delta from current approach: the MDL distillation for convention promotion and staleness invalidation patterns are novel harness engineering primitives not in current search space.

- **[intake-418] "Externalization in LLM Agents: A Unified Review of Memory, Skills, Protocols and Harness Engineering"** (arxiv:2604.08224)
  - Relevance: positions the harness layer as the primary locus of agent capability improvement (weights→context→harness era progression) — directly validates the meta-harness optimization thesis.
  - Key technique: three-dimensional externalization taxonomy (memory/skills/protocols) + harness layer orchestration; self-evolving harness search.
  - Delta from current approach: the unified taxonomy could audit completeness of EPYC's agent infrastructure; the "harness era" framing reinforces the meta-harness investment direction.

- **[intake-425] "Memory Transfer Learning: How Memories are Transferred Across Domains in Coding Agents"** (arxiv:2604.14004)
  - Relevance: Empirically validates that abstract "Insight" representations transfer better than concrete traces across coding domains (+3.7% avg). Simple embedding retrieval outperforms LLM reranking — directly applicable to harness memory layer design decisions.
  - Key technique: Four-tier memory abstraction (Trajectory → Workflow → Summary → Insight); negative transfer taxonomy for safety gates.
  - Delta from current approach: The Insight format (title + description + generalizable content, no task-specific details) is a concrete template for harness memory entries. The negative transfer taxonomy (domain-mismatched anchoring, false validation confidence, misapplied best-practice transfer) can inform PromptForge mutation guardrails.

- **[intake-426] "Dive into Claude Code: The Design Space of Today's and Future AI Agent Systems"** (arxiv:2604.14228)
  - Relevance: Independent confirmation that 98.4% of agent complexity lives in operational infrastructure — strongest external validation of the meta-harness optimization thesis. Identifies six open design directions including the observability-evaluation gap and harness boundary evolution.
  - Key technique: 13 design principles traced from 5 human values to implementation choices; five-layer compaction pipeline; comparative analysis (Claude Code vs OpenClaw) showing deployment context drives architectural choices.
  - Delta from current approach: The observability-evaluation gap (agents produce outputs but evaluating them is hard) and the finding that 27% of Claude Code tasks represent novel work are new data points for justifying meta-harness investment. The comparative framework (CLI agent vs gateway agent) is relevant to our Hermes integration decisions.

## Research Intake Update — 2026-04-22

### New Related Research

- **[intake-438] "Mind DeepResearch Technical Report"** (arxiv:2604.14518, Li Auto, production deployment)
  - Relevance: Multi-agent framework with role specialization via RL. Production deployment demonstrates meta-harness viability at 30B scale. Complements meta-harness thesis that harness-layer investment dominates capability-layer investment.
  - Key technique: Four-stage training (SFT → Search-RL → Report-RL → preference alignment) with multi-dimensional rubric evaluation.
  - Reported results: SOTA 51.8 on MindDR Bench; BrowseComp-ZH 45.7%, WideSearch 46.5%, xbench-DS 75.0%.
  - Delta: Our meta-harness work focuses on orchestration + context + routing. MindDR extends to RL agent-role specialization — an axis we've deferred (GPU-gated). Useful reference for a future Tier 3 direction if GPU becomes available.

- **[intake-444] "Agent-World: Scaling Real-World Environment Synthesis for Evolving General Agent Intelligence"** (arxiv:2604.18292)
  - Relevance: Self-evolving agent training with autonomous environment-task discovery. Addresses the meta-harness question: how do we scale past fixed benchmarks without manually curating tasks?
  - Key technique: Agentic Environment-Task Discovery + Continuous Self-Evolving Agent Training + MCP integration for real-world services.
  - Reported results: Agent-World-8B/14B beat proprietary baselines across 23 benchmarks.
  - Delta: Environment synthesis as a scaling mechanism is orthogonal to our meta-harness Tiers 1-2 (orchestration) and the autopilot's AR-3 mutation loop. Consider as a Tier 2b or Tier 3 direction where the "harness" synthesizes its own evaluation environments.

## Deep-Dive Integration — 2026-04-22

### Tier 3 — Concrete Outer-Loop Rebuild Recipes (now split into 2 dedicated handoffs)

The long-deferred Tier 3 outer-loop rebuild now has two concrete forward paths, each with its own dedicated handoff:

**1. [`agent-world-env-synthesis.md`](agent-world-env-synthesis.md) — Environment synthesis arena (DD6, intake-444)**

- Phase 1 training-free and CPU-feasible today: LLM-orchestrated exploration of databases + MCP tool ecosystem → synthesized verifiable tasks with controllable difficulty → fed into AR-3 as additional benchmark input.
- Phase 2 multi-env GRPO training: GPU-gated (post-DGX-Spark). Trains Qwen3-8B → Agent-World-8B-EPYC.
- Entry point: AW-1 `env_synth/` module scaffold.

**2. [`minddr-deep-research-mode.md`](minddr-deep-research-mode.md) — Three-agent RL specialization (DD7, intake-438)**

- Phase 1 prompt-level three-agent pipeline (Planning/DeepSearch/Report): zero-infra, falsifiable under eval tower, ~3w code.
- Phase 2 four-stage training recipe: SFT → Search-RL (GSPO/GRPO) → Report-RL (DAPO) → preference alignment (DPO + Self-SFT). GPU-gated.
- Entry point: MD-1 `deep_research_mode` feature flag.

Both Phase-1 paths are training-free and implementable today. They operate on different axes: Agent-World expands the benchmark surface (bottom-up); MindDR refactors the routing pipeline (top-down). A fully-rebuilt Tier 3 eventually combines both — synthesized tasks (Agent-World Phase 1) train the three-agent pipeline (MindDR Phase 2) when GPU is available.

### NIB2-41 — MDL distillation + staleness-detection mutation primitives (intake-414 Token Savior)

Candidate new StructuralLab mutation types. 2d design + 1d integration into `program.md` search space. Tracked in `non-inference-backlog.md` NIB2-41. No dedicated handoff needed; this is a local extension to the existing mutation-type registry.

### Cross-references

- `routing-and-optimization-index.md` P17 (Agent-World pointer) + P18 (MindDR pointer)
- `agent-world-env-synthesis.md` + `minddr-deep-research-mode.md`
- `/workspace/research/deep-dives/agent-world-environment-synthesis.md`
- `/workspace/research/deep-dives/minddr-multi-agent-rl-specialization.md`
