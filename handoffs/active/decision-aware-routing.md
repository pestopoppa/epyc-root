# Decision-Aware Routing for Q-Scorer

**Status**: ACTIVE, mostly waiting — DAR-2 contrastive is live-ON; DAR-3/DAR-6 FROZEN (fable5-02); DAR-3/4/5 re-aimed 2026-07-21 (§ RESCOPE); the reward carries the wall-clock axis since era E18 (2026-09-24); DAR-LAT is ❄ FROZEN (2026-09-27; unfreeze trigger since 2026-09-29: autopilot has trained on the swapped stack AND UFH-13 re-opened). Completed DAR-1/DAR-2/DAR-1.5 record: § Completed Scope.
**Created**: 2026-04-14 (from deep-dive research on intake-366)
**Updated**: 2026-07-03 (current-window DAR-1 replay; prior body updates through 2026-04)
**Priority**: HIGH
**Categories**: routing_intelligence, reinforcement_learning, cost_aware_routing
**Tracked in**: [routing-and-optimization-index.md](routing-and-optimization-index.md) P13
**Cross-claim (2026-06-12)**: DAR-1 replay deliverable + the ≥5%/<5% fork are closed in [routing-truth-restoration.md](../completed/routing-truth-restoration.md) W8; this handoff retains the future learned-routing research items only if a later gate re-opens them.

## Start here (2026-09-27)

- DAR-LAT is ❄ FROZEN, with a per-box unfreeze trigger; since 2026-09-29 (operator ruling, `typed-decision-plane.md` → *Operator rulings — 2026-09-29*, Q2) that trigger is "autopilot has trained on the swapped stack AND UFH-13 re-opened", replacing UFH-13's TE-6 verdict (UFH-13 PARKED 2026-09-28). DAR-LAT-3h is ✅.
- Operator narrowed plan 2026-09-27: hold new DAR work for UFH-13. The first unfrozen box after the verdict is DAR-SPLIT-1, then the `stage`/`producer_role` split.
- Operator-owned: the ">=5% regret" ruling and the E9 routing-reward era signature.
- Standing, never flip: no production epsilon-greedy; do not close DAR-3/4/5 as signal-bound; any reward redesign carries the speed axis.
- Do not dispatch the DAR-3 SPO+ boxes.

## Completed Scope

| Scope | Where |
|---|---|
| DAR-1, DAR-1 current-traffic replays, DAR-2, DAR-1.5 (phases + audit deliverable), the 2026-07-21 reward-saturation tables and root-cause evidence, the wall-clock speed-axis requirement (landed as E18), and the DAR-LAT-3h full box text | [completed sibling](../completed/decision-aware-routing-completed-through-2026-09-27.md) |
| April dependency graph, research-intake updates 2026-04-18 / 04-26 / 04-28 / 05-27, the superseded Status line and Start here (nothing dispatchable) | [archived history](../archived/decision-aware-routing-history-through-2026-09-27.md) |

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

DAR-1 (offline regret, ✅ 2026-04-15), the DAR-1 current-traffic replays (✅ 2026-06-12, 2026-07-03), DAR-2 contrastive (✅ 2026-04-15, live-ON via `CONTRASTIVE_Q_UPDATES`) and the DAR-1.5 REINFORCE-pathology audit (✅ 2026-05-07) moved to the [completed sibling](../completed/decision-aware-routing-completed-through-2026-09-27.md); see § *Completed Scope*.

### DAR-3: SPO+ with Exploration (~100 lines, 3-4 sessions) — superseded by § RESCOPE (do not dispatch)

**Motivation note (intake-495 BaRP)**: BaRP frames this as the train/test mismatch fix — production logs only record the chosen specialist's outcome, not counterfactuals for un-routed models. DAR-3 SPO+ adopts the bandit-feedback *rationale* (don't require labels for un-chosen specialists) with a convex surrogate loss instead of REINFORCE. The 10% epsilon-greedy exploration step is what manufactures counterfactual data; SPO+ is what learns from it without REINFORCE's high-variance gradient.

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

