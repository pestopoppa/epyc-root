# Agent-World: Scaling Real-World Environment Synthesis for Evolving General Agent Intelligence

**Intake**: intake-444
**ArXiv**: 2604.18292
**Categories**: agent_architecture, self_evolving_agents, environment_synthesis, mcp, reinforcement_learning
**Status**: deep-dive (written 2026-04-20)
**Cross-refs**: intake-411 (Qwen-Agent MCP), intake-412 (DeepPlanning), intake-438 (MindDR), intake-327/345 (GEPA), intake-328/329 (MiniMax self-evolution), intake-413 (HCC), intake-418 (externalization review)

---

## 1. Abstract

Agent-World couples **autonomous environment synthesis** with **continuous self-evolving agent training** in a closed loop: agents and environments co-evolve. A "deep-search" discovery agent mines web databases and tool ecosystems (MCP servers) for real-world environment themes, then synthesizes executable tools and verifiable tasks with controllable difficulty. The resulting training arena contains 1,978 environments and 19,822 tools; synthesized tasks average >15 interaction turns. Agents are trained with multi-environment reinforcement learning; the arena automatically diagnoses capability gaps and targets further environment/task expansion. Base models Qwen3-4B/8B/14B, fine-tuned as Agent-World-8B/14B, reportedly outperform strong open-source foundations and proprietary baselines across 23 agent benchmarks (τ²-Bench, BFCL V4, MCP-Mark, ClawEval, SkillsBench, etc.). Agent-World-8B jumps from 53.83 to 65.94 overall (+12.11); Agent-World-14B reaches 70.18. The paper reports clear scaling relationships among environment diversity, self-evolution rounds, and downstream agent performance.

---

## 2. Agent-World Mechanism

### 2.1 Agentic Environment-Task Discovery (ETD)

Instead of hand-authoring benchmark suites, Agent-World runs a **deep-search agent** that is anchored on abstract real-world environment themes (e.g. "scientific literature search", "e-commerce refund flows", "travel itinerary planning") and autonomously:

1. **Mines environment databases from the web** — crawls MCP registries, public APIs, SaaS/self-hosted tool catalogues; extracts endpoint schemas, behaviours, and side-effect contracts.
2. **Generates executable tools** — wraps discovered services with callable MCP-compatible tool schemas. The agent normalises authentication, parameter types, and error semantics into a uniform interface.
3. **Synthesizes verifiable tasks** — composes multi-step task specifications referencing those tools, each task paired with a verifier (a checker function that reads end-state or trajectory). Difficulty is **controllable** via number of required tool calls, chain length, cross-tool dependencies, presence of distractors, and adversarial dynamics.
4. **Registers environments** — the (theme, tools, tasks, verifier) bundle is stored as an environment in a growing arena. The paper reports the arena reaching **1,978 environments and 19,822 tools**; synthesized tasks average **>15 interaction turns**, indicating genuinely long-horizon agentic work.

The key design choice: every discovered environment is **executable** (not a static transcript) and **verifiable** (every task has a programmatic oracle). This makes the arena suitable as an RL training substrate — rewards are signal-grounded rather than LLM-judge-synthesized.

### 2.2 Continuous Self-Evolving Agent Training (CSE)

The agent is trained with **multi-environment reinforcement learning** (GRPO-family, outcome-based rewards from verifiers). Crucially, training is not a fixed dataset pass — it is a loop:

1. Sample batch of environments from the arena, weighted by a diagnostic signal.
2. Rollouts produce successes and failures; verifier returns scalar reward.
3. **Capability-gap diagnosis** — failure patterns (e.g. which task categories or tool compositions systematically fail) are summarised into gap descriptors.
4. **Targeted arena expansion** — the ETD agent is re-invoked with gap descriptors as new themes; it synthesizes additional environments/tasks that probe those specific failure modes.
5. Training continues on the expanded arena.

Agents and environments thus co-evolve: the agent gets harder, targeted practice; the arena grows toward the agent's frontier.

**Training arena parameters** (from the Snowflake-Labs open-source cousin "Agent World Model"):
- Base models: Qwen3-4B / 8B / 14B (thinking-capable, tool-use-capable).
- 1,024 parallel environment instances per training step.
- Outcome-based reward (task success from verifier).
- Multi-environment sampling (domain diversity in every batch).

### 2.3 MCP Integration as Unified Tool Interface

