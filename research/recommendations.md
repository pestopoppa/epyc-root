# Literature Recommendations — 2026-07-08

Compiled from deep-dive intake of agent benchmarking, evaluation, and autonomous research literature (intake-779 through intake-797).

> **Citation audit 2026-08-10.** Every `source:` line below was checked against the entry it names. Eight ids were wrong and are corrected; five sources were cited but had never been ingested and now exist as intake-1068..1072; two headline claims (rec-001, rec-002) were not supported by their own sources and are rewritten. The range above is a historical batch label — intake-784 and intake-797 were merged away on 2026-08-10, see [`intake_merge_map.md`](intake_merge_map.md).

## Recommendations

- id: rec-001
  title: "Harness and context optimization: the non-weight inputs to an agent are automatically optimizable"
  # 2026-08-10 citation audit: intake-784 was merged into intake-244 (same arXiv id).
  # Self-Harness and ACE were never ingested and had been given neighbouring entries' ids.
  source: Meta-Harness (intake-244), Self-Harness (intake-1070), ACE (intake-1071)
  category: benchmark_methodology
  priority: high
  description: >
    CORRECTED 2026-08-10 after ingesting the two sources this row cited but never held.
    The original claim was "LLM-as-judge benchmark design is itself optimizable". That is NOT supported by
    any of the three papers. Self-Harness (intake-1070) never mentions LLM-as-judge and validates against
    deterministic task verifiers; ACE (intake-1071) optimizes the CONTEXT fed to an agent; Meta-Harness
    (intake-244) searches over harness CODE. In all three the benchmark is a fixed evaluation target, not the
    object of optimization.
    What they do converge on, and what this row now claims: the non-weight inputs to an agent — harness code,
    system prompt, memory, context — are automatically optimizable against execution feedback, and the useful
    configuration is model-specific.
  action: "Review meta-harness-optimization.md handoff — the transferable pattern is automatic harness/context
    optimization gated on regression testing, NOT automated task generation, which none of these papers do." 
  status: open
  created: '2026-07-08'

- id: rec-002
  title: "Metacognitive self-modification (ADAS -> DGM -> Hyperagents lineage)"
  # 2026-08-10 citation audit: DGM repointed (786 was STOP); the other two name papers that
  # were never ingested and had been given neighbouring entries' ids.
  source: DGM (intake-772), Hyperagents (intake-1069), ADAS (intake-1068)
  category: benchmark_methodology
  priority: high
  description: >
    CORRECTED 2026-08-10 after ingesting the two sources this row cited but never held.
    The lineage is real: ADAS (intake-1068) -> DGM (intake-772) -> Hyperagents (intake-1069), and Hyperagents
    names DGM as the system it extends. Two corrections. (1) The author through-line is Jeff Clune alone;
    Hu and Lu drop out at Hyperagents and Zhang is absent from ADAS, so "Hu/Lu/Clune/Zhang lineage" overstates
    it. (2) NONE of the three generates tasks. All are evaluated on given benchmarks, and Hyperagents lists
    "a fixed task and evaluation distribution" among its own limitations. The trajectory is toward
    domain-general METACOGNITIVE SELF-MODIFICATION — ADAS automates agent design, DGM modifies its own code,
    Hyperagents makes the self-modification procedure itself editable — not toward autonomous task generation.
  action: "Do NOT scope task generation from this lineage; the capability is not there. If self-modification
    of our own harness is wanted, Hyperagents (intake-1069) is the closest prior art. See the correction in
    research/f1-dgm-scoping-2026-07.md, which was scoped on the task-generation premise." 
  status: open
  created: '2026-07-08'

- id: rec-003
  title: "Agent-as-judge calibration and multi-agent consensus"
  source: MCE (intake-787), AFlow (intake-788), STOP (intake-786)
  category: evaluation
  priority: medium
  description: >
    MCE and AFlow address LLM-as-judge reliability through multi-agent consensus and structured evaluation
    flows. STOP provides a stopping-criterion framework. These are relevant to our autopilot critic and
    early-failure-prediction work where we need reliable judgment without human annotation.
  action: "Cross-reference with early-failure-prediction.md and eval-tower-verification.md. Assess MCE consensus patterns for our critic pipeline."
  status: open
  created: '2026-07-08'

- id: rec-004
  title: "Self-improvement agent architectures (SIA / ShinkaEvolve)"
  source: SIA (intake-789), ShinkaEvolve (intake-779), SkillRL (intake-092)
  category: agent_architecture
  priority: medium
  description: >
    SIA and ShinkaEvolve explore recursive self-improvement loops for agents. Combined with SkillRL's
    recursive skill-augmented RL, these suggest a pathway for our autopilot to move beyond trial-and-error
    optimization toward structured self-improvement with skill accumulation.
  action: "Review autopilot-continuous-optimization.md for self-improvement integration points. Caution: SkillsBench v3 (intake-096) shows self-generated skills are net-negative (-1.3pp) — any self-improvement must include validation gates."
  status: open
  created: '2026-07-08'

