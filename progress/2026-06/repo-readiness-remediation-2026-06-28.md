# EPYC Repo Readiness Remediation Queue

Generated: `2026-06-28T16:12:19.651626+00:00`
Queue version: `1`
Total open items: `28`

This queue is advisory input for planning and dashboards. It is not an
AutoPilot authority gate; every item still requires normal handoff ownership,
GitNexus impact checks, implementation validation, and operator policy gates
where applicable.

| Priority | Repo | Criterion | Level | Pillar | Blocking next gate | Acceptance |
|---|---|---|---:|---|---|---|
| P0 | epyc-llama | `L3.standard_dev_env` | 3 | Dev Environment | yes | `L3.standard_dev_env` passes for `epyc-llama` on the next repo readiness scorer run. |
| P0 | epyc-llama | `L3.security_automation` | 3 | Security | yes | `L3.security_automation` passes for `epyc-llama` on the next repo readiness scorer run. |
| P0 | epyc-llama | `L3.machine_task_index` | 3 | Task Discovery | yes | `L3.machine_task_index` passes for `epyc-llama` on the next repo readiness scorer run. |
| P0 | epyc-llama | `L3.structured_experiments` | 3 | Product & Experimentation | yes | `L3.structured_experiments` passes for `epyc-llama` on the next repo readiness scorer run. |
| P0 | epyc-inference-research | `L5.autonomous_runner` | 5 | Build System | yes | `L5.autonomous_runner` passes for `epyc-inference-research` on the next repo readiness scorer run. |
| P0 | epyc-inference-research | `L5.self_healing_ops` | 5 | Dev Environment | yes | `L5.self_healing_ops` passes for `epyc-inference-research` on the next repo readiness scorer run. |
| P0 | epyc-inference-research | `L5.closed_loop_obs` | 5 | Debugging & Observability | yes | `L5.closed_loop_obs` passes for `epyc-inference-research` on the next repo readiness scorer run. |
| P0 | epyc-inference-research | `L5.autonomous_security_review` | 5 | Security | yes | `L5.autonomous_security_review` passes for `epyc-inference-research` on the next repo readiness scorer run. |
| P0 | epyc-inference-research | `L5.auto_eval_gates` | 5 | Testing | yes | `L5.auto_eval_gates` passes for `epyc-inference-research` on the next repo readiness scorer run. |
| P0 | epyc-root | `L5.auto_eval_gates` | 5 | Testing | yes | `L5.auto_eval_gates` passes for `epyc-root` on the next repo readiness scorer run. |
| P0 | epyc-inference-research | `L5.self_optimizing_loop` | 5 | Product & Experimentation | yes | `L5.self_optimizing_loop` passes for `epyc-inference-research` on the next repo readiness scorer run. |
| P0 | epyc-root | `L5.self_optimizing_loop` | 5 | Product & Experimentation | yes | `L5.self_optimizing_loop` passes for `epyc-root` on the next repo readiness scorer run. |
| P1 | epyc-llama | `L1.experiment_surface` | 1 | Product & Experimentation | no | `L1.experiment_surface` passes for `epyc-llama` on the next repo readiness scorer run. |
| P2 | epyc-llama | `L4.incremental_validation` | 4 | Style & Validation | no | `L4.incremental_validation` passes for `epyc-llama` on the next repo readiness scorer run. |
| P2 | epyc-llama | `L4.generated_docs` | 4 | Documentation | no | `L4.generated_docs` passes for `epyc-llama` on the next repo readiness scorer run. |
| P2 | epyc-llama | `L4.health_automation` | 4 | Dev Environment | no | `L4.health_automation` passes for `epyc-llama` on the next repo readiness scorer run. |
| P2 | epyc-llama | `L4.analysis_reports` | 4 | Debugging & Observability | no | `L4.analysis_reports` passes for `epyc-llama` on the next repo readiness scorer run. |
| P2 | epyc-llama | `L4.security_audit` | 4 | Security | no | `L4.security_audit` passes for `epyc-llama` on the next repo readiness scorer run. |
| P2 | epyc-llama | `L4.prioritized_tasks` | 4 | Task Discovery | no | `L4.prioritized_tasks` passes for `epyc-llama` on the next repo readiness scorer run. |
| P2 | epyc-llama | `L4.replay_analysis` | 4 | Product & Experimentation | no | `L4.replay_analysis` passes for `epyc-llama` on the next repo readiness scorer run. |
| P2 | epyc-llama | `L5.agent_doc_loop` | 5 | Documentation | no | `L5.agent_doc_loop` passes for `epyc-llama` on the next repo readiness scorer run. |
| P2 | epyc-llama | `L5.auto_remediation_queue` | 5 | Task Discovery | no | `L5.auto_remediation_queue` passes for `epyc-llama` on the next repo readiness scorer run. |
| P2 | epyc-llama | `L5.autonomous_runner` | 5 | Build System | no | `L5.autonomous_runner` passes for `epyc-llama` on the next repo readiness scorer run. |
| P2 | epyc-llama | `L5.self_healing_ops` | 5 | Dev Environment | no | `L5.self_healing_ops` passes for `epyc-llama` on the next repo readiness scorer run. |
| P2 | epyc-llama | `L5.closed_loop_obs` | 5 | Debugging & Observability | no | `L5.closed_loop_obs` passes for `epyc-llama` on the next repo readiness scorer run. |
| P2 | epyc-llama | `L5.autonomous_security_review` | 5 | Security | no | `L5.autonomous_security_review` passes for `epyc-llama` on the next repo readiness scorer run. |
| P2 | epyc-llama | `L5.auto_eval_gates` | 5 | Testing | no | `L5.auto_eval_gates` passes for `epyc-llama` on the next repo readiness scorer run. |
| P2 | epyc-llama | `L5.self_optimizing_loop` | 5 | Product & Experimentation | no | `L5.self_optimizing_loop` passes for `epyc-llama` on the next repo readiness scorer run. |

## Pickup Rules

- Prefer P0 items that unblock the current repo's next maturity gate.
- Keep generated or runtime artifacts out of remediation commits unless the
  owning handoff says they are durable evidence.
- Do not wire this queue into live AutoPilot behavior without a separate
  protocol and explicit default-off integration gate.
