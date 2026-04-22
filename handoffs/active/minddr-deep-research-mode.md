# MindDR Deep Research Mode

**Status**: stub / in-planning (Phase 1 prompt-level only; Phase 2 GPU-gated; Phase 3 conditional)
**Created**: 2026-04-22 (split from `routing-intelligence.md` per deep-dive integration pass)
**Categories**: agent_architecture, routing_intelligence, training_distillation
**Priority**: MEDIUM (Phase 1 zero-infra; Phase 2/3 deferred)
**Depends on**: `routing-intelligence.md` (classifier infrastructure), `eval-tower-verification.md` EV-9 (multi-dimensional rubric)

## Objective

Adopt MindDR's three-agent role-specialization pattern (Planning + DeepSearch + Report) as a `deep_research_mode` in the EPYC orchestrator. Phase 1 is prompt-level only — zero-infra, falsifiable under the existing eval tower, and expected to deliver ≥+5pp quality uplift on research-like queries vs current direct-answer mode. Phase 2 adds the paper's four-stage RL recipe (SFT → Search-RL → Report-RL → preference alignment) when DGX Spark becomes available. Phase 3 conditionally refactors the orchestrator's Tier-B architect split into a role-by-pipeline-stage architecture if Phase 1 uplift proves durable.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-438 | Mind DeepResearch Technical Report (arxiv:2604.14518, Li Auto) | high | worth_investigating |
| intake-412 | DeepPlanning agent benchmark | medium | adopt_patterns |
| intake-444 | Agent-World environment synthesis | medium | cross-ref (same meta-harness space) |

**Source deep dive**: [`/workspace/research/deep-dives/minddr-multi-agent-rl-specialization.md`](../../research/deep-dives/minddr-multi-agent-rl-specialization.md) (442 lines)

## Key Claims (from MindDR paper)

- Multi-agent framework (Planning + DeepSearch + Report) achieves competitive deep research at ~30B scale.
- Four-stage training (SFT cold-start + Search-RL with GSPO/GRPO + Report-RL with DAPO + preference alignment via DPO + Self-SFT) is the recipe.
- Multi-dimensional rubric evaluation (reasoning trajectory, tool calls, outline, content) is superior to single RACE metric.
- Production deployment at Li Auto validates the architecture at scale.
- BrowseComp-ZH 45.7%, WideSearch 46.5%, xbench-DS 75.0%, MindDR Bench 51.8 (SOTA).

## Phased Adoption

### Phase 1 — Prompt-level three-agent pipeline (zero-infra, CPU-feasible today)

Add a `deep_research_mode` feature flag. When enabled AND query matches the "research-like" classifier signal, route through a three-stage pydantic_graph pipeline:

1. **PlanningNode** (architect_general with task-decomposition system prompt) → produces outline of sub-questions
2. **DeepSearchFanOutNode** (frontdoor with ReAct-search system prompt; parallel fan-out per sub-question) → collects evidence
3. **ReportSynthesisNode** (worker_explore with outline-first citation-grounded system prompt) → synthesizes final report

Success criterion: ≥+5pp quality uplift on 20-40 research-like sentinel queries vs current direct-answer mode, no regression elsewhere, no tool-call explosion (>2× baseline).

### Phase 2 — Four-stage RL specialization (GPU-gated, deferred)

Post-DGX-Spark: implement MindDR's four-stage training recipe on Qwen3-32B or Qwen3-30B-A3B backbone. Requires AReaL async RL runner (or equivalent).

### Phase 3 — Architectural refactor (conditional on Phase 1 success)

If Phase 1 delivers ≥5pp durable uplift AND if pipeline-stage specialization shows value beyond role-type specialization (architect_general vs architect_coding), refactor into dedicated `architect_planning`, `architect_search`, `architect_report` roles.

## Tasks

### Phase 1 tasks (MD-1..MD-9)

**MD-1: Design `deep_research_mode` feature flag** [2h] — **DONE 2026-04-22 (NIB2-45)**. `features.py` gained `deep_research_mode: bool = False` + FeatureSpec; env override `ORCHESTRATOR_DEEP_RESEARCH_MODE=1`. Wiring into the routing decision itself is a 1-line check in the request dispatcher (see MD-6 note below); the flag machinery is ready.

**MD-2: Extend Category A classifier for "research-like" query detection** [2h] — **DONE 2026-04-22**. `orchestration/classifier_config.yaml` gained `research_like` exemplars (7 seed prompts). `src/classifiers/research_like.py` provides dep-free `is_research_like()` + `score_research_like()`. MemRL-based Q-value learning path (via existing `ClassificationRetriever`) remains available for future refinement.

**MD-3/4/5: Three agent prompts** — **DONE 2026-04-22**. `orchestration/prompts/planning_agent.md` (3-7 sub-questions, evidence tags WEB/CITATION/BENCHMARK/DOCS/COMPARISON), `deep_search_agent.md` (ReAct with `[src:<ref>]` citation contract + Sub-Report block schema), `report_agent.md` (outline-first synthesis, citation preservation, explicit Gaps section).

**MD-6: Implement pydantic_graph flow** [3 weeks] — **DONE 2026-04-22**. New standalone subpackage `src/graph/minddr/` (decoupled from production `src/graph/` orchestration graph):
- `state.py` — `MindDRState`, `MindDRDeps` (injectable LLM callables), `MindDRResult`, `SubQuestion`, `SubReport`, `EvidenceTag`.
- `parsing.py` — `parse_planning_output` (tag filtering / index dedup / max-N clamp) + `parse_sub_report` (graceful field extraction + indented-evidence scanner).
- `nodes.py` — `PlanningNode`, `DeepSearchFanOutNode` (asyncio.gather bounded by `max_parallel` semaphore, per-question graceful degradation), `ReportSynthesisNode`.
- `graph.py` — `minddr_graph` Graph singleton + `run_minddr()` entry point + `load_minddr_prompts()` disk loader.
- Request-dispatcher wiring (feature_flag && is_research_like → run_minddr else existing path) is a 1-line check — intentionally deferred so inference-side testing can land independently.

