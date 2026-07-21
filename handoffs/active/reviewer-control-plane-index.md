# Reviewer Control Plane — Coordination Index (H0)

**Status**: active — coordination index for the Architect→Reviewer control-plane series (9 leaf handoffs)
**Created**: 2026-07-16 (operator deep-research report → audited + adapted; 4 exploration agents + 13 Opus deep-dives during planning)
**Categories**: agent_architecture, routing_intelligence, benchmark_methodology
**Audit anchor**: [`research/deep-dives/2026-07-16-architect-reviewer-control-plane-audit.md`](../../research/deep-dives/2026-07-16-architect-reviewer-control-plane-audit.md)
**Leaves**: [H1 trace](reviewer-trace-materialization.md) · [H2 artifacts](reviewer-typed-artifacts.md) · [H3 decision plane](reviewer-decision-plane.md) · [H4 calibration](reviewer-calibration-accounting.md) · [H5 ablations](reviewer-model-ablations.md) · [H6 GLM gates](glm52-reviewer-capability-gates.md) · [H-LB latency budget](reviewer-latency-and-sampling-budget.md) · [H7 escalation policy](reviewer-escalation-and-human-gate-policy.md) · [H8 autopilot](autopilot-control-plane-integration.md)

## Objective

Elevate the orchestrator's dormant review machinery into a governed, measured **Architect→Reviewer control plane**: Architect plans/decomposes/re-plans; Reviewer is a judicial gate (no authorship) emitting typed, evidence-linked decisions; objective verifiers take precedence when conclusive; false-accept/false-reject calibration is the core instrument. **Domain-general** (not just SWE): the objective layer spans gate_runner AND eval-tower scorers/grounding/constraint checkers.

## Thesis

The machinery exists dormant (`ArchitectReviewService` + typed decisions behind OFF flags; IR schemas; trace-store scaffold; gate_runner/eval-tower/e-process stats; planner/read-only-critic split in the autopilot). The work is **activation + instrumentation**, sequenced measurement-before-sophistication: **M1 observable** (H1+H2) → **M2 measured** (H3 shadow + H4 instrument + H-LB budget) → **M3 compared** (H5 tournament; floor: beat a single augmented LLM) → **M4 governed** (H7 policy; enforce-mode only past the H-LB gate). Reviewer identity is now an explicit selection problem: **GLM-5.2 UD-IQ2_M failed decision-grade C-CRAB P-REV-1 and is diagnostic-only / not admitted as production patch reviewer on the current policy**; RM-2.fast/RM-2.next found no clean small-model, status-quo, or same-family replacement. Active path is RM-3 screening, Ref external judge-of-judge, or a named repair hypothesis, not unchanged GLM/Qwen/Qwable admission reruns. RM-3's code bridge is now live-wired to the P-REV prompt/schema path, and the first live routable-role batch ran on `frontdoor`/`coder_escalation`; both were weak (`frontdoor` FA `16.7%` / FR `50.0%`, `coder_escalation` FA `25.0%` / FR `75.0%`) and do not resolve the reviewer route. RM-3d metadata repair is closed: live forced-direct rows now say `forced_direct_chat` and preserve `planned_transport=placement_queue`, so future claims cannot confuse forced-direct observations with true placement-queue execution.

## Milestones

| Milestone | Definition of done | Owner leaves | Status |
|---|---|---|---|
| M1 observable | events.sqlite live; REVIEW_* categories; schemas validated; shadow emission ~100% coverage (TM-8) | H1, H2 | **CODE-COMPLETE 2026-07-17** (orchestrator `9958d819`+`30d3232b`): store live + durable resume + schemas/types + TM-3 always-on emission + TM-6/9 docs + RA-8 design. Only open: TM-8 coverage replay (**inference-gated**) |
| M2 measured | ledger + corpus v1 + P-REV-1 drafted; baseline FA/FR; regression attributed + budgets defined | H3, H4, H-LB | **CODE-COMPLETE 2026-07-17** (`30d3232b`): full shadow decision plane (RD-1..11 done; RD-7 in final sweep), rubric engine, verifier adapter + gates.yaml, review_ledger + gold labels + calibration report + symmetric e-processes, knob manifest + LB-5. Open: RC-8 baseline + RD-12 replay + LB-1/LB-4 (**inference-gated**); RC-6a P-REV-1 PR + LB-6b threshold (**operator**, OP-5) |
| M3 compared | tournament confirmation tier done; winner beats A0/A1 floor at acceptable cost (LB-7) | H5, H6, H8 | RM-1 pool-gen + H8 code (AP-1/4/5/6/7/8; screening driver emits placement-queue plans) DONE; GLM A4 failed P-REV-1 and RM-2.fast/RM-2.next closed with no clean replacement. RM-3 row-id-bound dry-run queue, live forced-direct bridge, first routable-role batch, and metadata repair are closed; first live rows (`frontdoor`, `coder_escalation`, n=12 each) worked mechanically but were weak observation-grade results, so no confirmation-tier winner exists yet. True placement-queue execution is future stronger transport evidence, not a metadata blocker. |
| M4 governed | thresholds/escalation policy live; enforce-mode past LB-6 gate | H7 | open |