- id: rec-005
  title: "RE-Bench (METR) — agentic ML-engineering benchmark, NOT a reasoning-quality eval"
  source: RE-Bench (intake-1072)
  category: benchmark_methodology
  priority: low
  description: >
    CORRECTED 2026-07-22 (parallel research agent finding, verified): RE-Bench is METR's AGENTIC
    ML-ENGINEERING evaluation - open-ended ML research/engineering tasks (kernel optimization,
    scaling-law experiments, fine-tuning) scored against human expert baselines over multi-hour
    agent runs. It is NOT a reasoning-capability/CoT eval and does not fit the reasoning-compression
    validation role the original entry assumed. Potential relevance is instead to long-horizon
    agentic harness evaluation (harness-selection track), at much higher per-run cost.
  action: "If pursued at all, evaluate under the harness-selection track as an agentic-capability
    reference, not under reasoning-compression. No CoT-study cross-reference."
  status: open
  created: '2026-07-08'

- id: rec-006
  title: "Paper-level benchmarking (PaperBench) — methodology transfer"
  source: PaperBench (intake-794)
  category: benchmark_methodology
  priority: low
  description: >
    PaperBench benchmarks model ability to understand and reproduce research papers. Methodology may be
    transferable to our autonomous research pipeline for validating that our agent-generated research
    artifacts are faithful to source material.
  action: "Monitor. Potentially relevant to minddr-deep-research-mode.md if we need source-fidelity validation."
  status: open
  created: '2026-07-08'

- id: rec-007
  title: "Kernel-level benchmarking (KernelBench) for CPU inference"
  source: KernelBench (intake-664)
  category: hardware_optimization
  priority: high
  description: >
    KernelBench provides fine-grained kernel-level benchmarking. Directly relevant to our MI210 speed
    campaign, iqk AVX-512 GEMM kernels, and v7 candidate validation. Could serve as a regression guard
    for experimental kernel promotion.
  action: "Evaluate KernelBench for integration into our experimental kernel validation pipeline (step 3 of the four-step workflow). Cross-reference with mi210-speed-campaign-summary.md."
  status: open
  created: '2026-07-08'

- id: rec-008
  title: "Autonomous research agent orchestration (EvoScientist pattern)"
  source: EvoScientist (intake-108), AI Scientist Nature (intake-780)
  category: agent_architecture
  priority: medium
  description: >
    EvoScientist's three-agent architecture (Researcher, Engineer, Evolution Manager) with persistent
    memory modules mirrors our tri-role coordinator architecture. The Nature-published AI Scientist
    provides validation that fully autonomous research pipelines are viable.
  action: "Cross-reference with tri-role-coordinator-architecture.md and user-facing-harness-index.md. Assess EvoScientist memory module patterns for our persistent memory work."
  status: open
  created: '2026-07-08'

- id: rec-009
  title: "J-space interpretability for routing and model understanding"
  source: Anthropic J-space (intake-782)
  category: model_interpretability
  priority: medium
  description: >
    Anthropic's J-space work on geometric interpretability of model representations could inform our
    routing intelligence — understanding the geometric structure of model capabilities may enable better
    routing decisions than current embedding-based approaches.
  action: "Review routing-intelligence.md for J-space integration points. May enable learned-head routing (outer-coordinator-learned-head.md) with geometric priors."
  status: open
  created: '2026-07-08'

- id: rec-010
  title: "fast-rlm re-review: RLM harness patterns"
  source: fast-rlm (intake-783)
  category: agent_architecture
  priority: medium
  description: >
    RecursiveLM patterns for structured agent orchestration, MCP integration, and session management.
    Tool inheritance boundaries and env injection patterns are applicable to our harness design.
  action: "Harvest ACP integration pattern, MCP client design, session management, and tool inheritance boundaries for EPYC orchestration."
  status: open
  created: '2026-07-08'

## Key Patterns Observed

1. **Self-generation caution**: SkillsBench v3 shows self-generated skills are net-negative (-1.3pp avg). Any autonomous benchmark/task/skill generation MUST include validation gates against a curated baseline.
2. **Author lineages matter**: ADAS → DGM → Hyperagents (Hu/Lu/Clune/Zhang), Meta-Harness → ACE (Qizheng Zhang), ShinkaEvolve → DGM (Robert Lange). Tracking author lineages reveals methodological evolution.
3. **Benchmark fatigue**: The field is producing many specialized benchmarks (RE-Bench, PaperBench, KernelBench, SkillsBench). The trend is toward automated/adaptive benchmarks rather than static suites.
4. **Multi-agent evaluation**: Consensus across multiple evaluators (MCE, AFlow) is emerging as the standard for reliable LLM-as-judge systems.

## Cross-References
- Handoffs: meta-harness-optimization.md, eval-tower-verification.md, autopilot-continuous-optimization.md, reasoning-compression.md, mi210-speed-campaign-summary.md, routing-intelligence.md, tri-role-coordinator-architecture.md
- Intake entries: intake-779 through intake-797 (batch label; 784 and 797 since merged — see `intake_merge_map.md`)
- Prior work: SkillsBench v3 (intake-096), SkillRL (intake-092), EvoScientist (intake-108)
