# Agent-Collaboration Harness for Kernel/Orchestration R&D

**Status**: ACTIVE/PARTIAL — C6 scoring-integrity guard landed 2026-07-22; Phase 2/C4 remain open.
**Created**: 2026-07-11 (via research intake, operator-directed: apply collab model to kernel R&D + autopilot harness)
**Categories**: swarm_techniques, autonomous_research, agent_architecture, hardware_optimization

## Objective

Evaluate adopting the HF **agent-collabs** collaboration model (persistent shared workspace + backend-mediated central store + leaderboard + taskforces + layered quality gates + human dashboard) as the *mechanism* for running our **experimental-kernel R&D campaigns** (the v6→v7 optimization work that today runs as ad-hoc dispatched agents with no persistent shared workspace or leaderboard). The Gemma Challenge (intake-798) is structurally almost identical to our own work: a swarm optimizing inference-kernel throughput under a downstream-quality gate. Secondary target: the same substrate could host autopilot's harness-optimization loop as a population rather than a single daemon.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-798 | The Gemma Challenge and the Case for Agent Collabs | high | adopt_patterns |

Related existing work (do NOT duplicate — this stub is about the *collaboration mechanism*, those are the current mechanisms):
- [`meta-harness-optimization.md`](../completed/meta-harness-optimization.md) — single-daemon harness optimization (the autopilot-harness target).
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
_Via /research-intake Stage-2 (intake-882#record + intake-883#record orx, intake-884#record HyRA, intake-885#record OpenHyra). NOTE: the HyRA/OpenHyra R&D-harness descriptor + scoring items were routed here rather than to the meta-harness completed ledger, which forbids new task checkboxes (the active compatibility pointer was retired 2026-08-23)._
- [x] Compare OpenHyra's all-outcomes Experience Bank + LLM Context-Agent cross-round memory (`eb.py`, `context_agent.py`) against StructuralLab / agent-collab archive design ✅ 2026-07-22
- [x] Adopt a uniform per-task descriptor {seed/baseline solution, run script -> solution.json, fixed objective scorer, always-valid fallback} for the R&D harness (HyRA cross-domain contract) ✅ 2026-07-22
- [x] Feature-mine OpenHyra's trusted-evaluator-outside-sandbox + anti-TOCTOU immutable-snapshot scoring (`sandbox.py:80-134,255`) as a reusable scoring-integrity pattern (general R&D-harness version of the C6 kernel-loop item in [rocm-verify-profile-backend.md](rocm-verify-profile-backend.md)) ✅ 2026-07-22 (research `2d5b1f6e`; `kernel_rnd/c6_reward_integrity.py` and task descriptor)
- [ ] (Optional spike, gate on operator interest) Point orx at EPYC's llama.cpp via OpenCode as a DISPOSABLE test vehicle (`--backend local`, custom OpenAI provider in `~/.config/opencode/opencode.json`) to validate the loop end-to-end. NOT a harness commitment — mining orx's patterns is unconditional and re-targeting to our eventual chosen harness is ~1 `impl Harness` file (`src/local/harness/mod.rs:1135`). Gate any long-term harness choice on [harness-selection-and-integration.md](harness-selection-and-integration.md) **Constraint if ever authorized:** SINGLE-USER only on this shared host (orx's own README states the dashboard binds loopback with no application-level authentication, so other host users can reach it), and built from source (channel development) so telemetry is compile-time disabled. Strip overleaf_live / browser_cookies at import (intake-883#record).
- [ ] (Optional spike) Add a 3rd OpenHyra llm_backend adapter (~30-60 LOC) targeting a local OpenAI-compatible coding agent -> llama.cpp; needs `OPENHYRA_ALLOW_UNSANDBOXED=1` + an external container (sandbox is macOS-only)
- [ ] **S3-ACH-01 — spike a PreToolUse read-only allowlist gate for planner/critic actors.** An actor may inspect evidence freely but cannot launch a build or benchmark until authorized. Classification is allowlist-only (unknown ⇒ gated), with a test asserting every allowlisted verb names a real command. Gates the ACTION, not the outcome: both our loops gate at promotion, so a misfiring planner can spend GPU-hours before a human sees a decision. Pattern: orx plan_gate, intake-883#record @3a8b0286.

## Fan-out A/B design constraints — 2026-08-13 (research-intake Stage 3, source round intake-1105…intake-1127)
- [ ] **Hard design constraints on any first-party fan-out A/B, fixed before one is built.** (a) Matched cost axis on the same plot; result shape is a Pareto frontier, not a bar — intake-1120 (arXiv:2407.01502v1, dive-verified), whose trivial warming baseline matched the best agent architecture at >50x less cost than the most expensive arm. (b) A simple-baseline CONTROL ARM (retry-to-N, warming) at equal spend, or the fan-out arm is unfalsified. (c) PAIRED within-task design with task as a random effect — intake-1122#01 (arXiv:2604.22750v2, dive-overturned) shows cross-problem token variance dwarfs cross-run variance, so an unpaired design measures task sampling rather than fan-out. (d) Our cost axis is not dollars: define GPU-seconds + total tokens + wall-clock and always record tokens so the axis stays re-derivable. Note on (c): that source's "up to 30x" is a TOKEN tail, typical ratio ~2x, and it prescribes no minimum n — do not cite it as a variance gate.

## Research-intake update — 2026-09-07 (execution-alignment failure triage)
- [ ] **Adopt the five execution-alignment symptoms as our agent-run failure triage label set** — contract/format, tool/recovery, evidence/grounding, artifact commitment, state/continuation (intake-1332#03, dive-verified). Cross-link **MHS-5** in [promptforge-mutation-safety-contract.md](promptforge-mutation-safety-contract.md): the meta-harness stub trains harness edits from exactly this kind of failure trajectory. The **label set** is the durable part and is independent of every defect the dive found in that source's published rates. Zero compute.

## Research Intake Update — 2026-09-17 (CORAL / SwarmResearch harness mechanisms, intake-1439…1455)

_Via /research-intake Stage 4 (operator-approved plan 2026-09-17). Sources dive-verified; external numbers motivate, never gate._

- [ ] **AC-CORAL — pin CORAL v0.7.20 (`bbae4f72`) and spike the shared-state design against orchestrator `/v1`.** Install via pinned tag; point opencode/codex runtimes at `/v1` (baseURL or embedded LiteLLM gateway); evaluate `.coral/public` shared state (attempts/notes/skills + heartbeat reflect-1/consolidate-10/pivot-5) as the persistent-workspace mechanism for kernel R&D against the current ad-hoc dispatch baseline (equal-spend control per the fan-out A/B constraints above). Sources: intake-1449, intake-1455.
- [ ] **AC-branch-per-agent — draft the SwarmResearch-pattern search-harness spec.** Branch+worktree per search agent, fresh-context explorers, lineage findings.md, shepherd global context, width/depth adaptation with explicit spawn telemetry; reuse the released repro harness (intake-1450) as trial substrate where useful. Sources: intake-1439, intake-1450, intake-1444.

## Research Intake Update — 2026-09-25 (ALE private evaluation)

**ACH-ALE-1 trigger record — private grader for a selected ALE-style campaign.** Activate only when the shared `SEQ-SHINKA-1` / `AP-DGM-SEL` replay beats matched simple controls, or a live long-horizon engineering campaign requires ALE-style evaluation. Then run private grading in a separate process or service with inaccessible instances, seeds, and standings, immutable one-shot receipts, and a non-resettable private-call budget. The search process may consume only the returned verdict; it may not inspect or tune against hidden cases. Until the trigger fires this record creates no active grader service or campaign. Sources: intake-1597#record, intake-1598#record, intake-1599#record.
