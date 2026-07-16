# Reviewer Control Plane — Decision Plane Activation (H3)

**Status**: active — M2 "measured" milestone; SHADOW-ONLY until H-LB budget gate + H4 calibration exist
**Created**: 2026-07-16 (Architect→Reviewer control-plane series; see index)
**Categories**: agent_architecture, routing_intelligence, tool_implementation
**Index**: [`reviewer-control-plane-index.md`](reviewer-control-plane-index.md)
**Related**: [`reviewer-typed-artifacts.md`](reviewer-typed-artifacts.md) (H2; schemas consumed here), [`reviewer-latency-and-sampling-budget.md`](reviewer-latency-and-sampling-budget.md) (H-LB; blocks enforce-mode), [`tri-role-coordinator-architecture.md`](tri-role-coordinator-architecture.md) (TR-1 answered by RD-7), [`eval-tower-verification.md`](eval-tower-verification.md) (EV-9 rubric judge machinery)
**Frozen-gate posture**: requires NO reopening of TR-4/5 or DAR gates; forbidden from touching role-aware dispatch; RD-7 is telemetry-only. HS-4 not required (server-side only).
**Repo**: `epyc-orchestrator`

## Objective

Activate the dormant review machinery (`ArchitectReviewService`, flags `plan_review`/`architect_delegation` currently OFF) as an explicit, typed, evidence-linked decision API with verifier precedence — in shadow mode. Zero dispatch/routing changes; zero enforcement until gated.

## Thesis

The decision plane is activation, not construction — but the dive evidence forces a specific shape. The reviewer is a **two-turn system**: the heavyweight model (GLM-5.2-IQ2 target / 122B-IQ2 interim) **authors a cached per-domain rubric once**; a cheap fast model **grades each candidate against it** (authoring $0.245 vs grading $0.003; grading-model capability barely matters — intake-834). This is the structural fix for review latency (the 2026-07-16 plan-review regression halved throughput). Objective verifiers take precedence **only when conclusive** (three-valued outcomes; 15% formalization false-positive tax — intake-843), and a `reject` unbacked by objective evidence is *inadmissible as enforcement* (overcorrection runs 10:1-440:1 — intake-836).

## Prioritized Task List

- [ ] **RD-1 — Reviewer role binding**: replace the alias-only mapping (`src/roles.py:262-273` `"reviewer"→ARCHITECT_GENERAL`) with a config-level binding so `reviewer` can target a different model than `architect_general` (default unchanged → zero behavior change). No escalation-chain or routing-classifier edits.
- [ ] **RD-2 — Two-turn rubric reviewer** (intake-834): (a) rubric-authoring turn — heavyweight model + repo/context exploration emits `review_rubric` artifact (H2 RA-4), cached per task-class/domain-template, refreshed on template drift; (b) grading turn — cheap model (frontdoor 35B or smaller) grades candidate per-item binary, aggregates S=Σws/Σw; decision bands **S≥0.85 approve / S≤0.5 reject / middle → request_changes|request_evidence**, majority-of-k grading near band edges (judge flakiness 2-9%).
- [ ] **RD-3 — Verifier-precedence rule (mechanical)**: conclusive objective results override reviewer claims — reviewer-approve + gate-FAIL → `fa_candidate` trace event; reviewer-reject + gate-PASS → `fr_candidate`; objective-PASS + rubric-LOW → `request_evidence`, never reject (54%/46% disagreement quadrant — intake-834); `inconclusive` hands control back to the reviewer (intake-843).
- [ ] **RD-4 — Verifier-request adapter**: map `verifier_requests[]` to `src/gate_runner.py` gates + MCP run_tests/lint via restricted_executor, **tiered cheap-first** (jsonschema/pydantic, invariant asserts, Hypothesis property tests) before heavy (Z3/symbolic — pluggable per-domain formalizer interface, code/math/logic-QA/retrieval); failure certificates (failing assertion/counterexample/unsat core) become the `request_evidence` payload (intake-842/843). **Create the missing `config/gates.yaml`** (gate_runner currently silently falls back to defaults). Non-code domains: eval-tower programmatic scorers + retrieval-grounding + instruction-constraint checkers are the objective layer.
- [ ] **RD-5 — Shadow/enforce split**: new flags `review_decision_shadow` (emit + trace, act never) and `review_decision_enforce` (default OFF, **blocked on H-LB budget gate**). Propagate `safety_gate.warn_only`'s mechanism into review_service (we are ahead of the Agents SDK here — intake-849 P2). Note `plan_review` requires `memrl` (`features.py:571`) — decide whether shadow emission needs a decoupled activation path.
- [ ] **RD-6 — Review prompt controls** (intake-836/837/838): framing-neutral (no "assume competent" priming, no explain-then-fix primary path — it DOUBLES false-rejects); fix suggestions only post-verdict as testable artifacts; pointwise single-candidate grading only; reviewer sees sanitized CandidatePackage (task+candidate+evidence, no architect self-assessment); reviewer context curated to the minimal high-signal set — a retrieval sub-agent distills large packages to 1-2k tokens for the IQ2 reviewer (context rot; intake-846).
- [ ] **RD-7 — Answer tri-role TR-1** (telemetry-only): a review decision turn IS a Verifier turn — log `assigned_role="verifier"` on review dispatches so Trinity shadow telemetry captures them; update `tri-role-coordinator-architecture.md` cross-ref. No dispatch change.
- [ ] **RD-8 — Reject-admissibility + escalate stub**: `reject` without an objective-verifier hit or passing counterfactual is logged *unverified* and down-weighted (intake-836); `escalate` decision → existing escalation pipeline + operator surface (no UI).
- [ ] **RD-9 — Plan-review specifics** (intake-835): plan rubric checks phase-coverage/order/executor-alignment (NOT prose quality; penalize over-specification); `REJECT_TO_EMPTY` outcome falls back to no-plan default workflow; **plan-reminder re-injection** (~every 5 steps / N tool calls) as a separate cheap knob — PREFERRED over re-review; iteration bounds keyed to compliance trend (drift→reminder; collapse→re-plan).
- [ ] **RD-10 — Delegation-mode hygiene** (intake-849 P4/P5/P7): specialist subtasks = as-tool (manager keeps control); ESCALATE = handoff (ownership transfer w/ input-filtered history — name the existing `feedback_history[-3:]` as that filter); **complexity-gated per-subtask review + single final-aggregate review otherwise** (stop reviewing every subtask output); sticky decision cache in `IterationContext` (approved patterns skip re-review in parallel waves).
- [ ] **RD-11 — Autopilot tuning-surface class 1** (H8 consumes): declare review-trigger complexity threshold, iteration bounds, confidence cutoffs, reminder cadence, per-subtask-review gate, majority-k in the guarded numeric-surface manifest → `config_applicator.apply_params`.
- [ ] **RD-12 — Per-decision latency_ms + token accounting** in artifact + trace (feeds H-LB); tests incl. parse-failure fallback counting; **50-question replay with shadow reviewer on**: zero enforcement side effects; overhead delta vs reviewer-off = the H-LB baseline.

