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
