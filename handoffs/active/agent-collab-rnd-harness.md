# Agent-Collaboration Harness for Kernel/Orchestration R&D

**Status**: stub
**Created**: 2026-07-11 (via research intake, operator-directed: apply collab model to kernel R&D + autopilot harness)
**Categories**: swarm_techniques, autonomous_research, agent_architecture, hardware_optimization

## Objective

Evaluate adopting the HF **agent-collabs** collaboration model (persistent shared workspace + backend-mediated central store + leaderboard + taskforces + layered quality gates + human dashboard) as the *mechanism* for running our **experimental-kernel R&D campaigns** (the v6→v7 optimization work that today runs as ad-hoc dispatched agents with no persistent shared workspace or leaderboard). The Gemma Challenge (intake-798) is structurally almost identical to our own work: a swarm optimizing inference-kernel throughput under a downstream-quality gate. Secondary target: the same substrate could host autopilot's harness-optimization loop as a population rather than a single daemon.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-798 | The Gemma Challenge and the Case for Agent Collabs | high | adopt_patterns |

Related existing work (do NOT duplicate — this stub is about the *collaboration mechanism*, those are the current mechanisms):
- [`meta-harness-optimization.md`](meta-harness-optimization.md) — single-daemon harness optimization (the autopilot-harness target).
- [`autopilot-continuous-optimization.md`](autopilot-continuous-optimization.md) — live autopilot loop.
- [`kernel-reconciliation-audit.md`](../completed/kernel-reconciliation-audit.md) / [`v6-iqk-promotion.md`](v6-iqk-promotion.md) — current experimental-kernel (v7-candidate) workflow.
- [`swarm-dataset-distillation.md`](swarm-dataset-distillation.md) — the other swarm handoff (dataset generation, different objective).
- [`halo-trace-loop-spike.md`](../completed/halo-trace-loop-spike.md) — trace sharing / attribution overlap.

## Open Questions

- Do we run our kernel R&D as isolated agent sessions today, or is there already a shared leaderboard/workspace? (If the latter, this is a smaller delta than it looks.) The collab's central value is the **persistent shared workspace + leaderboard + failed-trace reuse** — worth it only if our campaigns currently repeat dead ends across sessions.
- The Challenge ran on GPU-hosted E4B with challenge-defined gates. Our kernel R&D is CPU-first with `production-kernel immutability` + MEASUREMENT.md gating and a strict "experimental kernels only, never touch production" rule. Does a leaderboard-driven swarm respect those governance rails, or does it invite the exact metric-gaming the Challenge saw (their PPL gate was gamed until MMLU-Pro/GPQA layered on)?
- **Agent Collapse** is the headline risk: agents converged onto a narrow set of axes and *avoided custom quantization, large kernels, and engine changes* — which is precisely where our hardest CPU-kernel wins live. Any swarm we run must incentivize exploration of exactly the avenues their swarm skipped.
- Infra fit: could this reuse the existing handoff-dashboard hub (:8100) + a bucket/artifact store, or does it require the HF Buckets/Spaces/Jobs stack? (`opensource_only` / self-hosted constraint applies — the github.com/huggingface/agent-collabs template is a starting point, not a hosted dependency.)

## Notes

- Concrete transferable patterns from intake-798: layered/rotating quality gates (defeat metric-gaming), taskforces+channels (defeat collapse + message-flood), trace sharing (defeat repeated dead-ends), HITL dashboard to steer agents out of hopeless loops.
- All intake-798 numbers are OBSERVATION-grade (challenge-internal, self-reported); this stub is about the *organizational mechanism*, which does not depend on those numbers.
- Template referenced by the source: `github.com/huggingface/agent-collabs` (external, operator-review only — do not clone/run without approval).
