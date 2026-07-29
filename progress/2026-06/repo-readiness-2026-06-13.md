# EPYC Repo Readiness Report

Generated: `2026-06-13T03:13:13.288201+00:00`
Unlock threshold: `80.0%`

## Portfolio Summary

- Portfolio level: **Documented** (L2)

| Level | Name | Pass rate |
|---:|---|---:|
| 1 | Functional | 91.7% |
| 2 | Documented | 100.0% |
| 3 | Standardized | 66.7% |
| 4 | Optimized | 58.3% |
| 5 | Autonomous | 44.4% |

## Repo Summary

| Repo | Level | Next gate | L1 | L2 | L3 | L4 | L5 |
|---|---|---|---:|---:|---:|---:|---:|
| epyc-root | Optimized (L4) | Autonomous | 100.0% | 100.0% | 100.0% | 100.0% | 77.8% |
| epyc-orchestrator | Documented (L2) | Standardized | 88.9% | 100.0% | 77.8% | 55.6% | 77.8% |
| epyc-inference-research | Documented (L2) | Standardized | 88.9% | 100.0% | 33.3% | 44.4% | 11.1% |
| epyc-llama | Documented (L2) | Standardized | 88.9% | 100.0% | 55.6% | 33.3% | 11.1% |

## Lowest Portfolio Criteria

| Criterion | Level | Pillar | Coverage | Failed repos |
|---|---:|---|---:|---|
| `L3.security_automation` | 3 | Security | 25.0% | epyc-orchestrator, epyc-inference-research, epyc-llama |
| `L3.standard_dev_env` | 3 | Dev Environment | 25.0% | epyc-orchestrator, epyc-inference-research, epyc-llama |
| `L4.generated_docs` | 4 | Documentation | 25.0% | epyc-orchestrator, epyc-inference-research, epyc-llama |
| `L4.health_automation` | 4 | Dev Environment | 25.0% | epyc-orchestrator, epyc-inference-research, epyc-llama |
| `L4.prioritized_tasks` | 4 | Task Discovery | 25.0% | epyc-orchestrator, epyc-inference-research, epyc-llama |
| `L4.security_audit` | 4 | Security | 25.0% | epyc-orchestrator, epyc-inference-research, epyc-llama |
| `L5.agent_doc_loop` | 5 | Documentation | 25.0% | epyc-orchestrator, epyc-inference-research, epyc-llama |
| `L5.auto_eval_gates` | 5 | Testing | 25.0% | epyc-root, epyc-inference-research, epyc-llama |
| `L5.autonomous_security_review` | 5 | Security | 25.0% | epyc-orchestrator, epyc-inference-research, epyc-llama |
| `L5.self_optimizing_loop` | 5 | Product & Experimentation | 25.0% | epyc-root, epyc-inference-research, epyc-llama |
| `L1.setup_surface` | 1 | Dev Environment | 50.0% | epyc-orchestrator, epyc-inference-research |
| `L3.machine_task_index` | 3 | Task Discovery | 50.0% | epyc-inference-research, epyc-llama |
| `L4.analysis_reports` | 4 | Debugging & Observability | 50.0% | epyc-inference-research, epyc-llama |
| `L5.auto_remediation_queue` | 5 | Task Discovery | 50.0% | epyc-inference-research, epyc-llama |
| `L5.autonomous_runner` | 5 | Build System | 50.0% | epyc-inference-research, epyc-llama |

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
| `L5.autonomous_security_review` | Security | pass | handoffs/active/security-review-skill.md, scripts/hooks/pii_precommit.sh |
| `L5.auto_remediation_queue` | Task Discovery | pass | handoffs/active/frontier-f2-self-running-lab.md, handoffs/active/master-handoff-index.md |
| `L5.self_optimizing_loop` | Product & Experimentation | fail | - |

### epyc-orchestrator

Next gate: L3 Standardized

