# MindDR (Mind DeepResearch): Multi-Agent RL Specialization at 30B Scale — Deep Dive

- **Source**: https://arxiv.org/abs/2604.14518 ("Mind DeepResearch Technical Report")
- **HTML**: https://arxiv.org/html/2604.14518
- **Authors**: MindDR Team, Li Auto Inc.
- **Submission date**: 2026-04-16
- **Intake ID**: intake-438
- **Related intake**: intake-412 (DeepPlanning), intake-444 (Agent-World)
- **Artifacts**: No open-source code release located as of 2026-04-20. Paper only. The system is described as "deployed as an online product in Li Auto" — the Li Auto in-car intelligent assistant, a commercial-internal deployment.
- **Intake verdict delta**: `worth_investigating` upgrades to **`adopt_patterns (prompt-only) + revisit (post-DGX)`**. The full four-stage RL recipe requires GPU and is aligned with meta-harness Tier 3 (GPU-deferred). The three-agent role specialization and multi-dimensional rubric evaluation are adoptable today without RL.

---

## 1. Abstract (≤150 words)

MindDR is Li Auto's three-agent deep-research framework (Planning, DeepSearch, Report) trained on Qwen3-32B (dense) and Qwen3-30B-A3B (MoE) via a four-stage pipeline — SFT cold-start → Search-RL → Report-RL → preference alignment (DPO + Self-SFT) — achieving SOTA on Li Auto's internal MindDR Bench (51.8) while ranking competitively on BrowseComp-ZH (45.7%), BrowseComp (42.8%), WideSearch (46.5%), xbench-DS (75.0%), and DeepResearch Bench (52.5). The paper's core claim is that role-specialized RL at 30B scale rivals larger generalist agents. For EPYC the paper is doubly interesting: (a) the three-agent decomposition (plan / search / synthesize) is adoptable as a prompt-level pattern on our existing Tier A/B stack without RL, and (b) the full four-stage recipe becomes the concrete target recipe for Tier B specialist training when DGX Spark arrives. The multi-dimensional rubric evaluation (four pipeline stages × fine-grained metrics) is a directly transferable eval-tower upgrade.

---

## 2. MindDR Architecture

### 2a. Three-Agent Collaborative Architecture

MindDR factors deep research into three specialized roles that run as a pipeline with shared memory (Extended Chain-of-Thought, a.k.a. XoT, plus a Tool Memory of every tool-call/observation pair).

**Planning Agent**:
- Receives the raw user query.
- Performs intent analysis and task decomposition into a *structured subtask specification*.
- Emits parallel subtasks that are dispatched to independent DeepSearch Agent instances.
- Output is a typed plan (subtask list with per-subtask goals, constraints, and success conditions), not free-form text.

**DeepSearch Agent (parallel instances)**:
- ReAct-style loop (Thought → Action → Observation).
- Iteratively calls search tools across (i) Li Auto's proprietary tens-of-billions-scale internal knowledge base, (ii) external web (routed across Sogou, Bing, Quark), (iii) academic literature, (iv) web crawling / full-text extraction.
- Each instance decides when it has gathered enough evidence and emits a sub-report with citations.
- Tool calls are routed through a unified entry layer with traffic control, exception retry, and result caching — tool error rate is kept below 0.1%.

**Report Agent**:
- Receives the full task specification plus every DeepSearch sub-report.
- Generates a hierarchical outline first, then performs global aggregation into a coherent, comprehensive, well-structured final report with citations.
- Explicitly separates outline generation from content generation — outline quality is scored as its own pipeline stage.

**Memory**: Extended Chain-of-Thought (XoT) propagates reasoning state across agent boundaries; Tool Memory preserves the full provenance of every tool call. This lets the Report Agent cite the exact retrieval that supports each claim rather than paraphrasing without grounding.

**Why the three-agent split is non-trivial**: a single monolithic agent doing all three in one ReAct loop suffers from what the paper implicitly treats as three failure modes: (a) *premature commitment* — the agent starts searching before fully decomposing the task, produces shallow sub-answers, and cannot recover; (b) *retrieval-synthesis interleaving* — the agent synthesizes while still retrieving, leading to citations that were never actually grounded; (c) *outline drift* — without a separate outline phase, the final report's structure emerges from the order retrieval happened to arrive, not from the logical structure of the question. Factoring plan → search → synthesize forces each failure mode to be addressed by a different agent with a different reward signal during RL, which is the structural reason agent-specialized training outperforms monolithic RL at the same total compute.

### 2b. Four-Stage Training Pipeline

This is the paper's central technical contribution. Each stage is *agent-specialized* — data and reward functions target one agent's role.

