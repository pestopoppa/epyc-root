# EPYC Repo Readiness Report

Generated: `2026-06-28T16:33:37.892139+00:00`
Unlock threshold: `80.0%`

## Portfolio Summary

- Portfolio level: **Optimized** (L4)

| Level | Name | Pass rate |
|---:|---|---:|
| 1 | Functional | 100.0% |
| 2 | Documented | 100.0% |
| 3 | Standardized | 97.2% |
| 4 | Optimized | 80.6% |
| 5 | Autonomous | 55.6% |

## Repo Summary

| Repo | Level | Next gate | L1 | L2 | L3 | L4 | L5 |
|---|---|---|---:|---:|---:|---:|---:|
| epyc-root | Optimized (L4) | Autonomous | 100.0% | 100.0% | 100.0% | 100.0% | 77.8% |
| epyc-orchestrator | Autonomous (L5) | complete | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| epyc-inference-research | Optimized (L4) | Autonomous | 100.0% | 100.0% | 100.0% | 100.0% | 33.3% |
| epyc-llama | Standardized (L3) | Optimized | 100.0% | 100.0% | 88.9% | 22.2% | 11.1% |

## Lowest Portfolio Criteria

| Criterion | Level | Pillar | Coverage | Failed repos |
|---|---:|---|---:|---|
| `L5.auto_eval_gates` | 5 | Testing | 25.0% | epyc-root, epyc-inference-research, epyc-llama |
| `L5.self_optimizing_loop` | 5 | Product & Experimentation | 25.0% | epyc-root, epyc-inference-research, epyc-llama |
| `L5.autonomous_runner` | 5 | Build System | 50.0% | epyc-inference-research, epyc-llama |
| `L5.autonomous_security_review` | 5 | Security | 50.0% | epyc-inference-research, epyc-llama |
| `L5.closed_loop_obs` | 5 | Debugging & Observability | 50.0% | epyc-inference-research, epyc-llama |
| `L5.self_healing_ops` | 5 | Dev Environment | 50.0% | epyc-inference-research, epyc-llama |
| `L3.machine_task_index` | 3 | Task Discovery | 75.0% | epyc-llama |
| `L4.analysis_reports` | 4 | Debugging & Observability | 75.0% | epyc-llama |
| `L4.generated_docs` | 4 | Documentation | 75.0% | epyc-llama |
| `L4.health_automation` | 4 | Dev Environment | 75.0% | epyc-llama |
| `L4.incremental_validation` | 4 | Style & Validation | 75.0% | epyc-llama |
| `L4.prioritized_tasks` | 4 | Task Discovery | 75.0% | epyc-llama |
| `L4.replay_analysis` | 4 | Product & Experimentation | 75.0% | epyc-llama |
| `L4.security_audit` | 4 | Security | 75.0% | epyc-llama |
| `L5.agent_doc_loop` | 5 | Documentation | 75.0% | epyc-llama |

## Per-Repo Blocking Criteria

### epyc-root

Next gate: L5 Autonomous

| Criterion | Pillar | Status | Evidence |
|---|---|---|---|
| `L5.agent_guards` | Style & Validation | pass | AGENTS.md, scripts/hooks/agents_schema_guard.sh, scripts/hooks/check_filesystem_path.sh |
| `L5.autonomous_runner` | Build System | pass | scripts/nightshift, scripts/nightshift/bin, scripts/nightshift/bin/claude, scripts/nightshift/claude-nightshift, scripts/nightshift/claude_via_devc.sh |
| `L5.auto_eval_gates` | Testing | fail | - |
| `L5.agent_doc_loop` | Documentation | pass | .claude/commands, .claude/commands/agent-files.md, .claude/commands/agent-governance.md, .claude/commands/benchmark.md, .claude/commands/draft-compat.md |
| `L5.self_healing_ops` | Dev Environment | pass | scripts/nightshift/inference_guard.sh, scripts/session/emergency_cleanup.sh |
| `L5.closed_loop_obs` | Debugging & Observability | pass | logs/agent_audit.log, scripts/halo/convert_tap_to_otel.py |
| `L5.autonomous_security_review` | Security | pass | .claude/skills/security-review, .claude/skills/security-review/SKILL.md, .claude/skills/security-review/agents, .claude/skills/security-review/agents/openai.yaml, handoffs/active/security-review-skill.md |
| `L5.auto_remediation_queue` | Task Discovery | pass | handoffs/active/frontier-f2-self-running-lab.md, handoffs/active/master-handoff-index.md |
| `L5.self_optimizing_loop` | Product & Experimentation | fail | - |

### epyc-orchestrator

All levels meet the unlock threshold.

### epyc-inference-research

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
| `L4.prioritized_tasks` | Task Discovery | fail | - |
| `L4.replay_analysis` | Product & Experimentation | fail | - |

## Notes

- Criteria are deterministic file/pattern checks, not LLM judgments.
- A pass means the artifact exists; it does not certify quality.
- Failed criteria are intended to seed a remediation queue.
