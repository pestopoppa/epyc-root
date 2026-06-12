# Meta-Harness: Automated Harness Optimization

**Status**: COMPACTED 2026-05-28; J9 validation closed 2026-06-12 - active work is MH-6/7/9.
**Created**: 2026-04-01
**Updated**: 2026-06-12
**Priority**: MEDIUM
**Categories**: agent_architecture, benchmark_methodology
**Parent index**: [routing-and-optimization-index.md](routing-and-optimization-index.md)
**Completed ledger**: [meta-harness-optimization-completed-through-2026-05-28.md](../completed/meta-harness-optimization-completed-through-2026-05-28.md)

## Executor Start Here

Do not rebuild the full Meta-Harness outer loop now. The useful next work is targeted: improve PromptForge's proposer contract and trace inputs. The first observe-only harness metric validation pass is complete and did not justify letting current rule metrics affect acceptance or Pareto selection.

## Outstanding Tasks

- [ ] **MH-6 proposer-prior template**: adopt the SKILL.md proposer-prior template in `prompt_forge.py`; include explicit read order, `expected_cost_delta`, `expected_quality_delta`, and a no-task-specific-hints clause.
- [ ] **MH-7 contrastive traces**: upgrade `eval_tower.capture_recent_traces()` to `capture_contrastive_traces(k_success=2, k_failure=2)` once MH-6 can absorb richer inputs.
- [ ] **MH-9 new-file mutation type**: add directory-scoped `new_file` mutation support after MH-6/7 define the cost/quality contract; include traversal and collision tests.
- [x] **HLE-3 / J9 fixed-model harness lane**: observe-only analysis closed 2026-06-12 over 580 metric-bearing trials from `/mnt/raid0/llm/tmp/autopilot_journal_snapshot_1781290411.jsonl`. `execution_fidelity` and `planning_stability` separate keep/revert but mostly mirror existing task-quality/safety signals, so they remain diagnostic/advisory. `feedback_interpretation`, `memory_coherence`, and `recovery_rate` stay dashboard-only. No HLE metric is eligible for Pareto promotion before N2 ledger/sequential verdict redesign.
- [ ] **SkillOpt / EV-10 coordination**: keep the skill-efficacy gate work in [eval-tower-verification.md](eval-tower-verification.md) and the next AR-3 restart plan; do not mix it into MH-6/7/9 without an explicit feature flag.

## Dependency Forks

| Outcome | Next action |
|---|---|
| HLE metrics separate accepted vs rejected configs and missingness <=20% | Eligible for HLE-4 promotion as guardrail/co-objective in [autopilot-continuous-optimization.md](autopilot-continuous-optimization.md) only if they also show independent predictive signal after N2 ledger/sequential verdict redesign. |
| HLE metrics show no signal or high missingness | Keep dashboard-only; never use as a hard gate. |
| MH-6 improves proposer discipline without regressions | Proceed to MH-7 contrastive traces. |
| MH-7 trace volume hurts cost or proposer quality | Keep raw recent traces as fallback and tune `k_success/k_failure`. |
| MH-9 new-file mutations create safety or review overhead | Keep edit-only allowlist until a stronger isolation story exists. |

## Completed Scope

| Scope | Result | Ledger |
|---|---|---|
| Tier 1 execution-trace feedback | Landed. | [completed ledger](../completed/meta-harness-optimization-completed-through-2026-05-28.md) |
| Tier 2 code mutation search space | Landed with allowlist, syntax validation, rollback, safety gate, and simplicity criterion. | [completed ledger](../completed/meta-harness-optimization-completed-through-2026-05-28.md) |
| MH-4 GEPA search eval | Folded into AR-3 Package D. | [completed ledger](../completed/meta-harness-optimization-completed-through-2026-05-28.md) |
| MH-5 Agent Lightning telemetry pattern | Landed as `TelemetryCollector`/OTLP-compatible records. | [completed ledger](../completed/meta-harness-optimization-completed-through-2026-05-28.md) |
| HLE-1/HLE-2 observe-only fields | Schema and rule-based defaults landed in orchestrator commits `931e43c` and `9222a19`; J9 analysis closed 2026-06-12 with diagnostic-only verdict. | [completed ledger](../completed/meta-harness-optimization-completed-through-2026-05-28.md) |

## Key Files

- `/mnt/raid0/llm/epyc-orchestrator/scripts/autopilot/species/prompt_forge.py`
- `/mnt/raid0/llm/epyc-orchestrator/scripts/autopilot/eval_tower.py`
- `/mnt/raid0/llm/epyc-orchestrator/scripts/autopilot/hle_metrics.py`
- [autopilot-continuous-optimization.md](autopilot-continuous-optimization.md)
- [bulk-inference-campaign.md](bulk-inference-campaign.md)
- [eval-tower-verification.md](eval-tower-verification.md)
- [unified-trace-memory-service.md](unified-trace-memory-service.md)

## Reporting Instructions

After MH or HLE work, update this handoff with the code path, feature flag, validation command, observe-only result, and promotion/parking decision. Mirror priority changes in [routing-and-optimization-index.md](routing-and-optimization-index.md), Package J in [bulk-inference-campaign.md](bulk-inference-campaign.md), and [master-handoff-index.md](master-handoff-index.md) if queue priority changes.
