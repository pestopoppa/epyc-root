# Reviewer Control Plane — Typed Artifact Schemas (H2)

**Status**: active — M1 "observable" milestone; schemas are the contract everything downstream validates against
**Created**: 2026-07-16 (Architect→Reviewer control-plane series; see index)
**Categories**: agent_architecture, tool_implementation
**Index**: [`reviewer-control-plane-index.md`](reviewer-control-plane-index.md)
**Related**: [`reviewer-trace-materialization.md`](reviewer-trace-materialization.md) (H1; events carry these artifacts), [`reviewer-decision-plane.md`](reviewer-decision-plane.md) (H3; emits them), [`tri-role-coordinator-architecture.md`](tri-role-coordinator-architecture.md) (Verifier semantics)
**Repo**: `epyc-orchestrator`

## Objective

Author the three missing IR schemas — evidence-linked `ReviewDecision`, `CandidatePackage`, `VerificationReport` — wire them into `orchestration/validate_ir.py` alongside the existing task_ir/architecture_ir/procedure suite, evolve the dormant dataclasses in `src/proactive_delegation/types.py`, and make reviewer output grammar-constrainable. Schemas are **domain-general**: evidence kinds include answer spans, retrieval provenance, and scorer results — not just file_span/test_result.

## Thesis

Typed artifact contracts are the design center (report thesis + MetaGPT's validated discipline, intake-839). The repo already has the IR convention + validator; what's missing is the review-plane trio plus governance semantics the dive evidence forces: a **tripwire ⟂ advisory split** (blocking boolean orthogonal to score/feedback — `safety_gate.py` has it, `ArchitectReview` doesn't; intake-849 P1), **REJECT-to-empty** as a first-class plan outcome (bad plan < no plan; intake-835), **payload sanitization** (architect self-assessment shifts verdicts ~18-29pp; intake-837/838), and **parse-failure accounting** (an IQ2 reviewer's schema-emission failures are themselves a quality signal).

## Prioritized Task List

- [x] **RA-1 — `orchestration/review_decision.schema.json`** ✅ 2026-07-17: decision enum `{approve, reject, reject_to_empty, request_changes, request_evidence, escalate}`; `confidence` [0,1]; `tripwire: bool` + `blocking_issues[]` (hard stop) structurally separate from `score`/`non_blocking_issues`/`feedback` (advisory); `evidence[]` with kinds `{file_span, test_result, gate_result, scorer_result, answer_span, retrieval_provenance, trace_event, protocol_claim}`; `verifier_requests[]`; `human_review_required`.
- [x] **RA-2 — `orchestration/candidate_package.schema.json`** ✅ 2026-07-17 (sanitized_view projection w/ additionalProperties:false — leaked self-assessment FAILS validation): task ref, plan ref (task_ir), diff/output refs, declared acceptance checks, provenance (model+quant, role, flag state, instrument era) — **plus a sanitization contract**: the reviewer-visible view MUST exclude architect self-assessment prose, confidence assertions, and "refined/final/expert" labels (intake-837/838). Sanitization is applied at package assembly, not reviewer prompt time.
- [x] **RA-3 — `orchestration/verification_report.schema.json`** ✅ 2026-07-17 (certificate required-on-fail via if/then): normalizes `gate_runner.GateResult` + eval-tower tier outputs; **three-valued outcome per check: `pass | fail | inconclusive`** with a `certificate` field on fail (failing assertion / counterexample / unsat core — the request_evidence payload; intake-842/843) and instrument version.
- [x] **RA-4 — Rubric artifact schema** ✅ 2026-07-17 (`orchestration/review_rubric.schema.json`): items `{text, axis, weight ∈ {1,2,3}}`; axes per domain template (code: file-change/spec-alignment/integrity/runtime; QA: grounding/question-alignment/integrity-no-fabrication/completeness; math: answer/method/integrity/coverage) (intake-834). Rubrics are cacheable, versioned artifacts.
- [x] **RA-5 — Wire all four into `orchestration/validate_ir.py`** ✅ 2026-07-17 (SCHEMA_MAP; non-zero exit on failure); **schema validation gates every role boundary** — a validation failure is a routable bounce-to-author event, never silent (intake-839).
- [x] **RA-6 — Evolve `src/proactive_delegation/types.py`** ✅ 2026-07-17 (+REQUEST_EVIDENCE/+REJECT_TO_EMPTY; ArchitectReview +confidence/tripwire/evidence/verifier_requests, all defaulted; consumers verified — 102 regression tests pass; enum/semantics ratification stays in OP-5f): add `ReviewDecision.REQUEST_EVIDENCE` + `REJECT_TO_EMPTY`; extend `ArchitectReview` with `confidence`, `evidence`, `verifier_requests`, `tripwire` (keep `score` for compat; document score-vs-confidence semantics — operator question in OP bundle).
- [x] **RA-7 — GBNF/json_schema constrained-decoding generation** ✅ 2026-07-17 (`review_grammar.py`: enum sourced from schema file so grammar cannot drift; pure generators + `parse_review_decision` w/ ParseFailure accounting. Grammar EXECUTION on the v7 GPU lane remains K22-blocked) from RA-1/RA-4 for llama.cpp reviewer calls, flag-gated. **Blocked for v7 GPU lane by the grammar-sampler P0 crash** (`common/sampling.cpp:292` — routed to `gemma-challenge-kernel-techniques-v7.md`); CPU production path unaffected pending verification.
- [x] **RA-8 — Field-order A/B design** ✅ 2026-07-17 (full design appended below; EXECUTION inference-gated → H5 RM-6): evidence→confidence→verdict vs verdict-first. Opposing hypotheses on record: verdict-first suppresses self-justification overcorrection (intake-836) vs verdict-first anchors (intake-837). Design the experiment here; run under H5.
- [x] **RA-9 — Round-trip + validator tests; parse-failure accounting** ✅ 2026-07-17 (57 tests) (count schema-invalid emissions per reviewer config; never silently fall back).
- [x] **RA-10 — Schema-versioned artifact emission into the trace store** ✅ 2026-07-17 (ledger rows + emitted artifacts stamp schema_version; REVIEW_DECISION_SCHEMA_VERSION=1.0.0 default w/ override; verification_report versions threaded through gold resolutions).
- [x] **RA-11 — ArchitectureIR/PlanGraph hardening** ✅ 2026-07-17 (optional-but-recommended-for-new-artifacts: interfaces section + typed call_edges; existing docs stay valid) (intake-839): ArchitectureIR mandates an interface-definition/data-structure section; plan steps carry typed call-flow dependency edges, not prose.

## Dependency Graph

```text
RA-1..RA-4 (schemas, parallel) → RA-5 validator wiring → RA-6 types → RA-9 tests → RA-10 emission
RA-7 GBNF (after RA-1/RA-4; v7-GPU-blocked on kernel P0)     RA-8 design (parallel; executes in H5)
RA-11 (parallel)
```

## Cross-Cutting Concerns

1. **Domain generality** — every schema field must make sense for non-code candidates (answers, plans, summaries); code-specific fields are optional extensions.
2. **IQ2 strict-IF weakness** (2/11 measured) is why RA-7 grammar constraint + RA-9 parse-failure accounting are load-bearing, not nice-to-have.
3. **Immutable structure, mutable status** (intake-846): artifacts are append/versioned; only status fields mutate.

## Key Files / Surfaces

- `orchestration/*.schema.json` + `orchestration/validate_ir.py` (existing convention to extend)
- `src/proactive_delegation/types.py` (`ReviewDecision`, `ArchitectReview`, `IterationContext`)
- `src/task_ir.py`, `src/graph/task_ir_helpers.py`

## Reporting Instructions

Flip checkboxes with `✅ YYYY-MM-DD`; schema versions are instruments — version bumps get changelog lines here. RA-6 enum evolution and score-vs-confidence semantics are operator decisions (OP bundle in master index §A00).

## Evidence Base (intake)

intake-834 rubric artifact + axes · intake-835 REJECT-to-empty · intake-836 verdict-first/admissibility · intake-837/838 sanitization + field-order anchoring · intake-839 boundary validation-gating + IR hardening · intake-842/843 three-valued outcomes + certificates · intake-849 tripwire⟂advisory (P1) · audit doc 2026-07-16.

## RA-8 — Field-order A/B experiment design (designed 2026-07-17; executes as H5 RM-6)

**Question**: does ReviewDecision field ORDER in the constrained-decoding schema change reviewer calibration? Two GBNF/json_schema variants generated from the same schema (`review_grammar.py` supports property ordering): **V-first** = decision→confidence→blocking→evidence→feedback; **E-first** = evidence→blocking→confidence→decision→feedback.
**Opposing hypotheses on record**: H1 (intake-836): V-first ↓FR — forcing the verdict before free-text suppresses self-justification-driven overcorrection (their explain-then-fix effect, 35.9→87.9% FR). H2 (intake-837): V-first ↑anchoring — committing to a verdict before enumerating evidence degrades accuracy on near-miss items (their CoT-order effects).
**Protocol**: paired within-item (same corpus-v1 slice graded under both grammars, same reviewer/grader config, seed42 production sampling), stratified to include the ambiguous-tail + natural-defect control slices; N≥100/arm per P-AB-1; primary metrics FA, FR, CR (test-retest ≥2), parse-failure rate; secondary: per-domain splits + confidence calibration (ECE). Analysis: paired flips via `sequential_verdict.quality_trial_statistic`, Holm over {FA, FR, CR}. Decision rule: adopt the variant that is non-inferior on FA and superior on FR (or vice versa with operator weighting); tie → keep E-first (matches evidence-linked design intent). **Execution is inference-gated → H5 RM-6.**

## RA-9 — dual-gold annotation envelope + a gold-sanity gate (intake-948, intake-983; 2026-08-03)

_Via `/research-intake` Stage-2/2b. Schema-level items, so they belong here rather than in the skill;
the pipeline-ordering half lives in [`security-review-skill.md`](security-review-skill.md)._

- [ ] **Adopt benchmrk's annotation envelope as the dual-gold schema.** Its `status:"invalid"` decoys give us a **negative-control axis we do not have anywhere** — intake-845 records the gap explicitly. Every current gold annotation asserts a true finding; nothing in the corpus asserts a finding that *should* be rejected, so no false-accept rate is measurable from our own data.
- [ ] **Add a gold-sanity gate to the schema contract for any machine-generated annotation or test.** Procedure, in this order: inject into the real project test file → apply the **gold** solution → run the project's **native** runner → discard and retry at higher temperature on gold-failure → *only then* consult a 3-sample self-consistency judge. **The order is the finding**: the judge reasons about generated test code that may not itself run, and it endorsed **all six** named invalid cases in the source study. Measured per-augmentation defect rate is **61.9% (n=105)** — the author's own nominated headline, and more stable than the 28.5% iterative figure concentrated in 2 of 12 repos.
- [ ] **Ablation to preserve when implementing the retry:** retry *presence* is load-bearing (3/11 → 9/11); retry *style* is not (a neutral prompt also reaches 9/11). Do not spend design effort on the retry prompt.
- Source code is *"available upon reasonable request"* — **not open**, so this is a pattern adoption and nothing is vendored.