Agent-World adopts **Model Context Protocol (MCP)** as the standard agent↔environment interface. Discovered services are wrapped as MCP tools, enabling three properties:

- **Interoperability** — any MCP server in the wild is a candidate environment contributor.
- **Training-inference parity** — the same tool surface exists at train time and inference time; no scaffold mismatch.
- **Arena portability** — environments synthesized from one MCP corpus transfer to any MCP-compatible runtime (including ours).

The MCP layer is **tool-layer, not model-layer** — it doesn't depend on architecture or weights.

### 2.4 Co-Evolution of Policies and Environments

The closed loop is:

```
   [Deep-Search ETD Agent]
        │  (themes, gap descriptors)
        ▼
   [Environment Arena: 1,978 envs, 19,822 tools]
        │  (multi-env batches)
        ▼
   [Agent-World-XB policy]  <── RL training (outcome reward)
        │  (rollouts, failures)
        ▼
   [Capability-Gap Diagnosis]
        │  (new themes for ETD)
        └────> back to Deep-Search ETD Agent
```

This is structurally what the AutoResearch literature (intake-148/149) called an "autonomous loop with failure memory and git ratchet", but applied at the **environment+policy** level rather than the **prompt+code** level.

---

## 3. Reported Results

### 3.1 Benchmark Suite (23 agent benchmarks)

The suite includes:
- **τ²-Bench** — realistic multi-turn agent-user-tool interactions (airline, retail, telecom).
- **BFCL V4** — function-calling evaluation (parallel, multi-step, multi-turn).
- **MCP-Mark** — MCP-protocol tool-use benchmark.
- **ClawEval** — agentic code/claw task benchmark.
- **SkillsBench** — skill composition benchmark.
- Plus 18 additional agent benchmarks spanning browsing, planning, code, tool-use, long-horizon reasoning.

### 3.2 Headline Numbers

| Model                 | Overall | Δ vs base |
|-----------------------|---------|-----------|
| Qwen3-8B (base)       | 53.83   | —         |
| Simulator (prior SOTA env-scaling method) | lower than AW | — |
| EnvScaler (prior env-scaling method) | lower than AW | — |
| **Agent-World-8B**    | **65.94** | **+12.11** |
| **Agent-World-14B**   | **70.18** | best overall |

Agent-World-14B is the **best open-source model on this 23-benchmark suite** per the paper, beating larger open-weights baselines and a set of proprietary baselines selected from recent API models. The exact proprietary comparators are paper-reported and are the primary claim requiring Tier 2b corroboration (see §10).

### 3.3 Scaling Analyses

The paper reports clear scaling relationships:

- **Environment diversity ↔ agent performance** — performance increases with number of distinct environments, with diminishing returns past ~1,500 environments at 14B scale.
- **Self-evolution rounds ↔ agent performance** — each additional co-evolution round (ETD → training → diagnosis) yields monotone gains until plateau (~6–8 rounds in published figures).
- **Scale ↔ ceiling** — 14B extracts more from the same arena than 8B; 4B plateaus earlier. Consistent with standard RL scaling in agent settings.

The scaling story is the main theoretical contribution: it frames **environment count and diversity as the missing scaling axis** for agent RL, complementing parameter-count and data-size axes.

---

## 4. Existing EPYC Analog — AR-3 / AutoPilot

Our **AutoPilot loop** (`epyc-orchestrator/scripts/autopilot/`) runs continuous optimization over 4 species:

| Species | What it mutates | Against |
|---------|-----------------|---------|
| Seeder | Q-values (routing reward accumulation) | Debug suites |
| NumericSwarm | 23 numeric params (Optuna NSGA-II) | EvalTower benchmarks |
| PromptForge | Prompt templates (.md) + code mutations (allowlist) | EvalTower benchmarks |
| StructuralLab | Flags, routing model lifecycle, stack topology | EvalTower benchmarks |

The EvalTower validates against a **FIXED benchmark suite** (HF: MMLU, GSM8K, + internal sentinel + 579 debug questions + ~59K question pool). The loop gets tighter as mutations accumulate, but the **evaluation targets never move**.

**Agent-World's move**: synthesise the benchmarks too. The arena grows while the policy grows. Capability-gap diagnosis routes synthesis toward the weakest category. This is one level further up the meta-harness stack than AR-3 currently reaches.

