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
- [x] **LB-2 — Budget targets** ✅ 2026-07-17 (targets DEFINED below — see "LB-2 Budget targets (proposed)"; all numbers **PROPOSED/observation-grade**, pending LB-4 paired A/B confirmation + operator ratification): per-decision tokens + latency_ms; per-session review caps (reuse `IterationContext.max_iterations`/`max_total_iterations`); token-multiplier as a governed knob (target multiplier vs single-model baseline).
- [ ] **LB-3 — Sampling policies**: review only COMPLEX/escalated tasks (reuse `TaskComplexity`); k% sampling; quick_mode tiering (QUICK_REVIEW_PROMPT exists); reminder-instead-of-review substitution rate; fan-out gated by task type + effort-scaling rules (1 agent/3-10 calls simple … 2-4 agents comparisons).
- [ ] **LB-4 — Paired throughput A/B per policy** under P-AB-1 + P-SPEED-OBJ (task-rate axis, e-process — never single-trial); parallel-reviewer wall-clock modeled as SUM on-host (exception: NUMA-split or MI210-offloaded reviewer).
- [ ] **LB-5 — Budget-enforcement knobs** in features/delegation config; declared in the guarded numeric-surface manifest (H8 class 1).
- [ ] **LB-6 — THE BUDGET GATE** — ⏳ metric + decision procedure DRAFTED ✅ 2026-07-17 (see "LB-6 Budget-gate metric + decision procedure"); **checkbox stays OPEN — threshold VALUE is an operator decision (OP-5b), not yet picked**: define the (quality gain per throughput cost) threshold that `review_decision_enforce` and H7 policies must satisfy. Threshold VALUE is an operator decision (OP bundle); this task defines the metric and decision procedure.
  - [x] **LB-6a — gate metric + decision procedure drafted** ✅ 2026-07-17 (metric, who-runs-what, re-eval cadence, FA/FR auto-demote linkage, and 2–3 candidate thresholds for the operator recorded below).
  - [ ] **LB-6b — operator picks threshold (OP-5b)**: choose one of the candidate thresholds (or a variant) → operator decision queue §A00; until picked, no enforce-mode flip anywhere in the series.
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

## Budget Definitions (appended 2026-07-17 — design/spec only; wave-2 agent owns features/config)

Design/spec for LB-2 and LB-6. **No orchestrator code here** — a wave-2 agent implements the features/config knobs (LB-5) and runs the paired A/Bs (LB-4). Every number is **PROPOSED / observation-grade** until confirmed under **P-AB-1** (paired task-rate A/B) + **P-SPEED-OBJ** (task_rate axis); none may gate an enforce-mode flip on its own.

### LB-2 Budget targets (proposed)

**Stack facts used as anchors** (observation-grade decode rates, single-model, 96t canonical unless noted; re-confirm under P-BENCH/P-SPEED before gating): architect ~18–21 t/s CPU, frontdoor 24.3 t/s, worker 44.7 t/s; **rubric grading is cheap-model (worker-tier) work**; on this host parallel-reviewer wall-clock models as **SUM not MAX** (intake-846). Latency budgets below are derived as `tokens ÷ t/s` on the arm that performs that decision, then rounded up for prompt/queue overhead — they are ceilings, not forecasts.

| Decision type | Actor (typical) | Token budget (out) | Latency budget (ms) | Notes |
|---|---|---|---|---|
| **plan-review** | architect (~18–21 t/s) | ≤ 350 | ≤ 22,000 | one pass per plan; reminders-over-re-review (intake-835) preferred to a second pass |
| **candidate-review** | reviewer (CPU GLM low t/s / GPU-resident) | ≤ 300 | ≤ 18,000 (CPU) / ≤ 6,000 (GPU-resident) | GBNF-constrained verdict; SUM-not-MAX if run parallel to production |
| **rubric-authoring** | strong model (architect-tier) | ≤ 800 | ≤ 45,000 | **amortized** — authored once per task-type, sticky-cached (H3); cost divided over all items it grades |
| **rubric-grading** | cheap grader / worker (~44.7 t/s) | ≤ 180 | ≤ 5,000 | high-frequency per-item path; keep it cheap (intake-834 grading-model insensitivity 2.4pp) |