## Prioritized Task List (aggregated; leaf checkboxes are authoritative)

- [ ] **P1 — M1**: H1 TM-1..TM-9 (trace materialization + LangGraph SqliteSaver durable resume) ; H2 RA-1..RA-11 (schemas + sanitization + GBNF + validation gating)
- [ ] **P2 — M2**: H3 RD-1..RD-12 (shadow decision plane, two-turn rubric reviewer, verifier precedence, 50-q replay baseline) ; H4 RC-1..RC-9 (ledger, corpus v1, symmetric FA/FR e-processes, P-REV-1 draft) ; H-LB LB-1..LB-8
- [ ] **P3 — parallel infra**: H6 GC-1..GC-5 (GLM reviewer gates consumed; GLM diagnostic-only until a named repair hypothesis) ; kernel follow-ups (sparse-final-attention classification, v7 CPU/perf reproducibility — in `gemma-challenge-kernel-techniques-v7.md`; grammar crash and glm-dsa cache/runtime smoke are closed) ; GPU bets 1→4 (in `mi210-big-model-and-acceleration-roadmap.md` + `gpu-drafter-mi200-investigation.md`)
- [ ] **P4 — M3**: H8 AP-1..AP-8 (knob registration, Pareto axes, screening driver, dogfooding) ; H5 RM-1..RM-9 (registry-driven tournament + Ref judge-of-judge)
- [ ] **P5 — M4**: H7 HG-1..HG-8 (policy from curves; escalate-default; optional gated rebuttal)

## Dependency Graph

```text
H1 (TM-8 gate) → H2 → H3 (shadow) → H4 (P-REV-1) → H5 → H7
                        │              ▲               ▲
                        └→ H-LB ───────┴───────────────┤ (LB-6 blocks ALL enforce-mode)
H6 + glm51-reap infra (parallel from day 1) ──────────→ H5 A4/A4g arms
H8 (after H2+H3; screening driver after H4) ──────────→ H5 RM-3
Kernel status: grammar crash and glm-dsa cache/runtime smoke are closed; sparse-final-attention classification and v7 CPU/perf reproducibility gate cost/trust, not basic GLM loading
External gates: TR-4/5 + DAR FROZEN (never needed; RD-7 telemetry-only) · HS-4 gates only H7 harness-side · MEASUREMENT P-REV-1 = operator PR · bench windows = operator-approved
```

## Cross-Cutting Concerns

1. **Layer boundary (2026-07-16 harness-selection thesis)** — calibration/scoring/ledger = Layer A (server-side, human-amendment-only, behind `/v1`+`x_*`); acting-on-decisions in agent loops = Layer B (shadow or override-surface only until HS-4). The plane invokes the eval tower; it never absorbs the measurement trust boundary.
2. **Latency is first-class** — the 2026-07-16 plan-review regression (throughput halved) is the standing warning; H-LB owns budgets; structural mitigations (two-turn rubric, reminders-over-re-review, complexity gating, final-aggregate review, sticky cache) live in H3; single-host parallel review costs SUM not MAX.
3. **Single-card contention** — MI210 bets ordered 1→4 by the operator (drafter Stage-1 → architect residency → GLM offload → teleport); H5 GPU arms queue behind the parallel session's admission smokes.
4. **Overcorrection asymmetry** — FR ≫ FA (10:1-440:1) is the expected live failure; symmetric e-processes + reject-admissibility are the guards.
5. **Reward-hacking** — no learning loop may optimize against the rubric score alone; objective-verifier precedence + cross-family author/grade are mandatory in any closed loop.

## Adoption Shortcuts (framework verdicts, 2026-07-16 dives — named-module mappings)

| Framework | Verdict | What we take | Where |
|---|---|---|---|
| **LangGraph 1.0** (intake-847) | **adopt_component** | `SqliteSaver` durable checkpoints + `interrupt()`/`Command(resume=)` via the EXISTING `run_task_lg` bridge; replaces write-only `persistence.py`; keep pydantic_graph topology + `decision_gates.py` | H1 TM-7, H3 gates |
| **OpenAI Agents SDK** (intake-849) | mine_patterns ×7 | tripwire⟂advisory split; DelegationState shape; guardrail placement (final-aggregate review); TracingProcessor re-implementation; sticky decisions; as-tool/handoff distinction; is_enabled predicates. Validated ahead-of-SDK: `safety_gate.warn_only`, BindingRouter | H2 RA-1/6, H3 RD-5/10, H1 TM-4 |
| **OpenHands** (intake-848) | mine_patterns (runtime); serious-but-orthogonality-weak HS-4 candidate | EventStream + client/server executor split reserved for a future untrusted-code tier; harness assessment → HS-1 audit (`harness-selection-and-integration.md`) | future tier; HS-1 |
| **MetaGPT** (intake-839) | mine_patterns | artifact-contract chain shapes; boundary validation-gating; dependency-gated activation; multi-role-tax warning → baseline-to-beat framing | H2 RA-5/11, H-LB LB-7 |

