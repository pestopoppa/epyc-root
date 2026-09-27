# Decision-Aware Routing — completed scope through 2026-09-27

> **Historical ledger only; current work lives in [../active/decision-aware-routing.md](../active/decision-aware-routing.md).**
> Moved verbatim at the 2026-09-27 wrap-up (workspace-8d). Every range here was closed when moved (zero open boxes).
> Superseded intake updates and the April dependency graph: [archived history](../archived/decision-aware-routing-history-through-2026-09-27.md).

## DAR-1 / DAR-1 replays / DAR-2 / DAR-1.5 (moved from § Implementation Phases)

### DAR-1: Offline Regret Analysis — ✅ 2026-04-15

Script: `scripts/analysis/dar1_regret_analysis.py`. Results from 7,211 routing decisions (Apr 10-14):

- **96% uniform Q-values** (<0.001 spread) — Q-scorer has barely learned preferences
- Selection score spread is non-trivial (median 0.107) — comes from cost/similarity terms, not Q-values
- 25% trivial spread (<0.01), 75% have meaningful differentiation via cost terms
- 3,355 learned decisions vs 3,856 rules/classifier decisions
- **Implication**: Q-values are not driving routing decisions — cost and similarity dominate. This confirms the predict-then-optimize pathology: the Q-values are decorative, not decision-driving.

**Next step**: DAR-2 contrastive training has limited Q-signal to work with. Two paths:
1. Accumulate more routing memories via seeding (need 500+ updated memories; currently 419 with update_count > 0)
2. Proceed with DAR-2 anyway — contrastive loss will sharpen the few memories that DO have signal, and new routing decisions will accumulate contrastive-trained Q-values faster than current TD learning

### DAR-1 Current-Traffic Replay — ✅ 2026-06-12

Report: `epyc-orchestrator/orchestration/reports/dar1_regret_replay_2026-06-12.md`.

Replay window: 2026-06-05..2026-06-12 progress JSONL. Result: 12,057 routing decisions analyzed, 11,249 matched task outcomes, 8,145 regret-identifiable decisions, 0.00% identifiable mean regret, 99.1% uniform Q-values, 95.2% trivial selection-score spread.

Gate verdict: DAR-3/SPO+, DAR-6 swarm expansion, Package I, and broader learned-routing expansion remain frozen. Historical rules/classifier rows lacked candidate action IDs, so `epyc-orchestrator` `1dfbc22` added `action_topk` telemetry for future replays.

### DAR-1 Current-Traffic Replay — ✅ 2026-07-03

Report: `epyc-orchestrator/orchestration/reports/dar1_regret_replay_2026-07-03.md`.

Replay window: 2026-06-13..2026-07-03 progress JSONL. Result: 22,992 routing decisions analyzed, 20,477 matched task outcomes, 22,677 regret-identifiable decisions (98.6%), 0.00% gate regret, 99.6% uniform Q-values, 95.4% trivial selection-score spread, and 27,335 try-cheap-first counter rows.

Gate verdict: unchanged. DAR-3/SPO+, DAR-6 swarm expansion, Package I, and broader learned-routing expansion remain frozen because no >=5% mean decision-regret signal was proven.

### DAR-2: Contrastive Q-Score Update — ✅ 2026-04-15

- [x] Added `_compute_contrastive_adjustment()` method to `q_scorer.py` (~65 lines)
- [x] Contrastive term is additive to reward signal in `_score_task()`, NOT a modification to `_compute_reward()`
- [x] Feature flag `CONTRASTIVE_Q_UPDATES` (ON by default, disable with env var `CONTRASTIVE_Q_UPDATES=0`)
- [x] Routing memories use contrastive-adjusted reward; escalation memories use base reward
- [x] Bounded: max adjustment ±0.1, margin=0.05. With α=0.1, max extra Q-shift per update = 0.01
- [x] Skips memories at default Q=0.5 (the 96% unlearned) — only fires when alternatives have learned Q-values
- [x] Full logging: `DAR-2 contrastive: adj=X.XXXX reward=Y.YYY→Z.ZZZ task=...`
- [x] 5,285 tests pass (flag ON and OFF), 0 regressions. GitNexus re-indexed.
- [x] `episodic.db.backup-20260415` created before activation
- [x] Add dedicated unit test for `_compute_contrastive_adjustment()` with mock store — **DONE 2026-04-17**: `TestComputeContrastiveAdjustment` class with 13 tests in `tests/unit/test_q_scorer.py`