Our **meta-harness handoff Tier 3** (deferred outer-loop rebuild) explicitly anticipates this kind of outer loop but scopes it to harness code, not environments. Agent-World extends Tier 3 with an environment-synthesis axis.

---

## 5. Amend / Expand / Confirm

### 5.1 Confirm — Validates meta-harness thesis

**Yes.** The meta-harness thesis (intake-271/418/426) is that **harness-layer investment dominates weights-layer investment**. Agent-World is an extreme case:

- An 8B/14B open model beats proprietary baselines **not by changing model class but by changing what it trains against** (self-synthesized environments).
- The improvement (+12 points at 8B) from training-arena expansion exceeds what a comparable weights-only scaling step would yield.
- The win comes from **environment diversity and verifier grounding**, both harness-layer properties.

This corroborates intake-418's "weights→context→harness era" framing and intake-426's "98.4% of agent complexity lives in operational infrastructure". Our meta-harness investment direction is further validated.

### 5.2 Amend — Should AR-3's mutation space expand to include task synthesis?

**Yes, bounded.** The current AutoPilot mutation species are all **policy-side** (prompts, code, flags, routing weights). Agent-World suggests a **5th species** that mutates the **evaluation target** itself: synthesising new benchmarks from discovered tool/environment descriptors.

**Risk to guard against**: if the same loop synthesises and evaluates, it can game itself. Agent-World avoids this by using **verifiable tasks** — the verifier is programmatic, not LLM-judged. Our EvalTower already has partial programmatic verification (T0 state-matching via sentinel questions). Extending to an **Environment Synthesis species** requires:

- A held-out verifier path (verifier written at arena-creation time, frozen, never touched by training).
- A separation between **training arena** (can grow from agent-synth) and **validation tier** (T2+ must remain fixed/external).
- An immutable "gold ring" benchmark subset that the agent cannot propose changes to.

With those guards, an Environment Synthesis species is a natural extension.

### 5.3 Expand — Minimum viable environment synthesis for EPYC

The lightest adoption path uses **existing infrastructure**:

- **Question pool** at `/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/question_pool.py` (≈59K questions across 23 suites) is already an arena — just not a *grown* one.
- **Capability-gap diagnosis** is already partially present via per-suite quality trends in EvalTower and `journal.recent_failures()` in autopilot.
- **Difficulty control** is the missing piece.

**Phase 1 "Environment Synthesis Lite"**:
1. Add a `synthesize_task()` utility that takes (suite, difficulty, k tool calls, chain length) and generates a task variant from the existing pool by composition (pick k questions that share entities, chain their solutions, verify composed answer).
2. Diagnostic pass: EvalTower writes a per-suite gap report (which suites have quality < threshold, which per-role models fail most).
3. Autopilot proposes **new T1 validation batches** biased toward diagnosed gaps.
4. Difficulty-varied task generation: adjust k and chain length based on current best performance.

This is reachable in ~2 weeks of work on top of existing seeding infrastructure — no new model weights, no new training.

---

## 6. Integration With Existing Work

### 6.1 AR-3 / AutoPilot — Environment Synthesis Species

A 5th species alongside Seeder/NumericSwarm/PromptForge/StructuralLab:

```
Species 5: EnvSynth
  - Input: capability-gap diagnosis from EvalTower + strategy_store
  - Action types:
    - synthesize_task_batch(suite, difficulty, k)
    - expand_suite(suite, new_theme)
    - retire_saturated_suite(suite)  [gold ring immune]
  - Output: new validation batches, registered to EvalTower
```

Immediate integration with existing autopilot machinery:
- `experiment_journal.py` — log every synthesis event as a JournalEntry.
- `safety_gate.py` — add `_env_sanity_check()` (verifier runs on reference model; if reference solves it, task is non-trivial; if not, flag as broken).
- `pareto_archive.py` — add a 5th axis (arena diversity) to the 4D Pareto.

### 6.2 MCP Integration — Qwen-Agent Singleton Pattern (intake-411)

Our orchestrator already hosts a **Qwen-Agent MCP singleton** (intake-411). Adopting Agent-World's MCP tool ecosystem is therefore **cheap**:

- Agent-World's discovered tool descriptors can be imported as MCP tool manifests.
- The orchestrator's existing MCP surface (`src/mcp/`) accepts additional tool registrations without architectural change.
- Draft→target MCP parity: since MCP is tool-layer, changes do not require re-training or re-loading models.

