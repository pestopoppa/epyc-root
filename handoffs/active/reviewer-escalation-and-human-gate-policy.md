# Reviewer Control Plane — Escalation & Human-Gate Policy (H7, stub-grade)

**Status**: stub — deliberately LAST (M4 "governed"); policies derive from H4/H5 evidence that does not exist yet
**Created**: 2026-07-16 (Architect→Reviewer control-plane series; see index)
**Categories**: agent_architecture, safety
**Index**: [`reviewer-control-plane-index.md`](reviewer-control-plane-index.md)
**Gates**: H4 calibration curves + H5 tournament + H-LB LB-6 budget gate; harness-side surfacing additionally gated on HS-4 ([`harness-selection-and-integration.md`](harness-selection-and-integration.md))
**Repo**: `epyc-orchestrator`

## Objective

Convert calibration evidence into policy: confidence thresholds from reliability curves, verifier-disagreement escalation, protected-action human gates. Human-in-the-loop is a policy boundary, not a crutch — sparse but deliberate.

## Thesis (evidence-shaped)

**Default on disagreement = ESCALATE.** Our regime (strong judge, no information asymmetry, same inputs) is the debate literature's worst case: same-input homogeneous debate is a martingale (no expected-correctness gain); debate beats direct judging only under information asymmetry; one-sided consultancy actively DEGRADES judges — a persuasive-but-wrong architect could flip a correct reviewer (intake-840/841 + follow-ups). A rebuttal round exists only as an opt-in, evidence-gated pre-escalation step.

## Prioritized Task List

- [ ] **HG-1 — Threshold policy** from H4/H5 reliability-by-confidence-bucket curves (per-domain).
- [ ] **HG-2 — Verifier-disagreement rule**: reviewer vs conclusive-gate conflict → escalate (fa/fr_candidate events already fire mechanically per H3 RD-3); inconclusive-gate conflicts stay with the reviewer.
- [ ] **HG-3 — Protected-action list** aligned with existing SafetyGate: deploy, baseline change, MEASUREMENT-adjacent edits, protected-branch merges, DB migrations.
  - [x] **Scoping audit ✅ 2026-07-29 (mainA) — the premise is wrong; corrected here so HG-3 is actionable when it unblocks.** Two defects found:
    **(1) There is no "existing SafetyGate" to align to.** `epyc-orchestrator/scripts/autopilot/safety_gate.py` is AutoPilot's *baseline/quality regression* gate (`REGRESSION_THRESHOLD`, tier baselines, Pareto-archive ratchet). It does no action typing at all. A repo-wide grep for `protected_action` / `PROTECTED_ACTIONS` returns **nothing** — no action-typed gate exists anywhere in the codebase.
    **(2) The real enumeration is path- and branch-scoped, not action-scoped.** It is `coordination/session-bus/human_only_paths.yaml` (itself human-amendment-only, hash-pinned, hook-enforced) plus `BUS_PROTOCOL.md` rule 6. Mapping HG-3's five named actions onto it: *baseline change* → `orchestration/autopilot_baseline.yaml` ✅; *MEASUREMENT-adjacent edits* → `MEASUREMENT.md` + `agents/shared/MEASUREMENT_POLICY.md` ✅; *protected-branch merges* → the `branches:` block, `production-consolidated-*` ✅; **deploy → nothing**; **DB migrations → nothing**. So two of the five have no enumeration behind them and HG-3 cannot "align" to a list that does not cover them.
    **Corrected scope for HG-3 when it runs**: either (a) extend `human_only_paths.yaml` to cover deploy and DB-migration surfaces — note that file is a trust boundary, so this is a token-request, not an agent edit; or (b) narrow HG-3 to the three actions that already have enforcement and say explicitly that deploy/DB-migration are out of scope. Do **not** write an action list that has no enforcement behind it — that produces a policy document asserting protection that nothing implements.
  - [ ] **HG-3 is BLOCKED on HG-1, contrary to the dispatch queue.** The Dependency Graph below reads `H4 curves + H5 winners → HG-1 → HG-2/HG-3`, and HG-1 is open. `BACKLOG-DISPATCH-QUEUE.md` TOP-40 #6 classifies this row as `none` lane with **no blocker**, which is wrong. Same defect class as the queue's runbook-template rows (auditor, `msg-20260729T160627Z`) and its already-closed rows: **a row that looks dispatchable but is not.** Queue classification should consult the owning handoff's dependency graph, not just the checkbox.
- [ ] **HG-4 — Escalation-precision human-audit protocol**: sampling rate + operator cadence (operator decision, OP bundle — escalation precision is undefined without it).
- [ ] **HG-5 — Server-side surfacing**: `/v1` response fields + `x_*` override to force/suppress escalation (harness-agnostic cooperation pattern per `hermes-outer-shell.md` L55-69).
- [ ] **HG-6 — OPTIONAL single two-sided rebuttal round** (pre-escalation): architect rebuts AND verifier/original position restates; reviewer re-judges the contrastive pair; hard cap 2 rounds; **restricted to latent-evidence disagreements** (something checkable to surface — never style/preference); enabled per task-class ONLY after an offline A/B shows **signed net-flip Δ>0** (wrong→right ≫ right→wrong; the right→wrong tail is the safety metric, tracked continuously). Never one-sided; never multi-round-to-convergence.
- [ ] **HG-7 — Harness-side UX**: FROZEN pointer until HS-4 resolves — state the gate, do no work.
- [ ] **HG-8 — Policy A/B** under P-AB-1 + P-REV-1; promotion per H-LB LB-6.

## Dependency Graph

```text
H4 curves + H5 winners → HG-1 → HG-2/HG-3 → HG-8
HG-4 operator cadence (OP bundle) → escalation-precision measurable
HG-5 server-side (anytime after H3) ; HG-6 gated on its own offline A/B ; HG-7 frozen on HS-4
```

## Cross-Cutting Concerns

1. **Layer B boundary** — acting on escalations inside an agent loop needs the cooperating harness; server-side surfacing (HG-5) is the harness-agnostic interim.
2. **Cost** — a rebuttal round ≈ 2-3× a review call amortized by P(disagreement); cheaper than escalation only if accuracy-neutral-or-better — measure, don't assume.

## Reporting Instructions

Flip checkboxes `✅ YYYY-MM-DD`; HG-4 cadence + HG-6 enablement are operator decisions (§A00); all policy claims cite P-REV-1 + LB-6.

## Evidence Base (intake)

intake-840/841 debate regime analysis (martingale, consultancy degradation, plateau/cost) · intake-836 overcorrection tail · intake-846 HITL-as-policy-boundary · audit doc 2026-07-16.