**Implementation**: Added in `_score_task()` between reward computation and `_update_routing_memory()`. The method retrieves top-10 similar routing memories, compares selected model's Q-value against alternatives with learned Q-values, and computes a bounded adjustment that sharpens the decision boundary. Zero adjustment when ranking is already correct with sufficient margin.

**Files**: `q_scorer.py` (L31 flag, L271-282 integration, L457-520 method)

### DAR-1.5: REINFORCE-Pathology Audit (NEW 2026-04-26 — analytical, no code)

**Source**: deep-dive [`research/deep-dives/trinity-evolved-llm-coordinator-methodology.md`](../../research/deep-dives/trinity-evolved-llm-coordinator-methodology.md) Section 2.2.

**Trigger**: Trinity's Table 4 shows REINFORCE collapses to **0.253 LCB / 0.459 Math500** at the same training budget where sep-CMA-ES achieves **0.615 / 0.880**. The paper attributes this to the loss surface being block-ε-separable — pure policy-gradient methods get drowned in off-block noise. DAR-3 (SPO+) and DAR-4 (bilinear scorer) are NOT pure REINFORCE — they use closed-form gradients on contrastive losses — but the question is whether the same geometry hurts them in a milder form.

**Goal**: a written analytical audit (no code, no rerun) answering: do the gradients used in DAR-2 (contrastive Q-update, ALREADY LANDED), DAR-3 (SPO+), and DAR-4 (bilinear scorer) share REINFORCE's vulnerability to off-block noise on a block-ε-separable loss? If yes for any of DAR-3/DAR-4, document the mitigation before implementation begins.

- [x] **DAR-1.5.1** ✅ 2026-05-07 — Gradient forms tabulated. Per-action Q-table (DAR-2/3 substrate) is `ε_H=0` block-diagonal trivially; bilinear scorer (DAR-4) has high `ε_H` by design via shared W. See "DAR-1.5 audit deliverable" sub-section below for the table.
- [x] **DAR-1.5.2** ✅ 2026-05-07, resolved by P4.2 on 2026-06-27 — Cross-reference written. P4.2 later resolved the conditional branch: full-rank dominates, so DAR-4 proceeds full-rank for the current trained-label surface.
- [x] **DAR-1.5.3** ✅ 2026-05-07 — Mitigations enumerated per architecture. Per-action Q-table: none needed. Bilinear: (b) rank-restrict W ≤ k as cheapest first defense if P4.2 confirms separability. (a/c/d) documented as follow-ups.
- [x] **DAR-1.5.4** ✅ 2026-05-07 — Decision-gate verdict: **DAR-3 PROCEED unconditionally** (per-action substrate has ε_H=0 by construction); **DAR-4 CONDITIONAL on P4.2** (rank-restrict if separability confirmed, full-rank if falsified); **DAR-4b PROCEED** (inference-time blending, no training); **DAR-5 conditional on DAR-4 + P4.2** (adds more shared parameterization, inherits constraint).

**Effort**: 1 session, analytical only. No infra, no code. Deliverable is a markdown sub-section appended to this handoff.

**Why this matters even if it changes nothing**: it produces a *first-principles* answer to "does Trinity's REINFORCE result transfer to us?" — which the project repeatedly needs when reasoning about new optimizer choices. Cheap insurance against making the wrong optimizer call later.

## DAR-1.5 audit deliverable — REINFORCE-Pathology Cross-Check (2026-05-07)

**Status**: ANALYTICAL DELIVERABLE COMPLETE. Captured here per the handoff's "Deliverable is a markdown sub-section appended to this handoff" directive. Cross-reference with [`learned-routing-controller.md`](../active/learned-routing-controller.md) P4.2 + the Trinity deep-dive Section 2.2.

### Premise

Trinity (intake-474) reports that REINFORCE collapses to **0.253 LCB / 0.459 Math500** under the same compute budget where sep-CMA-ES achieves **0.615 / 0.880**. The paper attributes this to the loss surface being *block-ε-separable* (Section 1.5 of deep-dive: scaled Hessian `H_S(θ) = S^(1/2) H(θ) S^(1/2)` is uniformly nearly block-diagonal with inter-block coupling `ε_H` ∈ [0, 1)). Pure policy-gradient methods get drowned in off-block noise on this geometry; diagonal CMA gets `Ω(1/n)` per-iteration contraction after stabilization.

The question DAR-1.5 must answer: **do the gradient forms used in DAR-2 / DAR-3 / DAR-4 share REINFORCE's vulnerability to off-block noise on a block-ε-separable loss?**

