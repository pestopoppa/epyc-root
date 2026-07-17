# Audit-response: Local Architect→Reviewer Control-Plane Spec

**Date:** 2026-07-17
**Responds to:** [`2026-07-17-local-architect-reviewer-control-plane-spec.md`](2026-07-17-local-architect-reviewer-control-plane-spec.md) (operator-authored; preserved verbatim — this is a response, not an edit)
**Implementation:** landed Wave-2 of the backlog-churn campaign (orchestrator commit `43a77eaf`).

## Verdict: adopted, with four scoping amendments

The spec is a strong, internally-consistent implementation specification. The reducer/authority/invalidation/profile/cohort machinery is a genuine upgrade over the previously-landed RD-3 precedence + binary "conclusive" model, and the shadow→**advisory**→narrow-canary→selective-authority rollout is a better ramp than the prior shadow→enforce. It is adopted as the reviewer-plane semantics layer. Four amendments were applied during implementation; each is a scoping decision, not a rejection.

### A1 — Additive evolution, not a six-schema rewrite
The four v1 schemas (`review_decision`, `candidate_package`, `verification_report`, `review_rubric`) + the trace ledger + their 742 landed tests were already in production-shadow. Rather than rebuild §6's six schemas from scratch, the semantics layer landed as **v1.1 additive fields** (ABSTAIN in the decision enum; logical×execution status; 9-class authority; `untrusted_content_policy`; content-addressed refs) + **three genuinely-new schemas** (`evidence_item`, `decision_envelope`, `assurance_profile` + three example profiles). Proof of back-compat: the exact landed v1 fixtures still validate. This preserves the tested foundation while delivering the full §6 semantics.

### A2 — One enforcement authority per plane
§8's deterministic reducer is implemented as `src/proactive_delegation/policy_reducer.py::reduce_decision(...)` and **subsumes** the previously-inline RD-3 precedence: `review_service` now emits recommendations + findings, and the reducer decides. A boundary is stated explicitly in code and docstring so three non-overlapping authorities don't collide:
- **PolicyReducer** = reviewer-plane semantics for one CandidatePackage (this spec).
- **SafetyGate** (`src/safety_gate.py`) = autopilot experiment-admission — unchanged, untouched.
- **Batch manifest fork-tables** (`coordination/inference-batch/`) = batch-execution scope.
Enforcement stays flag-gated (`review_decision_enforce`, default off, blocked on the LB-6 budget gate); shadow records only.

### A3 — No stack change for shadow (operator-reaffirmed)
§14.1 proposes a GPU-resident Qwen interim reviewer "to unblock shadow-mode instrumentation." Amended: **shadow mode runs on the existing CPU architect alias** — zero stack change, exactly what §27's smallest-slice needs (it already lists "wrap the existing Qwen interim reviewer behind the typed interface"). The GPU-resident 122B-IQ2 stays an H5 tournament arm behind the operator's GPU bet #2, and ALL stack mutations wait for the parallel session's feature tests. This keeps the semantics layer decoupled from GPU optimization exactly as §23.1/§17-decision-17 recommend.

### A4 — Landed behavioral levers retained (spec is silent on them)
The Wave-1 reviewer plane already shipped levers the spec does not mention: plan-reminders-over-re-review, REJECT_TO_EMPTY, the sticky decision cache, complexity-gated review placement, the autopilot knob manifest (H8), and Consistency-Rate as a metric. These are retained; the semantics layer sits *under* them (the reducer decides; the levers shape when/whether a review happens and how it is cached).

## What landed vs what remains

**Landed (Wave-2, non-inference, tested):** the reducer + 9-class criterion-scoped authority (anti-laundering: an explicit per-evidence grant can narrow but never widen a NO class; logical×execution kept separate so a crash is never a conclusive failure; calibration-gated reviewer authority; bounded-loop terminals); the v1.1 schemas + EvidenceItem/DecisionEnvelope/AssuranceProfile; hash-bound automatic invalidation (DECISION_INVALIDATED events, never rewrites) + the replay query; the durable escalation sink (no dead-state); and §20's contract/evidence-semantics/invalidation/security/injection/evidence-loop test suites + an injection-probe corpus.

**Surfaced as findings (honest gaps, not silently patched):** the injection suite found three gaps in the Wave-1 CandidatePackage sanitizer — (1) no explicit control/data delimiter, so in-content injection text reaches the reviewer prompt (architecturally mitigated by zero-textual-authority, but the text still arrives); (2) no package path-allowlist / secret redaction; (3) silent truncation can drop a buried critical output. These are xfail'd as follow-up trackers and listed in `op-bundle.md`.

**Deferred to the operator's inference loop (spec §21 Phases 1-5):** shadow-mode telemetry accumulation, the near-miss corpus calibration runs, the reviewer tournament (Stage A mechanical qualification onward), and selective-authority promotion — all staged as entries in the consolidated inference-batch manifest (`coordination/inference-batch/`), each with pre-decided forks. The spec's P0-target-model blockers (grammar-crash, glm-dsa reconciliation) were CLOSED by the parallel kernel session mid-campaign.

## References
The spec's grounding references R6/R8/R9/R10/R11/R13/R14/R15 + R3 were dedup-checked and persisted as intake-850..858 (R7 position-bias, R12 Kenton, R16 AutoGen were already ingested).
