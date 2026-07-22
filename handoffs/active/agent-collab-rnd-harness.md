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
- [`kernel-reconciliation-audit.md`](../completed/kernel-reconciliation-audit.md) / [`v6-iqk-promotion.md`](../completed/v6-iqk-promotion.md) — current experimental-kernel (v7-candidate) workflow.
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


## Research-intake integration — 2026-07-22 (R&D-harness patterns from orx / HyRA / OpenHyra)
_Via /research-intake Stage-2 (intake-882/883 orx, intake-884 HyRA, intake-885 OpenHyra). NOTE: the HyRA/OpenHyra R&D-harness descriptor + scoring items were routed here rather than to meta-harness-optimization.md, which forbids new task checkboxes (compatibility pointer)._
- [x] Compare OpenHyra's all-outcomes Experience Bank + LLM Context-Agent cross-round memory (`eb.py`, `context_agent.py`) against StructuralLab / agent-collab archive design ✅ 2026-07-22
- [x] Adopt a uniform per-task descriptor {seed/baseline solution, run script -> solution.json, fixed objective scorer, always-valid fallback} for the R&D harness (HyRA cross-domain contract) ✅ 2026-07-22
- [ ] Feature-mine OpenHyra's trusted-evaluator-outside-sandbox + anti-TOCTOU immutable-snapshot scoring (`sandbox.py:80-134,255`) as a reusable scoring-integrity pattern (general R&D-harness version of the C6 kernel-loop item in [rocm-verify-profile-backend.md](rocm-verify-profile-backend.md))
- [ ] (Optional spike, gate on operator interest) Point orx at EPYC's llama.cpp via OpenCode as a DISPOSABLE test vehicle (`--backend local`, custom OpenAI provider in `~/.config/opencode/opencode.json`) to validate the loop end-to-end. NOT a harness commitment — mining orx's patterns is unconditional and re-targeting to our eventual chosen harness is ~1 `impl Harness` file (`src/local/harness/mod.rs:1135`). Gate any long-term harness choice on [harness-selection-and-integration.md](harness-selection-and-integration.md)
- [ ] (Optional spike) Add a 3rd OpenHyra llm_backend adapter (~30-60 LOC) targeting a local OpenAI-compatible coding agent -> llama.cpp; needs `OPENHYRA_ALLOW_UNSANDBOXED=1` + an external container (sandbox is macOS-only)
