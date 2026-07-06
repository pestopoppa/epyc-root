# EPYC Repo Readiness Remediation Queue

Generated: `2026-07-06T06:03:23.538500+00:00`
Queue version: `1`
Total open items: `13`

This queue is advisory input for planning and dashboards. It is not an
AutoPilot authority gate; every item still requires normal handoff ownership,
GitNexus impact checks, implementation validation, and operator policy gates
where applicable.

| Priority | Repo | Current level | Next gate | Criterion | Pillar | Blocking next gate | Acceptance |
|---|---|---:|---|---|---|---|---|
| P0 | epyc-llama | L3 Standardized | L4 Optimized | `L4.incremental_validation` | Style & Validation | yes | `L4.incremental_validation` passes for `epyc-llama` on the next repo readiness scorer run. |
| P0 | epyc-llama | L3 Standardized | L4 Optimized | `L4.generated_docs` | Documentation | yes | `L4.generated_docs` passes for `epyc-llama` on the next repo readiness scorer run. |
| P0 | epyc-llama | L3 Standardized | L4 Optimized | `L4.health_automation` | Dev Environment | yes | `L4.health_automation` passes for `epyc-llama` on the next repo readiness scorer run. |
| P0 | epyc-llama | L3 Standardized | L4 Optimized | `L4.analysis_reports` | Debugging & Observability | yes | `L4.analysis_reports` passes for `epyc-llama` on the next repo readiness scorer run. |
| P0 | epyc-llama | L3 Standardized | L4 Optimized | `L4.security_audit` | Security | yes | `L4.security_audit` passes for `epyc-llama` on the next repo readiness scorer run. |
| P0 | epyc-llama | L3 Standardized | L4 Optimized | `L4.replay_analysis` | Product & Experimentation | yes | `L4.replay_analysis` passes for `epyc-llama` on the next repo readiness scorer run. |
| P2 | epyc-llama | L3 Standardized | L4 Optimized | `L5.autonomous_runner` | Build System | no | `L5.autonomous_runner` passes for `epyc-llama` on the next repo readiness scorer run. |
| P2 | epyc-llama | L3 Standardized | L4 Optimized | `L5.auto_eval_gates` | Testing | no | `L5.auto_eval_gates` passes for `epyc-llama` on the next repo readiness scorer run. |
| P2 | epyc-llama | L3 Standardized | L4 Optimized | `L5.self_healing_ops` | Dev Environment | no | `L5.self_healing_ops` passes for `epyc-llama` on the next repo readiness scorer run. |
| P2 | epyc-llama | L3 Standardized | L4 Optimized | `L5.closed_loop_obs` | Debugging & Observability | no | `L5.closed_loop_obs` passes for `epyc-llama` on the next repo readiness scorer run. |
| P2 | epyc-llama | L3 Standardized | L4 Optimized | `L5.autonomous_security_review` | Security | no | `L5.autonomous_security_review` passes for `epyc-llama` on the next repo readiness scorer run. |
| P2 | epyc-llama | L3 Standardized | L4 Optimized | `L5.self_optimizing_loop` | Product & Experimentation | no | `L5.self_optimizing_loop` passes for `epyc-llama` on the next repo readiness scorer run. |
| P2 | epyc-root | L5 Autonomous | complete | `L5.self_optimizing_loop` | Product & Experimentation | no | `L5.self_optimizing_loop` passes for `epyc-root` on the next repo readiness scorer run. |

## Pickup Rules

- Prefer P0 items that unblock the current repo's next maturity gate.
- Keep generated or runtime artifacts out of remediation commits unless the
  owning handoff says they are durable evidence.
- Do not wire this queue into live AutoPilot behavior without a separate
  protocol and explicit default-off integration gate.