- DAR-1.5 verdict (2026-05-07; P4.2 resolved 2026-06-27): DAR-4 proceeds full-rank; sep-CMA-ES only for cold-start/no-label surfaces. Gate artifact: `/mnt/raid0/llm/epyc-orchestrator/orchestration/reports/p42_block_separability/report_20260627_sample80k.json`.
- Feature candidate (intake-408#06): add `is_reasoning_model` to `ModelFeatures`.

### DAR-4b: Inference-Time Preference Vector + Cost Scaling τ (~50–100 lines, 1–2 sessions)

Source: intake-495 (BaRP) — preference-tunable inference. Modulates the trained DAR-4 bilinear scorer at inference WITHOUT retraining.

**2026-07-04 code checkpoint**: default-compatible request-level DAR-4b plumbing landed in `epyc-orchestrator` `fbd569b5`. This does **not** reopen DAR-3/DAR-6/Package-I expansion gates; it only adds an explicit request override and cost-scaling surface on the existing retrieval selector.

- [x] Add a 2-D preference vector `ω = (ω_perf, ω_cost)` on the simplex (`ω_perf + ω_cost = 1`) read from request metadata (default ω = (0.5, 0.5)).
- [x] Add calibrated cost scaling parameter τ as a runtime knob (env var `DAR_COST_TAU`, default 1.0; canonical env `ORCHESTRATOR_MEMRL_RETRIEVAL_COST_TAU` takes precedence). τ multiplies the normalized-cost penalty.
- [x] Inference-time score: `selection_score = 2 * (ω_perf * Q(prompt, model) - ω_cost * cost_lambda * τ * normalized_cost(model))`. The default `ω=(0.5,0.5), τ=1.0` preserves the existing `Q - cost_lambda * normalized_cost` selector exactly.
- [x] Per-task ω override wired through `ChatRequest.routing_preferences`, TaskIR canonicalization, chat routing, and `retrieve_for_routing()`. Per-tenant policy defaults remain future work only if a concrete tenant/workload policy is needed.
- [x] No retraining required. The deployed path applies only inference-time scalarization to the existing per-action Q-table selector; bilinear DAR-4 remains separately open.
- [ ] Measure: routing decision distribution shift across ω sweeps; latency-quality Pareto curve.
  - 2026-07-04 offline proxy sweep complete in `epyc-orchestrator` `b40207b4`:
    `orchestration/reports/dar4b_sweep_20260704T160319Z/summary.md`.
    Frozen window 2026-06-13..2026-07-03: `24,918/30,725` eligible
    top-k routing decisions. Tested `ω=(0.5,0.5),(0.8,0.2),(0.2,0.8)` and
    `τ=0.8,1.0,1.2`; the logged selector surface is nearly insensitive
    (`0.00%` baseline flips for balanced/perf-heavy, `0.06%` for cost-heavy).
    This is an offline selector-proxy observation, not a live latency-quality
    decision gate; keep live/controlled measurement open before any default
    policy uses the new knobs.

**Files**: `retriever.py` L225-368 (selection scoring), `routing.py` L48-314 (ω plumbing), `q_scorer.py` (config — `DAR_COST_TAU` knob).

**Why orthogonal to DAR-4**: DAR-4 trains the bilinear scorer; DAR-4b modulates its outputs at inference. Can ship independently of DAR-4 by applying ω/τ to the existing per-action Q-table if DAR-4 slips.

### DAR-5: IRT-Augmented Prompt Features + Learned Model-Identity Vectors (~150 lines, 3-5 sessions, conditional on DAR-4)

Source: intake-496 (LLM Bandit) — IRT (Item Response Theory) score predictor + d-dim model identity vectors trained jointly. Replaces hard-coded model-feature specs in the bilinear scorer with end-to-end learned embeddings.

- [x] **DAR-5.1**: Implement IRT prompt-difficulty scorer over BGE prompt embeddings. Output: per-prompt `(latent_difficulty, latent_discrimination)` 2-D embedding. Trained via maximum-likelihood on existing 174K routing memories with observed model outcomes as IRT responses. Calibrated via Platt scaling. ✅ 2026-07-22
- [ ] **DAR-5.2**: Replace hard-coded `v_model = [baseline_tps, baseline_quality, memory_cost, param_count_log, is_moe, quant_bits]` in DAR-4 bilinear scorer with a learned d-dim model identity vector `v_model ∈ ℝ^d` (d=8 starting point), initialized from the hard-coded spec values, then trained jointly with the bilinear weights.
- [ ] **DAR-5.3**: Augment `v_prompt` with the IRT 2-D output concatenated to the BGE embedding. New `v_prompt = [BGE_embedding | irt_difficulty | irt_discrimination]`.
- [ ] **DAR-5.4**: A/B against frozen-DAR-4 (hard-coded features) on val set. Decision gate: if IRT+identity-vectors improves routing accuracy by ≥ 2 points val acc, promote to default.
- [x] **DAR-5.5**: Future-onboarding note ✅ 2026-07-29 — initialize a new model's learned identity vector from its declared spec features only after DAR-4/DAR-5 are re-authorized on the fixed reward; this is an initialization, never an admission or routing-default decision. Refine it only through LRC P5.2's promotion-grade **observed-outcome** IRT run, not label-proxy scores; P5.2 currently rejects its cached label-proxy result and P5.3 remains conditional on P5.2's acceptance gate. The current DAR-5 prerequisite is the reward redesign (including the wall-clock axis), so no cold-start execution follows from this note.

**Files**: New `irt_scorer.py`, modify `bilinear_scorer.py` from DAR-4, `q_scorer.py` (config).

**Conditional on**: DAR-4 (bilinear scorer) shipping first. If DAR-4 hard-coded features prove sufficient (no measured benefit from learned features), DAR-5 closes as `not_pursued`.

### Escalation Language (added 2026-04-28 from intake-495/496/474/493)

If DAR-3 / DAR-4 / DAR-4b / DAR-5 underdeliver on the zero-predictive-spread pathology:

1. **CPU-feasible escalation (Trinity, intake-474)**: sep-CMA-ES on the existing routing head (10K params, no gradient). Side-steps the credit-assignment / Q-magnitude problem entirely. CPU-feasible, no GPU budget required. See `learned-routing-controller.md` P4.4 (sep-CMA-ES cold-start spike) for the existing scoping.
2. **GPU-class escalation (Conductor, intake-493)**: 7B end-to-end RL coordinator. Requires 2× H100 80GB minimum. Out of CPU stack. Documented as competitive intelligence in `outer-coordinator-learned-head.md` OC-0.6.
3. **Bandit-as-such (BaRP, intake-495)**: REINFORCE on a fresh policy network, no Q-scorer at all. High-variance on small action spaces (≤5–8 specialists); LinUCB or Thompson sampling may match without policy-gradient instability. Unranked third option.

The realistic CPU-feasible escalation is option 1 (Trinity-style sep-CMA-ES). Options 2 and 3 are recorded for completeness, not roadmap commitments.

### DAR-6: Swarm-Fanout Mode for High-Injection-Risk Prompts (intake-614/615, ~1–2 days + one eval run) — ❄ FROZEN (fable5-02)

**Source**: arxiv:2510.24801 (intake-615) — peer-ranked consensus across heterogeneous models reportedly shows 0.12% adversarial-degradation vs 6.20% for single-model baseline on prompt injection. If even a third of that delta survives independent replication on our suite, swarm-fanout is a routing **mode**, not just a research curiosity.

**What this adds to DAR**: a new routing mode that fans high-injection-risk prompts to **N≥2 concurrent serves** and returns a Bradley-Terry-aggregated winner instead of escalating to a single stronger model. This is **post-hoc full-completion** swarm voting (the published method) — distinct from the unpublished chunk-ranking claim (which is scoped separately in [`peer-verifier-speculation-spike.md`](../completed/peer-verifier-speculation-spike.md), resolved NO-GO and archived 2026-06-12).

**Gate before any code**:
- Replicate the 0.12% / 6.20% claim on our own injection suite. Candidate suites: [Garak](https://github.com/leondz/garak), [HouYi](https://github.com/LLMSecurity/HouYi), [PromptInject](https://github.com/agencyenterprise/PromptInject). Pick one with active maintenance + Apache/MIT license.
- Roofline check: per memory `feedback_no_concurrent_inference.md`, request user approval before any concurrent-model inference; per memory `feedback_same_model_roles_share_server.md`, 2-of-N concurrent serve of DIFFERENT GGUFs requires N independent processes, each with its own RAM share. The 30–40 t/s aggregate Fortytwo quotes for 4–8 CCUs implies a real per-stream throughput penalty; verify ours empirically before committing the routing mode to production.

**Implementation sketch** (~150–250 LOC):
> **Note 2026-09-16:** `dispatch_swarm_fanout` and `src/swarm_fanout.py` (with `SwarmCompletion`, `SwarmFanoutResult`, `bradley_terry_aggregate` and `length_proxy_aggregator`) **no longer exist**. They were deleted as dead code in orchestrator `771348c8` (2026-06-16, "delete dead DAR-6 swarm_fanout module", an ancestor of `main`). Only the default-off `swarm_fanout` FeatureSpec in `src/features.py` remains. The DAR-6.3/6.4 text below and the Default-off safety bullet are historical, and DAR-6.5/J14 would have to rebuild the dispatcher first.
- [x] **DAR-6.1 ✅ 2026-05-27** (epyc-orchestrator commit pending): Feature flag `swarm_fanout` added to `src/features.py` registry (`SWARM_FANOUT` env var; default-off in BOTH test and prod). `Features.swarm_fanout` boolean field. **Production routing is not affected** until a caller explicitly invokes `dispatch_swarm_fanout` AND the flag is on — two safety layers.
- [ ] **DAR-6.2 (NOT YET BUILT — prereq for production gating)**: Trigger signal — extend the injection-risk classifier (or reuse the existing factual-risk classifier from [`routing-intelligence.md`](routing-intelligence.md) if it carries an injection axis) to produce a 0–1 score; threshold tunable. For the cheap-first DAR-6.5 A/B variant ([J14](bulk-inference-campaign.md) in bulk-inference), this can be deferred — fan unconditionally on a fixed injection-prompt set first.
- [x] **DAR-6.3 ✅ 2026-05-27 — SUPERSEDED/REMOVED 2026-06-16 (code deleted by orchestrator `771348c8`; see the note below)**: `dispatch_swarm_fanout(request, targets, ...)` in **`src/swarm_fanout.py`** fans the request to N≥2 backends concurrently via `ThreadPoolExecutor`. Per-backend failures (exceptions OR `success=False` results) are caught and surfaced as `SwarmCompletion(success=False, error=...)` rather than crashing the dispatch. Returns a `SwarmFanoutResult` with all N completions, per-role wall-clock, and optional aggregation.
- [x] **DAR-6.4 ✅ 2026-05-27 — SUPERSEDED/REMOVED 2026-06-16 (aggregator deleted by orchestrator `771348c8`; `src/bradley_terry.py` itself survives)**: `bradley_terry_aggregate(pairwise_scorer)` builds an aggregator that calls **`src/bradley_terry.py`** (moved from scripts/autopilot/ on 2026-05-27 to keep it a single-source-of-truth for the three consumers — autopilot P17.BT-2, DAR-6.4 here, swarm-dataset-distillation Phase 3). The aggregator returns `(winner_completion, diagnostics)` carrying BT log_skills, warnings, Condorcet cycles, and dominance skew. Also included: `length_proxy_aggregator` as an explicit cheap-baseline (BT on length-difference sigmoid) — labeled in its docstring as "NOT a meaningful aggregation" so no future agent confuses it with a real peer-judged scorer.
  - **Removal note 2026-09-16 (sub-closure-fix):** DAR-6.3 and DAR-6.4 stay ticked because the work was really built (orchestrator `5f5fd8f6`, 2026-05-27). It was then deleted as dead code by `771348c8` (2026-06-16, "delete dead DAR-6 swarm_fanout module", an ancestor of orchestrator `origin/main` @ `88a2902d`). `src/swarm_fanout.py`, `dispatch_swarm_fanout`, `SwarmFanoutResult`, `SwarmCompletion`, `bradley_terry_aggregate` and `length_proxy_aggregator` exist on no ref at main. **Neither box is a live capability.** Evidence: `progress/2026-09/2026-09-16-sub-closure-audit.md` (top-10 #5).
- [ ] **DAR-6.5 (INFERENCE-GATED — J14 in bulk-inference)**: Decision gate — run a 2-arm A/B on the chosen injection suite (single-model escalation vs swarm-fanout). Gate: must show ≥3pp absolute reduction in injection-success rate AND ≤30% per-stream throughput regression (roofline). If both met → enforce; otherwise stay shadow-only.
  - **Dependency note 2026-09-16 (sub-closure-fix):** the DAR-6.3/6.4 dependency this gate names is **gone**. The dispatcher and aggregator were deleted in orchestrator `771348c8`, so DAR-6.5/J14 must first rebuild a fan-out dispatcher (it can reuse `src/bradley_terry.py`, which survives) or be re-scoped. The `swarm_fanout` FeatureSpec (`src/features.py:211,563`, `orchestration/runtime_flags.spec.yaml:117`) is still defined but **is read by no code path: the flag controls nothing**. Turning it on today would change no behaviour, so it cannot serve as the A/B arm.

**Cross-task interactions**:
- BT aggregation module **lives at `src/bradley_terry.py`** (moved from scripts/autopilot/ during DAR-6 scaffolding) and is shared with autopilot P17 (selection step) and [`swarm-dataset-distillation.md`](swarm-dataset-distillation.md) Phase 3 (training-data filtering). One implementation, three consumers.
- Concurrent-serve infrastructure dependency is [`dynamic-stack-concurrency.md`](dynamic-stack-concurrency.md) — verify Phase B observability is sufficient to detect 2-of-N inference-thread contention before relying on this mode. (Phase B was already complete per dynamic-stack-concurrency.md status — no new dependency.)
- Injection-risk classifier may not exist yet; if not, that's a prerequisite task that should be raised in [`routing-intelligence.md`](routing-intelligence.md) as a new RI-phase, not buried inside DAR-6.
- **Default-off safety**: `dispatch_swarm_fanout` requires no aggregator by default; if called without one, returns all N completions and the caller picks. This is deliberate — the most faithful Fortytwo-style aggregator (peer-judged pairwise) needs N*(N-1) extra inference calls and is exactly the cost the DAR-6.5 A/B is designed to measure. Picking a default would prejudge the experiment.

**Non-goals for DAR-6**:
- Mid-stream / chunk-level peer verification ([`peer-verifier-speculation-spike.md`](../completed/peer-verifier-speculation-spike.md) covers that; spike resolved NO-GO 2026-05-27, archived 2026-06-12 with 4 re-eval triggers).
- Replicating Fortytwo's reputation-staking / Sybil resistance (single-user single-host stack — out of scope).
- Multi-model fan-out for general (non-injection) prompts — that's a latency burn without a clear quality justification at our scale.

## Cross-Cutting Concerns

### 1. Q-Scorer Baselines
Q-scorer baselines (`baseline_tps_by_role`, `baseline_quality_by_role`) must be re-established after any DAR-2/3/4 change. Current baselines from 2026-03-21 sweep (see memory: project_qscorer_calibration.md).

### 2. Difficulty Signal (research-eval P0)
The zero-predictive-spread pathology in `difficulty_signal.py` motivated this work. If contrastive Q-scoring (DAR-2) resolves the flat-band problem, the difficulty signal becomes useful as a routing feature again rather than being stuck in shadow mode.

### 3. AP-27 RLVR Eval Tower
Decision-aware routing changes the reward signal that the eval tower must evaluate. The eval tower verification framework ([eval-tower-verification.md](eval-tower-verification.md) EV-1–EV-7) must be able to assess whether the new routing reward is well-calibrated (ECE) and discriminative (AUC).

### 4. Existing RL Routing Research (R&O intake-275)
The BaRP (arxiv:2510.07429) lightweight policy network and LLM Bandit (arxiv:2502.02743) from the 2026-04-07 research intake update are complementary approaches. DAR-2/3 operate on the existing Q-scorer; BaRP/Bandit would replace it entirely with a trained policy. If DAR-2/3 show insufficient gains, BaRP is the next escalation path.

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

## Deep-Dive Task Proposals — 2026-05-25 (intake-607 Code-as-Agent-Harness §5.2.5)

DAR optimizes routing/escalation along a **quality** axis (learned Q-values + contrastive sharpening). The Code-as-Agent-Harness survey (§5.2.5) names a *different* axis worth adding: **decision uncertainty**, with the escalation decision recorded as first-class harness state for accountability. Audit pass tightened this into a calibration-first plan.

> **Schema + code anchors (gap-fix 2026-05-25):** the URE-2 approval/escalation record is part of the **shared trace schema owned by [`unified-trace-memory-service.md`](unified-trace-memory-service.md) § "Shared Harness/Trace Schema"** (do not define a private store). Concrete code targets for URE-1/URE-3: Q-value source `orchestration/repl_memory/q_scorer.py`, retrieval/selection `orchestration/repl_memory/retriever.py`, routing feature `src/classifiers/difficulty_signal.py`; calibration gate from eval-tower P8. **Inference run consolidated as bulk-inference Package J / J10** (shadow-only).

- [ ] **URE-1 — Uncertainty-quantified escalation signal.** Add a calibrated decision-uncertainty estimate as an escalation trigger *orthogonal* to the quality Q-value. Candidate inputs: routing classifier confidence/entropy, top-2 margin, Q-value spread, conformal abstention score, MC-dropout variance if enabled, and disagreement between rule/router/Q-scorer. High-uncertainty decisions route up even when the point Q-estimate looks fine. Connects to the DAR-1 finding that Q-values were near-uniform (96%) — uncertainty may carry signal the flat Q-band does not. Required gate before enforcement: ECE ≤ target from eval-tower P8, abstention precision above baseline escalation precision, and no >10% latency regression in shadow mode.
  - *Calibration split (2026-09-23, intake-1502):* fit temperatures on held-out sources/suites, not same-suite halves, and
    flag or refuse any fitted T < 1.0 (sharpening) — Laya shipped T 0.1006 and was worse than raw logits on 29/49 suites;
    its held-out ECE is 0.204 vs 0.030 in-task.
  - *Candidate input, shadow-only (2026-09-23, intake-1521, intake-1525):* sampled-token mean/min log-prob of the local
    model's own answer — post-generation, spec-OFF only, placeholder tokens excluded as `token_confidence.py` does. Report
    AUROC + ECE against this gate before any threshold; the signal is strongly model-dependent.
- [ ] **URE-2 — Approval/escalation as harness state.** Persist each escalation/approval decision into the trace store, not just as a transient routing event. Minimum record: `request_id`, `task_signature`, selected role/model, alternatives considered, quality score, uncertainty score and components, trigger reason, approval boundary ("what this approval permits"), human/system actor if any, downstream outcome, and linked behavior signature. Wires into [`unified-trace-memory-service.md`](unified-trace-memory-service.md) (see EXM-3).
- [ ] **URE-2a — Non-authoritative live cascade shadow.** After CJ-16 — now a LOCAL judge cascade (operator ruling Q1, 2026-09-29: local models only, no hosted Jev) — clears its frozen-fixture quality and operations gate, execute both the local first-stage choice and incumbent fallback on a frozen later-time traffic window, but continue returning the incumbent result. Persist the manifest and policy-baseline identities, per-item first-stage and fallback outputs, accepted/fallback attribution, threshold-selection split, confidence components, requested/resolved model identities, retries, typed failures, abstentions, queueing, disagreements, final outcome, end-to-end sequential p50/p95, and actual total cost from first-stage start through fallback completion. Retain every failure and abstention in the denominator and predeclare the stop/promotion rule under the [minimum viable research execution contract](eval-tower-verification.md#minimum-viable-research-execution-contract). Keep this result separate from offline substitution curves. URE-1 calibration gates authority and promotion; it does not block measurement-only shadow execution. Source: intake-1606#record.
- [ ] **URE-3 — Uncertainty as a routing feature.** If URE-1's estimate is calibrated, feed it back as a routing feature (revisits `difficulty_signal.py`, routing-index cross-cutting concern #12). Gated on URE-1 calibration quality and an ablation showing uncertainty improves routing or escalation decisions beyond existing difficulty/risk features. Start in shadow mode; do not let uncertainty recursively train itself without frozen labels.

**Audit refinements / missed gaps**:

1. **Calibration precedes enforcement.** An uncalibrated confidence score can be worse than no uncertainty signal because it creates false assurance. URE-1 must land in logging/shadow mode first and report ECE, AUC for "would escalation help?", abstention precision/recall, and per-suite calibration drift.
2. **Separate aleatoric from epistemic when possible.** Ambiguous prompts, missing context, and unfamiliar domains call for different interventions. Record component features so later work can distinguish "ask user/approve" from "route to stronger model."
3. **Approval is a bounded artifact.** URE-2 should store what was approved and what was not; e.g. "escalate to architect for plan review" is not the same as "apply code edits." This prevents approval state from becoming a vague global permission.
4. **Avoid feedback loops.** If uncertainty becomes a feature and also decides which examples get labels/escalations, the training distribution shifts. Keep a frozen shadow-calibration set and periodically re-run calibration after DAR-3/DAR-4 changes.

Additive to DAR-2/3/4 (which sharpen the *quality* Q), not a replacement — uncertainty is a second axis. Interacts with AP-27 (RLVR eval tower must score the uncertainty-augmented reward). Roll-up: [`routing-and-optimization-index.md`](routing-and-optimization-index.md) P24 § Additional task additions. Source: intake-607 `deep_dive` in `research/intake_index.yaml`.

## Post-calibration conditional workflow + mitigation (URE-1 / bulk-inference J10)

Wiring status: shadow logger **WIRED** on main (merged 2026-05-26) (`src/uncertainty_shadow.py`, flag `ORCHESTRATOR_URE_UNCERTAINTY_SHADOW_LOG`, default off, hooked at the single chokepoint `hybrid_router._record_decision_meta`, exception-safe). J10 collects shadow records → `ingest_uncertainty_shadow()` → `approval_record` → analyze. **The shadow score is UNCALIBRATED first-pass; calibration precedes enforcement (audit #1).**

Decision tree (after J10 analysis):
- ✅ ECE ≤ eval-tower P8 target AND abstention precision > baseline escalation precision AND ≤10% shadow latency regression → enable uncertainty-routed escalation (a SEPARATE enforce flag, not the shadow flag) + optionally URE-3 (uncertainty as a routing feature, frozen labels).
- ❌ any gate fails → stay shadow-only; recalibrate (re-weight the logged components / adjust threshold) on a **frozen shadow-calibration set**; do NOT enforce.

Mitigation: shadow→enforce is a deliberate second flag flip (shadow logging alone never changes routing); keep a frozen calibration set; re-run calibration after any DAR-3/DAR-4 change (audit #4, avoid feedback loop); separate aleatoric vs epistemic components so "ask/approve" vs "route-to-stronger-model" interventions stay distinct. Operator decision tree mirrored in [`bulk-inference-campaign.md`](bulk-inference-campaign.md) Package J.

## Research Intake Update — 2026-06-03

### New Related Research
- **[intake-657] "Choosing Your Model — Factory CLI (Droid)"** (https://docs.factory.ai/cli/user-guides/choosing-your-model)
  - Relevance: a closed-source competitor's *human-readable routing policy*, useful here as a hand-tuned **cold-start prior** to A/B our learned escalation against. Factory exposes a task-type→model-tier decision table (deep planning/architecture → flagship; repeatable edits/summarization/boilerplate → cheap tier; CI/CD automation loops → cheapest-predictable; high-volume quick turns → cheapest-capable) plus a per-model reasoning-effort knob (Off/Low/Medium/High/Max) with the explicit rule "**start low, escalate as needed**."
  - Key technique: their "start-cheap-escalate-on-need" heuristic is exactly the escalation policy DAR is trying to *learn* — and our current pain point is that escalation rates are **flat across difficulty bands**. Their hand-tuned task→tier mapping is a sanity prior: difficulty/task-class should monotonically raise both the tier and the reasoning-effort default.
  - Delta from current approach: selection in Factory is manual *by default*. The harvest is narrow: (1) encode their task-type→tier table as explicit cold-start labels / a baseline policy for the shadow comparison; (2) wire the reasoning-effort taxonomy + "start-low" default into [`per-request-reasoning-budget.md`](per-request-reasoning-budget.md). No new inference; pure policy-prior work. Verdict: adopt_patterns.

#### Deep-dive correction & high-value harvest (2026-06-03)
Full mining of `docs.factory.ai` (→ [`research/factory-ai-harvest-2026-06-03.md`](../../research/factory-ai-harvest-2026-06-03.md)) **corrects** the "no auto-routing" read above: **Factory Router** exists (opt-in Research Preview, `/web/factory-router.md`) — *"a per-task router that uses a mix of **session and per-request** routing"* that *"strongly considers **prompt cache** maintenance and savings,"* claiming **~20–25% cost reduction** vs always-top-tier at frontier-level perf. So we are *not* ahead on the existence of auto-routing, but it hands us a validated design + a concrete savings target. **Three router patterns to harvest here (Tier-1 backlog):**
  - [ ] **Prompt-cache-aware routing reward term** — add a `cache_affinity_bonus` (+ cold re-prefill penalty) favoring the role-server already holding the conversation prefix in slot-KV. This is a direct lever on **the flat-escalation-across-difficulty-bands open problem**: escalate only when `quality_gap` justifies the re-prefill cost.
  - [ ] **Session-sticky + per-request hybrid** — we decide per-request only; add a session-stickiness state to the outer coordinator (keep the role across turns unless escalation threshold crossed), combined with the cache-affinity term to stop flapping/cache-thrash.
  - [ ] **Reasoning-level as a first-class routing action** — make the action space `model × thinking-level` (not a fixed per-role thinking constant), operationalizing the phase-based spec/execution split.

## Deep-Dive Correction — 2026-07-21 (The DAR-1 gate metric is a tautology; root cause is the reward, not the policy)

Triggered by an intake deep-dive (intake-866/867). **The two RLM sources contributed nothing to routing** (~85% overlap with intake-536 RAO — advantage inheritance, mean-of-children, depth weighting all pre-held). What the dive found instead is a defect in this handoff's own evidence base. **All figures below were independently re-verified against source and the live store on 2026-07-21.**

**1. The regret metric cannot return non-zero.** `scripts/analysis/dar1_regret_analysis.py:241-245`:
```python
top_score = d.selection_score_topk[0]
selected_idx = d.action_topk.index(d.chosen_action)
regret = max(0.0, top_score - d.selection_score_topk[selected_idx])
```
`selected_idx` is the index of the action the selector chose — i.e. its own argmax — so `regret ≡ 0` by construction, plus an explicit `regret = 0.0` hard-assign for `strategy in ("learned","memrl")`. This measures **selector self-consistency**, not routing quality. The script's own docstring warns against exactly this reading ("Caveats are first-class so downstream handoffs do not treat proxy metrics as observed oracle regret"). The 0.00% figure that closed the expansion gate is therefore not evidence that routing is near-optimal.

**2. The reward is saturated** (`orchestration/repl_memory/sessions/episodic.db`, read-only, 2026-07-21):
- `initial_q = 0.5 + (reward * 0.5)` (`q_scorer.py:1146`, `:1202`) ⟹ `q=1.0` ⟺ reward `1.0` at write time.
- **587,391 / 661,717 rows (88.8%) are at `q_value=1.0` with `update_count=0`.**
- Outcome balance: 597,490 success / 64,229 failure = **90.3% success**.

**3. The TD update is effectively dead code in production.**
- **659,667 / 661,717 = 99.69% of rows have `update_count = 0`.** Only 1,797 rows were ever updated once, 196 twice.
- Each observation writes a NEW row (`episodic_store.py store()`) rather than updating the matching one, so `update_q_value()` (L618-678) — the apparatus DAR-1/2/3 are built on — almost never runs.

**Causal chain (this is the root cause, not the Q-value symptom):** saturated reward → dead TD path → uniform Q → zero selection-score spread → a metric that is a *function of that spread* returns 0.00% → gate closes → the freeze prevents anyone discovering links 1-2. **Self-sealing.**

Consequences for the frozen phases, stated plainly:
- **DAR-3 (SPO+) would not have helped.** SPO+ fires only when the decision would flip; with reward=1.0 on 88.8% of samples `c_true` is constant and the loss is ~0 almost everywhere. Freezing it was accidentally correct, for the wrong stated reason.
- **DAR-4/5 would not have helped either — and P4.1.3 already proved it.** Label-proxy IRT gave +9.02pp; *observed-outcome* IRT gave **0.00pp** with worse argmax match. That is the signal-vs-policy question answered in miniature.
- **DAR-2 is documented "live-ON" but may be live-ineffective:** it skips memories at default Q, and only ~2,050 of 661,717 rows have learned Q. Needs verification before the attestation stands.

**Counterweight measurement (OBSERVATION, not decision-gating).** The store contains an unused natural experiment: 622 objectives routed to ≥2 distinct roles at ≥5 observations each. Split-half (best role picked on fold A, scored on fold B): **8.40pp (A→B, n=184,628) / 8.09pp (B→A, n=179,364)** counterfactual outcome regret, against the gate's 0.00%. Caveats that MUST travel with it: assignment is not randomised (conflates role quality with selection conditions), `outcome` is a coarse binary, and stored objectives are truncated to 200 chars (`progress_logger.py:353`, `q_scorer.py:1261`) so distinct tasks sharing a prefix merge. Needs a protocol-id before it can gate anything.

- [ ] **OPERATOR DECISION (frozen gate — human-amendment-only, not an agent edit):** does fable5-02's ">=5% regret" criterion mean *selector self-consistency regret* (current implementation, definitionally ~0) or *counterfactual outcome regret* (~8.1-8.4pp)? Nothing is unfrozen pending this ruling.
  - *Decision-package input 2026-09-23 (intake-1527; annotation only — the gate is human-amendment-only):* if '>=5% regret'
    means oracle/counterfactual regret (fable5-02 L67), estimate it by cross-fitting on the store's repeated
    per-(objective, role) observations, report the single-draw noise gap G_noise, and compare 5% against the recoverable
    part only — single-draw oracle gaps can be ~the size of the threshold in noise alone (12-36% of the router-to-oracle
    gap on the paper's pools, likely underestimated).
  - *Provenance note 2026-09-23 (intake-1527 write-side check):* the '8.40 / 8.09 pp' figure above has no committed run
    artifact. The committed `dar_decisive_subset.json` @13112f77 reports a different estimand (14.73 / 14.64 pp vs
    uniform-random), and its snapshot directory no longer exists.
- [ ] **DAR-SPLIT-1 — Fix dar_decisive_subset.py selection leakage before any DAR-3 triage number is reused.** Select the decisive subset on fold A only and score on fold B; today gaps (L101-102) use all observations. Replace raw max-minus-min decisiveness (dar_common.py L170-175) with a binomial-null test. Re-state the ticked DAR-3 triage gate's number from the fixed script. Zero inference. Evidence: intake-1527.
- [x] Reward-saturation audit (zero inference, ~1 session): invert `q = 0.5 + r/2` on `update_count=0` rows, histogram reward by role and task_class. **Decision flip:** if per-decision reward entropy <1 bit AND role-conditional means differ <2pp, close DAR-3/4/5 as `not_pursued — signal-bound` rather than leaving them frozen behind a metric that can never fire. ✅ 2026-07-22
- [x] Write-path audit: is `update_count=0` on 99.69% of rows intentional (append-only replay buffer per the LRC design) or a dedup defect? Verify DAR-2 is live-*effective*, not just live-ON. ✅ 2026-07-22
- [x] Do NOT run DAR-3's 10% epsilon-greedy exploration to manufacture counterfactuals ✅ 2026-07-29 — epyc-root `bc4a7aa7` established that 386K already exist in the store for free; degrading production to collect what we already hold is strictly dominated.
- [ ] **STANDING — do NOT run DAR-3's 10% epsilon-greedy exploration in production to manufacture
  counterfactuals.** 386K already exist in the store for free (epyc-root `bc4a7aa7`); degrading
  production to collect what we already hold is strictly dominated.
  *(SPLIT 2026-08-12 by `mainC`. The ✅ recorded the DECISION, but the prohibition is live and
  load-bearing: the reward-saturation audit SPLIT and the close-as-signal-bound disposition
  explicitly DID NOT FIRE, so DAR-3 remains open work someone can pick up. A closed box left
  the one rule protecting production from that pickup invisible.)*
- [x] Raise the 200-char `objective` truncation before any counterfactual/competence analysis is run at promotion grade (runtime embedding path is NOT truncated, so live routing is unaffected). ✅ 2026-07-22

### Reward-Saturation Audit — EXECUTED 2026-07-21 (zero inference; read-only SQLite over episodic.db)

Pre-registered disposition was: *"if per-decision reward entropy <1 bit AND role-conditional means differ <2pp, close DAR-3/4/5 as `not_pursued — signal-bound`."* **The audit SPLITS: condition 1 fires, condition 2 does not. The close-as-signal-bound disposition therefore DOES NOT FIRE.**

Result: reward entropy 0.6877 bits (saturated) but role spread 11.06pp; within-objective gap mean 11.61pp / median 0.00pp; 136/621 = 21.9% of objectives decisive (a floor). Tables in the [completed sibling](../completed/decision-aware-routing-completed-through-2026-09-27.md).

**Revised disposition (supersedes the pre-registered one):**
- [x] Reward-saturation audit executed — entropy 0.6877 bits (saturated) but role-conditional spread 11.06pp (separating). Split verdict; close-as-signal-bound does NOT fire. ✅ 2026-07-21
- [ ] Do NOT close DAR-3/4/5 as `not_pursued — signal-bound`. The correct reframing is **triage, not policy**: the target is a *gate* that identifies the ~22% of objectives where role choice is outcome-relevant, not a better global argmax. Re-scope DAR-3/4/5 accordingly before considering any unfreeze. ✅ 2026-07-29 — already executed in the same handoff's **DAR-3 / DAR-4 / DAR-5 RESCOPE** section: DAR-3 is the decisive-subset triage gate with no epsilon-greedy collection, DAR-4 is retained only for fixed-reward retraining, and DAR-5 is gated on the wall-clock reward redesign.  *(Restored to `- [ ]` 2026-08-11 by `mainC` — standing constraint with no completion state; the dated evidence below is kept, the rule is live again.)*
- [x] Highest-value next measurement (zero inference): restrict the existing DAR-2 contrastive objective — and any future policy eval — to the matched decisive subset, and report lift THERE rather than over all traffic. A policy that improves the 22% while leaving the 78% untouched is invisible in every metric used so far. ✅ 2026-07-22
- [ ] Reconsider the reward itself before the policy: at 89.05% at exactly +1.0 with a −0.4 penalty tail, this is a success/failure flag wearing a continuous type. Graded reward on the decisive subset is likely worth more than any loss-function change.
- NOTE the confound that still stands: role assignment is not randomised, so marginal per-role means conflate role quality with the conditions under which each role is selected. The matched within-objective figures control for task identity but NOT for selection-within-task. Everything above is an OBSERVATION under MEASUREMENT.md; none of it is protocol-attested and none of it gates a promotion.

#### Operator qualification (2026-07-21) — the 78% figure is quality-only, and the corpus is tier-skewed

Two corrections to the audit reading above, from the operator:

1. **"Roles score identically" is a QUALITY statement, not a routing-indifference statement.** Autopilot optimizes task execution **speed × quality**. On the ~78% of objectives where every role reaches the same outcome, the correct action is still not arbitrary — it is *route to the cheapest/fastest role that clears quality*. So that majority is not "the decision does not matter"; it is "the decision is dominated by the cost term" — which is exactly what DAR-1 observed empirically (cost and similarity terms drive selection; Q-values are decorative). The two findings agree, and the reward as currently constructed simply **cannot express the speed half of the objective at all** — it collapses to a success flag. That is a second, independent argument for fixing the reward before the loss function.
2. **The measured corpus is tier-skewed toward T0/T1.** The 661,717 memories are dominated by autopilot eval traffic, which is mostly T0/T1 tasks. Easy tasks are exactly where models converge, so a 90.3% blanket success rate and a median 0.00pp role gap are partly an artifact of task difficulty, not evidence that roles are interchangeable in general. **T3 would plausibly show materially more quality divergence across roles/models** — and T3 is where routing errors are most expensive. This means the ~22% decisive-objective estimate is likely a FLOOR, and the audit understates the achievable headroom.

Combined implication: the triage-gate framing survives, but its target sharpens. The gate should separate (a) the cost-dominated majority, where the objective is cheapest-role-that-clears-quality, from (b) the quality-decisive minority, which is under-represented in the current corpus and concentrated at higher tiers.

- [x] Re-run the matched within-objective analysis **stratified by task tier (T0/T1/T2/T3)** before drawing any conclusion about how much of the corpus is genuinely role-indifferent. Current estimate (21.9% decisive) is derived from a T0/T1-dominated sample and is probably a floor. Zero inference — the tier label needs to be recoverable from the stored context/objective or joined from the eval-tower record. ✅ 2026-07-22
- [ ] Any redesigned reward MUST carry the speed axis, not just the outcome flag — autopilot's objective is speed × quality and the current `reward` collapses to success/failure. This is a prerequisite for the majority regime, where cost is the operative term.

## ROOT CAUSE FOUND — 2026-07-21: the cost/speed half of the reward was dead due to a key-name mismatch

compute_reward read role, telemetry wrote producer_role, so every cost dimension was skipped (0/20,521 rows carried role). The fix reads role → producer_role → final_answer_role; replay 0.0000 → 2.4580 bits. Evidence in the [completed sibling](../completed/decision-aware-routing-completed-through-2026-09-27.md).

### Retroactive rescoring is possible

- **94.5%** of `task_completed` entries carry usable speed telemetry (`tokens_generated` 99.8%, `generation_ms` 99.8%, `prompt_eval_ms` 99.8%, `http_overhead_ms` 99.8%).
- **20,516 `task_started`/`task_completed` pairs** carry timestamps, so **true wall-clock task duration is recoverable** — 85 days of progress logs are retained.
- Rescoring is therefore a replay over `logs/progress/*.jsonl`, not a re-run. It creates an instrument-era boundary: pre-fix stored `q_value`s and post-fix rewards are **not comparable**, and the era must be recorded before any mixed-era comparison is made.

- [x] Root-caused the reward saturation to a `role` vs `producer_role` key mismatch; fixed with regression tests; replayed on 20,526 historical completions (0.0000 → 2.4580 bits). ✅ 2026-07-21
- [x] Add a **wall-clock task-duration** term as the speed axis, derived from `task_started`→`task_completed`, and demote the tokens/sec term to a secondary signal. Per-role p50/p90 baselines above are computable from the retained logs — derive them under a protocol id rather than hand-setting constants.
  - [x] **Implemented, landed DEFAULT-OFF** ✅ 2026-09-24 — orch `b8035db9` + `88e24ef0`. Baselines: `scripts/analysis/derive_duration_baselines.py` → `orchestration/derived/duration_baselines_by_role.json` (protocol id `RTG09-DURATION-BASELINE-v1`, an analysis id not a MEASUREMENT.md protocol; 137,256 pairs, 117 logs 2026-02-27..09-23, min n 30/role — e.g. frontdoor p50 27.6s/p90 116.1s, worker_general 16.2/55.1, coder_escalation 9.1/75.4; toolrunner and worker_explore under n=30). `compute_reward` Dimension 0: 0 at the role's p50 → full `cost_lambda_duration` at p90, saturating; a missing duration or a role with no baseline skips only that dimension and warns once. `task_duration_s` wired at all 3 call sites (`QScorer._score_task`, replay engine, `rescore_rewards_from_progress.py`). Lands with `cost_lambda_duration=0.0`, `cost_penalty_lambda=0.15`: the live reward is byte-identical (tested), because a reward-distribution change is a `routing_reward` era boundary (cf. E9) and rewards feed Q-updates continuously. 120 tests pass.
  - [x] **Operator: apply the RTG-09 ratification** — `bash scripts/operator/ratify_rtg09_duration_reward_20260924.sh --show`, then `--apply`: flips 0.20 / 0.05 and appends era `E18-routing-reward-duration-axis` in one orchestrator commit, then reload the API. Ticking this ticks the parent box and unblocks DAR-5. ✅ 2026-09-24 (operator: "apply OP-47") — orch `60bfc4c4` RATIFIED: era `E18-routing-reward-duration-axis` from 2026-09-24T10:02:39Z; defaults 0.20 / 0.05. The script's post-flip test gate refused the first apply because 8 tests encoded the default-off contract; they moved with the flip in the same commit (121 pass). A `set -e`+`pipefail` bug in the script (zero-match `grep | wc -l`) was fixed first (root `c9450f9f`). API reloaded 10:13:35Z; live `ScoringConfig()` = 0.2 / 0.05 with 10 role baselines. DAR-5 is unblocked.
- [ ] Record the instrument-era boundary for reward values before any pre/post-fix comparison is made or any policy is trained across it.
  - [x] **Pre-validated human-amendment token authored ✅ 2026-07-29**: `RATIFY-E9-ROUTING-REWARD-ERA-20260729` is in `outbox/mainB.jsonl` with an append-only, SHA-pinned command and copy-only YAML validation (`dry_run_exit=0`). Await operator signature; agents did not edit `orchestration/instrument_eras.yaml`.
- [ ] Optional: replay-rescore historical rows so the episodic store carries post-fix rewards. Not indispensable (the logs are the source of truth and can be replayed on demand), but it would make the 174K-row store trainable without a join.

## DAR-3 / DAR-4 / DAR-5 RESCOPE — approved 2026-07-21

Superseding the "FROZEN pending a ≥5% regret replay" status. That gate was measured by a metric that cannot return non-zero (see the tautology finding above), so it was never a real gate.

**They are not unfrozen, and they are not closed. They are re-aimed.** The three phases were designed to improve a *global argmax* over a target that carried zero bits. Both premises are now known false: the target was broken (fixed above), and the majority regime is not quality-discriminative (median within-objective role gap 0.00pp; only 21.9% of objectives decisive, and that is a floor given the T0/T1-skewed corpus).

New shape:

- [x] **DAR-3 (was SPO+/epsilon-greedy) → triage gate.** Build a classifier that separates *cost-dominated* objectives (any role clears quality; choose cheapest/fastest) from *quality-decisive* objectives (role choice changes the outcome). Report lift on the decisive subset, never on all traffic — a policy that fixes the 22% and leaves the 78% alone is invisible in every metric used to date. **Do NOT run the original 10% epsilon-greedy exploration**: 386K counterfactual decisions already exist in the store for free, so degrading production to manufacture them is strictly dominated. ✅ 2026-07-22
- [ ] **DAR-4 (bilinear descriptor-conditioned predictor) → retained, but retrain on the fixed reward.** Its prior null (P4.1.3: label-proxy IRT +9.02pp, observed-outcome IRT 0.00pp) is now explained — the observed outcome was constant. Re-run before drawing any conclusion about the model class.
- [ ] **DAR-5 → gated behind the reward redesign, not behind a regret replay.** Precondition is a reward carrying a wall-clock speed axis (above), since the cost-dominated majority is where most traffic lives and the current reward cannot price it.
- [x] Re-run the matched within-objective analysis **stratified by task tier (T0/T1/T2/T3)** before sizing any of this. 21.9% is derived from a T0/T1-dominated sample and is expected to rise at T3, where routing errors are most expensive. ✅ 2026-07-22

### Reward-integrity follow-up — 2026-07-21 (role-field validation)

The rescore surfaced a second defect of the same shape as the `role`/`producer_role` miss. `ChatRequest.role` and `.force_role` were unvalidated `str` fields, and `stream_adapter.py:178` feeds `request.role` straight into telemetry as `producer_role`. Because `compute_reward` uses that value as a `baseline_tps_by_role` key, **an unresolvable role skips every cost dimension and scores the full base reward** — so unvalidated client input could suppress the entire cost/speed penalty. That is a latent reward-hacking surface, not just a hygiene issue, and it matters more now that the cost path actually fires.

- [x] Validated `role`/`force_role` at the API boundary via the existing `Role.from_string` (rejects free text, case-normalizes, passes pipeline sentinels); added a warn-once at the reward site for any role with no `baseline_tps_by_role` entry, so the miss can never be silent again. `epyc-orchestrator 6344fbdb`, 16 tests. ✅ 2026-07-21
- [x] Blast-radius verified by call-site analysis (gitnexus segfaulted): every production `force_role` value survives, including legacy aliases `reviewer`/`reviewer_agent`/`architect_coding`. One documented behaviour change — `memrl.should_skip_background_scoring` is `bool(force_role) and bool(real_mode)`, so an invalid `force_role` rewritten to `""` no longer suppresses background scoring; pinned by test in both directions. ✅ 2026-07-21
- [x] Confirmed `architect_coding` is genuinely deprecated (rows stop 2026-06-13), so its post-fix `+1.0000` is historical replay, not a live scoring gap; allow-listed alongside `mock`/`plan_review` to keep rescores quiet. ✅ 2026-07-21
- [ ] Consider splitting a separate `stage` field out of `producer_role`: the same field currently carries real roles AND pipeline sentinels (`plan`, `stream_init`, `proactive_delegation`, `mock`). Harmless today, but overloading the key that prices the reward is how this class of bug recurs.

## Research Intake Update — 2026-09-07

**Risk note — orchestration features carry a capability floor** (`intake-1333#06`, dive-verified).
Richer orchestration **REGRESSED** quality on all three smaller models, concentrated in
orchestration-heavy capabilities (Qwen 3.6 MCP .65 → .50), and sub-agent delegation scored 0.42–0.45
on the fast tier. Directional and vendor-internal, so it **cannot gate a decision** — but it suggests
routing on **feature demand** rather than prompt difficulty. Zero compute.

## Research Intake Update — 2026-09-26 (orchestration prior art: static latency prior + saturation guard; intake-1796/1797/1798/1815)

Selection has no latency or load term today. The only cost is historical elapsed from memory
(orch @fb7871ea `retriever.py:46-57`, fed by :113-142), and `baseline_tps_by_role` is reward-side only
(`q_reward.py:223`). The dive puts the gain on a latency term and found a static per-tier prior as good as a
learned live estimate (intake-1796#02). The regime left open is ours: single-instance, TTFT-bound, preferred tier
saturated (intake-1798#05; intake-1797#04). The terms land at weight 0 like DAR-4b: they do not reopen the
DAR-3/DAR-6 expansion gates, and nothing changes live routing until DAR-LAT-3 decides.

### DAR-LAT — ❄ FROZEN 2026-09-27 (do not dispatch; each box carries its unfreeze trigger — since 2026-09-29: autopilot has trained on the swapped stack AND UFH-13 re-opened)

- [ ] ❄ FROZEN 2026-09-27 — resume only once autopilot has trained on the swapped stack AND UFH-13 re-opened (operator ruling 2026-09-29) — **DAR-LAT-1 — Build the shared `SlotCapacity` snapshot and `expected_wait_s(role)` on the ONE admission ledger.**
  Role-keyed over the role's backend URLs:
  - `queued` = `AdmissionController` waiting_*, `running` = in_flight, `limit` = np (orch `src/api/admission.py:229-245`).
  - `kv_occupancy` comes from the existing `/slots` reader (`context_limits.py:433-452`); extend `parse_slots` with
    `n_decoded`.
  - Every field carries a source label.
  - Record dispatch start time + predicted length at `acquire`/`release` and dead-reckon the expected wait (0 when
    a slot is free).
  - No new poller and no `/metrics` dependency (Axiom 1, heterogeneous-slot-fabric-residency.md:201).
  - Direct consumers: DAR-LAT-2 and harness-selection-and-integration.md HS-OD-9 (c2-A1). Interface:
    `expected_wait_s(role, priority="interactive")` returns seconds or None with `basis` and `source`; each consumer
    applies its own fallback.
  - Tests: ledger/`/slots` agreement, free-slot W=0, fail-open when the ledger is absent. intake-1796#01, intake-1798#02.
  ❄ FROZEN 2026-09-27 (operator, narrowed plan): DAR-LAT is frozen once DAR-LAT-3h's G1 is recorded; the load-sweep programme is not on the thesis path; unfreeze trigger: DAR-LAT-3h's G1 is recorded (the only DAR-LAT work that proceeds) AND (operator ruling Q2, 2026-09-29, replacing "the UFH-13 thesis experiment shows that selection under load matters", which cannot fire while UFH-13 is PARKED) autopilot has trained on the swapped stack AND UFH-13 re-opened. The box stays open: frozen is not done.
- [ ] ❄ FROZEN 2026-09-27 — resume only once autopilot has trained on the swapped stack AND UFH-13 re-opened (operator ruling 2026-09-29) — **DAR-LAT-2 — Add the static per-role latency prior + saturation guard to `HybridRouter._apply_priors`
  (`hybrid_router.py:308-327`), landed at λ_lat=0 (byte-identical, test-pinned).**
  - `score −= λ_lat·(T̂+W)/T_ref`, with `T̂ = L̂(role)/baseline_tps_by_role[role]` (provenance-labelled,
    `q_scorer.py:386-402`).
  - `L̂` = per-role p50 `tokens_generated` from `logs/progress` under an analysis id.
  - `W` = DAR-LAT-1; missing inputs give term 0 plus a penalty flag (rider §7 Q1: soft cost fails open).
  - Emit a per-decision selection receipt: components, admission snapshot, and the selection-time role vs the final
    role after X-MAS (`routing.py:318`) and the failure veto (:344).
  - Env-gated AB mode: per-request arm id, declared candidate restriction, read-only episodic snapshot, Q-updates
    off, arm-A2 live term from `/slots` (busy flags + `n_decoded`). intake-1796#02, intake-1798#04.
    - Key every prior row by (role, device, topology_hash), never by role alone: record the device (CPU region set or MI210) and the `ContentionGate._live_topology_hash()` value (orch `src/scheduling/contention_gate.py:141`) the TPOT/L̂ inputs were derived under. A row whose topology_hash differs from the live stack contributes term 0 plus a `prior_stale` flag (the same fail-open path as a missing prior), so a stack change or a Layer-2 residency swap cannot leave a CPU-era prior pricing a GPU-resident role. Re-derive the table on every stack change. RouterWise's latency model is per (model, setup) and its own router is a static prior with no live arm (intake-1815#0, intake-1815#6).
  ❄ FROZEN 2026-09-27 (operator, narrowed plan): DAR-LAT is frozen once DAR-LAT-3h's G1 is recorded; the load-sweep programme is not on the thesis path; unfreeze trigger: DAR-LAT-3h's G1 is recorded (the only DAR-LAT work that proceeds) AND (operator ruling Q2, 2026-09-29, replacing "the UFH-13 thesis experiment shows that selection under load matters", which cannot fire while UFH-13 is PARKED) autopilot has trained on the swapped stack AND UFH-13 re-opened. The box stays open: frozen is not done.
- [ ] ❄ FROZEN 2026-09-27 — resume only once autopilot has trained on the swapped stack AND UFH-13 re-opened (operator ruling 2026-09-29) — **DAR-LAT-3 — Load-sweep A/B on the single-instance saturating tier under a TTFT-bound workload:
  Qwen3.8-Flash-Next (`architect_critic` :8074, `-np 1`) with divert target `architect_general` (:8083, MI210).**
  - Arms: A0 incumbent (λ_lat=0), A1 static prior + guard, A2 A1 + live `/slots` term.
  - Results go to `epyc-inference-research/data/sel-loadsweep-ab-<UTC>/`.
  - Decision rule (predeclared, frozen in FROZEN-AT-LAUNCH.sha256):
    - Adopt A2 only if S = TTFT-SLO attainment beats A1 by more than floor F (24 A1/A1 block pairs at ρ=1.25,
      unit=arm) at ≥2 saturating ρ, AND reproduces at ρ=1.25 in holdout window W2, AND quality is non-inferior (≥ −1
      per-suite quantum), AND no ρ<1 point degrades by more than F.
    - Otherwise write a BOUNDED-NULL-1 statement and keep static + guard.
    - The same structure clears A1 against A0.
  - Settles the c1 open residual. intake-1796#02, intake-1797#04, intake-1798#05.
  ❄ FROZEN 2026-09-27 (operator, narrowed plan): DAR-LAT is frozen once DAR-LAT-3h's G1 is recorded; the load-sweep programme is not on the thesis path; unfreeze trigger: DAR-LAT-3h's G1 is recorded (the only DAR-LAT work that proceeds) AND (operator ruling Q2, 2026-09-29, replacing "the UFH-13 thesis experiment shows that selection under load matters", which cannot fire while UFH-13 is PARKED) autopilot has trained on the swapped stack AND UFH-13 re-opened. The box stays open: frozen is not done.
  - [ ] ❄ FROZEN 2026-09-27 — resume only once autopilot has trained on the swapped stack AND UFH-13 re-opened (operator ruling 2026-09-29) — **DAR-LAT-3a — Freeze the pre-registration.**
    - Manifest: seeded MMLU-Pro/GPQA items (the frozen-v10 sets, amd-ai-lab-website-publication.md:18), `max_tokens`
      cap, candidate pair, dry-route-explain filter (architect_critic chosen under A0 and A1 at zero load), frozen
      prior table (keyed by role/device/topology_hash, with the live topology_hash at freeze) and episodic snapshot
      digests.
    - Calibration on the 50% calibration half: μ̂ and TTFT budget = 2 × unloaded p50 per length bucket.
    - Load points: ρ ∈ {0.5,0.8,1.0,1.25,1.6,2.0}×μ̂, 40 Poisson arrivals per block, ABBA arm order per ρ.
    - Denominator: every arrival; failures count as misses and quality 0; no retries.
    - Claim grade: the serving-selection load-sweep protocol **P-SERVE-SEL-1 — ratified 2026-09-26 (operator,
      orchestrator-design session) and LANDED 2026-09-26** (commit 3573028b: annex in
      `measurement/protocols/quality-eval.md`, MEASUREMENT.md row, §5 receipt
      `artifacts/operator/receipts/RATIFY-P-SERVE-SEL-1-20260926.json`; executed by session workspace-8d at the
      operator's explicit instruction, `--verify` passed). The A/B is decision-grade: record the protocol id in the
      manifest before the freeze.
    ❄ FROZEN 2026-09-27 (operator, narrowed plan): DAR-LAT is frozen once DAR-LAT-3h's G1 is recorded; the load-sweep programme is not on the thesis path; unfreeze trigger: DAR-LAT-3h's G1 is recorded (the only DAR-LAT work that proceeds) AND (operator ruling Q2, 2026-09-29, replacing "the UFH-13 thesis experiment shows that selection under load matters", which cannot fire while UFH-13 is PARKED) autopilot has trained on the swapped stack AND UFH-13 re-opened. The box stays open: frozen is not done.
  - [ ] ❄ FROZEN 2026-09-27 — resume only once autopilot has trained on the swapped stack AND UFH-13 re-opened (operator ruling 2026-09-29) — **DAR-LAT-3g — GATE (acquire, never observe):**
    - bus-granted whole-host window (INVARIANTS #8), because MEAS-6 forbids a concurrent CPU/GPU campaign;
    - `region-lock run --cpu-list 0-95 -- <driver>` (OPERATING_CONSTRAINTS.md:106) + MI210 lease;
    - AutoPilot quiesced by its owner; experiment API on its own port with a captured PID (production API untouched,
      :125);
    - host-health preflight (:110);
    - quiet-window preconditions (bench-cpu.md:59), checked via region holders and captured PIDs, never name patterns;
    - other servers sampled idle DURING each block;
    - live :8074 argv/env = the registered recipe incl. the OMP stack (bench-cpu.md:116);
      - **Fails as of 2026-09-26 (blocks this gate):** live `:8074` runs `-t 96` (ps, 2026-09-26), while the registry
        recipe says `threads: 48` (orch `model_registry.yaml:1899-1904`) and the codified recipe says
        `THREADS = 48  # NOT 96: the served decode optimum` (`qwen38_flash_next_recipe.py:690`); the likely source is
        the stack template's `threads: 96` (`stack_templates/default.yaml:155`). Production `n_ctx` 262144 also
        differs from the recipe's validated 8192. This is a production launch change, so it is reconciled only by a
        signed `stack-change` package (the lineup/recipe owner), never an ad-hoc relaunch; 3g stays blocked until then.
        **2026-09-27: resolved in substance by DAR-LAT-3h G1 (T96):** live `-t 96` is the measured-better shape, so the
        live argv is the one to hold; the registry `recipe:` text still says 48 (SSU-F11; not applied, see RESULT.md).
    - VB-SEL-LOADAB wired.
    ❄ FROZEN 2026-09-27 (operator, narrowed plan): DAR-LAT is frozen once DAR-LAT-3h's G1 is recorded; the load-sweep programme is not on the thesis path; unfreeze trigger: DAR-LAT-3h's G1 is recorded (the only DAR-LAT work that proceeds) AND (operator ruling Q2, 2026-09-29, replacing "the UFH-13 thesis experiment shows that selection under load matters", which cannot fire while UFH-13 is PARKED) autopilot has trained on the swapped stack AND UFH-13 re-opened. The box stays open: frozen is not done.
  - [x] **DAR-LAT-3h — Prepare the `:8074` recipe-reconciliation stack-change package that unblocks 3g.** ✅ 2026-09-27 —
    package v2 signed (`RATIFY-DAR-LAT-3H-CRITIC-THREADS-20260926`); G1 chose T96; **NOTHING APPLIED** (live `:8074`
    already runs `-t 96`). The `lane/dar-lat-3h-v2-*` lanes are NOT to be merged. Result:
    [`RESULT.md`](../../artifacts/operator/stack-change-dar-lat-3h-20260926/RESULT.md) and `g1-result/verdict.json`.
    Full box text: [completed sibling](../completed/decision-aware-routing-completed-through-2026-09-27.md).
  - [ ] ❄ FROZEN 2026-09-27 — resume only once autopilot has trained on the swapped stack AND UFH-13 re-opened (operator ruling 2026-09-29), or the operator reopens it — **DAR-LAT-3i — Decide `GGML_FA_SPLIT_KV=0` for the `:8074` critic at its served context.** The operator split it
    out of the DAR-LAT-3h package on 2026-09-26, after the GGML_* env audit. It is recorded under master registry
    `server_mode.architect_critic.recipe.env_not_serving`.
    - Why it is separate:
      - It changes numerics (BE-2: a row-exact reduction order for 1-row decode vs n-row MTP verify).
      - It is a perf risk at long context: single-row decode loses KV-axis parallelism.
      - The critic serves `n_ctx` 262144, and DAR-LAT-3h's G1 exercises only up to ~4k-token prompts.
    - Does not block 3g: the DAR-LAT-3h package does not set the knob.
    - Needs, all on production v10 at the served argv, as launch-unit arms (`FA_SPLIT_KV` unset vs `=0`) under a
      region claim in a quiet window:
      1. A long-context decode arm: tok/s at KV depths up to the served context (at least 64k and 128k, plus the
         deepest the host fits), and TTFT.
      2. A numerics check: greedy output agreement, first-divergence position, and MTP acceptance α.
      3. Per-suite quality non-inferiority on the DAR-LAT-3a item sets.
    - Adopt only if the knob is non-inferior on speed at every depth and on quality. The change ships as its own
      `stack-change` package, which adds it to the critic's `stack_env` block.
    ❄ FROZEN 2026-09-27 (operator, narrowed plan): a numerics-and-long-context knob for the critic seat; no thesis arm depends on it; unfreeze trigger (operator ruling Q2, 2026-09-29; it replaces "the UFH-13 verdict makes the critic seat's served shape decision-relevant"): autopilot has trained on the swapped stack AND UFH-13 re-opened, or the operator reopens it. The box stays open: frozen is not done.
  - [ ] ❄ FROZEN 2026-09-27 — resume only once autopilot has trained on the swapped stack AND UFH-13 re-opened (operator ruling 2026-09-29) — **DAR-LAT-3b — Run W1** (calibration, then the arm sweep plus the 24 A1/A1 floor pairs). Stop on any
    prerequisite that fails during a block; re-queue the block, never drop it. Per-request receipts + raw outputs.
    ❄ FROZEN 2026-09-27 (operator, narrowed plan): DAR-LAT is frozen once DAR-LAT-3h's G1 is recorded; the load-sweep programme is not on the thesis path; unfreeze trigger: DAR-LAT-3h's G1 is recorded (the only DAR-LAT work that proceeds) AND (operator ruling Q2, 2026-09-29, replacing "the UFH-13 thesis experiment shows that selection under load matters", which cannot fire while UFH-13 is PARKED) autopilot has trained on the swapped stack AND UFH-13 re-opened. The box stays open: frozen is not done.
  - [ ] ❄ FROZEN 2026-09-27 — resume only once autopilot has trained on the swapped stack AND UFH-13 re-opened (operator ruling 2026-09-29) — **DAR-LAT-3c — Holdout W2 (≥24 h later, ρ=1.25, ABBA, fresh seeds) + verdict.** PAIRED-CI-1 within a window
    only; W1 and W2 are never pooled (MEASUREMENT.md:434-438). Record the verdict and, on A2 loss, the BOUNDED-NULL-1
    power bound + positive-control readback.
    ❄ FROZEN 2026-09-27 (operator, narrowed plan): DAR-LAT is frozen once DAR-LAT-3h's G1 is recorded; the load-sweep programme is not on the thesis path; unfreeze trigger: DAR-LAT-3h's G1 is recorded (the only DAR-LAT work that proceeds) AND (operator ruling Q2, 2026-09-29, replacing "the UFH-13 thesis experiment shows that selection under load matters", which cannot fire while UFH-13 is PARKED) autopilot has trained on the swapped stack AND UFH-13 re-opened. The box stays open: frozen is not done.

**Default-weight flip (trigger prose, no checkbox).**
- Fires only when DAR-LAT-3c clears A1 (or A2) against A0.
- The flip is a routing-policy change. It needs an operator-signed instrument-era row (cf. E18) through consolidated
  ratification (MEASUREMENT.md:181), bundled with the P-SERVE-SEL-1 ratify script if the operator has not yet run it.
- If A2 wins, the learned/live-predictor question declined in learned-routing-controller.md (C1-A4) reopens. An
  SFS-style engine simulator stays excluded by the frozen kernel (intake-1798#06).

**Mixture-of-agents trigger (prose, no checkbox).**
- Fires if DAR-6 swarm-fanout or any cross-model aggregation mode is re-authorized on the x_* surface.
- Before choosing cross-model mixing vs same-model multi-sample aggregation, dive intake-1799#record and
  intake-1802#record (both stage1-unverified; do not cite their numbers until dived).

**Code pointers as of orch @fb7871ea (dated note; the Key Files table above is historical).**
- Selection score: `_scalarized_selection_score` at `retriever.py:46-57`, called at :286-297 and :786-810.
- Prior blend: `hybrid_router.py:308-327`.
- Initial route: `routing_decision.py:259-314`.
