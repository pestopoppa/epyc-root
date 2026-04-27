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
- [x] Add dedicated unit test for `_compute_contrastive_adjustment()` with mock store — **DONE 2026-04-17**: `TestComputeContrastiveAdjustment` class with 13 tests in `tests/unit/test_q_scorer.py`

**Implementation**: Added in `_score_task()` between reward computation and `_update_routing_memory()`. The method retrieves top-10 similar routing memories, compares selected model's Q-value against alternatives with learned Q-values, and computes a bounded adjustment that sharpens the decision boundary. Zero adjustment when ranking is already correct with sufficient margin.

**Files**: `q_scorer.py` (L31 flag, L271-282 integration, L457-520 method)

### DAR-1.5: REINFORCE-Pathology Audit (NEW 2026-04-26 — analytical, no code)

**Source**: deep-dive [`research/deep-dives/trinity-evolved-llm-coordinator-methodology.md`](../../research/deep-dives/trinity-evolved-llm-coordinator-methodology.md) Section 2.2.

**Trigger**: Trinity's Table 4 shows REINFORCE collapses to **0.253 LCB / 0.459 Math500** at the same training budget where sep-CMA-ES achieves **0.615 / 0.880**. The paper attributes this to the loss surface being block-ε-separable — pure policy-gradient methods get drowned in off-block noise. DAR-3 (SPO+) and DAR-4 (bilinear scorer) are NOT pure REINFORCE — they use closed-form gradients on contrastive losses — but the question is whether the same geometry hurts them in a milder form.

**Goal**: a written analytical audit (no code, no rerun) answering: do the gradients used in DAR-2 (contrastive Q-update, ALREADY LANDED), DAR-3 (SPO+), and DAR-4 (bilinear scorer) share REINFORCE's vulnerability to off-block noise on a block-ε-separable loss? If yes for any of DAR-3/DAR-4, document the mitigation before implementation begins.

- [ ] **DAR-1.5.1** Write out each loss's gradient form: REINFORCE (`∇log π · advantage`), contrastive Q (`∇(Q_chosen − Q_alt − margin)`), SPO+ (`max(0, 2·c_hat − c_true)` form), bilinear (`∇sigmoid(v_m^T W v_p + b)`). Identify which gradients couple parameters across notional "blocks" of the loss surface.
- [ ] **DAR-1.5.2** Cross-reference with `learned-routing-controller.md` P4.2 — the block-ε-separability diagnostic on our actual landscape. If P4.2 confirms our problem IS block-ε-separable, DAR-1.5 conclusions become load-bearing for DAR-3/DAR-4. If P4.2 falsifies it, this audit downgrades to a footnote.
- [ ] **DAR-1.5.3** For any loss that DOES couple across blocks (and our landscape is block-ε-separable), document the mitigation: (a) regularise toward block-diagonal weights, (b) add a population-style outer loop on top of the gradient method, (c) re-weight the gradient by inverse off-block coupling estimate, or (d) accept the risk and proceed.
- [ ] **DAR-1.5.4** Decision gate before DAR-3: if DAR-1.5 flags a high-confidence pathology and P4.2 confirmed block-ε-separability, pause DAR-3/4 and reconsider. Otherwise proceed with DAR-3 as planned, with DAR-1.5 conclusions captured as a "Known Risks" sub-section.

**Effort**: 1 session, analytical only. No infra, no code. Deliverable is a markdown sub-section appended to this handoff.

**Why this matters even if it changes nothing**: it produces a *first-principles* answer to "does Trinity's REINFORCE result transfer to us?" — which the project repeatedly needs when reasoning about new optimizer choices. Cheap insurance against making the wrong optimizer call later.

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

## Research Intake Update — 2026-04-18

### Episodic Memory Benchmark: Routing Intelligence Signal (intake-408/409 deep-dive)

The Tulving Episodic Memory Benchmark (arXiv 2501.13121, ICLR 2025) tested 24 models on 100K-token narratives requiring entity tracking and temporal ordering. Two metrics: Simple Recall (F1) and Chronological Awareness (Kendall τ). Key routing-relevant findings:

**Reasoning models catastrophically fail at long-context episodic memory:**

