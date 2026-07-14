# MindDR Deep Research Mode

**Status**: REFRESHED 2026-05-28 — Phase 1 scaffold landed; MD-9 A/B is the live gate; Phase 2 GPU-gated and Phase 3 conditional
**Created**: 2026-04-22 (split from `routing-intelligence.md` per deep-dive integration pass)
**Updated**: 2026-05-28 (executor gate clarified after MD-1..MD-8 landed)
**Categories**: agent_architecture, routing_intelligence, training_distillation
**Priority**: MEDIUM (Phase 1 zero-infra; Phase 2/3 deferred)
**Depends on**: `routing-intelligence.md` (classifier infrastructure), `eval-tower-verification.md` EV-9 (multi-dimensional rubric)
**Sibling (same gate, lighter weight)**: [`gpu-cot-scaffold-sidecar.md`](../completed/gpu-cot-scaffold-sidecar.md) — its **G1** ("does an injected CoT scaffold beat a code worker's own thinking, per token?") is **MD-9 one weight down**. Both live in the **reasoning-economics cluster** (`research-evaluation-index.md`) and must share the EV-9 DRACO/MindDR scoring contract + token-normalization, not re-derive them.

## 2026-05-28 Audit Reset — Executor Start Here

Phase 1 is no longer a stub. The flag, classifier, prompts, pydantic_graph subpackage, rubric fields, and sentinel suite are already in place. The remaining question is whether the pipeline beats direct-answer mode enough to justify production dispatcher wiring.

| Current gate | Executor rule |
|---|---|
| MD-9 A/B | Run the `deep_research_sentinel.yaml` suite with `ORCHESTRATOR_DEEP_RESEARCH_MODE=0` and `=1`; use EV-9 rubric scoring if available. |
| EV-9 not implemented | Use the structural `expected_contains` hints as a fallback only; label the result "structural-only" and do not promote default-on from that alone. |
| Web/search backend unavailable | Hold MD-9. A three-agent research pipeline without evidence retrieval is not the paper's claim. |
| Dispatcher wiring | Keep deferred until MD-9 passes; the current graph is intentionally decoupled from production request handling. |

Promotion rule:

- Promote to production default only if aggregate rubric uplift is >= +5 percentage points, existing eval-tower sentinels do not regress, and tool calls stay <= 2x baseline.
- Leave flag default-off if uplift <= 0, if rubric gains come only from longer answers, or if tool-call growth exceeds the cap.
- Phase 2 RL work is unmotivated until Phase 1 shows a durable non-RL gain.

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

Phase 2 GPU training (MD-10..13) is gated on **MI210/gfx90a training viability** (re-gated 2026-07-14). The prior "DGX Spark acquisition" gate is dead — DGX was never bought; an AMD MI210 (gfx90a, 64GB, ROCm 6.2) was installed 2026-07-02. The gate is now the pending training-viability smoke against gfx90a, not a hardware-acquisition wait.

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

## Research Intake Update — 2026-07-08: PaperBench Source-Fidelity (rec-006)

**Source**: PaperBench (intake-795)

**Key finding**: PaperBench benchmarks model ability to understand and reproduce research papers. Methodology may be transferable to our deep-research pipeline for validating that our agent-generated research artifacts are faithful to source material.

**Applicability to EPYC**: Our MindDR pipeline produces synthesized reports from multi-agent research. PaperBench-style validation could serve as a quality gate for the ReportSynthesisNode, ensuring the final report is faithful to the collected evidence. Particularly relevant for Phase 2 RL training where citation-grounded reward shaping is critical.

**Action**: Monitor PaperBench development; evaluate as a source-fidelity validation gate for our deep-research reports.

- [ ] **MD-PB-1** — evaluate PaperBench methodology for source-fidelity validation of deep-research reports
- [ ] **MD-PB-2** — consider integrating PaperBench-style evaluation into MD-9 A/B test rubric

## Progress checklist

- [x] MD-1..MD-8 Phase 1 scaffold (flag, classifier, prompts, pydantic_graph, rubric, sentinel suite - DONE 2026-04-22) ✅
- [ ] MD-9 A/B test sentinel suite with deep_research_mode 0/1 (>=+5pp gate, INFERENCE-GATED)
- [ ] Request-dispatcher 1-line wiring (feature_flag && is_research_like -> run_minddr) once MD-9 passes
- [ ] EV-9 multi-dimensional rubric scoring (handed to eval-tower; needed for non-structural MD-9)
- [ ] Phase 2 MD-10..MD-13 four-stage RL (GPU-gated, deferred)
- [ ] Phase 3 MD-14 architect role refactor (conditional on durable >=5pp uplift)

## Research Intake Update — 2026-07-11

### New Related Research
- **[intake-810] "RubricEM: Meta-RL with Rubric-guided Policy Decomposition beyond Verifiable Rewards"** (arxiv:2605.10899; Google Cloud AI + UIUC)
  - Relevance: same **four-stage Plan→Research→Review→Answer** scaffold this handoff uses, but treats **rubrics as the shared interface** structuring policy execution, judge feedback, AND agent memory (a reusable **rubric bank**) — not just a final-answer scorer. Directly informs MD-9 non-structural scoring + the EV-9 rubric contract.
  - Adoptable now (zero-training, Phase-1 style): rubric-as-interface framing + stage-specific reward decomposition + reflection/rubric-bank memory. **Not** adoptable: the RL core (SS-GRPO + reflection meta-policy training) needs GPU training infra we lack — aligns with this handoff's Phase-2 MD-10..13 being GPU-gated/deferred.
  - Reported (OBSERVATION-grade): RubricEM-8B long-form avg 55.5 (beats DR Tulu-8B 53.6, approaches OpenAI Deep Research 59.9 at far fewer params); short-form OOD avg 73.5. Heavy overlap with already-indexed MindDR (intake-438).
- [ ] Operator-review candidate (deep-dive 2026-07-11 SHARPENED): **PRIMARY (prompt-level, genuinely new):** rubric-as-**execution**-interface — PlanningNode emits a prospective `<rubrics>` block; DeepSearch loop does per-step `<state_evaluation>` vs rubric; add a **Review stage** (`<rubric_review>` mapping evidence→criteria before ReportSynthesis) — the *sole* scaffold delta vs our 3-node pipeline — plus a Review-stage rubric-adherence EV-9 dimension. **Note:** stage-decomposed *scoring* is already in EV-9 (`rubric_scoring.py`); only SS-GRPO's per-stage credit-assignment is new and it's **RL/GPU-gated (OUT — duplicates MD-10..13)**. **EXPERIMENTAL (adopt cautiously):** a heuristic kb-search rubric bank over `src/trace` — but the paper's own Fig-6 ablation attributes the transfer gain to the *trained* meta-policy and shows an untrained model doesn't benefit, so treat as a falsifiable experiment, not a free win.
