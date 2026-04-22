# Agent-World Environment Synthesis

**Status**: stub / in-planning (Phase 1 training-free; Phase 2 GPU-gated)
**Created**: 2026-04-22 (split from `autopilot-continuous-optimization.md` per deep-dive integration pass)
**Categories**: agent_architecture, autonomous_research, training_distillation
**Priority**: MEDIUM (autopilot 5th species; concrete Tier 3 recipe for meta-harness outer loop)
**Depends on**: `autopilot-continuous-optimization.md` (AR-3 loop), `meta-harness-optimization.md` (Tier 3)

## Objective

Adopt Agent-World's autonomous environment + task synthesis (Environment-Task Discovery) as the 5th species in the EPYC autopilot loop. Phase 1 is training-free and CPU-feasible today: LLM-orchestrated exploration of databases and MCP tool ecosystems to synthesize verifiable tasks with controllable difficulty, feeding them as new benchmark suites into AR-3. Phase 2 is GPU-gated and deferred to DGX Spark — multi-environment GRPO training of the co-evolving policy.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-444 | Agent-World: Scaling Real-World Environment Synthesis for Evolving General Agent Intelligence (arxiv:2604.18292) | high | worth_investigating |
| intake-411 | Qwen-Agent MCP singleton manager pattern | medium | adopt_patterns |
| intake-412 | DeepPlanning benchmark | medium | adopt_patterns |

**Source deep dive**: [`/workspace/research/deep-dives/agent-world-environment-synthesis.md`](../../research/deep-dives/agent-world-environment-synthesis.md) (426 lines)

## Key Claims (from Agent-World paper)

- Agentic Environment-Task Discovery autonomously explores databases + tool ecosystems to synthesize verifiable tasks with controllable difficulty.
- Continuous Self-Evolving Agent Training combines multi-env RL with dynamic task synthesis; identifies capability gaps automatically.
- Agent-World-8B and 14B outperform proprietary baselines across 23 agent benchmarks.
- Model Context Protocol (MCP) integration provides a unified real-world service interface.
- Scaling trends correlate with environment diversity and self-evolution rounds (not just model size).

## Phased Adoption

### Phase 1 — Training-free environment discovery (CPU-feasible today)

Use existing local models as ETD (Environment-Task Discovery) agents exploring the MCP ecosystem. Output: synthesized task suites feeding AR-3 as additional benchmark input. No weight updates.

### Phase 1.5 — Optional SFT on public Agent-World trajectories (if weights released)

If Agent-World team releases 8B/14B checkpoints + training trajectories, download + serve as reference models for the species loop.

### Phase 2 — Multi-environment GRPO training (GPU-gated)

Post-DGX-Spark: train Qwen3-8B → Agent-World-8B-EPYC via multi-env GRPO on the arena bootstrapped in Phase 1. Targets: match paper's beat-proprietary claim on ≥5 of our active benchmarks.

## Tasks

### AW-1: Scaffold `env_synth/` module [Phase 1, ~3-4 weeks]

- Create `epyc-orchestrator/scripts/autopilot/species/env_synth/` with:
  - `etd_agent.py` — LLM ReAct agent wrapping `web_search`, `fetch_url`, and MCP-tool enumeration
  - `task_synthesizer.py` — generates verifiable tasks from discovered environments with difficulty controls (easy/medium/hard band targets)
  - `verifier_builder.py` — emits deterministic verification functions (regex, exact_match, f1 with allowlist)
  - `mcp_tool_registry.py` — persistent registry of discovered MCP tools with health checks
- Integrate with existing `program.md` species framework (alongside Seeder/NumericSwarm/PromptForge/StructuralLab)

### AW-2: Wire EnvSynth as 5th species

- Add `env_synth` species to meta-optimizer budget allocation
- Extend `autopilot.py` controller prompt with "### Environment Synthesis" section
- Emit `EnvSynthAction` journal events with `environment_id`, `tool_set`, `synthesized_tasks` fields

### AW-3: Capability-gap diagnosis + weekly rollup

- Parse AR-3 journal for per-suite quality stagnation (no improvement >1pp over last 10 trials)
- Re-prompt ETD with gap descriptors ("need more medium-difficulty math reasoning with tool use")
- Weekly cron: emit rollup of coverage gaps → arena.md

### AW-4: Safety gate — reference-model solvability

- Every synthesized task must be solvable by a reference model (architect_general) before acceptance
- Prevents unsolvable / ambiguous tasks polluting the suite
- Rejection rate should be <20% at steady state (if higher, tune difficulty bands)

### AW-5: Integrate synthesized tasks with EvalTower

- Synthesized tasks enter T1 validation batches only (gold-ring benchmarks stay fixed at T0)
- Track per-task provenance: `discovered_via`, `difficulty_band`, `verifier_type`
- Flag synthesized tasks where >3 models fail for human review (potential bad task)