### DAR-1.5.1 — Gradient forms per loss

| Loss | Functional form | Gradient form | Parameter coupling pattern |
|---|---|---|---|
| **REINFORCE** (Trinity baseline) | `L = -E[A · log π(a\|s; θ)]` | `∇L = -∇log π(a\|s; θ) · A` (A = scalar advantage) | Couples ALL parameters of the policy network through ∇log π. On a deep network: `ε_H ≈ 1` (every layer couples everything). On a per-action softmax: `ε_H > 0` via partition function. |
| **DAR-2 contrastive Q** (LANDED) | `L_contrast = max(0, Q[alt] + margin − Q[chosen])` | `∇L = -∇Q[chosen] + ∇Q[alt]` when margin violated | Q is a **per-action discrete table**: `Q[a] = θ[a]`. Gradient touches ONLY the two scalar entries θ[chosen] and θ[alt]. **`ε_H = 0` exactly — block-diagonal trivially.** |
| **DAR-3 SPO+** (planned) | `L_SPO+ = Σⱼ max(0, 2c_hat[j] − c_true[j]) − c_hat[i*] + c_true[i*]` | `∇L = Σⱼ 2 ∇c_hat[j] · 𝟙{2c_hat[j] > c_true[j]} − ∇c_hat[i*]` | If `c_hat[j] = θ[j]` (per-action table, our existing Q-scorer): same as DAR-2, **`ε_H = 0` block-diagonal**. If `c_hat[j] = f(θ_shared, x_j)` (parameterized scoring, e.g. layered atop DAR-4): off-block coupling appears via shared `θ_shared`. |
| **DAR-4 bilinear scorer** (planned) | `Q(prompt, model) = σ(v_m^T W v_p + b)` | `∇L_W = (∂L/∂z) · σ'(z) · v_m v_p^T` (rank-1 outer product) | **Single shared W matrix used for all actions.** A single (m, p) update perturbs every other (m', p') pair through the shared `W`. **`ε_H ≈ 1` by design** — bilinear coupling is the architectural choice, not an accident. |

The key insight: **REINFORCE's pathology is parameter coupling × high-variance scalar advantage**, not the loss form per se. Block-ε-friendliness is determined by the **structural coupling pattern of the scorer**, not the loss:

- **Per-action Q-table** (DAR-2 today, DAR-3 if kept on the same substrate): `ε_H = 0` exactly. Each θ[a] is structurally independent. No off-block noise can hurt the update.
- **Shared parameterization** (DAR-4 bilinear, or any deep network): `ε_H > 0`. Updates couple across actions through shared parameters. The same geometry that hurts REINFORCE on deep policies hurts ANY gradient-based method on the same architecture — the coupling pattern is what matters, not whether the gradient comes from policy-gradient or a closed-form contrastive surrogate.

### DAR-1.5.2 — Cross-reference with LRC P4.2

`learned-routing-controller.md` P4.2 ("block-ε-separability diagnostic, medium cost") is **COMPLETE as of 2026-06-27**. The 80K-row offline diagnostic trained the existing 2-layer routing head under full-rank, block-diagonal-10, and diagonal-only connectivity. Result: full-rank `81.09%` validation accuracy, block-10 `56.55%`, diagonal `49.33%` (matching the majority baseline). This falsifies the "block-10 ≈ full-rank" premise for the current episodic-label classifier.

**DAR-1.5 conclusions become load-bearing if and only if P4.2 confirms our landscape IS block-ε-separable**:

- P4.2 says "full-rank dominates by ≥2 points" by a wide margin (`+24.54pp` over block-10) → our current routing-label landscape requires shared structure → DAR-4 bilinear's shared parameterization is appropriate; rank-restriction / sep-CMA-ES are not the default mitigation for this surface.

DAR-1.5's rank-restriction branch is now closed negative for the current trained-label classifier. Re-open it only for a materially different cold-start/no-label surface.

### DAR-1.5.3 — Mitigations (if P4.2 confirms block-ε-separability)

Per loss/architecture:

