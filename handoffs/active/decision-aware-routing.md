# Decision-Aware Routing for Q-Scorer

**Status**: IN PROGRESS — DAR-1 analysis complete (2026-04-15). 96% uniform Q-values confirmed. DAR-2 pending.
**Created**: 2026-04-14 (from deep-dive research on intake-366)
**Updated**: 2026-04-15
**Priority**: HIGH
**Categories**: routing_intelligence, reinforcement_learning, cost_aware_routing
**Tracked in**: [routing-and-optimization-index.md](routing-and-optimization-index.md) P13

## Problem / Context

The difficulty signal shows **zero predictive spread**: escalation rates are flat at 62.2% / 60.7% / 62.2% across easy/medium/hard bands (Package B Phase 4, n=635, research-eval P0). The current Q-scorer cannot differentiate routing needs because the training objective is detached from the routing decision.

**Current architecture** (predict-then-optimize):

1. **Predict**: TD-learn Q-values per action via `update_q_value()` at `episodic_store.py` L439-511. Formula: `Q_new = Q_old + α * (reward - Q_old)`
2. **Optimize**: Argmax over Q-values via `_retrieve()` at `retriever.py` L225-368. Selection: `selection_score = Q_value - cost_lambda * (expected_cost / cold_cost)`

The TD update pushes Q-values toward observed rewards **independently per model**, with no mechanism to sharpen the decision boundary between models. A model consistently scoring Q=0.72 vs Q=0.68 is making the right decision, but the Q-value magnitudes are irrelevant — what matters is A > B.

**Decision-aware learning** aligns training with the routing DECISION, not prediction accuracy. The gradient is zero when the routing decision is already correct — it only provides learning signal when the prediction would lead to a wrong decision.

## Key Insight: Trivial Tractability

The intractability concerns from intake-366 (differentiating through LP/MIP solvers in operations research) **do not apply** to our problem:

- **Action space**: N=3-5 models. This is trivially small — we can enumerate all actions at every training step.
- **Optimization**: Just `argmax` over N numbers — O(N), not NP-hard integer programming.
- **SPO+ loss**: Convex surrogate with closed-form gradients. No RL infrastructure needed.
- **Gumbel-softmax**: Perfect convergence at this scale (temperature annealing to 0 recovers exact argmax).
- **Compute**: CPU-only. SPO+ and contrastive losses are cheaper than current TD updates.

**This is one of the rare cases where the theoretically superior approach is also simpler to implement.**

## Research Context

| Intake | Title | Key Contribution |
|--------|-------|-----------------|
| intake-366 | Deep Learning for Sequential Decision Making under Uncertainty | Survey: predict-then-optimize vs decision-aware vs learning-to-optimize paradigms. PredOpt expandable architecture. |
| Ch 08 | Cost-Aware Rewards (epyc-inference-research) | xRouter: 7B RL router with cost-aware reward. RouteLLM: preference-based matrix factorization. |
| — | xRouter (arxiv:2510.08439) | DAPO end-to-end RL, 20+ API models. Requires multi-GPU — not applicable to our CPU stack. |
| — | RouteLLM (arxiv:2406.18665) | Matrix factorization for binary strong/weak routing. Our N>2 setting needs generalization. |
| — | Router-R1 (arxiv:2506.09033) | GRPO multi-round routing with think+route. 8×A100 training — not applicable. |

**Key comparison**: xRouter and Router-R1 require multi-GPU RL training. But their conceptual contribution — aligning training with routing decisions — can be achieved without RL via decision-aware losses on our existing CPU Q-scorer.

## Implementation Phases

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
- [ ] Add dedicated unit test for `_compute_contrastive_adjustment()` with mock store (deferred)

**Implementation**: Added in `_score_task()` between reward computation and `_update_routing_memory()`. The method retrieves top-10 similar routing memories, compares selected model's Q-value against alternatives with learned Q-values, and computes a bounded adjustment that sharpens the decision boundary. Zero adjustment when ranking is already correct with sufficient margin.

**Files**: `q_scorer.py` (L31 flag, L271-282 integration, L457-520 method)

### DAR-3: SPO+ with Exploration (~100 lines, 3-4 sessions)

- [ ] Implement SPO+ (Smart Predict-then-Optimize) loss:
  ```
  L_SPO+ = sum(max(0, 2*c_hat[j] - c_true[j])) - c_hat[i*] + c_true[i*]
  ```
  where `c_hat` = predicted costs, `c_true` = true costs, `i*` = true optimal model
- [ ] Add epsilon-greedy exploration to `_select_model()` at `retriever.py` L225-368 (10% random routing)
- [ ] Accumulate counterfactual data: for each prompt, observe outcomes from at least 2 different models
- [ ] Replace TD update with SPO+ gradient: only update when the routing decision would change
- [ ] Measure: routing accuracy, average task quality, average latency, Q-value convergence speed
- [ ] Connect exploration flag to existing `staged_scorer` exploration bonus mechanism

