# EPYC Repo Readiness Remediation Queue

Generated: `2026-08-25T13:36:40.264921+00:00`
Queue version: `1`
Total open items: `6`

This queue is advisory input for planning and dashboards. It is not an
AutoPilot authority gate; every item still requires normal handoff ownership,
GitNexus impact checks, implementation validation, and operator policy gates
where applicable.

| Priority | Repo | Current level | Next gate | Criterion | Pillar | Blocking next gate | Acceptance |
|---|---|---:|---|---|---|---|---|
| P0 | epyc-llama | L4 Optimized | L5 Autonomous | `L5.autonomous_runner` | Build System | yes | `L5.autonomous_runner` passes for `epyc-llama` on the next repo readiness scorer run. |
| P0 | epyc-llama | L4 Optimized | L5 Autonomous | `L5.auto_eval_gates` | Testing | yes | `L5.auto_eval_gates` passes for `epyc-llama` on the next repo readiness scorer run. |
| P0 | epyc-llama | L4 Optimized | L5 Autonomous | `L5.self_healing_ops` | Dev Environment | yes | `L5.self_healing_ops` passes for `epyc-llama` on the next repo readiness scorer run. |
| P0 | epyc-llama | L4 Optimized | L5 Autonomous | `L5.closed_loop_obs` | Debugging & Observability | yes | `L5.closed_loop_obs` passes for `epyc-llama` on the next repo readiness scorer run. |
| P0 | epyc-llama | L4 Optimized | L5 Autonomous | `L5.autonomous_security_review` | Security | yes | `L5.autonomous_security_review` passes for `epyc-llama` on the next repo readiness scorer run. |
| P0 | epyc-llama | L4 Optimized | L5 Autonomous | `L5.self_optimizing_loop` | Product & Experimentation | yes | `L5.self_optimizing_loop` passes for `epyc-llama` on the next repo readiness scorer run. |

## Pickup Rules

- Prefer P0 items that unblock the current repo's next maturity gate.
- Keep generated or runtime artifacts out of remediation commits unless the
  owning handoff says they are durable evidence.
- Do not wire this queue into live AutoPilot behavior without a separate
  protocol and explicit default-off integration gate.