- **Per-session caps** (reuse `IterationContext` semantics): `max_review_iterations` ← reuse `IterationContext.max_iterations` (per-task ceiling on review turns, proposed default **2**); `max_total_review_iterations` ← reuse `IterationContext.max_total_iterations` (per-session ceiling across all tasks, proposed default **scale with session task count, cap the review-token share — see multiplier below**). Review turns count against the same iteration ledger so a runaway Architect↔Reviewer handshake trips the existing budget, not a new one.
- **Token-multiplier knob** (`review_token_multiplier`): the governed ratio of **total tokens with the plane** ÷ **single-augmented-LLM baseline tokens on the same tasks** (LB-7 / A0–A1 arms). Literature tax is ~2–3× cost / ~8–10× latency for multi-role pipelines (intake-839); multi-agent ~15× tokens (intake-846). **Proposed target ≤ 1.5× (stretch 1.3×), hard ceiling 2.0×** — above the ceiling the plane auto-throttles review fan-out (sampling policies, LB-3) rather than spend. The multiplier is the single knob the autopilot (H8) tunes; it composes with, and is bounded by, the LB-6 gate.
- All targets are **PROPOSED**; confirm each under LB-4 (P-AB-1 + P-SPEED-OBJ) before any enforce-mode flip.

### LB-6 Budget-gate metric + decision procedure (proposed; threshold value = operator decision OP-5b)

**Gate metric — quality-gain-per-throughput-cost.** On **paired replays** (same task set, same seeds, plane arm vs single-augmented-LLM baseline arm A0/A1) under **P-AB-1** (N ≥ 100) with the throughput axis under **P-SPEED-OBJ** (task_rate = questions / eval-wall-hour, e-process, never single-trial):

```
G = ΔP(success) / (% throughput reduction)
    ΔP(success)          = P(success | plane) − P(success | single-LLM baseline)   [pp, higher-better]
    % throughput reduction = 100 × (task_rate_baseline − task_rate_plane) / task_rate_baseline   [higher = costlier]
```

Enforce-mode for a reviewer configuration requires **BOTH**: (1) `G ≥ threshold` **and** net `ΔP(success) > 0` measured as above (the budget gate), **and** (2) the config is not in FA/FR breach (the calibration gate — RC-5). The two gates are orthogonal: a config can pass budget yet fail calibration, or vice versa; enforce needs both green. If `task_rate_reduction ≤ 0` (plane is *faster*), the gate reduces to `ΔP(success) > 0` (pure win, no cost to trade).

**Decision procedure.**
- **Who / what**: the H8 autopilot proposes an enforce-candidate config and runs the paired replay (placement via the eval fan-out path, not `/chat`; respects no-concurrent-inference + operator bench window). It computes `G`, `ΔP(success)`, `% throughput reduction`, and the FA/FR e-process state, and writes them in P-AB-1 / P-REV-1 grammar. **The operator ratifies the threshold value (OP-5b)** — agents never self-approve a gate threshold (measurement trust boundary is human-amendment-only).
- **When re-evaluated**: on every enforce-candidate config; on any instrument-era change (P-REV-1 instrument version bump, corpus revision, kernel cutover); and continuously in shadow so a live config that drifts below threshold is caught.
- **Auto-demote linkage**: the budget gate hooks the **same** demotion machinery as FA/FR — a live config whose measured `G` falls below threshold (or `ΔP(success)` goes ≤0) auto-demotes reviewer enforcement to **shadow** via `sequential_verdict.py` (`EProcessState`/`SequentialPolicy`, RC-5), exactly as an FA/FR-tolerance breach does. One demotion path, two trigger families (calibration + budget).

**Candidate thresholds — FOR THE OPERATOR TO PICK (do not self-select):**
| # | Threshold (`G` = pp ΔP(success) per 10% throughput cut) | Guardrails | Rationale |
|---|---|---|---|
| **T-conservative** | `G ≥ 0.5` (≥0.5pp quality per 10% throughput lost) | net ΔP(success) ≥ +2pp **and** throughput reduction ≤ 25% | protects production task-rate; the plane must clearly earn its cost — matches "a control plane that only adds cost gets deleted" (Fable5). Fewest configs pass. |
| **T-moderate** | `G ≥ 0.25` | net ΔP(success) ≥ +1pp **and** throughput reduction ≤ 40% | balances quality lift against the ~2–3× literature tax; expects GPU relief valves (bets 1–2) to absorb some cost. |
| **T-liberal** | `G > 0` | net ΔP(success) > 0 (any real gain) **and** throughput reduction ≤ 50% | maximizes quality capture where correctness matters more than throughput; only viable if spare capacity / off-peak review windows exist. |

Each threshold pairs a **rate** (`G`) with an **absolute floor** (net ΔP) and an **absolute cost ceiling** (max throughput reduction) so a tiny quality gain bought at ruinous cost cannot pass on the ratio alone. The operator picks one (or a variant) → §A00 decision queue (OP-5b). Standing floor cross-ref: whichever threshold is chosen, the plane must still clear **LB-7** (beat a single augmented LLM on the same tasks) — the go/no-go the whole series answers to.