**MD-7: Extend EvalTower with multi-dimensional rubric** [2 weeks, handed to `eval-tower-verification.md` EV-9] — **STUB DONE 2026-04-22**. `EvalResult` gained four NaN-safe rubric fields (`rubric_reasoning_trajectory`, `rubric_tool_calls`, `rubric_outline`, `rubric_content_stage`). LLM-as-judge scoring functions themselves remain EV-9 and inference-gated.

**MD-8: Create sentinel suite** [3 days] — **DONE 2026-04-22**. `orchestration/deep_research_sentinel.yaml` with 20 curated queries (7 BrowseComp + 7 WideSearch + 6 mixed) each carrying `expected_contains` structural hints for rubric scoring. Every entry passes `is_research_like()` (enforced by test).

**MD-9: A/B test with ≥+5pp success criterion** [1 day inference, **INFERENCE-GATED**] — pending inference window. Run sentinel suite with/without `deep_research_mode`; promote to production default if uplift ≥5pp and no regression.

### Phase 2 tasks (MD-10..MD-13, GPU-gated)

**MD-10: SFT cold-start** [1-2 weeks GPU]
- 15k domain trajectories from research-like queries
- Target: match paper's SFT baseline before Search-RL stage

**MD-11: Search-RL (GSPO/GRPO)** [2-3 weeks GPU]
- 35k synthesized queries (cross-ref `agent-world-env-synthesis.md` Phase 1 output)
- MoE-friendly: use GSPO for architect_coding (REAP-246B) if applicable

**MD-12: Report-RL (DAPO + RACE rubric + citation reward)** [2-3 weeks GPU]
- Citation-grounded reward shaping
- RACE rubric for multi-dimensional reward signal

**MD-13: Preference alignment (DPO + Self-SFT)** [1 week GPU]
- DPO on structured-error corpus from Phase 1 failure cases
- Self-SFT on high-quality Phase 1 outputs

### Phase 3 task (MD-14, conditional)

**MD-14: Architectural refactor** [2-3 weeks]
- Conditional on Phase 1 showing ≥5pp durable uplift over ≥3 weeks
- Refactor architect_general → architect_planning + architect_report dedicated roles
- Update routing classifier + stack templates + orchestrator_stack.py

## Integration Map

| Subsystem | Current state | Interaction with deep_research_mode |
|-----------|---------------|-------------------------------------|
| Routing classifier (Category A) | Exists, shadow mode | Extended with `research_like` category (MD-2) |
| Pipeline architecture (pydantic_graph) | 7 typed nodes | +3 nodes for the three-agent pipeline (MD-6) |
| EvalTower | quality/speed/cost/reliability + ECE/AUC/calibration | +4 rubric dimensions (MD-7, handed to EV-9) |
| Escalation policy | retry-based | unchanged — deep_research_mode runs its own pipeline |
| Strategy memory (AP-28) | Per-species insights | deep_research_mode contributes sub-question → sub-answer mappings |

## Open Questions

- **Is research-like query detection accurate enough at Category A stage?** Shadow mode measurement for 2 weeks before enforce-mode gate.
- **Does Phase 1 uplift persist beyond the sentinel suite?** Need production validation window (e.g., 4 weeks of real user queries if/when multi-user).
- **Does the paper's Search-RL recipe require their specific benchmark data?** If not replicable, Phase 2 may need synthesis from Phase 1 data (cross-ref `agent-world-env-synthesis.md`).
- **GSPO vs GRPO choice**: MoE-friendly optimizer choice is ~15pp per paper. How does this scale to our REAP-246B architect_coding?

## Safety Gates

Per `feedback_handoff_driven_tracking`: all phase transitions require progress/log updates.

Per `feedback_checkpoint_pareto_state`: Phase 2 RL training must save autopilot_state.json checkpoints; lost frontier = lost compute.

Phase 2 GPU training is explicitly gated on DGX Spark acquisition (`project_dgx_spark_target`).

## Cross-references

- `routing-intelligence.md` Phase 7 (pointer entry → this handoff)
- `routing-and-optimization-index.md` P18 (pointer entry)
- `meta-harness-optimization.md` Tier 3 (concrete RL recipe reference)
- `eval-tower-verification.md` EV-9 (multi-dimensional rubric extension — required dependency)
- `agent-world-env-synthesis.md` AW-6 (synthesized tasks feed Phase 2 training data)
- `wiki/agent-architecture.md`, `wiki/routing-intelligence.md`
- Intake sources: 438 (primary), 412 (DeepPlanning benchmark methodology)

## Tier 2b Contradicting-Evidence Flag

- MindDR Bench (51.8 SOTA) is self-curated from Li Auto assistant logs — read as deployment evidence, not generalization evidence
- Public-benchmark numbers (BrowseComp 45.7, WideSearch 46.5, xbench-DS 75.0) are the reliable anchors
- No open-source release of weights or training code located
- Li Auto commercial context: internal benchmark selection may be tuned to their deployment

Before committing to Phase 2 training recipe, run WebSearch for "MindDeepResearch reproduction" / "MindDR Bench criticism".