### AW-6: Bootstrap initial arena [48h inference]

- 48-hour discovery run targeting ≥50 environments / ≥500 tools / ≥500 tasks
- Validate: each task passes AW-4 safety gate, verifier reproducible, difficulty band matches target
- Emit `arena.md` report

### AW-7: Integrate top MCP tools into orchestrator

- Once public Agent-World arena is released (GitHub), adopt top-100 discovered MCP tools
- Register via `tool_policy.py` (per standing policy: only open-source self-hosted tools)
- Cross-ref `orchestration/agent_world_tools.yaml` (new)

### AW-8 (Phase 1.5): Corroboration probe on released Agent-World-8B/14B weights

**Upgraded 2026-04-22 post Tier 2b sweep** from "Optional SFT" / freebie to a mandatory **corroboration probe** before any Phase 2 GPU commit. The paper's "beat proprietary on 23 benchmarks" is UNREPRODUCED in open literature; the 23-suite omits SWE-Bench Verified, GAIA, WebArena Hard, and OSWorld (suite-class cherry-picking).

- Contingent on public weight release by paper authors (1k-env subset + pipeline released Feb 2026; 8B/14B weights unconfirmed)
- If released: download, quantize Q4_K_M GGUF, register as `worker_agent_world` role in `model_registry.yaml`
- Acts as reference model for task solvability (AW-4)
- **New corroboration gate**: run released 8B on SWE-Bench Verified + GAIA (benchmarks the paper OMITTED). If performance diverges meaningfully from same-class open-weight baselines on these omitted benchmarks, downgrade intake-444 and revisit Phase 2 cost-benefit.
- See `/workspace/research/deep-dives/agent-world-environment-synthesis.md` § Tier 2b Contradicting-Evidence Sweep (2026-04-22) for the full rationale.

### AW-9 (Phase 2, GPU-gated): Multi-env GRPO training [deferred]

- Post-DGX-Spark: train Qwen3-8B → Agent-World-8B-EPYC variant via multi-env GRPO
- Target: ≥90% of paper's reported improvements on ≥5 of our benchmarks
- Gate: AW-6 arena size ≥1,000 environments AND ≥10,000 synthesized tasks before training

## Integration Map

| Subsystem | Current state | Interaction with env_synth |
|-----------|---------------|----------------------------|
| Autopilot AR-3 | 4 species (Seeder, NumericSwarm, PromptForge, StructuralLab) | env_synth becomes 5th species; feeds task suites into Seeder's input pool |
| Meta-harness Tier 3 | Deferred outer-loop rebuild | Phase 1 concretizes Tier 3's environment-synthesis direction |
| MCP registry (Qwen-Agent singleton, intake-411) | Pattern documented, not yet deployed | env_synth's `mcp_tool_registry.py` implements the pattern for real |
| EvalTower | Fixed gold-ring + dynamic T1/T2 | T1 gets synthesized-task additions; T0 protected |
| Strategy memory (AP-28) | FAISS-backed with RRF fusion | env_synth species' journal entries feed strategy_store like other species |

## Open Questions

- **Arena-agent reward hacking**: if ETD agent and training agent are same-family, the training agent may overfit to synthesis quirks. Mitigation: cross-family ETD (Qwen for synthesis, Llama/DeepSeek for training)?
- **Verifier quality**: deterministic verifiers are weaker than LLM judges. How much of a problem is this for non-trivial tasks?
- **MCP surface blast radius**: Agent-World references 19,822 tools in the public MCP ecosystem. We can't adopt all; what's the right filter?
- **Task difficulty calibration**: does the "controllable difficulty" claim hold when our reference model is Qwen3-35B-A3B instead of the paper's GPT-5?

## Safety Gates

Per `feedback_dont_dismiss_creative_uses`: synthesized tasks expand the benchmark surface; do not dismiss novel task categories without human review.

Per standing policy (`feedback_opensource_only`): only open-source self-hosted MCP tools. Reject any closed-source tool discovered by ETD.

Per `feedback_incremental_persistence`: task suites must be persisted incrementally during 48h bootstrap (AW-6), not only at completion.

## Cross-references

- `autopilot-continuous-optimization.md` P17 (pointer entry)
- `meta-harness-optimization.md` Tier 3 (concrete recipe pointer)
- `routing-and-optimization-index.md` P17
- `wiki/autonomous-research.md` (updated 2026-04-22 with environment-synthesis dimension)
- Intake sources: 444 (primary), 411 (MCP pattern), 412 (DeepPlanning benchmark methodology)

## Tier 2b Contradicting-Evidence Flag

The "beat-proprietary on 23 benchmarks" claim needs corroboration:
- Benchmark selection may be cherry-picked for Agent-World strengths
- Same-family ETD-and-training risk (noted above)
- No independent replication yet

Before committing to Phase 2 training, run WebSearch for "Agent-World reproduction" / "Agent-World criticism".