| Model | Recall (10K→100K) | Chronological (10K→100K) | Architecture |
|-------|-------------------|--------------------------|--------------|
| DeepSeek-R1 | 0.988→0.572 (-42%) | 0.964→0.147 (-85%) | MoE, reasoning |
| o1 | 0.978→0.384 (-61%) | 0.948→0.052 (-95%) | reasoning |
| GPT-4o | 0.908→0.670 (-26%) | 0.182→0.204 (+12%) | base |
| Gemini-2.5-Pro | 0.982→0.968 (-1%) | 0.948→0.796 (-16%) | base |

**Routing implications:**
- Chronological awareness varies **10x** across models (0.033 to 0.817) — a stronger differentiator than recall for routing decisions
- Reasoning models excel at short-context episodic tasks but collapse at 100K — their effective context utilization windows are much shorter than advertised context lengths
- For long-document temporal reasoning tasks, routing to reasoning-focused models is **actively harmful** (o1 scores worse than GPT-4o-mini)
- MoE vs dense architecture shows no clear signal — model size and training approach dominate
- **RAG chunk granularity matters**: chapter-level RAG matches in-context (0.82 vs 0.81 F1), paragraph-level RAG degrades to 0.60. Event-boundary-aligned chunking is critical.

**Actionable for DAR-4**: The `is_moe` binary feature in the bilinear scorer model features is less informative than a `reasoning_model` binary flag. Consider adding `is_reasoning_model` to `ModelFeatures` — it strongly predicts long-context episodic performance.

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

## Research Intake Update — 2026-04-26

### New Related Research

- **[intake-474] "TRINITY: An Evolved LLM Coordinator"** (arxiv:2512.04695, ICLR 2026, openreview:5HaRjXai12)
  - Authors: Jinglue Xu, Qi Sun, Peter Schwendeman, Stefan Nielsen, Edoardo Cetin, Yujin Tang
  - Relevance: Fourth peer in this handoff's Research Context table alongside xRouter / RouteLLM / Router-R1 — same problem (lightweight policy that selects among LLMs), qualitatively different optimizer.
  - Key technique: ≈0.6B base LM + ≈10K-parameter head, trained with **separable CMA-ES** (an evolutionary strategy) instead of RL/SFT. Penultimate-token hidden state is mapped to agent-role logits for multi-turn role-typed delegation (Thinker / Worker / Verifier).
  - Reported results: 86.2% on LiveCodeBench (claimed coordinator-system record at submission); consistent gains over individual constituent models on coding/math/reasoning/domain-knowledge benchmarks; OOD generalization without SFT or RL.
  - Delta from current approach (DAR): DAR is reshaping the *learning objective* of the existing TD-trained Q-scorer (predict-then-optimize → decision-aware). Trinity drops the TD/RL frame entirely and trains the routing head with a black-box ES against an end-task fitness signal — directly side-stepping the credit-assignment / Q-magnitude problem that DAR-1 diagnosed. If DAR-2/3/4 underdeliver on the zero-predictive-spread pathology, sep-CMA-ES on the existing routing head is the natural escalation path that does NOT require multi-GPU RL infra (xRouter / Router-R1's blocker) and is CPU-feasible at our scale (10K params, no gradient). Caveat: author-acknowledged limitation is the abstract-vs-grounded-execution gap, which Trinity does NOT solve — that part stays inside our orchestrator.
  - Recommended follow-up: spike sep-CMA-ES as an alternative trainer for the existing `routing_classifier.py` MLP head when distillation labels are sparse. Add Trinity to the handoff's Research Context table.
  - **Deep-dive**: [`research/deep-dives/trinity-evolved-llm-coordinator-methodology.md`](../../research/deep-dives/trinity-evolved-llm-coordinator-methodology.md) — read before extending DAR-2/3/4. Specifically section 2.2 ("ES side-steps the credit-assignment problem DAR is trying to solve") and action #4 ("Re-examine DAR-2/3/4 for hidden REINFORCE-class pathology" — analytical check on whether SPO+/bilinear gradients share REINFORCE's off-block-noise weakness on block-ε-separable losses).
