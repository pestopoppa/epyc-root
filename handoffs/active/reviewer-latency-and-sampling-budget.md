# Reviewer Control Plane — Latency & Sampling Budget (H-LB)

**Status**: active — cross-cutting; **blocks ALL enforce-mode** anywhere in the series
**Created**: 2026-07-16 (Architect→Reviewer control-plane series; see index)
**Categories**: agent_architecture, cost_aware_routing, benchmark_methodology
**Index**: [`reviewer-control-plane-index.md`](reviewer-control-plane-index.md)
**Related**: [`reviewer-decision-plane.md`](reviewer-decision-plane.md) (RD-12 supplies the baseline), [`autopilot-control-plane-integration.md`](autopilot-control-plane-integration.md) (tunes these knobs)
**Repo**: `epyc-orchestrator`

## Objective

Make review latency a governed, first-class budget. The 2026-07-16 regression is the motivating fact: plan-review/eval-routing overhead **halved** eval throughput (~68 backend requests + 11-17 architect plan-review prompts per 50-question replay; reroute bug fixed `bc8d3303` but the structural cost remains). Architect↔Reviewer handshakes multiply this; no enforcement until the budget gate passes.

## Thesis

The literature quantifies the tax: multi-role pipelines ~2-3× cost / ~8-10× latency (intake-839 critique lit); multi-agent ~15× tokens with token usage explaining 80% of outcome variance; on a single host, parallel-reviewer latency models as **SUM not MAX** (intake-846). The counter-levers are structural (two-turn rubric, reminders-over-re-review, complexity gating, final-aggregate review, sticky cache — all in H3) plus governed budgets tuned by the autopilot. The standing floor: **the plane must beat a single augmented LLM on the same tasks** (M3 baseline floor) — a control plane that only adds cost gets deleted, per the Fable5 enforcement-not-theory posture.

## Prioritized Task List

- [ ] **LB-1 — Reproduce + attribute the regression**: which calls dominate (plan-review prompt count vs prompt length vs architect queueing) on the RD-12 replay baseline.
- [ ] **LB-2 — Budget targets**: per-decision tokens + latency_ms; per-session review caps (reuse `IterationContext.max_iterations`/`max_total_iterations`); token-multiplier as a governed knob (target multiplier vs single-model baseline).
- [ ] **LB-3 — Sampling policies**: review only COMPLEX/escalated tasks (reuse `TaskComplexity`); k% sampling; quick_mode tiering (QUICK_REVIEW_PROMPT exists); reminder-instead-of-review substitution rate; fan-out gated by task type + effort-scaling rules (1 agent/3-10 calls simple … 2-4 agents comparisons).
- [ ] **LB-4 — Paired throughput A/B per policy** under P-AB-1 + P-SPEED-OBJ (task-rate axis, e-process — never single-trial); parallel-reviewer wall-clock modeled as SUM on-host (exception: NUMA-split or MI210-offloaded reviewer).
- [ ] **LB-5 — Budget-enforcement knobs** in features/delegation config; declared in the guarded numeric-surface manifest (H8 class 1).
- [ ] **LB-6 — THE BUDGET GATE**: define the (quality gain per throughput cost) threshold that `review_decision_enforce` and H7 policies must satisfy. Threshold VALUE is an operator decision (OP bundle); this task defines the metric and decision procedure.
- [ ] **LB-7 — M3 baseline floor measurement**: full plane (shadow→enforce candidate config) vs single-augmented-LLM baseline (A0/A1 arms) on the same tasks — the go/no-go the whole series answers to.
- [ ] **LB-8 — Publish standing numbers** into the index (H0) cross-cutting section.

## Dependency Graph

```text
H3 RD-12 baseline → LB-1 → LB-2 → LB-3 → LB-4 → LB-6 gate → (unblocks enforce-mode in H3/H7)
LB-5 (with LB-2/3) → H8. LB-7 needs H4 instrument + H5 anchor arms. LB-8 continuous.
```

## Cross-Cutting Concerns

1. **CPU economics** — decode is BW-bound; every review token competes with production traffic; "better reviewer model beats bigger token budget" (intake-846) favors fidelity + caching over volume.
2. **GPU relief valve** — drafter Stage-1 and architect-residency (operator GPU bets 1-2) directly reduce review-turn latency; teleport (bet 4) helps long review turns; cross-ref `mi210-big-model-and-acceleration-roadmap.md`.

## Key Files / Surfaces

- `src/proactive_delegation/` (IterationContext, complexity, QUICK_REVIEW_PROMPT), `src/features.py`
- `scripts/autopilot/eval_tower.py` replay harness; P-AB-1/P-SPEED-OBJ protocols (MEASUREMENT.md)

## Reporting Instructions

Flip checkboxes `✅ YYYY-MM-DD`; LB-6 threshold proposal → operator decision queue (§A00); standing numbers mirrored to H0; any enforce-mode flip anywhere cites LB-6 passage.

## Evidence Base (intake)

2026-07-16 throughput-regression checkpoint (master index) · intake-839 multi-role tax + single-model baseline · intake-846 15×/SUM-not-MAX/effort rules · intake-835 reminders-over-re-review + adaptive gating (2509.03581) · intake-849 P5 guardrail placement · audit doc 2026-07-16.