| Criterion | Pillar | Status | Evidence |
|---|---|---|---|
| `L3.style_enforced` | Style & Validation | pass | Makefile |
| `L3.repro_build` | Build System | pass | uv.lock |
| `L3.test_automation` | Testing | pass | Makefile |
| `L3.doc_validation` | Documentation | pass | docs, docs/ARCHITECTURE.md, docs/SETUP.md, docs/autopilot, docs/autopilot/hypervolume_trend.png |
| `L3.standard_dev_env` | Dev Environment | fail | - |
| `L3.structured_obs` | Debugging & Observability | pass | orchestration/instrument_eras.yaml |
| `L3.security_automation` | Security | fail | - |
| `L3.machine_task_index` | Task Discovery | pass | orchestration/autopilot_journal.jsonl |
| `L3.structured_experiments` | Product & Experimentation | pass | data, data/bep_sandbox, data/bep_sandbox/INVALID-apiclobber-results-real-20260526-232621, data/bep_sandbox/INVALID-apiclobber-results-real-20260526-232621/results.jsonl, data/bep_sandbox/INVALID-mockmode-results-real-20260526-230928 |

### epyc-inference-research

Next gate: L3 Standardized

| Criterion | Pillar | Status | Evidence |
|---|---|---|---|
| `L3.style_enforced` | Style & Validation | fail | - |
| `L3.repro_build` | Build System | fail | - |
| `L3.test_automation` | Testing | fail | - |
| `L3.doc_validation` | Documentation | pass | docs, docs/MODEL_MANIFEST.md, docs/chapters, docs/chapters/01-speculative-decoding.md, docs/chapters/02-moe-optimization.md |
| `L3.standard_dev_env` | Dev Environment | fail | - |
| `L3.structured_obs` | Debugging & Observability | pass | scripts/benchmark/analyze_usaco_failures.py, scripts/benchmark/analyze_web_research_baseline.py, scripts/benchmark/attention_matching.py, scripts/benchmark/bench_amd_pace.py, scripts/benchmark/context_generator.py |
| `L3.security_automation` | Security | fail | - |
| `L3.machine_task_index` | Task Discovery | fail | - |
| `L3.structured_experiments` | Product & Experimentation | pass | data, data/all_spec_sweep, data/all_spec_sweep/all_spec_sweep_20260320_011544.csv, data/all_spec_sweep/logs_20260320_011544, data/all_spec_sweep/logs_20260320_011544/arch_122b_q4km_192t_dm16_ps0.log |

### epyc-llama

Next gate: L3 Standardized

| Criterion | Pillar | Status | Evidence |
|---|---|---|---|
| `L3.style_enforced` | Style & Validation | pass | .github/workflows/ai-issues.yml, .github/workflows/bench.yml.disabled, .github/workflows/build.yml, .github/workflows/check-vendor.yml, .github/workflows/close-issue.yml |
| `L3.repro_build` | Build System | pass | CMakePresets.json, poetry.lock |
| `L3.test_automation` | Testing | pass | .github/workflows/ai-issues.yml, .github/workflows/bench.yml.disabled, .github/workflows/build.yml, .github/workflows/check-vendor.yml, .github/workflows/close-issue.yml |
| `L3.doc_validation` | Documentation | pass | docs, docs/android, docs/android.md, docs/android/imported-into-android-studio.jpg, docs/autoparser.md |
| `L3.standard_dev_env` | Dev Environment | fail | - |
| `L3.structured_obs` | Debugging & Observability | pass | scripts/compare-llama-bench.py, scripts/jinja/jinja-tester.py, scripts/tool_bench.py |
| `L3.security_automation` | Security | fail | - |
| `L3.machine_task_index` | Task Discovery | fail | - |
| `L3.structured_experiments` | Product & Experimentation | fail | - |

## Notes

- Criteria are deterministic file/pattern checks, not LLM judgments.
- A pass means the artifact exists; it does not certify quality.
- Failed criteria are intended to seed a remediation queue.