| Component | Pathology risk | Mitigation |
|---|---|---|
| DAR-2 contrastive Q (LANDED) | None (`ε_H = 0` exactly by per-action table) | None needed |
| DAR-3 SPO+ on per-action table | None (inherits per-action structure) | None needed |
| DAR-3 SPO+ on bilinear scorer | Same as DAR-4 (coupling from shared W) | Not currently planned to layer SPO+ over bilinear; if it ever happens, apply DAR-4's mitigations |
| DAR-4 bilinear scorer | High coupling by design — `W` shared across all (m, p) pairs | (a) **L1 / nuclear-norm regularization on W** to favor low-rank solutions empirically. (b) **Rank-restrict W** to rank ≤ k (e.g., k=8 matching Trinity's effective block count). (c) **Outer sep-CMA-ES loop on W** — Trinity's recipe directly applied. (d) **Accept and proceed** if P4.2 evidence is borderline. |

Recommended preference order: (b) rank-restriction is the cheapest first defense and aligns with Trinity's empirical evidence (block-diagonal-10 head retained competitive performance on Math500). (a) regularization is a follow-up if (b) underperforms. (c) sep-CMA-ES is the heaviest mitigation, only justified if (a) and (b) both underdeliver — and would graduate DAR-4 from "decision-aware loss reshape" to the full Trinity-style optimizer rewrite tracked under LRC P4.4.

### DAR-1.5.4 — Decision gate before DAR-3

Per the handoff's gate criterion ("if DAR-1.5 flags a high-confidence pathology and P4.2 confirmed block-ε-separability, pause DAR-3/4 and reconsider"):

- **DAR-3 (SPO+ on existing per-action Q-table)**: ✅ **PROCEED as planned, NO mitigation required**. The per-action table architecture has `ε_H = 0` exactly; no coupling pattern can carry the off-block-noise pathology. Trinity's REINFORCE result does NOT transfer to DAR-3 because the failure mode is architectural (deep-policy parameter sharing), and our existing Q-scorer is structurally a discrete lookup, not a deep parameterized policy.
- **DAR-4 (bilinear scorer)**: ✅ **PROCEED full-rank for the current trained-label surface**. P4.2 says NOT block-ε-separable; the W-coupling is the signal to learn, not a pathology to mitigate.
- **DAR-4b (preference vector + cost τ)**: ✅ **PROCEED as planned**. DAR-4b is inference-time blending of an already-trained scorer; gradient form is N/A (no training in DAR-4b). Whatever DAR-4 produces gets re-weighted at serve time.
- **DAR-5 (IRT + learned model identity vectors)**: 🟡 **CONDITIONAL on DAR-4 outcome, but not blocked by P4.2 for the current surface**. DAR-5 adds more shared parameterization; P4.2 does not argue against that coupling here.

### Why this matters even if it changes nothing

The audit produces a *first-principles* answer to a question the project repeatedly hits when reasoning about new optimizer choices: "does Trinity's REINFORCE result transfer to us?" The conclusion is sharper than "maybe":

- **For per-action Q-table architectures** (DAR-2, DAR-3): NO. Block-diagonal by construction. Trinity's negative result for REINFORCE does not transfer.
- **For shared-parameterization architectures** (DAR-4 bilinear, DAR-5, future deep policies): YES, conditionally. If our landscape is block-ε-separable (P4.2 question), shared parameterization is fighting the geometry, and the entire family of gradient-based methods (REINFORCE, SPO+, contrastive) on that architecture suffers similar pathology.

The unblocking insight: **the architectural choice (per-action vs shared) determines `ε_H`, and `ε_H` determines whether ANY gradient-based optimizer is appropriate.** Trinity's optimizer-vs-architecture confound is unwound: their negative result for REINFORCE is really a negative result for *gradient methods on coupled architectures over block-ε-separable geometry*. ES wins because it doesn't propagate gradients through the coupling.

### Recommended follow-ups

1. **Proceed with full-rank DAR-4 as the default trained-label architecture**; do not add rank restriction unless a future surface produces different P4.2 evidence.
2. **Keep sep-CMA-ES scoped to true cold-start/no-label surfaces**, not the current routing-label classifier.
3. **Use the P4.2 report as the cited gate artifact**: `/mnt/raid0/llm/epyc-orchestrator/orchestration/reports/p42_block_separability/report_20260627_sample80k.json`.

### Status

DAR-1.5 audit COMPLETE 2026-05-07; P4.2 gate resolved 2026-06-27. Decision-gate verdict: **DAR-3 unblocked** (no mitigation), **DAR-4 full-rank for the current trained-label surface**, **DAR-5 not blocked by P4.2 but still conditional on DAR-4 evidence**.

## Reward-saturation audit tables (2026-07-21; moved from § Reward-Saturation Audit)

Method: reward recovered by inverting `initial_q = 0.5 + reward*0.5` ⟹ `reward = 2q − 1`, over the 659,785 `update_count=0` rows (the 99.69% that were never TD-updated, i.e. still at write-time reward).

**Condition 1 — reward IS saturated. MET.**
| reward | count | share |
|---|---:|---:|
| +1.0 | 587,509 | **89.05%** |
| −0.4 | 47,802 | 7.25% |
| 0.0 | 7,460 | 1.13% |
| +0.9 | 5,216 | 0.79% |
| +0.7 | 2,614 | 0.40% |
| all others | <700 | <0.1% |

Per-decision reward entropy (0.1-bin) = **0.6877 bits**; binary (r==1 vs else) = **0.4985 bits**. Effectively trimodal — success / neutral / penalty — not a graded signal.

**Condition 2 — but the reward DOES separate roles. NOT MET.** Role-conditional means (`action_type='routing'`):
| role | n | mean reward |
|---|---:|---:|
| ingest_long_context | 59,724 | +0.9398 |
| architect_general | 61,435 | +0.9305 |
| worker_vision | 31,100 | +0.9193 |
| coder_escalation | 86,868 | +0.9118 |
| frontdoor | 287,686 | +0.8518 |
| worker_general | 127,183 | +0.7788 |

Spread = 0.2212 ⟹ **11.06pp**, or **8.05pp** excluding the degenerate `toolrunner` (n=616, all r=1.0). Either way ≫ the 2pp threshold. Standard errors are ≤0.0019, so the ordering is not noise. (`action_type` split: routing +0.8641 vs escalation +0.4319 over 4,382 rows — escalation carries far more signal per row.)

**The decisive number — matched within-objective comparison** (controls the task-mix confound in the marginal above). 621 objectives seen under ≥2 roles at ≥5 obs each, covering 385,917 decisions:
- Within-objective best-worst role reward gap: **mean 11.61pp, MEDIAN 0.00pp**
- Objectives where the gap exceeds 5pp: **136 / 621 = 21.9%**
- Non-saturated decisions in the matched set: **37,026 / 385,917 = 9.6%**

**Interpretation — this reframes the program more usefully than either prior hypothesis.** The signal is neither absent (so "signal-bound, close it" is wrong) nor uniformly present (so "train a better global policy" is also wrong). It is **concentrated**: for roughly 78% of objectives the median role gap is *literally zero* — the routing decision does not matter — and essentially all discriminative information lives in a ~10-22% minority. A global policy trained across all traffic is dominated by the majority where every action is equally correct, which is a sufficient mechanical explanation for the five-null streak WITHOUT needing the policy class to be wrong. This is also why the marginal counterfactual estimate (8.1-8.4pp split-half) understates the achievable gain: it averages the decisive minority against a majority where the ceiling is zero.

## Root-cause evidence (2026-07-21; moved from § ROOT CAUSE FOUND)

The reward-saturation audit above established *that* the reward was saturated. This establishes **why**, and it is not a design gap — the speed axis was designed, implemented, and never executed.

`compute_reward` (`orchestration/repl_memory/q_reward.py`) gates all three cost dimensions **plus** the teacher shaping behind one lookup:

```python
role = cost_metrics.get("role", "")
baseline_tps = config.baseline_tps_by_role.get(role, 0)
...
if baseline_tps > 0 and tokens_gen > 0 and elapsed > 0:   # latency penalty
if role in config.baseline_quality_by_role:               # quality-gap penalty
if role in config.memory_cost_by_role:                    # memory-tier penalty
```

`cost_metrics` is the TASK_COMPLETED entry's `data` dict (`q_scorer.py:812`). Measured over **20,521 production `task_completed` entries** (last 14 progress-log files):

| key | present |
|---|---:|
| `role` — **the key that is read** | **0** |
| `producer_role` — the key that is written | **20,521** |
| `regret` (teacher shaping) | 0 |
| `speedup_vs_teacher` (teacher shaping) | 0 |

So `baseline_tps` resolved to 0, every guard failed, and `reward` collapsed to `base_reward`. The outer `if cost_metrics` passed — the dict was non-empty — so nothing ever looked wrong.

**Fixed** (`epyc-orchestrator` `q_reward.py`): read `role` → `producer_role` → `final_answer_role`. `producer_role` values map cleanly onto `baseline_tps_by_role` keys (frontdoor 24.3, worker_general 38.46, architect_general 12.19, …; only the 49 `mock` rows miss). Five regression tests added (`tests/unit/test_q_reward_role_key.py`), two of which fail against the pre-fix code.

**Replayed against 20,526 real historical completions:**

| | at exactly r=+1.0 | mean | entropy (0.1-bin) |
|---|---:|---:|---:|
| before | **100.0%** | +1.0000 | **0.0000 bits** |
| after | **0.2%** | +0.5601 | **2.4580 bits** |

Role-conditional means post-fix: worker_vision +0.967, ingest_long_context +0.898, frontdoor +0.607, worker_general +0.524, coder_escalation +0.470, **architect_general +0.253** (lowest — slowest baseline at 12.19 tps and most expensive, so it takes all three penalties). Role spread **0.7147**, versus 0.2212 in the stored data.

**This is the mechanical explanation for the five-null streak.** Every learned-routing experiment (P4.1.3, P4.2, P4.5, P4.6, DAR-4b) was fitting a target that carried zero bits. No policy class, loss function, or feature set can extract signal from a constant.

## Wall-clock speed-axis requirement (2026-07-21; landed as era E18 on 2026-09-24)

### The speed axis must be wall-clock, not tokens/sec (operator requirement)

Dimension 1 as written is throughput-relative: `expected_elapsed = tokens_generated / baseline_tps` against `generation_ms`. **That is gameable through tools** and measurably blind. Wall-clock vs model-compute over 19,433 tasks: **median 1.60x, p90 9.09x**. Per role:

| role | n | wall p50 | model p50 | overhead |
|---|---:|---:|---:|---:|
| worker_vision | 1,775 | 11.9s | **0.4s** | **5.38x** |
| worker_general | 9,547 | 12.4s | 3.2s | 1.93x |
| frontdoor | 3,904 | 6.8s | 3.4s | 1.63x |
| coder_escalation | 2,493 | 6.9s | 3.3s | 1.20x |
| ingest_long_context | 748 | 8.5s | 6.7s | 1.12x |
| architect_general | 2,009 | 11.3s | 9.4s | 1.10x |

`worker_vision` spends 0.4s generating inside 11.9s of wall clock. A tokens/sec penalty scores it as fast; a task-execution-speed penalty would not. The gap is orchestration and tool time — exactly what autopilot's speed × quality objective is supposed to price, and exactly what the current dimension cannot see.

## DAR-LAT-3h — full box text (✅ 2026-09-27)

- [x] **DAR-LAT-3h — Prepare the `:8074` recipe-reconciliation stack-change package that unblocks 3g.** Use the
  `stack-change` skill (zero inference). Live `-t 96` vs recipe `threads: 48`, and `n_ctx` 262144 vs the validated
  8192. Trace which surface emits 96 (the suspect is `stack_templates/default.yaml:155`). Present the options: align
  serving to the recipe, or re-derive the recipe for the 96-thread serving shape (CPU co-tenancy with speech is a
  known cost, CURRENT-CAMPAIGN.md:22). Give a recommendation and a before/after decode gate. One package for the
  operator's signature; never an ad-hoc relaunch. Filed 2026-09-26 (workspace-8d wrap-up).
  ✅ 2026-09-27 — package v2 signed (`RATIFY-DAR-LAT-3H-CRITIC-THREADS-20260926`), G1 run 2026-09-27 ~17:41-18:57Z,
  15/15 launches clean, coherence equal across arms. **Outcome T96**:
  - premise holds: T96 vs L wall 0.988×, TTFT 0.950× (`GGML_FUSED_DECODE_OFF` inert under MTP);
  - 48-thread parity fails: T48 vs T96 1.0385× / 1.055×, T48N vs T96N 1.032× / 1.068× (bar: wall ≤ 1.03×);
  - THP shim not adopted: T96N vs T96 wall 1.009× (bar: ≤ 0.98×).
  **Disposition: recorded only, NOTHING APPLIED** — the T96 row adds only the inert knob and live `:8074` already runs
  `-t 96`, so no reload and no contention recert. The 2026-09-22 C3 ruling (`NUMA_FULL_T48`) is superseded;
  `NOHUGEPAGE_PROCESS` is settled as no gain on v10 at the served shape. The `lane/dar-lat-3h-v2-*` outcome lanes are
  NOT to be merged. Evidence, W2 reading and decode tables:
  [`RESULT.md`](../../artifacts/operator/stack-change-dar-lat-3h-20260926/RESULT.md), `g1-result/verdict.json`.
  **DAR-LAT is now FROZEN** (narrowed plan) apart from the UFH-13 thesis experiment; the boxes above and below keep
  their `❄ FROZEN 2026-09-27` markers and unfreeze triggers.
