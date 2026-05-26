# Cluster B — Edit Pass Report

## Files modified

- `/workspace/repos/epyc-orchestrator/docs/chapters/07-memrl-system.md` — 4 edits applied
  - Phase progression table extended with rows 8.1 (classifier fast-path) and 8.2 (frontdoor verifier gate); added the "dead code 2026-04-15 → 2026-05-21" cautionary note inline.
  - New section "Routing Classifier Fast-Path (Phase 8.1)" covering architecture (1031→128→64→N MLP, ~140K params), Q-weighted CE training, 98.7% val acc, reset safety, feature flag, and the pre/post-wiring telemetry contrast.
  - New section "Frontdoor Verifier Quality Gate (Phase 8.2)" covering BCE-trained single-action MLP, Brier 0.0072 / AUC 0.9996 / ECE 0.0145, explicit architectural distinction from the routing classifier (routing engine vs quality estimator), correct default-OFF semantics for `FRONTDOOR_VERIFIER_SHADOW` (the audit was wrong here — see below).
  - Distillation reference now points to BOTH the existing `MEMRL_DISTILLATION_DESIGN.md` (which does exist; the audit was wrong) and the new `learned-routing-controller.md` handoff for the Phase 6 verifier validation arc.

- `/workspace/repos/epyc-orchestrator/docs/chapters/09-memory-seeding.md` — 3 edits applied
  - Added `SPO_PLUS_EPSILON` exploration-epsilon paragraph and a separate regret-signal paragraph inside the 3-way seeding section, both inside the existing `<details>` block.
  - New top-level section "Embedding Health Preflight (2026-05)" placed before "Seeding Order & Dependencies" with the manual invocation command and the 40,862-vector / 22.9%-dropped historical context.
  - Stack-consolidation distribution-shift blockquote added under "3-Way Action Keys (February 2026)" with the pre/post-2026-05-09 success-rate numbers and the cross-reference to Ch07 Phases 8.1-8.2.

- `/workspace/repos/epyc-orchestrator/docs/chapters/15-skillbank-experience-distillation.md` — 2 edits applied (despite UP_TO_DATE verdict; both were brief and clearly worth it)
  - "Current Status (May 2026)" subsection inside the Feature Flag `<details>` block, recording the 57-skill / 180-trajectory 2026-03-09 dry-run and the "flag OFF in production, A/B deferred" status.
  - "ClaudeDebugger Integration (May 2026)" subsection inside Recursive Skill Evolution, documenting the `skill_mismatch` (sev 0.5) and `no_skills_available` (sev 0.3) anomaly signals.

- `/workspace/repos/epyc-orchestrator/docs/chapters/16-calibration-and-risk-control.md` — 5 edits applied (HIGH priority chapter)
  - RetrievalConfig section: the gate-provenance bullet list now correctly attributes `risk_gate_action` / `risk_gate_reason` to `HybridRouter.last_decision_meta` (not to RetrievalConfig as the audit implied) and adds `assigned_role` as a field on `MemoryEntry` (Trinity tri-role axis) rather than on RetrievalConfig.
  - Rollout & guardrail bullet list extended with the 2026-05-24 cross-role bandwidth-aware rollout mechanism and link to `cross-role-bw-aware-routing.md` (in `handoffs/completed/`, not `active/` — audit had that wrong too).
  - New top-level section "Verifier Quality Gate (May 2026)" inserted between "Skill Effectiveness Scoring" and "Input-Side Classifiers", emphasizing the orthogonality to the conformal margin formula.
  - "Interaction with Risk Control" subsection in Skill Effectiveness Scoring rewritten to make the orthogonal-confidence-axes distinction explicit (routing confidence vs skill effectiveness are independent, not aligned).
  - Output-Quality think-block-loop bullet annotated with the 2026-04-15 add-date and the rationale (catches a failure mode the generic 3-gram check misses because the loop is inside `<think>` blocks).

## Edits deferred or skipped

