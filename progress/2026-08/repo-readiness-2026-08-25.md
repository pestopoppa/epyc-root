# EPYC Repo Readiness Report

Generated: `2026-08-25T13:36:40.264921+00:00`
Unlock threshold: `80.0%`

## Portfolio Summary

- Portfolio level: **Autonomous** (L5)

| Level | Name | Pass rate |
|---:|---|---:|
| 1 | Functional | 100.0% |
| 2 | Documented | 100.0% |
| 3 | Standardized | 100.0% |
| 4 | Optimized | 100.0% |
| 5 | Autonomous | 83.3% |

## Repo Summary

| Repo | Level | Next gate | L1 | L2 | L3 | L4 | L5 |
|---|---|---|---:|---:|---:|---:|---:|
| epyc-root | Autonomous (L5) | complete | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| epyc-orchestrator | Autonomous (L5) | complete | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| epyc-inference-research | Autonomous (L5) | complete | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| epyc-llama | Optimized (L4) | Autonomous | 100.0% | 100.0% | 100.0% | 100.0% | 33.3% |

## Lowest Portfolio Criteria

| Criterion | Level | Pillar | Coverage | Failed repos |
|---|---:|---|---:|---|
| `L5.auto_eval_gates` | 5 | Testing | 75.0% | epyc-llama |
| `L5.autonomous_runner` | 5 | Build System | 75.0% | epyc-llama |
| `L5.autonomous_security_review` | 5 | Security | 75.0% | epyc-llama |
| `L5.closed_loop_obs` | 5 | Debugging & Observability | 75.0% | epyc-llama |
| `L5.self_healing_ops` | 5 | Dev Environment | 75.0% | epyc-llama |
| `L5.self_optimizing_loop` | 5 | Product & Experimentation | 75.0% | epyc-llama |
| `L1.basic_logs` | 1 | Debugging & Observability | 100.0% | - |
| `L1.basic_security` | 1 | Security | 100.0% | - |
| `L1.build_entry` | 1 | Build System | 100.0% | - |
| `L1.experiment_surface` | 1 | Product & Experimentation | 100.0% | - |
| `L1.readme_docs` | 1 | Documentation | 100.0% | - |
| `L1.setup_surface` | 1 | Dev Environment | 100.0% | - |
| `L1.style_config` | 1 | Style & Validation | 100.0% | - |
| `L1.task_surface` | 1 | Task Discovery | 100.0% | - |
| `L1.tests_present` | 1 | Testing | 100.0% | - |

## Per-Repo Blocking Criteria

### epyc-root

All levels meet the unlock threshold.

### epyc-orchestrator

All levels meet the unlock threshold.

### epyc-inference-research

All levels meet the unlock threshold.

### epyc-llama

Next gate: L5 Autonomous

| Criterion | Pillar | Status | Evidence |
|---|---|---|---|
| `L5.agent_guards` | Style & Validation | pass | AGENTS.md |
| `L5.autonomous_runner` | Build System | fail | - |
| `L5.auto_eval_gates` | Testing | fail | - |
| `L5.agent_doc_loop` | Documentation | pass | handoffs/active/master-handoff-index.md |
| `L5.self_healing_ops` | Dev Environment | fail | - |
| `L5.closed_loop_obs` | Debugging & Observability | fail | - |
| `L5.autonomous_security_review` | Security | fail | - |
| `L5.auto_remediation_queue` | Task Discovery | pass | handoffs/active/master-handoff-index.md |
| `L5.self_optimizing_loop` | Product & Experimentation | fail | - |

## Notes

- Criteria are deterministic file/pattern checks, not LLM judgments.
- A pass means the artifact exists; it does not certify quality.
- Failed criteria are intended to seed a remediation queue.