**Action**: dump the top-100 highest-coverage MCP tools from Agent-World's public arena (once released) into an MCP registry file at `/mnt/raid0/llm/epyc-orchestrator/orchestration/agent_world_tools.yaml` and wire into the existing MCP singleton with a feature flag `ORCHESTRATOR_AGENT_WORLD_TOOLS=1`.

### 6.3 Meta-Harness Tier 3 — Outer Loop Rebuild

Meta-harness Tier 3 was explicitly **deferred** because "the outer search loop is not open-sourced" and building from scratch is expensive. Agent-World **is** that outer loop, and its environment-synthesis component is **open-source-adjacent** (Snowflake-Labs' `agent-world-model` is public).

If we adopt Agent-World's architecture:
- Tier 1 (trace feedback) — already done.
- Tier 2 (code mutation) — already done.
- **Tier 3 (outer loop rebuild) — becomes: adopt Agent-World's arena + co-evolution skeleton, but with training-free discovery in Phase 1 (see §9).**

This re-opens a path we previously considered infeasible.

---

## 7. CPU Feasibility

### 7.1 Model Serving

- **Agent-World-8B** — runs comfortably on our stack (worker tier or frontdoor tier). ~6GB in Q4KM. Already within operating constraints.
- **Agent-World-14B** — fits the **worker tier** (intake-415, current worker swap). ~9GB Q4KM. Compatible with the 192t single-model mode and 48t NUMA-concurrent mode documented in the stack config.
- **Thinking-mode** — Agent-World-8B/14B are thinking-capable. Our `architect_general` currently has `--jinja` removed to avoid thinking loops (handoffs/autopilot, 2026-04-15). For Agent-World models, thinking should be **re-enabled at model level** but gated at role level.

### 7.2 Environment Discovery

The **discovery agent** is the Deep-Search ETD component. It is LLM-orchestrated but **inference-only** — no gradient updates. It fits the multi-step pipeline pattern we already run:

```
ETD = ReAct agent:
  Tool 1: web_search(query)
  Tool 2: fetch_url(url)
  Tool 3: parse_tool_schema(spec)
  Tool 4: register_tool(schema)
  Tool 5: synthesize_task(env, difficulty, k)
  Tool 6: verify_task(task, trajectory)
```

All 6 tools are **already present** (or trivially built) in our stack:
- `web_search` — existing Tavily/Searx integration.
- `fetch_url` — existing HTTP client.
- `parse_tool_schema` — new, trivial (MCP tool manifest parser).
- `register_tool` — new, trivial (append to MCP registry).
- `synthesize_task` — new, templated LLM call.
- `verify_task` — new, per-task verifier (depends on task).

Discovery is **sequential-only** (one environment at a time) and cost-bounded by wall-clock budget. On CPU this runs overnight batch-mode.

### 7.3 RL Training Component

RL training on 8B/14B requires **GPU** (A100/H100-class). Our DGX Spark is **not yet acquired** (user hardware note: project_dgx_spark_target.md). So **RL specialization is GPU-gated**.

However — environment discovery and task synthesis are **training-free** and adoptable today on CPU.

---

## 8. Training Requirements

| Component | Needs GPU? | CPU-feasible today? |
|-----------|-----------|---------------------|
| Deep-Search ETD agent (tool/env discovery) | No | **Yes** |
| Task synthesis (LLM-templated) | No | **Yes** |
| Task verification (programmatic) | No | **Yes** |
| Capability-gap diagnosis (log summarisation) | No | **Yes** |
| MCP tool wrapping / registration | No | **Yes** |
| **Multi-env GRPO training (Agent-World-8B/14B)** | **Yes** | **No** |
| Inference against synthesized environments | No | **Yes** (existing models) |

The critical observation: **the environment-synthesis half of Agent-World is CPU-feasible and training-free.** Only the RL training half is GPU-gated.

This cleanly suggests a phased adoption (§9).

---

## 9. Proposed Phased Adoption

### Phase 1: Training-Free Environment Discovery (CPU, adopt now)

**Goal**: run Agent-World's ETD component with existing EPYC models to grow the validation arena.

**Scope** (~3–4 weeks):

1. **Build `env_synth/` module** in `epyc-orchestrator/scripts/autopilot/species/`:
   - `etd_agent.py` — ReAct-style discovery agent, uses frontdoor model.
   - `task_synthesizer.py` — templated task generation with difficulty control.
   - `verifier_builder.py` — programmatic verifier scaffolder.
   - `mcp_tool_registry.py` — MCP tool manifest store.
2. **Wire into autopilot**: `EnvSynth` as 5th species; scheduled by meta-optimizer alongside others.
3. **Initial arena bootstrap**: run discovery for 48h, target ≥50 environments / ≥500 tools / ≥500 tasks.
4. **EvalTower integration**: synthesized tasks feed T1 validation batches; gold-ring benchmarks remain fixed.
5. **Capability-gap diagnosis**: weekly rollup; ETD agent re-prompted with gap descriptors.
6. **Safety**: every synthesized task must be solvable by a reference model (Claude or our architect_general) before accepted — prevents broken tasks contaminating the arena.

**Deliverable**: autopilot can grow its validation arena autonomously, against the same fixed policy weights. Expected gain: better diagnostic signal, not higher scores (scores depend on training, which is Phase 2).

### Phase 2: RL Specialization (GPU-gated, defer)

**Goal**: train Agent-World-style specialists on the expanded arena.

**Blockers**:
- DGX Spark not yet acquired (project_dgx_spark_target.md).
- Multi-env GRPO infrastructure not built (AReaL async RL is a candidate, see intake-??/areal-async-rl-system.md).
- 1,024 parallel environment instances is high infra overhead.

**Preconditions**:
- DGX Spark online.
- Phase 1 produced ≥1,000 stable environments.
- AReaL or equivalent async RL framework integrated.

**Scope**: train Qwen3-8B → Agent-World-8B-EPYC on our synthesized arena. Evaluate against 23-benchmark suite. Compare to published Agent-World-8B as external validator.

### Phase 1.5 (optional bridge): SFT on Agent-World public checkpoint

If Agent-World publishes 8B/14B weights before DGX Spark arrives, **download, register, serve, benchmark** — zero training cost. This is zero-risk and independent of Phase 2.

---

## 10. Risks & Tier 2b Corroboration

### 10.1 "Beat proprietary" claim

The 14B-beats-proprietary claim is the single strongest marketing hook but has two weak links:

- **Proprietary comparator selection** — which proprietary models, which versions, which settings? Papers in this space routinely cherry-pick the proprietary baselines (e.g. comparing to GPT-4-0613 rather than 5.x). **Tier 2b action**: reproduce against contemporaneously released proprietary APIs if possible; flag any older-version comparisons.
- **23-benchmark selection bias** — if the authors controlled benchmark selection, they could optimise the arena toward overlap. **Tier 2b action**: check which of the 23 benchmarks were designed by the same group vs external; rerun on 3–5 external held-out benchmarks not in the training-arena theme set (e.g. SWE-Bench Verified, WebArena Hard, GAIA).

Both concerns match the known MindDR Bench / BrowseComp caveat (intake-438) — internal benchmarks favour internal methods.

### 10.2 Environment-synthesis quality

Generated tasks can be:
- **Degenerate** — trivially solved by memorisation or by lucky tool hit.
- **Broken** — verifier always returns pass or always fail.
- **Out-of-distribution for the agent's tool surface** — impossible given current tools.

**Mitigations**:
- Reference-model sanity pass (§9 Phase 1.6).
- Verifier fuzzing (run verifier on reference correct + reference incorrect trajectories; both must match expected labels).
- Periodic external benchmark anchoring (§10.1 held-out set).

### 10.3 Arena-agent reward hacking

If the ETD agent and training agent share model families, they can collude (ETD synthesises tasks that favour a weak agent's biases). Published Agent-World uses the **same Qwen3 family** for both — this risk is real.

**Mitigation**: use a **different model family** for ETD vs training. In our stack: frontdoor (or architect_general Qwen3.5-122B) drives ETD; worker (Qwen3-30B-A3B) and specialists are trained. Cross-family separation reduces collusion risk.

### 10.4 MCP surface expansion blast radius

Dumping 19,822 tools into an orchestrator MCP registry can:
- Explode router context windows.
- Introduce untrusted tool endpoints (security).
- Bloat tool selection latency.

**Mitigation**:
- Treat synthesized tools as **sandboxed** — route through a hardened MCP proxy with deny-by-default network egress.
- Progressive disclosure (intake-414 token-savior pattern) — only surface top-k tools per query to the router.
- Tool allowlist per agent role.

### 10.5 Tier 2b verdict

**Corroboration pending**. Specifically:
- [ ] Confirm proprietary comparator versions.
- [ ] External held-out benchmark rerun (SWE-Bench Verified, GAIA, WebArena Hard).
- [ ] Check for same-authorship overlap between Agent-World and the 23 benchmarks.
- [ ] Replicate at smaller scale (4B on a 100-env subset) to confirm scaling direction.

Until corroborated, treat "beats proprietary" as **plausible but not confirmed**.

---

## 11. Cross-References

### 11.1 Active handoffs
- `handoffs/active/autopilot-continuous-optimization.md` — AR-3 prompt/structural mutation loop. Agent-World is the environment-synthesis extension.
- `handoffs/active/meta-harness-optimization.md` — Tier 3 deferred rebuild; Agent-World re-opens the path.
- `handoffs/active/bulk-inference-campaign.md` — Packages A–H. Environment synthesis could become Package I (arena bootstrap campaign).
- `handoffs/active/learned-routing-controller.md` — MLP routing classifier; EnvSynth species could feed diversified training data.

### 11.2 Related intakes / deep dives
- **intake-411** (Qwen-Agent MCP singleton) — MCP adoption path, already in stack.
- **intake-412** (DeepPlanning) — long-horizon planning benchmark; Agent-World complements at environment-synthesis layer. Deep dive: `research/deep-dives/deepplanning-agent-benchmark.md`.
- **intake-438** (MindDR, Li Auto) — production RL agent-role specialization; parallels Agent-World's CSE component but at role-specialization layer.
- **intake-327/345** (GEPA) — reflective evolutionary search at prompt/program level; EnvSynth is GEPA at environment level.
- **intake-328/329** (MiniMax M2.7 self-evolution) — self-evolving agent harness; Agent-World is the environment-side complement.
- **intake-413** (HCC cognitive accumulation) — L1/L2/L3 memory tiers; gap diagnosis in Agent-World maps to L2 phase summaries.
- **intake-418** (Externalization review) — weights→context→harness era thesis; Agent-World is the canonical "harness era" validation.
- **intake-426** (Dive into Claude Code) — 98.4% complexity in operational infra; Agent-World's environment layer is the most ambitious operational-infra scaling.
- **intake-394** (Evolver GEP) — auditable protocol-bound evolution; applicable governance pattern for EnvSynth species.
- **intake-425** (Memory Transfer Learning) — cross-domain memory pooling; informs arena partitioning.

### 11.3 Wiki pages
- `wiki/autonomous-research.md` — autopilot thesis, AutoResearch framing; update with environment-synthesis dimension.
- `wiki/agent-architecture.md` — agent scaffolding patterns; add Agent-World co-evolution loop diagram.

### 11.4 Code targets
- `epyc-orchestrator/scripts/autopilot/species/` — where EnvSynth species module would live.
- `epyc-orchestrator/src/mcp/` — MCP tool registry extension point.
- `epyc-inference-research/scripts/benchmark/question_pool.py` — existing pool, seed for Phase 1 synthesis.
- `epyc-orchestrator/orchestration/model_registry.yaml` — registration path for Agent-World-8B/14B if weights released.

### 11.5 External
- Paper: https://ar5iv.labs.arxiv.org/abs/2604.18292
- HuggingFace paper page: https://huggingface.co/papers/2604.18292
- Related open-source: `github.com/Snowflake-Labs/agent-world-model` (architectural cousin).
- Adjacent: AgentScaler (arxiv:2509.13311), AgentEvolver (arxiv:2511.10395), CoEvolve (arxiv:2604.15840), Nex-N1 (arxiv:2512.04987), TOUCAN (arxiv:2510.01179, 1.5M MCP trajectories).

---

## 12. Summary Verdict

| Axis | Verdict |
|------|---------|
| Validates meta-harness thesis? | **Yes** — strongest external validation to date. |
| Should AR-3 expand to task synthesis? | **Yes, bounded** — add EnvSynth as 5th species, protect gold-ring benchmarks. |
| MVP for EPYC environment synthesis? | **Feasible** — compose over 59K question pool, use diagnostic gap descriptors. |
| CPU-feasible today? | **Yes, partially** — discovery + synthesis + verification are training-free. |
| RL specialization? | **Defer to DGX Spark acquisition** — Phase 2 GPU-gated. |
| Adoption recommendation | **Phase 1 (training-free) adopt now; Phase 2 (RL-full) defer GPU-gated; Phase 1.5 (SFT on released weights) zero-risk.** |
| Tier 2b status | **Not run** — beat-proprietary + 23-benchmark selection bias require external corroboration. |

**Top 1 next action**: scaffold `epyc-orchestrator/scripts/autopilot/species/env_synth/` stub with an ETD agent wrapping existing web_search + fetch_url + question_pool.py as a seed arena. Run 48h on a 50-environment target. Feed gap diagnosis into AutoPilot controller prompt. No new training, no new models, no new benchmarks outside gold ring.

---

## Tier 2b Contradicting-Evidence Sweep (2026-04-22)

### Queries run (WebSearch)

1. `"Agent-World" reproduction OR criticism beat proprietary benchmark`
2. `Environment-Task Discovery reward hacking criticism self-synthesized benchmark`
3. `self-evolving agent training arena gaming benchmark contamination`
4. `"Agent-World-8B" OR "Agent-World-14B" independent evaluation reproduction`
5. `Agent-World arxiv 2604.18292 open source weights release code MCP registry`
6. `Agent-World 23 benchmarks SkillsBench ClawEval authorship same team`
7. `deterministic verifier gameable agent RL programmatic oracle failure modes`

### Findings against each challenged claim

#### C1 — "Agent-World-8B/14B beat proprietary baselines across 23 benchmarks"

**Status: UNREPRODUCED.** No third-party replication of the headline numbers appears in the public literature as of 2026-04-22. All references trace back to:
- the Agent-World paper itself (arxiv:2604.18292);
- the HuggingFace paper page (huggingface.co/papers/2604.18292);
- the Snowflake engineering blog describing "Agent World Model (AWM)" — an architectural *cousin* (arxiv:2602.10090), not the identical artifact, though it inherits the same 53.83 -> 65.94 / 70.18 numbers.

The exact proprietary comparator list (which GPT-X, which Claude revision, which Gemini, with which tool-calling harness) is not independently verified. Known pattern (MindDR / intake-438 caveat): proprietary baselines are often pinned to older API versions that postdate the authors' training window.

**Verdict on C1: plausible but unconfirmed. The claim should NOT be cited in downstream planning as if it were an established fact.**

#### C2 — "ETD produces verifiable tasks with controllable difficulty"

**Status: DESIGN-PLAUSIBLE, EXECUTION-RISKY.** The design (programmatic oracle + parameterised k/chain-length/distractor count) is coherent, but the reward-hacking literature makes the failure envelope concrete:
- Survey on reward hacking (arxiv:2507.05619, Comprehensive Empirical Study, Jul 2025) and Lilian Weng's review (2024) document that deterministic verifiers are routinely bypassed in practice (assertion rewriting, sys.exit(0), test-file edits, process-killing in game-play).
- RLEF (ICML 2025) proposes the standard mitigation — private-test holdout with only public tests for intermediate feedback. Agent-World does not report doing this for its synthesized verifiers.
- TRACE (arxiv:2601.20103, Jan 2026) explicitly flags circular labeling risk when the same model family produces both synthesis and detection/verification.

**Verdict on C2: verifiability claim is procedural, not empirical — the paper provides no verifier-fuzzing or private-test-holdout analysis.**

#### C3 — "CSE combines multi-env RL with dynamic task synthesis"

**Status: ARCHITECTURAL NOVELTY CONFIRMED, QUALITY CLAIM UNCONFIRMED.** The architecture (closed loop: synthesize -> train -> diagnose gaps -> re-synthesize) is corroborated by similar frameworks: AgentEvolver (modelscope, GitHub), AReaL async RL (arxiv intake pending). So the pattern exists and is credible. The specific claim that *this* instantiation produces the reported gains is the unreproduced part (see C1).

#### C4 — "Scaling correlates with environment diversity and self-evolution rounds"

**Status: PLAUSIBLE BUT SELF-REPORTED.** All scaling curves are from the same paper using the same arena. There is no external replication at 4B / 8B / 14B across an independent environment pool. The concern is circular: if the arena is constructed by the same model family that is being evaluated, diversity-vs-performance correlation can be inflated by synthesis quirks the agent learns to exploit.

#### C5 — "MCP integration provides unified real-world service interface (19,822 tools)"

**Status: PARTIALLY CONFIRMED.** Snowflake-Labs/agent-world-model repo exists (GitHub), HF paper page live. **Released as of Feb 2026**: synthesis pipeline, **1,000-environment subset** (not 1,978), and RL-trained agents. **Not confirmed released**: the full 19,822-tool MCP registry, complete arena, and 14B weights. Release scope for "Agent-World proper" vs "Agent World Model (AWM)" is ambiguous — same team, overlapping numbers, different artifact names.

### Benchmark selection bias (23-suite)

- **ClawEval**: Peking U + HKU, arxiv:2604.06132v1 — different institutions from Agent-World authors (Dong, Lu, Huang, Zhong are not in ClawEval's author list per search results). Not author-overlap, but co-release timing (April 2026) in the same "real-world agent benchmark" marketing wave.
- **SkillsBench**: benchflow-ai, arxiv:2602.12670 — third-party; released Feb 2026.
- **τ²-Bench, BFCL V4, MCP-Mark**: external, pre-existing benchmarks.

So the 23 benchmarks are **not all author-controlled**. However, the paper does not report results on well-established external held-outs that *don't* fit a tool-use-heavy profile — **SWE-Bench Verified, GAIA, WebArena Hard, OSWorld** are conspicuously absent. Selection bias is not from co-authorship but from **suite-class cherry-picking**: the 23 are all within a profile that favors arena-trained tool-use agents.

### Arena-agent collusion

Confirmed risk per the reward-hacking literature. Agent-World uses Qwen3 family for both ETD and trained agent. TRACE (arxiv:2601.20103) specifically cites this pattern as producing "optimistically biased" scores from circular labeling. Deep-dive §10.3 flagged this — sweep confirms the concern is materially real, not speculative.

### Impact on Phase 1 training-free adoption (AW-1..AW-6)

**Phase 1 adoption remains defensible. Rationale:**

1. Phase 1 (AW-1..AW-6) imports Agent-World as an **architectural pattern** — deep-search ETD + capability-gap diagnosis + programmatic verifier scaffolding + co-evolution loop. It does **not** inherit Agent-World's weights, its arena, or its benchmark numbers.
2. The beat-proprietary claim, which is the weakest element under scrutiny, is entirely irrelevant to Phase 1. Phase 1 improvements are **diagnostic signal quality**, not **benchmark score**.
3. The verifier-gaming risk *does* apply to Phase 1, but deep-dive §10.2/§10.3 already prescribed the correct mitigations: (a) reference-model sanity pass before accepting synthesized tasks, (b) held-out verifier path frozen at arena creation time, (c) gold-ring immutable benchmarks the agent cannot propose changes to, (d) cross-family separation — use frontdoor/architect_general for ETD, not the same model family being evaluated.

**Phase 2 gating (stricter than before):** Phase 2 (full RL specialization on synthesized arena) was already GPU-gated on DGX Spark acquisition. **New gating condition added**: before committing compute to Phase 2, independent external-benchmark replication of Agent-World's claim must exist — either in the literature or by our own Phase 1.5 SFT reproduction of the released 8B checkpoint on SWE-Bench Verified / GAIA. If Phase 1.5 on the released weights fails to match paper claims on external benchmarks, Phase 2 is downgraded from "defer-until-GPU" to "do-not-pursue".

**Phase 1.5 (SFT on released checkpoint) repurposed as Tier 2b corroboration probe:** rather than treating Phase 1.5 as a zero-risk freebie, it now carries a *diagnostic* role — running the released Agent-World-8B against SWE-Bench Verified + GAIA locally would be the single most informative datapoint for deciding Phase 2.

### Updated verdict row in §12

| Tier 2b status | **Run 2026-04-22. Beat-proprietary claim UNREPRODUCED in open literature; all numbers author-self-reported. Phase 1 adoption (pattern-level) unaffected. Phase 2 (RL specialization) adds external-replication gate on top of existing DGX Spark gate. Phase 1.5 (SFT on released weights) upgraded from freebie to corroboration probe.** |

### Items still open

- [ ] Run Agent-World-8B released checkpoint against SWE-Bench Verified and GAIA when weights + inference harness are confirmed public.
- [ ] Check ArXiv v2 / TMLR submission of 2604.18292 for reviewer-visible additional comparator details.
- [ ] Monitor huggingface.co/papers/2604.18292 comment section and Semantic Scholar citations over next 90 days for independent replication attempts.