- **Ch07 audit Item 4 (cross-role BW-aware routing reference in the "Calibration and risk metrics" subsection)**: deferred. The audit suggested noting that `effective_threshold` accounts for role-load variance — but that note is more naturally a Ch16 concern, and I added it there (Edit 2 / rollout-controls bullet). Adding it again in Ch07 would duplicate content across chapters.

## Audit items I disagreed with

- **`FRONTDOOR_VERIFIER_SHADOW` default**. The audit (Ch07 Edit 3, Ch16 Edit 2) says shadow mode is the default. The code disagrees: `hybrid_router.py:76-78` reads `os.environ.get("FRONTDOOR_VERIFIER_SHADOW", "0") == "1"`, so shadow is OFF by default — when the gate is enabled it defaults to enforce. I wrote the doc to match the code, not the audit. The audit's broader narrative (gate runs in shadow first, then enforce) is still operationally true, but the env-var default is the opposite of what the audit claims.

- **`MEMRL_DISTILLATION_DESIGN.md` "broken" reference (Ch07 line 671)**. The audit said this file does not exist. It does: `/workspace/repos/epyc-orchestrator/docs/reference/agent-config/MEMRL_DISTILLATION_DESIGN.md`. I kept the existing link and added the new `learned-routing-controller.md` link alongside it instead of replacing.

- **`cross-role-bw-aware-routing.md` path**. The audit refers to it as `handoffs/active/cross-role-bw-aware-routing.md`. It is actually in `handoffs/completed/cross-role-bw-aware-routing.md` (the handoff has already been completed). All my cross-references use the correct `completed/` path.

- **`risk_gate_action` / `risk_gate_reason` / `assigned_role` as RetrievalConfig fields (Ch16 Edit 1)**. The audit lists these as RetrievalConfig parameters. They are not: `risk_gate_action`/`risk_gate_reason` live in `HybridRouter.last_decision_meta` (telemetry), and `assigned_role` is a column on `MemoryEntry` / the episodic store. I documented them in the right place (gate-provenance logging) rather than misplacing them in the RetrievalConfig parameter list.

- **Ch15 Edit 2 line number (audit says "after line 678")**. There is no §9.2 Trigger Mechanism / line 678 in the current chapter. I placed the ClaudeDebugger integration note inside the Recursive Skill Evolution section where it conceptually belongs.

## Recommended new chapters or follow-ups

- A short cross-cutting page (or a unified diagram in Ch16) showing how the stacked confidence-gating mechanisms compose: input-side factual-risk + difficulty-signal → routing-confidence (conformal margin + cross-role BW modulation) → post-routing verifier gate → output-quality detector. The audit flagged the absence of a unified picture in its notes; Ch16 has all the pieces now but they are spread across sections.
- Consider noting in Ch08 (Graph Reasoning) that FailureGraph + SkillBank now feed effectiveness data into the Phase 8.2 verifier's training pipeline, not just the Q-scorer. Audit raised this in Ch07's Notes; out of scope for this pass.
- The `SPO_PLUS_EPSILON` interaction with the conformal margin (exploration overrides the gate by design) deserves a short callout once a dedicated epsilon-tuning session has produced numbers. Currently called out only obliquely.

## Verification notes

- `hybrid_router.py` confirmed live with classifier, frontdoor-verifier (P6.2-A2), `SPO_PLUS_EPSILON`, and `BILINEAR_SCORER_ENABLED` (DAR-4) all present.
- `orchestration/repl_memory/verifier_head.py` (10489 bytes) and `routing_classifier.py` (17412 bytes) both present, modified 2026-05-21.
- `scripts/maintenance/repair_episodic_embeddings.py` and `verify_routing_wiring.py` both present, modified 2026-05-21.
- `/workspace/progress/2026-05/2026-05-21.md` exists; cited Session 4 and Session 6 content matched the audit's quoted numbers.
- `handoffs/active/learned-routing-controller.md` exists; `handoffs/completed/cross-role-bw-aware-routing.md` exists (NOT active, as the audit claimed).
- All four modified chapters are staged uncommitted; no commit was made.