**Files**: `q_scorer.py`, `retriever.py` L225-368, `routing.py` L48-314

### DAR-4: Model-Feature-Conditioned Q (~200 lines, 4-5 sessions)

- [ ] Replace per-action Q-values with bilinear scorer:
  ```
  Q(prompt, model) = sigmoid(v_model^T W v_prompt + b)
  ```
- [ ] Model features (already available in `ScoringConfig` L34-117):
  - `baseline_tps` (from `baseline_tps_by_role`)
  - `baseline_quality` (from `baseline_quality_by_role`)
  - `memory_cost` (from `memory_cost_by_role`)
  - `param_count_log` (derivable from model registry)
  - `is_moe` (binary flag)
  - `quant_bits` (from model registry)
- [ ] Create new `bilinear_scorer.py` module
- [ ] Modify `retriever.py` selection logic to use bilinear scorer instead of per-action Q lookup
- [ ] Test: add a simulated new model with known features, measure cold-start convergence vs current approach
- [ ] Zero cold-start: when a new model joins the fleet, its features are known from specs — no routing history needed

**Files**: New `bilinear_scorer.py`, `retriever.py`, `q_scorer.py` (config), `episodic_store.py`

## Dependency Graph

```
DAR-1 (offline regret analysis)    ──independent──
DAR-2 (contrastive Q-score)        ──depends on DAR-1 confirming regret > threshold──
DAR-3 (SPO+ with exploration)      ──depends on DAR-2 producing ranked Q-values──
DAR-4 (model-feature-conditioned)  ──independently developable in parallel with DAR-2/3──
```

## Cross-Cutting Concerns

### 1. Q-Scorer Baselines
Q-scorer baselines (`baseline_tps_by_role`, `baseline_quality_by_role`) must be re-established after any DAR-2/3/4 change. Current baselines from 2026-03-21 sweep (see memory: project_qscorer_calibration.md).

### 2. Difficulty Signal (research-eval P0)
The zero-predictive-spread pathology in `difficulty_signal.py` motivated this work. If contrastive Q-scoring (DAR-2) resolves the flat-band problem, the difficulty signal becomes useful as a routing feature again rather than being stuck in shadow mode.

### 3. AP-27 RLVR Eval Tower
Decision-aware routing changes the reward signal that the eval tower must evaluate. The eval tower verification framework ([eval-tower-verification.md](eval-tower-verification.md) EV-1–EV-7) must be able to assess whether the new routing reward is well-calibrated (ECE) and discriminative (AUC).

### 4. Existing RL Routing Research (R&O intake-275)
The BaRP (arxiv:2510.08429) lightweight policy network and LLM Bandit (arxiv:2502.02743) from the 2026-04-07 research intake update are complementary approaches. DAR-2/3 operate on the existing Q-scorer; BaRP/Bandit would replace it entirely with a trained policy. If DAR-2/3 show insufficient gains, BaRP is the next escalation path.

## Key Files

| File | Purpose | Lines of Interest |
|------|---------|-------------------|
| `epyc-orchestrator/orchestration/repl_memory/q_scorer.py` | Reward computation, Q-value updates | L318-430 (_compute_reward), L34-117 (ScoringConfig) |
| `epyc-orchestrator/orchestration/repl_memory/episodic_store.py` | Memory storage, Q-value TD update | L439-511 (update_q_value) |
| `epyc-orchestrator/orchestration/repl_memory/retriever.py` | Two-phase retrieval, selection score | L225-368 (_retrieve), L194-216 (confidence) |
| `epyc-orchestrator/src/api/routes/chat_pipeline/routing.py` | Full routing pipeline | L48-314 (_route_request) |
| `epyc-orchestrator/src/classifiers/difficulty_signal.py` | Difficulty classification (zero-spread diagnostic) | L201-236 (scoring + banding) |
| `epyc-orchestrator/tests/unit/test_q_scorer.py` | Q-scorer unit tests | — |

## Known Issues

- The zero predictive spread diagnostic came from Package B Phase 4 with n=635. If the underlying issue is data sparsity rather than architectural, DAR-1 regret analysis will reveal this — regret would be near-zero because there are too few samples to establish reliable counterfactuals.
- DAR-3 exploration routing (10% random) will temporarily degrade routing quality during data collection. Must run in shadow mode or during low-priority tasks.
- DAR-4 bilinear scorer assumes model features are informative predictors of per-prompt quality. If all models perform similarly on most prompts (low variance), the feature-conditioned approach adds complexity without benefit.