## Scope Cuts (documented, not built)

Public benchmark **adapters** (suites acquired as corpus-mining inputs only — `/mnt/raid0/llm/datasets/BENCHMARKS.md`); full ArchBench (only the near-miss corpus slice); reviewer rewrite/repair modes (role-collapse risk); Qwen3.5-397B architect arm (off-thesis); debate machinery beyond H7's gated rebuttal; human-escalation UI (HS-4-gated); new decision theory (Fable5: enforcement and deletion, not theory). Escape hatch: if corpus v1 cannot discriminate arms, a SWE-bench-Lite-style subset may be proposed (operator approval).

## Key File Locations

- Dormant machinery: `src/proactive_delegation/{review_service,delegator,types,complexity}.py` · `src/roles.py:262-273` · `src/trace/store.py` · `src/gate_runner.py` · `src/autopilot_core/sequential_verdict.py` · `scripts/autopilot/{eval_tower,rubric_scoring,safety_gate,planner_providers}.py`
- Schemas: `orchestration/*.schema.json` + `validate_ir.py`
- Flags: `src/features.py` + `orchestration/runtime_flags.json` (`plan_review`, `architect_delegation`, new `review_decision_shadow/_enforce`)
- Instruments: `/workspace/MEASUREMENT.md` (P-REV-1 approved/signed 2026-07-19) · `orchestration/instrument_eras.yaml` · trace DB `data/trace/events.sqlite`
- Datasets: `/mnt/raid0/llm/datasets/` (+ `BENCHMARKS.md` manifest)

## Reporting Instructions

- Work lands in the leaf handoffs; flip leaf checkboxes with `✅ YYYY-MM-DD`; this index's P-rows flip only when ALL constituent leaf tasks are done. Update the Milestones table on M-transitions.
- Operator decisions route to master-index §A00 (OP bundle): LB-6 threshold; GLM RAM-residency posture (GC-4); teleport quant policy; mmvq family gating; ReviewDecision enum/score-vs-confidence semantics; escalation-audit cadence (HG-4); scope-cut confirmation. P-REV-1 approval is closed; future decision-grade claims still need protocol and attestation evidence.
- Any posture change (layer boundary, reviewer identity, enforce-mode) is an operator decision — flag, never decide autonomously.

## Evidence Base (intake)

intake-834 Agentic Rubrics · intake-835 plan compliance · intake-836 reviewer overcorrection · intake-837/838 judge bias · intake-839 MetaGPT · intake-840/841 debate · intake-842/843 verification-in-loop · intake-844/845 RACE-bench/c-CRAB · intake-846 Anthropic set · intake-847 LangGraph · intake-848 OpenHands · intake-849 Agents SDK · audit doc 2026-07-16 · IQ2==Q4 parity (n=212) · N5 drafter α=1.0 (2026-07-16) · plan-review 2× regression (2026-07-16).

## Time-sensitive intake follow-up — registered 2026-07-21 (audit catch: was in no index)

- [ ] **RC-6a window: add a chance-corrected agreement statistic to P-REV-1 BEFORE it ratifies.** intake-876 (arXiv 2606.00093): on binary judge-vs-human data Pearson/Spearman/Kendall/phi/MCC collapse to the same number; Cohen's kappa is the one coefficient adding information (exposes judge-vs-human positive-rate drift). Our draft P-REV-1 grammar reports raw FA/FR/yield/CR with **no chance correction, no confusion matrix, no declared tie/abstention estimand** — and RM-3c's live slice (FR 50.0% / FA 16.7%) is exactly the skewed-marginal regime where raw rates overstate judge quality. **Pair kappa with prevalence disclosure (kappa paradox — our near-miss corpora are deliberately skewed).** RC-6a is still an open checkbox, so this amends a DRAFT rather than a ratified protocol — the cheap window closes when the operator PR lands. Full detail: [reviewer-calibration-accounting.md](reviewer-calibration-accounting.md) 2026-07-21 section. Human-amendment-only: operator PR, not an agent edit.
- [ ] GC-external-1a: declare the tie/abstention estimand explicitly and report its rate, rather than dropping malformed/tie rows as data cleaning (intake-876; same source).