## Dependency Graph

```text
H2 schemas → RD-1 → RD-2 → RD-3 → RD-4 → RD-8
                RD-5, RD-6 (parallel after RD-2)
                RD-9, RD-10 (parallel)      RD-7 (anytime, telemetry)
RD-11 (after RD-2/RD-9 knob set stabilizes) → H8
RD-12 replay (last) → hands baseline to H-LB
Enforce-mode: BLOCKED until H-LB LB-6 budget gate passes.
```

## Cross-Cutting Concerns

1. **Layer boundary** — decision *emission* is server-side (Layer-A-adjacent, behind `/v1`); *acting* on decisions in an agent loop is Layer B and stays shadow/`x_*`-only until HS-4. The plane invokes the eval tower; it never absorbs the measurement trust boundary.
2. **Latency** — every design choice above (two-turn rubric, reminders-over-re-review, complexity gating, final-aggregate review, sticky cache) exists to keep the plane affordable on a CPU stack; H-LB owns the numbers.
3. **v7 grammar P0** — GBNF-constrained emission on the GPU lane is blocked by `common/sampling.cpp:292` (kernel handoff); free-parse + RA-9 accounting is the interim.

## Key Files / Surfaces

- `src/proactive_delegation/review_service.py`, `delegator.py`, `types.py`, `complexity.py`
- `src/roles.py:262-273` (alias to replace), `src/features.py` (flags), `orchestration/runtime_flags.json`
- `src/gate_runner.py` + `config/gates.yaml` (to create), `src/api/routes/chat_review.py`
- `scripts/autopilot/rubric_scoring.py` + `eval_tower.py` (EV-9 machinery to reuse, not duplicate)

## Reporting Instructions

Flip checkboxes `✅ YYYY-MM-DD`; RD-12's overhead delta gets recorded in H-LB AND here; any enforce-mode proposal is an operator decision gated on H-LB LB-6 (OP bundle). Update H0 milestone table when shadow decisions flow end-to-end.

## Evidence Base (intake)

intake-834 two-turn rubric economics + bands · intake-835 plan rubric/reminders/reject-to-empty · intake-836 overcorrection + admissibility + framing · intake-837/838 sanitization/pointwise/probe set · intake-842/843 three-valued verifiers + certificates · intake-846 context curation + fan-out gating · intake-849 P2/P4/P5/P7 patterns · audit doc 2026-07-16.