**Stage 1 — SFT Cold-Start** (~15K trajectories):
- 60% knowledge-graph trajectories (multi-hop reasoning, 1–5 hops).
- 35% real-world scenarios (automotive, technology, transportation — Li Auto's domain priors).
- 5% human-annotated edge cases.
- Loss: standard autoregressive NLL on (thought, action) pairs conditional on history.
- **Curriculum**: progressive context lengthening 8K → 32K–64K → 128K. Format correctness at 128K improves from 72% → 94% under curriculum.
- Stop criterion: format-error rate <2.5% at 64K and 128K; policy entropy ≥90% of mid-training value (prevents collapse).

**Stage 2 — Search-RL** (~35K synthesized queries with entity annotations and difficulty labels):
- Optimizer: GSPO (Group Sequence Policy Optimization) for MoE; GRPO for dense. (The choice matters: MoE routing makes vanilla GRPO unstable — GSPO is required to prevent collapse in Qwen3-30B-A3B.)
- Composite reward with four components:
  1. **Tool Invocation**: +0.1 success, −0.2 for consecutive failures, −0.1 for isolated failure.
  2. **Format**: +0.1 correct, −0.2 errors.
  3. **Process (PRM)**: fraction of ground-truth entities observed over the trajectory (string-matched).
  4. **Outcome (ORM)**: binary LLM-as-Judge on the final answer.
- **Dynamic scheduling**: coefficients progress from (λ_tool, λ_format, λ_PRM, λ_ORM) = (0.6, 0.3, 0.1, 0.0) toward (0, 0, 0.3, 0.7). Early training rewards *using tools correctly*; late training rewards *getting the right answer*.

**Stage 3 — Report-RL**:
- Optimizer: DAPO (asymmetric clipping, preferred for long-form) on dense; GSPO on MoE.
- **RACE Rubrics reward** with four dimensions (each synthesized per-query by a strong LLM): Comprehensiveness, Insight, Instruction Following, Readability.
- **Auxiliary rewards**:
  - Citation reward: −1.0 if citations <0.7× reference count; +0.1 for adequate + grounded; −0.1 for invalid grounding.
  - Format reward: penalizes missing final-answer tags, Markdown errors, citation-format errors. Range [−3, 0].
- **Composite**: R_Report = R_RACE + λ_c·R_cite + λ_f·R_format.
- **Data mix**: long-form (query + retrieval trace + outline + RACE rubric + reference report) blended with short-form (query + rubric + synthesized reference report without retrieval). Ablation Table 5 shows mixing short-form lifts RACE 48.82 → 50.60 with the largest gains on Comprehensiveness and Insight.

**Stage 4 — Preference Alignment**:
- **DPO** targets structured issues where RL has weak signal — 1.8K temporal-expression and 2.8K table-repair pairs. Reduces table-error rate 2.70% → 1.22% and temporal-error 6.2% → 2.0%.
- **Self-SFT** on 4.3K high-quality self-sampled reports — improves stylistic consistency (expression/logic consistency 1.8% → 0.3%).

### 2c. Multi-Dimensional Rubric Evaluation

The paper argues RACE alone compresses too much signal into a single number and that real deep-research quality decomposes along the *pipeline stages* themselves. MindDR evaluates across four stages with fine-grained metrics per stage:

| Pipeline Stage | Metric Family | Individual Items |
|----------------|---------------|------------------|
| **Reasoning Trajectory** | Thinking Efficiency | Reflection-turn count; Search-query repetition rate |
| **Tool Call** | Correctness | Tool-usage proportions; Tool-failure rate |
| **Outline Generation** | Outline Logic | Title-miss rate; Incorrect-hierarchy count |
| **Report Generation** | Content Logic | Tense-error rate; Valid-format-table rate |

On top, the **RACE Rubrics** themselves (Comprehensiveness, Readability, Insight, Instruction Following) are scored via 3-way LLM-as-Judge with majority-vote aggregation and rationale capture.

This is structurally the same move DeepPlanning made (dimension-level + composite + case-level — see `/workspace/research/deep-dives/deepplanning-agent-benchmark.md`) but applied to open-ended generation rather than constraint-satisfiable planning.

### 2d. Scale

- **MindDR-v1.5-32B**: Qwen3-32B dense backbone, trained end-to-end through all four stages.
- **MindDR-v1.5-30B-A3B**: Qwen3-30B-A3B MoE backbone (3B active of 30B total). Matches or exceeds the 32B dense variant on accuracy while being cheaper at inference — this is the variant used in their "Accurate & Efficient" efficiency-accuracy quadrant analysis.

Both sit at ~30B-parameter scale yet match or beat much larger closed agents on several benchmarks — the paper's headline claim.

---

## 3. Benchmarks

Headline numbers (paper Table 1-3 region):

| Benchmark | MindDR (30B-A3B) | Competitive Open/Closed SOTA Context |
|-----------|------------------:|--------------------------------------|
| BrowseComp-ZH | **45.7%** | Strong on Chinese web navigation; beats comparable 30–70B open agents |
| BrowseComp | **42.8%** | English web navigation; competitive vs commercial agents |
| WideSearch | **46.5%** | Breadth-oriented search benchmark |
| xbench-DS | **75.0%** | Deep-search capability benchmark |
| DeepResearch Bench | **52.5** | Public deep-research leaderboard |
| **MindDR Bench** (internal) | **51.8 (SOTA)** | 500 curated Chinese queries from Li Auto assistant logs |

**MindDR Bench construction**: 500 real user queries from Li Auto's in-car intelligent assistant interaction logs, double-filtered (LLM prescreen for reasoning depth + expert review). Covers 16 domains weighted toward automotive, travel, technology, and finance. The paper positions it as *the* realistic-distribution deep-research benchmark (vs. the often-synthetic public benchmarks).

**Ablation highlights**:
- Table 4: DAPO/GSPO substantially outperform GRPO on format metrics (GSPO 99% tag-format vs GRPO 91%) while maintaining BrowseComp-ZH 45.7% vs GRPO's 29.1%. Optimizer choice is not cosmetic — it is ~15pp.
- Table 5: Short-form + long-form data mix improves RACE 48.82 → 50.60.
- Table 6: DPO + Self-SFT close the residual structured-error gaps (tables, tense, expression consistency).
- Figure 7: Stage-wise attribution — Search-RL is the largest accuracy lever across benchmarks; Report-RL introduces minimal regressions on DeepSearch performance (i.e., the stages are reasonably orthogonal).

**Efficiency**: On the "Accurate & Efficient" quadrant, MindDR-30B-A3B reaches the highest BrowseComp-ZH with the lowest average context tokens and tool-call count among top performers. This is genuinely important — frontier closed agents reach similar accuracy but with 5–10× the tool-call volume.

**Reading the numbers against competitors**: the comparable open baselines at similar scale (30–70B open research agents) land in the 30–40% range on BrowseComp-ZH; MindDR at 45.7% is ~5–10pp over the best comparable-scale open agent. Frontier closed agents (GPT-5-class deep-research modes) reach higher absolute numbers but (a) at 10×+ scale, (b) with substantially more tool calls per query, and (c) without the efficiency analysis the paper makes central. The paper's framing — "SOTA per-FLOP" rather than "SOTA absolute" — is the honest reading. For a CPU-constrained deployment like EPYC, per-FLOP SOTA is the relevant metric, not absolute SOTA.

---

## 4. EPYC Parallel Architecture

The architectural comparison is striking: EPYC already has **tier-based role specialization** but uses *routing* rather than *RL-trained specialization* to get per-role capability.

| Axis | MindDR | EPYC |
|------|--------|------|
| Scale per role | ~30B (all three agents share one trained backbone) | Frontdoor 35B, Coder 32B, Architect 122B or 480B, Worker cheap tier |
| Specialization mechanism | **RL-trained** — four-stage agent-specialized pipeline | **Prompt + routing** — same family of base models, differentiated by system prompt, tool policy, and routing heuristics |
| Roles | Planning / DeepSearch / Report | Frontdoor / Architect (general + coding split) / Coder / Worker |
| Synthesis/report role | Dedicated Report Agent with outline-then-content separation | No dedicated synthesis role — final answer produced by whoever handled the request |
| Coordination | Sequential pipeline with parallel DeepSearch fan-out | Role escalation ladder (worker → coder → architect) + cheap-first acceptance |
| Routing | Implicit (architecture is fixed; plan → search → report) | Explicit — MemRL Q-value weighted voting, MLP+GAT classifier, factual-risk scorer, 9 routing subsystems |
| Training | SFT + Search-RL + Report-RL + preference alignment (requires GPU) | Base models used as-is; optimization via PromptForge + GEPA + meta-harness code mutations (CPU-compatible) |
| Memory | XoT + Tool Memory (built into trained agents) | 5-layer context pipeline (hard preview, stale clearing, session log, compaction/virtual memory, solution file persistence) |
| Evaluation | RACE rubrics + module-level metrics (LLM-as-Judge, 3-way majority vote) | Eval tower: quality/speed/cost/reliability scalars |

**The key structural difference**: EPYC's Tier A/B/C is organized by *capability ceiling* (how big a model you unlock based on difficulty). MindDR's three agents are organized by *role within the research pipeline* (what stage of the task you are at). The two decompositions are orthogonal — you could in principle have both (Tier A Planning, Tier B Search, Tier C Report with some size-scaling within each).

A closer analog: EPYC's `architect_general` vs `architect_coding` split is already a *role-based* specialization at the same Tier B size. MindDR's Planning/DeepSearch/Report split asks whether role specialization should be broader than "general vs coding" — specifically whether a **synthesis/Report role** deserves its own slot.

---

## 5. Amend / Expand / Confirm

### Confirm

- **Multi-agent role specialization delivers measurable value at ~30B scale.** Prior to this paper, the multi-agent benefit was often attributed to "ensembling bigger models." MindDR's ablation (Figure 7) shows role-specialized RL on a single 30B backbone produces agent-style gains without needing frontier scale. This is strong evidence for the EPYC thesis that *harness design + role factoring* beats raw model scaling for CPU-constrained deployments.
- **Production deployment at Li Auto confirms the architecture survives real traffic.** The 500-query MindDR Bench is drawn from real user logs — this is not a synthetic academic benchmark. The deployment is commercial (in-car assistant), not a research demo.
- **Multi-dimensional / pipeline-stage evaluation beats single-score RACE**, just as DeepPlanning showed dimension/composite/case-level beats single RACE-like metrics on planning. Convergent evidence from two independent teams that **open-ended agent quality decomposes into multiple largely-independent axes** and measuring them separately catches failure modes single-score aggregation hides.

### Amend

- **Re-think the `architect_general` vs `architect_coding` split.** We currently factor architect by *domain* (general vs code). MindDR factors by *pipeline stage* (plan vs search vs synthesize). These are orthogonal axes. Candidate: either (a) a third architect persona — `architect_synthesis` or `architect_report` — specialized for cross-source synthesis and structured reporting, or (b) reframe the entire architect tier as a pipeline (architect_plan → architect_search → architect_report) where one request passes through all three in sequence. The latter is more disruptive and risks amplifying latency; the former is a drop-in.
- **We may be missing a dedicated Report/synthesis role.** Our frontdoor handles initial response and our architect handles deep reasoning, but *synthesis of multiple tool outputs into a final structured answer* currently falls to whoever ran the query. MindDR's Report Agent + outline-first methodology + citation-grounding reward suggests this is a distinct skill worth a dedicated prompt/role.
- **Routing is not the only way to specialize.** Our current assumption is that routing intelligence + a single base model per tier is sufficient. MindDR's results show that *RL-specializing* the same base for different pipeline stages produces measurable lift. When DGX Spark arrives this becomes a viable alternative for Tier B.

### Expand

- **The four-stage recipe (SFT → Search-RL → Report-RL → preference) is concrete and transferable.** When DGX Spark lands, the Tier B specialist training question ceases to be open. This paper provides:
  - Data composition (60/35/5 for SFT cold-start).
  - Curriculum (8K → 32K–64K → 128K context lengthening).
  - Optimizer selection (GSPO for MoE, GRPO/DAPO for dense — not interchangeable).
  - Reward scheduling (dynamic coefficient progression for Search-RL).
  - Short-form + long-form data mix for Report-RL.
  - Preference-alignment targets for residual structured errors.
- **Per-stage ablation data** — Figure 7 of the paper attributes gains to each stage. This allows prioritized adoption: if we can only afford one RL stage, Search-RL is highest-leverage for agent-benchmark accuracy; Report-RL adds synthesis quality without harming search.
- **Dynamic reward scheduling is the non-obvious ingredient.** Most published RL agent work uses fixed reward coefficients. MindDR's three-phase scheduling (tool use → process → outcome) is a template we should keep on the shelf for any future agent RL, not just deep research.

---

## 6. RL Training Requirements — GPU Dependency

The four-stage pipeline is unambiguously a GPU project:

- **Stage 1 SFT**: 15K trajectories at 128K context requires substantial GPU memory and is infeasible on CPU at any reasonable throughput.
- **Stage 2 Search-RL**: Online RL with tool calls inside the rollout loop. Each rollout requires the full agent to execute (including web tools), then credit assignment via GSPO/GRPO. CPU rollouts are ~50× slower than GPU and the rollout-to-training ratio dominates wall time.
- **Stage 3 Report-RL**: DAPO with long-form generation (rollouts of thousands of tokens) + LLM-as-Judge rubric scoring per rollout. CPU-infeasible at dataset scale.
- **Stage 4 DPO / Self-SFT**: Offline preference learning, smallest GPU requirement, but still GPU.

This fits cleanly with the existing meta-harness Tier 3 deferral (`/workspace/handoffs/active/meta-harness-optimization.md`, "Tier 3: Full Outer Loop Rebuild — DEFERRED"). Tier 3 was deferred for similar operational reasons (infrastructure overhead, full outer loop not open-sourced). MindDR extends that list with a *specific recipe* we would run on DGX Spark once acquired.

Relative priorities when DGX Spark arrives:
1. AReaL-style async RL infrastructure (intake tracked, deep-dive exists at `/workspace/research/deep-dives/areal-async-rl-system.md`) — provides the runner.
2. MindDR four-stage recipe — provides the method.
3. Tier B specialist targets — provides the models to train (architect_general, architect_coding, and potentially architect_report if we adopt the Amend above).

**Budget reality check**: Stage 2 and Stage 3 RL at 30B-MoE scale on Qwen3-30B-A3B is non-trivial even with a single DGX Spark. MindDR does not publish exact compute numbers but the ~35K rollouts × ~15K trajectories at 128K context + LLM-as-Judge reward computation implies weeks of DGX time per stage. Plan accordingly.

---

## 7. Prompt-Only Adoption — Phase 1 Today

Without any RL training, the three-agent pattern is adoptable as a prompt-level orchestration on the existing stack. Concrete mappings:

### 7a. "Planning Agent" → prompt-specialize architect_general

- **Role prompt**: task-decomposition emphasis. Input: raw query. Output: structured subtask list (typed, JSON-ish) with per-subtask goals and success conditions.
- **Tool policy**: no search tools in this step. Reasoning-only.
- **Model**: architect_general (Qwen3-122B or GLM-4.6-Air-Coder) with `think` mode on.
- **Stop criterion**: must emit a parseable plan before dispatch.

### 7b. "DeepSearch Agent" → prompt-specialize frontdoor (or worker_explore at cheap tier)

- **Role prompt**: ReAct-style search emphasis. One subtask in; one sub-report with citations out.
- **Tool policy**: search tools enabled; synthesis tools disabled.
- **Parallelism**: if the plan has N subtasks, dispatch N independent DeepSearch calls. This is a natural fit for our existing cheap-first parallel workers.
- **Model**: frontdoor 35B for hard subtasks, worker tier for easy ones (already routed by difficulty).

### 7c. "Report Agent" → new cheap-first synthesis stage using worker_explore

- **Role prompt**: outline-first methodology (generate hierarchical outline, then fill content; cite every claim).
- **Tool policy**: no tools. Pure synthesis.
- **Model**: worker_explore (cheap tier) for routine synthesis; escalate to architect on failure. This mirrors MindDR's structural separation of outline-generation from content-generation as distinct pipeline stages.

### 7d. What we get, what we miss

**Get**: Structural benefits of the pipeline — explicit planning, parallel search, dedicated synthesis. Catches the same class of failures MindDR's architecture catches (tangled reasoning, missing citations, incoherent final structure).

**Miss**: The RL-trained Search-RL precision (tool-use correctness, entity-coverage process reward) and Report-RL rubric adherence (RACE reward). These show up as ~10–15pp of the gap between prompt-only and trained MindDR on the hardest benchmarks (BrowseComp-ZH, MindDR Bench).

**Feasibility**: High. The existing pydantic_graph has the infrastructure (typed state, role escalation, tool-policy gating) to add a pipeline like this as a new orchestration mode alongside the existing direct-mode and escalation-mode paths.

**Concrete prompt sketches** (to illustrate; not final copy):

*Planning Agent* — system prompt core:
> You are the Planning Agent. Your job is to decompose a research query into a structured list of independent subtasks that can be executed in parallel by downstream search agents. Each subtask must have: a single narrow goal, a success condition, and a priority. Do not answer the query yourself. Output JSON only.

*DeepSearch Agent* — system prompt core:
> You are a DeepSearch Agent. You are given exactly one subtask. Iteratively search, evaluate evidence, and produce a concise sub-report answering only this subtask. Cite every claim with source URLs. Stop when evidence is sufficient — do not over-search.

*Report Agent* — system prompt core:
> You are the Report Agent. You receive the original user query and a set of sub-reports from DeepSearch agents. First produce a hierarchical outline that logically structures the answer. Then fill each outline node with synthesized content. Every non-trivial claim must cite one of the sub-reports. Do not introduce facts that are not present in the sub-reports.

**Phase 1 proposal**: Feature-flagged "deep research" pipeline mode that (a) detects "research-like" queries via the existing Category A classifier, (b) routes into plan → parallel-search → synthesize, (c) uses existing roles with specialized prompts, (d) measured against the eval tower under the new multi-dimensional rubric (see §8).

---

## 8. Multi-Dimensional Rubric Evaluation for the Eval Tower

MindDR's evaluation architecture is a standalone contribution worth adopting even independent of the agent architecture.

**Current EPYC eval tower** (`/mnt/raid0/llm/epyc-orchestrator/scripts/autopilot/eval_tower.py`):
- Four metrics: quality, speed, cost, reliability (all scalars).
- Quality is a single `score_answer_deterministic()` output.

**MindDR upgrade**:
- Decompose **quality** into pipeline-stage sub-dimensions for open-ended tasks:
  - Reasoning Trajectory (thinking efficiency — reflection turns, query repetition)
  - Tool Call (correctness — usage proportions, failure rate)
  - Outline/Structure (for synthesis tasks — hierarchy correctness, coverage)
  - Content (tense, table correctness, grounding)
- Add **rubric-style scoring** for research-like queries: RACE dimensions (Comprehensiveness, Insight, Instruction Following, Readability) via 3-way LLM-as-Judge majority vote.
- Retain the single scalar as a headline metric, but stop optimizing solely against it.

This converges with the DeepPlanning deep-dive recommendation (add dimension-level quality decomposition to `EvalResult`). Two independent benchmark papers making the same architectural recommendation is strong signal.

**Integration point**: eval-tower-verification handoff (EV-3/4/5 pending) becomes the natural home.

**Schema sketch for the extended EvalResult**:

```
EvalResult {
  # existing scalars
  quality_overall: float        # retained for leaderboard continuity
  speed_tps: float
  cost_usd: float
  reliability: float

  # new for open-ended / research tasks
  quality_by_stage: {
    reasoning_trajectory: {
      reflection_turns: int,
      query_repetition_rate: float,
    },
    tool_call: {
      usage_proportions: {tool_name: float},
      failure_rate: float,
    },
    outline: {
      title_miss_rate: float,
      hierarchy_errors: int,
    },
    content: {
      tense_error_rate: float,
      table_valid_rate: float,
      citation_grounding_rate: float,
    },
  },
  race_rubric: {
    comprehensiveness: float,   # 3-way LLM judge, majority vote
    insight: float,
    instruction_following: float,
    readability: float,
  },
  case_pass: bool,              # all dimensions above threshold
}
```

This is backward-compatible — existing code reading `quality_overall` continues to work, and the new fields are populated only for open-ended tasks where the multi-dimensional scoring runs.

---

## 9. Risks & Tier 2b

### 9a. Internal-benchmark selection bias

MindDR Bench (51.8 SOTA) is built and scored by the authors. The 500 queries are from Li Auto's own assistant logs. Two concerns:
- **Distributional fit to training data.** The same domain mix that trained the system (automotive, travel, technology, finance) generates the benchmark. Performance on MindDR Bench should be read as "best in its distribution," not "best agent overall."
- **No external validation.** A benchmark where the SOTA-holder owns the benchmark is structurally suspect until independent runs reproduce. Public benchmarks (BrowseComp-ZH, xbench-DS, DeepResearch Bench) are the better anchor points for cross-comparison.

Treat MindDR Bench 51.8 as evidence of *deployment viability in their target domain*, not as a generalizable capability claim.

### 9b. Li Auto commercial context

The paper is a technical report from an industrial team with a commercial deployment. Standard concerns:
- Selective disclosure of what worked; failures and dead ends may be omitted.
- The "deployed as online product" framing is a commercial signal, not an engineering claim.
- Proprietary data — the ~35K Search-RL queries and tens-of-billions-scale internal KB — cannot be reproduced externally. Any attempt to replicate the recipe must synthesize its own dataset.

### 9c. Reproducibility without the datasets

The full recipe depends on three proprietary datasets:
- ~15K SFT trajectories with domain mix.
- ~35K Search-RL queries with entity annotations.
- Long-form + short-form Report-RL data with per-query RACE rubrics.

For an external replication at EPYC, data synthesis becomes the rate-limiting step. This is where `/workspace/research/deep-dives/agent-training-posttrainbench-act.md` and `/workspace/research/deep-dives/evoscientist-multi-agent-evolution.md` become relevant — synthetic trajectory generation infrastructure is a prerequisite.

### 9d. Tier 2b (next-level intake follow-ups)

- Ablate whether the outline-first Report methodology works at prompt-only scale (no Report-RL) — isolate the structural contribution from the RL contribution.
- Compare MindDR-30B-A3B efficiency claims against our own frontdoor-35B wall-clock on equivalent queries.
- Reproduce the dynamic reward scheduling pattern on a toy RL setup (when DGX available) before committing to the full recipe.

---

## 10. Phased Adoption Roadmap

### Phase 1 — Today (prompt-level, CPU-only)

**Scope**: Three-agent pipeline as a prompt-level orchestration mode. No model training.

Tasks:
1. Design `deep_research_mode` feature flag in routing (off by default).
2. Category A classifier addition: "research-like query" detection (multi-fact synthesis, comparison, survey-style questions).
3. New Planning Agent system prompt at architect_general (task-decomposition format).
4. New Report Agent system prompt at worker_explore (outline-first, citation-grounded synthesis).
5. pydantic_graph flow: `PlanningNode` → `DeepSearchFanOutNode` → `ReportSynthesisNode`, with standard escalation on any-node failure.
6. Eval tower extension (partial §8): add pipeline-stage sub-dimensions to quality metric for deep-research queries.
7. Sentinel suite: 20–40 research-like queries scored under multi-dimensional rubric. A/B vs current direct-answer mode.

**Success criteria**:
- Quality uplift ≥ +5pp on research-like sentinels vs direct mode.
- No regression on non-research sentinels (the flag should be dormant unless research detected).
- Tool-call count per research query should *not* explode — MindDR's efficiency advantage comes partly from structural organization, and if our prompt-only version 3× the tool calls we have done it wrong.

**Owner**: routing-intelligence handoff (new subsection) + eval-tower-verification handoff (rubric additions).

### Phase 2 — Post-DGX Spark (full RL recipe)

**Scope**: Adopt the four-stage training on a Tier B base model.

Prerequisite: DGX Spark acquired (tracked in `/workspace/handoffs/active/gpu-acceleration-path.md`) + AReaL-style async RL runner operational.

Target:
- Base: Qwen3-30B-A3B (MoE) or Qwen3-32B (dense), whichever the DGX Spark runs economically.
- Stage 1: SFT cold-start with EPYC-domain data (coding, orchestration, inference research) replacing Li Auto's automotive priors.
- Stage 2: Search-RL with EPYC tool set (REPL, web, gitnexus queries).
- Stage 3: Report-RL with RACE rubrics adapted to our eval tower.
- Stage 4: DPO + Self-SFT targeting our specific structured-error classes.

**Success criteria**: trained Tier B specialist beats prompt-only Tier B at equal inference cost on the sentinel suite + public deep-research benchmarks.

**Blocker**: DGX Spark arrival. Hard gate, not time-estimable from this handoff.

### Phase 3 — Architectural refactor (if Phase 1 pays off)

**Scope**: If Phase 1 shows durable +5pp uplift on research queries with no non-research regression, consider promoting the three-agent pattern from "mode" to "architecture."

Candidate structural changes:
- Dedicated `architect_report` (or `architect_synthesis`) role alongside `architect_general`/`architect_coding`.
- Routing classifier gains a third axis — not just difficulty (worker/coder/architect) and domain (general/coding) but *pipeline stage* (plan/search/synthesize).
- Possible consolidation of Phase 2 trained specialists into this refactored architecture.

Decision gate: at Phase 1 completion, review whether uplift is concentrated in research queries (→ refactor makes sense) or smeared across all queries (→ stay with routing-based specialization).

---

## 11. Cross-References

### Related intake entries

| Intake | Title | Relationship |
|--------|-------|--------------|
| intake-412 | DeepPlanning (Qwen) | Convergent evidence on multi-dimensional eval methodology |
| intake-438 | This paper | — |
| intake-425 | Memory Transfer Learning | Insight-format memory aligns with MindDR's XoT + Tool Memory |
| intake-426 | Dive into Claude Code | 98.4% infrastructure thesis — supports "harness design beats scaling" framing |
| intake-444 | Agent-World (related multi-agent architecture work) | Parallel decomposition patterns |
| intake-338 | Agent Lightning (trace collection) | Telemetry prerequisite for any agent RL |
| intake-244 | Meta-Harness | Tier 3 deferred to GPU — same blocker as MindDR Phase 2 |

### Related deep-dives (compile into wiki cluster later)

- `/workspace/research/deep-dives/deepplanning-agent-benchmark.md` — multi-granularity scoring precedent
- `/workspace/research/deep-dives/areal-async-rl-system.md` — RL runner infrastructure
- `/workspace/research/deep-dives/agent-training-posttrainbench-act.md` — agent RL training
- `/workspace/research/deep-dives/evoscientist-multi-agent-evolution.md` — multi-agent evolution patterns
- `/workspace/research/deep-dives/autopilot-iteration-strategy-synthesis.md` — iteration-strategy framing

### Active handoffs touched

- `/workspace/handoffs/active/routing-intelligence.md` — Phase 1 "deep research mode" would extend Category A classifier and add a new routing branch
- `/workspace/handoffs/active/meta-harness-optimization.md` — Phase 2 is the concrete "what to run on Tier 3" recipe when DGX arrives
- `/workspace/handoffs/active/eval-tower-verification.md` — rubric-style multi-dimensional evaluation addition
- `/workspace/handoffs/active/autopilot-continuous-optimization.md` — if Phase 1 ships, autopilot sentinels must include research-mode suites
- `/workspace/handoffs/active/repl-turn-efficiency.md` — MindDR's efficiency finding (fewer tool calls + higher accuracy under role-specialization) is complementary to the S1-S6 turn-efficiency work; the three-agent pipeline is a structural mechanism, the frecency/combined-ops work is a tactical one
- `/workspace/handoffs/active/gpu-acceleration-path.md` — gates Phase 2

### Wiki cross-references

- `/workspace/wiki/agent-architecture.md` — add MindDR to the cluster of "role-specialized agent" references (alongside Paperclip, AgentRxiv, OpenGauss)
- `/workspace/wiki/routing-intelligence.md` — the "role by pipeline stage" axis is a new dimension of specialization the wiki should capture

---

## 12. Summary Verdict

MindDR is a strong "adopt the pattern, defer the training" paper. The **three-agent role factoring** is adoptable as prompt-level orchestration on today's EPYC stack with meaningful expected uplift on research-like queries. The **four-stage RL recipe** is a concrete, detailed training protocol that slots cleanly into the existing DGX-Spark-gated workstream (meta-harness Tier 3, AReaL runner). The **multi-dimensional rubric evaluation** is the most immediately useful *standalone* contribution — it extends the eval tower for any open-ended task today, independent of whether we adopt the agent architecture.

Intake verdict: `worth_investigating` → `adopt_patterns (Phase 1)` + `revisit_post_DGX (Phase 2)`.

---

## Tier 2b Contradicting-Evidence Sweep (2026-04-22)

Run scope: four targeted WebSearch queries challenging the five load-bearing claims in intake-438. All queries executed against general web + arxiv. Nothing behind paywalls was reached.

### Queries executed

1. `"Mind DeepResearch" Li Auto reproduction OR criticism`
2. `"MindDR Bench" 51.8 SOTA independent evaluation`
3. `"Search-RL" "Report-RL" reproduction limitations deep research`
4. `GSPO GRPO MoE 15pp comparison criticism reinforcement learning`

### Findings by claim

**Claim 1 — SOTA 51.8 on MindDR Bench.**
No independent re-run found. MindDR Bench is a *self-curated* evaluation set: 500 queries mined from Li Auto's own intelligent-assistant production logs, spanning 16 domains (automotive, travel, technology, finance, etc.). The paper itself acknowledges the automotive-industry skew of the training population. Because the benchmark is neither public nor maintained by a neutral third party, and because no external deep-research agent has been evaluated on it, the 51.8 SOTA claim is *intrinsically unverifiable* outside the authors. This is not a fatal flaw — Li Auto has a legitimate reason to measure on their own distribution — but it means the 51.8 number should not be used as a headline comparison against OpenAI DR, Gemini DR, or Tongyi DR without disclosing the benchmark's provenance.

**Claim 2 — Public-benchmark numbers (BrowseComp-ZH 45.7, BrowseComp 42.8, WideSearch 46.5, xbench-DS 75.0).**
Third-party benchmarks, so reproducible *in principle*. But no independent re-run on MindDR-released checkpoints has been published to date. Magnitudes are in-family with Tongyi DeepResearch (arxiv 2510.24701v2) and DeepResearcher (arxiv 2504.03160v1), which report similar numbers for 30B-class agents on these benchmarks. So: plausible, cross-corroborated by *family of systems*, but NOT specifically verified for MindDR. Risk for our purposes is low, because Phase 1 adoption relies on the architectural *pattern*, not on hitting these specific numbers.

**Claim 3 — Four-stage training recipe (SFT → Search-RL → Report-RL → preference alignment) is replicable.**
The *components* are all public — Search-R1, R1-Searcher, ReSearch predate the Search-RL stage; Report-RL is a mild variant of rubric-conditioned PPO; preference alignment is standard DPO/RLHF. The *novelty* is sequencing them. Two concerns surfaced by the searches:
  - Deep-RL reproducibility baseline is poor (Henderson et al. 1709.06560 "Deep RL that Matters"): intrinsic variance, stochastic environments, unreported hyperparameters; four-stage pipelines compound these.
  - Surveys at arxiv 2509.06733 (RL Foundations for Deep Research) and 2508.12752 (Deep Research Survey) note that static-corpus RAG-RL approaches (which dominate the open-source deep-research space) have known ceiling issues due to sanitized environments. MindDR moves to real-web search, which helps, but the paper does not release reproduction code or full hyperparameters at first-release, and it does not ablate the Search-RL × Report-RL interaction. So the recipe is *not yet verifiably replicable* externally.

**Claim 4 — GSPO vs GRPO ~15pp on MoE.**
This is the *best-supported* claim in the paper. External corroboration exists:
  - GSPO paper itself (Chujie Zheng et al., arxiv 2507.18071, Qwen team) documents that GRPO's token-level importance ratios become unreliable on MoE because the set of activated experts shifts ~10% per gradient update on a 48-layer Qwen3-30B-A3B-Base model.
  - Qwen3 blog post (qwenlm.github.io/blog/gspo) reports GSPO eliminated the Routing Replay strategy GRPO needed for convergence.
  - Multiple review posts (Medium, HuggingFace blog) consistently place GSPO above GRPO on MoE.
  - Caveat: newer variants RSPO (Router-Shift Policy Optimization) and GMPO report matching or exceeding GSPO on the same benchmarks. The ~15pp gap vs GRPO is real but is a GRPO-baseline artifact; vs RSPO or GMPO the gap shrinks or flips.

**Claim 5 — ~30B scale sufficient to beat proprietary on research-like tasks.**
Consistent with Tongyi DeepResearch and DeepResearcher. Not contradicted. Caveat: "beat proprietary" is evaluated only on open benchmarks where proprietary systems were *also measured externally* — actual OpenAI Deep Research and Gemini Deep Research APIs change continuously, so snapshot comparisons have short shelf lives.

### Public-benchmark legitimacy flag (explicit per request)

The 42-75% public-benchmark range (BrowseComp-ZH, BrowseComp, WideSearch, xbench-DS) **looks legitimate**, not cherry-picked. Evidence: (a) the numbers are in-family with two independently-produced peers (Tongyi DR, DeepResearcher) at similar parameter scale; (b) these are third-party benchmarks, so gaming them would require disclosed-set overfit which would likely be called out on HuggingFace / X; (c) no contradicting independent evaluation was found.

The **MindDR Bench 51.8** number, by contrast, stands alone — it is the only strong signal on a self-curated domain-skewed benchmark, and should be treated as an internal engineering metric, not a SOTA claim, until an independent party evaluates competing systems on the same 500-query set.

### Implication for Phase 1 adoption (MD-1..MD-9 prompt-level pattern)

Phase 1 adoption (prompt-level three-agent factoring: Planning / DeepSearch / Report, plus the multi-dimensional rubric eval) remains **justified**, because:

1. Phase 1 depends on the *architectural pattern* (three-agent role specialization + rubric evaluation), NOT on any specific benchmark number.
2. The pattern has multiple independent analogues (AgentRxiv, Paperclip, OpenGauss multi-agent research), so MindDR is not the sole source.
3. No Tier-2b finding contradicts the *architectural* claim. The contradictions we found are about (a) MindDR Bench being internal-only and (b) four-stage RL training not being verifiably replicable yet — both of which are out-of-scope for Phase 1 (prompt-level) and in-scope only for Phase 2 (DGX-gated training).
4. The multi-dimensional rubric evaluation carries independent value regardless of whether the MindDR checkpoints themselves are reproducible.

**Phase 2 adoption (four-stage RL training recipe) should be gated harder than Phase 1**: require either (a) official MindDR code release + hyperparameters, or (b) an independent reproduction paper, before committing DGX time to Search-RL × Report-RL pipeline implementation. Until then, Phase 2 stays in the `revisit_post_DGX` bucket and should NOT be treated as a pre-validated recipe.

**Net**: Phase 1 (MD-1..MD-9) proceeds unchanged. Phase 2 gains an additional gate beyond hardware — reproducibility evidence for the four-stage recipe.
