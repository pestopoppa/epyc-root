# EPYC Repo Readiness Remediation Queue

Generated: `2026-06-20T11:21:45.948728+00:00`
Queue version: `1`
Total open items: `49`

This queue is advisory input for planning and dashboards. It is not an
AutoPilot authority gate; every item still requires normal handoff ownership,
GitNexus impact checks, implementation validation, and operator policy gates
where applicable.

| Priority | Repo | Criterion | Level | Pillar | Blocking next gate | Acceptance |
|---|---|---|---:|---|---|---|
| P0 | epyc-inference-research | `L3.style_enforced` | 3 | Style & Validation | yes | `L3.style_enforced` passes for `epyc-inference-research` on the next repo readiness scorer run. |
| P0 | epyc-inference-research | `L3.test_automation` | 3 | Testing | yes | `L3.test_automation` passes for `epyc-inference-research` on the next repo readiness scorer run. |
| P0 | epyc-llama | `L3.structured_experiments` | 3 | Product & Experimentation | yes | `L3.structured_experiments` passes for `epyc-llama` on the next repo readiness scorer run. |
| P0 | epyc-inference-research | `L3.machine_task_index` | 3 | Task Discovery | yes | `L3.machine_task_index` passes for `epyc-inference-research` on the next repo readiness scorer run. |
| P0 | epyc-llama | `L3.machine_task_index` | 3 | Task Discovery | yes | `L3.machine_task_index` passes for `epyc-llama` on the next repo readiness scorer run. |
| P0 | epyc-inference-research | `L3.standard_dev_env` | 3 | Dev Environment | yes | `L3.standard_dev_env` passes for `epyc-inference-research` on the next repo readiness scorer run. |
| P0 | epyc-llama | `L3.standard_dev_env` | 3 | Dev Environment | yes | `L3.standard_dev_env` passes for `epyc-llama` on the next repo readiness scorer run. |
| P0 | epyc-orchestrator | `L3.standard_dev_env` | 3 | Dev Environment | yes | `L3.standard_dev_env` passes for `epyc-orchestrator` on the next repo readiness scorer run. |
| P0 | epyc-inference-research | `L3.security_automation` | 3 | Security | yes | `L3.security_automation` passes for `epyc-inference-research` on the next repo readiness scorer run. |
| P0 | epyc-llama | `L3.security_automation` | 3 | Security | yes | `L3.security_automation` passes for `epyc-llama` on the next repo readiness scorer run. |
| P0 | epyc-orchestrator | `L3.security_automation` | 3 | Security | yes | `L3.security_automation` passes for `epyc-orchestrator` on the next repo readiness scorer run. |
| P0 | epyc-root | `L5.auto_eval_gates` | 5 | Testing | yes | `L5.auto_eval_gates` passes for `epyc-root` on the next repo readiness scorer run. |
| P0 | epyc-root | `L5.self_optimizing_loop` | 5 | Product & Experimentation | yes | `L5.self_optimizing_loop` passes for `epyc-root` on the next repo readiness scorer run. |
| P1 | epyc-llama | `L1.experiment_surface` | 1 | Product & Experimentation | no | `L1.experiment_surface` passes for `epyc-llama` on the next repo readiness scorer run. |
| P1 | epyc-inference-research | `L1.setup_surface` | 1 | Dev Environment | no | `L1.setup_surface` passes for `epyc-inference-research` on the next repo readiness scorer run. |
| P1 | epyc-orchestrator | `L1.setup_surface` | 1 | Dev Environment | no | `L1.setup_surface` passes for `epyc-orchestrator` on the next repo readiness scorer run. |
| P2 | epyc-llama | `L4.replay_analysis` | 4 | Product & Experimentation | no | `L4.replay_analysis` passes for `epyc-llama` on the next repo readiness scorer run. |
| P2 | epyc-inference-research | `L4.analysis_reports` | 4 | Debugging & Observability | no | `L4.analysis_reports` passes for `epyc-inference-research` on the next repo readiness scorer run. |
| P2 | epyc-llama | `L4.analysis_reports` | 4 | Debugging & Observability | no | `L4.analysis_reports` passes for `epyc-llama` on the next repo readiness scorer run. |
| P2 | epyc-inference-research | `L4.generated_docs` | 4 | Documentation | no | `L4.generated_docs` passes for `epyc-inference-research` on the next repo readiness scorer run. |

_Showing first 20 items; see the JSON queue for the full list._

## Pickup Rules

- Prefer P0 items that unblock the current repo's next maturity gate.
- Keep generated or runtime artifacts out of remediation commits unless the
  owning handoff says they are durable evidence.
- Do not wire this queue into live AutoPilot behavior without a separate
  protocol and explicit default-off integration gate.
