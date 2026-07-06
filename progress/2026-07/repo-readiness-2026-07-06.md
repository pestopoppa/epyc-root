# EPYC Repo Readiness Report

Generated: `2026-07-06T06:03:23.538500+00:00`
Unlock threshold: `80.0%`

## Portfolio Summary

- Portfolio level: **Autonomous** (L5)

| Level | Name | Pass rate |
|---:|---|---:|
| 1 | Functional | 100.0% |
| 2 | Documented | 100.0% |
| 3 | Standardized | 100.0% |
| 4 | Optimized | 83.3% |
| 5 | Autonomous | 80.6% |

## Repo Summary

| Repo | Level | Next gate | L1 | L2 | L3 | L4 | L5 |
|---|---|---|---:|---:|---:|---:|---:|
| epyc-root | Autonomous (L5) | complete | 100.0% | 100.0% | 100.0% | 100.0% | 88.9% |
| epyc-orchestrator | Autonomous (L5) | complete | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| epyc-inference-research | Autonomous (L5) | complete | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| epyc-llama | Standardized (L3) | Optimized | 100.0% | 100.0% | 100.0% | 33.3% | 33.3% |

## Lowest Portfolio Criteria

| Criterion | Level | Pillar | Coverage | Failed repos |
|---|---:|---|---:|---|
| `L5.self_optimizing_loop` | 5 | Product & Experimentation | 50.0% | epyc-root, epyc-llama |
| `L4.analysis_reports` | 4 | Debugging & Observability | 75.0% | epyc-llama |
| `L4.generated_docs` | 4 | Documentation | 75.0% | epyc-llama |
| `L4.health_automation` | 4 | Dev Environment | 75.0% | epyc-llama |
| `L4.incremental_validation` | 4 | Style & Validation | 75.0% | epyc-llama |
| `L4.replay_analysis` | 4 | Product & Experimentation | 75.0% | epyc-llama |
| `L4.security_audit` | 4 | Security | 75.0% | epyc-llama |
| `L5.auto_eval_gates` | 5 | Testing | 75.0% | epyc-llama |
| `L5.autonomous_runner` | 5 | Build System | 75.0% | epyc-llama |
| `L5.autonomous_security_review` | 5 | Security | 75.0% | epyc-llama |
| `L5.closed_loop_obs` | 5 | Debugging & Observability | 75.0% | epyc-llama |
| `L5.self_healing_ops` | 5 | Dev Environment | 75.0% | epyc-llama |
| `L1.basic_logs` | 1 | Debugging & Observability | 100.0% | - |
| `L1.basic_security` | 1 | Security | 100.0% | - |
| `L1.build_entry` | 1 | Build System | 100.0% | - |

## Per-Repo Blocking Criteria

### epyc-root

All levels meet the unlock threshold.

### epyc-orchestrator

All levels meet the unlock threshold.

### epyc-inference-research

All levels meet the unlock threshold.

### epyc-llama

Next gate: L4 Optimized

| Criterion | Pillar | Status | Evidence |
|---|---|---|---|
| `L4.incremental_validation` | Style & Validation | fail | - |
| `L4.build_speed` | Build System | pass | build_libomp_pgo_use, build_libomp_pgo_bolt, build_libomp_pgo_use/tests, build_libomp_pgo_use/Makefile, build_libomp_pgo_use/CTestTestfile.cmake |
| `L4.fast_safe_tests` | Testing | pass | scripts/server-test-parallel-tc.py, scripts/snapdragon/qdc/run_qdc_jobs.py, scripts/snapdragon/qdc/tests/linux/run_linux.sh, scripts/tool_bench.py |
| `L4.generated_docs` | Documentation | fail | - |
| `L4.health_automation` | Dev Environment | fail | - |
| `L4.analysis_reports` | Debugging & Observability | fail | - |
| `L4.security_audit` | Security | fail | - |
| `L4.prioritized_tasks` | Task Discovery | pass | handoffs/active/master-handoff-index.md |
| `L4.replay_analysis` | Product & Experimentation | fail | - |

## Notes

- Criteria are deterministic file/pattern checks, not LLM judgments.
- A pass means the artifact exists; it does not certify quality.
- Failed criteria are intended to seed a remediation queue.
