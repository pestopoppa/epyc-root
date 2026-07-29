# Plan compliance, verification-in-the-loop, and debate: the architect-side and disagreement-side evidence

**Date:** 2026-07-16
**Companion handoffs:** [`reviewer-decision-plane.md`](../../handoffs/active/reviewer-decision-plane.md) (H3 RD-4/RD-9), [`reviewer-latency-and-sampling-budget.md`](../../handoffs/active/reviewer-latency-and-sampling-budget.md) (H-LB), [`reviewer-escalation-and-human-gate-policy.md`](../../handoffs/active/reviewer-escalation-and-human-gate-policy.md) (H7)
**Sources:** intake-835 (From Plan to Action / plan compliance, 2604.12147, cred 5/6) · intake-842 (Hao et al. plan→SMT, NAACL 2025, 5/6) · intake-843 (Towards Verified Code Reasoning, 2509.26546, 4/6) · intake-840/841 (AI Safety via Debate 1805.00899; Multiagent Debate 2305.14325 + 2024-26 follow-ups)

---

## Plan compliance (architect side) — intake-835

16,991 SWE-agent trajectories: compliance (phase-coverage × order × no-spurious-actions) correlates with success; **plan reminders every ~5 steps improve compliance AND success**; **a subpar plan is worse than no plan**; extra misaligned phases HURT and effects are executor-model-specific. Design consequences (H3 RD-9): plan-review rubric checks structure/alignment, not prose (penalize over-specification); `REJECT_TO_EMPTY` is a first-class outcome; **reminder re-injection is a separate cheap knob PREFERRED over re-review** (one context append vs a heavyweight pass — the direct counter to the 2× plan-review regression); iteration bounds keyed to compliance *trend*; trace rows carry per-step phase tags + executor-model-id. The contradiction literature sharpens rather than refutes: "Learning When to Plan" (2509.03581) shows always-planning degrades long-horizon performance while adaptive gating matched reward at −85% tokens — the empirical charter for the review-trigger/reminder-cadence autopilot knobs (H8). All SWE-domain; re-measure before gating.

## Verification-in-the-loop (verifier adapter ceiling) — intake-842/843

Hao: TravelPlanner 10% (o1-preview) → **93.9%** with the LLM as *translator* and Z3 as the sound decision-maker; the **UNSAT core → guided repair** loop fixed 81.6% of infeasible queries. Sistla: formalizing the agent's *reasoning* catches ~75% (6/8) of wrong judgments prose review would pass — but single-pass coverage is low (18/88; 5× iteration → 36/88) and formalization incompleteness yields **15% false-positives**. Design consequences (H3 RD-4): verifier outcomes are **three-valued** (PASS / FAIL-with-certificate / INCONCLUSIVE — inconclusive returns control to the reviewer; precedence applies only to conclusive verdicts); the **failure certificate IS the request_evidence payload** (guided repair, not blind retry); the adapter is tiered cheap-first (jsonschema/pydantic, invariant asserts, Hypothesis property tests, Soufflé Datalog) escalating to Z3/symbolic only for theory-solver claims — all open-source and CPU-local; formalizers are pluggable per-domain (the pattern generalizes, the encoders don't). Coverage realism: the formally-decidable slice is minority-but-high-value; a large inconclusive residual stays with the reviewer.

## Debate (disagreement side) — intake-840/841 + follow-ups

Honest net: **our regime — strong judge, no information asymmetry, same inputs — is the debate literature's worst case.** The martingale result (Zhu 2601.19921) shows same-input homogeneous debate does not improve expected correctness (vanilla MAD often loses to majority vote); Kenton (2407.04622) finds debate beats direct judging only under information asymmetry; Khan (2402.06782) shows one-sided consultancy actively DEGRADES judges — a persuasive-but-wrong architect could flip a correct reviewer; Du's own gains plateau by ~round 4 at ~6× token cost with a documented confidently-wrong-convergence failure mode. Design consequences (H7): **default on disagreement = ESCALATE**; the only debate artifact that survives is an *opt-in single two-sided rebuttal round* (architect rebuts AND the verifier/original position restates; hard cap 2; latent-evidence disagreements only), enabled per task-class strictly on an offline A/B showing signed net-flip Δ>0 — with the right→wrong flip rate tracked as the safety tail.

## MEASUREMENT note

Every number here is an external observation. The three adopted mechanisms (reminders-over-re-review, certificate-driven request_evidence, escalate-default with gated rebuttal) carry their own local validation tasks in the owning handoffs before any enforce-mode use.
