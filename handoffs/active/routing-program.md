# Decision-Aware Routing for Q-Scorer

> **Fold destination** (BRF-T7-F16, BRF-T7-1, route 1b, 2026-11-03): every former handoff of this plan target is a `## Track:` with its own gate marker: `routing-program`, `routing-intelligence` (rows RTG-30 retired into RTG-09). The former `routing-program.md` body is `## Track: routing-program`; tracks those handoffs already had are lifted verbatim after their owner.

> **Fold destination** (BRF-T1-F26, BRF-T1-1, route 1a, 2026-11-02): renamed from `decision-aware-routing.md`; absorbs 7 handoff(s) as `## Track:` sections at the end of this file (`internal-interaction-lifecycle.md`, `learned-routing-controller.md`, `model-capability-descriptors.md`, `retrain-routing-models.md`, `tri-role-coordinator-architecture.md`, `typed-decision-plane.md`, `x-mas-text-routing.md`). The body above the first track is the former `decision-aware-routing.md`.

**Status**: ACTIVE, mostly waiting — DAR-2 contrastive is live-ON; DAR-3/DAR-6 FROZEN (fable5-02); DAR-3/4/5 re-aimed 2026-07-21 (§ RESCOPE); the reward carries the wall-clock axis since era E18 (2026-09-24); DAR-LAT is ❄ FROZEN (2026-09-27; unfreeze trigger since 2026-09-29: autopilot has trained on the swapped stack AND UFH-13 re-opened). Completed DAR-1/DAR-2/DAR-1.5 record: § Completed Scope.
**Created**: 2026-04-14 (from deep-dive research on intake-366)
**Updated**: 2026-07-03 (current-window DAR-1 replay; prior body updates through 2026-04)
**Priority**: HIGH
**Categories**: routing_intelligence, reinforcement_learning, cost_aware_routing
**Tracked in**: [routing-and-optimization-index.md](routing-and-optimization-index.md) P13
**Cross-claim (2026-06-12)**: DAR-1 replay deliverable + the ≥5%/<5% fork are closed in [routing-truth-restoration.md](../completed/routing-truth-restoration.md) W8; this handoff retains the future learned-routing research items only if a later gate re-opens them.

## 2026-11-09 audit refresh

Staleness audit (RTG-09, 66 open boxes); Autopilot stays on operator HOLD (never start it). Goal of this campaign: orchestration stack running by end of November 2026. Autopilot last truly ran 2026-08-09T19:29Z (trial 1503); the audit's "journal last entry 06-27" is the journal file mtime, not the last run. A brand-new era will be set up for the relaunch.

- **Next action (lead):** DAR-SPLIT-1 (split-half decisive subset, zero inference), then RTG-DUR-1 (duration-baseline refresh rule and compiler, below). RTG-EP-1 is no longer the lead: it needs MIGraphX built first and nothing here depends on it.
- **Doable now (no inference, no Autopilot):** DAR-SPLIT-1, RTG-DUR-1 (derive script exists), RTG-RETRAIN-1 design, DAR-4b replay, TD-29.M2/M3, TD-30a rebase, RI-10 decision packet on post-07-23 traffic, RI-18c reading, RTG-VAR-1/2 schema work.
- **Needs compute:** RI-17, RI-19, TR-5.3, P5.2, DAR-6.5/J14, TD-1d.*, TD-29.M4, RTG-EP-1 (GPU window).
- **Waits on the Autopilot hold:** DAR-LAT-1/2/3/3i, LRC-1, TD-28, P3-3/P3-4/P4-2.
- **Anchor rot (measured; text is the identity):** `features.py:258` typed_decisions_tool_args is now :335; routing_classifier flag :123 is now :133; hybrid_router `_apply_priors` 308-327 is now :332; `builder.py:287` Routing Intelligence is now :323/:817; `admission.py:229-245` is now `get_status` (SlotCapacity exists only in `src/embedding_pool/busy.py`; `expected_wait_s` has zero hits). The `Updated:` header predates the body edits.
- **New (2026-11-09):** EG2 v11 boundary track, RTG-DUR-1, RTG-RETRAIN-1 below; EPD-3 folded into the EG2 re-embed (see EPD-3).

### Planned track: EG2 (v11) embedding boundary and stale-stack inputs

- [ ] **RTG-EG2-1 — Own the EG2@256 boundary for routing artifacts.** `scripts/migration/reembed_stores_eg2.py:140-200` (orchestrator; commits 931ba135, 249ff242, 46f03ecc) lists everything trained or tuned on BGE-1024 that the v11 EmbeddingGemma-2 swap invalidates: `routing_classifier_weights.npz` (06-12, 8 classes) and `_kl.npz` (06-26, 6 classes), `verifier_head_weights.npz` (05-21), `training_data.npz` (526,661x1031, 07-06, git-ignored), offline-reward/verifier weights, the IRT projector (REPL-EMB-R1), GAT (none on disk, REPL-EMB-R3), and every cosine threshold (`min_similarity` 0.3, 0.85 same-item, 0.8/0.5 classifier/verifier; REPL-EMB-R5). Boxes that cross the boundary (each carries a dated EG2 note with what to regenerate): DAR-4, DAR-5, P1.5.2, P5.2, TR-5.3, RI-10, RI-17, RI-19. Acceptance: one table (box -> artifact -> regen owner -> before/after-v11 ordering) in this handoff, checked against the migration script's list; owners are REPL-EMB-R1..R5 in `harness-program.md` where they exist. Standalone, zero inference.
  - Ordering rule: do not spend a training run on BGE-1024 inputs that v11 will invalidate; run RI-17 on both sides of the re-embed; EPD-3 rides the same single re-embed (see EPD-3).
- [ ] **RTG-DUR-1 — Refresh rule and compiler for `orchestration/derived/duration_baselines_by_role.json`.** The file is static: generated 2026-09-24, window 2026-02-27..09-23 (117 files), 10 roles including deprecated `architect_coding` (n=5870) and a pre-ARCHSWAP `architect_general` (n=14543; Flash-Next since 09-27), loaded at `orchestration/repl_memory/q_scorer.py:99` (`load_duration_baselines_by_role`). `scripts/analysis/derive_duration_baselines.py` can regenerate it, but nothing triggers it and neither the registry nor stack-priors compiler touches it; E18 (`instrument_eras.yaml:452`) records the flip with no refresh trigger. Consequence: a role whose model changed is priced against the wrong distribution (rewards since 09-27 for `architect_general` are wrong; `coder_escalation` p50 9.1 s / p90 75.4 s is the pre-27B coder; `worker_vision` baselines are from the old VL model). Scope: (a) key baselines by model identity (descriptor v3), not role, or invalidate a role's entry when its bound model changes; (b) a refresh rule (new window after any lineup change, minimum n, expiry age) and a compile step wired next to `src/registry/stack_priors.py`; (c) regenerate on post-lineup traffic; (d) a staleness warning when the file's window predates the bound model. Acceptance: a test that fails when a role's bound model changed after the baseline window; regenerated file with window and n per model. Changing the live baseline changes the reward: this is an era decision (human-only `instrument_eras.yaml`), so prepare the package and do not edit eras. Zero inference for (a)-(d); the era is the operator's.
- [ ] **RTG-RETRAIN-1 — Retrain routing classifiers on model-keyed labels, with a reproducible build.** Current weights label retired roles: `routing_classifier_weights.npz` = {coder_escalation, worker_vision, architect_general, worker_math, architect_coding, ingest_long_context, frontdoor, worker_explore}; `_kl.npz` = {worker_vision, architect_general, coder_escalation, worker_general, ingest_long_context, frontdoor}. `architect_coding` stopped 2026-06-13, and 4 physical models now serve all roles, so one role label mixes model generations. The weights and `training_data.npz` are git-ignored (`.gitignore:95 *.npz`), so they cannot be rebuilt from git. The classifier feature is default OFF (`src/features.py:133`) and the LRC-2 verifier gate is inert (`src/api/services/routing_models.py:137`), so nothing live depends on them yet. Scope: label set keyed by model identity from the descriptor (not role); record the training recipe, data window, label map and sha256 of inputs in a tracked manifest so a retrain is reproducible; train once on EG2@256 (RTG-EG2-1), not on BGE. Acceptance: tracked manifest plus a script that rebuilds the weights from stated inputs; label map has no retired role. Needs the era/lineup window decision and the EG2 re-embed first; design and manifest are doable now.


## Track: routing-program
<!-- gate: none -->

> Folded from the body of `handoffs/active/routing-program.md` (row RTG-09), from its first `##` section on, @ `1befe3bc860d` on 2026-11-03 (BRF-T7-F16, route 1b, operator D1/D5). Headings demoted two levels; every box kept its text and ID.

#### Start here (2026-09-27)

- DAR-LAT is ❄ FROZEN, with a per-box unfreeze trigger; since 2026-09-29 (operator ruling, `typed-decision-plane.md` → *Operator rulings — 2026-09-29*, Q2) that trigger is "autopilot has trained on the swapped stack AND UFH-13 re-opened", replacing UFH-13's TE-6 verdict (UFH-13 PARKED 2026-09-28). DAR-LAT-3h is ✅.
- The first box to unfreeze when the trigger above fires is DAR-SPLIT-1, then the `stage`/`producer_role` split.
- Operator-owned: the ">=5% regret" ruling and the E9 routing-reward era signature.
- Standing, never flip: no production epsilon-greedy; do not close DAR-3/4/5 as signal-bound; any reward redesign carries the speed axis.
- Do not dispatch the DAR-3 SPO+ boxes.

#### Completed Scope

| Scope | Where |
|---|---|
| DAR-1, DAR-1 current-traffic replays, DAR-2, DAR-1.5 (phases + audit deliverable), the 2026-07-21 reward-saturation tables and root-cause evidence, the wall-clock speed-axis requirement (landed as E18), and the DAR-LAT-3h full box text | [completed sibling](../completed/decision-aware-routing-completed-through-2026-09-27.md) |
| April dependency graph, research-intake updates 2026-04-18 / 04-26 / 04-28 / 05-27, the superseded Status line and Start here (nothing dispatchable) | [archived history](../archived/decision-aware-routing-history-through-2026-09-27.md) |

#### Problem / Context

The difficulty signal shows **zero predictive spread**: escalation rates are flat at 62.2% / 60.7% / 62.2% across easy/medium/hard bands (Package B Phase 4, n=635, research-eval P0). The current Q-scorer cannot differentiate routing needs because the training objective is detached from the routing decision.

**Current architecture** (predict-then-optimize):

1. **Predict**: TD-learn Q-values per action via `update_q_value()` at `episodic_store.py` L439-511. Formula: `Q_new = Q_old + α * (reward - Q_old)`
2. **Optimize**: Argmax over Q-values via `_retrieve()` at `retriever.py` L225-368. Selection: `selection_score = Q_value - cost_lambda * (expected_cost / cold_cost)`

The TD update pushes Q-values toward observed rewards **independently per model**, with no mechanism to sharpen the decision boundary between models. A model consistently scoring Q=0.72 vs Q=0.68 is making the right decision, but the Q-value magnitudes are irrelevant — what matters is A > B.

**Decision-aware learning** aligns training with the routing DECISION, not prediction accuracy. The gradient is zero when the routing decision is already correct — it only provides learning signal when the prediction would lead to a wrong decision.

#### Key Insight: Trivial Tractability

The intractability concerns from intake-366 (differentiating through LP/MIP solvers in operations research) **do not apply** to our problem:

- **Action space**: N=3-5 models. This is trivially small — we can enumerate all actions at every training step.
- **Optimization**: Just `argmax` over N numbers — O(N), not NP-hard integer programming.
- **SPO+ loss**: Convex surrogate with closed-form gradients. No RL infrastructure needed.
- **Gumbel-softmax**: Perfect convergence at this scale (temperature annealing to 0 recovers exact argmax).
- **Compute**: CPU-only. SPO+ and contrastive losses are cheaper than current TD updates.

**This is one of the rare cases where the theoretically superior approach is also simpler to implement.**

#### Research Context

| Intake | Title | Key Contribution |
|--------|-------|-----------------|
| intake-366 | Deep Learning for Sequential Decision Making under Uncertainty | Survey: predict-then-optimize vs decision-aware vs learning-to-optimize paradigms. PredOpt expandable architecture. |
| Ch 08 | Cost-Aware Rewards (epyc-inference-research) | xRouter: 7B RL router with cost-aware reward. RouteLLM: preference-based matrix factorization. |
| — | xRouter (arxiv:2510.08439) | DAPO end-to-end RL, 20+ API models. Requires multi-GPU — not applicable to our CPU stack. |
| — | RouteLLM (arxiv:2406.18665) | Matrix factorization for binary strong/weak routing. Our N>2 setting needs generalization. |
| — | Router-R1 (arxiv:2506.09033) | GRPO multi-round routing with think+route. 8×A100 training — not applicable. |

**Key comparison**: xRouter and Router-R1 require multi-GPU RL training. But their conceptual contribution — aligning training with routing decisions — can be achieved without RL via decision-aware losses on our existing CPU Q-scorer.

#### Implementation Phases

DAR-1 (offline regret, ✅ 2026-04-15), the DAR-1 current-traffic replays (✅ 2026-06-12, 2026-07-03), DAR-2 contrastive (✅ 2026-04-15, live-ON via `CONTRASTIVE_Q_UPDATES`) and the DAR-1.5 REINFORCE-pathology audit (✅ 2026-05-07) moved to the [completed sibling](../completed/decision-aware-routing-completed-through-2026-09-27.md); see § *Completed Scope*.

##### DAR-3: SPO+ with Exploration (~100 lines, 3-4 sessions) — superseded by § RESCOPE (do not dispatch)

**Motivation note (intake-495 BaRP)**: BaRP frames this as the train/test mismatch fix — production logs only record the chosen specialist's outcome, not counterfactuals for un-routed models. DAR-3 SPO+ adopts the bandit-feedback *rationale* (don't require labels for un-chosen specialists) with a convex surrogate loss instead of REINFORCE. The 10% epsilon-greedy exploration step is what manufactures counterfactual data; SPO+ is what learns from it without REINFORCE's high-variance gradient.

- [x] ~~Implement SPO+ (Smart Predict-then-Optimize) loss:~~ (closed 2026-10-29 audit: SUPERSEDED → decision-aware-routing.md:64 "DAR-3 SPO+ with Exploration -- superseded by RESCOPE (do not dispatch)"; Start-here: "Do not dispatch the DAR-3 SPO+ boxes"; RESCOPE section replaced it with a triage gate; epsilon-greedy...)
  ```
  L_SPO+ = sum(max(0, 2*c_hat[j] - c_true[j])) - c_hat[i*] + c_true[i*]
  ```
  where `c_hat` = predicted costs, `c_true` = true costs, `i*` = true optimal model
- [x] ~~Add epsilon-greedy exploration to `_select_model()` at `retriever.py` L225-368 (10% random routing)~~ (closed 2026-10-29 audit: SUPERSEDED → decision-aware-routing.md:64 "DAR-3 SPO+ with Exploration -- superseded by RESCOPE (do not dispatch)"; Start-here: "Do not dispatch the DAR-3 SPO+ boxes"; RESCOPE section replaced it with a triage gate; epsilon-greedy...)
- [x] ~~Accumulate counterfactual data: for each prompt, observe outcomes from at least 2 different models~~ (closed 2026-10-29 audit: SUPERSEDED → decision-aware-routing.md:64 "DAR-3 SPO+ with Exploration -- superseded by RESCOPE (do not dispatch)"; Start-here: "Do not dispatch the DAR-3 SPO+ boxes"; RESCOPE section replaced it with a triage gate; epsilon-greedy...)
- [x] ~~Replace TD update with SPO+ gradient: only update when the routing decision would change~~ (closed 2026-10-29 audit: SUPERSEDED → decision-aware-routing.md:64 "DAR-3 SPO+ with Exploration -- superseded by RESCOPE (do not dispatch)"; Start-here: "Do not dispatch the DAR-3 SPO+ boxes"; RESCOPE section replaced it with a triage gate; epsilon-greedy...)
- [x] ~~Measure: routing accuracy, average task quality, average latency, Q-value convergence speed~~ (closed 2026-10-29 audit: SUPERSEDED → decision-aware-routing.md:64 "DAR-3 SPO+ with Exploration -- superseded by RESCOPE (do not dispatch)"; Start-here: "Do not dispatch the DAR-3 SPO+ boxes"; RESCOPE section replaced it with a triage gate; epsilon-greedy...)
- [x] ~~Connect exploration flag to existing `staged_scorer` exploration bonus mechanism~~ (closed 2026-10-29 audit: SUPERSEDED → decision-aware-routing.md:64 "DAR-3 SPO+ with Exploration -- superseded by RESCOPE (do not dispatch)"; Start-here: "Do not dispatch the DAR-3 SPO+ boxes"; RESCOPE section replaced it with a triage gate; epsilon-greedy...)

**Files**: `q_scorer.py`, `retriever.py` L225-368, `routing.py` L48-314

##### DAR-4: Model-Feature-Conditioned Q (~200 lines, 4-5 sessions)

- **[declined: ws58 2026-11-03 content-review: merged into the rescoped DAR-4 box (retrain on the fixed reward)]** Replace per-action Q-values with bilinear scorer:
  ```
  Q(prompt, model) = sigmoid(v_model^T W v_prompt + b)
  ```
- [x] Model features (already available in `ScoringConfig` L34-117): ✅ 2026-10-31 [no-belief: prior source and fixture controls only] [implementation: APP 6f288fe483c2d9c8467ff3088740f9ec2e1efc83 and 10b3bceb52e20514cf729e545f388d5de9f560bf; test: epyc-orchestrator/tests/unit/test_bilinear_scorer.py; historical closure hygiene, not quota]
  - `baseline_tps` (from `baseline_tps_by_role`)
  - `baseline_quality` (from `baseline_quality_by_role`)
  - `memory_cost` (from `memory_cost_by_role`)
  - `param_count_log` (derivable from model registry)
  - `is_moe` (binary flag)
  - `quant_bits` (from model registry)
  - The existing model feature vector and stack-prior extraction provide these six fields, with additional explicit speed/quality-known masks; eight current-source feature controls passed. Fallback model specifications remain degraded defaults, not measurements. This reconciles only the feature-vector item; the fixed-reward retraining and DAR-4 adoption remain open. [Evidence](../../artifacts/engineering/dar4-model-features-20261031/dar4-model-features-audit-20261031.log). [no-belief: source and fixture controls]
- [x] Create new `bilinear_scorer.py` module ✅ 2026-10-31 [no-belief: prior source and fixture controls only] [implementation: APP 6f288fe483c2d9c8467ff3088740f9ec2e1efc83; test: epyc-orchestrator/tests/unit/test_bilinear_scorer.py; historical closure hygiene, not quota]
- [x] Modify `retriever.py` selection logic to use bilinear scorer instead of per-action Q lookup ✅ 2026-11-01 — APP `58598acd1031a500c41eef9034d26c165eab0a4f`; artifact `../../artifacts/engineering/dar4-bilinear-selection-20261101/README.md`; R6 61 passed, receipt SHA-256 `75dd4668817b7e6c8c31764c36dc623bc84f5caeb540390bffb3f29b4a0a4237` [belief: cc]
- **[declined: ws58 2026-11-03 content-review: merged into the rescoped DAR-4 box as its acceptance test]** Test: add a simulated new model with known features, measure cold-start convergence vs current approach
- **[declined: ws58 2026-11-03 content-review: a claim, not a task]** Zero cold-start: when a new model joins the fleet, its features are known from specs — no routing history needed

**Files**: New `bilinear_scorer.py`, `retriever.py`, `q_scorer.py` (config), `episodic_store.py`

- DAR-1.5 verdict (2026-05-07; P4.2 resolved 2026-06-27): DAR-4 proceeds full-rank; sep-CMA-ES only for cold-start/no-label surfaces. Gate artifact: `/mnt/raid0/llm/epyc-orchestrator/orchestration/reports/p42_block_separability/report_20260627_sample80k.json`.
- Feature candidate withdrawn (2026-10-07 citation audit): no independent rationale is recorded in this handoff for adding `is_reasoning_model` to `ModelFeatures`; the cited record contains five claims about an episodic-memory benchmark and none about this descriptor (`intake-408#record`).

##### DAR-4b: Inference-Time Preference Vector + Cost Scaling τ (~50–100 lines, 1–2 sessions)

Source: intake-495 (BaRP) — preference-tunable inference. Modulates the trained DAR-4 bilinear scorer at inference WITHOUT retraining.

**2026-07-04 code checkpoint**: default-compatible request-level DAR-4b plumbing landed in `epyc-orchestrator` `fbd569b5`. This does **not** reopen DAR-3/DAR-6/Package-I expansion gates; it only adds an explicit request override and cost-scaling surface on the existing retrieval selector.

- [x] Add a 2-D preference vector `ω = (ω_perf, ω_cost)` on the simplex (`ω_perf + ω_cost = 1`) read from request metadata (default ω = (0.5, 0.5)).
- [x] Add calibrated cost scaling parameter τ as a runtime knob (env var `DAR_COST_TAU`, default 1.0; canonical env `ORCHESTRATOR_MEMRL_RETRIEVAL_COST_TAU` takes precedence). τ multiplies the normalized-cost penalty.
- [x] Inference-time score: `selection_score = 2 * (ω_perf * Q(prompt, model) - ω_cost * cost_lambda * τ * normalized_cost(model))`. The default `ω=(0.5,0.5), τ=1.0` preserves the existing `Q - cost_lambda * normalized_cost` selector exactly.
- [x] Per-task ω override wired through `ChatRequest.routing_preferences`, TaskIR canonicalization, chat routing, and `retrieve_for_routing()`. Per-tenant policy defaults remain future work only if a concrete tenant/workload policy is needed.
- [x] No retraining required. The deployed path applies only inference-time scalarization to the existing per-action Q-table selector; bilinear DAR-4 remains separately open.
- [ ] Measure: routing decision distribution shift across ω sweeps; latency-quality Pareto curve.
  - 2026-11-09 audit: UNDERSPECIFIED, doable now (replay only, zero inference). Snapshot: episodic-store rows after era E18 (2026-09-24T10:02:39Z) AND after the 07-23 lineup restoration, so reward uses the duration axis and actions are the current lineup; the pre-E18 store mixes reward eras (E9/E18), so do not mix. Sweep: omega_perf in {0,0.25,0.5,0.75,1} via `scripts/analysis/dar4b_sweep.py` (plumbing `fbd569b5`). Latency axis = the wall-clock duration term (0.20/0.05) priced with refreshed baselines (RTG-DUR-1); with the 09-24 baselines the axis is wrong for swapped roles. Output: decision-distribution shift per omega and the Pareto curve. First count qualifying rows; stop on futility if the post-E18 row count is too small to resolve a shift (n unknown until counted). Wire a `[belief:]` capture for the result.
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

##### DAR-5: IRT-Augmented Prompt Features + Learned Model-Identity Vectors (~150 lines, 3-5 sessions, conditional on DAR-4)

Source: intake-496 (LLM Bandit) — IRT (Item Response Theory) score predictor + d-dim model identity vectors trained jointly. Replaces hard-coded model-feature specs in the bilinear scorer with end-to-end learned embeddings.

- [x] **DAR-5.1**: Implement IRT prompt-difficulty scorer over BGE prompt embeddings. Output: per-prompt `(latent_difficulty, latent_discrimination)` 2-D embedding. Trained via maximum-likelihood on existing 174K routing memories with observed model outcomes as IRT responses. Calibrated via Platt scaling. ✅ 2026-07-22
- **[declined: ws58 2026-11-03 content-review: merged into the gated DAR-5 box]** **DAR-5.2**: Replace hard-coded `v_model = [baseline_tps, baseline_quality, memory_cost, param_count_log, is_moe, quant_bits]` in DAR-4 bilinear scorer with a learned d-dim model identity vector `v_model ∈ ℝ^d` (d=8 starting point), initialized from the hard-coded spec values, then trained jointly with the bilinear weights.
- **[declined: ws58 2026-11-03 content-review: merged into the gated DAR-5 box]** **DAR-5.3**: Augment `v_prompt` with the IRT 2-D output concatenated to the BGE embedding. New `v_prompt = [BGE_embedding | irt_difficulty | irt_discrimination]`.
- **[declined: ws58 2026-11-03 content-review: merged into the gated DAR-5 box as its decision gate (>= 2 points val acc)]** **DAR-5.4**: A/B against frozen-DAR-4 (hard-coded features) on val set. Decision gate: if IRT+identity-vectors improves routing accuracy by ≥ 2 points val acc, promote to default.
- [x] **DAR-5.5**: Future-onboarding note ✅ 2026-07-29 — initialize a new model's learned identity vector from its declared spec features only after DAR-4/DAR-5 are re-authorized on the fixed reward; this is an initialization, never an admission or routing-default decision. Refine it only through LRC P5.2's promotion-grade **observed-outcome** IRT run, not label-proxy scores; P5.2 currently rejects its cached label-proxy result and P5.3 remains conditional on P5.2's acceptance gate. The current DAR-5 prerequisite is the reward redesign (including the wall-clock axis), so no cold-start execution follows from this note.

**Files**: New `irt_scorer.py`, modify `bilinear_scorer.py` from DAR-4, `q_scorer.py` (config).

**Conditional on**: DAR-4 (bilinear scorer) shipping first. If DAR-4 hard-coded features prove sufficient (no measured benefit from learned features), DAR-5 closes as `not_pursued`.

##### Escalation Language (added 2026-04-28 from intake-495/496/474/493)

If DAR-3 / DAR-4 / DAR-4b / DAR-5 underdeliver on the zero-predictive-spread pathology:

1. **CPU-feasible escalation (Trinity, intake-474)**: sep-CMA-ES on the existing routing head (10K params, no gradient). Side-steps the credit-assignment / Q-magnitude problem entirely. CPU-feasible, no GPU budget required. See `learned-routing-controller.md` P4.4 (sep-CMA-ES cold-start spike) for the existing scoping.
2. **GPU-class escalation (Conductor, intake-493)**: 7B end-to-end RL coordinator. Requires 2× H100 80GB minimum. Out of CPU stack. Documented as competitive intelligence in `outer-coordinator-learned-head.md` OC-0.6.
3. **Bandit-as-such (BaRP, intake-495)**: REINFORCE on a fresh policy network, no Q-scorer at all. High-variance on small action spaces (≤5–8 specialists); LinUCB or Thompson sampling may match without policy-gradient instability. Unranked third option.

The realistic CPU-feasible escalation is option 1 (Trinity-style sep-CMA-ES). Options 2 and 3 are recorded for completeness, not roadmap commitments.

##### DAR-6: Swarm-Fanout Mode for High-Injection-Risk Prompts (intake-614/615, ~1–2 days + one eval run) — ❄ FROZEN (fable5-02)

**Source**: arxiv:2510.24801 (intake-615) — peer-ranked consensus across heterogeneous models reportedly shows 0.12% adversarial-degradation vs 6.20% for single-model baseline on prompt injection. If even a third of that delta survives independent replication on our suite, swarm-fanout is a routing **mode**, not just a research curiosity.

**What this adds to DAR**: a new routing mode that fans high-injection-risk prompts to **N≥2 concurrent serves** and returns a Bradley-Terry-aggregated winner instead of escalating to a single stronger model. This is **post-hoc full-completion** swarm voting (the published method) — distinct from the unpublished chunk-ranking claim (which is scoped separately in [`peer-verifier-speculation-spike.md`](../completed/peer-verifier-speculation-spike.md), resolved NO-GO and archived 2026-06-12).

**Gate before any code**:
- Replicate the 0.12% / 6.20% claim on our own injection suite. Candidate suites: [Garak](https://github.com/leondz/garak), [HouYi](https://github.com/LLMSecurity/HouYi), [PromptInject](https://github.com/agencyenterprise/PromptInject). Pick one with active maintenance + Apache/MIT license.
- Roofline check: per memory `feedback_no_concurrent_inference.md`, request user approval before any concurrent-model inference; per memory `feedback_same_model_roles_share_server.md`, 2-of-N concurrent serve of DIFFERENT GGUFs requires N independent processes, each with its own RAM share. The 30–40 t/s aggregate Fortytwo quotes for 4–8 CCUs implies a real per-stream throughput penalty; verify ours empirically before committing the routing mode to production.

**Implementation sketch** (~150–250 LOC):
> **Note 2026-09-16:** `dispatch_swarm_fanout` and `src/swarm_fanout.py` (with `SwarmCompletion`, `SwarmFanoutResult`, `bradley_terry_aggregate` and `length_proxy_aggregator`) **no longer exist**. They were deleted as dead code in orchestrator `771348c8` (2026-06-16, "delete dead DAR-6 swarm_fanout module", an ancestor of `main`). Only the default-off `swarm_fanout` FeatureSpec in `src/features.py` remains. The DAR-6.3/6.4 text below and the Default-off safety bullet are historical, and DAR-6.5/J14 would have to rebuild the dispatcher first.
- [x] **DAR-6.1 ✅ 2026-05-27** (epyc-orchestrator commit pending): Feature flag `swarm_fanout` added to `src/features.py` registry (`SWARM_FANOUT` env var; default-off in BOTH test and prod). `Features.swarm_fanout` boolean field. **Production routing is not affected** until a caller explicitly invokes `dispatch_swarm_fanout` AND the flag is on — two safety layers.
- **[declined: ws58 2026-11-03 content-review: merged into DAR-6.5 as its prerequisite; RI-13 says do not build it until the J14 A/B clears]** **DAR-6.2 (NOT YET BUILT — prereq for production gating)**: Trigger signal — extend the injection-risk classifier (or reuse the existing factual-risk classifier from [`routing-intelligence.md`](routing-program.md#track-routing-intelligence) if it carries an injection axis) to produce a 0–1 score; threshold tunable. For the cheap-first DAR-6.5 A/B variant ([J14](eval-tower-program.md#track-bulk-inference-campaign) in bulk-inference), this can be deferred — fan unconditionally on a fixed injection-prompt set first.
- [x] **DAR-6.3 ✅ 2026-05-27 — SUPERSEDED/REMOVED 2026-06-16 (code deleted by orchestrator `771348c8`; see the note below)**: `dispatch_swarm_fanout(request, targets, ...)` in **`src/swarm_fanout.py`** fans the request to N≥2 backends concurrently via `ThreadPoolExecutor`. Per-backend failures (exceptions OR `success=False` results) are caught and surfaced as `SwarmCompletion(success=False, error=...)` rather than crashing the dispatch. Returns a `SwarmFanoutResult` with all N completions, per-role wall-clock, and optional aggregation.
- [x] **DAR-6.4 ✅ 2026-05-27 — SUPERSEDED/REMOVED 2026-06-16 (aggregator deleted by orchestrator `771348c8`; `src/bradley_terry.py` itself survives)**: `bradley_terry_aggregate(pairwise_scorer)` builds an aggregator that calls **`src/bradley_terry.py`** (moved from scripts/autopilot/ on 2026-05-27 to keep it a single-source-of-truth for the three consumers — autopilot P17.BT-2, DAR-6.4 here, swarm-dataset-distillation Phase 3). The aggregator returns `(winner_completion, diagnostics)` carrying BT log_skills, warnings, Condorcet cycles, and dominance skew. Also included: `length_proxy_aggregator` as an explicit cheap-baseline (BT on length-difference sigmoid) — labeled in its docstring as "NOT a meaningful aggregation" so no future agent confuses it with a real peer-judged scorer.
  - **Removal note 2026-09-16 (sub-closure-fix):** DAR-6.3 and DAR-6.4 stay ticked because the work was really built (orchestrator `5f5fd8f6`, 2026-05-27). It was then deleted as dead code by `771348c8` (2026-06-16, "delete dead DAR-6 swarm_fanout module", an ancestor of orchestrator `origin/main` @ `88a2902d`). `src/swarm_fanout.py`, `dispatch_swarm_fanout`, `SwarmFanoutResult`, `SwarmCompletion`, `bradley_terry_aggregate` and `length_proxy_aggregator` exist on no ref at main. **Neither box is a live capability.** Evidence: `progress/2026-09/2026-09-16-sub-closure-audit.md` (top-10 #5).
- [ ] **DAR-6.5 (INFERENCE-GATED — J14 in bulk-inference)**: Decision gate — run a 2-arm A/B on the chosen injection suite (single-model escalation vs swarm-fanout). Gate: must show ≥3pp absolute reduction in injection-success rate AND ≤30% per-stream throughput regression (roofline). If both met → enforce; otherwise stay shadow-only. Absorbs DAR-6.2 and RI-13: the injection-risk trigger signal is built only if this A/B clears its gate, and then lands as an injection axis of the routing-intelligence track, not inside DAR.
  - 2026-11-09 audit: SV. Owned as J14 in `eval-tower-program.md` (~L1671). Needs a measured window on today's lineup (frontdoor 35B-A3B-MTP, architect_general Flash-Next); arms must be proven on the v10 kernel store (`kernels/production/{cpu,gpu}`) via `verify_ggml_linkage.sh`, not `llama.cpp/build/bin`.
  - **Dependency note 2026-09-16 (sub-closure-fix):** the DAR-6.3/6.4 dependency this gate names is **gone**. The dispatcher and aggregator were deleted in orchestrator `771348c8`, so DAR-6.5/J14 must first rebuild a fan-out dispatcher (it can reuse `src/bradley_terry.py`, which survives) or be re-scoped. The `swarm_fanout` FeatureSpec (`src/features.py:211,563`, `orchestration/runtime_flags.spec.yaml:117`) is still defined but **is read by no code path: the flag controls nothing**. Turning it on today would change no behaviour, so it cannot serve as the A/B arm.

**Cross-task interactions**:
- BT aggregation module **lives at `src/bradley_terry.py`** (moved from scripts/autopilot/ during DAR-6 scaffolding) and is shared with autopilot P17 (selection step) and [`swarm-dataset-distillation.md`](../completed/swarm-dataset-distillation.md) Phase 3 (training-data filtering). One implementation, three consumers.
- Concurrent-serve infrastructure dependency is [`dynamic-stack-concurrency.md`](numa-placement-and-contention.md#track-dynamic-stack-concurrency) — verify Phase B observability is sufficient to detect 2-of-N inference-thread contention before relying on this mode. (Phase B was already complete per dynamic-stack-concurrency.md status — no new dependency.)
- Injection-risk classifier may not exist yet; if not, that's a prerequisite task that should be raised in [`routing-intelligence.md`](routing-program.md#track-routing-intelligence) as a new RI-phase, not buried inside DAR-6.
- **Default-off safety**: `dispatch_swarm_fanout` requires no aggregator by default; if called without one, returns all N completions and the caller picks. This is deliberate — the most faithful Fortytwo-style aggregator (peer-judged pairwise) needs N*(N-1) extra inference calls and is exactly the cost the DAR-6.5 A/B is designed to measure. Picking a default would prejudge the experiment.

**Non-goals for DAR-6**:
- Mid-stream / chunk-level peer verification ([`peer-verifier-speculation-spike.md`](../completed/peer-verifier-speculation-spike.md) covers that; spike resolved NO-GO 2026-05-27, archived 2026-06-12 with 4 re-eval triggers).
- Replicating Fortytwo's reputation-staking / Sybil resistance (single-user single-host stack — out of scope).
- Multi-model fan-out for general (non-injection) prompts — that's a latency burn without a clear quality justification at our scale.

#### Cross-Cutting Concerns

##### 1. Q-Scorer Baselines
Q-scorer baselines (`baseline_tps_by_role`, `baseline_quality_by_role`) must be re-established after any DAR-2/3/4 change. Current baselines from 2026-03-21 sweep (see memory: project_qscorer_calibration.md).

##### 2. Difficulty Signal (research-eval P0)
The zero-predictive-spread pathology in `difficulty_signal.py` motivated this work. If contrastive Q-scoring (DAR-2) resolves the flat-band problem, the difficulty signal becomes useful as a routing feature again rather than being stuck in shadow mode.

##### 3. AP-27 RLVR Eval Tower
Decision-aware routing changes the reward signal that the eval tower must evaluate. The eval tower verification framework ([eval-tower-verification.md](eval-tower-program.md) EV-1–EV-7) must be able to assess whether the new routing reward is well-calibrated (ECE) and discriminative (AUC).

##### 4. Existing RL Routing Research (R&O intake-275)
The BaRP (arxiv:2510.07429) lightweight policy network and LLM Bandit (arxiv:2502.02743) from the 2026-04-07 research intake update are complementary approaches. DAR-2/3 operate on the existing Q-scorer; BaRP/Bandit would replace it entirely with a trained policy. If DAR-2/3 show insufficient gains, BaRP is the next escalation path.

#### Key Files

| File | Purpose | Lines of Interest |
|------|---------|-------------------|
| `epyc-orchestrator/orchestration/repl_memory/q_scorer.py` | Reward computation, Q-value updates | L318-430 (_compute_reward), L34-117 (ScoringConfig) |
| `epyc-orchestrator/orchestration/repl_memory/episodic_store.py` | Memory storage, Q-value TD update | L439-511 (update_q_value) |
| `epyc-orchestrator/orchestration/repl_memory/retriever.py` | Two-phase retrieval, selection score | L225-368 (_retrieve), L194-216 (confidence) |
| `epyc-orchestrator/src/api/routes/chat_pipeline/routing.py` | Full routing pipeline | L48-314 (_route_request) |
| `epyc-orchestrator/src/classifiers/difficulty_signal.py` | Difficulty classification (zero-spread diagnostic) | L201-236 (scoring + banding) |
| `epyc-orchestrator/tests/unit/test_q_scorer.py` | Q-scorer unit tests | — |

#### Known Issues

- The zero predictive spread diagnostic came from Package B Phase 4 with n=635. If the underlying issue is data sparsity rather than architectural, DAR-1 regret analysis will reveal this — regret would be near-zero because there are too few samples to establish reliable counterfactuals.
- DAR-3 exploration routing (10% random) will temporarily degrade routing quality during data collection. Must run in shadow mode or during low-priority tasks.
- DAR-4 bilinear scorer assumes model features are informative predictors of per-prompt quality. If all models perform similarly on most prompts (low variance), the feature-conditioned approach adds complexity without benefit.

#### Deep-Dive Task Proposals — 2026-05-25 (intake-607 Code-as-Agent-Harness §5.2.5)

DAR optimizes routing/escalation along a **quality** axis (learned Q-values + contrastive sharpening). The Code-as-Agent-Harness survey (§5.2.5) names a *different* axis worth adding: **decision uncertainty**, with the escalation decision recorded as first-class harness state for accountability. Audit pass tightened this into a calibration-first plan.

> **Schema + code anchors (gap-fix 2026-05-25):** the URE-2 approval/escalation record is part of the **shared trace schema owned by [`unified-trace-memory-service.md`](memory-program.md#track-unified-trace-memory-service) § "Shared Harness/Trace Schema"** (do not define a private store). Concrete code targets for URE-1/URE-3: Q-value source `orchestration/repl_memory/q_scorer.py`, retrieval/selection `orchestration/repl_memory/retriever.py`, routing feature `src/classifiers/difficulty_signal.py`; calibration gate from eval-tower P8. **Inference run consolidated as bulk-inference Package J / J10** (shadow-only).

- [ ] **URE-1 — Uncertainty-quantified escalation signal.** Add a calibrated decision-uncertainty estimate as an escalation trigger *orthogonal* to the quality Q-value. Candidate inputs: routing classifier confidence/entropy, top-2 margin, Q-value spread, conformal abstention score, MC-dropout variance if enabled, and disagreement between rule/router/Q-scorer. High-uncertainty decisions route up even when the point Q-estimate looks fine. Connects to the DAR-1 finding that Q-values were near-uniform (96%) — uncertainty may carry signal the flat Q-band does not. Required gate before enforcement: ECE ≤ target from eval-tower P8, abstention precision above baseline escalation precision, and no >10% latency regression in shadow mode. Follow-on (absorbs URE-3): only if the estimate is calibrated, feed it back as a routing feature and run the ablation showing it improves routing over the Q-value alone.
  - 2026-11-09 audit: UNDERSPECIFIED. Wired (`src/uncertainty_shadow.py`, `routing_decision.py:590`) behind `ure_uncertainty_shadow_log` (`src/features.py:263`), default OFF and never enabled, so no data exists. The ECE gate cites an unnamed 'eval-tower P8 target'. Decision needed: the numeric ECE bar. Options: (a) ECE below the raw-logit ECE on held-out suites (relative, no invented number); (b) a fixed absolute bar. Recommendation: (a), per the calibration-split bullet. Inputs 'classifier confidence/MC-dropout' are inert while `routing_classifier` is OFF (`src/features.py:133`); usable inputs today are Q-value spread, top-2 margin, and rule/router/Q-scorer disagreement. Enabling the shadow log is a zero-risk flag flip at relaunch.
  - *Calibration split (2026-09-23, intake-1502):* fit temperatures on held-out sources/suites, not same-suite halves, and
    flag or refuse any fitted T < 1.0 (sharpening) — Laya shipped T 0.1006 and was worse than raw logits on 29/49 suites;
    its held-out ECE is 0.204 vs 0.030 in-task.
  - *Candidate input, shadow-only (2026-09-23, intake-1521, intake-1525):* sampled-token mean/min log-prob of the local
    model's own answer — post-generation, spec-OFF only, placeholder tokens excluded as `token_confidence.py` does. Report
    AUROC + ECE against this gate before any threshold; the signal is strongly model-dependent.
- [ ] **URE-2 — Approval/escalation as harness state.** Persist each escalation/approval decision into the trace store, not just as a transient routing event. Minimum record: `request_id`, `task_signature`, selected role/model, alternatives considered, quality score, uncertainty score and components, trigger reason, approval boundary ("what this approval permits"), human/system actor if any, downstream outcome, and linked behavior signature. Wires into [`unified-trace-memory-service.md`](memory-program.md#track-unified-trace-memory-service) (see EXM-3).
  - [x] **URE-2-schema — approval record schema, insert and shadow ingest.** ✅ 2026-11-09 (verified by source: `src/trace/harness_schema.py:139` `ApprovalRecord` with `approval_boundary`, `:472` `insert_approval_record`, ingest at `src/uncertainty_shadow.py:127-141`) [no-belief: software presence verified by source inspection]
  - [ ] **URE-2-writer — live writer for non-shadow escalations plus the EXM-3 link.** 2026-11-09 audit: remaining part of URE-2: `v1_escalation` and the other live escalation sites do not call `insert_approval_record`; the linked behavior signature (EXM-3) is not set. Acceptance: one record per escalation on a stubbed `/chat` turn, a unit test, zero inference. Standalone code work.
- [ ] **URE-2a — Non-authoritative live cascade shadow.** After CJ-16 — now a LOCAL judge cascade (operator ruling Q1, 2026-09-29: local models only, no hosted Jev) — clears its frozen-fixture quality and operations gate, execute both the local first-stage choice and incumbent fallback on a frozen later-time traffic window, but continue returning the incumbent result. Persist the manifest and policy-baseline identities, per-item first-stage and fallback outputs, accepted/fallback attribution, threshold-selection split, confidence components, requested/resolved model identities, retries, typed failures, abstentions, queueing, disagreements, final outcome, end-to-end sequential p50/p95, and actual total cost from first-stage start through fallback completion. Retain every failure and abstention in the denominator and predeclare the stop/promotion rule under the [minimum viable research execution contract](eval-tower-program.md#minimum-viable-research-execution-contract). Keep this result separate from offline substitution curves. URE-1 calibration gates authority and promotion; it does not block measurement-only shadow execution. Source: intake-1606#record.
  - 2026-11-09 audit: SV, genuinely blocked on the named external event CJ-16 (local judge cascade clears its frozen-fixture gate). Not an Autopilot wait.
- **[declined: ws58 2026-11-03 content-review: merged into URE-1 as its conditional follow-on]** **URE-3 — Uncertainty as a routing feature.** If URE-1's estimate is calibrated, feed it back as a routing feature (revisits `difficulty_signal.py`, routing-index cross-cutting concern #12). Gated on URE-1 calibration quality and an ablation showing uncertainty improves routing or escalation decisions beyond existing difficulty/risk features. Start in shadow mode; do not let uncertainty recursively train itself without frozen labels.

**Audit refinements / missed gaps**:

1. **Calibration precedes enforcement.** An uncalibrated confidence score can be worse than no uncertainty signal because it creates false assurance. URE-1 must land in logging/shadow mode first and report ECE, AUC for "would escalation help?", abstention precision/recall, and per-suite calibration drift.
2. **Separate aleatoric from epistemic when possible.** Ambiguous prompts, missing context, and unfamiliar domains call for different interventions. Record component features so later work can distinguish "ask user/approve" from "route to stronger model."
3. **Approval is a bounded artifact.** URE-2 should store what was approved and what was not; e.g. "escalate to architect for plan review" is not the same as "apply code edits." This prevents approval state from becoming a vague global permission.
4. **Avoid feedback loops.** If uncertainty becomes a feature and also decides which examples get labels/escalations, the training distribution shifts. Keep a frozen shadow-calibration set and periodically re-run calibration after DAR-3/DAR-4 changes.

Additive to DAR-2/3/4 (which sharpen the *quality* Q), not a replacement — uncertainty is a second axis. Interacts with AP-27 (RLVR eval tower must score the uncertainty-augmented reward). Roll-up: [`routing-and-optimization-index.md`](routing-and-optimization-index.md) P24 § Additional task additions. Source: intake-607 `deep_dive` in `research/intake_index.yaml`.

#### Post-calibration conditional workflow + mitigation (URE-1 / bulk-inference J10)

Wiring status: shadow logger **WIRED** on main (merged 2026-05-26) (`src/uncertainty_shadow.py`, flag `ORCHESTRATOR_URE_UNCERTAINTY_SHADOW_LOG`, default off, hooked at the single chokepoint `hybrid_router._record_decision_meta`, exception-safe). J10 collects shadow records → `ingest_uncertainty_shadow()` → `approval_record` → analyze. **The shadow score is UNCALIBRATED first-pass; calibration precedes enforcement (audit #1).**

Decision tree (after J10 analysis):
- ✅ ECE ≤ eval-tower P8 target AND abstention precision > baseline escalation precision AND ≤10% shadow latency regression → enable uncertainty-routed escalation (a SEPARATE enforce flag, not the shadow flag) + optionally URE-3 (uncertainty as a routing feature, frozen labels).
- ❌ any gate fails → stay shadow-only; recalibrate (re-weight the logged components / adjust threshold) on a **frozen shadow-calibration set**; do NOT enforce.

Mitigation: shadow→enforce is a deliberate second flag flip (shadow logging alone never changes routing); keep a frozen calibration set; re-run calibration after any DAR-3/DAR-4 change (audit #4, avoid feedback loop); separate aleatoric vs epistemic components so "ask/approve" vs "route-to-stronger-model" interventions stay distinct. Operator decision tree mirrored in [`bulk-inference-campaign.md`](eval-tower-program.md#track-bulk-inference-campaign) Package J.

#### Research Intake Update — 2026-06-03

##### New Related Research
- **[intake-657] "Choosing Your Model — Factory CLI (Droid)"** (https://docs.factory.ai/cli/user-guides/choosing-your-model)
  - Relevance: a closed-source competitor's *human-readable routing policy*, useful here as a hand-tuned **cold-start prior** to A/B our learned escalation against. Factory exposes a task-type→model-tier decision table (deep planning/architecture → flagship; repeatable edits/summarization/boilerplate → cheap tier; CI/CD automation loops → cheapest-predictable; high-volume quick turns → cheapest-capable) plus a per-model reasoning-effort knob (Off/Low/Medium/High/Max) with the explicit rule "**start low, escalate as needed**."
  - Key technique: their "start-cheap-escalate-on-need" heuristic is exactly the escalation policy DAR is trying to *learn* — and our current pain point is that escalation rates are **flat across difficulty bands**. Their hand-tuned task→tier mapping is a sanity prior: difficulty/task-class should monotonically raise both the tier and the reasoning-effort default.
  - Delta from current approach: selection in Factory is manual *by default*. The harvest is narrow: (1) encode their task-type→tier table as explicit cold-start labels / a baseline policy for the shadow comparison; (2) wire the reasoning-effort taxonomy + "start-low" default into [`per-request-reasoning-budget.md`](context-and-token-economy.md#track-per-request-reasoning-budget). No new inference; pure policy-prior work. Verdict: adopt_patterns.

###### Deep-dive correction & high-value harvest (2026-06-03)
Full mining of `docs.factory.ai` (→ [`research/factory-ai-harvest-2026-06-03.md`](../../research/factory-ai-harvest-2026-06-03.md)) **corrects** the "no auto-routing" read above: **Factory Router** exists (opt-in Research Preview, `/web/factory-router.md`) — *"a per-task router that uses a mix of **session and per-request** routing"* that *"strongly considers **prompt cache** maintenance and savings,"* claiming **~20–25% cost reduction** vs always-top-tier at frontier-level perf. So we are *not* ahead on the existence of auto-routing, but it hands us a validated design + a concrete savings target. **Three router patterns to harvest here (Tier-1 backlog):**
  - [ ] **Prompt-cache-aware routing reward term** — add a `cache_affinity_bonus` (+ cold re-prefill penalty) favoring the physical server/slot already holding the conversation prefix in slot-KV (roles share one server per model since the 4-model lineup, so affinity is per server/slot, not per role; see `kv_slot_retention_policy.yaml`). This is a direct lever on **the flat-escalation-across-difficulty-bands open problem**: escalate only when `quality_gap` justifies the re-prefill cost. Pair with session stickiness (absorbs the next row): keep the role across turns unless the escalation threshold is crossed, so the cache-affinity term and stickiness together stop flapping and cache thrash; measure cold re-prefill tokens per conversation before/after.
    - 2026-11-09 audit: STALE-PREMISE, rewritten above. Plumbing exists but is dead: `cache_affinity_bonus` (`src/graph/state.py:209`, `src/api/models/responses.py:287`, `retrieval_config.py:55` `cache_affinity: float = 0.0`) is always 0.0 (the only non-test reader is `repl_executor.py:1131`, which copies it). Key the term by (model server, slot), not role. Any reward change is an era decision (human-only `instrument_eras.yaml`); land at weight 0 like DAR-4b. Gate on KVU slot-retention measurements existing.
  - **[declined: ws58 2026-11-03 content-review: merged into the cache-affinity row (one lever)]** **Session-sticky + per-request hybrid** — we decide per-request only; add a session-stickiness state to the outer coordinator (keep the role across turns unless escalation threshold crossed), combined with the cache-affinity term to stop flapping/cache-thrash.
  - [ ] **Reasoning-level as a first-class routing action** — make the action space `model × thinking-level` (not a fixed per-role thinking constant), operationalizing the phase-based spec/execution split.
    - 2026-11-09 audit: UNDERSPECIFIED. No `reasoning_level` action exists in the router; `reasoning_effort_certifications.yaml` carries per-role effort only. Missing facts: action space = 4 physical models (`orchestration/model_descriptors.yaml`) x certified effort levels; Qwen3.6+ requires `enable_thinking=false` via the chat-completions path; interacts with the per-request-reasoning handoff. Decision needed: build the action space on (model, effort) now vs after RTG-RETRAIN-1; recommend after, so the learned policy is not trained on role labels.

#### Deep-Dive Correction — 2026-07-21 (The DAR-1 gate metric is a tautology; root cause is the reward, not the policy)

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
  - 2026-11-09 audit: Decision package. This is the only operator-only item here; the 2026-07-21 RESCOPE already routes DAR-3/4/5 around it, so it gates only the P1.5.2/TR-4/TR-5/LRC freeze exits. Options: (a) retire the >=5% criterion as definitionally ~0 under selector self-consistency regret and unfreeze those items on their own merits; (b) define counterfactual regret (needs matched outcomes across models, which the store does not hold per the DAR-3 evidence). Recommendation: (a). Present through AskUserQuestion; do not edit the frozen gate.
  - *Decision-package input 2026-09-23 (intake-1527; annotation only — the gate is human-amendment-only):* if '>=5% regret'
    means oracle/counterfactual regret (fable5-02 L67), estimate it by cross-fitting on the store's repeated
    per-(objective, role) observations, report the single-draw noise gap G_noise, and compare 5% against the recoverable
    part only — single-draw oracle gaps can be ~the size of the threshold in noise alone (12-36% of the router-to-oracle
    gap on the paper's pools, likely underestimated).
  - *Provenance note 2026-09-23 (intake-1527 write-side check):* the '8.40 / 8.09 pp' figure above has no committed run
    artifact. The committed `dar_decisive_subset.json` @13112f77 reports a different estimand (14.73 / 14.64 pp vs
    uniform-random), and its snapshot directory no longer exists.
- [ ] **DAR-SPLIT-1 — Fix dar_decisive_subset.py selection leakage before any DAR-3 triage number is reused.** Select the decisive subset on fold A only and score on fold B; today gaps (L101-102) use all observations. Replace raw max-minus-min decisiveness (dar_common.py L170-175) with a binomial-null test. Re-state the ticked DAR-3 triage gate's number from the fixed script. Zero inference. Evidence: intake-1527.
  - 2026-11-09 audit: verified still unfixed. `scripts/analysis/dar_decisive_subset.py:95-103` computes gaps on all observations, no binomial null, last commit 13112f77 (07-22). Zero inference, standalone: the lead code item. The DAR-3 triage number stays leakage-inflated until it lands. Wire a `[belief:]` capture on the re-stated number.
- [x] Reward-saturation audit (zero inference, ~1 session): invert `q = 0.5 + r/2` on `update_count=0` rows, histogram reward by role and task_class. **Decision flip:** if per-decision reward entropy <1 bit AND role-conditional means differ <2pp, close DAR-3/4/5 as `not_pursued — signal-bound` rather than leaving them frozen behind a metric that can never fire. ✅ 2026-07-22
- [x] Write-path audit: is `update_count=0` on 99.69% of rows intentional (append-only replay buffer per the LRC design) or a dedup defect? Verify DAR-2 is live-*effective*, not just live-ON. ✅ 2026-07-22
- [x] Do NOT run DAR-3's 10% epsilon-greedy exploration to manufacture counterfactuals ✅ 2026-07-29 — epyc-root `bc4a7aa7` established that 386K already exist in the store for free; degrading production to collect what we already hold is strictly dominated.
- **[declined: ws58 2026-11-03 content-review: standing rule with no completion state (its own split note says so); stays readable here]** **STANDING — do NOT run DAR-3's 10% epsilon-greedy exploration in production to manufacture
  counterfactuals.** 386K already exist in the store for free (epyc-root `bc4a7aa7`); degrading
  production to collect what we already hold is strictly dominated.
  *(SPLIT 2026-08-12 by `mainC`. The ✅ recorded the DECISION, but the prohibition is live and
  load-bearing: the reward-saturation audit SPLIT and the close-as-signal-bound disposition
  explicitly DID NOT FIRE, so DAR-3 remains open work someone can pick up. A closed box left
  the one rule protecting production from that pickup invisible.)*
- [x] Raise the 200-char `objective` truncation before any counterfactual/competence analysis is run at promotion grade (runtime embedding path is NOT truncated, so live routing is unaffected). ✅ 2026-07-22

##### Reward-Saturation Audit — EXECUTED 2026-07-21 (zero inference; read-only SQLite over episodic.db)

Pre-registered disposition was: *"if per-decision reward entropy <1 bit AND role-conditional means differ <2pp, close DAR-3/4/5 as `not_pursued — signal-bound`."* **The audit SPLITS: condition 1 fires, condition 2 does not. The close-as-signal-bound disposition therefore DOES NOT FIRE.**

Result: reward entropy 0.6877 bits (saturated) but role spread 11.06pp; within-objective gap mean 11.61pp / median 0.00pp; 136/621 = 21.9% of objectives decisive (a floor). Tables in the [completed sibling](../completed/decision-aware-routing-completed-through-2026-09-27.md).

**Revised disposition (supersedes the pre-registered one):**
- [x] Reward-saturation audit executed — entropy 0.6877 bits (saturated) but role-conditional spread 11.06pp (separating). Split verdict; close-as-signal-bound does NOT fire. ✅ 2026-07-21
- [x] Do NOT close DAR-3/4/5 as `not_pursued — signal-bound`. The correct reframing is **triage, not policy**: the target is a *gate* that identifies the ~22% of objectives where role choice is outcome-relevant, not a better global argmax. Re-scope DAR-3/4/5 accordingly before considering any unfreeze. ✅ 2026-07-29 — already executed in the same handoff's **DAR-3 / DAR-4 / DAR-5 RESCOPE** section: DAR-3 is the decisive-subset triage gate with no epsilon-greedy collection, DAR-4 is retained only for fixed-reward retraining, and DAR-5 is gated on the wall-clock reward redesign.  *(Restored to `- [ ]` 2026-08-11 by `mainC` — standing constraint with no completion state; the dated evidence below is kept, the rule is live again.)* ✅ 2026-10-29 (audit: box text itself carries "done 2026-07-29 -- already executed in DAR-3/4/5 RESCOPE section" (RESCOPE at ~line 366: DAR-3 triage gate, DAR-4 retained, DAR-5 gated)) [no-belief: audit-reconciliation]
- [x] Highest-value next measurement (zero inference): restrict the existing DAR-2 contrastive objective — and any future policy eval — to the matched decisive subset, and report lift THERE rather than over all traffic. A policy that improves the 22% while leaving the 78% untouched is invisible in every metric used so far. ✅ 2026-07-22
- **[declined: ws58 2026-11-03 content-review: merged into the reward-redesign precondition that gates DAR-5]** Reconsider the reward itself before the policy: at 89.05% at exactly +1.0 with a −0.4 penalty tail, this is a success/failure flag wearing a continuous type. Graded reward on the decisive subset is likely worth more than any loss-function change.
- NOTE the confound that still stands: role assignment is not randomised, so marginal per-role means conflate role quality with the conditions under which each role is selected. The matched within-objective figures control for task identity but NOT for selection-within-task. Everything above is an OBSERVATION under MEASUREMENT.md; none of it is protocol-attested and none of it gates a promotion.

###### Operator qualification (2026-07-21) — the 78% figure is quality-only, and the corpus is tier-skewed

Two corrections to the audit reading above, from the operator:

1. **"Roles score identically" is a QUALITY statement, not a routing-indifference statement.** Autopilot optimizes task execution **speed × quality**. On the ~78% of objectives where every role reaches the same outcome, the correct action is still not arbitrary — it is *route to the cheapest/fastest role that clears quality*. So that majority is not "the decision does not matter"; it is "the decision is dominated by the cost term" — which is exactly what DAR-1 observed empirically (cost and similarity terms drive selection; Q-values are decorative). The two findings agree, and the reward as currently constructed simply **cannot express the speed half of the objective at all** — it collapses to a success flag. That is a second, independent argument for fixing the reward before the loss function.
2. **The measured corpus is tier-skewed toward T0/T1.** The 661,717 memories are dominated by autopilot eval traffic, which is mostly T0/T1 tasks. Easy tasks are exactly where models converge, so a 90.3% blanket success rate and a median 0.00pp role gap are partly an artifact of task difficulty, not evidence that roles are interchangeable in general. **T3 would plausibly show materially more quality divergence across roles/models** — and T3 is where routing errors are most expensive. This means the ~22% decisive-objective estimate is likely a FLOOR, and the audit understates the achievable headroom.

Combined implication: the triage-gate framing survives, but its target sharpens. The gate should separate (a) the cost-dominated majority, where the objective is cheapest-role-that-clears-quality, from (b) the quality-decisive minority, which is under-represented in the current corpus and concentrated at higher tiers.

- [x] Re-run the matched within-objective analysis **stratified by task tier (T0/T1/T2/T3)** before drawing any conclusion about how much of the corpus is genuinely role-indifferent. Current estimate (21.9% decisive) is derived from a T0/T1-dominated sample and is probably a floor. Zero inference — the tier label needs to be recoverable from the stored context/objective or joined from the eval-tower record. ✅ 2026-07-22
- [x] Any redesigned reward MUST carry the speed axis, not just the outcome flag — autopilot's objective is speed × quality and the current `reward` collapses to success/failure. This is a prerequisite for the majority regime, where cost is the operative term. ✅ 2026-10-29 (audit: wall-clock speed axis landed as era E18-routing-reward-duration-axis ratified 2026-09-24 (orch b8035db9, 88e24ef0, 60bfc4c4; instrument_eras.yaml:452; header line 3 states it)) [no-belief: audit-reconciliation]

#### ROOT CAUSE FOUND — 2026-07-21: the cost/speed half of the reward was dead due to a key-name mismatch

compute_reward read role, telemetry wrote producer_role, so every cost dimension was skipped (0/20,521 rows carried role). The fix reads role → producer_role → final_answer_role; replay 0.0000 → 2.4580 bits. Evidence in the [completed sibling](../completed/decision-aware-routing-completed-through-2026-09-27.md).

##### Retroactive rescoring is possible

- **94.5%** of `task_completed` entries carry usable speed telemetry (`tokens_generated` 99.8%, `generation_ms` 99.8%, `prompt_eval_ms` 99.8%, `http_overhead_ms` 99.8%).
- **20,516 `task_started`/`task_completed` pairs** carry timestamps, so **true wall-clock task duration is recoverable** — 85 days of progress logs are retained.
- Rescoring is therefore a replay over `logs/progress/*.jsonl`, not a re-run. It creates an instrument-era boundary: pre-fix stored `q_value`s and post-fix rewards are **not comparable**, and the era must be recorded before any mixed-era comparison is made.

- [x] Root-caused the reward saturation to a `role` vs `producer_role` key mismatch; fixed with regression tests; replayed on 20,526 historical completions (0.0000 → 2.4580 bits). ✅ 2026-07-21
- [x] Add a **wall-clock task-duration** term as the speed axis, derived from `task_started`→`task_completed`, and demote the tokens/sec term to a secondary signal. Per-role p50/p90 baselines above are computable from the retained logs — derive them under a protocol id rather than hand-setting constants.
  - [x] **Implemented, landed DEFAULT-OFF** ✅ 2026-09-24 — orch `b8035db9` + `88e24ef0`. Baselines: `scripts/analysis/derive_duration_baselines.py` → `orchestration/derived/duration_baselines_by_role.json` (protocol id `RTG09-DURATION-BASELINE-v1`, an analysis id not a MEASUREMENT.md protocol; 137,256 pairs, 117 logs 2026-02-27..09-23, min n 30/role — e.g. frontdoor p50 27.6s/p90 116.1s, worker_general 16.2/55.1, coder_escalation 9.1/75.4; toolrunner and worker_explore under n=30). `compute_reward` Dimension 0: 0 at the role's p50 → full `cost_lambda_duration` at p90, saturating; a missing duration or a role with no baseline skips only that dimension and warns once. `task_duration_s` wired at all 3 call sites (`QScorer._score_task`, replay engine, `rescore_rewards_from_progress.py`). Lands with `cost_lambda_duration=0.0`, `cost_penalty_lambda=0.15`: the live reward is byte-identical (tested), because a reward-distribution change is a `routing_reward` era boundary (cf. E9) and rewards feed Q-updates continuously. 120 tests pass.
  - [x] **Operator: apply the RTG-09 ratification** — `bash scripts/operator/ratify_rtg09_duration_reward_20260924.sh --show`, then `--apply`: flips 0.20 / 0.05 and appends era `E18-routing-reward-duration-axis` in one orchestrator commit, then reload the API. Ticking this ticks the parent box and unblocks DAR-5. ✅ 2026-09-24 (operator: "apply OP-47") — orch `60bfc4c4` RATIFIED: era `E18-routing-reward-duration-axis` from 2026-09-24T10:02:39Z; defaults 0.20 / 0.05. The script's post-flip test gate refused the first apply because 8 tests encoded the default-off contract; they moved with the flip in the same commit (121 pass). A `set -e`+`pipefail` bug in the script (zero-match `grep | wc -l`) was fixed first (root `c9450f9f`). API reloaded 10:13:35Z; live `ScoringConfig()` = 0.2 / 0.05 with 10 role baselines. DAR-5 is unblocked.
- [x] Record the instrument-era boundary for reward values before any pre/post-fix comparison is made or any policy is trained across it. ✅ 2026-10-29 (audit: era boundary recorded: orchestration/instrument_eras.yaml:372 E9-routing-reward (from 2026-07-21T15:27:04Z) and :452 E18-routing-reward-duration-axis) [no-belief: audit-reconciliation]
  - [x] **Pre-validated human-amendment token authored ✅ 2026-07-29**: `RATIFY-E9-ROUTING-REWARD-ERA-20260729` is in `outbox/mainB.jsonl` with an append-only, SHA-pinned command and copy-only YAML validation (`dry_run_exit=0`). Await operator signature; agents did not edit `orchestration/instrument_eras.yaml`.
- **[declined: ws58 2026-11-03 content-review: optional by its own text ("not indispensable"); logs are the source of truth]** Optional: replay-rescore historical rows so the episodic store carries post-fix rewards. Not indispensable (the logs are the source of truth and can be replayed on demand), but it would make the 174K-row store trainable without a join.

#### DAR-3 / DAR-4 / DAR-5 RESCOPE — approved 2026-07-21

Superseding the "FROZEN pending a ≥5% regret replay" status. That gate was measured by a metric that cannot return non-zero (see the tautology finding above), so it was never a real gate.

**They are not unfrozen, and they are not closed. They are re-aimed.** The three phases were designed to improve a *global argmax* over a target that carried zero bits. Both premises are now known false: the target was broken (fixed above), and the majority regime is not quality-discriminative (median within-objective role gap 0.00pp; only 21.9% of objectives decisive, and that is a floor given the T0/T1-skewed corpus).

New shape:

- [x] **DAR-3 (was SPO+/epsilon-greedy) → triage gate.** Build a classifier that separates *cost-dominated* objectives (any role clears quality; choose cheapest/fastest) from *quality-decisive* objectives (role choice changes the outcome). Report lift on the decisive subset, never on all traffic — a policy that fixes the 22% and leaves the 78% alone is invisible in every metric used to date. **Do NOT run the original 10% epsilon-greedy exploration**: 386K counterfactual decisions already exist in the store for free, so degrading production to manufacture them is strictly dominated. ✅ 2026-07-22
- [ ] **DAR-4 (bilinear descriptor-conditioned predictor) → retained, but retrain on the fixed reward.** Its prior null (P4.1.3: label-proxy IRT +9.02pp, observed-outcome IRT 0.00pp) is now explained — the observed outcome was constant. Re-run before drawing any conclusion about the model class. Scope (absorbs the DAR-4 phase rows): replace per-action Q with the bilinear `Q(prompt, model) = sigmoid(v_model^T W v_prompt + b)`; acceptance: a simulated new model with known features converges faster than the current cold start, and the retrained predictor beats the constant-outcome null on the fixed reward.
  - 2026-11-09 audit: STALE-PREMISE + UNDERSPECIFIED. Missing facts: era = post-E18 and post-07-23 lineup; action set keyed by physical model (4 models), not role; `scripts/graph_router/bilinear_scorer.py` today uses 8 heuristic features whereas this box says BGE `v_prompt`: state which feature set is being trained; E18 baselines are stale until RTG-DUR-1 lands. Do not train before the EG2 decision (see the EG2 note below).
  - 2026-11-09 EG2 boundary (RTG-EG2-1): v_prompt is BGE-1024; at v11 it is EG2@256, so the predictor is trained on (or re-projected to) EG2 vectors only. Regenerate: the bilinear weights W/b and the training table. State the era (post-E18, post-07-23 lineup) and a model-keyed action set (4 physical models, `orchestration/model_descriptors.yaml`) instead of role labels. Decision needed: train on BGE now and retrain at v11 (recommend NO: spend the run once, on EG2) vs wait for the re-embed.
- [ ] **DAR-5 → gated behind the reward redesign, not behind a regret replay.** Precondition is a reward carrying a wall-clock speed axis (above), since the cost-dominated majority is where most traffic lives and the current reward cannot price it. Scope once the reward carries the wall-clock axis (absorbs DAR-5.2/5.3/5.4 and the graded-reward note): learned d=8 model-identity vector initialized from the spec values; v_prompt = [BGE | irt_difficulty | irt_discrimination]; a graded reward on the decisive subset instead of the 89% +1.0 flag; A/B vs frozen DAR-4 on the val set, promote only at >= 2 points val accuracy.
  - 2026-11-09 audit: STALE-PREMISE. The 'spec values' initialisation names models gone from the lineup; the E18 precondition is satisfied (ratified 2026-09-24, orch `60bfc4c4`) but the duration baselines it relies on are the 09-24 old-stack ones (RTG-DUR-1). Re-scope the initialisation to the four descriptor records.
  - 2026-11-09 EG2 boundary (RTG-EG2-1): v_prompt = [BGE | irt_difficulty | irt_discrimination] changes dimension at v11 (256 + 2). Regenerate: the IRT projector (REPL-EMB-R1) and the identity-vector/bilinear weights. The `spec values` initialisation names models no longer in the lineup; re-seed from the four descriptor records (see RTG-VAR-2 note).
- [x] Re-run the matched within-objective analysis **stratified by task tier (T0/T1/T2/T3)** before sizing any of this. 21.9% is derived from a T0/T1-dominated sample and is expected to rise at T3, where routing errors are most expensive. ✅ 2026-07-22

##### Reward-integrity follow-up — 2026-07-21 (role-field validation)

The rescore surfaced a second defect of the same shape as the `role`/`producer_role` miss. `ChatRequest.role` and `.force_role` were unvalidated `str` fields, and `stream_adapter.py:178` feeds `request.role` straight into telemetry as `producer_role`. Because `compute_reward` uses that value as a `baseline_tps_by_role` key, **an unresolvable role skips every cost dimension and scores the full base reward** — so unvalidated client input could suppress the entire cost/speed penalty. That is a latent reward-hacking surface, not just a hygiene issue, and it matters more now that the cost path actually fires.

- [x] Validated `role`/`force_role` at the API boundary via the existing `Role.from_string` (rejects free text, case-normalizes, passes pipeline sentinels); added a warn-once at the reward site for any role with no `baseline_tps_by_role` entry, so the miss can never be silent again. `epyc-orchestrator 6344fbdb`, 16 tests. ✅ 2026-07-21
- [x] Blast-radius verified by call-site analysis (gitnexus segfaulted): every production `force_role` value survives, including legacy aliases `reviewer`/`reviewer_agent`/`architect_coding`. One documented behaviour change — `memrl.should_skip_background_scoring` is `bool(force_role) and bool(real_mode)`, so an invalid `force_role` rewritten to `""` no longer suppresses background scoring; pinned by test in both directions. ✅ 2026-07-21
- [x] Confirmed `architect_coding` is genuinely deprecated (rows stop 2026-06-13), so its post-fix `+1.0000` is historical replay, not a live scoring gap; allow-listed alongside `mock`/`plan_review` to keep rescores quiet. ✅ 2026-07-21
- [x] Consider splitting a separate `stage` field out of `producer_role`: the same field currently carries real roles AND pipeline sentinels (`plan`, `stream_init`, `proactive_delegation`, `mock`). Harmless today, but overloading the key that prices the reward is how this class of bug recurs. ✅ 2026-11-01 — APP source `3011c9e9271ecebd50892b818530f21de0e22c75`, published on main in `da163c70cc347337f7d76d3ce5acc14fafc75411`; hosted CI run [41283762176](https://github.com/pestopoppa/epyc-orchestrator/actions/runs/41283762176) passed 399/399 (0 failures, errors, skips); original custody: [artifact](../../artifacts/engineering/decision-aware-routing-producer-stage-20261101/README.md). [no-belief: software verification]

#### Research Intake Update — 2026-09-07

**Risk note — orchestration features carry a capability floor** (`intake-1333#01`, dive-verified).
Richer orchestration **REGRESSED** quality on all three smaller models, concentrated in
orchestration-heavy capabilities (Qwen 3.6 MCP .65 → .50), and sub-agent delegation scored 0.42–0.45
on the fast tier. Directional and vendor-internal, so it **cannot gate a decision** — but it suggests
routing on **feature demand** rather than prompt difficulty. Zero compute.

#### Research Intake Update — 2026-09-26 (orchestration prior art: static latency prior + saturation guard; intake-1796/1797/1798/1815)

Selection has no latency or load term today. The only cost is historical elapsed from memory
(orch @fb7871ea `retriever.py:46-57`, fed by :113-142), and `baseline_tps_by_role` is reward-side only
(`q_reward.py:223`). The dive puts the gain on a latency term and found a static per-tier prior as good as a
learned live estimate (intake-1796#02). The regime left open is ours: single-instance, TTFT-bound, preferred tier
saturated (intake-1798#05; intake-1797#04). The terms land at weight 0 like DAR-4b: they do not reopen the
DAR-3/DAR-6 expansion gates, and nothing changes live routing until DAR-LAT-3 decides.

##### DAR-LAT — ❄ FROZEN 2026-09-27 (do not dispatch; each box carries its unfreeze trigger — since 2026-09-29: autopilot has trained on the swapped stack AND UFH-13 re-opened)

- [ ] ❄ FROZEN 2026-09-27 — resume only once autopilot has trained on the swapped stack AND UFH-13 re-opened (operator ruling 2026-09-29) — **DAR-LAT-1 — Build the shared `SlotCapacity` snapshot and `expected_wait_s(role)` on the ONE admission ledger.**
  - 2026-11-09 audit: Anchors fixed inline above (`admission.py` -> `get_status`). Zero-inference code is feasible, but the box is frozen by operator ruling; trigger needs Autopilot, which is on HOLD. HOLD list.
  Role-keyed over the role's backend URLs:
  - `queued` = `AdmissionController` waiting_*, `running` = in_flight, `limit` = np (orch `src/api/admission.py`, `AdmissionController.get_status`; was :229-245; `SlotCapacity` exists only in `src/embedding_pool/busy.py`).
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
  - 2026-11-09 audit: `_apply_priors` is `orchestration/repl_memory/hybrid_router.py:332` (fixed inline). Depends on DAR-LAT-1. HOLD list.
  (`orchestration/repl_memory/hybrid_router.py:332` (`_apply_priors`; was :308-327)), landed at λ_lat=0 (byte-identical, test-pinned).**
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
  - 2026-11-09 audit: Premise matches live topology (Flash-Next :8074 -np 1, divert to :8083 per `stack_topology.yaml`; note :8083 is now the 27B). Needs a whole-host window. HOLD list.
  Qwen3.8-Flash-Next (`architect_general` :8074 since ARCHSWAP-20260927, `-np 1`) with divert target `architect_critic` (:8083, MI210).** Absorbs DAR-LAT-3a (pre-registration freeze), 3g (acquire-never-observe gate: bus-granted whole-host window, MEAS-6), 3b (W1 calibration + arm sweep + 24 A1/A1 floor pairs) and 3c (holdout W2 >= 24 h later, rho = 1.25, ABBA, fresh seeds; W1 and W2 never pooled; PAIRED-CI-1 within a window) — the sub-rows below stay as its protocol record.
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
  - **[declined: ws58 2026-11-03 content-review: merged into DAR-LAT-3 as its protocol step]** ❄ FROZEN 2026-09-27 — resume only once autopilot has trained on the swapped stack AND UFH-13 re-opened (operator ruling 2026-09-29) — **DAR-LAT-3a — Freeze the pre-registration.**
    - Manifest: seeded MMLU-Pro/GPQA items (the frozen-v10 sets, amd-ai-lab-website-publication.md:18), `max_tokens`
      cap, candidate pair, dry-route-explain filter (architect_general chosen under A0 and A1 at zero load), frozen
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
  - **[declined: ws58 2026-11-03 content-review: merged into DAR-LAT-3 as its gate step]** ❄ FROZEN 2026-09-27 — resume only once autopilot has trained on the swapped stack AND UFH-13 re-opened (operator ruling 2026-09-29) — **DAR-LAT-3g — GATE (acquire, never observe):**
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
  - [ ] ❄ FROZEN 2026-09-27 — resume only once autopilot has trained on the swapped stack AND UFH-13 re-opened (operator ruling 2026-09-29), or the operator reopens it — **DAR-LAT-3i — Decide `GGML_FA_SPLIT_KV=0` for the `:8074` Flash-Next server (`architect_general` since ARCHSWAP-20260927) at its served context.** The operator split it
    - 2026-11-09 audit: SV. Kernel decision on the v10 production server: no action without explicit operator authorisation (production kernels are frozen). HOLD list.
    out of the DAR-LAT-3h package on 2026-09-26, after the GGML_* env audit. It is recorded under master registry
    `server_mode.architect_general.recipe.env_not_serving` (the Flash-Next row; renamed by ARCHSWAP-20260927).
    - Why it is separate:
      - It changes numerics (BE-2: a row-exact reduction order for 1-row decode vs n-row MTP verify).
      - It is a perf risk at long context: single-row decode loses KV-axis parallelism.
      - The :8074 server serves `n_ctx` 262144, and DAR-LAT-3h's G1 exercises only up to ~4k-token prompts.
    - Does not block 3g: the DAR-LAT-3h package does not set the knob.
    - Needs, all on production v10 at the served argv, as launch-unit arms (`FA_SPLIT_KV` unset vs `=0`) under a
      region claim in a quiet window:
      1. A long-context decode arm: tok/s at KV depths up to the served context (at least 64k and 128k, plus the
         deepest the host fits), and TTFT.
      2. A numerics check: greedy output agreement, first-divergence position, and MTP acceptance α.
      3. Per-suite quality non-inferiority on the DAR-LAT-3a item sets.
    - Adopt only if the knob is non-inferior on speed at every depth and on quality. The change ships as its own
      `stack-change` package, which adds it to the :8074 server's (`architect_general`) `stack_env` block.
    ❄ FROZEN 2026-09-27 (operator, narrowed plan): a numerics-and-long-context knob for the :8074 seat (the critic seat before ARCHSWAP-20260927); no thesis arm depends on it; unfreeze trigger (operator ruling Q2, 2026-09-29; it replaces "the UFH-13 verdict makes the critic seat's served shape decision-relevant"): autopilot has trained on the swapped stack AND UFH-13 re-opened, or the operator reopens it. The box stays open: frozen is not done.
  - **[declined: ws58 2026-11-03 content-review: merged into DAR-LAT-3 as its W1 step]** ❄ FROZEN 2026-09-27 — resume only once autopilot has trained on the swapped stack AND UFH-13 re-opened (operator ruling 2026-09-29) — **DAR-LAT-3b — Run W1** (calibration, then the arm sweep plus the 24 A1/A1 floor pairs). Stop on any
    prerequisite that fails during a block; re-queue the block, never drop it. Per-request receipts + raw outputs.
    ❄ FROZEN 2026-09-27 (operator, narrowed plan): DAR-LAT is frozen once DAR-LAT-3h's G1 is recorded; the load-sweep programme is not on the thesis path; unfreeze trigger: DAR-LAT-3h's G1 is recorded (the only DAR-LAT work that proceeds) AND (operator ruling Q2, 2026-09-29, replacing "the UFH-13 thesis experiment shows that selection under load matters", which cannot fire while UFH-13 is PARKED) autopilot has trained on the swapped stack AND UFH-13 re-opened. The box stays open: frozen is not done.
  - **[declined: ws58 2026-11-03 content-review: merged into DAR-LAT-3 as its W2/verdict step]** ❄ FROZEN 2026-09-27 — resume only once autopilot has trained on the swapped stack AND UFH-13 re-opened (operator ruling 2026-09-29) — **DAR-LAT-3c — Holdout W2 (≥24 h later, ρ=1.25, ABBA, fresh seeds) + verdict.** PAIRED-CI-1 within a window
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
- Prior blend: `orchestration/repl_memory/hybrid_router.py:332` (`_apply_priors`; was :308-327).
- Initial route: `routing_decision.py:259-314`.

- [x] **DAR-CITATION-SOURCE-REPAIR — resolve two dangling claim anchors against actual native intake records.** ✅ 2026-10-07 — MAIN reviews the actual five-claim intake-408#record and withdraws the unsupported reasoning-feature annotation; intake-1333#01 precisely supports the existing source-reported capability risk, with no live/performance or new policy gate. This corrected anchor remains UNKNOWN in the current belief ledger; original failed check and source evidence are retained. No intake/source claim, ledger or grading rule is rewritten.

## Track: internal-interaction-lifecycle
<!-- gate: none -->

> Folded from `handoffs/active/internal-interaction-lifecycle.md` @ `b33c4e7a5fd1` on 2026-11-02 (BRF-T1-F26, route 1a, operator D1/D5; retired row RTG-14 → RTG-09). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Internal Interaction Lifecycle

**Status**: P1 lifecycle substrate landed 2026-06-28 in `epyc-orchestrator` `18956892`; P2 edit-transaction consult wiring is staged default-off as of 2026-07-05 (`0e555822`); the P1 bake gate cleared 2026-07-07, P2/J17 live evidence says **targeted-positive**, the T3 consult-gate canary produced a frontier row, and the generalized default-off `should_consult()` policy is implemented pending broader shadow/enablement evidence.
**Priority**: P0 for substrate cleanup; downstream of intake-655 deep-dive
**Created**: 2026-05-31
**Owning index**: [`routing-and-optimization-index.md`](routing-and-optimization-index.md)
**Related**: [`delegation-context-preassembly.md`](context-and-token-economy.md#track-delegation-context-preassembly), [`routing-intelligence.md`](routing-program.md#track-routing-intelligence), [`hermes-outer-shell.md`](../completed/hermes-outer-shell.md), intake-655
**Provenance**: 2026-05-31 deep-dive on intake-655 (A2A protocol). Two-question framing: adopt A2A *lifecycle semantics* internally; defer A2A *wire transport*.

#### Objective

Replace the implicit delegation loop shape in `epyc-orchestrator` with an explicit `Interaction` lifecycle abstraction modeled after A2A's task semantics. Use the same substrate for `delegate` and a new `consult` kind. Skill contracts described in a sibling YAML, keyed by role × skill, with typed advisory output schemas. Reuse every existing optimization machinery (region locks, contention gating, shared-backend aliasing, DCP context packaging, `delegation_cache`, MemRL telemetry) underneath.

#### Non-Goals

- No internal A2A wire transport. No per-role A2A servers.
- No opaque-agent boundary inside the orchestrator. Region-lock / contention visibility preserved.
- No streaming consult in v1. Current `/chat/stream` wraps pipeline events, not backend tokens (`stream_adapter` calls `primitives.llm_call()` then emits events) — true concurrent integration requires backend streaming callbacks first.
- No multi-turn `input_required` consult in v1. Would require a local `ConsultationTask` store with terminal/interrupted states.
- No behavior change in P1.

#### Current Execution Gate (2026-05-31)

Sequencing is locked:

1. **Done**: P2-0 discovery — complete, no runtime change.
2. **Done**: P1 lifecycle refactor — landed as a no-behavior-change substrate in `epyc-orchestrator` `18956892`.
3. **After P1 regression gate**: P2 one-shot consult at the P2-0 chosen attach point.
4. **After A/B evidence**: P3 consult gating, then P4 reward/eval.

P1 was completed as an additive/no-behavior-change substrate without changing the contention gate or live inference admission path. P2 remains locked until the P1 regression bake and cross-role contention/autopilot bake are clean. P2-0 was safe because it was documentation/discovery only; P2 touches the consult/delegation substrate and would otherwise contaminate live attribution.

#### Core Model

New module `src/orchestration/interaction.py`:

```python
@dataclass
class Interaction:
    kind: Literal["delegate", "consult", "verify", "route"]
    owner_role: str
    callee_role: str
    skill: str
    state: Literal["created", "working", "input_required", "completed", "failed", "cancelled"]
    artifacts: list[ArtifactRef]            # report handles, advice bundles
    events: list[InteractionEvent]          # generalized DelegationEvent
    token_budget: int
    deadline: float | None
    scheduler_policy: SchedulerPolicy
    telemetry: InteractionTelemetry         # interaction_type, skill, context_hash, policy_version

INTERACTION_POLICY_VERSION = "1.0"
```

`InteractionEvent` generalizes `DelegationEvent` (`src/api/models/responses.py:19-30`) by adding `interaction_type: Literal["delegate", "consult", "verify", "route"] = "delegate"`. Default preserves backward compat with existing `delegation_events` consumers.

`SchedulerPolicy` is a thin dataclass wrapping the existing `ChatRequest` admission fields:

| Field | Maps to | Default for `delegate` | Default for `consult` |
|-------|---------|------------------------|-----------------------|
| `priority: str` | `ChatRequest.request_priority` (`requests.py:102`) | `"interactive"` | `"background"` |
| `max_queue_wait_ms: int \| None` | `ChatRequest.max_queue_wait_ms` (`requests.py:107`) | inherit | `2000` |
| `migration_budget_ms: int \| None` | `ChatRequest.migration_budget_ms` (`requests.py:114`) | inherit | `inherit` |
| `cancellable: bool` | NEW | `False` | `True` |

`InteractionTelemetry` carries `interaction_type`, `skill`, `context_hash`, `policy_version` for log emission and reward attribution.

#### Invariants

| # | Invariant | Why | How to verify |
|---|-----------|-----|---------------|
| I1 | Region-lock visibility preserved across all interaction kinds | shape-aware contention (`inference.py:230`) depends on cross-role state; opacity would break the global region-mutex (see [[project_cross_role_contention_placement_blind]]) | `epyc-orchestrator/scripts/server/affinity_preflight.py` snapshot per phase |
| I2 | Shared-backend `topology_role` alias preserved | `coder_escalation` aliases `frontdoor` pool (`backend.py:90-140`); consult must dispatch under physical role | Live thread-union affinity vs `NUMA_CONFIG` (per [[feedback_verify_live_affinity_not_just_topology_hash]]) |
| I3 | `enable_thinking=false` per-role transport flags preserved | Qwen3.6 frontdoor + Qwen3.5-122B architect_general require thinking=off ([[feedback_qwen3x_enable_thinking_false]]); applies on `/v1/chat/completions` only ([[feedback_enable_thinking_requires_chat_completions_path]]) | Per-role chat completions probe |
| I4 | DCP remains advisory, not a hard context firewall | DCP-4 (`chat_delegation.py:247-289`) explicitly "advisory only; reactive discovery stays fully enabled" | Reactive top-up still works in consult mode |
| I5 | Legacy delegation telemetry readable for one rev | External MemRL / log / wandb consumers may read `delegation_events` / `DelegationEvent` field name; rename must alias-not-break | Field alias verified in `delegation_events` consumers; old name still serializes |
| I6 | One-shot only in P2; no `input_required` consult | Multi-turn consult requires `ConsultationTask` store; out of scope for v1 | API rejects multi-turn consult requests with `UnsupportedOperationError` parity |

#### Phase Plan

##### P1 — Lifecycle refactor, no behavior change

**Goal**: Express the existing delegation loop in the `Interaction` abstraction without changing behavior.

- [x] **P1-1**. Create `src/orchestration/interaction.py` with `Interaction` dataclass, `InteractionEvent`, `ArtifactRef`, `SchedulerPolicy`, `InteractionTelemetry`, and `INTERACTION_POLICY_VERSION = "1.0"`. Done 2026-06-28 in orchestrator `18956892`.
- [x] **P1-2**. Add `interaction_type: str = "delegate"` field to `DelegationEvent` (`responses.py:19-30`) additively. Update `ChatResponse.delegation_events` description to mention `interaction_type`. Do NOT rename the field. Do NOT rename the class. Done in `18956892`.
- [x] **P1-3**. Refactor `_architect_delegated_answer()` (`chat_delegation.py:658-743`) to construct an `Interaction(kind="delegate", ...)` internally. Preserve the `tuple[str, dict]` return signature. Preserve `stats["delegation_events"]` field shape on the wire. Done in `18956892`; per-event `to_role` remains the actual delegate target.
- [x] **P1-4**. Wire `Interaction.scheduler_policy` to existing `request_priority` / `max_queue_wait_ms` / `migration_budget_ms` admission path (`inference.py:230-259`). No new fields on `ChatRequest`. Done in `18956892` via `SchedulerPolicy.from_primitives()` / `request_context_kwargs()`; `src/llm_primitives/inference.py` was intentionally untouched because GitNexus marked `_real_call` CRITICAL.
- [x] **P1-5**. Add `ProgressLogger.log_interaction()` (`progress_logger.py:250+`) as a generalization of `log_delegation()`. Preserve `log_delegation()` as an alias that calls `log_interaction(interaction_type="delegate", ...)`. Add `INTERACTION_POLICY_VERSION` alongside existing `DELEGATION_POLICY_VERSION`. Done in `18956892`.
- [x] **P1-6**. Preserve all existing tests. Add unit tests for `Interaction` lifecycle state transitions and event emission. Done in `18956892`.

**Gate to P2**:
- [x] Focused/adjacent pytest green: `uv run pytest -q tests/unit/test_interaction_lifecycle.py tests/unit/test_api_models_responses.py tests/unit/test_progress_logger_interaction.py tests/unit/test_architect_delegation.py tests/unit/test_chat_delegation.py tests/unit/test_inference_mixin.py` -> 138 passed; post-fix adjacent suite `uv run pytest -q tests/unit/test_interaction_lifecycle.py tests/unit/test_architect_delegation.py tests/unit/test_chat_delegation.py tests/unit/test_chat_pipeline_stages.py tests/integration/test_chat_pipeline.py` -> 187 passed.
- [x] `delegation_diagnostics` byte-equal on identical inputs across before / after. Current regression proof landed 2026-06-28 in orchestrator: `tests/unit/test_architect_delegation.py::TestArchitectDelegatedAnswer::test_delegation_diagnostics_are_byte_equal_for_identical_inputs` runs the lifecycle-backed delegation path twice with identical mocked inputs, isolates the delegation cache, serializes diagnostics with sorted JSON keys, and asserts byte equality. Validation slice: focused test plus adjacent delegation/lifecycle/API-model suite -> `117 passed`; ruff and py_compile passed.
- [x] No breaking rename to `delegation_events` / `DelegationEvent`; additive `interaction_type="delegate"` field only.
- [x] `epyc-orchestrator/scripts/server/affinity_preflight.py` shows no region-lock drift. Live artifact `epyc-orchestrator/orchestration/reports/internal_interaction_affinity_preflight_20260703T151843Z.json` checked 22 instances across `frontdoor`, `architect_general`, `ingest_long_context`, `worker_general`, `worker_vision`, and `vision_escalation`: `live_affinity_verified=true`, `memory_mismatches=0`, `memory_locality_required=false`.
- [x] One progress-window cycle (≥48h) with no rise in `delegation_cache_hits` miss rate or `ContentionDenied` 503 rate. ✅ 2026-07-07 Counter emission blocker is resolved in `epyc-orchestrator` `02a01617` and deployed by orchestrator API reload at `2026-07-03T15:40:30Z` (API PID `1769725`): delegated completions now persist `delegation_cache_lookups` / `delegation_cache_hits` / `delegation_cache_misses` / `delegation_cache_hit_rate` in progress completion metadata and response diagnostics, while HTTP `ContentionDenied` 503s emit `ROUTING_FALLBACK` progress events with `kind="contention_denied"` and best-effort flush. P2 live behavior was locked until the live ≥48h bake over these counters was clean.
  - 2026-07-04 bake readout `orchestration/reports/internal_interaction_bake_report_20260704T203808Z.{json,md}` is correctly not ready: `28.96h/48h`, `3` delegation-cache lookups, `0` hits, `3` misses, `0` ContentionDenied events, blockers `window_too_short` and `delegation_cache_split_comparison_unavailable`.
  - 2026-07-05 bake readout `orchestration/reports/internal_interaction_bake_report_20260705T054257Z.{json,md}` is still not ready: `38.04h/48h`, `3` delegation-cache lookups, `0` hits, `3` misses, `0` ContentionDenied events, blockers `window_too_short` and `delegation_cache_split_comparison_unavailable`.
  - 2026-07-07 bake readout `orchestration/reports/internal_interaction_bake_report_20260707T001921Z.{json,md}` has enough elapsed time (`80.65h/48h`) and `0` ContentionDenied events, but remains not ready because the second half has `0` delegation-cache lookup observations; blocker `delegation_cache_split_comparison_unavailable` remains.
  - 2026-07-07 quiet-window probe issued two real delegated `/chat` requests (`mock_mode=false`, `real_mode=true`, `force_mode=delegated`) to create second-half delegation-cache observations without AutoPilot running. Follow-up bake readout `orchestration/reports/internal_interaction_bake_report_20260707T005105Z.{json,md}` is ready: full-window lookups/hits/misses `4/0/4`, first-half miss rate `1.0`, second-half miss rate `1.0`, `0` ContentionDenied events, blockers `none`.
  - 2026-07-04 no-inference scaffold note: `epyc-orchestrator` staged the P2 skill spec, consult helper, cache-key namespacing, `log_consult()`, and an explicitly opt-in `run_edit_transaction(..., enable_review_before_commit=True)` review hook. No current caller enables that hook, no route/API path changed, and J17/live consult behavior remains gated by this bake.
  - Bake readout command landed in `epyc-orchestrator` `dc11d2ba`: `uv run python scripts/analysis/internal_interaction_bake_report.py --since 2026-07-03T15:40:30Z --min-hours 48 --output-json <path> --output-md <path>`. Initial artifact `orchestration/reports/internal_interaction_bake_report_20260703T154526Z.{json,md}` is correctly blocked (`0.08h/48h`, `0` delegation-cache observations, `0` contention-denied events).

##### P2 — One-shot consult sibling

**Goal**: Add `kind="consult"` as a narrow specialization on the same substrate, with typed output schema and scheduler defaults. **First and only consult site in v1: the code-edit drafting requester → `architect_general` for `review_before_commit`** (requester role identified in P2-0).

- [x] **P2-0**. **Discovery — identify the exact attach point** in the code-edit pipeline for the first consult site. Candidate paths to enumerate: the `force_mode="edit"` flow (`requests.py:force_mode` consumers), `batched-edit-parallel-apply` (sibling handoff), the REPL final-answer hook, `worker_coder` / `coder_escalation` drafting flows. Pick the single attach point where (a) the requester has a complete-enough draft to advise on, (b) integration of advisory feedback before commit is structurally possible (one re-run capacity), (c) the requester role identity is stable. Output: a one-paragraph design note appended to this handoff naming the chosen pipeline file:function. Validate with `gitnexus impact <chosen_function> --direction upstream` before P2-1 begins. **Do NOT assume `worker_general` is the requester** — the consultant skill `review_before_commit` is keyed by *consultant role*, not requester role; the requester is whatever role is at the attach point. Completed 2026-05-31: chosen seam is `epyc-orchestrator/src/edit_transaction.py:199` `run_edit_transaction()`, between draft parse and transactional apply; requester role is `coder_escalation`.

- [x] **P2-1**. Create `orchestration/interaction_skills.yaml` (sibling to `model_registry.yaml`). Done 2026-07-04 as a default-off skill spec for `architect_general.review_before_commit` with JSON output schema, background/consult scheduler defaults, max output tokens `400`, tools budget `0`, and consult TTL `1800s`.

  ```yaml
  interaction_skills:
    architect_general:
      review_before_commit:
        kind: consult
        description: "Advisory review of a coder draft before it commits."
        output_schema:
          type: object
          required: [risks, blocking_issues, confidence, recommended_delta]
          properties:
            risks:             { type: array, items: { type: string } }
            blocking_issues:   { type: array, items: { type: string } }
            confidence:        { type: number, minimum: 0, maximum: 1 }
            recommended_delta: { type: string }
            do_not_do:         { type: array, items: { type: string } }
            needs_input:       { type: string, nullable: true }
        max_output_tokens: 400
        scheduler_defaults:
          priority: background
          max_queue_wait_ms: 2000
          cancellable: true
        tools_budget: 0
        cache_ttl_seconds: 1800
  ```

- [x] **P2-2**. Add `consult()` entrypoint in `src/orchestration/consultation.py`. Done 2026-07-04 as an inert helper that loads the skill spec, builds a one-shot advisory prompt, calls `LLMPrimitives.llm_call(..., json_schema=...)`, validates JSON with `jsonschema`, returns `(parsed_advisory, stats)`, and raises `ConsultationDenied(reason="schema_violation")` on parse/schema failure.

  ```python
  def consult(
      consultant_role: str,
      requester_role: str,
      skill: str,
      context: str,
      primitives: "LLMPrimitives",
      *,
      override_max_tokens: int | None = None,
      override_priority: str | None = None,
  ) -> tuple[dict, dict]:
      """Returns (parsed_advisory, stats). parsed_advisory matches the skill's output_schema."""
  ```

  Loads the skill spec from `interaction_skills.yaml`. Constrains the LLM output via `LLMPrimitives.llm_call(..., json_schema=skill.output_schema)` (`primitives.py:506`) — **NOT** via `ChatRequest.output_schema`, which is a REPL-context FINAL() validator injected into the prompt, not a call-time output constraint. Parses + validates the returned JSON against the schema; on parse / validation failure, raises `ConsultationDenied(reason="schema_violation")`. Enforces `max_output_tokens` and `tools_budget`. Dispatches through the same contention gate (`inference.py:230`) and shared-backend `topology_role` mapping (`backend.py:90+`).

- [x] **P2-3**. Extend `DelegationCache.make_key()` (`src/orchestration/delegation_cache.py:69-78` — the actual module; `src/delegation_cache.py` is only a back-compat shim) to namespace by interaction type and skill. Done 2026-07-04 with keyword-only `interaction_type`, `skill`, `schema_hash`, and `policy_version`; legacy delegate keys remain byte-stable when callers pass only `(brief, delegate_to)`.

  ```python
  @staticmethod
  def make_key(
      brief: str,
      delegate_to: str,
      *,
      interaction_type: str = "delegate",
      skill: str = "",
      schema_hash: str = "",
      policy_version: str = "1.0",
  ) -> str:
      normalized = brief.strip().lower()[:200]
      payload = f"{interaction_type}|{skill}|{normalized}|{delegate_to}|{schema_hash}|{policy_version}"
      return hashlib.sha256(payload.encode()).hexdigest()
  ```

  Existing call sites (`chat_delegation.py:939`) pass only `(brief, delegate_to)` — keyword defaults preserve them. Cache TTL per-skill via `cache_ttl_seconds` field; falls back to `DEFAULT_TTL_SECONDS = 3600`.

- [x] **P2-4**. Reuse `_maybe_dcp_seed_context()` (`chat_delegation.py:247-289`) for consult context packaging. Done 2026-07-05 in `epyc-orchestrator` `4183522f`: `dcp_for_consult` is a new default-off feature flag that validates dependency on `dcp_pre_assembly`; `consult()` accepts optional `code_search_fn` / `dcp_budget` and, only when both flags are enabled, calls the existing DCP seed helper instead of creating a second packer. Without a code-search hook or with either flag off, consult context is unchanged.

- [x] **P2-5**. Add `log_consult()` shim on `ProgressLogger`. Done 2026-07-04; it records `interaction_type="consult"`, `skill`, consultant/requester roles, confidence, outcome, reason, and the interaction policy version.

- [x] **P2-6**. Add `ConsultationDenied` exception (parallel to `ContentionDenied`). **P2 is an INTERNAL consult sibling — no new HTTP endpoint and no 503 mapping in this phase.** Internal callers catch `ConsultationDenied` and record a `consult_denied` event in `interaction_events`. Done 2026-07-04: `consult()` translates contention-gate `ContentionDenied` into `ConsultationDenied(reason="contention_skip")`; the current skill uses its explicit per-skill `max_queue_wait_ms=2000` override, and can be changed to `0` before live enablement if the final policy chooses strict skip-or-admit. A future external consult HTTP endpoint (deferred, D3-adjacent) would map `ConsultationDenied` to 503; that mapping is out of scope here.
  - **Verified 2026-05-31** (`contention_gate.py:346-399`): `max_queue_wait_ms=0` achieves the intended skip-or-admit semantics natively. The default-fallback at `:366` (`if max_queue_wait_ms is None`) does NOT catch `0`, so per-skill `0` is preserved. `deadline = time.monotonic() + 0/1000 = now` at `:372`, the loop at `:375` runs one `evaluate()` call, admits-immediately if no blocker, otherwise returns `reason="timeout"` after that single evaluate with `waited_s ≈ 0`. No separate skip-logic needed. Add a regression test pinning this behavior so a future gate refactor cannot silently re-introduce the default-fallback for `0`.

- [x] **P2-7**. Wire the first consult site **at the attach point identified in P2-0**. Skill: `review_before_commit`. Consultant: `architect_general`. Requester: the role producing the code-edit draft at the chosen attach point (named in the P2-0 design note — may be `worker_coder`, `coder_escalation`, or another; do NOT assume `worker_general`). Done 2026-07-05 in `epyc-orchestrator` `0e555822`: `force_mode="edit"` now passes a `review_before_commit` callback into `run_edit_transaction()` only when the new `review_before_commit_consult` feature flag is explicitly enabled. The hook calls `architect_general.review_before_commit`, caps integration at one requester rerun on high-confidence blocking advice, and records consult events in `delegation_diagnostics["edit_transaction_consult_events"]`. With the flag off, existing edit-mode callers remain one-shot/no-consult.
  ```python
  consult(
      consultant_role="architect_general",
      requester_role=<from P2-0>,
      skill="review_before_commit",
      context=draft_summary,
      primitives=primitives,
  )
  ```
  Integrate the parsed advisory:
  - If `blocking_issues` non-empty AND `confidence >= 0.6`: re-run the requester with the advisory injected; cap at 1 re-run.
  - Otherwise: emit the advisory as a `review_advisory` event in the response telemetry and proceed.
  - On `ConsultationDenied`: emit a `consult_denied` event and proceed without the advisory.
  - 2026-07-04 scaffold: `run_edit_transaction()` now has an explicitly opt-in `review_before_commit` hook and `enable_review_before_commit` flag. If a blocking advisory with confidence `>=0.6` is returned, the requester gets exactly one rerun with the advisory injected before transactional apply. With the default flag unset, existing callers remain one-shot and no review hook is invoked.
  - 2026-07-05 route wiring: the chat edit-mode route now supplies the consult callback behind `review_before_commit_consult`; live enablement remains locked until the P1 bake gate clears and J17 evidence is collected.

**Gate to P3**: A/B test on a fixed eval slice (≥50 code-edit turns):
- Tokens saved vs full-delegation baseline ≥ 30% on the advisory leg
- Answer quality non-regression: ≤ 1pp drop on the code-edit eval slice
- Contention tax not visible: `worker_general` decode p50 within ±5% pre vs post
- Advice cache hit rate ≥ 10% on repeated identical-shape edits within a 1h window
- All six invariants (I1–I6) hold under P2 traffic

- [x] **P2/J17 live evidence collected** ✅ 2026-07-07. Artifact:
  `epyc-orchestrator/orchestration/reports/internal_interaction_j17_ab_20260707T011136Z/`.
  The 50-turn-per-arm live A/B repeated the current 5-task BEP sandbox slice
  10x. Baseline and consult both passed `40/50` (`quality=0.800`, delta
  `0.0pp`), but consult added latency (`coder_wall_p50` `2.839s` vs `2.316s`,
  `+22.58%`), produced `50/50` successful consultant calls, requested `0`
  reruns, and had `0.0` cache-hit rate. Conclusion: the default-off
  `review_before_commit_consult` seam works mechanically, but the BEP slice is
  too simple to support blanket enablement.
- [x] **P2/J17 targeted consult-value slice collected** ✅ 2026-07-07.
  Artifact:
  `epyc-orchestrator/orchestration/reports/internal_interaction_j17_ab_20260707T121211Z/`.
  The 10-task targeted suite repeats higher-risk edit shapes 5x each:
  compatibility shims, migration defaults, rollback semantics, parser edge
  cases, async ordering, graph cycles, dedupe, optional dependencies, plugin
  registry contracts, and path safety. Baseline passed `35/50`
  (`quality=0.70`); consult passed `40/50` (`quality=0.80`, `+10.0pp`), with
  `50/50` consult successes and `15` rerun requests. Consult rescued the
  parser/comment/value edge case from `0/5` to `5/5`, but did not fix
  transaction rollback parse failures or plugin-registry verifier failures.
  Coder wall p50 rose `+14.49%`, and consult wall p50 was `22.871s`. Decision:
  **targeted-positive / default-off**. Proceed to a P3-style gate only for
  high-risk edit shapes; do not enable consult on every edit transaction.

##### P3 — Consult gating policy, shadow first

**Goal**: Stop calling consult on every code edit. Gate by signals owned by `routing-intelligence`.

- [x] **P3-0**. Convert the J17 targeted-positive result into a narrow gate proposal: fire `review_before_commit_consult` only for high-risk edit shapes where the targeted slice showed plausible value (parser/data-contract edge cases, compatibility shims, optional-dependency fallbacks, high blast-radius symbols, or hidden-verifier-risk patterns). Explicitly avoid easy/small edits and known format-compliance failures where consult did not help. Completed 2026-07-07: `epyc-orchestrator/src/orchestration/review_consult_gate.py` implements the transparent lexical/shape gate, and `run_edit_transaction()` records `targeted_gate_skip` consult events when the gate declines to call the consultant.
- [x] **P3-1**. Gate signal taxonomy: ✅ 2026-07-14 — substantially implemented via P3-2d (`epyc-orchestrator` `1967c682`): `ConsultSignals` combines difficulty band, factual-risk band/score, touched-symbol blast radius, recent failure pressure, benchmark class, latency budget, and MemRL hints.
  - `factual_risk_score` (from `routing-intelligence`)
  - `difficulty_band` (`progress_logger.log_delegation` already carries this; reuse via `log_interaction`)
  - `diff_size` (lines changed in the proposed edit)
  - `touched_symbol_blast_radius` (via `gitnexus impact <symbol> --direction upstream`)
  - `recent_failure_history` (last N turns of this requester role)
  - `benchmark_class` (in-eval or live)
  - `latency_budget_remaining`

- [x] **P3-2a**. Implement the first `review_before_commit` high-risk edit-shape policy behind `ORCHESTRATOR_FEATURE_REVIEW_BEFORE_COMMIT_TARGETED_GATE=1`. It is inert unless `review_before_commit_consult` is also enabled, preserves blanket-consult behavior when the new gate flag is off, and currently triggers on parser/data-contract/compatibility terms, hidden-verifier/transaction risk, deletes, multi-file edits, and public API/registry/config paths.
- [x] **P3-2b seed surface**. AutoPilot now has a first-class `consult_gate_probe` action surface that runs hard edit-transaction turns as `baseline` vs blanket `consult` vs targeted `gated`, records consult calls/skips/reruns/quality/latency, and reports the result on the requested tier (default `tier=3`) under `consult_gate_targeted`. This is not a T0 side audit: it is intended to let the optimizer search for high-quality, fast review-before-commit policies on hard workflow material.
- [x] **P3-2c memory projection seed**. Consult-gate probe rows now project into StrategyStore as deterministic `journal-consult-gate-trial-<id>` pattern memories, including dominated/negative rows when they are otherwise trustworthy. Stored metadata preserves tier, task suite, quality delta, consult-call/skip rate, reruns, and gate-reason counts, so planner retrieval can learn conditional policy (`consult when T3 + parser/data-contract risk`, skip easy/single-file edits) rather than a global consult-good/bad rule.
- [x] **P3-2d**. Generalize to `should_consult(interaction_intent, signals) -> bool` with routing-intelligence/MemRL signals rather than only lexical edit-shape rules. Completed 2026-07-07 in `epyc-orchestrator` `1967c682`: `ConsultIntent` / `ConsultSignals` now combine the transparent lexical edit-shape gate with hard tier, difficulty band, factual-risk band/score, touched-symbol blast radius, recent failure pressure, benchmark class, latency budget, and MemRL hint signals. The live edit-mode adapter passes routing risk/difficulty and latency budget through `review_before_commit_gate_from_context()`. Focused validation: `tests/unit/test_review_consult_gate.py`, `tests/unit/test_edit_transaction.py`, and `tests/unit/test_features.py` passed (`87 passed`), py_compile passed, and ruff passed.

- [ ] **P3-3**. **Shadow/optimization calibration**: use `consult_gate_probe` on T2/T3 hard workflow slices to compare always-consult vs targeted-gate behavior. The key metrics are solved-task quality, tasks/hour, consult-call rate, false skips, rerun quality lift, and whether StrategyStore retrieval surfaces the right conditional memories on subsequent planner turns.
  - 2026-11-09 audit: NAR. `consult_gate_probe` is an Autopilot action (`scripts/autopilot/actions.py:2380`); no calibration run is possible while Autopilot is on HOLD. HOLD list.
  - 2026-07-07 T3 canary ✅: trial `1251`, action `{"type":"consult_gate_probe","task_suite":"targeted","turns":10,"tier":3}`, artifact `epyc-orchestrator/orchestration/reports/internal_interaction_j17_ab_20260707T140837Z/`. Result: baseline `7/10` (`quality=0.70`) vs gated `8/10` (`quality=0.80`, `+10.0pp`), `consult_gate_targeted=2.4` on the 0-3 scale, `pareto_status=frontier` for T3, `tasks_per_hour=171.736`, `consult_calls=9`, `consult_skips=1`, `rerun_requests=3`, and gate reason counts `{hidden_verifier_or_transaction_risk: 7, parser_data_contract_or_compatibility: 5, multi_file_edit_surface: 2, no_parsed_file_blocks: 1}`. StrategyStore retrieval for `consult gate parser data contract T3 targeted review_before_commit` returns `journal-consult-gate-trial-1251` as the top hit. This satisfies the first canary; keep P3-3 open for T2/T3 breadth, false-skip analysis, and week-scale shadow data.

- [ ] **P3-4**. After ≥1 week of shadow data: enable enforcement for one signal at a time. Require an explicit gate-rollback handoff if quality regresses (≥1pp on the code-edit eval slice).
  - 2026-11-09 audit: NAR, blocked on P3-3: needs >=1 week of shadow data and none has accrued since the stack stopped. HOLD list.

**Gate to P4**: Shadow logs show consult provides nonzero advice value on > 30% of triggered turns; enforcement plan shows expected net token saving with bounded quality risk.

##### P4 — Integration-quality evaluation

**Goal**: Beyond token / latency, measure whether consultation actually helps.

- [ ] **P4-1**. Integration-quality metrics:
  - 2026-11-09 audit: UNDERSPECIFIED. The box text is only a header; the metrics are the nested bullets (`advice_adopted_correctly`, `issue_catch_rate`, `false_block_rate`, ...). No code emits any of them (grep: zero hits). Missing: owner and record source. Decision needed: emit them as trace-store records through the harness schema (`src/trace/harness_schema.py`, same path as URE-2 approval records) vs inside the Autopilot `consult_gate_probe` result. Recommendation: harness-schema records, so they exist outside Autopilot runs. Add a `[belief:]` wiring task when built.
  - `advice_adopted_correctly` — did the requester act on the advice?
  - `issue_catch_rate` — did consult catch real bugs that delegation alone missed?
  - `false_block_rate` — consult flagged a non-issue, blocked the requester unnecessarily
  - `downstream_answer_quality_delta` — vs no-consult baseline on the same prompt
  - `contention_impact_tax` — cross-role latency cost of running consults

- [ ] **P4-2**. Wire metrics into MemRL reward signal as a separate `consult_reward` head. Do NOT blend with delegation reward until calibrated.
  - 2026-11-09 audit: SV, HOLD. Its own text forbids blending until the head is 'calibrated'; calibration is P3-3, which runs through the Autopilot action `consult_gate_probe`. `consult_reward` has zero hits in `src`/`scripts`. It cannot start before P3-3 produces data, and that waits on Autopilot. HOLD list.

- **[declined: ws58 2026-11-03 content-review: recurring bookkeeping with no trigger]** **P4-3**. Quarterly review: keep / tune / disable each consult skill based on metrics.

**Exit**: At least one skill (`worker_general → architect_general review_before_commit`) shows positive `consult_reward` over 4 weeks. Metrics dashboard exists. Quarterly review cadence established.

##### Deferred Work — require their own gate before re-opening

- **D1. Streaming consult**. Needs backend streaming callback exposure (current `/chat/stream` wraps pipeline events, not backend tokens). Reopen when `stream_adapter` exposes tokens directly OR when a consult skill needs intermediate artifacts to integrate concurrently.
- **D2. Multi-turn `input_required` consult**. Needs local `ConsultationTask` store with terminal / interrupted states. Reopen when one-shot consult fails on a real use case (e.g., consultant needs clarification before advising).
- **D3. External A2A adapter**. Inbound at `hermes-outer-shell` (advertise Agent Cards for external callers); outbound for cross-vendor consult (consume external A2A peers). Reopen when (a) Path A external exposure becomes load-bearing on `hermes-outer-shell`, OR (b) a frontier cloud model exposes A2A endpoints.

#### Dependency Graph

```
P1 (lifecycle refactor, no behavior change)
  │
  ▼
P2 (one-shot consult sibling) ◄── delegation-context-preassembly (DCP-6: ranking/rendering for context packaging)
  │
  ▼
P3 (gating policy, shadow first) ◄── routing-intelligence (factual-risk / difficulty / shadow-routing signal quality)
  │
  ▼
P4 (integration-quality eval) ──► MemRL/reward telemetry (separate consult_reward head)

External deferred:
  D3 (external A2A) ◄── hermes-outer-shell Path A go/no-go
```

#### Migration Plan (additive, two revs)

**Rev N (this handoff's P1 + P2)**:
- Add `InteractionEvent` class with `interaction_type: str` field default `"delegate"`.
- Add `interaction_type: str = "delegate"` field directly to `DelegationEvent` (additive).
- Keep `DelegationEvent` class name. Do NOT rename to `InteractionEvent` yet.
- Keep `ChatResponse.delegation_events` field name. Do NOT rename to `interaction_events` yet.
- Keep `ProgressLogger.log_delegation()` as an alias calling `log_interaction(interaction_type="delegate", ...)`.
- Keep `DELEGATION_POLICY_VERSION = "1.0"` alongside new `INTERACTION_POLICY_VERSION = "1.0"`.
- Update field descriptions to mention `interaction_type`.

**Rev N+1 (next major orchestrator release, after telemetry consumers audited)**:
- Optionally rename `DelegationEvent` → `InteractionEvent` (alias old name for one rev).
- Optionally rename `delegation_events` → `interaction_events` on `ChatResponse` (alias old name for one rev).
- Audit MemRL / wandb / external log consumers. Coordinate breaking-change announcement if needed.

#### Open Decisions (none block P1; surface for P2)

1. **`tools_budget` semantics**. Proposal: `tools_budget=0` = no tools at all; `tools_budget=N` = at most N tool calls; `tools_budget=null` = inherit from caller. Confirm.
2. **`TrafficClass` for consult**. Proposal: reuse existing `TrafficClass.BACKGROUND` (per skill default). Reopen if BACKGROUND's queueing semantics (90s default queue wait) doesn't fit consult cancellability. Alternative: add `TrafficClass.FOREGROUND_ADVISORY`. Confirm.
3. **Consult cache TTL**. Existing `DEFAULT_TTL_SECONDS = 3600`. Proposal: 1800s default for consult (advice goes stale faster); per-skill override in `interaction_skills.yaml`. Confirm.
4. **`features()` flag naming**. Proposal: `features().consult_skills_enabled` as a per-skill dict (so `review_before_commit` can enable without enabling all future consults). Alternative: global `features().consult_enabled`. Confirm.

#### Key file locations

Primary touch points:

- `epyc-orchestrator/src/api/routes/chat_delegation.py:658-743` (P1 refactor)
- `epyc-orchestrator/src/api/routes/chat_delegation.py:247-289` (P2 DCP reuse)
- `epyc-orchestrator/src/api/routes/chat_delegation.py:936-955` (P2 cache namespace)
- `epyc-orchestrator/src/orchestration/delegation_cache.py:27-78` (P2 `make_key` extension; `src/delegation_cache.py` is a back-compat shim only)
- `epyc-orchestrator/src/llm_primitives/primitives.py:506` (P2 `llm_call(..., json_schema=...)` constraint path)
- `epyc-orchestrator/scripts/server/affinity_preflight.py` (per-phase I1 region-lock verification)
- `epyc-orchestrator/src/api/models/responses.py:19-30` (P1 `DelegationEvent` additive `interaction_type`)
- `epyc-orchestrator/src/api/models/requests.py:102-131` (P1/P2 admission + `output_schema`)
- `epyc-orchestrator/orchestration/repl_memory/progress_logger.py:250-288` (P1 `log_interaction` generalization)
- `epyc-orchestrator/src/llm_primitives/inference.py:230-259` (preserve contention gate)
- `epyc-orchestrator/src/llm_primitives/backend.py:90-140` (preserve topology_role aliasing)
- `epyc-orchestrator/orchestration/model_registry.yaml` (sibling for new `interaction_skills.yaml`)

NEW files (created during phase execution):
- `epyc-orchestrator/src/orchestration/interaction.py` (P1)
- `epyc-orchestrator/src/orchestration/consultation.py` (P2)
- `epyc-orchestrator/orchestration/interaction_skills.yaml` (P2)

#### P2-0 Design Note — chosen attach point (2026-05-31)

Discovery completed 2026-05-31. GitNexus is indexed only for `epyc-root` (not `epyc-orchestrator`), so upstream-caller analysis used grep + direct code read instead of `gitnexus impact`.

##### Candidate scorecard

| Candidate | (a) Complete draft pre-commit | (b) Re-run capacity | (c) Stable requester | Verdict |
|-----------|-------------------------------|---------------------|----------------------|---------|
| `force_mode="edit"` → `run_edit_transaction()` at `src/edit_transaction.py:199` | ✅ `new_files: dict[str, str]` parsed at `:210` before apply at `:211` | ✅ in-memory draft; `apply_edit_transaction()` is a separate function — natural seam | ✅ routes to `coder_escalation` (Qwen3.6-35B-A3B Q8 @ :8071, shared mmap with frontdoor) per `model_registry.yaml:381,908` + CHANGELOG | **CHOSEN** |
| REPL `_final()` at `src/repl_environment/context.py:169` | ◐ answer complete, but the wiki notes this path was bypassed for code-edit work (multi-turn read→peek→edit→FINAL loop failed BEP) | ✘ `FINAL()` terminates REPL execution; injecting a consult that may re-run is structurally invasive | ◐ role identity varies by REPL caller (worker_general / worker_fast / etc.) | rejected |
| `worker_coder` default flow | — | — | ✘ `worker_coder` (port 8102, 30B alias) failed the BEP code-edit tasks; production code-edit producer is now `coder_escalation` per the 2026-05-27 protocol-fix work | rejected |
| `coder_escalation` default flow | overlaps with Candidate A when `force_mode="edit"` is set | — | ✅ same role as Candidate A | folded into Candidate A |
| Batched-edit pipeline (`batched-edit-parallel-apply`) | — | — | ✘ "implementation-scoped draft" status; BEP-2 was the falsification gate and is now optional provenance per its handoff banner — not a shipping production path | rejected |

##### Chosen attach point

**`epyc-orchestrator/src/edit_transaction.py:199` `run_edit_transaction()`, between the one-shot draft `llm_call()` at `:209` and the transactional `apply_edit_transaction()` at `:211`.**

##### Why this is the right seam

1. **Production-shipping path.** `force_mode="edit"` is the canonical multi-file code-edit surface (default-off via `ORCHESTRATOR_EDIT_TRANSACTION=1` + scoped `ORCHESTRATOR_EDIT_ROOT`, fail-closed with HTTP 412 if either is missing). The wiki names it as the remediation for the BEP read→peek→edit→FINAL failure class. Not a vapor target.
2. **Complete structured draft pre-commit.** After `parse_edit_response(raw)` at `:210`, the draft is a fully-typed `(new_files: dict[str, str], deletes: list[str])`. Advisory feedback can be summarized against this structured artifact rather than against free-form prose.
3. **Apply is a separate function.** `apply_edit_transaction()` (`:138`) handles snapshot / write / syntax-check / rollback as a discrete step. Inserting a consult between draft parse and apply is a single-statement change with no transaction-semantics risk — the rollback path is untouched.
4. **Stable requester role.** `force_mode="edit"` per `chat.py:589` calls `run_edit_transaction(..., _edit_llm_call, ...)`; the `_edit_llm_call` closure at `chat.py:573-586` calls `_execute_direct()` against `initial_role`, which for `force_mode="edit"` resolves to `coder_escalation` per the production routing. Stable identity for `interaction_skills.yaml` registry + telemetry.
5. **LOW blast radius.** Only TWO upstream callers of `run_edit_transaction` exist in the entire codebase:
   - `epyc-orchestrator/src/api/routes/chat.py:589` (sole production caller)
   - `epyc-orchestrator/tests/unit/test_edit_transaction.py:104` (`test_run_edit_transaction_with_stub_llm`)

   Adding `primitives` as a keyword-only optional with `None` default preserves the test's existing call shape.

##### Wiring sketch (executed in P2-7)

```python
def run_edit_transaction(
    llm_call: Callable[[str], str],
    task_prompt: str,
    root: Path | str,
    target_files: list[str] | None = None,
    self_check: bool = True,
    *,
    primitives: "LLMPrimitives | None" = None,   # NEW (P2-7)
) -> tuple[EditResult, str]:
    try:
        files_ctx = assemble_context(root, target_files)
    except EditScopeError as e:
        return EditResult(ok=False, error=str(e)), ""
    raw = llm_call(build_edit_prompt(task_prompt, files_ctx)) or ""
    new_files, deletes = parse_edit_response(raw)

    # NEW (P2-7): optional advisory consult between draft and apply
    if primitives is not None and features().consult_skills_enabled.get("review_before_commit"):
        try:
            advisory, _stats = consult(
                consultant_role="architect_general",
                requester_role="coder_escalation",
                skill="review_before_commit",
                context=_summarize_draft(new_files, deletes, task_prompt),
                primitives=primitives,
            )
            if advisory.get("blocking_issues") and advisory.get("confidence", 0.0) >= 0.6:
                raw = llm_call(build_edit_prompt(task_prompt, files_ctx, advisory=advisory)) or ""
                new_files, deletes = parse_edit_response(raw)  # one re-run cap
        except ConsultationDenied:
            pass  # event recorded upstream as consult_denied in interaction_events

    return apply_edit_transaction(root, new_files, deletes, self_check=self_check), raw
```

##### Wiring impact upstream

- `chat.py:589` becomes `run_edit_transaction(_edit_llm_call, request.prompt, get_task_root(), None, primitives=primitives)` — `primitives` is already in scope (passed to `_execute_direct` etc.).
- `build_edit_prompt()` gains an optional `advisory` parameter for the re-run path; default `None` preserves all existing call sites.
- `_summarize_draft()` is a new helper (small, P2-7 scope) producing the bounded context the consultant sees — NOT the full file bodies (that's the consultant's job to reason about, gated by `tools_budget`).

##### Sanity gates before P2-1

- ✅ Single production caller verified (`chat.py:589`).
- ✅ Apply step is a separable function (`apply_edit_transaction` is called once at `:211`).
- ✅ Requester role identity stable (`coder_escalation` per `force_mode="edit"` branch).
- ✅ Test fixture impact LOW (keyword-only optional preserves `test_run_edit_transaction_with_stub_llm`).
- Pending P1: `Interaction(kind="consult", ...)` substrate must land before P2-7 wiring (per phase ordering — P2-7 depends on P1's interaction abstraction).

**Discovery status**: COMPLETE. P2-1 may proceed when P1 lifecycle refactor is gate-passed.

##### P3 — Heterogeneous structured delegation chain (post-P2, added 2026-06-25)

**What already exists** (from `routing.py` audit):
- `_delegate_single`: isolation already correct — workers receive `self.context[:4000]` (original user task) + brief. Frontdoor's REPL scratchpad, tool call history, and reasoning are **not passed**. No scaffolding needed for single worker isolation.
- `_delegate_parallel`: homogeneous fan-out works — up to 4 concurrent workers of the same role, each isolated, results returned as a list. Frontdoor synthesizes the list in its own REPL code.

**Three interaction patterns and their current REPL implementation**:

| Pattern | Mechanism | Context passed | Status |
|---------|-----------|----------------|--------|
| Consultation (frontdoor → architect for advice) | Escalation → IIL `consult` kind (P2) | Full context (correct) | P2 in progress |
| Worker execution (frontdoor → coder for bounded task) | `_delegate_single` | Original task + brief only (isolation already implemented) | ✅ done |
| Fan-out + synthesis (N workers → synthesizer) | `_delegate_parallel` (homogeneous only) | Each worker: original task + its item (isolated) | Partial — homogeneous only |

**Gap for P3**: heterogeneous structured chains — e.g. "coder handles implementation (isolated), architect reviews coder's output (access_list=[0]), synthesizer sees both (access_list=[0,1])." Not implemented. `_delegate_parallel` only dispatches to one role; there's no explicit access_list routing.

**Autopilot exploration path (no P3 code needed)**:
The homogeneous fan-out + synthesis pattern IS reachable today via PromptForge mutations on `resolver.py` (in `CODE_MUTATION_ALLOWLIST`). Teaching the frontdoor prompt to use `delegate(brief, parallel=True)` followed by explicit synthesis in REPL code exercises the parallel infrastructure without new code. A strategy store entry has been seeded to prime this exploration — see below.

**P3 scope** (gated on P2 complete):
- Add `delegate_chain(steps: list[tuple[role, brief, access_list]])` to `routing.py` — structured multi-step heterogeneous dispatch where each step's context is explicitly constructed from designated prior outputs
- Add `features().iil_structured_chain` feature flag (default-off)
- The access_list semantics: `[]` = isolated (just original task + brief), `["all"]` = all prior step outputs, `[0, 2]` = specific step indices
- Gate: do NOT implement before P2 A/B evidence shows the consult pattern has positive quality signal (P3 adds complexity; validate the simpler consult first)

**Strategy store hypothesis (seeded 2026-06-25, for autopilot PromptForge exploration)**:
When autopilot restarts, it will find a primed entry: "frontdoor should use delegate(brief, parallel=True) for independent subtasks then synthesize — infrastructure exists in _delegate_parallel." This primes PromptForge to try mutations in resolver.py that teach the frontdoor model to use the existing fan-out capability before P3 adds heterogeneous chains.

##### Inference-window scheduling (bulk-inference-campaign cross-ref)

The P2 A/B (≥50 code-edit-turn comparison at the edit-transaction seam) is registered as **J17** in [`bulk-inference-campaign.md`](eval-tower-program.md#track-bulk-inference-campaign) under the "Other agents' inference-gated work" table. That handoff carries the inference-window scheduling logic, model requirements (`coder_escalation` + `architect_general`), and prereq-chain visibility for the operator triggering the eval. The bulk-inference handoff's "Internal Interaction Lifecycle (consult sibling) — TRACKING" tail section mirrors the live status (P2-0 ✅ / P1 code ✅ / P1 bake ⏳ / P2 ⏳ / J17 🔒 / P3+P4 🔒) so the inference-window agent can see exactly when to schedule J17 without reading this full handoff. Update both sides when phase state changes.

#### Reporting

- Tick checkboxes inline in this handoff after each phase task.
- Update `Status` line at top of handoff after each phase gate.
- Append A/B results and gate-pass evidence to `progress/YYYY-MM/YYYY-MM-DD.md`.
- Cross-link decisive findings to `routing-and-optimization-index.md` Outstanding Tasks section.
- On completion of all four phases, move this handoff to `handoffs/completed/` and write a wrap-up.

## Track: learned-routing-controller
<!-- gate: none -->

> Folded from `handoffs/active/learned-routing-controller.md` @ `b33c4e7a5fd1` on 2026-11-02 (BRF-T1-F26, route 1a, operator D1/D5; retired row RTG-15 → RTG-09). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Learned Routing Controller: MLP Distillation from Episodic Memory

**Scratch**: `/mnt/raid0/llm/tmp/learned-routing-controller/` · worktrees: `/mnt/raid0/llm/worktrees/learned-routing-controller-*`

**Created**: 2026-04-15
**Status**: REFRESHED 2026-06-12 (BGE+MLP repair follow-up) — classifier fast-path is **STAGED, not live**: fresh `routing_classifier_weights.npz` now exists and wiring preflight passes, but production still attests `routing_classifier=false` across 6 workers pending a rollout decision. The historical "Phase 1 COMPLETE — 92% val acc, flag enabled" claim below describes pre-reset state; current retrain is 81.0% val acc with thresholded >=0.8 precision 94.4% over 61.6% coverage. The BGE repair blocker is cleared (see [retrain-routing-models.md](routing-program.md#track-retrain-routing-models)): 275,960 FAISS vectors, 94.6% coverage, diagnose-only HEALTHY. **Phases 1.5+ are FROZEN per fable5-findings-02** pending a future DAR-1 regret replay >=5% plus per-question eval vectors.
**Next (start here, 2026-09-27)**: EP-5 — re-run the outcome-label probe on rows updated after `24b43990` (or after
the EPD-1b backfill), then EPD-3. Open follow-ups: LRC-1 (autopilot data as MLP training data), LRC-2 (the inert
`ORCHESTRATOR_FRONTDOOR_VERIFIER_GATE=1`); LRC-TD-1 was folded into `typed-decision-plane.md` TD-11 on 2026-09-29. Completed history is linked from *Completed Scope*.
**Priority**: ACTIVE for rollout decision of the repaired BGE+MLP fast path; FROZEN for expansion. Do not promote logit/hidden-state/GraphRouter-style expansion until the fable5 routing-freeze gates clear.
**Related**: [routing-intelligence.md](routing-program.md#track-routing-intelligence), [autopilot-continuous-optimization.md](autopilot-program.md), [retrain-routing-models.md](routing-program.md#track-retrain-routing-models), [decision-aware-routing.md](routing-program.md), SkillBank (completed handoff)
**Rollback**: Set `ORCHESTRATOR_ROUTING_CLASSIFIER=0` (default). Zero schema/API/data changes. (With weights missing, flag-ON is already functionally equivalent to fallback — but the flag should be reconciled with reality.)

---

#### Problem

The routing MLP classifier (`routing_classifier.py`) exists but was trained on raw, unnormalized action labels from the episodic store. The store has ~30 distinct action strings that should map to ~5 clean routing targets. Escalation events (10K+ labeled examples of "frontdoor was wrong") aren't being used as training signal. The classifier feature flag is OFF.

Meanwhile, the fallback KNN retrieval pipeline (FAISS + Q-ranking, 10-50ms/request) runs on every request because the classifier was never production-validated.

#### Solution

Retrain the existing MLP with normalized labels and per-class confidence thresholds. The infrastructure is complete — this is a data quality + calibration improvement, not a new build.

##### Architecture (unchanged — already wired)

```
Request arrives
    |
[MLP classifier]  <1ms, ~200K params, numpy-only
    |
conf >= per-class threshold?
    |--- Yes --> route immediately (strategy: "classifier")
    |--- No  --> fall through to full MemRL pipeline (10-50ms)
                    |
              [Episodic KNN + Q-ranking + risk gate]
                    |
              Log (embedding, decision, outcome) --> write-only append
                    |
              Periodic retrain --> updated weights file
```

##### Key Insight: Episodic Memory Becomes Write-Only

Once the MLP handles the common case, episodic memory shifts from **runtime query target** (expensive FAISS lookup per request) to **write-only append log** (cheap INSERT). It becomes an experience replay buffer for retraining, not an inference engine. The full retrieval pipeline only fires on MLP fallthrough.

---

#### Decision Surfaces

##### Phase 1 (current): Role selection only

| Surface | Choices | Training data |
|---------|---------|---------------|
| **Role selection** | 5 classes (frontdoor, architect_general, architect_coding, coder_escalation, worker_explore) | 174K normalized episodic memories |

##### Future phases: Additional surfaces (independent models)

| Surface | Choices | Training data | Status |
|---------|---------|---------------|--------|
| Mode selection | direct vs repl | Action field encodes mode | Data exists, needs extraction |
| Escalation prediction | Binary (will frontdoor fail?) | 10,528 positive + 56,457 negative (frozen 2026-04-15 snapshot) — **live db 2026-07-27: 54,960 routing rows, per-role 22-33% failure** | **PROBED 2026-07-27 — see below; result PROVISIONAL** |
| Context injection budget | Continuous (0-2000 tokens) | SkillBank effectiveness_score | Needs collection |
| Multi-turn budget | Integer (1-10 REPL turns) | Session turn counts | Needs extraction |

**Excluded**: Speculative decoding parameters (hardware-bound, not task-dependent).

**Architecture decision**: Independent models per surface, not shared trunk. Routing has 174K clean labels; other surfaces have 10K or less. Don't risk degrading the best-data task with noisy co-training. Merge to multi-task only after all surfaces have abundant data + experiment confirms no routing accuracy regression.

---

#### Escalation-prediction probe — 2026-07-27 (PROVISIONAL, adversarial verification pending)

Built and run: `scripts/analysis/escalation_prediction_probe.py`. Report:
`orchestration/reports/escalation_prediction_probe/escalation_prediction_probe.json`.

**Zero inference.** The 1024-d BGE vectors already exist in `sessions/embeddings.faiss`; the probe
reads a read-only snapshot. Runnable without a clean inference window — this is why it was picked up
while E1/E3 stay blocked. Ran pinned to 8 cores at `nice -n 19`, 179 MB of vectors, ~20 s.

**Freeze compliance.** This handoff is FROZEN for expansion per fable5-findings-02. Building and
MEASURING a probe is allowed — COMP_r was completed 2026-07-22 under the same freeze — but PROMOTING
one is not. Any positive result here is RECOMMEND-only. Nothing has been wired.

##### Tasks

- [x] EP-1 — Build the probe with mandatory grouped splits, a shuffled-label control, and a
      pre-declared decision gate (NULL <=0.55 / SIGNAL >=0.65). ✅ 2026-07-27
- [x] EP-2 — Run against live data (54,960 routing rows with an outcome + embedding). ✅ 2026-07-27
- [x] EP-3 — **Adversarial verification COMPLETE — the result is REFUTED.** ✅ 2026-07-27.
      3 of 6 attacks refute it. See *EP-3 refutation* below. **Do not cite the 0.726.**
- [x] EP-4 — **Verdict: N17's conditional-depth surface is UNSUPPORTED by this probe.** ✅ 2026-07-27.
      The honest number is the within-suite AUC (worker_general `0.5521 ± 0.038`, frontdoor
      `0.5204 ± 0.037`) — on the NULL side of the pre-declared 0.55 gate. Recorded here rather than
      edited into N17, whose owner should pick it up.
- [ ] EP-5 — **Re-run the probe only after the `outcome` label defects below are fixed.** The current
  - 2026-11-09 audit: SV + UNDERSPECIFIED. The EPD-1 fix landed forward-only (orch `24b43990`, 2026-09-23). State the input: either rows written after that commit, or the post-EPD-1b backfill. Post-v11 the store is re-embedded (EPD-3 fold), so run the probe on EG2@256 vectors after the re-embed, not on BGE now. Zero inference once the input is chosen.
      label cannot support this question; a repeat on the same label would reproduce the same
      artifact.

##### ⚠️ REFUTED numbers (retained so nobody re-derives them) — group-weighted AUC, GroupShuffleSplit x5

| role | group-weighted | row-weighted (misleading) | base rate | n | groups |
|---|---|---|---|---|---|
| worker_general | **0.726 +/- 0.022** | 0.579 | 33.0% | 6,596 | 2,334 |
| ingest_long_context | **0.674 +/- 0.013** | 0.581 | 25.1% | 6,040 | 1,999 |
| coder_escalation | **0.648 +/- 0.010** | 0.637 | 24.2% | 6,764 | 2,171 |
| architect_general | 0.626 +/- 0.020 | 0.547 | 25.7% | 6,327 | 2,101 |
| **frontdoor** | **0.575 +/- 0.032** | 0.784 | 22.2% | 26,995 | 2,384 |

Shuffled-label controls all 0.49-0.52. `worker_vision` skipped (4 positives, not evaluable).

**These numbers are exactly reproducible and mean nothing about task difficulty.** They survived
near-duplicate merging and a time-ordered split, and the shuffled controls are clean — the harness
arithmetic is correct. What it decodes is the benchmark suite and the writer pipeline, not the task.
See below.

##### EP-3 refutation (independent adversarial verification, 2026-07-27)

Six attacks; **3 refute**. Attack scripts under `/mnt/raid0/llm/tmp/esc_refute/` (read-only; the repo
was never written to).

| # | Attack | Verdict |
|---|---|---|
| 1 | Near-duplicate leakage across sha1 groups | SURVIVED — merging at cos>=0.99 *raises* AUC |
| 2 | Temporal leakage (time-ordered split) | SURVIVED as posed — but the time axis is confounded with the writer path |
| 3 | Trivial surface features | **REFUTED** |
| 4 | Metric artifact / continuous rate | **REFUTED** |
| 5 | Does `outcome` mean what we think | **REFUTED** |
| 6 | Sanity of controls | SURVIVED — controls are sound |

**Attack 3 — a 13-feature length/format model beats the 1024-d embedding on 4 of 5 roles**, and the
embedding adds nothing on top of it (`emb+triv` <= `TRIVIAL` on three roles, within noise on the
rest). Trivial features: char length, word count, newline count, code-fence and URL flags, digit and
uppercase counts, punctuation counts. The "semantic decodability" framing is hollow — the ceiling is
prompt length and format statistics.

| role | BGE 1024-d | trivial-13 | emb+triv |
|---|---|---|---|
| worker_general | 0.7262 | 0.6840 | 0.6861 |
| ingest_long_context | 0.6736 | **0.7332** | 0.6837 |
| coder_escalation | 0.6480 | **0.7318** | 0.6485 |
| architect_general | 0.6262 | **0.6748** | 0.6191 |
| frontdoor | 0.5750 | **0.6178** | 0.6228 |

**Attack 4 — the headline lives entirely in objectives seen exactly once.** 74-82% of test groups are
size 1. On objectives observed more than once — the only ones where a failure *rate* is even a rate —
all four "signal" roles collapse to chance (0.47-0.53), and `worker_general` drops to **0.411** at
size>=3. Spearman against the continuous rate *inverts* the role ranking. Root cause: per-objective
failure rate has split-half reliability of **-0.04 to 0.43**; there is no stable propensity to decode.

**Attack 5 — `outcome` is a benchmark-suite detector, not a difficulty signal.** Suite x task_type
identity alone, with no embedding, beats the embedding on all five roles (0.727-0.804). Within
(suite x task_type) strata the embedding collapses:

| role | all-strata | **within-suite** |
|---|---|---|
| worker_general | 0.6926 | **0.5521** |
| ingest_long_context | 0.6654 | **0.5822** |
| coder_escalation | 0.6362 | **0.5250** |
| architect_general | 0.6350 | **0.5669** |
| frontdoor | 0.6104 | **0.5204** |

Three of five land at or below the probe's own pre-declared NULL gate of 0.55. Failure is a property
of the grader: `simpleqa_general` 0.711-0.930 fail vs `mbpp` 0.017-0.068. And single templates
dominate — `worker_general`'s largest vector group is a 497-row *"You are a physics answer
equivalence judge…"* prompt at **81.1%** failure; `frontdoor` carries a 2,335-row *"Return executable
Python only"* template at **97.1%**.



##### Three methodology errors caught during the run — each inverted the result

Recorded because they generalize to any probe over this store:

1. **Grouping by a hash of `context` is wrong.** 26,995 frontdoor rows carry only **2,384 distinct
   vectors** (~11x reuse) and 497 vector-hashes span multiple context-derived groups, so identical
   points land in train AND test. The `context` column holds material beyond the embedded objective.
   **Group by the embedding itself.** 2,384 is the same figure `comp_region_probe.py` warns about.
2. **`GroupKFold` is deterministic** — a "multi-seed stability check" over it reported a spread of
   exactly `0.0000`, a no-op masquerading as a control. Use `GroupShuffleSplit`.
3. **Row-weighted pooling is carried by a handful of objectives.** Top-10 groups hold **33%** of
   frontdoor rows while the **median group size is 1**. Report group-weighted (one point per distinct
   objective) as the headline; row-weighted flatters.


#### 🔴 EP-3 fallout: three VERIFIED defects in the `outcome` label (cross-cutting)

The refutation's most valuable output is not the null — it is what the null exposed. These affect
**every consumer of `memories.outcome`**, not just this probe: MemRL reward shaping, Q-values, the
routing classifier's own training labels, and skill-bank effectiveness.

- [~] **EPD-1 — CONFIRMED but reclassified 2026-07-27: correct semantics, not a bug.**
      `outcome` is indeed written once at INSERT and never updated. But a consumer audit found
      **nothing in the live read path consumes it** — `retriever.py` contains the string `outcome`
      zero times in 951 lines, and there is no SQL `WHERE` on the column anywhere in the repo. Live
      routing ranks on `q_value` + cosine + cost, and `q_value` updates correctly (TD(0) reproduced
      bit-exactly for the 5 highest-`update_count` rows). First-observation semantics is therefore
      the right reading; rewriting it would silently redefine a historical field. **The genuinely
      broken sibling was `update_count`** — see below — which DOES feed a live gate. Retained as
      context; original text follows.
  - [x] EPD-1-orig — `outcome` is written once at INSERT and NEVER updated. Verified directly:
        ✅ 2026-09-23 — epyc-orchestrator `24b43990`: `update_q_value` re-derives `outcome` from the updated Q (success iff Q>0.5) on every update; INSERT mapping shared. No backfill (live store; SQL shape in the commit).
      `orchestration/repl_memory/episodic_store.py:723-725` is
      `UPDATE memories SET q_value = ?, updated_at = ?, update_count = ? WHERE id = ?` — `outcome`
      is absent from the SET clause, while the INSERT at `:435` writes it once.
      Measured impact on the live store: **max `update_count` = 7,888**, mean `20.3`, and **2,792 of
      54,960 rows have >10 updates**. Every one of those rows still carries the sign of
      *observation #1* while its `q_value` has been refined thousands of times. Decide: update
      `outcome` alongside `q_value`, or formally demote `outcome` to "first-observation sign" and
      stop treating it as a label.
  - [ ] EPD-1b — **(operator-gated, live store)** backfill historical labels: `UPDATE memories SET outcome = CASE WHEN q_value > 0.5 THEN 'success' ELSE 'failure' END WHERE update_count > 0`. Until then rows never updated again keep their first-observation label; EP-5 should filter to rows updated after 24b43990 or run after the backfill.
    - 2026-11-09 audit: SV, operator-gated live store. The SQL threshold `q_value > 0.5` spans two reward eras (E9 and E18, duration axis from 2026-09-24), so one cut mislabels pre-E18 rows; split by era or recompute from the progress logs before applying. Not an Autopilot dependency.
- [~] **EPD-2 — OVERSTATED, largely withdrawn 2026-07-27.** The original claim was that `failure`
      conflates errors with cost penalties on correct answers (`reward <= 0 -> failure`, with reward
      carrying latency / escalation −0.15 / delegation-misattribution −0.10 penalties). Adversarial
      verification measured the actual reach: it explains **~4.3%** of live-traffic failure labels
      (207 of 4,822), not a dominant share. And the related `reward == 0.0 -> failure` is **correct
      behaviour, not a bug** — `seeding_rewards.py:452-468` defines
      `success_reward(passed) = 1.0 if passed else 0.0`, and genuine no-signal cases are dropped one
      branch earlier as `INFRA_SKIP` (`seeding_eval.py:1268-1279`). The q_value histogram confirms
      the binary encoding: the never-updated external population is 98.2% concentrated on exactly
      {1.0, 0.5}. **`outcome='failure'` on those rows is the right label.** No action; retained so the
      claim is not re-derived.
- [ ] **EPD-3 — the embedding index mixes >=3 text conventions, so the vector leaks the writer path.**
      Observed conventions: `"type:{t} | objective:{o[:200]} | priority:{p}"`,
      `"type:chat | objective:{p[:200]}"`, and raw <=450-char text from
      `scripts/maintenance/repair_episodic_embeddings.py`'s FAISS rebuild. Consequence: a probe can
      read the writer path straight off the vector at **ROW-AUC 0.906 (worker_general) / 0.940
      (frontdoor)**, and the two writer paths have failure rates differing by up to **8x**
      (coder_escalation 0.037 vs 0.288). Any embedding-based model over this store is partly a
      pipeline classifier. Decide: re-embed under one convention, or partition by convention. Deployment constraint (absorbs EPD-3-R1, operator): the recipe change invalidates the 34,938 rows embedded with `priority`, so the code lands only inside an inference window that re-embeds the store in the same change; never land the code first.
  - 2026-11-09 OPERATOR DECISION: **EPD-3 is folded into the EG2 re-embed run, so the store is re-embedded exactly once.** The re-embed is the EmbeddingGemma-2 migration (`scripts/migration/reembed_stores_eg2.py`, orchestrator) owned by REPL-EMB-2.10 / UFH-12-PROD-ADOPT and the R1-R5 consumer-migration gate in `harness-program.md` (REPL-EMB-2.x; production adoption ships with the v11 promotion, operator 2026-11-02). The single canonical embedding text (drop `priority`, `embedding_text_for`; `memory_record.py` still emits `priority`) must therefore be in the code that run uses; EPD-3 closes when that run's post-verify shows one convention over the full store. No separate EPD-3 re-embed window, and no re-embed of the BGE store beforehand. Remaining EPD-3 work before the run: land the convention change in the same change as the run, never earlier (the existing deployment constraint above stands).
  - [x] **EPD-3-decision — DECIDED 2026-08-12: re-embed under one convention, with the convention
        CORRECTED to drop `priority`. Partition-by-writer-path is REJECTED.** ✅ 2026-08-12
    - **The stated cause is stale.** "The index mixes >=3 text conventions" was true when written and
      is not true now. `reseed_episodic_store.py` run `20260809T160329Z` rebuilt **63,786 / 63,786**
      rows from the single canonical builder `MemoryRecord.embedding_text()`
      (`already_on_contract: 63786`, ntotal=id_map=63,786, desync 0; receipt in
      `orchestration/repl_memory/sessions/`, narrative in `progress/2026-08/2026-08-09.md`). Only
      **233 rows (0.36%)** have been written since. So "re-embed under one convention" has already
      been EXECUTED — and the leak survived it. Re-running EPD-3 as written would burn an inference
      window and change nothing; a naive re-run of the probe would still show high AUC and be
      misread as "the reseed failed".
    - **The leak moved from the FORMAT to a FIELD VALUE.** Verified read-only against the live
      `episodic.db` (64,019 rows): `context.priority` takes exactly two values store-wide —
      `interactive` (34,938) and absent (29,081) — and splits the writer paths at **99.973%**
      purity: `interactive` ⟺ {`legacy` 30,719, `progress_log` 4,219}; absent ⟺ {`external` 28,124,
      `seed` 940}; 17 strays. The literal token `| priority:interactive` is therefore present in one
      pipeline's embedded text and absent from the other's, inside one format. `priority` is also
      **not observed** — `src/orchestration/task_ir.py:81` hard-codes the default `"interactive"` —
      so it carries ~zero task semantics and ~total writer-path identity. That is the definition of
      a field to remove from the embedded text.
    - **This is a LIVE retrieval defect, not only a training confound.** `canonicalize_task_ir`
      always emits `priority`, so **every** live routing query embeds a `priority:interactive`-shaped
      text while **45.4% of the corpus does not**. The two populations sit on systematically
      different manifolds today, at query time.
    - **Decision.** One convention, and the convention drops `priority` from the embedded text
      (keep it stored; it is telemetry, not task semantics). The `task_type` segment stays — unlike
      `priority` it carries real semantics; what is wrong there is `seeding_injection.py:65`
      hard-coding `type:chat`, which is a writer bug to fix, not a field to drop.
    - **REJECTED ALTERNATIVE — partition by writer path**, on five counts. (1) It *preserves* the
      defect and makes it a permanent schema fact, so every downstream model must stay
      partition-aware forever. (2) It costs corpus: a live (interactive-shaped) query would lose
      reach to 29,081 rows that [`episodic-memory-integrity.md`](memory-program.md)
      showed carry real decision signal (macro failure 0.1964 vs 0.2518 random / 0.1790 oracle =
      76% of achievable headroom, permutation p = 0.0025). (3) The de-confounding it buys is not
      established — the same file attacked the writer-path confound directly and the signal survived
      (partial correlation unchanged at −0.875). (4) It does not work as a cheap post-filter:
      `episodic_store.py:699` is a GLOBAL KNN with only `k*2` over-fetch and a SQLite post-filter, so
      a convention filter silently returns fewer than `k` whenever the query's partition is a
      minority of the top-2k. (5) A per-convention index is structural, not cheap:
      `FAISSEmbeddingStore` binds one (index, id_map) pair and the whole publish/desync/self-heal
      apparatus assumes exactly one. Dropping one field removes the leak at zero corpus cost.
  - [x] **EPD-3-R4 — the standing integrity gate measured against a string that was never embedded.
        FIXED ✅ 2026-08-12.** Found while gathering the evidence above.
        `scripts/maintenance/check_episodic_integrity.py` hand-built `type:{t} | objective:{o}` for
        its semantic self-match probe — no `priority:` segment — while the index was published from
        `record_from_legacy_context(ctx).embedding_text()`, which emits one. On 54.6% of rows the
        DECISIVE check was cosine-ing the stored vector against a different string, spending margin
        against its own 0.90 floor; it also read `objective` only, silently dropping
        `task_description`-keyed rows from the sample. Fixed by calling the publish function rather
        than re-spelling it. Real callers: `scripts/session/health_check.sh` (both repos),
        `autopilot.py` `_run_episodic_check`, `collect_multitier_incumbent_baseline.py`. Orchestrator
        `604c70bf`; `tests/unit/test_episodic_integrity_check.py` 11 -> 14, both mutations caught.
  - [x] **EPD-3-R2 — no live write site produces the canonical vector, so the convention re-drifts
        between reseeds by construction. FIXED ✅ 2026-09-14.** `embedder.py:243` `_serialize_task_ir`
        now delegates to the new `memory_record.embedding_text_for()` (a thin wrapper over
        `MemoryRecord.embedding_text()`), so every `embed_task_ir` caller — the live query path
        included — emits the canonical text: truthiness-keyed (no more literal `priority:None`),
        stripped, capped at `EMBED_TEXT_MAX_CHARS`, and without the `constraints:`/`input_types:`
        segments no other writer emits. `tests/unit/test_one_embedding_convention_writers.py` (26
        tests) supplies the `TestOneEmbeddingConvention` analogue this box asked for: goldens are the
        canonical text of four REAL store rows (`51aae08a`, `531f4890`, `80d975c1`, `a30ba0aa`), so
        the writers are pinned to the format the corpus was published with rather than to each other,
        plus a delegation guard that monkeypatches the builder and asserts each writer CALLS it.
        Orchestrator `9096a600`; `-k "embed or seed or routing"` 1113 -> 1139 passed, 9 pre-existing
        `test_e8_quality_baseline_reseed` failures unchanged; mutation-checked (restoring
        `or "chat"` fails 3 tests).
  - [x] **EPD-3-R3 — two live writers still use foreign conventions. FIXED ✅ 2026-09-14.**
        `scripts/benchmark/seeding_injection.py:65` `_precompute_embedding` takes the row's own
        `task_type` (both call sites pass the suite) and builds the text via
        `memory_record.embedding_text_for`, defaulting to `chat` exactly as
        `q_scorer.score_external_result` does — the hard-coded `type:chat` mislabelled every non-chat
        suite's vector (3,795 `math` / 3,787 `hotpotqa` / 3,585 `coder` rows in the live store).
        `orchestration/repl_memory/seed_loader.py:470` now embeds `record.embedding_text()` instead
        of the bare task string. The 200-char truncation stays at the injection call site because the
        payload's `task_description` is what gets stored. Orchestrator `9096a600`; golden rows
        `531f4890` (math injection) and `80d975c1`/`a30ba0aa` (seed rows) pin both.
  - **[declined: ws58 2026-11-03 content-review: merged into EPD-3 as its deployment constraint]** **OPERATOR: EPD-3-R1 — the recipe change needs an inference window, and must NOT land before
        one.** Dropping `priority` from `embedding_text()` invalidates the 34,938 rows embedded with
        it, so landing the code first would make live queries mismatch 100% of the store instead of
        today's 45.4%. The re-embed and the recipe must flip together. Cost is measured, not
        estimated: the 2026-08-09 run did 63,786 rows at **151.8 rows/s** in **~15 min end-to-end**
        (vs ~74 min for the 2026-07-27 run at 58,281 rows), on a temporary fleet of 6 BGE processes
        pinned across all 96 cores. The tool already fails closed —
        `reseed_episodic_store.py:473` refuses without `--i-understand-this-re-embeds`. Sequence
        when the window is granted: land R2+R3 -> drop `priority` from the builder -> reseed ->
        re-run the EP-3 probe to confirm the writer-path AUC actually collapses.
  - [x] **EPD-3-R5 — kill or annotate the deprecated copy of the hard-coded
        `type:chat | objective:{task_description[:200]}` convention**, since a deprecated tree is still the copy
        a future author greps and cargo-cults (`scripts/benchmark/deprecated/seed_specialist_routing_v1.py:1501`)
        (found 2026-09-14, noninf sweep).
        ✅ 2026-09-17 — orchestrator `d3f6062c` (on `origin/main`): ANNOTATED, not killed (docs and the
        `question_pool` shadow-copy cleanup still reference the file). The site (`:1500-1507`) now carries an
        `EPD-3-R5` do-not-copy block pointing at `embedding_text_for`; `tests/unit/test_epd3_r5_r6_r8.py`
        fails if any `objective:{` f-string under a `deprecated/` tree lacks the marker.
        **2026-10-24 candidate update:** `refactor/scripts-cleanup-reviewed-01a16fc3` removes the deprecated orchestrator v1 tree and its dependent marker checks after consumer review. The annotation above remains the historical 2026-09-17 remedy; no canonical-tree deletion or deployment is claimed here.
  - [x] **EPD-3-R6 — make the seed write loop fail closed**: it catches every `Exception` and only prints, so a
        total embed failure reports `loaded: 0, failed: N` and still exits 0 even though the tests now assert
        `failed == 0` (`orchestration/repl_memory/seed_loader.py:~495`) (found 2026-09-14, noninf sweep).
        ✅ 2026-09-17 — orchestrator `d3f6062c`: the loop still records-and-continues (one run names every bad
        row) and flushes what loaded, then raises `SeedLoadError` (stats + `failures` list); the CLI exits 1 with
        `SEEDING FAILED`. Tests: total outage, partial failure (flush-then-raise), clean run, CLI exit code.
  - [x] **EPD-3-R7 — decide the fate of the 200-char objective truncation at the payload level**, i.e. the ✅ 2026-10-31 — orchestrator implementation `9c388042475d835f88e62355443e7036986b9a34`; `tests/unit/test_seeding_injection_objective_storage.py` and Git capsule `artifacts/audit/epd3-r7-objective-payload-20261031/verification.md`; 68 focused tests pass. Both reward writers store the full objective and use the unchanged canonical 2,000-character embedding-text bound; historical truncated records are not expanded. [no-belief: software source publication and regression verification]
        2026-07-27 audit's defect #2 (12.6% of rows at the cap, 96.9% objective collision) still live on the
        eval-injection path, where changing it changes what is *stored* and not only what is embedded
        (`scripts/benchmark/seeding_injection.py:189,287`) (found 2026-09-14, noninf sweep).
  - [x] **EPD-3-R8 — route the three remaining unguarded convention builders through the shared builder**
        (`_serialize_failure_context:279`, `_serialize_exploration:299`, `_serialize_classification_prompt:305`)
        — single-writer today so no drift yet, but the same shape EPD-3-R2/R3 just fixed
        (`orchestration/repl_memory/embedder.py`) (found 2026-09-14, noninf sweep).
        ✅ 2026-09-17 — orchestrator `d3f6062c`: new `memory_record.join_embedding_segments` is the one
        `key:value | …` assembler (None drops a segment, `""` keeps a mandatory one, cap `EMBED_TEXT_MAX_CHARS`);
        `MemoryRecord.embedding_text` and all three serializers call it. Output byte-identical to the old
        serializers on goldens and a 3,000-case randomized differential (only texts >2,000 chars differ, now cut
        at the shared cap; unreachable for real failure contexts), except a present-but-`None` failure key no
        longer embeds the literal `None`. Spy tests assert the CALL, plus a scan forbidding hand-joined segments in
        `embedder.py`. No re-embed needed (R1 untouched).

**Why this is the real result — REVISED 2026-07-27.** The probe asked "is failure decodable?" and
got 0.726, which was refuted. The follow-up audit then established that EPD-1 and EPD-2 are much
smaller than stated (see the strikethroughs above): `outcome` feeds nothing live, and the cost-penalty
conflation reaches ~4.3% of labels. **The defect that actually mattered was EPD-3's cousin — the
FAISS/id_map desync**, which corrupted vector resolution store-wide from 2026-07-05 and is now fixed
and repaired. See [`episodic-memory-integrity.md`](memory-program.md). EP-5 (re-run) should
wait for the reseed there, not for a label fix. Cross-reference: this may be a second mechanical contributor to the five-null
learned-routing streak alongside the constant-reward bug fixed 2026-07-21 (master-index N16).


#### Training Data

##### Action Label Normalization

The episodic store has ~30 distinct action strings. Mapping to 5 clean classes:

| Raw action | Count | Map to | Rationale |
|---|---|---|---|
| `frontdoor` | 70,060 | **frontdoor** | Clean organic data |
| `architect_general` | 41,624 | **architect_general** | Clean organic data |
| `architect_coding` | 36,710 | **architect_coding** | Clean organic data |
| `escalate:frontdoor->coder_escalation` | 10,528 | **coder_escalation** | Destination = correct initial route. 91% failure at frontdoor = high-conviction signal |
| `WORKER` | 7,497 | **worker_explore** | Seeding data, 88% task_type=chat |
| `SELF` | 2,066 | **frontdoor** | SELF = frontdoor handles it. 100% failure — negative signal |
| `ARCHITECT` | 2,034 | **architect_general** | Seeding data, spread across task types |
| `SELF:direct` | 1,893 | **frontdoor** | Includes mode annotation |
| `SELF:repl` | 1,552 | **frontdoor** | Includes mode annotation |
| `escalate:coder->architect` | 16 | **architect_coding** | Destination = correct route |

**Excluded** (2,250 memories): `<empty>` (2,138 "Hello" probes), `frontdoor:repl/direct/react` (17 seeded), `persona:*` (15 seeded), code snippet exemplars (~80).

**Post-normalization distribution:**

| Class | Count | % |
|---|---|---|
| frontdoor | 75,571 | 43% |
| architect_general | 43,658 | 25% |
| architect_coding | 36,726 | 21% |
| coder_escalation | 10,528 | 6% |
| worker_explore | 7,497 | 4% |
| **Total** | **173,980** | |

3 zero-data classes (worker_math, worker_vision, ingest_long_context) deferred — MLP uses 8 output neurons but unused classes receive no gradient until data exists.

---

#### Implementation Plan

##### Phase 1: Retrain with Normalized Labels

- [x] **P1.1** Update `extract_training_data.py` with label normalization mapping — DONE 2026-04-15
- [x] **P1.2** Re-embed 157K memories via 8 parallel BGE servers (17 min) — DONE 2026-04-15
- [x] **P1.3** Run extraction + training — **92.0% val accuracy** (4 classes, 157K samples) — DONE 2026-04-15
- [x] **P1.4** Add per-class confidence thresholds + calibration (precision >= 0.9) — DONE 2026-04-15

**Training results (2026-04-15):**

| Class | Val Accuracy | Val Samples | Calibrated Threshold |
|-------|-------------|-------------|---------------------|
| frontdoor | 91.5% | 14,459 | 0.447 |
| architect_general | 95.1% | 8,406 | 0.362 |
| architect_coding | 95.7% | 7,342 | 0.560 |
| worker_explore | 56.7% | 1,297 | 0.806 |
| coder_escalation | — | 0 (no objectives) | 0.950 (default) |

**Note**: coder_escalation (10K entries) excluded from training — all escalation memories have empty objective fields (logged at escalation time, not initial routing). Worker_explore accuracy is low (56.7%) because seeding data was 88% task_type=chat with low Q-values, making it look like frontdoor. Both gaps will improve as organic data with proper objectives accumulates.

- [x] **P1.5** Enable `ORCHESTRATOR_ROUTING_CLASSIFIER=1` in `orchestrator_stack.py` — DONE 2026-04-15. Takes effect on next API restart.
- [x] **P1.6** Add extraction step to autopilot `structural_lab.py` before classifier training — DONE 2026-04-15

##### Phase 1.5: Logit-Based Probe (No llama.cpp changes)

Validate "piggyback on frontdoor" concept before investing in hidden-state extraction.

- [x] **P1.5.1** Instrument frontdoor to log top-k=64 first-token log-probabilities — DONE 2026-04-17, re-verified 2026-07-03. `src/backends/llama_server.py` adds `n_probs=64` only for `frontdoor` when `ORCHESTRATOR_LOGIT_PROBE=1`, and `_write_logit_probe()` appends hashed prompt metadata plus first-token top-k probabilities to `data/logit_probe.jsonl`. 2026-07-03 coverage pins the default-off feature flag/env gate, frontdoor-only payload behavior, sanitized JSONL writes, and runtime-flag-isolated feature registry defaults.
- [ ] **P1.5.2** Collect over ~1000+ requests — FROZEN under the 2026-06-12 routing-expansion guard. Reopen only after a current-traffic DAR-1 replay shows >=5% identifiable routing regret and N2 per-question vectors exist; then enable `ORCHESTRATOR_LOGIT_PROBE=1` in a coordinated collection window. Absorbs P1.5.3/P1.5.4: on reopening, train the 512-param linear probe and report per-role AUROC + ECE against TF-IDF/length and BGE+MLP baselines; >= 80% opens a hidden-state probe (refile from the freeze-exit annotation: an off-stack decoupled encoder, since /hidden-states is not in v10), < 60% keeps BGE+MLP.
  - 2026-11-09 audit: STALE-PREMISE. The >=5% gate is declared definitionally ~0 under the current metric (see the OPERATOR DECISION on regret meaning); the `BGE+MLP` comparison baseline is retired by EG2; `/hidden-states` is not in v10; `ORCHESTRATOR_LOGIT_PROBE` is referenced only in an analysis script. Reframe or retire after the regret ruling; per the research-intake rule, ask the operator before declining. Decision needed: (a) reframe as an EG2-era probe after RTG-RETRAIN-1, (b) retire. Recommendation: (a) deferred, it costs nothing to keep frozen.
  - 2026-11-09 EG2 boundary (RTG-EG2-1): the probe baselines named here (`BGE+MLP`, TF-IDF) are retired by EG2; the comparison baseline must be rebuilt on EG2@256 (routing classifier retrain, RTG-RETRAIN-1) before any AUROC/ECE claim. Gate wording is still unresolved under the regret ruling (see the OPERATOR DECISION box on regret meaning).
- **[declined: ws58 2026-11-03 content-review: merged into P1.5.2]** **P1.5.3** Train linear probe (512 params), evaluate accuracy — gated by P1.5.2 collection.
- **[declined: ws58 2026-11-03 content-review: merged into P1.5.2 as its decision gate]** **P1.5.4** Decision gate: >= 80% → proceed to Phase 2; < 60% → stay with BGE+MLP — gated by P1.5.3.
  - *Freeze annotation 2026-09-23 (intake-1522; not an unfreeze):* when reopened, restate this and P2.6 as per-role AUROC
    + ECE against TF-IDF/length and BGE+MLP baselines, with a (layer, position) sweep — accuracy thresholds hide
    surface-feature wins.

##### Phase 2: Hidden State Probe (llama.cpp fork changes required)

**SSM hybrid awareness**: Frontdoor is Jamba-style (Mamba SSM + attention). Probe attention layers only. Mean-pool across all token positions (SSM last-token state is recency-biased).

- [x] **P2.1** Enumerate attention layer indices — DONE 2026-04-15. Qwen3.5-35B-A3B: 41 layers, attention at 0,4,8,12,16,20,24,28,32,36,40 (11 layers), hidden_dim=2048
- [x] **P2.2** Add `/hidden-states` endpoint to llama.cpp-experimental — DONE 2026-04-15. Commit `4c7fe20c6`. Graph capture + context mean-pooling + C API + server endpoint.
- **[declined: ws58 2026-11-03 content-review: conditional on P1.5.4 >= 80%, which is frozen; /hidden-states is not in v10 and the freeze-exit note names a different substrate — refile from P1.5.2 if it ever passes]** **P2.3** Collect mean-pooled hidden states at each attention layer during inference (needs live server test)
- **[declined: ws58 2026-11-03 content-review: same chain as P2.3]** **P2.4** Train independent linear probes per attention layer — find best
- **[declined: ws58 2026-11-03 content-review: same chain as P2.3]** **P2.5** If complementary, use learned attention pooling (N learnable weights)
- **[declined: ws58 2026-11-03 content-review: same chain as P2.3; its freeze-exit annotation is now carried by P1.5.2]** **P2.6** Decision gate: >= 90% → Phase 3; < 80% → stay with BGE+MLP
  - *Freeze-exit annotation 2026-09-23 (intake-1526; not an unfreeze):* alternative substrate when reopened — an off-stack
    decoupled encoder, since `/hidden-states` is not in v10. Gate it on per-role AUC + ECE on the incumbent-disagreement
    subset vs BGE+MLP. Published encoders are 20B-122B and the headline savings are frontier-pool-only.

##### Phase 3: BGE Elimination (Conditional on Phase 2)

- **[declined: ws58 2026-11-03 content-review: conditional on Phase 2, retired above]** **P3.1** Replace BGE embedding with hidden-state features in MLP input
- **[declined: ws58 2026-11-03 content-review: conditional on Phase 2, retired above]** **P3.2** Remove BGE model from inference path (~300MB RAM, ~5-10ms/request saved)
- **[declined: ws58 2026-11-03 content-review: conditional on Phase 2, retired above]** **P3.3** Update episodic store schema (hidden states instead of BGE embeddings)

##### Phase 4: Trinity-Derived Methodology Audits (NEW 2026-04-26)

Source: deep-dive [`research/deep-dives/trinity-evolved-llm-coordinator-methodology.md`](../../research/deep-dives/trinity-evolved-llm-coordinator-methodology.md) on Trinity (intake-474, ICLR 2026, Sakana AI). Trinity is the most direct prior art for this handoff's thesis. These four tasks are the *portable methodology lessons* — they apply regardless of whether we end up adopting their full architecture.

Order tasks by cost: P4.1 is cheapest (audit only), P4.4 is most expensive (overnight ES run). Each phase's go/no-go feeds the next.

- [/] **P4.1** **Feature-extraction position audit** — **Phase A (audit) DONE 2026-05-07; Phase B (experiment) deferred pending FAISS rebuild + per-run inference approval.**

  **Phase A audit findings (analytical, no code):**

  1. **Current pool method confirmed as CLS** (not mean-pool). Per `epyc-orchestrator/scripts/server/orchestrator_stack.py:862`: BGE-large-en-v1.5 launches with `--pooling cls`. Comment in source: "BGE uses CLS token pooling (standard BERT)". This is the BGE-trained pool method (BGE was distilled with [CLS] as the pooled output) — switching to mean-pool or last-layer would diverge from the training distribution.
  2. **Data-scale finding: handoff text says 174K labels, actual on-disk state is ~8K memories.** Production episodic.db at `/mnt/raid0/llm/epyc-orchestrator/orchestration/repl_memory/sessions/episodic.db` has 8,115 rows *(historical audit snapshot; 64,396 routing rows live on 2026-09-26)* (135 MB file size is bloat from prior larger state + FTS). The 174K figure was aspirational from a previous epoch; current routing-classifier training would draw from 8K, not 174K. With 8K labels, binomial 95% CI half-width on per-arm val-acc is ~3-4 pp depending on val split — borderline for the ≥1 pp decision-gate.
  3. **FAISS index is currently RESET.** `embeddings.faiss` is 385 KB (current) vs `.bak` 32 MB (Apr 28 snapshot). The live FAISS holds essentially no embeddings. Backup `.bak` files contain ~9.2K embeddings consistent with the DB row count.
  4. **Implication for Phase B**: a real ablation requires (i) rebuilding FAISS from DB (≈40s of BGE inference), (ii) running BGE again for each alternative pool (`--pooling mean`, `--pooling last`) to produce 2 more 8K × 1024-dim matrices. Total inference: 3 × ~40s + 3 × startup ≈ 5 min wall-clock. Plus 3 head retrains (seconds, CPU-bound). The full ablation is cheap, but does require crossing the inference threshold.
  5. **Trinity transfer caveat (re-emphasised)**: Trinity's penultimate-vs-final-token result is decoder-specific. BGE is a bidirectional encoder — its pool methods have different theoretical implications. Trinity's 10-point swing should NOT be expected here. The decision gate of ≥1 pp is appropriate (smaller expected effect size on encoder).

  **Phase B (deferred — explicit per-run inference approval required, per `feedback_no_concurrent_inference`):**

  ```bash
  # Step 1: rebuild FAISS index from live episodic.db (uses current --pooling cls)
  python3 scripts/graph_router/extract_training_data.py
    --output orchestration/repl_memory/training_data_cls.npz

  # Step 2: re-launch BGE with mean pooling
  pkill -f 'llama-server.*bge'  # tear down current cls server
  OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active OMP_NUM_THREADS=16 \
    /mnt/raid0/llm/llama.cpp/build/bin/llama-server \
      --model /mnt/raid0/llm/models/bge-large-en-v1.5-f16.gguf \
      --port 8090 --host 127.0.0.1 --threads 16 \
      --embedding --pooling mean &
  python3 scripts/graph_router/extract_training_data.py
    --output orchestration/repl_memory/training_data_mean.npz

  # Step 3: re-launch BGE with last-token pooling
  pkill -f 'llama-server.*bge'
  /mnt/raid0/llm/llama.cpp/build/bin/llama-server \
    ... --pooling last &
  python3 scripts/graph_router/extract_training_data.py
    --output orchestration/repl_memory/training_data_last.npz

  # Step 4: train 3 heads with identical hyperparameters
  for variant in cls mean last; do
    python3 scripts/graph_router/train_routing_classifier.py \
      --data orchestration/repl_memory/training_data_${variant}.npz \
      --output orchestration/repl_memory/routing_classifier_weights_${variant}.npz
  done

  # Step 5: compare val acc across variants
  python3 scripts/graph_router/ab_test_classifier.py
    --weights orchestration/repl_memory/routing_classifier_weights_*.npz
  ```

  **Decision gate (when Phase B runs)**: best pool method becomes default if Δ val-acc ≥ 1 pp vs CLS baseline AND 95% CI rules out the null. With n=8K, this requires |Δ| ≥ ~4 pp for statistical confidence (half-width is sample-size-bounded, not protocol-bounded). If no variant moves the needle ≥4 pp, mark feature-position as solved (CLS stays default) and move on. If a variant wins, switch default in `orchestrator_stack.py:862` and document.

  **Recommended sequencing**: bundle Phase B with P4.1.3 (IRT-feature variant) into a single inference run — same BGE invocations, +1 head retrain. Total wall-clock for combined P4.1 + P4.1.3 ≈ 10-15 min once authorized.
- [x] **P4.1.3** **IRT-feature audit (intake-496 LLM Bandit)** — **COMPLETE 2026-06-27; label-proxy positive, cached observed-outcome null.** Orchestrator adds `scripts/graph_router/irt_feature_ablation.py`, an evidence-only diagnostic that fits train-split IRT difficulty/discrimination targets from the existing label-proxy matrix, projects those two scores from the BGE embedding columns, appends them to the routing features, and trains the same numpy `RoutingClassifier` head without writing production weights. The 80K-row run in `orchestration/reports/p413_irt_feature_ablation/report_20260627_sample80k.json` used `64K` train / `16K` validation rows from the current `275,960`-row `training_data.npz`: baseline `1031`-feature head reached `69.20%` validation accuracy, while the IRT-augmented `1033`-feature head reached `78.22%` (`+9.02pp`, gate threshold `+1pp`). The follow-up cached observed-outcome diagnostic in `scripts/graph_router/observed_irt_feature_ablation.py` wrote `orchestration/reports/p413_observed_irt_feature_ablation/report_20260627_cached_p45.json` from the P4.5 soft-label embedding artifact (`540` qids, `710` observed role cells): baseline role-success accuracy was `53.70%`, observed-IRT role-success accuracy was also `53.70%` (`0.00pp`), with worse argmax match (`77.78%` vs `78.70%`). **Decision**: do not escalate observed IRT features from the cached outcome matrix. Treat the label-proxy lift as a lead for a future promotion-grade prompt×action outcome dataset only, not as deployable routing evidence.
- [x] **P4.2** **Block-ε-separability diagnostic (medium cost)** — **COMPLETE 2026-06-27, NULL FOR BLOCK-SEPARABILITY / FULL-RANK DOMINATES**. Trinity's optimizer-choice argument rests on the loss surface being block-ε-separable (formal Hessian-based definition; their empirical evidence is a "block-diagonal-10" head retaining competitive performance). Orchestrator `60c0b784` adds `scripts/graph_router/block_separability_diagnostic.py` plus focused tests and writes `/mnt/raid0/llm/epyc-orchestrator/orchestration/reports/p42_block_separability/report_20260627_sample80k.json`. The 80K-row offline diagnostic used a fixed 64K/16K train/val split from `orchestration/repl_memory/training_data.npz`: majority baseline `49.33%`, full-rank `81.09%`, block-10 `56.55%`, diagonal `49.33%`. Result: block-10 is `-24.54pp` vs full, so the routing-label geometry does **not** match Trinity's block-separable assumption for this surface. **Decision**: DAR-4 should prefer full-rank/shared structure, not rank-restriction as a default mitigation; P4.4 sep-CMA-ES is no longer justified by P4.2 and should remain gated to a future true cold-start/no-label surface rather than this trained-label classifier.
- **[declined: ws58 2026-11-03 content-review: backbone fine-tuning research, artifact/env-blocked by its own text, with no routing decision attached]** **P4.3** **SVD-scale fine-tuning trial (medium cost; currently artifact/env-blocked for the true experiment)**: Trinity uses singular-value FT on the backbone — learn only singular-value scales, keep orthogonal matrices fixed (~9K extra params). Their ablation: removing SVD-FT costs −3 to −4 points across all four benchmarks. This is a parameter-efficient adaptation cheaper than LoRA and applicable to whatever backbone we use as the routing-head feature extractor. **2026-06-27 feasibility checks**: the live feature extractor is `bge-large-en-v1.5-f16.gguf`, served through llama-server `/embedding`, and both orchestrator/research registry state point to that GGUF. No local trainable `BAAI/bge-large-en-v1.5` HF checkpoint was found, only GGUF/HF download metadata. The only local trainable BGE-family checkpoint is `/mnt/raid0/llm/hf/BAAI_bge-m3`, with `pytorch_model.bin`, tokenizer files, `colbert_linear.pt`, and `sparse_linear.pt`, but using it would change the extractor and would not answer the original BGE-large last-block SVD-FT question. Available envs are partial (`torch+transformers+safetensors` in `/mnt/raid0/llm/tmp/a9-neuraltxt-cpu-venv` and `/mnt/raid0/llm/comfyui-ernie-test/ComfyUI/.venv`; `datasets` only in research `.venv`), with no single env containing the full `torch`/`transformers`/`peft`/`accelerate`/`sentence-transformers`/`safetensors` stack. **Next real gate**: acquire/restore a trainable BGE-large checkpoint and an isolated full training environment, then implement SVD-FT on the last `k` transformer blocks, retrain the head end-to-end, and A/B against frozen BGE-large on the same validation split. **Allowed interim work**: a BGE-M3 proxy or feature-space spectral scaling run may be performed only if reported as proxy evidence, not as P4.3 completion. Decision gate for the true trial remains: if Δ ≥ +2 points val acc, promote SVD-FT to default; if flat, record null and move on.
- **[declined: ws58 2026-11-03 content-review: its own text: no longer justified after P4.2]** **P4.4** **sep-CMA-ES cold-start spike (large cost; no longer justified for the current trained-label surface after P4.2)**: Trinity trains the routing head with sep-CMA-ES against terminal binary reward (no labels). P4.2 refuted the block-separable rationale on the current episodic-label classifier, so do **not** spend an overnight ES run here just to chase Trinity transfer. Keep this only for a future true cold-start surface with sparse/no distillation labels (Phase 2/3 hidden-state probe, a new role surface, or a new model added to the pool) where ES against eval-tower fitness could train the head from cold. Replication budget estimate (deep-dive Section 5): population λ≈45 for our 200K-param head, m=16 reps, ≈720 fitness evals per generation, ≈10 generations as feasibility-test target ≈ 10h overnight at 32-way concurrency. Prerequisites remain: (a) eval-tower wired as a per-question scorable, parallelisable fitness oracle (Math-Verify adoption is on the critical path — see `routing-and-optimization-index.md` cross-cutting concern #13), (b) `pycma` or equivalent sep-CMA-ES library vendored.
- [x] **P4.5** **Journal-derived soft-label SFT — zero-inference cold-start (Fugu Stage 1 analog)** — **COMPLETE 2026-06-26, NULL RESULT (soft labels do NOT beat hard labels; keep hard-label training)**. See "P4.5 Phase B Outcome" below for the full A/B. Original spec: Fugu Stage 1 trains via KL divergence against a per-worker reward distribution rather than contrastive binary labels. The equivalent for our LRC: for each `qid` with ≥5 appearances in the autopilot journal `question_results`, compute mean correctness per role across all trials → apply softmax(τ=2) → use as a soft probability distribution over roles for that question type. Train LRC via KL(predicted_logits ∥ soft_labels) instead of cross-entropy on hard winner-take-all labels. **Cost: zero additional inference** — all data is already in `orchestration/autopilot_journal.jsonl`. Current data: 546 qids with ≥5 appearances, ~5 roles → ~2,730 soft-label examples. Implementation: (a) extract per-qid per-role mean correctness from `question_results` in journal (script already feasible given the earlier per-question analysis); (b) apply softmax τ=2 to get probability vectors (τ=2 gives soft distributions; τ→0 is winner-take-all; τ→∞ is uniform — tune τ on a held-out quality check); (c) retrain LRC head via KL loss. Decision gate: if val acc improves ≥1 pp over hard-label baseline, adopt as the default Phase 1 training signal going forward. **Critical caveat**: the stable core has 3/50 mid-range qids (30–70% pass rate) — the remaining 47 are polarized floor/ceiling. This means the soft labels will be mostly near-deterministic (one role clearly dominates each question type), so the KL signal will be similar to hard labels for those cases. The real benefit is on the ~300 qids in the rotating pool with genuine mid-range histories (53% mid-range at ≥5 appearances), where the soft labels capture real uncertainty across roles. **Priority**: HIGH relative to P4.3/P4.4 — zero inference cost makes this the lowest-risk next experiment.
- [x] **P4.6** **Randomized-pool training for stack-change robustness (Conductor analog, added 2026-06-25)** — **COMPLETE 2026-06-27, NULL RESULT under the current P4.5 soft-label objective**. Orchestrator `688c6076` adds opt-in `--role-dropout-rate` training for the KL/soft-label arm and focused unit coverage; `a404e3bc` records 10 offline runs at rates `0.2` and `0.3` across five seeds. No run beat the hard-label arm by the +1pp role-success gate, so decision remains **keep current hard-label training**. Artifacts: `orchestration/reports/p46_role_dropout/{summary.json,summary.md,rate_*_seed_*.json}`. Future available-role robustness should be revisited only with an architecture/input contract that exposes role availability to the model, not by retuning this soft-label-only dropout path.

##### Phase 5: IRT-Stratified Cold-Start Onboarding (NEW 2026-04-28, from intake-496)

Source: intake-496 (LLM Bandit) — model identity vectors + Item Response Theory (IRT) discrimination-score-stratified prompt selection enable cold-starting a new specialist with 20–50 carefully chosen prompts instead of a full benchmark sweep.

**Why this matters for EPYC**: every model swap currently triggers a full benchmark sweep against the q-scorer baselines. Recent swaps (worker → 30B-A3B 2026-03-21, q-scorer recalibration 2026-03-21, coder Q4KM 2026-03-24) each cost a sweep. If the IRT-stratified cold-start workflow produces baselines within ~2 points of the full sweep, future swaps compress from a multi-hour sweep to a focused ~30-minute calibration. **This is the most actionable single experiment from intakes 495/496.**

Sequencing note: P5 is gated on having an IRT scorer (built in P5.1), NOT on Phase 2/3 completing. P5 can run in parallel with Phase 2 hidden-state work.

- [x] **P5.1** **IRT discrimination scorer substrate (~80–100 LoC, ~2 sessions)** — **COMPLETE 2026-06-27 as artifact-only scorer; outcome-matrix calibration remains a P5.2/P5.1b evidence task**. Orchestrator `3e0dcae9` adds `scripts/graph_router/irt_scorer.py` plus focused tests. The scorer is numpy-only and sidecar-only: it accepts direct prompt×model/action `responses` matrices with NaN masks for observed per-model outcomes, estimates `(latent_difficulty, latent_discrimination)`, fits global Platt calibration, and persists a compact NPZ artifact with canonical action map, calibration metadata, and a linear BGE-embedding projector for future prompt scoring. It also supports the current `training_data.npz` contract (`X`, `y`, `q_weights`, `label_map`) in explicitly marked `response_source="label_proxy"` mode so P4.1.3/DAR-5 feature experiments can proceed without inference. **Caveat**: the real cold-start adoption gate still requires observed per-model outcome responses, not just label-proxy routing labels. **Validation**: ruff + `tests/unit/test_irt_scorer.py` and `tests/unit/test_graph_router_action_space.py` (`15 passed`); real artifact smoke over 2,000 rows from `orchestration/repl_memory/training_data.npz` wrote `/mnt/raid0/llm/tmp/irt_prompt_scores_smoke.npz` with 8 actions, Platt params, and projector arrays.
- [ ] **P5.2** **Cold-start A/B vs on-disk full sweep (~70 LoC harness, 1 session)** — **HARNESS + KEYED-EMBEDDING BUILDER + ACCEPTANCE GATE COMPLETE 2026-06-27; promotion-grade observed-outcome run remains**. Orchestrator `6d0d1ecb` adds `scripts/calibration/irt_cold_start_ab.py` and tests. The harness flattens legacy baseline JSON artifacts (for example `benchmarks/results/runs/20260303_170903/worker_general_baseline.json`), selects an IRT-stratified subset across difficulty bins, compares subset vs full baseline summary (`avg_algorithmic_score`, `avg_tokens_per_second`, `pass_rate`), and writes a JSON report. It deliberately refuses to make a fake comparison unless baseline prompts can be matched to keyed IRT scores (`prompt_hashes`/`question_ids`) or keyed prompt embeddings plus the P5.1 projector. Orchestrator `a07edeff` adds `scripts/calibration/build_irt_prompt_embeddings.py`, which embeds baseline prompts through the live embedding fleet and writes both keyed prompt embeddings and optional keyed IRT-score artifacts. Orchestrator `039c6062` adds `--acceptance-gate`, wall-clock speedup checks, configurable metric thresholds, and zero-inference `--input-embeddings` reuse that rekeys cached embedding rows to the target baseline before writing new artifacts. **Smokes**: unkeyed label-proxy artifact correctly reports `blocked_missing_irt_scores` (`full_records=91`, `scored_records=0`); a two-record live embedder smoke over `worker_general_baseline.json` produced 1024-dim prompt embeddings and keyed IRT scores, and the harness then reached `status=ok` with `scored_records=2`. A full keyed plumbing run over all 91 `worker_general_baseline.json` records produced `/mnt/raid0/llm/tmp/worker_general_baseline_prompt_embeddings_20260627_185242.npz`, `/mnt/raid0/llm/tmp/worker_general_keyed_irt_scores_20260627_185242.npz`, and `/mnt/raid0/llm/tmp/worker_general_irt_cold_start_20260627_185242.json`; the harness scored all 91 records with a 50-prompt subset and reported relative deltas of 2.29% (`avg_algorithmic_score`), 3.54% (`avg_tokens_per_second`), and 9.0% (`pass_rate`). The new acceptance gate wrote `orchestration/reports/p52_irt_cold_start_acceptance/worker_general_cached_label_proxy_20260627.json` and correctly rejected the label-proxy subset: score and speed were within 5%, but pass-rate relative error was 9.0% and wall-clock speedup was only 1.94× vs the required 5×. This remains plumbing evidence only because the scorer is label-proxy-derived, three over-context prompts were truncated by the embedder path, and promotion still requires observed per-model outcome scores. **Next acceptance task**: run the same gate with a promotion-grade observed-outcome IRT scorer; accept only if all configured baseline features are within threshold and the measured wall-clock speedup clears the gate. On a pass (absorbs P5.3 and RI-X): document the cold-start workflow in the routing-intelligence track as the standard new-model onboarding procedure and add `tools/onboard_specialist.py` wrapping P5.1 + the calibration harness.
  - 2026-11-09 EG2 boundary (RTG-EG2-1): the keyed prompt embeddings (`build_irt_prompt_embeddings.py` output) and the P5.1 projector are BGE-1024 and the baseline JSONs are 2026-03-03 runs on retired models. Regenerate on the v11 stack: baselines for the 4-model lineup, prompt embeddings on EG2@256, and the IRT projector (REPL-EMB-R1).
- **[declined: ws58 2026-11-03 content-review: merged into P5.2 as its conditional rollout]** **P5.3** **(conditional)** Production rollout: if P5.2 passes its decision gate, document the cold-start workflow in `routing-intelligence.md` as the standard new-model onboarding procedure, and add a `tools/onboard_specialist.py` CLI that wraps P5.1 + the calibration harness. ~1 session, no new code beyond CLI assembly.

##### Phase 6: Per-Decision Verifier (NEW 2026-05-21, scoping only)

**Source**: deep-dive [`research/deep-dives/2026-05-21-recursive-reasoning-routing.md`](../../research/deep-dives/2026-05-21-recursive-reasoning-routing.md) Hypothesis C ("GRAM-as-verifier"). User-authorized scoping on 2026-05-21 in response to the standing thread on training a network dedicated to routing.

**Thesis**: today's router has no separate verifier head. Confidence comes from the softmax magnitude of the same MLP that emits the class prediction. A *distinct* verifier — trained on a *distinct* objective (probability that the proposed action is correct) — is a real architectural advance that none of `decision-aware-routing.md`, `outer-coordinator-learned-head.md`, or any prior Phase of this handoff proposes.

**The verifier interface**:

```
                  ┌────────────────────────────────────────┐
   request ─────► │  Existing routing pipeline:            │
                  │   BGE embed ─► RoutingClassifier MLP   │
                  └─────────────┬──────────────────────────┘
                                │ (top class, top prob)
                                ▼
                  ┌────────────────────────────────────────┐
                  │  NEW: Verifier head                    │
                  │   in:  (1024-d BGE) ⊕ (5-d one-hot)    │
                  │   out: P(action is correct) ∈ [0,1]    │
                  └─────────────┬──────────────────────────┘
                                │
                  P_correct ≥ τ ─┤── Yes ► route via MLP top class
                                └── No  ► fall through to FAISS KNN
```

This *replaces the per-class confidence threshold* (currently the per-class calibrated threshold from P1.4, e.g., frontdoor 0.447, architect_coding 0.560) with a *learned* gate trained on the actual correctness label.

**Training data exists** (per P1 normalization table): 10,528 positive failure examples (escalation memories = MLP routed wrong) + 56,457 negative examples (no escalation = MLP routed right) = ~67K labels in the canonical 174K snapshot. Live episodic.db was at 8K rows *(historical; 64,396 routing rows on 2026-09-26)* per [P4.1 Phase A audit](#phase-4-trinity-derived-methodology-audits-new-2026-04-26) — would need rebuild from episodic memory before training.

**Decision gates**:
- The scoping subtasks (P6.1, P6.2, P6.3) each end in a binary decision before the next escalates.
- DO NOT branch a separate handoff. All work stays under this index.
- DO NOT start P6.4+ recursive port without P6.2 demonstrating that a *simple* MLP verifier moves the needle. Occam's razor gates the recursion lever.

###### P6.1 — Verifier-vs-DAR-vs-threshold audit (analytical, no code, 1 session)

The current routing pipeline already has TWO mechanisms that overlap with a "verifier":
1. **Per-class confidence threshold** (P1.4) — discards low-confidence top-class predictions and falls through to KNN.
2. **DAR-2 contrastive Q-score** (per [decision-aware-routing.md](routing-program.md) DAR-2 ✅ 2026-04-15) — sharpens Q-value margins so the routing decision is robust.

Question: does adding a separate verifier head *materially* differ from these two, or is it equivalent at scale?

- [x] **P6.1.1** ✅ 2026-07-14 (audit: delivered per P6.1 Audit Outcome 2026-05-21) Read `decision-aware-routing.md` DAR-1 through DAR-5; identify where DAR's loss function differs from a calibrated "P(action correct)" prediction. Specifically: does DAR's contrastive adjustment converge to the same gradient signal as a logistic-regression verifier on the correctness label? If yes, the verifier may be redundant.
- [x] **P6.1.2** ✅ 2026-07-14 (audit: delivered per P6.1 Audit Outcome 2026-05-21) Inspect the per-class threshold calibration logic (P1.4) in `routing_classifier.py` or its training script. Is the threshold derived from a held-out *correctness* signal, or just from softmax precision/recall on the class label? If correctness signal, the threshold IS already a degenerate verifier (single scalar per class).
- [x] **P6.1.3** ✅ 2026-07-14 (audit: delivered per P6.1 Audit Outcome 2026-05-21) Write a 1-paragraph audit answering: "What does a separate verifier head *give us* that the per-class threshold + DAR-2 contrastive sharpening don't?"
  - If answer is "nothing material" → mark P6 closed, archive Hypothesis C, end of Phase 6.
  - If answer is "calibrated P(correct) at decision time, conditioned on both embedding AND proposed action, with a single decision threshold rather than 5 per-class thresholds" → proceed to P6.2.
- [x] **P6.1.4** Append the audit to this Phase. ~1 session, no code, deliverable is a paragraph and a binary go/no-go. **DONE 2026-05-21 — see "P6.1 Audit Outcome" below.**

###### P6.1 Audit Outcome (2026-05-21)

**Verdict**: a separate verifier head IS materially distinct from the per-class threshold + DAR-2 contrastive sharpening. **Phase 6 escalates to P6.2 (MLP verifier baseline).**

**Three-way comparison of the candidate gating mechanisms**:

| Axis | Per-class threshold (P1.4) | DAR-2 contrastive Q-adjust | Proposed verifier head |
|---|---|---|---|
| **Where in pipeline** | Decision-time, in `routing_classifier.py:155-159` `predict_action()` | Post-outcome, in `q_scorer.py:492-568` `_compute_contrastive_adjustment()` | Decision-time, between MLP and FAISS fallback |
| **Input signal** | `best_prob` (scalar softmax peak) + `best_idx` (1 of N) | `selected_q`, `alt_q_values[]` (sampled from top-10 similar memories) | `(1024-d embedding) ⊕ (5-d action one-hot)` — full joint input |
| **Training objective** | Class-precision: "given top-1 = class X, was the class label X correct?" | Q-ranking: "is selected Q above (success) / below (failure) competitors' Q-values?" | **Correctness**: "given embedding and action, P(no escalation downstream)" |
| **Per-instance adaptivity** | Zero — a single per-class scalar fixed at calibration time | Zero at decision time (DAR-2 is a *training* signal modifier, not a gate) | Full — learns embedding-conditional accept/reject patterns |
| **What it can represent** | `accept(x, a) = (p_softmax(a\|x) > τ_a)` — a 1-D calibrator over softmax per class | Q-value ranking sharpness in episodic memory (accumulates over time) | Arbitrary `P_correct = f(embedding, action)` — strictly more expressive than the threshold |
| **What it cannot represent** | Embedding-conditional risk: "cluster Y + frontdoor fails even at high softmax" | Decision-time gating (operates only on accumulated Q-values, not on this request) | (none of the above are limitations of the verifier) |
| **Failure-mode locus** | Fixed once at calibration; per-request adaptivity = 0 beyond per-class lookup | Distribution drift in Q-values over time; no per-decision protection | Retraining cycle (same as classifier); susceptible to escalation-label bias |
| **Latency** | ~µs (single comparison) | N/A at decision time (post-outcome path) | <1ms (single 70K-param MLP forward pass) |

**Material distinction (the load-bearing finding)**:

The per-class threshold is the **degenerate case** of the verifier — it is the family of verifier functions `f(p_softmax(a|x), a)` collapsed to a step function with a single per-class breakpoint. The general verifier function `P_correct(x, a)` is strictly more expressive because:
- The threshold ignores the embedding `x` entirely except through its compression into a softmax peak.
- The verifier observes the full 1024-d embedding AND the action jointly. It can learn patterns of the form "embedding-cluster Y + action frontdoor fails even when softmax is confident" — patterns the threshold provably cannot represent (the threshold sees only a scalar peak; it cannot tell embedding-cluster Y apart from cluster Z if both produce the same softmax peak).

The classifier itself emits a distribution over actions ("which action?") and uses the softmax peak as a proxy for confidence. The verifier evaluates a specific action ("is this action right?"). For an N=5 multi-class problem these are genuinely different questions — the classifier's softmax cannot encode action-specific accept/reject patterns the way a (x, a) → P(correct) head can.

DAR-2 is **not** a decision-time gate — it modifies the reward signal feeding the Q-value TD update over time. It improves the *learned ranking quality* of stored Q-values but does not look at any individual incoming request. A verifier and DAR-2 are orthogonal: DAR-2 improves the population of Q-values episodic memory holds; the verifier gates whether any given request should trust the current MLP prediction.

**Caveats and risks to address in P6.2**:

1. **Embedding-saturation risk**: the existing classifier achieves 92% val accuracy on the 174K-label class objective. If the 8% miss rate is Bayes-irreducible (i.e., the BGE embedding alone does not contain enough signal to separate the remaining hard cases), then a verifier head reading the same embedding cannot recover them either. **P6.2.5 gate explicitly requires ROC-AUC ≥ 0.75 on the held-out CORRECTNESS split — not the class split — to catch this.**
2. **Escalation-label bias**: escalation memories (the 10.5K positives) only fire when the system actually escalated. Cases where the MLP was wrong but the user did not escalate are missing from the training set. The verifier's correctness label is therefore a noisy proxy correlated with the existing escalation policy. **P6.2.2 must operationalize "correctness" as either (a) explicit downstream-quality-threshold gates, or (b) survivor-bias-aware reweighting of the negative class, not just "no escalation observed".**
3. **MC-dropout overlap**: if P6.4 demonstrates that multi-pass dropout on the existing classifier already produces a calibrated correctness predictor (variance-of-top-class-prob correlated with correctness ≥ 0.05 AUC over softmax magnitude), the verifier's information-theoretic edge may shrink to nothing in practice. **Let P6.4 run in parallel with P6.2 design — whichever produces a calibrated correctness signal at lowest cost wins.**
4. **DAR-2 interaction is benign, not redundant**: DAR-2 sharpens the *training* signal feeding the classifier (via Q-value TD updates); the verifier gates *inference-time* decisions. They compose without conflict — DAR-2 makes the classifier more confident on the right cases; the verifier catches cases where the classifier is confidently wrong. This is orthogonal capability, not duplicate.

**Decision**: proceed to P6.2 (MLP verifier baseline). The verifier framing introduces a primitive — a per-decision, embedding-conditional, action-specific correctness gate — that none of the existing mechanisms can express. The Occam-gated P6.2.5 acceptance criteria will determine whether the *expressive* superiority translates into an *empirical* win on our data. If P6.2 fails its gate, the verifier is closed without recursion-related sunk cost.



###### P6.2 — Baseline MLP verifier (the Occam gate, ~1-2 sessions)

If P6.1 escalates: build the *simplest possible* verifier head and test it before considering anything recursive.

- [x] **P6.2.1** Add `VerifierHead` class to `orchestration/repl_memory/routing_classifier.py` (or a new sibling file `verifier_head.py`). Architecture: 1029-d input (1024 BGE ⊕ 5 one-hot action) → Dense(64, ReLU) → Dense(32, ReLU) → Dense(1, Sigmoid). ~70K params, numpy-only, same style as `RoutingClassifier`. Output: P(action is correct) ∈ [0, 1]. **DONE 2026-05-21** — `verifier_head.py` (sibling file). Architecture: 1031-d features (matches classifier `input_dim`) ⊕ 8-d action one-hot = 1039-d input → 64 → 32 → 1 sigmoid. Param count: 68,673.
- [x] **P6.2.2** Add `extract_verifier_training_data.py` under `scripts/graph_router/`. Joins episodic memories with escalation events to produce `(embedding, action, correct)` triples. Correctness label: `correct=1` if no escalation downstream, `correct=0` if escalation event followed within the session. Stratify train/val/test 80/10/10. **DONE 2026-05-21 — with revised label scheme**. The cached reembedded.npz contained no routable rows under the `coder_escalation` action (per P1.4 note — escalation events lack initial-routing embeddings). **Pivoted from escalation-based to Q-value-threshold-based correctness**: `correct = (q_weight > 0.5)`. Rationale: Q-values are the TD-updated outcome of all task results that used a given routing memory — a per-memory aggregate success signal. Result: 134,905 positive (85.6%) + 22,615 negative (14.4%). Inverse-frequency sample weighting (pos=0.58, neg=3.48). **Caveat recorded**: Q-values are themselves shaped by the routing policy (DAR-2 contrastive sharpening, TD-update dynamics) — the verifier learns "good routes per current policy", not "good routes in absolute terms". P6.2 results below are interpreted with this caveat in mind.
- [x] **P6.2.3** Add `train_verifier_head.py`. Binary cross-entropy loss with class-weighting (negatives outnumber positives ~6:1). <1 min training on CPU per P1.6 retrain timing. Save weights to `orchestration/repl_memory/verifier_head_weights.npz`. **DONE 2026-05-21** — 100 epochs, lr=0.05 cosine decay, batch=256, patience=15, BCE + inverse-frequency weighting. Training wall-clock: 45 seconds on CPU (~157K samples, 80/20 split). Best val loss 0.0092 at epoch 81 (no early stopping triggered). Final val accuracy 99.79%.
- [x] **P6.2.4** Evaluate calibration via reliability diagram (binned P(correct) vs empirical correctness rate) and ROC-AUC on val set. Compute Brier score. Compare against (a) the per-class threshold baseline and (b) the softmax-of-top-class baseline. **DONE 2026-05-21 — with critical disaggregation. See "P6.2 Eval Outcome" below.** Headline numbers blow past every gate, but a per-action breakdown reveals the result is dominated by class-conditional triviality on three of four classes; the genuine signal is on action[0] (frontdoor) and IS real, just smaller than the headline implies.
- [x] **P6.2.5** **Decision gate**: if Brier improves by ≥ 0.02 AND ROC-AUC ≥ 0.75 AND calibration error (ECE) ≤ 0.05 → verifier survives Occam. Wire as a fallback gate in `retriever.py` behind a NEW feature flag `ORCHESTRATOR_VERIFIER_GATE` (default OFF; orthogonal to existing classifier flag). Else: record null result, archive Hypothesis C, end of Phase 6. **GATES PASS 2026-05-21 — but wiring DEFERRED pending user review of the disaggregation below.** Headline ΔBrier +0.122 / AUC 0.9999 / ECE 0.0042 all exceed their thresholds, but the genuine within-action signal is more modest. Recommend the user review the disaggregation before authorizing the production wire-in.

###### P6.2 Eval Outcome (2026-05-21)

**Verdict (headline)**: all three P6.2.5 gates PASS — ΔBrier vs the stronger baseline (softmax_max) is **+0.1220** (≥ +0.02 gate), ROC-AUC is **0.9999** (≥ 0.75 gate), ECE is **0.0042** (≤ 0.05 gate).

**Verdict (honest, after disaggregation)**: the headline is dominated by class-conditional triviality — three of four active classes have near-deterministic correctness rates that any predictor with action-one-hot access will trivially memorize. The **genuine demonstration of the verifier's information-theoretic edge** is on action[0] = frontdoor, the only class with substantial within-action variance.

**Aggregate metrics** (val set, n=31,504):

| Predictor | Brier ↓ | ROC-AUC ↑ | ECE ↓ | Notes |
|---|---|---|---|---|
| **verifier (P6.2)** | **0.0025** | **0.9999** | **0.0042** | 68,673 params, joint (features, action) input |
| softmax_max (clf top-1 prob) | 0.1245 | 0.7557 | 0.1082 | the per-class-threshold gate's input |
| softmax_taken (clf p(taken_action\|x)) | 0.1319 | 0.7669 | 0.1246 | softmax mass on the *taken* action |
| constant base rate (0.856) | 0.1211 | — | — | uninformative reference |
| **action-only marginal** | **0.0787** | **0.8494** | 0.0018 | predict per-action mean train correctness |

**Per-action disaggregation** (correctness label = `q_weight > 0.5`):

| Action | n_val | Per-action correctness rate (train) | Verifier Brier | Marginal Brier | Verifier intra-action AUC |
|---|---|---|---|---|---|
| 0 (frontdoor) | 14,459 | **0.7818** | **0.0055** | **0.1686** | **0.9997** |
| 1 (architect_general) | 8,406 | 1.0000 | 0.0000 | 0.0000 | — (no variance) |
| 2 (architect_coding) | 7,342 | 0.9936 | 0.0000 | 0.0057 | 1.0000 |
| 4 (worker_explore) | 1,297 | 0.0000 | 0.0000 | 0.0000 | — (no variance) |

**Where the signal lives**:

- **Action[0] (frontdoor)** is the only class where the correctness label is non-trivially distributed (78.2% positive, 21.8% negative). The verifier achieves **Brier 0.0055** vs the marginal-action baseline's **Brier 0.1686** — a **30× improvement**. Intra-action ROC-AUC of **0.9997** demonstrates that the verifier learns embedding-conditional discrimination of which frontdoor decisions succeed vs fail. **This IS the demonstration of the joint-conditioning edge the P6.1 audit predicted.**
- **Action[1] (architect_general)**: 100% positive in training data — verifier and marginal both trivially correct. No signal to learn.
- **Action[2] (architect_coding)**: 99.4% positive — near-trivial. The verifier reaches Brier 0.0000 by leveraging the action one-hot.
- **Action[4] (worker_explore)**: 0% positive — trivially separable from the rest. Both verifier and marginal achieve Brier 0.0000.

The aggregate 0.9999 AUC is not "the verifier learned to predict routing correctness with near-perfection across the board" — it is "the verifier learned the marginal per-action correctness rates (which a 4-bucket lookup table could also do) AND on top of that learned to discriminate within action[0]". The 30× Brier improvement on action[0] is the real win, masked by the easy-classes contribution to the aggregate.

**Caveats** (load-bearing for any production wire-in):

1. **Q-value correctness label is policy-biased.** Architect_general's 100% correctness rate is almost certainly not a real-world success rate — it reflects the TD-update dynamics under the current routing policy + DAR-2 contrastive sharpening. The verifier is learning "good routes per current policy", not "good routes in absolute terms". This bias is acceptable for a *gate that defends the current policy from itself* (i.e., predicts when the classifier will be wrong relative to the policy's own success criterion), but does NOT generalize to a verifier of new routes.
2. **Action[4] (worker_explore) being 0% correct is suspect.** Per the Phase 1 normalization note, worker_explore data is 88% `task_type=chat` with low Q-values because chat tasks often hit the legacy frontdoor-by-default logic. The verifier learns to predict "worker_explore → incorrect", which is a true statement about the training distribution but may be wrong as the worker_explore role evolves.
3. **Aggregate ranking AUC is misleading** because most of the val ranking is between deterministic classes (action[1]/[2] positives vs action[4] negatives) — i.e., the verifier's "discrimination" is largely the marginal action distribution, not embedding-conditional discrimination. Always report the per-action disaggregation, never just the aggregate.
4. **No counterfactual data.** The training set contains `(embedding, taken_action, correct)` triples — there are no `(embedding, untaken_action, ?)` examples. At inference, if the classifier proposes a counterfactual action (one not typically taken for this embedding), the verifier extrapolates without ground truth. This is the standard offline-policy limitation; needs an A/B in shadow mode to detect drift.
5. **No held-out distribution test.** Train/val is i.i.d. (random split). The verifier's robustness on a different task distribution (different time period, different user population, different model versions in the pool) is unmeasured.

**Recommendation**: do NOT wire `ORCHESTRATOR_VERIFIER_GATE` to production retriever yet. The headline numbers pass the gate but the real signal is narrow (essentially "improved frontdoor confidence calibration"). Two concrete next steps before wiring:

- **NEXT-A**: train and evaluate a **policy-debiased** correctness label — e.g., `correct = (final_task_quality_score > threshold)` joined per-session from a quality oracle independent of the Q-update loop. This addresses caveats 1 and 2. Estimated: 1-2 sessions of data-pipeline work to join task_outcome events with routing decisions.
- **NEXT-B**: write a **shadow-mode evaluation harness** that runs the verifier in parallel with the current per-class threshold for ≥ 1 week, logging both decisions and downstream outcomes, without changing routing behavior. This addresses caveats 4 and 5. Estimated: 1 session of harness code, then wall-clock waiting.

**Artifacts** (preserved for re-runs):
- `orchestration/repl_memory/verifier_head.py` — VerifierHead class (created 2026-05-21)
- `scripts/graph_router/extract_verifier_training_data.py` — data extraction (created 2026-05-21)
- `scripts/graph_router/train_verifier_head.py` — train + eval harness (created 2026-05-21)
- `/tmp/p6_2_verifier_training_data.npz` — verifier training NPZ (regenerable)
- `/tmp/verifier_head_weights.npz` — trained weights (68,673 params; NOT in production directory yet)

###### P6.2 NEXT-A Result (2026-05-21) — counterfactual probe is the real story

**Setup**: rebuilt training data using `outcome` field from `episodic.db.backup-20260415` instead of `q_weights > 0.5` to address the policy-bias caveat (#1). Join key: memory_id from reembedded.npz ⋂ backup db. Result: 153,847 rows (97.7% of reembedded), label distribution 86.1% positive / 13.9% negative.

**Finding 1 — Q-value label and outcome label are interchangeable in this data**:

```
Action                  n        outcome_rate   Q-rate
[0] frontdoor          70,996   0.784          0.784
[1] architect_general  40,312   1.000          1.000
[2] architect_coding   36,686   0.994          0.994
[4] worker_explore      5,853   0.000          0.000
```

Q-values in this dataset were initialized from outcome and `update_count=0` everywhere — TD updates never moved Q substantially. So the "policy bias on Q-values" caveat (#1) was a false alarm on THIS data; the Q-label IS the outcome label by construction. The retrained verifier produces near-identical metrics: Brier 0.0021 (was 0.0025), AUC 0.9999 (same), ECE 0.0036 (was 0.0042).

**Finding 2 — counterfactual probe falsifies the "joint conditioning" interpretation**:

I queried the trained verifier with the SAME 14,239 frontdoor val embeddings, paired with each possible action one-hot, to see whether the verifier discriminates by `(embedding, action)` jointly or just by action.

| Action paired with frontdoor embedding | Mean P_correct | Median | % endorsed (>0.5) |
|---|---|---|---|
| 0 (frontdoor — taken in training) | 0.7806 | 0.9997 | 78.7% |
| 1 (architect_general — counterfactual) | **1.0000** | **1.0000** | **100.0%** |
| 2 (architect_coding — counterfactual) | **0.9930** | **1.0000** | **100.0%** |
| 4 (worker_explore — counterfactual) | **0.0000** | **0.0000** | **0.0%** |

The verifier is essentially `P_correct = per_action_marginal(action) + intra_action_refinement(embedding | action=frontdoor)`. For actions 1, 2, 4 the embedding contributes nothing — the verifier outputs the marginal action rate regardless of what's in the embedding. This is **architecturally** what the verifier should be able to do (the input includes the joint), but the training data didn't supply enough action-conditional variance to teach it. Intra-action AUC matrix:

| Action | n_val | Intra-action AUC | Verifier Brier | Softmax_max Brier | Status |
|---|---|---|---|---|---|
| 0 frontdoor | 14,239 | **0.9997** | **0.0046** | 0.1942 | genuine discrimination (~42× Brier improvement) |
| 1 architect_general | ~8,000 | — | 0.0000 | 0.0000 | no within-class variance — nothing to learn |
| 2 architect_coding | ~7,000 | — | 0.0000 | 0.0057 | near-trivial; verifier returns 1.0 |
| 4 worker_explore | ~1,300 | — | 0.0000 | 0.0000 | no within-class variance — verifier returns 0.0 |

The verifier IS effective on frontdoor specifically — 0.7321 → 0.9997 ROC-AUC, a substantial intra-action win — and that win is real, embedding-conditional discrimination. It's just NOT what the headline 0.9999 aggregate AUC suggested.

**Finding 3 — production wire-in is unsafe under current training data**:

- For frontdoor routes: verifier ADDS genuine signal (good).
- For architect_general / architect_coding routes: verifier RUBBER-STAMPS at ~100% regardless of embedding (effectively erases the existing softmax-magnitude gate's discrimination on these classes — REGRESSION).
- For worker_explore routes: verifier REJECTS at 0% regardless of embedding (would prevent any worker_explore deployment — REGRESSION).

The training data has no architect_general failure examples and no worker_explore success examples, so the verifier cannot learn what those would look like. Wiring this verifier to production would systematically lock in the seeded biases for those classes.

**Decision update**: **Do NOT wire the multi-action verifier.** P6.2.5's aggregate gates pass but the per-action analysis shows the deployment would regress 3 of 4 classes. The methodology is validated (joint conditioning DOES learn within frontdoor) but the data does not yet support a production multi-action verifier.

**Two paths forward** (replace original NEXT-A scope which is now resolved):

- **NEXT-A2 — frontdoor-specialist verifier**: train a binary success-predictor on frontdoor decisions only (70K training samples, 22% failures). Avoids the label-leakage trap by construction (no other classes in scope). Gates on Brier improvement over softmax magnitude *restricted to frontdoor inputs*. ~1 session of code. Useful if our top operational pain point is "the MLP is over-confident in frontdoor on certain inputs."
- **NEXT-A3 — defer until data infrastructure refresh**: see "Operational Findings" section below. The reembedded.npz is a frozen 2026-04-15 snapshot; the live episodic.db has 52K newer routing memories with no cached embeddings (FAISS reset). A proper multi-action verifier needs the new data + balanced failure coverage across classes. Costs one bundled BGE-inference run.

###### Operational Findings (2026-05-21) — surfaced during NEXT-A work, NOT verifier-blocking

These findings are about data infrastructure, not the verifier itself, but should be considered before autopilot restart:

1. **reembedded.npz is 100% disjoint from live db**. The 157,520 IDs in `reembedded.npz` have zero overlap with the 52,667 routing memories currently in `episodic.db`. The live db has been growing with new memories since 2026-04-16; the cached embeddings are a frozen 2026-04-15 snapshot. Recoverable only via the backup at `episodic.db.backup-20260415` (153,847 of 157,520 IDs joinable, used for NEXT-A debiased label).
2. **Live db routing memories have minimal FAISS embeddings**. `embeddings.faiss` is 385 KB (reset); `.bak` is 32 MB (Feb 24). 52K routing memories were written without corresponding embeddings being computed or indexed.
3. **Implication for autopilot restart**: the classifier MLP fast-path is unaffected (stateless feed-forward). The KNN fallback path (FAISS similarity over episodic memories) cannot function as designed because there are essentially no current embeddings to match against. If the per-class threshold gates fail confidence for any request, the fallback returns trivial neighbors.
4. **Implication for any retrained verifier or classifier**: training new versions on the current data state would either (a) use the frozen 2026-04-15 distribution again (stale), or (b) require re-embedding the live db's 52K rows (BGE inference run, user authorization required per `feedback_no_concurrent_inference`).
5. **No log scrubbing needed**. Episodic logs reflect real task outcomes. The data state is incomplete (missing embeddings), not corrupt. Q-saturation is a property of the initial-Q-from-reward initialization, not TD-dynamics contamination.

**Recommendation to user before autopilot restart**:
- Either accept the current state and restart autopilot (classifier MLP fast-path still works; KNN fallback degrades silently).
- Or authorize ONE bundled BGE-inference session that:
  - Re-embeds the live db's 52K routing memories into a fresh FAISS + new reembedded.npz.
  - Rebuilds the verifier training extract using fresh outcomes for the new memories.
  - Enables P4.1 Phase B (audited but deferred per `feedback_no_concurrent_inference`) at the same time.
  - Total wall-clock estimate: ~5–15 min per the P4.1 estimate.

###### P6.2 NEXT-B Status (2026-05-21) — deferred pending NEXT-A2/A3 decision

NEXT-B (shadow-mode eval harness) was scoped to run a verifier alongside the existing per-class threshold for ≥ 1 week. **Deferred** because:
- The current multi-action verifier would regress 3 of 4 classes if shadow-deployed (per Finding 3 above) — shadow-mode would just confirm what the counterfactual probe already shows.
- The right next step depends on whether the user authorizes NEXT-A2 (frontdoor-specialist verifier — cheap, no inference) or NEXT-A3 (data infrastructure refresh — bundled BGE-inference run).

If NEXT-A2 is chosen, NEXT-B's shadow harness can be retargeted to evaluate the frontdoor-specialist on frontdoor-routed requests specifically. If NEXT-A3 is chosen, NEXT-B becomes a routine shadow harness on the retrained multi-action verifier with proper data coverage.

**Additional artifacts** (debiased pipeline):
- `scripts/graph_router/extract_verifier_training_data_debiased.py` — outcome-based extractor (created 2026-05-21)
- `/tmp/p2_2_verifier_training_data_debiased.npz` — debiased training NPZ
- `/tmp/verifier_head_weights_debiased.npz` — retrained weights (substantively identical to original)

###### A3 Implementation (2026-05-21) — orphan-embedding preflight + repair tool

**User-authorized 2026-05-21**: implement an episodic-store health preflight that detects and (on flag) repairs the orphan-FAISS state surfaced during NEXT-A work. Goal: make autopilot/orchestrator restart self-healing wrt FAISS gaps.

**Implementation**:

1. **New: `scripts/maintenance/repair_episodic_embeddings.py`** — standalone diagnostic + repair tool.
   - `--diagnose-only`: read-only. Reports `n_db_routing`, `n_faiss_vectors`, `n_reembedded`, `overlap_live`, `faiss_coverage`. Exit 0 if healthy, 1 if orphaned.
   - `--repair`: invokes `scripts/graph_router/reembed_episodic_store.py` (existing 8-parallel-BGE primitive) to produce a fresh `reembedded.npz`, then rebuilds `embeddings.faiss` + `id_map.npy` atomically with backups (writes to `.new`, renames; originals saved as `.pre-repair-<timestamp>`). Re-validates by re-opening FAISS and checking ntotal.
   - Threshold: `faiss_coverage < 50%` OR `overlap_live < 50%` → ORPHANED. Repair guarded by `--min-orphans` (default 1000) to avoid touching small drift.

2. **Wired into `scripts/server/orchestrator_stack.py`** at step `[0.7] Episodic embedding health check`, between model-path validation and server-launch sequence:
   - Diagnostic always runs (read-only, ~1 sec on cold cache).
   - If unhealthy AND `--repair-embeddings` flag passed: runs full repair before launch (~5-15 min wall-clock for the current 52K-orphan state).
   - If unhealthy AND no flag: prints warning + manual-repair instructions; does NOT block startup.
   - Import is defensive (`ImportError` → skip-with-log; `Exception` → log-and-continue) to avoid breaking older deployments.
   - New CLI arg: `--repair-embeddings`.

**Verified on current state (2026-05-21 12:23)**:

```
========================================================================
Episodic Embedding Health Report
========================================================================
  Routing memories in db:          53,087
  Vectors in FAISS index:              94
  IDs in reembedded.npz:          157,520
  FAISS coverage:                    0.2%  (threshold ≥ 50%)
  reembedded ⋂ live db:              0.0%  (threshold ≥ 50%)
  Orphan count (db − FAISS):       52,993
  Status:                      ORPHANED — repair recommended
========================================================================
```

Diagnostic + import path both verified to work as the orchestrator_stack `[0.7]` hook will invoke them. `--repair-embeddings` flag is registered and visible in `start --help`.

**Operational procedure for first restart**:
```
python3 scripts/server/orchestrator_stack.py start --repair-embeddings
```
This will trigger the bulk repair on first restart, ~5-15 min, then proceed with normal launch. After that, the orphan state is gone — subsequent restarts diagnose-clean in ~1 sec and proceed immediately.

**Artifacts**:
- `scripts/maintenance/repair_episodic_embeddings.py` (created 2026-05-21, ~280 LoC)
- `scripts/server/orchestrator_stack.py` (modified 2026-05-21, +60 LoC at step [0.7] + 1 CLI arg)

###### A2 Result (2026-05-21) — frontdoor-specialist verifier PASSES gates

**Setup**: filtered the debiased verifier training data to frontdoor (action=0) only. Stripped the 8-d action one-hot from inputs (since there's only one action, the one-hot is constant and meaningless). Trained `VerifierHead(feature_dim=1031, n_actions=0)` — 68,161 params, 64×32 hidden — on 70,996 frontdoor samples with 22% failure rate. BCE loss + inverse-frequency class weighting, 100 epochs cosine LR decay.

**Intra-action val metrics** (action[0] only, n=14,199, 78.8% positive base rate):

| Predictor | Brier ↓ | ROC-AUC ↑ | ECE ↓ | Acc@0.5 |
|---|---|---|---|---|
| **frontdoor verifier (A2)** | **0.0043** | **0.9997** | **0.0066** | **0.9960** |
| softmax max prob (clf top-1) | 0.1941 | 0.7348 | 0.1851 | — |
| softmax p(frontdoor\|x) | 0.2034 | 0.7378 | 0.2056 | — |
| constant base rate (0.788) | 0.1670 | — | — | — |

**A2 decision gates** (same thresholds as P6.2.5):

| Gate | Verifier | Threshold | Status |
|---|---|---|---|
| ΔBrier vs best baseline (softmax_max) | **+0.1898** | ≥ +0.02 | **PASS** (9.5× margin) |
| ROC-AUC | **0.9997** | ≥ 0.75 | **PASS** |
| ECE | **0.0066** | ≤ 0.05 | **PASS** |

**This is the genuine joint-conditioning win** the P6.1 audit predicted, isolated from the action-marginal label-leakage trap the multi-action verifier fell into. The frontdoor verifier:
- Cannot memorize per-action marginals (only one action in scope).
- Achieves a ~45× Brier improvement vs softmax_max baseline on frontdoor val rows.
- Reaches 99.6% accuracy on a 22%-failure-rate task — the classifier+softmax-threshold alone gets the trivial 78.8% from always predicting positive.
- Calibration is excellent: reliability bins show |gap| ≤ 0.005 for the two dominant bins ([0,0.1] and [0.9,1.0]) which together cover 96.8% of val samples.

**Caveats specific to A2** (lighter than multi-action ones):
1. **Outcome label is still from backup-20260415** — frozen snapshot of the routing policy as of that date. Generalization to current live-db distribution is unmeasured. Mitigated once A3 repair runs: a re-extraction on the post-repair `reembedded.npz` will give a current-distribution training set.
2. **No counterfactual generalization issue** here (the action is fixed at frontdoor, so there are no untaken-action examples to worry about).
3. **Frontdoor-only coverage**: this verifier ONLY gates frontdoor routes. For other classes, no gate. The existing per-class threshold mechanism handles them. Acceptable.

**Deployment shape** (NOT YET WIRED — same Occam discipline as multi-action verifier):

```
Request ─► BGE embed ─► RoutingClassifier MLP → top class + softmax
                                  │
            top class == frontdoor?
                    │   no  ─► per-class threshold (unchanged)
                    │   yes ─►
                                  │
              frontdoor verifier (A2)
                                  │
            P(success) ≥ τ_fd?
                    │   yes ─► route via frontdoor
                    │   no  ─► fall through to KNN  ← REQUIRES A3 HEALTHY
```

**Phase 6 status synthesis**:

| Step | Status | Decision-relevant finding |
|---|---|---|
| P6.1 audit | ✅ DONE | Verifier framing materially differs from threshold + DAR-2; proceed |
| P6.4 MC-dropout proxy | ✅ DONE (null) | No falsification of verifier value; classifier trained w/o dropout |
| P6.2 multi-action verifier | ✅ DONE (gate passes but invalid) | Counterfactual probe revealed 3-of-4 classes are action-marginal lookups — would regress production if wired |
| P6.2 NEXT-A debiased label | ✅ DONE (no-op) | Q-label ≡ outcome-label in this snapshot; bias caveat doesn't apply |
| **A3 orphan-embedding preflight + repair** | ✅ DONE | Detects ORPHANED state; `--repair-embeddings` flag triggers bulk fix; safe for first autopilot restart |
| **A2 frontdoor-specialist verifier** | ✅ DONE (PASS) | All gates pass with 9.5× Brier margin; ready to wire as frontdoor-only gate AFTER A3 runs |
| Wire `ORCHESTRATOR_FRONTDOOR_VERIFIER_GATE` flag | DEFERRED | Pending: (a) A3 repair runs on first restart, (b) shadow-mode eval of A2 on fresh post-repair data |

**Recommended sequencing**:

1. **First autopilot restart** with `--repair-embeddings`: rebuilds FAISS, restores KNN fallback. ~5-15 min.
2. **Re-extract debiased training data** from the fresh reembedded.npz (no inference, just re-join). Confirms A2 generalization holds on current distribution.
3. **Retrain A2 frontdoor verifier** on the fresh data. If gates still pass, wire the gate behind `ORCHESTRATOR_FRONTDOOR_VERIFIER_GATE` (default OFF). If regression, A2 is over-fit to the April snapshot and we close out Phase 6.

**Artifacts**:
- `scripts/graph_router/train_frontdoor_verifier.py` (created 2026-05-21)
- `/tmp/frontdoor_verifier_weights.npz` — 68,161 params, intra-action val AUC 0.9997

###### Open Action — restart authorization

User authorization required for the first `orchestrator_stack.py start --repair-embeddings` run (BGE inference, ~5-15 min). This is a one-time bulk operation; subsequent restarts will diagnose-clean in ~1 sec.

###### A3/A2 Production Wiring (2026-05-21) — done

User authorized 2026-05-21 and the following four-step sequence was executed end-to-end:

**Step A — RoutingClassifier loading wired into production routing path**

Pre-existing gap discovered during A2 wiring: the P1.5 task ("enable `ORCHESTRATOR_ROUTING_CLASSIFIER=1`") had flipped the feature flag but the actual *loading code* was never written. `HybridRouter` accepted a `routing_classifier` parameter but nothing in `src/api/services/memrl.py` ever called `RoutingClassifier.load(...)` and passed it in. **Every production request was taking the full KNN path** since 2026-04-15.

Fix landed at `src/api/services/memrl.py:471` (before the `HybridRouter` construction). The new block:
- Checks `features().routing_classifier` (existing flag, default OFF)
- Loads weights from `ROUTING_CLASSIFIER_WEIGHTS` env override or `DEFAULT_WEIGHTS_PATH` (which points at `orchestration/repl_memory/routing_classifier_weights.npz`)
- Logs param count, action count, and weights path on success
- Gracefully degrades if weights missing (logs warning, fast-path stays disabled)
- Threads the loaded classifier into `HybridRouter(routing_classifier=…)`

**Step B — Classifier retrained on the post-stack-change distribution**

The April 2026-04-15 weights were trained on a distribution where `architect_general` was 100% successful. The 2026-05-09 stack consolidation (`project_stack_consolidation_2026_05`) reshuffled the role pool and architect_general's empirical success rate dropped to 9.1% in post-change data. The April-weights classifier was therefore mis-routing aggressively into architect_general failures.

Retrained via `train_routing_classifier.py` on the post-repair `/tmp/p6_4_training_data_fresh.npz` (40,956 samples):

| Metric | April 2026-04-15 | Fresh 2026-05-21 |
|---|---|---|
| Train accuracy | 92.0% | **98.7%** |
| Val accuracy | 92.0% | **98.7%** |
| Best val loss | 0.099 | **0.017** |
| Per-class val acc — frontdoor | 91.5% | **99.6%** |
| Per-class val acc — architect_general | 95.1% | 93.9% |
| Per-class val acc — architect_coding | 95.7% | 100.0% |
| Per-class threshold — frontdoor | 0.447 | 0.611 |
| Per-class threshold — architect_general | 0.362 | 0.604 |
| Per-class threshold — architect_coding | 0.560 | 0.379 |

Fresh weights staged to production path: `orchestration/repl_memory/routing_classifier_weights.npz` (522KB, 140,872 params). Next API restart picks them up via Step A's loading code.

**Coverage caveat**: fresh classifier still only trained on 3 classes (frontdoor, architect_general, architect_coding) because the normalizer-bug-driven 22.9% drop excluded `coder_escalation`, `worker_general`, `ingest_long_context` from the reembed. Normalizer fix landed (next bullet), but rebuilding the missing classes' embeddings requires another `--repair-embeddings` run.

**Step C — Frontdoor verifier gate wired in retriever.py + memrl.py**

`HybridRouter.__init__` now accepts `frontdoor_verifier` (default None) and a configurable `frontdoor_verifier_threshold` (default 0.5, env override `FRONTDOOR_VERIFIER_THRESHOLD`). The classifier fast-path in `route()` was extended:

```
classifier predicts top class
    ├── confidence < per-class threshold → fall through to KNN (unchanged)
    └── confidence ≥ threshold AND routing[0] == "frontdoor" AND verifier loaded
            verifier.predict(features, action_idx=0) → P_success
                ├── P_success ≥ threshold OR shadow mode → return via fast-path (with verifier metadata)
                └── P_success <  threshold AND enforcing → fall through to KNN
```

For non-frontdoor routes the verifier is bypassed (no signal to add). Loading wired in `memrl.py` behind `ORCHESTRATOR_FRONTDOOR_VERIFIER_GATE` (default OFF) — same defensive style as the classifier. Two related env vars:
- `FRONTDOOR_VERIFIER_THRESHOLD` — default 0.5
- `FRONTDOOR_VERIFIER_SHADOW` — set to `1` for shadow mode (verifier runs and is logged via `last_decision_meta`, but never gates)

Fresh frontdoor-specialist weights staged at `orchestration/repl_memory/verifier_head_weights.npz` (253KB, 68,161 params).

**Step D — Shadow-mode capability**: implemented inline via `FRONTDOOR_VERIFIER_SHADOW=1` (no separate harness needed — `last_decision_meta` records `verifier_verdict`, `verifier_p_success`, `verifier_shadow` on every fast-path decision, so existing telemetry captures the shadow signal). A week of live shadow traffic can be analyzed against downstream outcomes to validate the gate before enforcing-mode rollout.

**Step normalizer-fix — bonus, also done 2026-05-21**

Added 7 missing entries to `ACTION_NORMALIZATION` (5 identity maps for canonical actions whose raw label IS the canonical name — `coder_escalation`, `ingest_long_context`, `worker_explore`, `worker_math`, `worker_vision` — plus `worker_general → worker_explore` and `coder → architect_coding` for renamed/legacy labels). Closes the 22.9% silent drop discovered during the first `--repair-embeddings` run. Next `--repair-embeddings` run will capture the missing 12K memories.

**Bug fixes landed during this work**

1. `repair_episodic_embeddings.py` — `np.save` auto-appends `.npy` to its path; my original code constructed `id_map.new` via `Path.with_suffix(".new")` and then renamed `id_map.new → id_map.npy`, but np.save had actually written to `id_map.new.npy`. The rename silently failed (`FileNotFoundError` swallowed by the orchestrator_stack wrapper), leaving FAISS rebuilt with 40,956 vectors but `id_map.npy` stuck at 94 entries. Fixed by explicit naming + post-write existence validation. Production `id_map.npy` was manually corrected (the bug version preserved as `id_map.npy.broken-1779368503`).
2. `VerifierHead.join/join_batch` — IndexError when `n_actions == 0` (single-action specialist case, e.g., frontdoor-only). `oh = np.zeros(0)` is empty, so `oh[action_idx] = 1` raises. Fixed to skip the one-hot construction entirely when `n_actions <= 0`.

###### Rollout sequence to enable in production

1. **Restart the API service.** It will:
   - Pick up the fresh classifier (98.7% val acc) automatically — `routing_classifier` flag is already on.
   - Pick up the fresh frontdoor verifier ONLY IF `ORCHESTRATOR_FRONTDOOR_VERIFIER_GATE=1` is set (default OFF).

2. **For initial verifier rollout (recommended)**: set `ORCHESTRATOR_FRONTDOOR_VERIFIER_GATE=1` + `FRONTDOOR_VERIFIER_SHADOW=1`. Verifier runs and decisions are logged via `last_decision_meta` but no fast-path is gated. ≥1 week of traffic accumulates shadow-mode signal.

3. **After shadow validation**: unset `FRONTDOOR_VERIFIER_SHADOW` (or set to `0`). Gate enforces — frontdoor routes with verifier P_success < 0.5 fall through to KNN instead of fast-path routing.

4. **Optional follow-up**: another `orchestrator_stack.py start --repair-embeddings` to ingest the previously-dropped 12K memories (coder_escalation, worker_general, ingest_long_context). Will trigger because the diagnostic will report ORPHANED for those 12K rows. Once they're in, classifier can be retrained for full 4+ class coverage.

###### Files touched (all in /mnt/raid0/llm/epyc-orchestrator/)

| File | Change |
|---|---|
| `src/api/services/memrl.py` | +60 LoC — RoutingClassifier + VerifierHead loading, wired into HybridRouter |
| `orchestration/repl_memory/retriever.py` | +50 LoC — verifier gate in fast-path, constructor args, env-var threshold + shadow flag |
| `orchestration/repl_memory/verifier_head.py` | bug fix — `join`/`join_batch` handle `n_actions=0` |
| `orchestration/repl_memory/routing_classifier_weights.npz` | NEW — fresh weights, 98.7% val acc on current distribution |
| `orchestration/repl_memory/verifier_head_weights.npz` | NEW — frontdoor-specialist verifier, intra-action AUC 0.9996 on fresh val |
| `scripts/graph_router/extract_training_data.py` | +7 entries to ACTION_NORMALIZATION — closes 22.9% drop |
| `scripts/maintenance/repair_episodic_embeddings.py` | bug fix — id_map.new.npy filename handling |
| `orchestration/repl_memory/sessions/id_map.npy` | repaired in-place (broken version preserved) |

**Files**:
- New: `orchestration/repl_memory/verifier_head.py`
- New: `scripts/graph_router/extract_verifier_training_data.py`
- New: `scripts/graph_router/train_verifier_head.py`
- Modified (conditional on P6.2.5 pass): `orchestration/repl_memory/retriever.py` — add verifier gate
- Modified (conditional): `src/features.py` — add `verifier_gate` flag

###### P6.3 — Recursive verifier (DEFERRED, conditional on P6.2 pass)

Only if P6.2 demonstrates that a simple MLP verifier moves the needle, escalate to a recursive verifier port informed by the HRM → TRM → GRAM lineage (intake-582/583/584).

- **[declined: ws58 2026-11-03 content-review: deferred since 2026-05 with no consumer — the MLP verifier passed its gates and the live verifier gate is inert (LRC-2); a recursive-model port decides nothing today]** **P6.3.1** Port the SamsungSAILMontreal `TinyRecursiveModels` repo to a CPU-only training mode (it currently requires CUDA). Adapt the input adapter to consume 1024-d BGE embeddings + 5-d action one-hot, output a scalar correctness probability. Use the MLP-only variant (no self-attention) since context is fixed-size.
- **[declined: ws58 2026-11-03 content-review: same as P6.3.1]** **P6.3.2** Apply the **Augmented-HRM training recipe** from intake-585 — data augmentation (Gaussian noise on embeddings), input perturbation (random one-hot flips during training), bootstrapping (verifier-as-teacher for itself). The mechanistic-analysis finding is that THIS recipe, not the recursive architecture, is the load-bearing lever.
- **[declined: ws58 2026-11-03 content-review: same as P6.3.1]** **P6.3.3** A/B against P6.2 MLP verifier on the same train/val/test split. Decision gate: Brier improvement ≥ 0.01 over P6.2 baseline AND latency ≤ 5ms per decision (vs MLP verifier <1ms). If both gates pass, promote recursive verifier as default. Else: stick with MLP verifier, archive recursive verifier as null result.

**Open recursion questions to answer in P6.3.1**:
- Do we need GRAM-style stochastic trajectories (multi-sample at inference) or is deterministic recursion enough? Hypothesis: deterministic suffices for a binary verifier — multi-trajectory was load-bearing for GRAM only because its task (N-Queens multi-solution coverage) has multiple equally-correct outputs; verifier outputs are scalar-valued.
- How many recursive iterations? TRM uses 42 effective recursions/step × 16 supervision steps. For a verifier, that's wildly over-budgeted. Start with T=2, n=4 (8 effective recursions) and grow only if accuracy plateaus.

###### P6.4 — Cheap MC-dropout proxy for GRAM multi-trajectory (Hypothesis B, parallel to P6.1, ~1 session)

Separate cheap experiment that does NOT depend on P6.1/P6.2 outcome. The deep-dive's Hypothesis B argues that GRAM-style width-scaling (parallel trajectories at inference) is approximated for free by MC-dropout on the existing MLP.

- [x] **P6.4.1** Add an `mc_predict()` method to `RoutingClassifier` that runs N=10 forward passes with dropout p=0.1 applied to the two hidden layers. Returns (mean_probs, std_probs) over the 10 samples. **DONE 2026-05-21** — `routing_classifier.py:163-200` `mc_predict()` returns full `(n_samples, N, n_actions)` tensor so callers can derive any uncertainty signal.
- [x] **P6.4.2** Compute two derived signals: (a) **mean argmax** as the predicted class, (b) **variance of top-class probability** across passes as an uncertainty signal. **DONE 2026-05-21** — eval harness `scripts/graph_router/mc_dropout_eval.py` derives four candidates: max softmax (baseline), variance-of-top-class, entropy-of-mean-distribution, max-of-mean-distribution.
- [x] **P6.4.3** Evaluate on the existing val set: does using `mean argmax` change any decisions vs single-pass argmax? Does the variance signal correlate with correctness better than the softmax magnitude? Compute the same Brier / ROC-AUC / ECE metrics as P6.2. **DONE 2026-05-21** — see "P6.4 Eval Outcome" below.
- [x] **P6.4.4** **Decision gate**: if the MC-dropout uncertainty signal beats softmax-magnitude as a correctness predictor by ≥ 0.05 AUC, wire it as the fallback gate (cheaper than P6.2). If not, record null and rely on P6.2. **DONE 2026-05-21 — GATE FAILS**. ΔROC-AUC = −0.0136 to −0.0697 across the hyperparameter sweep. Hypothesis B archived; rely on P6.2 verifier head.

###### P6.4 Eval Outcome (2026-05-21)

**Verdict**: clean null. Test-time MC-dropout uncertainty is **worse** than the existing softmax magnitude as a correctness predictor across all three metrics (ROC-AUC, Brier, ECE) and across a hyperparameter sweep. Hypothesis B (Hypothesis B from `research/deep-dives/2026-05-21-recursive-reasoning-routing.md`) is empirically falsified.

**Setup**:
- Weights: `autopilot_checkpoints/20260416_134815/routing_classifier_weights.npz` (Phase 1 production weights, 140,872 params)
- Data: 157,520 samples × 1031-d features extracted from cached `sessions/reembedded.npz` via `extract_training_data.py`
- Val split: 31,504 samples (seed=42, val_split=0.2 — identical to training-time split)
- Deterministic val accuracy: **91.99%** (matches the handoff's stated 92% figure precisely — load and split reproducible)

**Hyperparameter sweep results** (correctness label = "deterministic argmax matched val label"):

| Config | Det val acc | MC mean val acc | Flip rate | Best MC predictor | Best MC AUC | Baseline AUC | ΔROC-AUC | Gate (≥ +0.05) |
|---|---|---|---|---|---|---|---|---|
| p=0.05, N=20 | 0.9199 | 0.9157 | 2.14% | mc_max_prob_mean | 0.9101 | **0.9237** | −0.0136 | FAIL |
| p=0.10, N=10 | 0.9199 | 0.9068 | 4.22% | mc_max_prob_mean | 0.8693 | **0.9237** | −0.0544 | FAIL |
| p=0.20, N=20 | 0.9199 | 0.9030 | 5.16% | mc_max_prob_mean | 0.8540 | **0.9237** | −0.0697 | FAIL |

Monotone pattern: lower dropout rate → MC predictors closer to (but still below) baseline; higher dropout → MC predictors substantially worse. **No setting beats softmax magnitude** on ROC-AUC, Brier, or ECE.

**Mechanistic interpretation**: the classifier was trained **without** dropout (`routing_classifier.py:268-326` — pure mini-batch SGD with cosine LR decay, no dropout in train or forward). Test-time dropout is therefore **noise injection** into a network that wasn't conditioned to be invariant under it — variance reflects "how much does the model wobble under random feature suppression?" which turns out to be weakly correlated with correctness (best AUC 0.91) compared to "how confident is the model in its top class?" (AUC 0.92). The Bayesian-posterior interpretation of MC-dropout (Gal & Ghahramani 2016) explicitly requires train-time dropout — applied without it, MC-dropout is just feature-noise sensitivity, and feature-noise sensitivity is not a calibrated correctness signal on this model.

**Implication for Phase 6**: Hypothesis B closed. The verifier's information-theoretic edge identified in the P6.1 audit (joint conditioning on `(embedding, action)` rather than the marginal `p_softmax(a|x)`) remains the only candidate route to improving correctness prediction beyond the existing per-class threshold. **Proceed to P6.2.**

**Re-opening criteria for Hypothesis B**: if the classifier is ever retrained **with** dropout (i.e., adding dropout to the train-time forward pass), re-run this eval. With train-time dropout, MC-dropout becomes the Bayesian posterior approximator it is in the literature, and the result may flip. Until then, the falsification stands.

**Artifacts** (preserved for re-runs):
- `orchestration/repl_memory/routing_classifier.py:163-200` — `mc_predict()` method (added 2026-05-21)
- `scripts/graph_router/mc_dropout_eval.py` — eval harness (created 2026-05-21)
- `/tmp/p6_4_training_data.npz` — ephemeral training NPZ (regenerable from `reembedded.npz`)

**Files**:
- Modified: `orchestration/repl_memory/routing_classifier.py` — add `mc_predict()` method (small change, <50 LoC)
- New: `scripts/graph_router/mc_dropout_eval.py` — evaluation harness

**Why this runs in parallel to P6.1**: P6.4 is a property of the *existing* MLP and doesn't depend on the verifier architecture question. If P6.4 already explains away the verifier idea (i.e., MC-dropout is a sufficient calibrator), that's a faster falsification path than P6.1's analytical audit. Run both; let whichever finishes first inform the other.

###### Phase 6 dependency graph

```
P6.1 (audit, no code)  ──pass──► P6.2 (MLP verifier) ──pass──► P6.3 (recursive verifier)
        │                                │
        └── parallel ────────────────────┤
                                         │
P6.4 (MC-dropout proxy, no dep) ─────────┘
                                         │
                                         ▼
              Either P6.2 OR P6.4 surviving its decision gate is sufficient to
              justify continued Phase 6 investment. If BOTH yield null results,
              archive Hypothesis C and Hypothesis B; Phase 6 closes.
```

###### Phase 6 open questions

1. **Correctness label semantics**: is "no escalation within this session" the right correctness label, or does that conflate "MLP was right" with "MLP was wrong but user gave up"? P6.2.2 must resolve this — likely needs a more nuanced label like "MLP routed and the downstream task completed with quality ≥ threshold".
2. **Joint vs cascaded training**: should the verifier be trained jointly with the classifier (shared backbone) or as a fully decoupled head? P6.2 starts cascaded (frozen classifier, train verifier on its outputs) for engineering simplicity; joint training is a follow-up if cascaded plateaus.
3. **Verifier latency budget**: if P6.2 verifier adds ≥ 2ms per decision, the orchestrator may want to skip it for low-stakes routes. Per-route gating policy is a P6.2.5 question, not a P6.2.1 question.
4. **Interaction with [DAR-2](routing-program.md) contrastive sharpening**: if both DAR-2 and a verifier are active, do their decision boundaries reinforce or contradict? P6.1.3 audit must address this.

##### Retraining Strategy

**Batch retraining, manually triggered initially.** Training on 174K samples is <1 minute on CPU. Automate frequency after understanding distribution shift patterns.

Future: automatic trigger after N new decisions, idle-window scheduling, staleness detection.

---

#### Relationship to Existing Systems

| System | Relationship | Impact |
|--------|-------------|--------|
| **Episodic memory** | Becomes write-only during inference (read only for retraining) | None — still logs everything |
| **Autopilot** | Consumer of episodic data, separate from MLP | None — independent data flows |
| **SkillBank** | Complementary: SkillBank = "what model should do", MLP = "which model does it" | None — different optimization axes |
| **Q-Scorer** | Continues scoring outcomes → feeds episodic store → feeds MLP retraining | None — unchanged |
| **HybridRouter** | MLP classifier fast-path already wired (line 767) | Toggle via feature flag |

---

#### Open Questions

1. **Class imbalance** — frontdoor is 43%. Start with class-weighted loss, measure per-class recall.
2. **SSM probing viability** (Phase 2) — no literature on probing Mamba/Jamba hidden states. Phase 1.5 de-risks.
3. **Mean-pool vs attention-pool** (Phase 2) — test both for hidden states across token positions.

---

#### Key Files

All orchestrator paths relative to `/mnt/raid0/llm/epyc-orchestrator/`.

| Component | Path | Status |
|-----------|------|--------|
| **MLP classifier** | `orchestration/repl_memory/routing_classifier.py` | EXISTS — 2-layer numpy MLP, ~200K params |
| **Training script** | `scripts/graph_router/train_routing_classifier.py` | EXISTS |
| **Data extraction** | `scripts/graph_router/extract_training_data.py` | EXISTS — needs label normalization (P1.1) |
| **Classifier weights** | `orchestration/repl_memory/routing_classifier_weights.npz` | EXISTS — needs retraining |
| **HybridRouter fast-path** | `orchestration/repl_memory/retriever.py` (line 767) | EXISTS — wired with fallback |
| **Feature flag** | `src/features.py` (line 108, `routing_classifier`) | EXISTS — default OFF |
| **A/B test scaffold** | `scripts/graph_router/ab_test_classifier.py` | EXISTS |
| **Autopilot hooks** | `scripts/autopilot/species/structural_lab.py` | EXISTS |
| Episodic store | `orchestration/repl_memory/sessions/episodic.db` | 175K memories (2026-04-04 to 2026-04-15) |
| Q-Scorer | `orchestration/repl_memory/q_scorer.py` | Reward computation |

#### Completed Scope

Moved verbatim on 2026-09-27 to [`../completed/learned-routing-controller-completed-through-2026-09-27.md`](../completed/learned-routing-controller-completed-through-2026-09-27.md):

| Moved section | What it holds |
|---|---|
| Research Intake Updates 2026-04-26 / 05-19 / 06-20 / 07-02 | ES-cluster training paths, offline reward-model stack (intake-706/716/717/719), tabular-FM parked reference |
| Implementation checkpoint 2026-06-21 | the label-normalization and retrain implementation record |
| P4.5 Phase A/B outcomes (2026-06-26), P4.6 role dropout (2026-06-27) | two NULL results, summarized by the 2026-07-21 deep-dive correction below |

#### Research Intake Update — 2026-07-14 — Knowing-Using Gap caveat (intake-814)

Reference/caveat only — **no phase, no checkbox, unfreezes nothing.** Attaches to the **"Key Insight: Episodic Memory Becomes Write-Only"** thesis above.

- **[intake-814] "…Why Memorized Knowledge Fails to Generalize in LLM Finetuning"** (arXiv:2607.08393; credibility 3; verdict worth_investigating) formalizes a **"Knowing-Using Gap"**: knowledge fine-tuned into transformer weights is memorized but fails multi-hop *chaining* ("knowledge-circuit misalignment").
- **Why it's filed here:** this controller is EPYC's one **memory→weights** path — `routing_classifier.py` is a 2-layer MLP distilled (Q-weighted cross-entropy SGD) from episodic traces, i.e. the write-only-memory replay buffer becomes training data. The paper studies exactly that direction.
- **Why it gates nothing:** the Gap is about **multi-hop factual chaining**; our router is a **single-step discriminative action classifier** — no factual recall, no chaining to misroute — so the failure mode does not transfer to the current head. **Watch only if/when** a future phase moves the routing head toward parametric factual/multi-hop injection (e.g. distilling reasoning, not just an action label). Until then it *corroborates* the write-only-memory design rather than challenging it. Per this file's standing directive, this is **not** filed under `retrain-routing-models.md` / `decision-aware-routing.md` (both expansion-FROZEN).

#### Deep-Dive Correction — 2026-07-21 (Signal-bound, not policy-bound; plus the one usable idea from intake-866)

See the fuller root-cause writeup in [decision-aware-routing.md](routing-program.md) (2026-07-21 section). Summary as it bears on this handoff: the five-null streak (P4.1.3, P4.2, P4.5, P4.6, DAR-4b) is **signal-bound, not policy-bound**. Verified 2026-07-21: 88.8% of routing memories sit at `q_value=1.0`/`update_count=0`, 99.69% were never TD-updated, and outcomes are 90.3% success. No policy class can exceed the mutual information between features and a saturated outcome. **Train a bigger policy on this signal and you bank a sixth null.**

**Explicit negative on the LM-as-router idea.** intake-867 reports Qwen3.5-4B at **0 pass@16** on an RLM harness without cold-start SFT — but the failure mode is *harness conformance* (malformed `FINAL(...)`, runaway tool calls), not decision difficulty. Routing is a 5-way categorical with no output-format failure mode possible. Fine-tuning an LM to emit role names would pay that conformance tax (parse failures, format drift, tokens, tens of ms) to produce what `routing_classifier.py` already serves in **<0.1ms from ~200K numpy params** at 81.0% val acc / 94.4% precision at 61.6% coverage. **Do not do it.** (This says nothing against a discriminative head on richer features — that transfer is void, since a 4B autoregressive LM and a 200K-param MLP are not on the same difficulty scale.)

**The one usable idea from intake-866.** Its "locally in-distribution" (LID) principle is unfalsifiable as stated — the author concedes he cannot formalize it. But his Appendix ships a *substitute* that is directly liftable: nearest-training-trajectory distance. Applied to us that is a **per-role competence/familiarity feature**, computable with zero inference from data already on disk:

`COMP_r(x) = max cos(e(x), e(m))` over memories with `action=r, outcome=success`, where `e(·)` is the 1024-d BGE vector already stored in `sessions/embeddings.faiss` (~2.7GB, one vector per row). `retriever.py _retrieve()` L235-326 already performs this FAISS lookup at runtime — only a per-role restriction and success filter are new. Feature would concatenate onto the existing 1031-d input at `routing_classifier.py:61`.

- [x] Competence-region probe (cheapest experiment in the program; zero inference): compute `COMP_r(x)` **leave-one-objective-out** (mandatory — with only ~2,384 distinct objectives an in-sample NN finds a near-duplicate at cos≈1.0 and scores AUC≈1.0 for free), report AUC for `success | role` plus argmax accuracy on the 622-objective counterfactual set. **Decision flip:** AUC ≤0.55 → record the null, close the intake-866 line, and note that both the difficulty axis and the familiarity axis are flat. AUC ≥0.65 → first routing feature with real spread in the program's history; concatenate at `routing_classifier.py:61` and re-run the standard val split. ✅ 2026-07-22
- **[declined: ws58 2026-11-03 content-review: resolved 2026-07-29 by its own text (retained only the testable per-role feature)]** Do NOT import intake-866's "harness induces an equivalence relation" framing — it is unmeasured, and the author concedes the isomorphism leaks in practice. ✅ 2026-07-29 — retained the directly testable per-role nearest-success-trajectory feature only; no equivalence-class claim enters routing policy or acceptance criteria.  *(Restored to `- [ ]` 2026-08-11 by `mainC` — standing constraint with no completion state; the dated evidence below is kept, the rule is live again.)*

#### Research Intake Update — 2026-09-17 (candidate-scoring arm; intake-1462/1487)

- [x] **LRC-TD-1 — Candidate-scoring arm for the learned controller.** Compare the per-call label-set pattern (option-as-query head intake-1462 or native token logits intake-1487) against the current classifier on the recorded routing corpus; treat as unadopted until TD-2 reports calibration. (Owner stub `typed-decision-plane.md`, RTG-56.) ✅ 2026-09-29 — folded into TD-11 (`typed-decision-plane.md`; operator ruling Q5: TD-11 is the single typed-routing owner). The classifier comparison and the option-as-query arm moved there.


#### Research Intake Update — 2026-10-04 — P4 observed-outcome routing

Filed from the operator-approved [decision-tools plan](../../research/intake-stage3-plan-2026-10-03-decision-tools.md)
at `3911ec91`. Objective: honor the requested training-data source and test routing under changing role availability
without treating unobserved alternatives as failures. The source/filter repair is independent of the experimental
scorer. Scorer implementation precedes its cached comparison. Existing LRC-1/2 freezes remain; TD-11 owns typed routing.

- [x] **LRC-RI-EXTRACT-SOURCE — Make routing-data extraction honor explicit source and update-count filtering.** Use the requested DB by default; select an NPZ only through the existing explicit embeddings-file argument. Reject a positive min_updates when the selected snapshot cannot enforce it, or enforce it from an actual captured update-count array. Add DB/NPZ branch tests proving the effective source/filter and included/excluded counts; retain action/feature ordering and weights. No live-store mutation, re-embedding, training or routing enablement. ✅ 2026-10-24

**Extractor acceptance.** With a default cache present, a DB request still uses the test DB. Explicit snapshot
selection works at zero threshold; a positive threshold without update counts refuses before output. Equivalent
eligible DB/snapshot fixtures preserve row/action/feature semantics. Existing callers explicitly select their snapshot
or retain DB behavior. Tests use temporary stores and small arrays. Consumers are extraction and the existing
training CLI; frozen learning tasks remain frozen.

- [x] **LRC-SDM-ACTION-SCORER — Add an experimental availability-aware task/action outcome scorer at the existing HybridRouter seam.** Provide an optional injected score_candidates(features, admissible_roles) returning independent estimated correctness rates plus explicit unsupported/abstain states; leave it off in production. Preserve the existing 1,031-column ordering and append semantic action identity (1,037 historical inputs for this six-role screen). Bind actual decision-time covariates explicitly at the live seam; do not silently equate the historical suite-derived proxies with runtime values. Fit only observed question/role cells against raw role_correctness; unseen targets contribute no loss, while observed zero remains a real failure. Weight each question equally across its observed cells unless genuine per-role counts are recovered; total_appearances is not a per-role count. Start with the already-installed CPU HistGradientBoostingRegressor and training-context-only preprocessing reused at prediction. Do not use Q, realized outcomes/latency or test support masks as prediction features. Preserve actual missing covariates as missing, without fabricating retrospective values. Filter against the actual admissible menu and existing preferences/capabilities; use the existing cost policy among supported roles meeting a calibration-set quality floor, otherwise return the incumbent fallback. Keep rates distinct from softmax confidence; invalid rates/errors abstain. Define support from training/calibration evidence, not a finite prediction: a role needs at least 20 independent observed training groups and 10 independent observed calibration groups for this historical screen, plus a calibration quality bound meeting the existing quality floor; otherwise it is unsupported. These are sparse-evidence refusal minima, not sufficiency for calibration. The confidence/precision budget can require more, never fewer on the basis of test masks. Test sparse roles with plausible numeric predictions, availability changes, unknown roles, preference precedence, feature ordering, missing-versus-zero semantics and unchanged incumbent routing when the scorer is disabled. ✅ 2026-10-29 — implemented and published on orchestrator main `517e608324efcbfd4bcb9ebcbb773abe2317d754`; 57 focused/routing regression tests pass, including observed masks, group support, verifier enforcement/shadow and unchanged flag-off fallback. Production flag remains off; cached comparison and adoption are separate. [no-belief: source implementation and regression tests]

- [x] **LRC-SDM-CACHED-SCREEN — Run one grouped observed-outcome challenger comparison on the existing P4.5 cache.** Join arrays and JSONL by verified qid and semantic role mapping; require roles_seen, never correctness>0 as the observation mask. Freeze a suite-stratified 60/20/20 train/calibration/test partition by question/near-duplicate group before expanding to action rows. Refit the existing NumPy MLP architecture and the one CPU tabular recipe on the same training partition through the explicit-partition _train_arm helper; label the cache's hard-label arm a historical P4.5 comparator, not a reproduction of production Q-weighted training; retain existing staged weights only as a descriptive reference unless their disjoint training lineage is proven. Fit preprocessing on train, choose thresholds on calibration, open test once. Use squared_error, max_iter=100, max_leaf_nodes=7, min_samples_leaf=20, l2_regularization=1 and early_stopping=False; include a train-only role-mean baseline and shuffled-label negative control, with no sweep. Retain raw fit error separately from policy-choice quality. An unobserved selected action has unavailable outcome, not zero or an invented prediction-as-label. Count invalid embeddings, unsupported selections and abstentions over every test question. Recover only a bounded set of original existing trial records if the aggregate cannot answer the question; never retune repeatedly on the opened test or overwrite current weights. ✅ 2026-10-29 — completed once as a data-limited descriptive diagnostic; [original evidence](../../artifacts/research/lrc-sdm-cached-screen-20261029/README.md), root `8c77b3f5fc4fb96840c1e7cd0717c3c3cdfd6584`. Paired outcomes cover 57/106 questions (53.8%, 57 groups); paired mean gain and bootstrap lower bound are both 0.0000, below the predeclared coverage/gain criteria. No pilot or serving change. Raw fit error is reported separately. [belief: cc]

**Frozen inputs and evidence limits.** The approved plan records a historical inventory of 540 rows × 1,031 features,
six semantic roles and seven zero embedding rows. NPZ SHA-256:
`eb456857e6e667bb87aaa791ba55e765ca231e0fdee58976006d7673a12351cd`; labels JSONL SHA-256:
`39e3fc21acee3f356e4ece6d5fd1baa4a01dfc546d5fc0394635e76d2a1b7112`.
This is inventory, not quality evidence. The current builder already rejects zero embeddings; this filing adds no
new builder-defect task. Cached task/image proxies and prompt/context character lengths are not attested runtime
TaskIR values. Historical roles lack served model/configuration identity, per-role counts and timestamps.

**Six controls and decision.** Freeze both source hashes, group partition, recipes, source code, label mapping and
historical weight references. Compare against the existing MLP architecture refitted on identical training groups;
potentially contaminated staged weights are not the deciding baseline. Keep per-qid/group menus, rates,
choices/fallbacks, observed-label availability, raw observed rates, errors and timings. Calibration/test groups remain
disjoint and are never selected using outcomes; preprocessing is train-only. Report all test questions and the paired
outcome-evaluable subset separately.

Before collection record a sensitivity/power or interval-width budget against available observed cells and the
operational benefit/cost basis for continuing. Predeclare at least 30 independent matched test groups, at least 90%
outcome-evaluable choice coverage, and paired observed correctness-rate gain ≥2pp with a positive group-bootstrap
95% lower bound before proposing a current-stack pilot. Thirty groups is a resampling minimum, not adequate precision;
90% limits selective comparison; 2pp is the proposed historical minimum useful gain, not a measured economic threshold.
If the cache cannot support the budget, stop at a descriptive diagnostic. Otherwise classify unmet criteria as
data-limited, null or inconclusive as appropriate; missing alternate outcomes cannot establish a negative technique
result. Aggregate-rate comparisons certify neither trial-level calibration nor production gain. A pass yields an
exact candidate and bounded current-stack pilot proposal, not deployment. Recover original counts/model identity/time
fields before a current-stack learning claim; that later comparison uses the actual serving incumbent.

**K10 and M4 — retained qualifications and broader follow-ons.** Train-context fitting and immutable recipe/cache
reuse address only part of leakage; decision-time feature availability, related-case contamination and outcome-derived
inputs require separate checks. Wrapper Apache licensing does not relicense TabFM assets; exact intended use must meet
their separate terms. Eager operator paths and `is_cuda` predicates do not establish ROCm compatibility, and relational
sampling has separate backend dependencies. Classifier replications and tabular benchmark results do not establish
EPYC routing utility. Gradient-attribution/missingness reports are qualified contributor observations, not causal
explanations or proof that current predictions fail.

The isolated installed-CPU design diagnostic is allowed under the existing probe posture; it does not reopen LRC-1
autopilot-data retraining or live routing expansion. Native SDM remains a backend option after a deciding result,
subject to its exact assets/runtime/operators and eligibility. A current-stack pilot needs its specific owner/window
and promotion conditions. A useful follow-on encountering an operator gate remains a concrete proposal naming the
required amendment/cutover. No relational sampler or explanation platform is added. Risk calls for safeguards and
does not dismiss the candidate. Before the first decision-bearing screen, land its native write-side capture under
VB-RI-OPS-WIRE; reuse ClaimTuple and the sole shared grader.

Record discussion: intake-1852#record, intake-1881#record, intake-1888#record, intake-1889#record and
intake-1890#record. Source/code grounding is pinned in the approved plan; no application execution is established.

#### 2026-09-26 audit follow-ups (code + live-process audit)

- [ ] ❄ FROZEN 2026-09-27 — resume only once autopilot has trained on the swapped stack AND UFH-13 re-opened (operator ruling 2026-09-29) — **LRC-1 — distill autopilot-generated data into episodic memory as MLP training data** (operator
  - 2026-11-09 audit: NAR: no autopilot-generated data since 2026-08-09 (last run 1503). Projection design is zero-inference but frozen; it also needs the era (post-E18, post-07-23) and the EG2 decision before any distillation. HOLD list.
  direction 2026-09-26). Define the projection from autopilot trial records to routing memories (task, chosen
  role, outcome), keep it separate from live write-back (see `episodic-memory-integrity.md` M-21), and
  measure whether a retrain with it beats the current 81.0% retrain on the held-out split.
  ❄ FROZEN 2026-09-27 (operator, narrowed plan): retraining the routing MLP tunes a component before the thesis experiment says routing is where the value is; unfreeze trigger (operator ruling Q2, 2026-09-29; it replaces "the UFH-13 thesis experiment reaches a pre-registered verdict of SUPPORTED, and the operator names a workload class where A2's escalation gain lives", which cannot fire while UFH-13 is PARKED): autopilot has trained on the swapped stack AND UFH-13 re-opened. The box stays open: frozen is not done.
- [ ] ❄ FROZEN 2026-09-27 — resume only once autopilot has trained on the swapped stack AND UFH-13 re-opened (operator ruling 2026-09-29) — **LRC-2 — resolve the inert `ORCHESTRATOR_FRONTDOOR_VERIFIER_GATE=1`.** It is set live, but the
  - 2026-11-09 audit: SV: still inert (`src/api/services/routing_models.py:137` plus `routing_classifier` OFF at `src/features.py:133`). Check for the relaunch: `scripts/server/orchestrator_stack.py:2768` does `env.setdefault("ORCHESTRATOR_FRONTDOOR_VERIFIER_GATE", "1")`, so a stack relaunch sets the env ON while the gate stays inert; either unset it or tie it to the classifier flag. A config edit; frozen only by the marker.
  verifier (`src/api/services/routing_models.py:131-149`) only runs in the classifier path, which is off
  (`routing_classifier`, `src/features.py:133` (was :123)). Either unset it so the environment matches behaviour, or tie
  it to the classifier rollout decision above; do not leave a live flag that does nothing.
  ❄ FROZEN 2026-09-27 (operator, narrowed plan): the flag is inert (classifier path off), so it costs nothing while frozen; resolve it with the classifier rollout; unfreeze trigger (operator ruling Q2, 2026-09-29; it replaces "the UFH-13 thesis experiment reaches a pre-registered verdict of SUPPORTED, and the operator names a workload class where A2's escalation gain lives", which cannot fire while UFH-13 is PARKED): autopilot has trained on the swapped stack AND UFH-13 re-opened. The box stays open: frozen is not done.

#### Research Intake Update — 2026-09-26 (orchestration prior art: declines + a rollout precondition)

**DECLINED — an HW-Router-style learned live latency predictor or an SFS engine-snapshot simulator for role
selection (C1-A4).**
- Neither was compared against a static latency prior. HW-Router's baselines are priced in money and it has no
  live-signal ablation (intake-1797#04); SFS has no static arm (intake-1798#04).
- SFS needs per-iteration engine snapshots from a forked server, which the frozen kernel forbids (intake-1798#06).
- Reopen only if decision-aware-routing.md DAR-LAT-3 adopts its live arm (A2).

**Already satisfied (C1-A6).** The routing classifier is one ~70K-param MLP forward at <1 ms (:583), not a serial
generative scorer. RouteBalance's deployment ladder (intake-1796#04) is a caution only if a generative scorer is ever
put on the /v1 hot path; then it must be batched or amortised.

**Correction — 2026-10-04:** that conclusion covers the MLP forward only, not embedding/retrieval
or event-loop concurrency. The current async `/chat` handler enters routing synchronously; learned
retrieval and classifier feature construction embed before their decision. This exposes an unchecked
blocking path, not evidence of measured production saturation. The retained paragraph above is
historical rationale, not a closure of the complete route. See the
[main-reviewed retrospective](../../docs/reviews/research-intake-practical-applications-20261004.md).

- [ ] **LRC-RI-CONCURRENCY — PROPOSED: qualify and repair blocking embedding/retrieval in the complete routing path.** Recover C1-A6 with a zero-inference conformance probe through the actual `/chat` routing seam and classifier feature construction, using a controllably delayed fake embedder and an independent event-loop sentinel. If routing blocks the sentinel, isolate the blocking operation behind an asynchronous boundary while preserving shared-router synchronization, request-local metadata, deterministic route results, cancellation and error propagation. Acceptance: the probe detects incumbent blocking; the repaired path permits sentinel progress while embedding is pending and accounts for every concurrent request. MLP-only timing cannot close it. Use producer-bound fixture/read-set digests and exact decided propositions before a decision-bearing probe. This filed proposal changes no routing policy, reopens no DAR-LAT/learning freeze and authorizes no production rollout. Record discussion: intake-1796#record.
  - 2026-11-09 audit: SV + premise changed: the embedder now goes through the embedding pool client (`src/embedding_pool/policy.py`, neighbour cap, UFH-12), so the blocking boundary differs from C1-A6. Re-read the current seam before scoping the fake-embedder probe. Zero inference, standalone code work.

**Rollout precondition (prose).** The MLP fast path (orch `hybrid_router.py:405-490`) returns before the selection
score. If `routing_classifier` is ever enabled (LRC-2), first apply the DAR-LAT-2 saturation guard as a post-check on
the fast-path result (around :411). Otherwise saturated roles bypass the guard.

**Evaluation caution (2026-09-26, intake-1821#7).** In EvoHarnessBench's delegation study, specialist-selection precision stays around 90%, yet 78–86% of trials that reach every required specialist still fail their verifier: a metric that scores only role choice misses the dominant failure. GPT-5-only and enterprise-workflow-only, so a hypothesis for our traces. If LRC-2 is evaluated for rollout, report realized task outcome beside role agreement; decision-aware-routing.md DAR-LAT-3 already grades realized quality per request.

#### Evaluation protocol: cost-of-pass objective needs a reliability floor (ROUTE-COP-GUARD, 2026-10-21)

Any learned-router or controller evaluation that reports or optimises the cost-of-pass frontier (`cost_per_attempt / pass_rate`) applies the floor in `routing-intelligence.md` section "Router objective: cost-of-pass needs a reliability floor" before a candidate counts as on the frontier:

- Declare `tau` (and `k` if the surface retries) before the run; admit only candidates with pass rate (or pass^k) at or above `tau`; list the excluded candidates and their unguarded cost-of-pass in the report.
- A cheap near-random policy is the standing adversarial case and is included in every frontier run as a control candidate; the evaluation fails if it is admitted.
- State that retries are not independent when context carries over: a carried-context surface reports its measured k-attempt pass rate, not `pass_rate ** k`.

Code and test: `epyc-orchestrator` `scripts/analysis/cop_frontier.py`, `tests/unit/test_cop_frontier.py`.

## Track: model-capability-descriptors
<!-- gate: none -->

> Folded from `handoffs/active/model-capability-descriptors.md` @ `b33c4e7a5fd1` on 2026-11-02 (BRF-T1-F26, route 1a, operator D1/D5; retired row RTG-17 → RTG-09). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Model-Capability Descriptors: The Model-Agnosticism Interface

**Status**: W1/W2 descriptor compile is effectively clean through `3e8121d`: planner-signature consumer landed in `73ed436`, seeder role discovery landed in `2e31055`, q_scorer alias-quality propagation landed in `9ed177d`, architect/REAP quality landed in `837829f`/`2ea28dd`, GGUF context landed in `b8477b0`, thinking-control evidence landed in `865b2b1`, shared-runtime alias mismatches are now provenance rather than blocking gaps, and VL projector requirements are descriptor-native for Qwen2.5-VL/Qwen3-VL. `03ed49f` also closed the temporary retired-architect enum waiver path. W3 first-consumer migration is complete through launch command construction in `7121f38`; W4 now has no-inference data-only swap coverage in the stack-change promotion gate for both frontdoor and worker candidate swaps, and the replay meta-agent now has an explicit archive-backed candidate-swap replay report path. The W5 cascade tail remains gated.
**Created**: 2026-06-12
**Updated**: 2026-07-26
**Priority**: MED — compiler can start today (no blockers); the Phase-3 cascade tail is GATED and predicted to stay so
**Spec**: [fable5-findings-02-impl-plan.md](../completed/fable5-findings-02-impl-plan.md) Phase 2 (+ Phase 3 for the gated tail) and [fable5-findings-02-routing-decision-architecture.md](../completed/fable5-findings-02-routing-decision-architecture.md) §3 — read both before claiming any waypoint
**Related**: [retrain-routing-models.md](routing-program.md#track-retrain-routing-models) (descriptor-conditioned predictor is the post-retrain shape), [routing-truth-restoration.md](../completed/routing-truth-restoration.md) (its W5 stopgap is replaced here; its W8 gates the tail), [MEASUREMENT.md](../../MEASUREMENT.md) §5 item 5 (registry provenance comments are the ONLY measurement witness — never reformat them away)

#### 2026-07-26 Staleness Review

W1-W4 and the W5 planning/freshness work remain landed as summarized in the
[master handoff index](master-handoff-index.md). The unified-cascade tail is
still blocked by the [design-backlog triage](../completed/design-backlog-triage-2026-07-23.md)
gate: DAR regret is `0.00%`, below the required `>=5%`, and no operator
authorization exists for a cascade rollout. Keep that tail gated.

#### Why

Routing intelligence is keyed to role names and dies on stack change (the
2026-05-25 reset; standing rule: index by model, never by role). The research
registry already holds per-model benchmark records the router never reads —
the single missing interface between months of benchmarking and the serving
system. A versioned capability descriptor per model makes a model swap a data
update: the predictor transfers, launch args travel with the model, routing survives.

#### Waypoints

- [x] **W1 — schema** (~1 day): `orchestration/model_descriptors.yaml`, one entry per MODEL (canonical id `family-params-quant`), NEVER per role; fields per spec 2.1: quality suite_vector with source/eval_protocol, speed with bench provenance, acceleration (spec_type, draft_compat, enable_thinking, kv), serving (binary, numa_policy, mlock), descriptor_version + compiled_at. Landed live in `epyc-orchestrator` as `17731a7` (`Add model capability descriptor seed`), a current-lineage cherry-pick of branch-ready `578eb8a`. W1 deliberately records role/server conflicts as explicit `known_gaps` instead of resolving them by hand.
- [x] **W2 — compiler** (~2 days): `scripts/registry/compile_descriptors.py`; sources = research registry + lean registry + bench artifacts; REFUSES to emit a descriptor with missing load-bearing fields (lists gaps instead); runs at stack launch (compose with the existing `--compile-registry` path) and on registry change; converts free-text provenance comments into structured `measured: {date, protocol, value}` fields. Implementation landed live as `86a7387` (`Add model descriptor compiler`) + `545eb57` (`Enrich model descriptors from registry evidence`): default-off `--compile-descriptors`, strict refusal, `--allow-incomplete` diagnostic mode, focused tests, read-only research-registry enrichment for `ctx_max`/thinking evidence, role-endpoint serving evidence for dedicated VL roles, and benchmark-date extraction from nested performance blocks. Follow-ups closed the strict descriptor evidence tranche: GGUF header extraction in `b8477b0`, REAP quality projection in `2ea28dd`, structured thinking-control projection in `865b2b1`, shared-runtime alias provenance in `54b7c77`, and descriptor-native VL projector requirements in `3e8121d`. Generated descriptors now have `status: compiled`; stack prior records have empty `known_gaps`.
- [x] **W3 — first consumers** (~2 days, no router redesign): q_scorer cost model (replaces routing-truth-restoration W5 stopgap), seeder per-role eval config, `orchestrator_stack` acceleration args (spec/MTP/enable_thinking travel with the model), eval-tower/planner model signatures replacing hand-maintained `orchestration/model_quality_signatures.yaml` (stale since 2026-04-16, fed to the planner every trial). First consumer landed in `73ed436`: AutoPilot planner signatures now prefer `orchestration/model_descriptors.yaml`, render descriptor `compiled_at`, keep the legacy YAML fallback, and pass focused tests. Seeder per-role discovery landed in `2e31055`: default/eval role discovery now prefers generated stack priors, restores live `worker_vision` and `vision_escalation` coverage, excludes shared non-default aliases, and preserves registry fallback. q_scorer alias-quality propagation landed in `9ed177d`: `worker_explore` now receives stack-prior quality from live `worker_general`, matching TPS/memory alias behavior. Launch command construction landed in `7121f38`: `orchestrator_stack.py` now prefers generated `orchestration/derived/stack_priors.yaml` runtime/requirements for vision escalation, worker vision, `worker_general` MTP launch, and generic role launch arguments while keeping explicit degraded fallbacks. Acceptance: planner-prompt signatures show descriptor `compiled_at`; stack-change no-inference promotion gate is green at `7121f38`.
- [x] **W4 — simulated model-SWAP CI** (~1 day): replace one role's descriptor with a candidate model's; replay a day of routing decisions + launch-arg generation; PASS = data-only change, zero code edits. Acceptance: passes for 2 candidate models. Current no-inference coverage: the canonical stack-change promotion gate now exercises data-only frontdoor/coder shared-runtime swap, shared alias runtime descriptor provenance, retired-role enum removal, generated operator-summary refresh, q_scorer source provenance, and runtime/context/KV/acceleration drift rejection via `tests/unit/test_stack_change_pipeline_simulated_fixtures.py`. The fixture suite now also covers a second worker candidate swap in the same promotion-gate path, and the replay meta-agent now exposes `MetaAgentWorkflow.generate_candidate_swap_report()` / `--swap-replay` so archive-backed candidate swaps can be replayed directly.
- 2026-06-15: W4 swap-CI coverage expanded in the canonical stack-change
  fixture suite so the promotion gate now also runs inside a swapped worker
  fixture in addition to the swapped frontdoor fixture. That extension keeps
  the current no-inference coverage aligned with generated artifacts,
  promotion-gate execution, and selected consumer movement under two
  candidate models; the replay meta-agent now also exposes a direct
  archive-backed candidate-swap replay report path.
- **[declined: ws58 2026-11-03 content-review: unbounded ("2-3 weeks IF ever opened") with no trigger]** **W5 — GATED tail: unified cascade (Phase 3)** (2–3 weeks IF ever opened): one calibrated bilinear `P(success | task_features, model_descriptor)` (isotonic, ECE-reported, abstain band) + explicit `cost(model, placement_state)` + ω scalarization; cheap-first/escalation/think-harder become arms of the same argmax; 2-week shadow then staged migration per spec 3.3. Gate: DAR-1 regret replay ≥5% AND per-question eval vectors exist (findings-01). Prediction on record: stays gated.

#### Gates & pitfalls

- Registry provenance lives in free-text YAML comments — a reformat DESTROYS the only witness (MEASUREMENT.md §5 item 5); the compiler must read-and-convert, never rewrite the source registries in place.
- Refuse-on-incomplete is load-bearing: silent defaults would re-create the exact stale-signature disease this replaces.
- Sweep-era registry values are demote-to-prior (MEASUREMENT.md §5): re-measure queue ordered by consumer impact, q_scorer first.
- W5 stays closed until BOTH gate conditions hold; no speculative predictor work. Placement/contention is out of scope entirely (separate, working, safety-critical — spec §5).

#### Reporting

Tick waypoints + one-line progress entry; delete the master-index row on completion; numbers via MEASUREMENT.md §2 claim grammar.

#### Progress

- 2026-06-12: W1 branch-ready (`578eb8a`). Added the descriptor seed for 9 deployed/wired local inference targets plus schema tests. Validation: `pytest tests/unit/test_model_descriptors_schema.py -q` -> 4 passed; `ruff check`; `ruff format --check`; YAML type check; `git diff --check`.
- 2026-06-12: W2 scaffold branch-ready (`e7ca893`). Added `src/registry/model_descriptors.py`, `scripts/registry/compile_descriptors.py`, default-off stack flags `--compile-descriptors` / `--allow-incomplete-descriptors`, and compiler tests. Validation: descriptor/compiler tests -> 7 passed; stack-manifest import suite -> 50 passed; `ruff check` on new compiler/test files; formatter check; `py_compile`; live allow-incomplete dry-run -> 8 model descriptors with gaps; live strict dry-run exits 1 with explicit missing-field list.
- 2026-06-12: W2 enrichment branch-ready (`32b8c65`). Compiler now promotes explicit research-registry `max_context` / `disable_thinking` evidence without mutating source registries, extracts nested performance benchmark dates into `measured.date`, marks role-local VL endpoints as serving evidence, and tags `mmproj`/vision roles with `vision` modality. Live allow-incomplete dry-run: 8 deployed descriptor identities, 2 clean (`gemma-4-26b-a4b-it-q4-k-m`, `qwen3.6-35b-a3b-q8-0`); live strict dry-run still refuses 15 residual gaps across 6 identities. Validation: descriptor/compiler/schema tests -> 9 passed; `ruff check`; `py_compile`; `git diff --check`. GitNexus impact/detect-changes could not resolve the model-descriptor worktree despite fresh index/registration; manual blast radius was descriptor CLI + stack start hook + descriptor tests.
- 2026-06-13: W1/W2 landed live on `epyc-orchestrator` `fix/substring-scorer-digit-separators` as `17731a7`, `86a7387`, and `545eb57`. Validation after live cherry-pick: `py_compile`; `pytest -q tests/unit/test_model_descriptor_compiler.py tests/unit/test_model_descriptors_schema.py` -> 9 passed; `ruff check` passed; `git diff --check HEAD~3..HEAD` passed; live `compile_descriptors.py --dry-run --allow-incomplete` passed. `orchestrator_stack.py start --help` exposes `--compile-descriptors` and `--allow-incomplete-descriptors`. W3 next: replace the stale planner model-signature table with descriptor-derived signatures, then move to q_scorer/launch-arg consumers.
- 2026-06-13: W3 planner-signature consumer landed live as `73ed436` (`Use model descriptors for AutoPilot signatures`). `scripts/autopilot/state_store.py` now derives planner model signatures from `orchestration/model_descriptors.yaml` when present, emits descriptor source/`compiled_at`/version, preserves canonical model ids and descriptor known gaps, parses descriptor speed ranges, and falls back to legacy `model_quality_signatures.yaml`. Validation: `py_compile`; `pytest -q tests/unit/test_autopilot_state_store.py tests/unit/test_model_descriptors_schema.py tests/unit/test_model_descriptor_compiler.py` -> 30 passed; `ruff check` on touched state-store/test files; `ruff check scripts/autopilot/autopilot.py --ignore F401`; `git diff --check`; live render smoke showed `_source=orchestration/model_descriptors.yaml; compiled_at=2026-06-12T20:24:22Z; descriptor_version=3_`.
- 2026-06-13: W3 seeder role-discovery consumer landed live as `2e31055` (`Derive seeding roles from stack priors`). `scripts/benchmark/seeding_types.py` now prefers generated `orchestration/derived/stack_priors.yaml` for live seeding role discovery, restores `worker_vision` and `vision_escalation` eval coverage, filters shared non-default aliases, and keeps registry fallback for degraded mode. Validation: direct discovery smoke; `py_compile`; `tests/unit/test_seeding_types_state.py` -> 8 passed; targeted seeding eval -> 2 passed; `tests/unit/test_seeding_consumers.py tests/unit/test_seeding_rewards.py` -> 28 passed; `stack_change_pipeline.py check` OK.
- 2026-06-13: W3 q_scorer alias-quality cleanup landed live as `9ed177d` (`Propagate q scorer quality to worker alias`). `orchestration/repl_memory/q_scorer.py` now propagates stack-prior quality to `worker_explore` from live `worker_general`, matching existing TPS and memory alias behavior and removing that degraded fallback residue. Validation: `py_compile`; `tests/unit/test_q_scorer.py tests/unit/test_bilinear_scorer.py` -> 82 passed; `stack_change_pipeline.py check` OK.
- 2026-06-13: Architect quality evidence landed live as `837829f` (`Project architect quality into stack priors`). Structured `roles.architect_general.performance.quality_score: "2.57/3"` regenerated `model_descriptors.yaml` and `derived/stack_priors.yaml`, projecting `quality_overall: 0.8567` for `architect_general` and `qwen35_122b_q4km`; their known gaps narrowed from quality+ctx to structured ctx only. Validation: `py_compile`; `ruff`; focused pytest -> 124 passed; adjacent pytest -> 211 passed; `stack_change_pipeline.py check --allow-known-gaps` summary ok; procedure enum check OK; stack-change guard default/all-surface passed with expected warnings; scoped diff check passed.
- 2026-06-13: GGUF context projection landed live as `b8477b0` (`Project GGUF context limits into stack priors`). The compiler extracted local GGUF header metadata and projected it into `roles.*.model.ctx_max` for Qwen3-Next 80B, Qwen3.5-122B, Qwen2.5-VL 7B, Qwen3-VL 30B, and REAP-Qwen3-Coder 25B; regenerated descriptors and stack priors removed the `Missing structured ctx_max` warning class. Guard output was 15 known warnings at this point. Remaining gaps then: enable_thinking evidence, REAP quality, and shared-runtime alias notes. Validation: `py_compile`; `stack_change_pipeline.py check --allow-known-gaps`; `sync_procedure_role_enums.py --check`; `stack_change_guard.py`; scoped `git diff --check`; focused pytest -> 124 passed; broader adjacent pytest -> 211 passed.
- 2026-06-13: REAP quality evidence landed live as `2ea28dd` (`Project REAP quality evidence into stack priors`). Existing REAP-25B Claude-as-Judge raw-score evidence from `epyc-inference-research` now populates `roles.reap_25b_frontdoor.performance`: overall `110/183 (60%)`, with suite totals `thinking 14/30`, `general 21/30`, `math 13/30`, `agentic 26/30`, `coder 18/30`, and `instruction_precision 18/33`. Regenerated descriptors and stack priors project `quality_overall: 0.6011` and remove REAP `Missing quality suite_vector evidence` / `Missing overall quality prior`; at that point REAP still had `Missing enable_thinking compatibility evidence`, which was cleared by `865b2b1`. Validation: `py_compile`; `stack_change_pipeline.py check --allow-known-gaps`; `sync_procedure_role_enums.py --check`; `stack_change_guard.py`; scoped `git diff --check`; adjacent pytest -> 211 passed.
- 2026-06-13: Thinking-control descriptor evidence landed live as `865b2b1` (`Add thinking-control descriptor evidence`). The descriptor compiler now supports structured `acceleration.thinking_control` alongside legacy boolean `enable_thinking`, so native/no-toggle/template-ignored behavior can be preserved without forcing a boolean. Registry evidence was added for `ingest_long_context`, `worker_vision`, `vision_escalation`, and `reap_25b_frontdoor`; regenerated `orchestration/model_descriptors.yaml` and `orchestration/derived/stack_priors.yaml` now include `thinking_control` for all descriptors. Enable-thinking compatibility gaps are cleared for ingest, REAP, and VL roles; at that point only shared-runtime alias notes plus the waived retired-role enum surface remained. Validation: `py_compile`; descriptor/schema pytest -> 15 passed; `stack_change_pipeline.py check --allow-known-gaps`; `sync_procedure_role_enums.py --check`; `stack_change_guard.py`; scoped `git diff --check`; adjacent pytest -> 212 passed.
- 2026-06-13: Shared-runtime alias provenance landed live as `54b7c77` (`Treat shared-runtime aliases as provenance`). The descriptor compiler now writes `role_bindings.alias_overrides` for ignored stale role-local model metadata when `server_mode.shared_with` binds an alias to a primary live server; stack priors expose those records under `evidence.alias_overrides`; and `docs/reference/stack-truth-precedence.md` states the precedence rule. Generated descriptors and stack priors now have `status: compiled`, stack-prior role records have empty `known_gaps`, and the guard was reduced to the expected waived production-blocker warning for temporary `ARCHITECT_CODING` enum compatibility. Validation: `py_compile`; focused stack/descriptor/pipeline pytest -> 34 passed; `stack_change_pipeline.py check`; `sync_procedure_role_enums.py --check`; `stack_change_guard.py`; scoped `git diff --check`; adjacent pytest -> 212 passed.
- 2026-06-13: Retired architect role alias normalization landed live as `03ed49f` (`Normalize retired architect role alias`). `Role.ARCHITECT_CODING` is now an enum alias of live `Role.ARCHITECT_GENERAL`; legacy string input `"architect_coding"` still normalizes through `_missing_` / `_LEGACY_ROLE_ALIASES`; and prompt fallback, graph node map, and prewarm special-cases no longer treat coding architect as a distinct live role. Default and strict stack-change guards are clean; `--all-hardcoded-surfaces` now reports only legacy-test and historical-doc mentions for this class.
- 2026-06-13: Descriptor-native projector requirements landed live as `3e8121d` (`Expose projector requirements in descriptors`). `src/registry/model_descriptors.py` now projects `role.model.mmproj_path` into descriptor `serving.requirements.mmproj_path`; generated descriptors carry projector requirements for Qwen2.5-VL and Qwen3-VL roles; and regenerated stack priors preserve those requirements for launch/status consumers. Validation: descriptor/schema/fixture/stack-prior pytest -> 28 passed; `stack_change_pipeline.py check` summary ok with known retired-role all-surface warnings; `stack_change_guard.py --all-hardcoded-surfaces` known warnings only; `git diff --check`; `py_compile`.
- 2026-06-14: W3 launch consumer landed live as `7121f38` (`Use stack priors for launch runtime args`). `scripts/server/orchestrator_stack.py` now prefers generated stack-prior runtime/requirements for vision binary/model/mmproj/cache/flags, `worker_general` binary/model/draft/cache/spec/flags, and generic role binary/cache/KV/spec/reasoning/slot-save launch state, while preserving degraded fallbacks for missing priors. Regression coverage prevents numeric YAML fields such as slots, context, ubatch, draft_max, draft_p_min, and threads_draft from becoming command args like `True`. Validation: `py_compile`; `ruff` with existing legacy launcher `F401/F541` ignored; `git diff --check`; focused pytest -> 54 passed; `stack_change_pipeline.py check --run-promotion-gate` -> descriptors/stack_priors/procedure_enums/promotion_gate/summary ok, nested promotion gate 48 passed, known warning inventory unchanged (`waived_production_blocker=2`, `legacy_test=72`, `historical_doc=25`).
- 2026-06-14: W4 no-inference data-only swap coverage is now part of the canonical stack-change promotion gate. The current fixture set proves generated descriptor/stack-prior/procedure/operator-summary/q_scorer/runtime consumers follow frontdoor/coder shared-runtime swaps, shared alias provenance, retired-role removal, and runtime/context/KV/acceleration drift without production source edits. This does not claim the original day-level routing replay acceptance; that remains the only W4 tail if the gate is required for AutoPilot-proposed Stack-Config swaps.

## Track: retrain-routing-models
<!-- gate: none -->

> Folded from `handoffs/active/retrain-routing-models.md` @ `b33c4e7a5fd1` on 2026-11-02 (BRF-T1-F26, route 1a, operator D1/D5; retired row RTG-29 → RTG-09). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Retrain Routing Models

**Status**: ACTIVE/PARTIAL — BGE repair + current-data MLP retrain completed 2026-06-12; classifier weights are staged, the clean-window rollout harness landed 2026-07-05, and the production flag remains OFF pending operator rollout decision.
**Unblocked by**: `repair_episodic_embeddings.py --repair --servers 90 --batch-size 128 --base-port 8090` completed 2026-06-12. Post-repair diagnose-only report: 291,587 routing memories in DB, 275,960 FAISS vectors, 275,960 `reembedded.npz` IDs, 94.6% FAISS coverage, 94.6% live-overlap, 15,627 orphan IDs, **Status: HEALTHY**. The earlier 0-byte `embeddings.faiss` anomaly was the repair window, not the standing blocker.
**Next sequence**: the clean-window wiring/attestation bracket passed and rolled back in orchestrator `fe270b48`. Live routing remains OFF because `--keep-enabled` was not requested and the artifact is feature-attestation evidence, not routing-quality promotion evidence. Decide explicitly whether to run a keep-enabled bracket, and then decide whether GAT and SkillBank retrains are still justified under the Fable 5 routing freeze.
**Created**: 2026-05-25

#### Context
Episodic memory was reset on 2026-05-25. The routing classifier weights,
GraphRouter GAT weights, and SkillBank skills were invalidated. Normal
FAISS retrieval is active as fallback. The former blocker was not label
volume: by 2026-06-12 the store already held hundreds of thousands of routing
rows, but FAISS/reembedded coverage was stale after reset. The BGE repair is
now complete, so the immediate production-correctness task is to extract
current training data, retrain the MLP classifier, and verify the live flag
cannot silently claim a dead fast path. That repair was staged on 2026-06-12;
the live flag remains intentionally off until the rollout decision.

#### Steps

##### 1. Verify memory + embedding health
```bash
python3 -c "from orchestration.repl_memory.episodic_store import EpisodicStore; s = EpisodicStore(); print(s.count('routing'))"
python3 scripts/maintenance/repair_episodic_embeddings.py --diagnose-only
```

##### 2. Retrain routing classifier (MLP)
```bash
python3 scripts/graph_router/extract_training_data.py
python3 scripts/graph_router/train_routing_classifier.py --batch-size 512
```

**2026-06-12 result**:
- Extracted 275,960 samples / 1,031 features from repaired `reembedded.npz`.
- Label distribution: frontdoor 137,027; worker_explore 43,959; ingest_long_context 36,215; coder_escalation 30,382; architect_general 28,377; no architect_coding/worker_math/worker_vision rows in the repaired set.
- First large-batch pass underfit (58.4% validation accuracy; non-frontdoor classes poor) and was archived at `/mnt/raid0/llm/tmp/routing_classifier_weights_b4096_20260612.npz`.
- Batch-512 pass was promoted to `orchestration/repl_memory/routing_classifier_weights.npz`: 81.0% validation accuracy; per-class validation: frontdoor 92.7%, architect_general 83.2%, coder_escalation 82.0%, worker_explore 47.9%, ingest_long_context 74.3%.
- Full-dataset threshold check: at global confidence >=0.8, coverage 61.6% and precision 94.4%; at >=0.9, coverage 45.6% and precision 97.7%.

##### 3. Verify classifier wiring before enabling
```bash
python3 scripts/maintenance/verify_routing_wiring.py
```

Only re-enable `ORCHESTRATOR_ROUTING_CLASSIFIER=1` after weights exist,
validation is acceptable, and `/config/attest` proves the flag is uniform
across workers.

**2026-06-12 result**: `verify_routing_wiring.py` passed with the promoted
weights and existing verifier head. `/config/attest` still saw 6 workers with
`routing_classifier=false`, so the artifact is staged but not live.

**2026-07-05 follow-up**: Orchestrator `7f5d874f` adds
`scripts/maintenance/routing_classifier_rollout_window.py`, a no-inference,
plan-only-by-default rollout harness. Live mutation requires both `--apply` and
`--confirm-clean-window`; active AutoPilot blocks by default. The harness runs
`verify_routing_wiring.py`, reloads the orchestrator API with
`ORCHESTRATOR_FEATURE_ROUTING_CLASSIFIER=1`, attests sampled `/config/attest`
workers with `attest_flags.py --expect routing_classifier=true`, and rolls back
to `routing_classifier=false` unless `--keep-enabled` is explicit. Plan-only
smoke while AutoPilot was active found API health OK, weights present, and five
sampled API workers still attesting `routing_classifier=false`. Orchestrator
`d59e6532` records the latest plan-only preflight artifact at
`orchestration/reports/routing_classifier_rollout_20260705T052644Z/`: API
health OK, weights present, AutoPilot active, and 4 sampled workers still
attesting `routing_classifier=false`. The subsequent clean-window bracket in
orchestrator `fe270b48` wrote
`orchestration/reports/routing_classifier_rollout_20260705T053117Z/` with
`status=attestation_passed_rolled_back`: `verify_routing_wiring` passed,
`routing_classifier=true` attestation passed, rollback to
`routing_classifier=false` passed, and live routing remains OFF by policy.

##### 4. Retrain GraphRouter (GAT) only if still justified
```bash
python3 scripts/graph_router/train_graph_router.py --epochs 100
python3 scripts/graph_router/onboard_model.py \
    --role test_new_model \
    --description "Validation model" \
    --port 9999 --tps 60.0 --memory-tier HOT --memory-gb 10
```

Fable 5 froze routing-learning expansion until current-traffic DAR-1 regret
reaches >=5% and per-question vectors exist. Treat GAT retraining as
verification/backstop work unless a fresh gate says routing regret is real.

##### 5. Re-distill SkillBank only if trajectory volume and freeze gate pass
```bash
# Dry-run to check trajectory volume
python3 -m orchestration.repl_memory.distillation.pipeline --days 25 --teacher mock --dry-run

# Real distillation (needs ~500 trajectories)
python3 -m orchestration.repl_memory.distillation.pipeline --days 25 --teacher claude

# Verify
sqlite3 /mnt/raid0/llm/tmp/skills.db "SELECT skill_type, COUNT(*) FROM skills GROUP BY skill_type;"
```

##### 6. Enable features
Set in `orchestrator_stack.py` or environment:
```bash
export ORCHESTRATOR_ROUTING_CLASSIFIER=1
export ORCHESTRATOR_GRAPH_ROUTER=1
export ORCHESTRATOR_SKILLBANK=1
```

#### Research Intake Update — 2026-06-10

##### New Related Research
- **[intake-687] "LOLLMS Smart Router Dataset"** (huggingface.co/datasets/ParisNeo/lollms_smart_router_dataset)
  - Relevance: this handoff is data-starved (gated on accumulating ~500+ routing examples). The lollms dataset is **464 labeled query→model-index examples with natural-language rationales** (Apache-2.0) — usable as bootstrap/eval data or a schema/format reference for a generative-router surface.
  - Key technique: synthetic routing-label generation via multi-LLM prompting (TTT Dataset Builder); two reference routers fine-tuned on it (Llama-3.2-1B/3B). Schema is `task_prompt` (task + enumerated candidate-model list with capability descriptions) → `task_solution` (selected index + justification).
  - Delta from current approach: **taxonomy mismatch** — lollms labels are generic public models (GPT-4/Claude-2/CodeLlama/DALL-E/Whisper), NOT our 5-role EPYC taxonomy (frontdoor/architect_general/architect_coding/coder_escalation/worker_explore). Requires a relabel/translation step before training use; the transferable value is the difficulty-tier signal, the prompt-with-candidate-list format, and the rationale field. Verdict worth_investigating — cold-start/reference data, not a drop-in.

##### Deep-Dive Refinement (2026-06-12) — correction: lollms is NOT the unblock
**This retrain is NOT short on labels.** The live `episodic.db` already holds **52K+ labeled routing memories**; the real blocker is **missing BGE embeddings** (FAISS was reset; `reembedded.npz` is a frozen 2026-04-15 snapshot). The lollms dataset cannot fix an embedding gap, and it's the wrong surface: it's generative-router SFT *text* (per-row candidate-list → index+rationale), while our controller is a discriminative **BGE-embedding MLP** (1031-d feature → 8 roles). Its "relabel to 5 roles" is structurally infeasible — the label is a *prompt-relative index into a per-row candidate list*, with no stable model→role map — and synthetic labels would pollute the Q-grounded store. **Unblock path = operator BGE re-embed** (`repair_episodic_embeddings.py --repair` → `extract_training_data.py` → `train_routing_classifier.py`), not lollms. Keep lollms parked only as a TTT-synthesis / generative-router reference. Full: `research/deep-dives/2026-06-12-lollms-smart-router-dataset.md`.

##### 7. Delete this handoff

#### Progress checklist

- [x] Step 1 verify memory/embedding health - HEALTHY post BGE repair ✅
- [x] Step 2 retrain MLP classifier - 81.0% val acc, staged to routing_classifier_weights.npz ✅
- [x] Step 3 verify wiring - passed (attest still routing_classifier=false, staged not live) ✅
- [x] clean-window rollout harness + enable/attest/rollback bracket (orch fe270b48) - passed, rolled back ✅
- **[declined: ws58 2026-11-03 content-review: duplicate — RI-10 is the shadow-to-enforce canary decision]** Operator decision: run a --keep-enabled bracket to actually enable live routing
- **[declined: ws58 2026-11-03 content-review: gated on a regret threshold that is definitionally ~0 under the current metric (L309); GAT retraining on EG2 is owned by harness-program REPL-EMB-R2/R3]** Step 4/5 GAT + SkillBank retrains - only if Fable 5 freeze gate (DAR-1 regret >=5%) justifies
- **[declined: ws58 2026-11-03 content-review: bookkeeping]** Step 7 delete handoff once complete

## Track: tri-role-coordinator-architecture
<!-- gate: none -->

> Folded from `handoffs/active/tri-role-coordinator-architecture.md` @ `b33c4e7a5fd1` on 2026-11-02 (BRF-T1-F26, route 1a, operator D1/D5; retired row RTG-40 → RTG-09). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Tri-Role Coordinator Architecture (Thinker / Worker / Verifier)

**Status**: REFRESHED 2026-06-20 — TR-1, TR-2, TR-3.1, TR-3.2, TR-3.3, and TR-3.4 are complete. The latest report has 10,686 role-bearing rows across 7.822 days, non-degenerate role distribution, and both TR-3.3/TR-3.4 PASS. TR-4/5 remain frozen until DAR-regret and per-question-vector gates reopen routing expansion.
**Created**: 2026-04-26 (via Trinity deep-dive — intake-474, ICLR 2026)
**Updated**: 2026-06-20 (N10 telemetry report refreshed; clean-week and non-degeneracy gates passed)
**Priority**: HIGH (architectural — unblocks Trinity's strongest empirical lever)
**Categories**: agent_architecture, routing_intelligence, cost_aware_routing
**Related**: [decision-aware-routing.md](routing-program.md), [learned-routing-controller.md](routing-program.md#track-learned-routing-controller), [routing-intelligence.md](routing-program.md#track-routing-intelligence), [routing-and-optimization-index.md](routing-and-optimization-index.md)
**Deep-dive**: [`research/deep-dives/trinity-evolved-llm-coordinator-methodology.md`](../../research/deep-dives/trinity-evolved-llm-coordinator-methodology.md)

> **Fable 5 review (2026-06-12, refreshed 2026-06-20)**: the shadow-telemetry keep-or-kill decision was resolved by [routing-truth-restoration.md](../completed/routing-truth-restoration.md) W7: keep the signal and persist it in progress JSONL. N10 follow-through added `scripts/analysis/trinity_shadow_telemetry.py`; the refreshed report `orchestration/reports/trinity_shadow_telemetry_2026-06-20.md` scans 10,868 routing-decision rows with 10,686 role-bearing rows (98.3%), worker 87.0% / thinker 10.4% / verifier 2.6%, and both TR-3.3 clean-week collection and TR-3.4 non-degenerate distribution PASS. TR-4/5 remain frozen per fable5-findings-02 until DAR evidence justifies routing expansion and per-question vectors exist.

---

#### 2026-05-28 Audit Reset — Executor Start Here

This is no longer a fresh stub. The schema, storage field, backfill script, feature flag, classifier, and routing shadow hook have landed. The live work is to prove the shadow classifier produces usable telemetry before any role-aware dispatch behavior changes.

| Gate | Required evidence | Fork |
|---|---|---|
| TR-3.3 shadow telemetry | >= 1 week of production-like progress JSONL rows with `data.assigned_role`, or an explicitly labeled offline replay over representative requests | PASS 2026-06-20: 10,686 role-bearing rows over `7.822d`, 98.3% coverage. |
| TR-3.4 distribution diagnostic | Role distribution is not degenerate and examples match taxonomy intent | PASS 2026-06-20: top role worker at 87.0% (<95%), with thinker 10.4% and verifier 2.6%. |
| TR-4 prompt/dispatch wiring | TR-3.4 pass plus clear per-role prompt templates | If telemetry is noisy, keep flag off and add better logging before wiring. |
| TR-5 A/B | >= N=200/arm on role-sensitive benchmarks | If gains are flat or regressions exceed gate, leave `ROLE_AWARE_ROUTING` default-off and document the negative result. |

Telemetry command:

```bash
uv run python scripts/analysis/trinity_shadow_telemetry.py --log-dir logs/progress --from YYYY-MM-DD --to YYYY-MM-DD --output orchestration/reports/trinity_shadow_telemetry_YYYY-MM-DD.md
```

The report keeps the collection-window gate separate from the distribution gate so a short smoke sample cannot accidentally unlock TR-4/5.

#### Objective

Add a per-call **role axis** (Thinker / Worker / Verifier) to the routing decision, orthogonal to model selection. Today our orchestrator collapses every dispatch to model-selection only — `(model)` — and review/escalation is a pipeline-level concern outside the routing policy. Trinity's evidence is that the role axis is *separable* from agent selection and worth **5–8 points** on benchmarks (their ablation: removing tri-role costs −5 to −8 across LCB/Math500/MMLU/RLPR; removing Thinker alone costs −6.0 on Math500 and −4.57 on RLPR). The change is architectural and *optimizer-independent* — it lands the same regardless of whether the routing head is trained by ES, SFT, or contrastive Q-update.

#### Why this is the gap, not the optimizer choice

Trinity has two orthogonal contributions: (1) sep-CMA-ES as the trainer, (2) `(LLM, role)` as the action space. Our existing routing controller (`learned-routing-controller.md`) and Q-scorer (`decision-aware-routing.md`) work on the model-selection axis. Neither addresses the role axis. The role axis is **independent** — it matters whether we train via backprop or evolution. This handoff isolates the architectural change so it can ship without committing to the optimizer rewrite.

#### Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-474 | TRINITY: An Evolved LLM Coordinator (ICLR 2026, Sakana AI) | high | new_opportunity |

Key Trinity ablation evidence (from deep-dive section 1.5 / paper Table 2):

| Ablation | Δ vs full Trinity |
|---|---|
| Remove tri-role (single role) | −5 to −8 points across all four benchmarks |
| Remove Thinker role only | −6.0 Math500, −4.57 RLPR |
| Final-token instead of penultimate | >−10 on LiveCodeBench |
| Remove SVD-scale FT | −3 to −4 across tasks |

Tri-role removal is the second-largest ablation effect after the feature-position swap.

#### Open Questions (must resolve in TR-1)

1. **Role taxonomy mapping**: Trinity defines *T = analyse/plan/decompose/critique*, *W = act on the task*, *V = check correctness/completeness*. Our existing labels (`frontdoor`, `architect_general`, `coder`, `reviewer`, `worker`) mix model identity with implied role. What is the clean separation? Is `architect_general` a Thinker or a Worker? Is the existing review/escalation pipeline a Verifier turn under another name?
2. **Pool-scale meaningfulness**: Trinity's pool has 7 LLMs with massive specialization variance (GPT-5 vs Gemma-3-27B). Our open-source-only inner pool is narrower. Do tri-role distinctions carry semantic weight at our scale, or do all three roles collapse to "ask the most capable available model"?
3. **Surface area**: does role assignment apply per individual orchestrator call, per multi-turn session, or both?
4. **Termination semantics**: Trinity terminates when Verifier returns ACCEPT (max K=5 turns). Our orchestrator already has retry/escalation logic. How do these compose? Is V acceptance equivalent to passing the existing review gate?
5. **Action space arithmetic**: Trinity uses decoupled `(L+3)`-dim flat logits (independent softmaxes over L LLMs and 3 roles). Should we adopt the same decoupling, or model `L × 3` directly (joint distribution)? Decoupled is cheaper and matches Trinity's evidence.

#### Implementation Phases

##### TR-1: Role Taxonomy Definition (SCOPING — required before TR-2+)

- [x] **TR-1.1** ✅ 2026-05-07 — Role mapping table written. Confirms roles are NOT model-permanent; every model participates in multiple roles depending on context. See "TR-1 Deliverable — Role Taxonomy" section below.
- [x] **TR-1.2** ✅ 2026-05-07 — Verifier as parallel mechanism initially; AND with existing review gate for early termination (TR-4.4). Autopilot telemetry to discover collapse opportunity after 1-2 weeks.
- [x] **TR-1.3** ✅ 2026-05-07 — Decoupled `(L + 3)` flat logits. Matches Trinity AND extends `RoutingClassifier` with +195 params (vs ~200K baseline).
- [x] **TR-1.4** ✅ 2026-05-07 — Role Taxonomy section appended below. All 5 open questions resolved with the user.
- [x] **TR-1.5** ✅ 2026-05-07 — `ROLE_AWARE_ROUTING` feature flag, default OFF. Toggle via `ORCHESTRATOR_ROLE_AWARE_ROUTING=1`.

**Gate**: TR-1 produces a written role schema and is reviewed before TR-2 begins. ✅ **GATE PASSED 2026-05-07** — TR-2 (data layer) is unblocked.

##### TR-2: Data Layer — Add Role to Routing Payload ✅ LANDED 2026-05-07

- [x] **TR-2.1** Extended `RoleResult` (`scripts/benchmark/seeding_types.py:300`) and `RoutingResult` (`src/api/routes/chat_utils.py:67-72`) with `assigned_role: str = "worker"` field. **Naming note:** the field is `assigned_role`, NOT `role`, because `RoleResult.role` already exists as the model-role string ("frontdoor"/"worker_30b"/etc); collision would have silently broken every `RoleResult.role` consumer. Constants + feature flag live in new `src/classifiers/role_taxonomy.py` (TrinityRole enum + `normalise_role` + `role_aware_routing_enabled`).
- [x] **TR-2.2** Schema migration in `episodic_store.py` adds `assigned_role TEXT` via `ALTER TABLE memories ADD COLUMN assigned_role TEXT` (idempotent — `OperationalError` on existing column is swallowed, mirrors the precedent set by `model_id`). Index `idx_assigned_role` created. `MemoryEntry` dataclass + `to_dict`/`from_dict` carry the field. `store()`, `store_immediate()`, and `store_with_graphs()` all accept `assigned_role: Optional[str] = None`.
- [x] **TR-2.3** Reader paths surface the field — all four `SELECT … FROM memories` paths (`retrieve_by_similarity`, `get_by_id`, `get_all_memories`, `get_q_outliers`) now include `assigned_role` in their SELECT list and populate `MemoryEntry.assigned_role`. Downstream consumers (`routing_classifier.py`, `q_scorer.py`) read `MemoryEntry` via the dataclass surface, so no consumer-side changes were required to expose the field; TR-3 will populate it.
- [x] **TR-2.4** Backfill script at `scripts/memory/backfill_assigned_role.py`. Heuristic: action substring match — `review|verify|validate|compliance|critique|judge|qa` → VERIFIER; `architect|decompose|plan|design|strategy|synthes|ingest_long_context` → THINKER; default WORKER. Only writes rows where `assigned_role IS NULL`; idempotent on rerun; `--dry-run` flag prints classification counts without writing.
- [x] **TR-2.5** Tests: 21 unit tests in `tests/unit/test_episodic_store_assigned_role.py` cover taxonomy normalisation, feature-flag reading, schema migration idempotence, writer round-trip, legacy-NULL tolerance, backfill correctness + idempotence + dry-run + missing-DB error. All 21 pass; the existing 29 `test_episodic_store.py` tests still pass (no regressions).

**Validation**: feature flag `ORCHESTRATOR_ROLE_AWARE_ROUTING` is wired but defaults OFF — TR-3 classifier will populate the field in shadow mode without acting on it. The TR-5 A/B is what flips the flag.

##### TR-3: Initial Role Classifier (Heuristic First)

- [x] **TR-3.1** ✅ **DONE 2026-05-07** — `src/classifiers/role_classifier.py`. Deterministic regex-only classifier. Returns `RoleClassification(role, reason)`. Rule precedence (first-match wins): VERIFIER (review/verify trigger AND prior-content cue), THINKER (architect-class routing OR force_role architect_* OR thinking_budget>0 OR plan/decompose/design keyword), WORKER (default). Word-boundary anchored so `checkmate`/`above the line` don't false-positive. 27 unit tests in `tests/unit/test_role_classifier.py` + 7 routing-integration tests in `tests/unit/test_pipeline_routing.py::TestTrinityRoleShadow` cover precedence, return shape, distribution-non-degeneracy.
- [x] **TR-3.2** ✅ **DONE 2026-05-07** — wired into `_route_request` in `src/api/routes/chat_pipeline/routing.py`. Classifier invoked AFTER `routing_decision` is set so it can read the head model role. Field is **always** populated and logged via `task_extra(strategy="trinity_role_shadow")` regardless of the `ROLE_AWARE_ROUTING` flag — TR-4 gates *acting* on the role; TR-3.3 just collects telemetry. Defensive `try/except` around the classifier call falls back to `"worker"` on any failure (verified by integration test `test_classifier_failure_falls_back_to_worker`).
- [x] **TR-3.3** ✅ **DONE 2026-06-20** — clean-week shadow telemetry passed. Report `orchestration/reports/trinity_shadow_telemetry_2026-06-20.md` scans 10,868 routing-decision rows with 10,686 role-bearing rows (98.3%) across 7.822 days. This proves persistence and collection-window sufficiency; it does not by itself reopen TR-4/5.
- [x] **TR-3.4** ✅ **DONE 2026-06-20** — non-degenerate distribution passed on the same report: worker 9,296 (87.0%), thinker 1,116 (10.4%), verifier 274 (2.6%), below the 95% top-role degeneracy screen.

##### TR-4: Per-Call Dispatch Wiring (Execution)

- [ ] **TR-4.1** In `routing.py`, compose role with model selection: model-keyed affinity table (keyed by descriptor-v3 physical model, not role: three roles share one model) OR independent role+model softmax (per TR-1.3 decision). Scope (absorbs TR-4.2/4.3/4.4): RoleResult consumers honour the assigned role (planning / verification / execution templates); multi-turn sessions read the prior turn's role; a Verifier ACCEPT short-circuits further dispatch in the session.
  - 2026-11-09 audit: STALE-PREMISE, rewritten above. The 'per-role model-affinity table' collapses on the 4-physical-model lineup (3 roles share one model); the classifier is OFF with a label set that includes retired `architect_coding`; the box is frozen on a metric that is tautological (see regret decision). Prerequisites: RTG-RETRAIN-1 and the regret ruling. If the operator picks option (a) on the regret decision, re-evaluate whether TR-4.* should be closed as superseded.
- **[declined: ws58 2026-11-03 content-review: merged into TR-4.1]** **TR-4.2** Update `RoleResult` consumers to honour the assigned role — Thinker turns get the planning prompt template, Verifier turns get the verification prompt template, Worker turns get the standard execution template.
- **[declined: ws58 2026-11-03 content-review: merged into TR-4.1]** **TR-4.3** Multi-turn composition: if our orchestrator runs multi-turn sessions, ensure subsequent turns can read the prior turn's role and adapt. (Trinity passes the full transcript + a brief role-specific prompt each turn.)
- **[declined: ws58 2026-11-03 content-review: merged into TR-4.1]** **TR-4.4** Verifier-acceptance termination: if Verifier returns ACCEPT, short-circuit subsequent dispatch within the same session (echoing Trinity's K=5 termination semantics).

##### TR-5: A/B Evaluation — Role-Aware vs Role-Agnostic

- **[declined: ws58 2026-11-03 content-review: merged into TR-5.3 (suite definition)]** **TR-5.1** Define benchmark suite for the A/B: must include at least one task family where role distinction is *expected* to matter (Math500-style multi-step reasoning, code-write-then-test). Reuse existing eval-tower benchmarks where possible.
- **[declined: ws58 2026-11-03 content-review: merged into TR-5.3 (run protocol)]** **TR-5.2** Run paired A/B with `ROLE_AWARE_ROUTING=1` vs `=0` for ≥N=200 per arm per benchmark. Use the same routing-classifier weights so the model-selection axis is constant.
- [ ] **TR-5.3** Decision gate: if Δ ≥ +2 points on at least one benchmark with no regression > −1 point on others, promote to default-on. If flat or regression, stay OFF and document negative result in `Open Questions` for future revisit (consider whether the role taxonomy from TR-1 was wrong). Protocol (absorbs TR-5.1/5.2): suite includes at least one family where role distinction should matter (Math500-style multi-step, code-write-then-test), reusing eval-tower suites; paired A/B ROLE_AWARE_ROUTING=1 vs 0, >= 200 per arm per benchmark, same classifier weights.
  - 2026-11-09 audit: Compute: needs >=200 requests per arm on eval-tower suites (inference, not Autopilot). See EG2 note.
  - 2026-11-09 EG2 boundary (RTG-EG2-1): `ROLE_AWARE_ROUTING` A/B uses the 06-12 classifier weights (BGE-1024, 8 old role labels). The A/B arms must run on the retrained classifier (RTG-RETRAIN-1) and the EG2 cosine thresholds (REPL-EMB-R5); a result on the old weights does not transfer.

#### Dependency Graph

```
TR-1 (taxonomy + open questions) ──gate──
TR-2 (data layer)                    │
TR-3 (heuristic classifier)          │ ── needs TR-2
TR-4 (dispatch wiring)               │ ── needs TR-2, TR-3 (heuristic OK as starter)
TR-5 (A/B eval)                      │ ── needs TR-4 + benchmarks
```

TR-1 is a hard gate — do not start TR-2 without resolving the open questions, since the data-layer schema depends on the action-space decision (TR-1.3) and the Verifier-vs-review decision (TR-1.2).

#### Relationship to Existing Systems

| System | Relationship | Impact |
|---|---|---|
| `learned-routing-controller.md` | Supplies the model-selection axis; this handoff adds the role axis | Routing classifier output dim grows from `N_models` to `N_models + 3` (decoupled) |
| `decision-aware-routing.md` | DAR-2/3/4 reshape Q-value learning on the model axis | Tri-role addition is independent — DAR fixes apply per-role after this lands |
| `routing-intelligence.md` | Owns the review-trigger and escalation pipeline | TR-1.2 decides whether Verifier subsumes or parallels the existing review path |
| `../completed/meta-harness-optimization.md` | Optimises prompt templates per role | Tri-role gives PromptForge a richer search space (one template per role × task family) |
| Episodic memory | Currently stores `(prompt, model, outcome)` | Add `assigned_role` so retraining can condition on role |

#### Cross-Cutting Concerns

- **Backwards compatibility**: All existing memories pre-TR-2 lack the role field. Default to `"worker"` on read; backfill where inferable. Don't hard-fail on missing role.
- **Observability**: Add role to all telemetry surfaces (logs, metrics, eval-tower output) from TR-2 onward, before any A/B.
- **Optimizer-independence**: This handoff lands the architectural change. Whether the role classifier is rule-based (TR-3 starter), MLP-distilled (later, via `learned-routing-controller.md`), or sep-CMA-ES-trained (later, via the Trinity replication spike) is a separate decision.

#### Reporting

After each TR-X completion, update:
- This handoff (mark task done, capture lessons)
- `routing-and-optimization-index.md` (subsystem-status row + P19 section)
- Progress log for the day

If TR-5 produces a negative result, also update [`research/deep-dives/trinity-evolved-llm-coordinator-methodology.md`](../../research/deep-dives/trinity-evolved-llm-coordinator-methodology.md) Section 6 ("Open Questions") with the empirical answer to "do tri-roles have semantic meaning at our scale?".

#### Key Files (anticipated)

| Component | Path | Status |
|---|---|---|
| Role classifier (heuristic) | `epyc-orchestrator/src/classifiers/role_classifier.py` | NEW |
| Routing dataclass | `epyc-orchestrator/src/api/routes/chat_pipeline/routing.py` | EDIT (add role field) |
| RoleResult | locate via grep at TR-2 start | EDIT |
| Episodic store schema | `epyc-orchestrator/orchestration/repl_memory/episodic_store.py` | EDIT (migration) |
| Feature flag | `epyc-orchestrator/src/features.py` | EDIT (`role_aware_routing`) |
| Eval-tower benchmark | TBD at TR-5.1 | EDIT |

#### Notes

This handoff isolates the *single biggest empirical lever* in Trinity's ablation set. It can ship under any optimizer choice and does not commit us to the sep-CMA-ES rewrite. Treat the existing routing controller and Q-scorer as compatible substrates — both can grow a role axis without re-architecture.

#### Research Intake Update — 2026-07-08: EvoScientist Pattern (rec-008)

**Source**: EvoScientist (intake-108), AI Scientist Nature (intake-780)

**Corrected finding — 2026-09-25:** The Nature AI Scientist record demonstrates an integrated computational-ML paper-production pipeline, while human topic/template input, filtering, implementation checks, data preparation, and submission selection remained material. Its Automated Reviewer predicts venue accept/reject labels and is not a scientific-validity verifier (intake-780#record).

**Mapping to EPYC tri-roles**:
- EvoScientist Researcher → our Thinker role (analysis, planning, decomposition)
- EvoScientist Engineer → our Worker role (execution, implementation)
- EvoScientist Evolution Manager → aligns with Verifier + our autopilot's Evolution Manager species

**Memory module patterns**: EvoScientist's persistent memory modules could inform our StrategyStore enrichment and episodic memory design. Particularly relevant for cross-session knowledge retention in the tri-role dispatch loop.

**Disposition:** retain EvoScientist's role/memory comparison. Do not use AI Scientist acceptance framing as validation of an unattended research loop or as a reason to reopen frozen TR-4/TR-5.

- [x] **TR-ES-1** — cross-reference EvoScientist memory modules for StrategyStore enrichment ✅ 2026-07-29. EvoScientist's **Experimentation Memory** is the relevant analogue: ESE distills engineer trajectories and retrieves one strategy by embedding similarity. Map that narrowly to StrategyStore's derived strategy view, while retaining EPYC's stronger invariants: raw trajectory/event provenance remains append-only, reads are policy-gated, and write-side provenance validation rejects ungrounded non-operator strategies. Do **not** copy EvoScientist's LLM-summary-only source of truth or fixed `k=1`; its Ideation Memory belongs to the separate planner/idea layer, not StrategyStore. This is an architecture cross-reference only—no retrieval policy, store schema, or runtime behavior changes.
- [x] **TR-ES-2** — evaluate EvoScientist's knowledge distillation separation for our Evolution Manager species ✅ 2026-07-29. Adopt only the separation-of-duties shape: an observer/distiller must remain separate from proposal generation and execution. EPYC already represents that boundary with its uninstantiated `KnowledgeDistiller`/Evolution Manager path; it has zero non-test callers. Do not wire it to write derived strategies or feed retrieval yet: first run it as shadow/observer-only and prove it beats AP-29's episodic-only retain-and-delete control arm. Keep raw events append-only and derived outputs provenance- and policy-gated. EvoScientist's LLM-only summaries, fixed cadence, and reported outcomes are paper observations, not EPYC performance evidence; no runtime, cadence, retrieval, or schema change follows from this evaluation.

#### Research Intake Update — 2026-04-28

##### New Related Research

- **[intake-493] "Learning to Orchestrate Agents in Natural Language with the Conductor"** (arxiv:2512.04388, ICLR 2026, Sakana AI)
  - **Framing**: competitive intelligence — what others are publishing in the design space. Not an architecture EPYC is committing to copy.
  - Authors: Nielsen, Cetin, Schwendeman, Sun, Xu, Tang — six-author overlap with Trinity (intake-474), parallel design-space probes underpinning Sakana Fugu.
  - Distinct from Trinity: Trinity = 0.6B SLM + 10K linear head trained by sep-CMA-ES emitting `(LLM, role)` per turn. Conductor = 7B model trained via **GRPO** (2× H100, 200 iter × batch 256) emitting **`(worker_id, NL_subtask, access_list)`** per coordination step — communication topology emerges as a derived consequence of access-list selections; "role" is NOT a Conductor primitive (only Trinity has roles). Conductor adds recursive self-as-worker as a small (+1–2.2 pp) test-time scaling mechanism.
  - Reported results (concrete): LCB V6 +1.03 pp vs GPT-5 (within pass@1 noise); GPQA-D +2.7 pp vs Gemini-2.5-Pro; open-source-only inference +~10 pp vs Claude Sonnet 4 (strongest ablation). Code/weights promised in supplementary post-anonymization, NOT visible at intake date.
  - Delta from this handoff: this handoff scopes a *static heuristic* tri-role classifier (TR-1.x). Conductor and Trinity together demonstrate that learned, end-to-end-trained coordinators are a viable published design space — but neither is a target we are committing to. **One of several options for future escalation paths** if/when the tri-role classifier saturates; the current tri-role surface remains the substrate regardless of any future learning-head choice.
  - Caveats (Tier 2b): six-author overlap with Trinity means the two papers are not independent corroboration; multi-agent systems literature (MAST taxonomy, arxiv:2503.13657 — 36.9% inter-agent misalignment) documents failure modes terminal-reward RL does not directly address; +1.03 pp LCB headline is within noise.
  - Action: cross-link to `outer-coordinator-learned-head.md` (OC-0 scoping should reference Conductor + Trinity as design-space data points, NOT primary peer architectures). No tri-role scope change here — intake informational.

---

#### TR-1 Deliverable — Role Taxonomy (2026-05-07)

User-resolved decisions on the five open questions. This section is the ROLE SCHEMA referenced by the TR-1.4 directive ("write the conclusions into a Role Taxonomy section appended to this handoff"). TR-2 onward depends on this.

##### TR-1 Q1 — Role-to-model mapping

**Roles are NOT model-permanent properties.** Every model in our stack participates in multiple roles depending on context. This is a sharp confirmation of Trinity's per-call role-axis insight (deep-dive Section 2.1: "role is a per-turn property of the dispatch, not of the model").

Concrete mapping:

| Existing model / role | T (Thinker) | W (Worker) | V (Verifier) | Notes |
|---|---|---|---|---|
| `architect_general` (Qwen3.5-122B-A10B Q4) | **always** | rare | rare | Either queried by frontdoor for an opinion on hard cases, OR receives an escalated task and takes ownership: makes a plan and delegates partial/incremental/entire work to a suitable worker. Thinker turns dominate; direct Worker execution is the exception when the plan is short enough to inline. |
| `coder_escalation` (Qwen3.6-35B-A3B Q8) | sometimes | **mostly** | rare | Default Worker. Becomes Thinker when it identifies a parallelizable bundle and delegates focused sub-tasks to `worker_*` models instead of executing all in-process. |
| `frontdoor` (Qwen3.6-35B-A3B Q8, shared GGUF with `coder_escalation`) | sometimes | sometimes | sometimes | Genuinely tri-role. Direct answer = W. Plan + delegate to `worker_*` = T. Review of prior model output (e.g., long-context ingestion result) = V. Per-call role assignment is essential here — this is where the architectural lever produces the most leverage. |
| `worker_general` / `worker_fast` / `worker_math` (Qwen3-Coder-30B-A3B Q4) | rare | **default** | rare | Pure Worker. Could be promoted to Verifier on cheap-quick verification turns (e.g., "did the previous answer satisfy the format?"), but Thinker capacity is bounded by base-model quality. |
| `ingest_long_context` (Qwen3-Next-80B-A3B Q4) | sometimes | sometimes | sometimes | Long-document ingestion is W (extract). Multi-document synthesis is T (plan the synthesis structure). Cross-document fact-checking is V. |
| `worker_fast` (Qwen2.5-Coder-1.5B Q4) | NEVER | **default** | NEVER | Phase 3 compliance verdict (2026-05-07): baseline recall 0.33-0.47 — model lacks the working-memory capacity to hold an agent file faithfully. By extension, it cannot reliably plan or verify. Restrict to W role only, simple deterministic dispatches. Per `agent_file_compression_operating_point: none` (BLOCKED) in the registries. |
| Existing review/escalation pipeline | n/a | n/a | partial mapping | Today's review/escalation is *operational*, not *structural*: a worker fails or low-confidence-flags, a different role is invoked. This is a Verifier turn under another name when the next role is review-class. The proposal: instead of treating review as a black-box pipeline construct, surface it as an explicit `verifier` role assignment so the routing policy can REASON about it (and the classifier can learn it). |

The existing review pipeline is **partially** equivalent to a Verifier turn. TR-1.2 decision (below) makes this explicit.

##### TR-1 Q2 — Pool-scale meaningfulness

**Tri-role distinctions DO carry semantic weight at our scale, but the interpretation is inverted from Trinity.**

Trinity's pool spans GPT-5 to Gemma-3-27B — capability variance dominates, so Verifier ≈ "ask the most capable available". Our open-source-only inner pool has narrower capability variance; the binding constraint is **cost-per-token-of-correctness**, not raw capability. Roles in our system collapse to:

> "Ask the **cheapest** model that can be trusted to correctly perform a given **role** for this task."

This is the routing policy our orchestrator already implements implicitly (frontdoor first; escalate to coder_escalation if frontdoor fails; fall back to architect_general only if escalation insufficient). The tri-role addition makes this implicit cost-aware policy explicit and learnable: the routing classifier outputs `(model, role)` rather than `(model)`, where `role` constrains the prompt template + the verification expectation.

**Concrete implication**: routing should NEVER blanket-default to architect_general because it's the most capable. Architect_general is reserved for tasks where the Thinker role is binding AND the cheaper Thinker (frontdoor) has insufficient quality on the task class. The role axis surfaces this cost-quality tradeoff for the routing policy to reason about — that's the value, not "use the smartest model".

##### TR-1 Q3 — Surface area: per-call

**DECISION**: per-call (per orchestrator dispatch). NOT per-session, NOT both.

Trade-offs the user asked about:

- **Per-call** (per dispatch): every orchestrator call carries an independently-assigned role. A multi-turn session with 3 dispatches gets 3 independent role decisions. Most flexible, matches Trinity's per-turn evidence, matches the Q1 mapping (`frontdoor` switches between T/W/V across calls within the same session).
- **Per-session**: role fixed at session start, all dispatches inherit. Simpler, lower overhead, BUT incompatible with "frontdoor as Thinker on turn 1, frontdoor as Verifier on turn 5". Falsified by Q1 answer.
- **Both** (hybrid): session-level default + per-call override. Over-engineered; per-call already subsumes both.

Per-call is the only choice consistent with the Q1 mapping. TR-2.1 (RoleResult.role field) and TR-3.2 (classifier wired into routing.py) make this concrete: each call to `routing.py:_route_request` carries a role decision in its payload, defaulting to `worker` for backward compat.

##### TR-1 Q4 — Termination semantics: deferred to autopilot exploration

User declined to over-specify upfront. **DECISION**: TR-4.4 implements Verifier-acceptance termination as a parallel mechanism to the existing review/escalation pipeline (NOT subsuming it). Operate them side-by-side initially. The autopilot evolutionary memory will discover whether V acceptance correlates with passing the existing review gate (in which case they collapse to one mechanism in a future iteration) OR whether they're orthogonal (the right outcome is "early-exit if V says ACCEPT AND existing review gate doesn't escalate").

Concretely:

- **TR-4.4** (Verifier-acceptance termination): if a Verifier turn returns ACCEPT, short-circuit subsequent dispatches within the same session — but ONLY if the existing review/escalation pipeline did not flag the prior Worker turn for escalation. The two signals AND together for early termination.
- **Telemetry from TR-3.3 onward** (shadow-mode role assignment): log both signals on every dispatch so autopilot has observational data to learn the correlation. After 1-2 weeks of data, decide whether to collapse the two mechanisms.

##### TR-1 Q5 — Action-space encoding: decoupled

**DECISION**: decoupled `(L + 3)` flat logits — independent softmaxes over `L` LLMs and 3 roles. Matches Trinity's choice AND extends the existing `RoutingClassifier` infra minimally.

Rationale:

1. **Existing infra**: `epyc-orchestrator/orchestration/repl_memory/routing_classifier.py:50` defines `RoutingClassifier` as `Input(1031) → Dense(128) → Dense(64) → Dense(n_actions=6) → Softmax`. The 6-output softmax is over models. Decoupled extension: add a parallel `Dense(64) → Dense(3) → Softmax` role head sharing the Dense(64) trunk. Two independent softmaxes; combine at dispatch time. New parameter cost: (64 × 3) + 3 = 195 params. Negligible vs the 200K-param baseline.
2. **Joint `L × 3` encoding**: would change `n_actions` from 6 to 18. Every existing routing memory needs a `(model, role)` tuple label, NOT just `(model)`. Migration is heavier; backfill (TR-2.4) is harder because role inference for legacy memories is ambiguous. Ranking accuracy on 8K labels with 18 classes is sample-size-bounded.
3. **Trinity's evidence**: their decoupled design is what they ablated. Joint not tested. Default to the published-evidence version.
4. **Independent updates**: decoupled allows the role head to be retrained without retraining the model head, and vice versa. For instance, a new model can be added (model head expands by 1 logit) without touching the role head's weights. This is operationally important for the registry-driven model-pool.

##### TR-1.2 decision — Verifier vs existing review pipeline

**DECISION**: parallel mechanism initially (per Q4 answer above), with TR-4.4 wiring V-acceptance to AND with the existing review gate for early termination. After 1-2 weeks of observational telemetry from TR-3.3, decide whether to collapse.

This DOES require updates to `routing-intelligence.md` (which owns the review trigger) — to flag that the review trigger now coexists with Verifier-acceptance, not replaces it. Cross-referenced below.

##### TR-1.5 decision — feature flag

**DECISION**: yes, add `ROLE_AWARE_ROUTING` feature flag, default OFF. Required for the TR-5 A/B (`=1` vs `=0` paired comparison). Adding the flag now (TR-2 phase) avoids a retrofit. Toggle via env var `ORCHESTRATOR_ROLE_AWARE_ROUTING=1`.

##### TR-1 sub-task closure

- [x] **TR-1.1** Role mapping table — written above (Q1 section).
- [x] **TR-1.2** Verifier vs review pipeline — parallel mechanism with eventual-collapse exploration via autopilot. See TR-1.2 decision section above.
- [x] **TR-1.3** Action-space encoding — decoupled `(L + 3)` flat logits, matches Trinity AND minimizes existing-infra change. See Q5 section above.
- [x] **TR-1.4** Open questions resolved — this whole section. ✅ DONE 2026-05-07.
- [x] **TR-1.5** Feature flag — yes, `ROLE_AWARE_ROUTING` default OFF.

**TR-1 GATE PASSED.** TR-2 (data layer) is unblocked.

##### What TR-2 onward looks like under this taxonomy

- **TR-2.1**: Add `role: Literal["thinker", "worker", "verifier"]` to `RoleResult`, default `"worker"`.
- **TR-2.2**: Add `assigned_role` column to `episodic.db` `memories` table; new column NULLable for legacy rows. `parallel_embedder.py` writer + `episodic_store.py` reader.
- **TR-2.3**: Surface in `routing_classifier.py` (extend output to include role logits) + `q_scorer.py` (per-role Q-values? — to decide; default is "no, role is independent of Q") + retraining scripts.
- **TR-2.4**: Backfill via heuristic on existing 8K memories: review-flagged memories → V; first-pass non-escalated frontdoor calls → W; architect-class invocations → T. Acceptable to leave NULL where ambiguous.
- **TR-3** (heuristic classifier): rule-based mapping from request context (retry count, escalation flag, prompt features) to {T, W, V}. Lives at `src/classifiers/role_classifier.py`. Validates the schema before any ML.
- **TR-4**: dispatch wiring — per-call role drives prompt template + verification expectation. Verifier turns get a verification prompt; Thinker turns get a planning prompt.
- **TR-5**: paired A/B `=1` vs `=0` for ≥N=200 per arm per benchmark. Promote on Δ ≥ +2 points without regression > −1 point.

#### Research Intake Update — 2026-07-16 (Architect→Reviewer control plane answers TR-1)

The new control-plane series ([`reviewer-control-plane-index.md`](reviewer-control-plane-index.md)) formally answers Open Question TR-1: **a review decision turn IS a Verifier turn under another name** — H3 task RD-7 ([`reviewer-decision-plane.md`](../completed/reviewer-decision-plane.md)) logs `assigned_role="verifier"` on all review dispatches (telemetry-only; NO dispatch changes; TR-4/5 and DAR gates remain FROZEN and are not needed by the series). The calibration ledger (H4) will produce exactly the V-acceptance-vs-review-gate correlation telemetry TR-1.2 deferred to; collapse authority remains an operator decision. Supporting intake: intake-835 (plan-compliance — plan rubric = phase-coverage/order/executor-alignment), intake-839 (MetaGPT tri-role precedent: reviewer-no-authorship validated externally).

**2026-07-17 update**: RD-7 is now LIVE in code (orchestrator `5586ce1e`) — review-plane trace events carry `assigned_role="verifier"` in the detail payload per the `routing_meta()` convention, so `scripts/analysis/trinity_shadow_telemetry.py` will pick up review turns as Verifier turns once shadow decisions flow. The TR-1.2 correlation telemetry (V-acceptance vs review gate) becomes computable from the review_ledger after the first shadow replays (inference-gated).

## Track: typed-decision-plane
<!-- gate: none -->

> Folded from `handoffs/active/typed-decision-plane.md` @ `b33c4e7a5fd1` on 2026-11-02 (BRF-T1-F26, route 1a, operator D1/D5; retired row RTG-56 → RTG-09). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Typed Decision Plane — one-pass typed decisions over the local stack

**Scratch**: `/mnt/raid0/llm/tmp/typed-decision-plane/` · worktrees: `/mnt/raid0/llm/worktrees/typed-decision-plane-*`

**Status**: in progress — **Owner: the research-intake lane** (operator-assigned 2026-09-17 to `intake-jev-sageattn`; that session is closed, and the lane owns this handoff from 2026-09-23). *Ownership note (operator-directed tidy 2026-09-26):* ownership is unchanged, but TD-21 and every TD-21.N row, plus the TD-1d.1/TD-1d.2/TD-1d.5 closures, were executed 2026-09-24 by a separate operator-dispatched main session with no roster lane (`workspace-8d`; `progress/2026-09/2026-09-24-td21.md`, `progress/2026-09/2026-09-24-main-ak-seat.md:123`), not by the research-intake lane. Implementation landed in `epyc-orchestrator` main from branch `intake/jev-typed-decisions-20260917` (merged; its worktree was retired 2026-09-23 — cut a fresh lane worktree from origin/main for new TD work).
**Created**: 2026-09-17 (via research intake, operator-approved 2026-09-17)
**Categories**: routing_intelligence, cost_aware_routing, inference_serving, tool_implementation, agent_architecture
**Parent index**: [routing-and-optimization-index.md](routing-and-optimization-index.md)
**Evidence**: intake-1472, intake-1473, intake-1474, intake-1485, intake-1486, intake-1487, intake-1490 (all dive-verified); intake-1476#record (application survey, anecdote-grade)

#### Start here (2026-10-01)

- **Next, zero inference:** TD-29, the shadow mode (the typed pick is written beside the executed arguments in
  `decision_receipt.v1`; JSON mode in production until v11).
- **Next, zero inference:** TD-29.M0a (prefill tokens on the `/completion` lane), then TD-29.M4 (prefix-cache reuse).
- **Next, GATE: champion-sidecar (CPU window):** TD-1d.0 (n≥4), TD-12, TD-16/17 (ruling 6 order). TD-29.K2 is done
  (2026-10-01: native 18/18 at 1.45x free-form wall, 5.3x faster than JSON).
- **GATE: mi210-window (JSON-mode only):** TD-29.M3, TD-13, TD-19, TD-23. CJ-13 and CJ-16 ride the same window.
- **Frozen:** TD-28, until v11 ships and autopilot has trained on the swapped stack and UFH-13 has re-opened. TD-11 is
  the single owner of typed routing.
- Closed work: § *Completed Scope*.

#### Operator rulings — 2026-09-29

Canonical record of the operator's chat answer (2026-09-29) to Q1-Q5 of the 2026-09-28 Jev-techniques map
(`/mnt/raid0/llm/tmp/jev-techniques-map-20260928.md` §6). Each ruling is also written into the boxes it touches; a box
that contradicts this section is stale and must be corrected, not reconciled.

1. **Q1 — Local models only: no proprietary or hosted Jev.** We adopt Jev *techniques*, never the hosted product. This
   restates the operator's 2026-09-26 "no proprietary Jev" ruling, which no handoff recorded until now. TD-23 loses its
   hosted arm (one local compact decision backend vs the constrained incumbent readout); CJ-16
   (`canonical-judge-suite-revamp.md`) becomes a local judge-cascade shadow; URE-2a (`decision-aware-routing.md`) runs on
   that local cascade. No box may plan a call to the hosted service.
2. **Q2 — New unfreeze trigger: "autopilot has trained on the swapped stack AND UFH-13 re-opened".** UFH-13 is PARKED (2026-09-28), so the old "UFH-13 verdict" triggers could not
   fire. Applies to TD-28 (which ALSO needs the v11 promotion), VB-TD-ADVICE, LRC-1/LRC-2 and every DAR-LAT box
   (VB-SEL-LOADAB unfreezes with DAR-LAT-3).
3. **Q3 — Typed-decision measurement runs use the CURRENT MI210 as a fast test environment; do not hold them for the
   second MI210.** Gate token: **`GATE: mi210-window`** = a slot on the current MI210 scheduled with workspace-76 (DS41's
   planner and authors use `:8083`) under a session-bus grant or a coordinated window. It replaces the device-less "one
   short window" gates: TD-1d.0, TD-12 (live comparison), TD-13, TD-16, TD-17, TD-19, TD-23, TD-29.M0/M3, CJ-13, CJ-16
   (TD-29.M1 was on this list; DECLINED by ruling 6). **Amended by ruling 6:** the native-mode parts of TD-29/TD-29.M0,
   TD-1d.0, TD-12, TD-16 and TD-17 moved to `GATE: champion-sidecar (CPU window)`; their JSON-mode-only runs keep
   `mi210-window`.
4. **Q4 — Closed-set tool-argument selection (TD-4, flag `typed_decisions_tool_args`) runs SHADOW-ONLY until v11.** It
   records what it would pick, never replaces the model's arguments, and builds a labelled corpus in
   `decision_receipt.v1`. Enable task and latency mitigations: TD-29.
5. **Q5 — Typed routing has one owner: TD-11.** RI-14 (`routing-intelligence.md`) and LRC-TD-1
   (`learned-routing-controller.md`) are folded into it. Revisit TD-11's "written decision to drop typed routing" clause
   after the autopilot run on the swapped stack.
6. **Test bed — champion side instance (operator, 2026-09-29).** Features that need fixes only on the champion (v11) are tested on a CHAMPION SIDE INSTANCE (CPU build, spare port, in AutoKernel CPU windows agreed with workspace-76), not gated on production promotion. GPU champion side instances follow when a HIP champion build exists and the 2nd MI210 (or an approved displacement window) provides VRAM.
   Gate token: **`GATE: champion-sidecar (CPU window)`** = the champion CPU build `kernels/builds/cpu-20260925-90c12df42`
   (branch `ak/champion/llama-cpp-ffc1bac82eec`, contains the SW-9 fix `2b57340bf`, so native one-token scoring gets
   token probabilities on the MTP spec path) launched as a side instance with frontdoor's model and recipe args on spare
   port 8199 via `/mnt/raid0/llm/tmp/champion-sidecar/launch_champion_sidecar.sh`, inside an AutoKernel CPU window
   (`/mnt/raid0/llm/autokernel/cpu-window.json` open, `loop_holds_claim=false`, >=30 min left) or with workspace-76's
   agreement; bench driver `/mnt/raid0/llm/tmp/champion-sidecar/run_td_bench.sh`. It replaces `mi210-window` for NATIVE-mode
   tests; JSON-mode-only tests keep `GATE: mi210-window`. Precedent: 2026-09-24 champion CPU build on :8199 with frontdoor
   args through `LLMPrimitives` `/v1` (receipt `/workspace/tmp/td1d5-20260924/bench-candidate-8199.json`). Test order:
   TD-29 (native vs JSON vs free-form with TD-29.M0 instrumentation) → TD-1d.0 (n>=4 rounds) → TD-12 → TD-16/17.
   TD-29.M1 (per-request spec-off probe on v10) is DECLINED: native mode is measured on the champion directly.
   Window discipline (added 2026-09-29, INC-20260929-peer-window-closing-overrun): stop the bench and the sidecar at
   once on any window `state` other than `open`, or when `loop_holds_claim=true`; `closing` means stop. The sidecar
   lives exactly as long as its bench run. `window_loop.sh` and `run_td_bench.sh` enforce both.

Duplicate-owner consolidation the same day (the map's §3.2): closed-set tool arguments → TD-4/TD-12 (TU-TD-1 in
`tool-use-eval-contract.md` folded); cheap-judge redundancy → CJ-13 (ECR-TD-1 in `eval-benchmark-cost-reduction.md`
folded); JSON repair → TD-21 (struck from PAW-5's candidate list in `paw-compiled-specialists.md`).

#### Objective

Give the orchestrator a first-class one-pass decision call: declared typed questions (choice / score / noul)
in, per-question values + probabilities + a caller-computed confidence statistic out, with no autoregressive
JSON generation, and with locally measured behaviour before any gate uses it. Operator steering 2026-09-17:
"extremely relevant for the orchestrator where json schemas are passed and tool use is important ... guarantees
exact tool use and also a pretty large overall speed boost ... may also be relevant for fast routing and
episodic memory writing."

#### Research Context

| Intake ID | What it settles | Use |
|-----------|-----------------|-----|
| intake-1472 | Public typed-decision spec (primitives, one-call parallel questions, confidence is an undisclosed statistic) | Contract for the local implementation |
| intake-1473 | MIT reference implementation over generic LLM APIs (per-request schema, corrective retries, normalization, local confidence stats, injection guard) | Pattern set to transplant onto llama.cpp |
| intake-1474 | Independent evidence that candidate-softmax confidence is NOT calibrated (65% of wrong 7B fields >0.90) and the real local speedup is 3.4–7.9x, not 40–200x | Hard constraint: no gate before local calibration |
| intake-1485 | Paired Jev-vs-fast-LLM run: measured p50 176 ms vs 215 ms; fixture agreement scene-dependent | External datapoint; baseline is fast, so no multiplier transfer |
| intake-1486 | Independent rerank reproduction: Jev tied with Cohere Pro (nDCG 0.692 vs 0.691, CI crosses 0); Jev Choice order-sensitive 24.7% | Guarantees are not quality; order effects must be measured |
| intake-1487 | Fully local pinned one-pass implementation: 5.21x vs same-model JSON on a 3090; 20.03 decisions/s parallel reuse; reuse drifts 5–6/777 argmaxes | Local mechanism + acceptance envelope |
| intake-1490 | Independent audit of jevlike: shipped shuffled-context control was defective; informed-vs-blind lift ~25 pts after correcting | Verification discipline for our own measurements |
| intake-1493 | Open browser agent (MIT) that asks one typed call for an operation plus one speculative target head per operation, consuming only the matching head; its measured gain is ~half fewer model requests, ~half browser I/O | Pattern for TD-12..TD-15 (tool choice + arguments in one call) |
| intake-1498 | Kev: trained LoRA + pointer head over option hidden states; OOD numbers recount from committed rows; llama.cpp feasible with merge-first + `seq_cp` | TD-18, TD-19, TD-20 |
| intake-1504 | CC0 300-state x 3-question OOD set (tier visible; priority policy-unknown, not unknowable); corrected Jev T 1.30 / 1.92 | TD-17 |
| intake-1517 | Noul label-word bias (laya#156 reproduced); neutral-key choice changes three things at once | TD-16 |
| intake-1502 | Laya: fitted calibration holds in-task only (ECE 0.030 vs 0.204 held-out); shipped a sharpening T 0.1006 | Counterexample for TD-17, TD-18 |

#### Completed Scope

| Scope | Where |
|---|---|
| TD-1 … TD-3b, TD-5/6/7/9/10 (2026-09-17/18) | [completed ledger](../completed/typed-decision-plane-completed-through-2026-09-29.md) |
| TD-21 and every TD-21.N except TD-21.1a (2026-09-24) | same file |

#### Tasks

- TD-1, TD-1a, TD-2, TD-3, TD-1b, TD-1c and TD-3b are done (2026-09-17): the call path, native scoring,
  contamination/calibration, fan-out, tokenizer-aware candidates, parity and fan-out agreement. § *Completed Scope*.
- [x] **TD-1d — Recover native speed at parity.** The cue replay costs a forward pass per forced cue token (2.08x vs JSON; 18.9x pre-fix). Options to test: (a) minimal grounding cues (id + a few tokens) judged on the same 24-question set; (b) parallel per-question native reads against one cached prefix (use the server's multiple slots) — the faithful 'parallel sampler' shape; (c) routing cheap vs hard questions between native and JSON arms. ✅ 2026-09-17 ACCEPTED via the id-only cue. Cue sweep on the worker (same 35B, same 24-question set, one run each): JSON 19.3 s / 1,354 tok; native:full 7.3 s (2.66x) / 523 tok; native:short 3.2 s (6.0x) / 239 tok; **native:id_only 1.6 s (11.98x) / 112 tok** — all three native styles at 15/16 agreement and 15/16 accuracy on the overlap (JSON 14/16 on the same 16). The prompt catalogue carries the grounding; the id-only cue re-anchors position. Parallel per-question reads were tested and rejected on this stack (exclusive heavy_model lock serializes workers; client concurrency 0.65x vs batched; the true parallel-sampler needs a multi-slot readout readout the generation API lacks — record for any future runtime choice). Remaining: adopt id_only as the native default after review and decide whether a `native_cue_sweep` study gets a belief-kernel carrier.
  - ⚠️ **2026-09-18 RE-MEASUREMENT DISAGREES WITH THE ACCEPTANCE — the bar is not cleared at n>1.** The row above
    accepted TD-1d on **one run per arm**. A 4-round re-measurement on the same model and catalogue, with every
    arm run before the next round and arm order rotated, puts the best arm **below** the 10x bar. The tick is
    left standing because the box belongs to the accepting session; **this note is the evidence against it.**

    | arm | this run (n=4, mean ± sd) | speedup | 2026-09-17 (n=1) |
    |---|---|---|---|
    | json baseline | 14.02 ± 1.82 s (11.34–15.45) | 1.00x | 19.3 s |
    | native_full | 6.52 ± 0.05 s | 2.15x | 7.3 s (2.66x) |
    | native_short | 3.03 ± 0.12 s | 4.63x | 3.2 s (6.0x) |
    | **native_id_only** | **1.46 ± 0.03 s** | **9.60x** | 1.6 s (**11.98x**) |
    | native_pq1 (1 slot) | 2.09 ± 0.04 s | 6.69x | — |
    | native_pq3 (3 slots) | 5.24 ± 0.93 s | 2.67x | — |
    | native_pq3_id_only | 2.27 ± 0.45 s | 6.17x | — |

    **The disagreement is the JSON BASELINE, not the native arm** — the two id_only measurements agree (1.46 s
    vs 1.6 s). The 2026-09-17 JSON sample (19.3 s) is **above the maximum of four samples measured here**
    (15.45 s), and pairing each side's baseline with the other's native time spans **8.8x–13.2x**. A single
    baseline sample cannot see that spread, which is exactly why the bar needs a repeated baseline.
    Agreement is NOT in dispute: 60/64 pooled = 0.9375 = 15/16, every round, same `n01` disagreement as TD-1c.
    **Denominator caveat that applies to BOTH numbers:** native decides 16/24 (c01–c08 fail closed,
    `native_unsupported_candidates`), so the ratio compares a 16-decision run to a 24-decision one. Per decision
    it is 584 ms vs 91 ms = **6.40x**. The bar never stated its denominator; neither figure passes it.
    Independent corroboration of the 09-17 note: parallel reads ARE a loser here — measured 2.67x, slower than
    serial. Artifacts: `artifacts/typed_decisions/run_20260918/`; server launched and killed by the measuring
    session, VRAM 59% in all 24 in-run samples.
    - [ ] **TD-1d.0 — OWNER/OPERATOR: re-settle the acceptance.** Either re-run the 09-17 arms with a repeated
          - 2026-11-09 audit: SV (owner). The 09-17 arms ran on a worker model that has since changed (Qwen3.6-35B-A3B now); the re-run needs repeated baselines, n>=4. Inference window.
      baseline (n>=4, alternated) and keep the acceptance if it survives, or downgrade "ACCEPTED" to
      "best-effort 6.4–9.6x, bar not cleared". Do not adopt id_only as the native default on the n=1 number
      alone. Inference-gated — **GATE: champion-sidecar (CPU window)** (operator ruling 6, 2026-09-29); the whole sweep above took ~20 min including model load.
  - [x] **TD-1d.1 — `/v1` drops `grammar`/`json_schema`, so the native path cannot run through `LLMPrimitives`.**
    `frontdoor` routes to `/v1/chat/completions` (`use_chat_completions=True`), which forwards neither field:
    measured 515 free-form tokens and **0/24 decisions** (`native_unknown_candidate` x16). Every arm above used a
    direct `/completion` adapter mirroring `_build_payload`, and TD-1c's result must have gone the same way.
    **No typed-decision arm is deployable through the normal primitives path until this is closed** — decide
    whether `/v1` forwards the fields for internal callers, or whether typed decisions keep a declared direct
    `/completion` lane. Zero inference to decide.
    ✅ 2026-09-24 — closed by **TD-21.0** (folded here, per the TD-21 dispatch): `/v1` now forwards both
    (orch `b284ede3`), so no declared `/completion` lane is needed. Verified live on frontdoor :8070 through
    `LlamaServerBackend` (same prompt: prose without a schema, schema-valid JSON with one) and end to end through
    the reloaded API (`/chat` + `output_schema` + `force_role=frontdoor` → `{"answer": true, "city": "Paris"}`).
  - [x] **TD-1d.2 — re-run the TD-1d native arm through `LLMPrimitives` on frontdoor.** The 0/24 above was the
    dropped grammar; the schema path is now live, but the native candidate-probability readout over `/v1`
    (`logprobs`/`top_logprobs` instead of `/completion`'s `n_probs`) has not been re-measured. One short window
    with `src/typed_decisions/bench.py`; schedule it outside a CPU-decode campaign window.
    - *2026-09-24 live windows:* 12:07Z run through `LLMPrimitives` on frontdoor: JSON 0/24 (`no_json`), native
      full 1/16, `id_only` 0/16. Two fixes landed from the review: orch `4610be60` — the streaming
      repetition-loop guard ran unconditionally and aborted legitimately repetitive schema-constrained output,
      now exempt when `json_schema`/`grammar` is set; and orch `71be6ed3` — native `n_probs` was captured
      pre-grammar-mask by default, now the request sets `post_sampling_probs`. (The "noul" key one agent
      suspected as a bug turned out to be the schema's own key for yes/no questions — grammar converter
      verified faithful; that hypothesis was wrong.) Re-bench 13:38-13:41Z: JSON 0/24 now ends on `length`
      (1600-token budget too small for the schema+reasoning), native still unchanged (the flag appears not to
      reach the server). Diagnosis in flight.
    - [x] Raise the JSON arm's token budget above 1600 (measured ending on `length`, not a real parse failure)
      and re-bench. ✅ 2026-09-24 — schema-aware budget landed (`8977f540`); late-afternoon re-bench: **JSON arm
      24/24 decisions, 23/24 vs labels.**
    - [x] Trace why the native `post_sampling_probs` request flag (orch `71be6ed3`) is not reaching the
      server — native result unchanged across the fix. ✅ 2026-09-24 — root cause is not the flag: the frozen
      production kernel's MTP speculative-accept path never populates token probabilities at all (`// TODO: set
      result.probs` in `server-context.cpp`) — ~94% of frontdoor tokens come from accepted MTP drafts, so
      `post_sampling_probs` has nothing to read on those tokens regardless of the request flag. **Operator
      decision (2026-09-24 ~15:45Z): NATIVE mode is out of reach on the current production kernel; patch the
      spec-accept path in kernel research and advance the AutoKernel champion so future campaigns pick it up**,
      rather than disabling MTP for frontdoor or reworking the flag further. Filed as its own task: TD-1d.5.
    - ✅ 2026-09-24 **closed overall**: JSON arm cleared the bar (24/24, 23/24 vs labels, `8977f540`); the native
      arm's remaining gap is not a bench defect but a kernel limitation with an explicit operator disposition
      (patch-in-kernel-research, tracked as TD-1d.5). Nothing left dispatchable under TD-1d.2 itself.
  - [x] **TD-1d.5 — spec-accept path never fills token probabilities on the frozen production kernel (`llama.cpp`
    `server-context.cpp`, MTP speculative-accept path, `// TODO: set result.probs`).** Blocks the native
    typed-decision arm's candidate-probability readout (TD-1d.2) because ~94% of frontdoor tokens are accepted
    MTP drafts with no probs attached, regardless of the `post_sampling_probs` request flag (orch `71be6ed3`).
    Operator decision 2026-09-24 ~15:45Z: patch it via kernel research on an experimental branch (never patch
    the frozen `production-consolidated-v10` tree in place — full experimental → validate → new-production
    cycle per CLAUDE.md), then advance the AutoKernel champion so campaigns pick up the fix. A subagent is
    preparing the patch on an experimental branch as of this wrap-up; build/validation needs an operator-granted
    CPU window (**in flight**). Owner: `handoffs/active/speculative-decoding.md` **SW-9** (filed
    there as the kernel-side task; this row tracks the typed-decision consumer side and is closed by SW-9
    landing + a native re-bench).
    ✅ 2026-09-24 — fixed in the champion (`2b57340bf`, SW-9): native mode works on the champion build (16/16
    decisions, ~11× faster than JSON). Production (v10) still lacks it — native stays out of reach in production
    until a v11 promotion carries the champion.
    *Comparability caveat (operator-directed tidy 2026-09-26):* the ~11× (native `id_only` 7.1 s vs JSON 80.4 s
    = 11.4×) is ONE run per arm on the **CPU frontdoor** — the candidate champion CPU build (10306) on spare
    port 8199 with frontdoor args, through `LLMPrimitives` `/v1` (receipt
    `/workspace/tmp/td1d5-20260924/bench-candidate-8199.json`, role `frontdoor`, 2026-09-24T17:51Z). It is NOT
    comparable with the GPU figures above (11.98× n=1 and 9.60× n=4, MI210 worker, direct `/completion`): different
    device, server build (MTP draft-accept path), transport and JSON baseline (JSON 2,368 generated tokens here vs ~1,356 on the GPU).
    "16/16" = the 16 natively eligible of 24 questions (c01–c08 fail closed, the same 6.40×-style denominator
    confound). Agreement with JSON: `id_only` 15/16, `full` 14/16 (14/16 across all three arms). It shows the
    SW-9 fix unblocks the native readout; it is not evidence for the TD-1d 10× bar or for TD-1d.0.
  - [ ] **TD-1d.2b — concurrent in-process `llm_call`s are serialized by the cross-process `inference_lock`** (probed: parallel wall == serial wall, max 1 slot busy) — a constraint on every fan-out design. Task: decide whether the lock should be per-server and slot-aware instead of global; measure on :8083 (np 4) parallel vs serial wall for 4 concurrent calls with the lock scoped per server; done when the lock scope is chosen with that number and the heavy_model lock note is reconciled.
      - 2026-11-09 audit: SV. `src/inference_lock.py` exists. The measurement shape named :8083 np4, but :8083 is now the 27B (architect_critic, DFlash2, STACKCHG-DFLASH2-20261003): re-confirm the shape from `stack_topology.yaml` before booking. Needs an inference window.
    *(Filed 2026-09-18 as "TD-1d.2"; renamed TD-1d.2b 2026-09-26 because the 2026-09-24 native re-bench row above
    reused that id. Code comments and the 2026-09-24 progress logs that say "TD-1d.2" mean the re-bench row.)*
  - [ ] **TD-1d.3 — Build and compare checkpoint-safe isolated question branches over one shared state prefix.**
      - 2026-11-09 audit: SV, PROPOSED not approved. The design-only first step (checkpoint-safe branch design note, no inference) is doable now; the comparison needs an inference window.
    **PROPOSED outcome refinement, 2026-10-04 retrospective; not implementation or activation approval.**
    Restrict the comparison to independent same-state questions. Reuse TD-31's prefix-stable layout,
    TD-29.M0a's actual cache/prefill counts and KPF-11–16's checkpoint-safe sequence sharing; do not
    build a second cache system or depend on TD-19 selecting Kev. A question branch must contain
    only that question/options after the common instructions/state, not the sibling catalogue or
    another answer. Keep dependent decisions staged by the host.
    Compare cold sequential singletons, current serial native scoring and the isolated-prefix path
    on one pinned experimental champion sidecar. Freeze model/binary/tokenizer, prompts/catalogues,
    readout/candidate bindings and cache policy; retain probabilities, raw replies, failures,
    abstentions, actual prefill/cache counts and whole-call wall time for every case. Use held-out
    catalogues/state families and interleaved paired repeats. Require singleton equivalence within
    a separately measured same-backend numerical floor, sibling-mutation invariance, no correctness
    regression under the existing typed screen's predeclared gate, and a cost-improvement interval
    clearing zero before any follow-on. Unsupported hybrid/checkpoint paths remain unavailable,
    not successful zero-cost rows. The existing champion-sidecar/resource gates apply; production
    activation is separate and remains gated. Write-side capture is registered under
    VB-RI-OPS-WIRE before a new decision-bearing run. [Review](../../docs/reviews/research-intake-earlier-applications-20261004.md).
    **Historical mechanism context:** `qwen35moe` is hybrid-recurrent (SSM layers); cross-request
    prefix reuse in the inspected run was checkpoint-quantized, not a model-class impossibility.
    Back-to-back per-question reads on one slot reuse **0** tokens (~450 ms each) unless a prefix-only request
    first leaves a checkpoint at the prefix end (then `cache_n` 1105, ~128 ms/read); under 3-way concurrency they
    stretch to 585–900 ms. This is the mechanism behind fan-out losing, and it belongs in any prefix-cache
    reasoning about this model class.
    - *Note 2026-09-23 (intake-1498, intake-1514#00):* an exact per-question prefix fork on hybrid qwen35/qwen35moe exists
      inside ONE request: decode the state once into seq 0, then `llama_memory_seq_cp` 0->i per question
      (`llama-memory-hybrid.cpp:152-155` copies KV + recurrent state), as espetro/llama.cpp@kev `common/decision.cpp:538`
      does. The 0-token reuse above comes from cross-request slot caching, not from the model class; the stock
      server's pooling-none embeddings path has no prefix reuse (`server-context.cpp:426-431`).
  - [ ] **TD-1d.4 — to clear the bar honestly, handle the 8 multi-token choice questions natively** (which also
      - 2026-11-09 audit: SV. Related to v11 native scoring (the TD-28 trigger). Inference.
    removes the denominator confound), or take option (c): per-question cost/confidence labels plus a JSON
    fallback for those 8. Not built; (c) is a routing policy, not a speed fix.
    Harness extension `run_typed_decisions_native_parallel` (`src/typed_decisions/native.py`, +251 lines, ruff
    clean, 209 native unit tests pass) is **uncommitted** pending TD-1d.0.
    - [x] ✅ 2026-09-24 — orch `11818eb5`: the parked 2026-09-22 harness landed **UNWIRED** (taken over from the
      other session at operator direction; the parked diff's silent `CueStyle` default reversion to `full` was
      deliberately NOT carried over). Still gated on TD-1d.0 — landing the code is not adopting it.
    - *Options added 2026-09-23 (intake-1498, intake-1514#00):* (d) a trained option-end pointer readout (Kev) — viable only
      as a separate small decision model, not a zero-shot fix; TD-9's single-token codes already removed the TD-7 blocker.
      (e) score multi-token candidates as `seq_cp` branches (summed teacher-forced log-prob), on llama.cpp-experimental.
- [x] **TD-4 — Closed-set tool-argument selection pilot.** Map tool arguments to closed sets (Literal → Choice,
  list[Literal] → multi-choice, bool → Noul) with per-argument confidence; compare against the current
  free-form tool-call path on exact-match argument correctness and wall time. Citation: intake-1472 pattern,
  intake-1473 adapter. ✅ 2026-09-17 live pilot on the worker (18 deterministic cases, 3 tool schemas): **closed-set 18/18 exact-match (0 failures) vs free-form 6/18 (12 failures)**, per-arg exact 66 vs 24, at 116.6 s vs 11.4 s (10.2x wall). Exact tool use is the closed-set arm's to win; the free-form arm's failures are parse/schema failures, not merely wrong values. `tool-use-eval-contract.md` TU-TD-1 was folded into TD-4/TD-12 on 2026-09-29: that contract reads this harness as its eval arm.
  - *Cost decomposition (receipt re-read 2026-09-29, `artifacts/typed_decisions/run_20260917/tool-args-pilot-worker.json`).*
    The 10.2x is not a like-for-like decode comparison. The closed-set arm (JSON mode) generated 5,112 tokens vs 270
    free-form (18.9x). The free-form arm stopped after ~1 token on its 12 parse failures (0.40-1.05 s per case), so its
    wall is flattered by failing fast; its 6 successes used 37-45 tokens. The closed-set arm made 1 call in 9 cases and
    2 (one corrective retry, `failure_count=1`) in the other 9: 27 calls vs 18, inferred, because the receipt has no call
    count. One-call closed-set cases still took 5.1-6.6 s for 136-447 tokens, which points at per-call fixed cost
    (prefill of the typed catalogue) more than decode. An exact split is not recoverable: per-case `tokens` is the LAST
    call's only (`tool_args_pilot.py:540-544`) and no prompt-token field survives (`_arm_case_view`, :643-656). TD-29.M0
    re-measures it. The receipt records `role: "frontdoor"` despite its `worker` filename.
- [ ] **TD-29 — Shadow-only closed-set tool arguments until v11 (operator ruling Q4, 2026-09-29).** Today
  - 2026-11-09 audit: SV. Anchor `src/features.py:335` fixed inline. Umbrella of M0a-M4.
  `typed_decisions_tool_args` (`src/features.py:335` (was :258), default off) has REPLACE semantics only: `context.py:630-631` swaps
  the model's kwargs for the typed dict when validation is `accepted`, and neither `tool_args_integration.py` nor
  `prepared_action.py` has a shadow path (`shadow.py` covers routing only). Add a shadow mode (a separate flag or a mode
  value; decide in review) that runs the typed selection, executes the model's own arguments, and writes the typed pick
  beside the executed arguments and the tool outcome in `decision_receipt.v1` (`prepared_action.py:20`; sink
  `artifacts_dir/typed_decisions/decision_receipts.jsonl`, `context.py:684-688`), so the receipts form a labelled corpus.
  - Run the shadow off the tool call's critical path (non-blocking, bounded, fail-open, as `shadow.py` does), or its
    latency lands on the user.
    Execute the original arguments unchanged. Drop/refuse shadow work on saturation or failure without altering
    the tool result. Capture action identity and explicitly bind bounded request/deadline/cancellation/workload/
    placement context through the existing context seam; executor submission alone does not carry ContextVars.
    Attribute shadow inference counters and cost separately from foreground accounting. Append proposed arguments,
    executed arguments and outcome through the existing decision receipt.
  - Pin the shadow's decode mode explicitly. The integration defaults to native (`context.py:806-812` passes no mode),
    and native needs token probabilities that v10's MTP accept path does not return (SW-9, fixed only in v11). Use JSON
    mode in production until v11; native mode is measured on the champion sidecar (operator ruling 6, 2026-09-29).
  - The native vs JSON vs free-form comparison (with TD-29.M0 instrumentation) runs all arms on the same sidecar server —
    **GATE: champion-sidecar (CPU window)** (operator ruling 6, 2026-09-29).
  - [x] **Skip the typed-args call site when the flag is off** (the bullet below). ✅ 2026-09-28 — orchestrator
    `e60ee78a`: `_dispatch_tool` calls `_typed_tool_arguments` only when a prepared action exists; the flag-off test
    proves neither it nor `maybe_typed_arguments` runs and no receipt is written, and fails against the old code.
  - The flag-off call-site fix above is completed; preserve its no-selector-call/no-receipt behavior.
  - Acceptance: mocked blocking/failing/saturated selectors never alter executed kwargs or make dispatch await them.
    Delayed results bind to the original action/outcome. Concurrent foreground/shadow and post-cancellation fixtures
    prove no metadata crossover, misjoined outcomes, expired execution or contamination of foreground cumulative cost
    counters. Existing permissions, freshness/fallback and retry tests remain green. After deterministic acceptance,
    the stack launcher enables shadow for one role in its coordinated window and yields receipts with typed pick,
    executed arguments and outcome. No replacement mode before v11.
  - [x] **TD-29.M0 — Split the TD-4 cost into decode, extra calls and prefill.** ✅ 2026-10-01 Make the pilot sum tokens across retries,
    keep `prompt_n`/`cache_n` and an explicit call count per case, then re-run the 18 cases. Code is zero-inference; the
    re-run is **GATE: champion-sidecar (CPU window)** (operator ruling 6, 2026-09-29), all arms on the sidecar as part of the TD-29 comparison (TD-29.M1 declined). Acceptance: per-arm decode tokens, prefill tokens, call count and
    wall, from the receipt.
    - Progress 2026-09-29: the code half landed as orchestrator `c4e99dbe` (`call_recorder.py` snapshots tokens,
      `prompt_tokens`, `cache_n`, `prompt_n`, `prompt_ms` and `gen_ms` after every call; the pilot sums per case and
      keeps `tokens_last_call`; new `--closed-mode`, `--cue-style`, `--arm`, `--case-log`, `--server-url`). The box
      ticks with the re-run, which rides TD-29.K2's sidecar window.
    - ✅ 2026-10-01: the re-run is TD-29.K2's run `td-20260930-p32`. It delivers per-arm decode tokens, call count
      (18 per arm, no retries) and wall. The prefill split is only partial. `prompt_n` and `cache_n` are `None` in all
      three arms. `prompt_ms` arrives only on the native arm (batch transport, 24.96 s total vs 19.31 s gen). The
      JSON and free-form arms stream and report `prompt_ms` 0.0. Cause: `inference.py:1359-1367` sets
      `prompt_tokens`/`cached_prompt_tokens` only when a `chat_payload` is present, and frontdoor is on the raw
      `/completion` lane (the limit is documented in `call_recorder.py:24-27`). Filed as TD-29.M0a.
  - [ ] **TD-29.M0a — Report prefill tokens on the `/completion` lane.** (filed 2026-10-01) Populate `prompt_tokens` and
      - 2026-11-09 audit: PARTLY PRESENT: `src/llm_primitives/inference.py:1146-1154` already reads `prompt_n`/`cache_n` from server timings (and `call_recorder.py:16-25`, `serving_params.py:127-129`). Verify whether the `/completion` lane specifically sets them before building. Zero inference.
    `cached_prompt_tokens` from llama-server's `timings.prompt_n`/`timings.cache_n` on the raw `/completion` path
    (batch and stream transports), and `prompt_ms` on the stream transport. Carry server-reported `prompt_n`,
    `cache_n` and streaming `prompt_ms` through raw completion results and primitives metadata into the existing
    recorder. Preserve absent values as unknown; do not estimate or substitute `tokens_cached`. Code and unit tests
    are zero-inference. Batch/stream fixtures with known timings must produce exact counts; missing timings remain
    unknown. A fresh sidecar receipt with server-reported timings must show non-null `prompt_n_total`/`cache_n_total`
    on all three arms. TD-29.M4 needs this first. TD-31 already owns general prefill optimisation and depends on this
    plumbing; coordinate the shared seam with workspace-ec without duplicating its prompt/slot work.
  - [x] **TD-29.M0a.S0 — Prove raw `/completion` prefill source controls in isolated off-host CI.** Bind the reviewed APP source commit and run the complete three affected unit modules: `tests/unit/test_llama_server.py`, `tests/unit/test_inference_mixin.py`, and `tests/unit/test_typed_decisions_call_recorder.py` (119 AST test definitions at proposal time; the original JUnit is authoritative for collected/executed cases). Preserve existing controls by exact node ID: `tests/unit/test_llama_server.py::TestEarlyStopTiming::test_early_stop_produces_timing`, `tests/unit/test_typed_decisions_call_recorder.py::TestRecordLlmCalls::test_every_call_is_logged_and_summed`, and `tests/unit/test_typed_decisions_call_recorder.py::TestRecordLlmCalls::test_absent_telemetry_is_none_not_zero`. Include exact test-body identities, in-module fixtures, `tests/conftest.py`, `tests/unit/conftest.py`, `pyproject.toml`, `uv.lock` and all locked package/wheel hashes in the existing native CI readset. Use only the existing `native_conformance.py` / `ci_conformance.py` carrier and shared `claim_tuple.grade()`. Capture once only after this child, VB companion and source-table row are prospectively filed and the ROOT handoff context is pinned. This proves bounded source/fixture conformance only; TD-29.M0a stays open for its fresh three-arm sidecar receipt and TD-29.M4 dependency. ✅ 2026-10-08 — [Accepted original209 source/control custody](../../artifacts/ni08/td29-current-source209-acceptance-20261008/README.md); APP main eadb. This paired source child is complete; parent sidecar/inference gates remain open.
  - [x] ~~**TD-29.M1 — Native scoring probe on v10 with speculation disabled per request.**~~ **DECLINED (operator,
    2026-09-29):** the operator prefers testing native mode on the champion directly (ruling 6) over a per-request spec-off
    probe on v10. ✅ 2026-09-29 — resolved to a decline; the text below is kept for the record. Native one-token scoring needs
    token logprobs, which production v10's MTP/speculative accept path does not return; SW-9's fix is only in v11. Probe
    whether turning speculation off PER REQUEST returns logprobs on v10, so native mode works before v11. Source reading
    says llama-server parses a per-request `speculative.n_max`, where 0 disables speculation for that request
    (`tools/server/server-schema.cpp:205-207`, applied at `server-context.cpp:489`, tree `ffc1bac82`; `n_min`/`p_min`/
    `type` sit under `#if 0`, not wired per request); the orchestrator sends no speculative params today
    (`src/backends/llama_server.py`). That is not evidence the logprobs come back; the probe is. ~~GATE: mi210-window~~ (declined).
    Acceptance: logprobs present, the native path succeeds on the TD-4 case set, latency measured, with the decode cost
    of losing MTP on that request recorded.
  - [ ] **TD-29.M2 — Validate-first fallback.** Validate original kwargs against a lossless supported schema projection
      - 2026-11-09 audit: SV, doable now: code and unit tests (`src/typed_decisions/tool_args.py` exists). Standalone.
    and registry-compatible argument validation before asking for repair; explicitly refuse unsupported constraints
    rather than dropping them. The current converter drops constraints and `additionalProperties: false`, so its
    output alone is not a full validity check. Valid calls incur zero repair calls; unknown-key, dropped-constraint
    and genuinely valid fixtures must exercise the actual dispatch contract. For an invalid eligible closed-set
    call, compute at most one repair proposal and an explicit accept/abstain result, initially in shadow. Acceptance
    requires complete selected-action validity, host revalidation and an outcome-labelled policy for that exact
    role/catalogue/readout. Otherwise retain the ordinary structured-failure/REPL repair path. Reuse TD-18 outputs;
    never multiply marginal head confidences into complete-action correctness. Keep JSON verbalized and native token
    probability policies separate. Lack of adequate labels prevents enforcement, not shadow implementation.
    First measure the real-traffic free-form failure rate by role from TD-29 receipts with a CI; TD-4's adversarial
    12/18 is not a traffic rate. Charge typed latency only to the failing share and include the incumbent's subsequent
    REPL repair turns in the comparison.
    - Decision note 2026-10-01 (TD-29.K2), re-scoping M2 and M3: free-form is 18/18 on frontdoor (Qwen3.6-35B-A3B)
      against 6/18 on the gemma worker in TD-4. So on frontdoor the typed path buys robustness only, not accuracy on
      this case set. Validate-first is therefore more attractive on frontdoor, not less. If free-form already passes,
      the typed call (1.45x free-form wall native, 7.76x JSON) is pure overhead, and validate-first charges it only to
      the failing share. M2 stays, unchanged in scope. Its first input is the free-form failure rate in the TD-29
      shadow receipts, measured per role, because the rate is model-dependent. M3 also stays: it matters only while
      JSON mode is the production decode (until v11), and that is exactly the shadow path.
  - [ ] **TD-29.M3 — Trim the JSON-mode output.** In shadow mode emit no confidence fields, and put closed-set arguments
      - 2026-11-09 audit: SV, doable now: schema change plus unit tests, zero inference. Standalone.
    only on exactness-critical tools (name them from `ToolRegistry`). Schema change and unit tests are zero-inference;
    the before/after tokens-per-pass count on the TD-4 case set is **GATE: mi210-window** (operator ruling Q3, 2026-09-29).
    - 2026-10-31 source partial: APP `92f67a84b24bad6519d5f14ba34b1f978708861c` adds strict value-only JSON to tool-argument shadow selection, keeps unavailable confidence null, and preserves existing retry abstention and foreground arguments. Final focused controls passed 86/86; [committed source-bound proof](https://github.com/pestopoppa/epyc-orchestrator/tree/33693ca71d8a6c0a06a5aef121ac6df62475eccb/artifacts/typed_decisions/td29-m3-source-controls-20261031). Exactness-critical ToolRegistry selection and the declared MI210 tokens-per-pass comparison remain unfulfilled, so M3 stays OPEN with no completion credit. No model/GPU execution or live reload. [no-belief: source conformance controls only]
  - [ ] **TD-29.M4 — Confirm prompt-prefix cache reuse between the tool call and the typed call.** Check that the typed
      - 2026-11-09 audit: SV. Needs a live server (inference window).
    pass shares the tool call's prompt prefix, so llama-server reuses the cached prefix instead of re-prefilling it.
    Acceptance: `prompt_n`/`cache_n` recorded for paired calls (with TD-29.M0); if reuse is absent, name the prefix break.
    - **2026-10-31 prepared source checkpoint (M4 remains open):** APP main `5c1dfea76467cc82edc57192667677dcb1308af3` publishes Q4 shadow-only tool-argument observation plus the paired-cache harness; original kwargs remain foreground, strict replacement gate is unchanged, feature flag stays OFF, and production runtime was not reloaded. Exact original TD-4 schema preflight passed 18/18; focused integration passed 134 and `make gates` passed. The four broader inference-mixin failures matched the untouched `fb9ada63` base. Final same-launcher R11 first pair recorded actual `prompt_n/cache_n` 274/0 (tool) and 330/0 (typed); actual chat JSON was rendered and tokenized through the same sidecar, with equal reported/tokenized lengths. Rendered prompts share 17 bytes / 3 tokens, then diverge immediately after `<|im_start|>user\n` (`Fill in` vs `Answer`). This is one pair only; no latency or cohort cache verdict is claimed. The full18 packet is now finalized as READY id `codex-ni-td29-m4-cache-r3-20261031` (SHA-256 `4764a50fefce0dcfe0948f509eb124c1dc57fdcd3fc63abd8b6a79af56406bb3`), pinning a 717-file / 13 MiB source/config/bench snapshot from `5c1dfea7`, archive SHA `1886bb1fca062e22f8e521883f79f8937fe6649d4a25f2aca465b75373a43252`, and closure-manifest SHA `36b924eefa143d7deee76769a96d7aab88f635eabe888fd482de387ac7ed3bf0`. The job verifies the packet before load and records `results/source-runtime.json`; the final validator/grant fixture had zero warnings and its fixture poller was terminated and verified dead. The full18 diagnostic has not run, so TD-29.M4 remains open. Earlier R1/R2 READY packets were withdrawn before any grant. Evidence: `/mnt/raid0/llm/tmp/codex-ni-td29-m4-cache-20261030/SOURCE-REVIEW.md`, `results/smoke.jsonl`, `cutoff-fixture/RESULT-snapshot-r3.json`, and `GRANT-OK-FIXTURE-r3.log`.
    - **2026-10-31 full18 owner source audit and future harness repair (M4 remains open):** Preserve C3 original full-run filing main `e5c641188`: R4 normal admission passed and collected all18 exposures/36calls, but only12 pairs were valid; all6 `file_ticket` pairs failed, so the predeclared18-valid criterion remains **INCOMPLETE**, with no overall zero-cache conclusion. The raw six free-form model objects included every required field but emitted optional `assignee:null` against a string schema. An independent harness bug discarded those parsed invalid objects when the strict pilot validator returned `(None,error)`, then dispatched `{}`, causing synthetic missing-required errors. The actual Q4 foreground preserved the kwargs it received; its selector proposed required fields, so those errors are not evidence of a selector omission. APP main `367df713ee4e272164026a9c1498e7a82d31fda4` now fixes only the future standalone benchmark: preserve the original parsed object through actual dispatch/shadow while retaining schemaerror/invalid pair; unparseable/nonobject replies do not fabricate empty kwargs; an original empty object is still dispatched as originally emitted. General pilot parser, schemas, Q4 foreground, default-off flag and historical717-file `5c1dfea7` source/raw are unchanged. Actual run→ContextMixin→Registry model-free controls plus pilot/integration regressions74passed; `make gates`, Ruff and diff checks passed, normal-hook source commit/push verified and APP lane/claims/leases released. No redraw, new READY or model rerun. Resource correction: earlier67.58s native first-pair smoke peaked39,439,646,720B and exceeded explicit OWNER-RULINGS R11 standing8GiB cap; record it as actual ungranted over-cap evidence, never R11-compliant qualification. Future over8GiB CPU model work requires a matching grant. Evidence: `/mnt/raid0/llm/tmp/codex-ni-td29-m4-cache-20261030/r4/full18-audit/` (`AUDIT.json`, `FINDINGS.proposed.md`, `regression.log`, `gates.log`, `push.log`); original pairs SHA-256 `6ae32b44bdf2b7866eaffa33da46e56b7aa387967812f72749e559da478d04f3`. [belief: cc]
  - **2026-09-29 champion-sidecar native result (n=1, CPU sidecar).** `--closed-mode native --cue-style id_only`, 18
    TD-4 cases, build `cpu-20260925-90c12df42` on :8199, 40 threads, cores 48-87. **12/18 exact; all 12 resolved cases
    correct.** The 6 failures are all `cannot assemble tool arguments: required argument 'severity' was not answered`:
    the `p1`..`p4` enum is multi-token, so native excluded the question (`native_unsupported_candidates`). 534 generated
    tokens in total (17-38 per case) vs 5,112 in the 2026-09-17 GPU JSON arm; 18 calls, one per case; wall 42.3 s
    (2.35 s per case); prompt 20.3 s vs gen 16.9 s, so prefill dominates and M4 prefix-cache reuse is the next lever.
    The same-machine JSON and free-form arms were NOT run (the window closed early), so no within-run native-vs-JSON
    ratio exists yet. Receipt: `/mnt/raid0/llm/tmp/champion-sidecar/runs/td-20260929/td29/closed_native_id_only.pre-K1.json`
    (cases in `closed_native_id_only.pre-K1.cases.jsonl` beside it; renamed with the `.pre-K1` suffix so the K2 re-run
    writes fresh receipts under the original names).
  - [x] **TD-29.K1 — Single-token keys for multi-token closed sets (native mode).** A closed set whose labels are not all
    single tokens is re-keyed with the TD-9 code alphabet (A-Z, 0-9), each key verified single-token and collision-free
    through `/tokenize`; the model picks a key and the layer maps it back to the original value (`Decision.native_key`
    plus value; the pilot receipt records both). Sets that already bind are untouched (byte-identical); more than 36
    labels falls back as before, with the reason recorded. JSON mode is unchanged. ✅ 2026-09-29 — orchestrator
    `c595e13d` (`src/typed_decisions/native.py` `_bind_single_token_keys`, serial and parallel native runners).
  - [x] **TD-29.K2 — Re-run the native arm after K1.** ✅ 2026-10-01 Repeat `--closed-mode native --cue-style id_only` on the champion
    sidecar with the fixed harness (`orch-tdbench-8d`), together with the same-machine JSON and free-form arms that the
    2026-09-29 window missed. **GATE: champion-sidecar (CPU window).** Acceptance: 18/18 resolved or each failure named;
    `native_keys` present on the file_ticket cases; within-run native vs JSON token and wall ratios.
    - Progress 2026-09-29: a window-gated loop is running the remaining arms
      (`/mnt/raid0/llm/tmp/champion-sidecar/window_loop.sh td29 td-20260929`, started 23:48Z, log
      `window_loop-td29.log`). It waits for an open window, launches the sidecar, runs the bench, and confirms the
      sidecar is dead afterwards. It needs 10 min left in the window (`NEED_MIN=10`), not 30, because DS41's two-lane
      windows have all been shorter than 30 min. The bench still aborts on any state other than `open`. No arm had run
      by 23:50Z. The 03:3xZ JSON attempt was aborted at the window close; its partial cases are kept as
      `closed_json.aborted-0336Z.cases.jsonl` and are not a result.
    - Note 2026-09-30, one profile per run: workspace-76 will pause DS41 for 4-8 h (a 27B harness on :8083). They
      agreed the arms may run during that ANNOUNCED pause on an explicit override. The condition is that the
      sidecar stays off cores 72-79, where the 27B's host threads decode.
      - Pause profile: cpuset `48-71,80-87`, 32 threads, NUMA interleave 2,3. The standing profile is `48-87` with
        40 threads.
      - The arms must share one profile to be comparable, so under the pause profile all three run fresh in
        run `td-20260930-p32`.
      - The pre-K1 native receipt is superseded. The post-K1 native receipt in `td-20260929` (2026-09-30 01:48Z)
        is 48-87/40, so it is not mixed in. No JSON or free-form arm has completed in either run.
      - If the pause profile is not used, `td-20260929` continues at 48-87/40.
      - `run_td_bench.sh` now refuses a second profile in one run dir (`profile.json`).
      - Machinery: `champion-sidecar/window_gate.py --allow-announced-pause` (the pause file
        `sequencer-8d/DS41_PAUSE_ANNOUNCED.json`, plus an exited, claim-free, dead DS41 loop) and the lane
        `sequencer-8d/run_cpu_lane_pause.sh`.
    - [x] **TD-29.K2a — record workspace-76's agreement to the 10-minute threshold.** Ruling 6's gate names ≥30 min
      left, or workspace-76's agreement. The running loop uses 10 min, so record that agreement here (bus message
      id or chat date), or restart the loop at `NEED_MIN=30`.
      ✅ 2026-09-29 — workspace-76 agreed on the session bus: the loop may start in any cpu-window with ≥10 min
      left, each arm gated to fit the time remaining, and it stops on any window state other than `open`. Their
      words: "Keep going by cpu-window.json and its est_close_at; the flock is the truth." The loop stays at
      `NEED_MIN=10`.
    - ✅ 2026-10-01 result, run `/mnt/raid0/llm/tmp/champion-sidecar/runs/td-20260930-p32/` (03:08-03:15Z, announced
      DS41 pause). One profile for all three arms: cpuset `48-71,80-87`, 32 threads, champion `cpu-20260925-90c12df42`,
      frontdoor Qwen3.6-35B-A3B Q8 with MTP, 18 TD-4 cases. Summary:
      `python3 /mnt/raid0/llm/tmp/champion-sidecar/summarize_td_bench.py <run dir>`.

      | arm | exact | per-arg | decode tokens | calls | wall | vs free-form |
      |---|---|---|---|---|---|---|
      | native `id_only` (K1 keys) | 18/18 | 66/66 | 564 | 18 | 49.6 s | 1.45x |
      | JSON | 18/18 | 66/66 | 9,870 | 18 | 265.3 s | 7.76x |
      | free-form | 18/18 | 66/66 | 805 | 18 | 34.2 s | 1.0x |

      - K1 lifted native from 12/18 to 18/18. `native_keys` is present on all six `file_ticket` cases (`severity`
        p1..p4 → A..D).
      - Native is 5.3x faster than JSON, with 17.5x fewer decode tokens.
      - Free-form is 18/18 on frontdoor, against TD-4's 6/18 on the gemma worker. Closed-set accuracy gains are
        model-dependent; on frontdoor the gain is robustness only. M2/M3 are re-scoped in the decision note under M2.
      - Native costs 1.45x free-form wall. Prefill dominates (native `prompt_ms` 24.96 s vs `gen_ms` 19.31 s), so M4
        prefix-cache reuse is the next lever. It needs TD-29.M0a first.
      - n=1 per arm on one profile; this is not a production-profile (48-87/40) number.
- TD-5, TD-9, TD-6, TD-7 and TD-10 are done (2026-09-17/18): the shadow integration, the routing code map, the
  `id_only` native default (it stands pending TD-1d.0), the live replay, and the counterfactual OPE (typed routing is
  ~1pp worse, so enforcement is OFF; TD-11 owns the follow-up). § *Completed Scope*.
- [ ] **TD-11 — Routing prompt/policy improvement, re-tested through the counterfactual harness.** The harness now measures value, not agreement; use it to iterate (framing, support-aware candidates, leave-one-out conditioning) before any enforcement proposal. Acceptance: positive delta with a CI excluding zero on the frozen snapshot, or a written decision to drop typed routing.
  - 2026-11-09 audit: SV. `src/typed_decisions/routing_counterfactual.py` and `routing_replay.py` exist (d827fd05, 2026-11-07). The frozen snapshot predates the lineup change: state which snapshot (recommend a post-07-23 one) before running. Inference.
  - *Single typed-routing owner (operator ruling Q5, 2026-09-29).* RI-14 (`routing-intelligence.md`) and LRC-TD-1
    (`learned-routing-controller.md`) are folded here; their "once TD-2 lands" gates were met 2026-09-17, and TD-10 then
    measured a loss. Scope carried over: (a) from RI-14, report agreement + calibration + wall time against the CURRENT
    routing classifier, never gate on uncalibrated confidence, and use the intake-1501 question shape (tier choice with
    criteria + an ordinal effort score) with a 20-card OOD probe whose labels come from a distribution the arm was not
    tuned on; (b) from LRC-TD-1, compare against the learned controller's BGE+MLP classifier on the recorded routing
    corpus, and treat the option-as-query head (intake-1462) as a second candidate-scoring arm beside native token
    logits (intake-1487).
  - *Revisit note (operator ruling Q5):* re-decide the "written decision to drop typed routing" clause after the autopilot
    has trained on the swapped stack. TD-7 showed multi-token role labels need v11-native scoring before a fair retest.
- [ ] ❄ FROZEN 2026-09-27 — resume only once v11 is promoted (native scoring) AND autopilot has trained on the swapped stack AND UFH-13 re-opened — **TD-28 — typed routing as ADVICE, not enforcement (operator direction 2026-09-26).** TD-10 showed typed routing ~1pp worse as an enforcer (delta -0.0104). A/B a typed routing hint in the frontdoor prompt vs no hint: measure how often frontdoor overrides the hint and whether overrides help (accuracy on overridden vs followed items). Wire the A/B's write side into the belief kernel (`vidya-belief-substrate-program.md` VB-TD-ADVICE).
  - 2026-11-09 audit: NAR, triple trigger (v11 native scoring AND Autopilot trained on the swapped stack AND UFH-13 re-opened); cannot fire under the Autopilot hold. HOLD list.
  ❄ FROZEN 2026-09-27 (operator, narrowed plan): typed advisors add a routing input before the base comparison exists, and 0/200 native scoring (TD-7) makes the advice JSON-fallback only; unfreeze trigger (operator ruling Q2, 2026-09-29; it replaces "the UFH-13 thesis experiment has a recorded verdict", which cannot fire while UFH-13 is PARKED): the v11 promotion ships native scoring (multi-token action labels scored natively) AND autopilot has trained on the swapped stack AND UFH-13 re-opened. The box stays open: frozen is not done.

- [ ] **TD-12 — One-call tool + argument arm (operation × conditional target).** Build a typed-decision arm that asks,
  - 2026-11-09 audit: SV. The build is doable now; adoption is gated on TD-13.
  in one call, a choice over the role's tools (`ToolRegistry.list_tools(role)`) plus one argument head set per candidate
  tool whose instructions name the tool they assume. Namespace conditional argument heads by tool and consume only
  the resolved operation's complete, schema-valid branch. Keep global JSON/envelope validation strict. Only explicitly
  permitted, structurally valid failure records in unused branches may be ignored; malformed unused-head objects,
  malformed envelopes and selected-branch failures still reject. Adapt the conditional schema rather than bypassing
  the general runner's validation. Do not repair/rerun unused branches. An unresolved selected branch falls back to
  the incumbent. The current helper accepts one already-selected tool schema and rejects any failed question; this
  is a new whole-catalogue joint capability, not a demonstrated current unused-tool failure incident.
  Connect proposals to the TD-29 shadow seam; operation differences never change the original executed tool.
  Preserve host-owned prepared-action authority, eligible menu, freshness and read-set revalidation. TD-13 must test
  joint/sibling dependence; joint probabilities are not presumed independent.
  Compare exact-match tool+argument correctness and wall time against current same-server REPL generation of both
  operation and arguments on genuinely multi-tool-choice fixtures. Extend TD-4's prescribed-tool cases rather than
  treating them as an operation-selection baseline; selected-tool typed arguments may be an attribution arm.
  Citation: intake-1493 (dive-verified; `jev_ultrafast/model.py:94-133` @ 1231850a).
  Code and unit tests are zero-inference; the live comparison is **GATE: champion-sidecar (CPU window)** (operator
  ruling 6, 2026-09-29), both arms on the same sidecar. A JSON-mode-only run keeps `mi210-window`.
  The tool-use eval contract reads this harness as its closed-set arm (TU-TD-1 folded here 2026-09-29). Conditional (absorbs TD-15): only if this needs tables beyond the TD-9 code map (36 symbols) or the 128 n_probs cap, add hierarchical codes or chunked candidate tables; otherwise record not-needed.
- [ ] **TD-13 — Contamination between the operation head and its conditional heads.** Before TD-12's heads are trusted as independent: for each case, answer the chosen tool's argument heads alone and batched with the sibling (unused) tools' heads; report top-answer flip rate per model. Existing receipts (TD-2, TD-3b) cover flat catalogues only. Acceptance: flip rate reported for the worker model; TD-12 adoption gated on it. The run is **GATE: mi210-window** (operator ruling Q3, 2026-09-29).
  - 2026-11-09 audit: SV. GATE mi210-window (operator ruling Q3), not Autopilot. Still relevant; compute list.
  - *Acceptance amendment 2026-09-25 (intake-1577#record, intake-1583#record):* randomize and interleave two dependency controls: move one sentinel fact between shared state and an unused sibling head, and prepend/append one semantically irrelevant candidate inside the chosen head. Report chosen-answer flips and pairwise log-odds among unchanged candidates. Treat any effect as a behavioral dependency; do not infer an attention mask, prefix-cache layout, or readout architecture.
- [ ] **TD-14 — Per-candidate descriptions on Question: live no-harm acceptance.** Optional aligned descriptions now exist in both catalogues and native/JSON readers through completed TD-14-NI-PREP. Retain the TD-16 described-versus-undescribed no-harm comparison before live caller adoption; deterministic source conformance does not establish model quality.
  - 2026-11-09 audit: SV. Source conformance is done (TD-14-NI-PREP); the remainder is the TD-16-comparison inference.
  - [x] **TD-14-NI-PREP — implement and validate optional candidate descriptions without inference.** ✅ 2026-10-06 — [Contract](../../docs/reference/typed-candidate-description-preparation.md), original37468262427 TRUE14/14 after MAIN3367Git+2contexts/all3377member review; APPa6883d04/ROOT4a46ac2f. Empty-default compatibility, strict descriptions, original-label/key and ordered layout/reader controls accepted. PriorFALSE13/14 preserved; parentTD14/TD16 live no-harm remains open.
  - *Acceptance amendment 2026-09-23 (intake-1517):* descriptions must not hurt — compare with vs without descriptions on
    the TD-16 pairs and report the delta; a negative delta blocks using descriptions.
- **[declined: ws58 2026-11-03 content-review: merged into TD-12 as its conditional]** **TD-15 — (conditional on TD-12) Native path for more than 36 candidates.** Only if TD-12 needs tables beyond the TD-9 code map (36 symbols, `routing_replay.py:153`) or the 128 `n_probs` cap (`native.py:259`): hierarchical codes or chunked candidate tables. Close as not-needed if TD-12 stays under 36.
  - [x] **TD-15a — lift the chat-completions log-probability cap to128.** Orchestrator main `74a313d6c172438a309b9e4f62115bd020169917` preserves explicit request semantics and raises only the chat cap.178 related tests plus nine boundary controls pass. A real public-backend→frozen native CPU smoke returned64/128 alternatives for64/128 requested (3.90s, sampled1.258GB); linkage, model identity and captured-tree drain checked. This establishes protocol capacity, not task accuracy or TD-15 necessity; parent remains open. ✅ 2026-10-30 [no-belief: source capacity repair and native protocol smoke]
- [ ] **TD-16 — Label-word bias control on the native noul path.** Freeze hunch's 240 look-alike pairs (`hunch/lookalikes.py` @8bac3f2b, MIT; 80 pos / 160 neg) as a noul set. On the worker model at its current pin run (N) native noul as today, (C) the same question as a 2-option choice with neutral A/B keys and the yes/no conditions as option text, both orders, reported per order and averaged, (J) the JSON arm, plus question-only variants of N and C. Report AUROC, argmax accuracy, Brier, ECE, order disagreement and both constant baselines (always-no 66.7%, base-rate Brier 0.222) with paired-bootstrap CIs. If C beats N beyond the CI, TD-1c's 15/16 parity holds only for its 8-noul set. No gate follows (wiki/routing-intelligence.md L40). Evidence: intake-1517, intake-1502. Inference-gated — **GATE: champion-sidecar (CPU window)** (operator ruling 6, 2026-09-29); all arms, including (J), run on the sidecar so the comparison is like-for-like (a JSON-arm-only run keeps `mi210-window`).
  - 2026-11-09 audit: SV. Inference. 'The worker model at its current pin' is Qwen3.6-35B-A3B-MTP Q8_0 now; state that pin in the run manifest.
  - *Acceptance amendment 2026-09-25 (intake-1618#record, intake-1634#record, intake-1635#record, intake-1636#record, intake-1637#record, intake-1654#record, intake-1655#record, intake-1656#record, intake-1657#record, intake-1677#record):* cross position, criteria/candidate order, opaque-key alphabet, key-to-description reassignment, semantic name/rubric rebinding, and answer-format conversion as distinct arms. Report mapped-back accuracy, probability divergence, flip rate, conjunction-based consistent accuracy, per-cardinality strata, and a repeat-only floor. A neutral key or one canonical sorted order is not evidence of invariance.
- [ ] **TD-17 — Frozen OOD calibration slice.** [too-big: source landed; per-model inference-gated calibration readouts belong to handoff owner] Zero-inference adapter over `scienthoon/jev-ood-calibration` `data/val.jsonl` @914d87a (sha256 763949cd…, CC0, byte-reproducible): 300 states x {queue choice, priority score 0-3 with level names as criteria, angry noul}; do not state the priority rule in the catalogue. Also a tier-ablated variant (drop `customer_tier`, fresh `--seed`) so priority depends on a genuinely hidden input. Report the TD-18 metric set per (model pin, catalogue) for the native and JSON arms. The calibrated target is mean max-prob ≈ accuracy, not a near-uniform priority. Cite only the corrected Jev temperatures (1.30 / 1.92), never 3.29 / 3.40 / 2.74. Evidence: intake-1504, intake-1516. The adapter is zero-inference; the run is **GATE: champion-sidecar (CPU window)** (operator ruling 6, 2026-09-29), native and JSON arms on the same sidecar (a JSON-arm-only run keeps `mi210-window`).
  - 2026-11-09 audit: SV. `src/typed_decisions/jev_ood_calibration.py` exists (adapter landed); the box says source landed and readouts belong to the owner. Verify the adapter reproduces the sha256 before building anything new.
  - *Acceptance amendment 2026-09-25 (intake-1619#record, intake-1622#record):* add matched with-unknown and without-unknown fixtures. Report forced-choice error, abstain precision/recall, candidate eligibility, probability mass, and invalid responses; never infer abstention quality from confidence separation alone.
  - **2026-11-01 source-only partial:** APP source adapter, five frozen/fresh/tier-ablated/paired fixtures, and dedicated workflow published in `5cb3f2c9a7d510f498acbd77eaaed587a59d5399` (candidate `027427c223d53a0b5a95541e5e2e49cd2cf0dc5d`); hosted CI 41287440906 passed 70/70, exit 0. Evidence and pinned source/data hashes: [artifact](../../artifacts/ni08/td17-source-partial-20261101/README.md). No model calls or TD-18 metrics were produced. Parent remains open pending per-model-pin native/JSON metric readouts under the champion-sidecar gate; no quota credit.
- [ ] **TD-18 — Calibration receipt upgrade (zero inference).** Extend the typed_decisions calibration receipt (today n, ECE, Brier, 10 bins; no floor, no model-pin field) with, per question kind: a resampled perfectly-calibrated ECE noise floor; a record/template-clustered paired bootstrap; tie-aware coverage at a stated error budget and AURC; NLL and refit-T sensitivity to the log floor and clamp; exact-0 / exact-1 endpoint rates; a flag when a fitted temperature lands on a search bound; a single in-distribution temperature with a group-disjoint out-of-fold check; and the model pin. Clean-room from the patterns in `kev/metrics.py` and `kev/calibrate.py` (Apache-2.0). Evidence: intake-1498, intake-1504, intake-1516.
  - 2026-11-09 audit: SV, doable now: zero inference; extend `confidence.py` and the measure receipt. Wire a `[belief:]` capture.
  - *Receipt amendment 2026-09-25 (intake-1584#record, intake-1585#record, intake-1619#record, intake-1636#record, intake-1658#record, intake-1659#record, intake-1660#record, intake-1681#record):* record requested alias, resolved response model/build, model/head/base revisions, question and policy version, state and candidate fingerprints, adapter hash, effective config, region, concurrency, rate headers, price snapshot, typed failure cause, per-row prediction, fallback attribution, downstream outcome, raw timing samples, and deterministic report digest. The receipt must reconstruct one prior deterministic branch and detect deliberate drift mutations.
- [ ] **TD-19 — External OOD read via a `/v1/systemone` shim.** Expose our typed-decision path behind Kev's `/v1/systemone` contract (`kev/predictors.py:61-92`, `kev/benchmark.py:34-66`) and score it with `kev.benchmark --remote` on Kev's committed transfer-v4 dev (764 records) and scienthoon-v1. Multi-token candidates return JSON-arm probabilities; send options in insertion order (Kev is order-sensitive; gojev sorts keys). Report accuracy, ECE and coverage against the committed Kev/Jev reports — the Jev figures are report-level only, and the Kev-vs-Jev coverage CI already includes 0. Evidence: intake-1498, intake-1515. Inference-gated — **GATE: mi210-window** (operator ruling Q3, 2026-09-29). Conditional follow-on (absorbs TD-20): only if a trained decider beats our path on the external OOD read, serve Kev-4B on llama.cpp-experimental from fresh production (port common/decision.{h,cpp} + tools/kev/kev-decide.cpp as new files with a sidecar head.json).
  - 2026-11-09 audit: SV. Needs inference and external repo pins; still relevant. Compute list.
- **[declined: ws58 2026-11-03 content-review: merged into TD-19 as its conditional]** **TD-20 — (conditional on TD-19 showing a trained decider beats our path) Serve Kev-4B on llama.cpp-experimental.** Branch from fresh production ffc1bac; port `common/decision.{h,cpp}` + `tools/kev/kev-decide.cpp` + 2 CMake lines as new files with a sidecar `head.json` (no `src/` change, no fork merge). Source weights from `taigrr/kev-4b-gguf` at a pinned sha, sha256-verified against `manifest.json` (merged GGUF avoids the 4B/9B `out_proj` LoRA conversion gap). Parity vs HF-fp32 on committed decision-v7 dev rows plus fixtures with unsorted keys, a long state and 4B; test `seq_cp` fan-out against v10's recurrent rollback-index abort on shared cells. Evidence: intake-1498, intake-1514#00, intake-1514#05, intake-1515.
- [x] **TD-21 — Re-audit of every free-text JSON consumer (operator, 2026-09-24).** ✅ 2026-09-24 — every sub-row
  landed (the last, TD-21.33c, orch `c347600e`). Audit: `artifacts/audits/td-json-consumer-audit-20260924.md`.
  TD-21.0, TD-21.H, TD-21.1 and TD-21.2 … TD-21.35 (incl. TD-21.EQ1, TD-21.22a/b, TD-21.31 (a), TD-21.33a/b) are in
  the [completed ledger](../completed/typed-decision-plane-completed-through-2026-09-29.md). One residual stays here:
  - [x] **TD-21.1a — the FINAL() repair is INERT in production (OP-51).** All REPL schema validation — and so TD-21.1's
    repair and 422 — sits behind `final_schema_validation` (default OFF since `86957b6e`; production runs
    `baseline`). Live 11:53Z: `/chat` `force_mode=repl` with `output_schema {result: int}` returned the bare `51`, no
    error. Enabling is a production-posture pin in `orchestration/runtime_flags.spec.yaml` (reason + since) plus the
    live flag; it changes what `/chat` callers receive (a conforming object or a 422, instead of an unvalidated
    value). Recommendation: enable.
    - *2026-09-24:* OP-51 enabled (orch `98edfeb0`, `PRODUCTION_FEATURE_WAVE_OVERRIDES`), API reloaded. First
      live smoke (13:41Z) of REPL `/chat` (`{17*3, output_schema {result:int}}`) returned **HTTP 500**
      "repeated no-progress nudges at `coder_escalation`" (flag off it returned `51`), with `Model fallback:
      coder_escalation → frontdoor (connection_error)` in the logs although :8083 is healthy. Operator chose to
      **SUSPEND** → orch `6b26f3ae` (flag back OFF), API reloaded 13:48:02Z. Kept `[ ]` — regression diagnosis
      in flight (schema preamble ```` ```json ```` fence vs escalation routing).
    - [x] Root-cause the `coder_escalation → frontdoor (connection_error)` fallback logged during the OP-51
      smoke even though :8083 answers health checks — a live routing/connection defect independent of the
      schema-validation flag itself, surfaced only because OP-51 exercised the escalation path.
      ✅ 2026-09-30 — explained, not a routing defect. The ✅ note below attributes the 13:41Z failures to
      placement timeouts behind an AutoKernel CPU-floor calibration holding the whole CPU region, with a clean A/B
      at 15:35Z once the region was free. The `connection_error` label itself was a misclassification: the
      contention-gate denial of a healthy, busy backend fell through `health_tracker.classify_failure`'s string
      default to `connection_error`. Orch `8977f540` (2026-09-24, on main) classifies it structurally as
      `admission_denied` (`FailoverReason.ADMISSION_DENIED`, `src/roles.py`; `src/api/health_tracker.py`).
    ✅ 2026-09-24 — ON in production (orch `07fcf422`). History: enabled `98edfeb0`; the 13:41Z smoke's HTTP 500
    and the first A/B (all arms failing, flag on AND off, and the last-good d12202f2 too) were placement
    timeouts behind an AutoKernel CPU-floor calibration holding the whole CPU region — the REPL masked them as
    "all comments" no-progress failures (fixed: orch `32a52fba`, infra sentinels end the turn with the right
    status; live check → HTTP 504 in 1 turn). Suspended `6b26f3ae` meanwhile. Clean A/B 15:35Z with the region
    free: on 3/3 HTTP 200 `{"result": 51}`, off 3/3 HTTP 200 bare `51`, 1 turn each. (DS41 run 8 held the region
    ~13:43Z→15:32Z, stopped by the operator; the region-hog-vs-production-serving policy question is evidence
    under `autokernel-unified-surface-program.md` U4-SEQ, not a new decision — OP-41 already rules that space.)

#### Coherence judge and `coherence_gate` rollout (filed 2026-10-04, workspace-ec)

*Ownership:* workspace-ec owns this section. It comes from the operator-approved replacement of the INF-70
classifier (2026-10-04); the rest of the handoff stays with the research-intake lane. The judge reuses TD-29's
native single-token path and its sidecar.

**Operator-approved scope (2026-10-04):**
- The judge is orchestrator-hosted.
- A cloud judge (`codex-luna-low` or `sonnet-low`) is allowed only when the caller itself is cloud-hosted.
- Local work targets the CHAMPION build (the sidecar, which becomes v11), with no promotion now.

**Evidence:**
- `artifacts/gpu-block-27b-20261004/analysis/q38t7-rescore/{AUDIT,RESCORE}.md`
- `artifacts/gpu-block-27b-20261004/analysis/classifier-rectify/RECTIFY.md`

- [x] **TD-30 — tier-2 coherence judge as an orchestrator-hosted typed decision.** ✅ 2026-10-04 (workspace-ec)
  - **Library:** shared `coherence_gate` on research main 95157ad7 (`scripts/lib/coherence_gate/`, schema
    `epyc.coherence_gate.v1`, 55 tests). Tier 0 is paired byte-identity; tier 1 is ground truth plus the
    length-aware `degeneracy.v2`. It refuses synthetic token ids, and an INCOMPLETE gate is never a PASS. Adoption
    notes and the migration list are in `epyc-inference-research/docs/coherence-gate.md`.
  - **Endpoint:** `POST /v1/typed/coherence_judge` (localhost only) on orch main f8c9c0a3, DEPLOYED by an API reload.
    The window guard was verified live: it refuses local calls while the MI210 or AutoKernel CPU window is held.
    Every verdict carries a `calibration_id`, and an uncalibrated judge is refused unless `allow_uncalibrated` is set.
  - **Audit of past decisions:** the INF-70 classifier was a near no-op on every chat client, because of the fake
    ids `list(range(n))`. The direct version has a length-biased `uniq`. No production decision flips. The MTP
    divergences were re-read and are fluent alternative continuations.
  - [ ] **TD-30a — merge the champion-sidecar judge backend to orch main.** Branch `feat/judge-champion-backend-ec`
      - 2026-11-09 audit: STALE-PREMISE rewritten above. Rebase `feat/judge-champion-backend-ec` onto current origin/main (typed_decisions changed 2026-11-07, d827fd05); `feat/judge-embed-excerpt-ec` also contains 4359b43c and carries TD-30c. Re-check the 'champion sidecar' binding against champion C9 and the v10 kernel-store paths before merge; the box must not assume `llama.cpp/build/bin`. Do not delete the branch.
    @ 4359b43c, not merged. It adds:
    - the `local:champion_sidecar` native backend, which probes `/health` and `/props` only and never starts a
      process;
    - `auto` backend selection;
    - a `judge_key` bound to the serving build;
    - the prefill addendum TD-31 generalises: a fixed head, then rubric, then prompt, then base, with the candidate
      last; `id_slot` pinned only on the sidecar; a `max_judged_tokens` excerpt; per-call `prompt_ms` / `prompt_n` /
      `cache_n` / `prefix_reuse_rate`.

    Done when it is merged with tests green, the API is reloaded, and a call log shows the backend selection
    recorded. With the sidecar down, a 503 `sidecar_unavailable` counts as the selection proof.
  - [ ] **TD-30b — calibrate the judge.** Run the seeded 32-pair calibration set, which includes real INF-70 MTP
      - 2026-11-09 audit: SV, depends on TD-30a. GATE champion-sidecar CPU window; still relevant (compute list).
    divergences, on `local:champion_sidecar` native (**GATE: champion-sidecar CPU window**). Verify the cloud judges
    (`codex-luna-low`, `sonnet-low`) as `verified_live` on the same set. Done when each backend has a sealed
    calibration row (`calibration_id`, agreement on the seeded labels, backend, build, scoring), and the
    uncalibrated refusal lifts only for those backends.
  - [ ] **TD-30c — embedder-based excerpt option for the judge (operator suggestion, 2026-10-04).** When a divergence
      - 2026-11-09 audit: SV + SP. Embedder choice moves with EG2: specify the embedder (EG2@256 at v11, BGE today). Doable after TD-30a.
    exceeds `max_judged_tokens`, the excerpt is positional today: head, tier-0 divergence span, tail. Add an option
    that chunks base and candidate, embeds the chunks with the BGE embedders already served (BGE-M3 /
    bge-large-en-v1.5), and judges the most semantically divergent aligned chunks. Record the excerpt method and the
    chosen spans in the verdict. Done when the option exists behind a parameter with tests, and on the TD-30b set it
    agrees with the labels at least as often as the positional excerpt, at an equal judged-token budget.
  - [ ] **TD-30d — migrate the coherence consumers** per `epyc-inference-research/docs/coherence-gate.md` §2:
      - 2026-11-09 audit: SV, doable now: research-repo code move; `epyc-inference-research/docs/coherence-gate.md` exists (verified).
    1. The Q38-T7 runner (`q38_t7.py` + `lib_gpublock.py`) moves to `coherence_gate.evaluate` with the no-draft anchor
       and needle truth rows. This is the successor that Q38-T7b in `qwen38-27b-replace-qwen36.md` names.
    2. The INF-70 harness1 client, via CLS-RECT-1a in `cpu-decode-roofline-program.md`: patch 04 first.
    3. G2-CONC / E-GATE / PROD-1 are a text change in CLS-RECT-1, done by the `inference` lane.
    4. The AutoKernel T0 gate: no swap. It is already paired and sits inside the immutable evaluator bundle.
    5. The cousins (DAR-LAT `critic_thread_gate.v2.py`, batch-envelope `conc.py`) re-point on their next version bump.

    DS41's own gate is DS41-C118 in `deepseek-v41-flash-evaluation.md`. Done when items 1 and 2 produce
    `epyc.coherence_gate.v1` verdicts and items 3–5 are each recorded as done or not-needed.
  - [ ] **TD-30e — ONE ratification package for the coherence instrument eras (operator signs; agents prepare).**
      - 2026-11-09 audit: SV, operator signs. `instrument_eras.yaml` is human-only; the latest eras are E18-E20+, so number the new rows after them. Agents prepare only.
    It covers two era rows for `epyc-orchestrator/orchestration/instrument_eras.yaml`, which is a human-only
    trust boundary:
    - `OC1-coherence-gate-v1` (draft in `docs/coherence-gate.md` §1a);
    - `CLS1` for the harness1 labels (draft in `analysis/classifier-rectify/07-instrument-era-row.DRAFT.yaml`).

    Set CLS1's `from:` to patch 04's root commit time. Leave the Annex B amendment B-COH-1 out unless the paired gate
    is made mandatory for promotion. Prepare one ratify script with a `--validate-only` mode; the operator runs it.
    Operator queue row OP-75, text prepared in `/mnt/raid0/llm/tmp/wrapup-ec-gpublock2/INDEX_ROWS.md`. Done when the
    receipt exists and both rows are in the file.
  - [ ] **TD-30f — check the orchestrator's runtime unique-ratio guards for the same length bias** (RECTIFY §6f).
      - 2026-11-09 audit: SV, doable now: zero inference; `quality_detector.py::detect_output_quality_issue` named.
    Current source correction2026-10-06: the guards are `src/classifiers/quality_detector.py::detect_output_quality_issue`
    (only its20-word trigram branch), `src/pipeline_monitor/anomaly.py::detect_repetition_loop`
    (9-word trigram minimum), and `src/llm_primitives/inference.py::_detect_streaming_repetition`.
    The third is not a unique-ratio guard: it counts exact repeated three-line substrings of at least60characters
    in the last4,000characters, with separate streaming cadence/schema constraints. The earlier coherent-text
    threshold finding concerned the historical classifier and is not evidence that these guards false-flag.
    Preserve this parent's need for independently supported coherence labels and output-length denominators. Replay the `length_bias.py` corpora
    (`analysis/q38t7-rescore/`) through each guard's threshold, with no inference. Done when each guard has a
    measured false-positive rate by output length, and any guard that fires on coherent long text is made
    length-aware or switched to the `degeneracy.v2` loop trigger.
  - [x] **TD30F-PUBLIC-REPLAY — source-bound authored-Markdown successor and runner controls.** ✅2026-10-06 MAIN accepted [original aggregate and native custody](../../artifacts/ni08/td30f-public-replay-20261006/README.md): 218 pinned public documents; trigram triggers 0/218 for each guard, stream-body triggers 0/217 with one tail-line exclusion; four original controls pass. This completes the scoped successor only. No coherence labels, false-positive rate, length interaction, stream cadence or threshold recommendation; TD-30f remains open.
- [ ] **TD-31 — prefill optimisation for typed decisions generally.** (filed 2026-10-04, workspace-ec, from TD-30a)
  - 2026-11-09 audit: SV. The build is doable now; the speed claim needs an inference window. Overlaps TD-29.M0a/M4 (prefix reuse): keep one owner.
  Carry the judge's prefill addendum to every Jev typed decision:
  - **prefix-stable ordering:** a fixed head of instructions and label definitions, then the shared context, with the
    question-specific part last;
  - **a pinned slot:** `id_slot` plus `cache_prompt` on the sidecar and on explicit `pin_slot` opt-in lanes only,
    never on production chat roles;
  - **judged-length caps,** with the excerpt recorded;
  - **per-call metrics:** `prompt_ms`, `prompt_n`, `cache_n`, `prefix_reuse_rate`, rolled up per question kind.

  It depends on TD-29.M0a (`cache_n` on the `/completion` lane) and is confirmed by TD-29.M4. Done when a sidecar
  receipt shows `cache_n` > 0 and `prefix_reuse_rate` per question kind for repeated-head decisions, and the
  ordering is enforced by a test on the prompt builder.

#### Immediate ROI path — 2026-09-25

- [x] **TD-22 — Refresh the public Jev contract and evidence boundary.** ✅ 2026-09-25 — Current official material was consolidated into intake-1470#record and intake-1472#record: moving aliases require resolved-model capture; current limits are dynamic; same-request questions inspect one shared state independently; dependent decisions require another call or host composition; host code owns permission, freshness, candidate existence, and outcome verification; current latency language is vendor guidance rather than an SLA; the hierarchy result is a four-case smoke; and the independent day-run cost report supplies no labels or public replay.
- [ ] **TD-23 — Shared typed-decision screen.** After the CJ-15 fixture and HS-TD-4 receipt exist, compare one available local compact decision backend against the constrained incumbent readout on one sealed, row-pinned workload (operator ruling Q1, 2026-09-29: local models only; the hosted-Jev arm is removed). Freeze the manifest, backend/model revisions, requested/resolved identities, candidate descriptions, prompts, threshold-selection split, and held-out source groups; retain per-row probabilities and raw outputs, invalids, failures, abstentions, timing, and cost in `decision_receipt.v1`. Cross position, order, opaque keys, semantic rebinding, response format, repeated calls, irrelevant siblings, explicit unknown, and long-context placement; report accuracy, consistent accuracy, ECE/Brier, flip rates, probability divergence, clustered intervals, and total decision cost. Predeclare quality, calibration, and operations stop/promotion thresholds; keep same-state independent questions, staged dependent decisions, and hierarchy search as separate protocol classes. This is the common cheap screen under the [minimum viable research execution contract](eval-tower-program.md#minimum-viable-research-execution-contract), not a paper-wide reproduction. Sources: intake-1577#record, intake-1583#record, intake-1606#record, intake-1618#record, intake-1619#record, intake-1623#record, intake-1634#record, intake-1637#record, intake-1654#record, intake-1660#record, intake-1676#record, intake-1681#record. The run is **GATE: mi210-window** (operator ruling Q3, 2026-09-29).
  - 2026-11-09 audit: SV. Waits on the named external events CJ-15 fixture and HS-TD-4 receipt.

##### Trigger records — materialize only when the named condition fires

- **TD-24 — GLiNER2.5-Decide follow-on.** Activate only if the GLiNER backend in TD-23 clears the held-out quality, calibration, and operations gate or EPYC needs a claim-bearing public reproduction. Then pin model, library, and Fast Decisions revisions; pass `multi_label`; emit all 2,900 public rows and per-head outputs; report macro-domain and pooled-head exact match separately; and test constraint invariance, brute-force optimality on small schemas, candidate retention, infeasibility behavior, and `Classifier` versus `classify_text`. Do not claim the unavailable held-out result. Sources: intake-1586#record, intake-1587#record, intake-1588#record.
- **TD-25 — CLM specialized-head follow-on.** Activate only if the released default head in TD-23 clears the held-out quality, calibration, and operations gate. Pin exact base/head hashes and candidate-description policy; a task-specific projection head may enter shadow only after a group-disjoint comparison beats the incumbent on quality and calibration. Default-head JevBench results cannot substitute for that gate, and full three-stage training remains dormant until this candidate gate passes. Sources: intake-1581#record, intake-1589#record, intake-1590#record, intake-1591#record.
- **TD-26 — Phishing transfer.** Activate when phishing classification becomes an EPYC product or benchmark workload. Freeze the PhishNChips CSV, revision, licenses, prompts, and raw calls; report its synthetic arm separately from a pinned real-email split, with proper scores, order/key controls, model resolution, per-row outputs, and uncertainty. Sources: intake-1659#record, intake-1678#record.
- **TD-27 — BTZSC replay.** Activate when BTZSC-style classification becomes an active benchmark or claim surface. Replay historical commit `8a0d52cbe423` and current v0.1.2 separately, freezing rows, models, verbalizers, prompts, permutations, hardware, precision, failures, and raw timings. Alphabetical label sorting is one deterministic assignment, not robustness evidence. Sources: intake-1660#record, intake-1679#record, intake-1680#record, intake-1681#record.

#### Wiring policy (2026-09-18, operator-directed)

- **Fan-out decision rule (TD-8, implemented in `src/typed_decisions/fanout_policy.py`):** exactness-required + native-eligible -> native id-only per question (11.98x n=1, contested: 9.60x at n=4 pending TD-1d.0; isolated); stability-tolerant batches of >= 8 -> batched (2.2x at 87.5% measured agreement); otherwise sequential JSON. The 87.5% figure governs the choice per surface.
- **Tool arguments (item 1):** closed-set wiring landed in the orchestrator tool path (`src/repl_environment/context.py` `_dispatch_tool`) behind `typed_decisions_tool_args` (default off), fail-open to model-provided args. Shadow-only until v11 (operator ruling Q4, 2026-09-29): TD-29.
- **Deferred but tracked:** routing replay -> TD-7; judge redundancy -> CJ-13/CJ-14 in `canonical-judge-suite-revamp.md`; episodic pre-write gate -> M-19 in `episodic-memory-integrity.md`; harness items -> HS-TD-1..3 in `harness-selection-and-integration.md`.
- [x] **TD-8 — Fan-out policy helper.** Implemented + 18 tests (`fanout_policy.py`, provenance-stamped constants). ✅ 2026-09-18


#### Research Intake Update — 2026-10-04 — P1 acceptance and retained qualifications

Filed from the operator-approved [decision-tools plan](../../research/intake-stage3-plan-2026-10-03-decision-tools.md)
at `3911ec91`. This refines TD-29, TD-29.M0a, TD-12 and TD-29.M2; it creates no checkbox.
TD-18 owns decision calibration and TD-23 owns backend selection. Workspace-ec retains TD-30/31, including
TD-30b's judge calibration and TD-31's general prefill work; these are interface dependencies, not duplicated tasks.

**P1 six controls and decision.** Freeze extended TD-4 cases, tool schemas, allowed menus, state/model/build/readout
identities and outcomes. TD-12's baseline is current same-server REPL generation of operation and arguments;
M2's baseline is the full failed-call-to-REPL-repair sequence, including subsequent turns. Keep proposed/executed
operations and args, selected/unused failures, calls, timings, fallback and actual final outcome. A different proposed
tool needs independent correctness labels: the executed original tool's outcome is not its counterfactual label.
Tune on development groups only; hold out tool/state families or later traffic. Count all valid/invalid calls,
unsupported schemas, stale menus, transport failures, abstentions and eventual task failures.

Reject every authority/freshness violation; valid inputs must incur zero repair calls. Before collection record the
task-specific loss/cost basis and sample/precision budget; otherwise perform conformance only. For the initial shadow
screen, predeclare TD-12's two-percentage-point exact-action non-inferiority margin, and M2's 5% upper selective-risk
bound (wrong accepted repairs / all accepted repairs) and 10% lower useful-coverage bound (correct accepted repairs /
all invalid eligible calls), using the owner's paired/group-aware 95% intervals. The 2pp margin is a maximum tolerable
offline loss for restricted non-consequential fixtures; 5%/10% are screen tradeoffs, not permission for consequential
production errors. Insufficient accepted-repair evidence requires abstention. Advance only when held-out bounds pass
and paired total time/cost per correctly completed action improves with an interval clearing zero.
Shadowing adds overhead: offline candidate timing estimates substitution economics, while an operational latency
claim requires a later matched execution comparison. Unresolved precision permits no activation.

**Existing M4 performance follow-through.** Use M4's current sidecar/gate, frozen manifest, current same-server
incumbent, raw per-case counts/outputs including errors, development/held-out cases and full failure/abstention
denominators. Predeclare rejection of any result/argument regression. Report paired prefill and total-wall changes
with constitution-required intervals; claim benefit only when the applicable interval clears zero. If reuse is
absent, identify and fix only the actual prefix break; if present, make no cache rewrite. TD-31 owns general prompt
ordering/explicit slot opt-ins; slot-pinning defaults remain unchanged.

**K2/K3/K4/K5/K7 — retained decision qualifications.** Keep corrected release/source-tree/scoring-edition/publication
scope in the source records; the prior truncated-tree calibration scripts-absence finding was retracted.
Historical quotations and current vendor pages retain separate attribution. Hosted products supply schema/economics
context only; the local-only ruling remains. Existing prepared actions own permission, live menus, freshness,
read-set revalidation and fallback. Preserve raw versus normalized distributions, rounding/invalid mass and confidence
definitions. Choice top-option correctness calibration, Noul event calibration, ordinal Score quality and logical
coherence are distinct. Teacher fidelity is not gold correctness; uniform placeholder relevance labels are ineligible.
Keep per-head/group support, ties, zero-support outcomes, option-order controls, repeat noise, input loss and
refusal/invalid/transport states explicit. Requested aliases are not resolved artifact identity. External comparisons
retain method/addendum/scorer/cohort revisions, raw-to-aggregate linkage, complete denominators, timing scope and
separate code/response-data permissions. Separate observed billing from price/proxy estimates and final-attempt
elapsed time from retry-inclusive completed-action cost. Same-item threshold fitting is descriptive, not held-out
certification. Newly landed coherence machinery is reused rather than rebuilt.

**M1/M6/M7/M8 — broader follow-ons, prose only.** TD-23 may compare one compatible local Clef/Flash/AutoTrust candidate
when it and a sealed workload are available in the existing coordinated window; no candidate is selected here.
Resolve a particular external score only when it affects that choice and existing reviewed evidence cannot settle it.
A provisional narrative needed as factual rationale requires separate intake qualification; the five provisional
records supply no factual premise and this campaign adds no fourth wave. Verify a released hardware/modality path
only for an actual selected candidate that needs it. Production substitution remains a separately reviewed v11/cutover
decision. Risk determines safeguards rather than candidate relevance.

Record discussion: intake-1855#record, intake-1859#record, intake-1862#record, intake-1863#record,
intake-1865#record, intake-1869#record, intake-1875#record, intake-1882#record, intake-1884#record,
intake-1885#record and intake-1891#record. Their primary anchors and corrections remain the factual warrants.

#### Open Questions

- Which confidence statistic, if any, survives local calibration well enough to gate an action?
- Does the production server's (`production-consolidated-v10`, final freeze 2026-09-22; the question was first asked against frozen v9) json_schema→GBNF converter accept the nested probability-map schemas the adapter generates?
- Does question-order contamination on our stack reproduce the 24.7% seen in intake-1486, or is it smaller at our batch sizes?

#### Notes

All numbers above are from dive-verified entries; none may be promoted to a deployment measurement until TD-2/TD-3
produce our own. This stub follows the 2026-09-17 operator steering; the vendor's own documentation states confidence
is an undisclosed statistic and calibration is group-level only.

- [x] **TD-18-NI-INPUTS — prospective exact-byte calibration input binding.** ✅ 2026-10-06 — [Contract](../../docs/reference/calibration-input-byte-bindings.md), original37473538913 TRUE34/34 after MAIN3370Git+2contexts/all3380 original API ZIP review; APP main 99d8ada7 / ROOT main 525c5bcd. The CLI binds exact state/questions/labels bytes at the shared read/parse boundary; direct API metadata is caller_asserted or null. Existing metrics, rows and shared provenance helpers are unchanged. Broader TD-18 receipt metrics/probability-source work and live calibration gates remain open.


##### 2026-10-08 TD-29.M0a.S0 accepted current-source controls

Original push run `37729628899` attempt1 at ROOT `11f1b00ae478a76544eb3b649f4b0d9af199095a` passed all209 cases from seven whole mocked modules (175 AST definitions): TD122 plus unchanged HG87, zero failures/errors/skips. APP current-tip merge `eadb959172fbc433da41aaf069c1bcf20c6ce98f` is promoted to remote main by one ordinary nonforce fast-forward from76624a91. MAIN independently accepted the source merge, four-file recipe commit,123-command source-first publication, original209 custody and120-command main promotion. Earlier FALSE/NULL archives remain immutable. Existing native CI adapter/shared carrier returns Judged/Located observation only; no runtime activation, model quality, inference, performance or three-arm sidecar result.

[Original209 accepted custody](../../artifacts/ni08/td29-current-source209-acceptance-20261008/README.md). This closes only TD-29.M0a.S0 and its single VB companion as one scoped source/control child. TD-29.M0a, TD-29.M4 and the TD-29 inference parent remain open for their own fresh evidence.


- **2026-10-31 FAILED-RUN `codex-ni-td29-m4-cache-r3-20261031`:** outer rc70; launcher reports `DRYRUN_REFUSED: malformed claimed_cpus`, then in-claim RLIMIT/affinity/cgroup proof refusal before the job. class=admission; no RESULT.json and no 18-pair cache verdict. Missing evidence is INCOMPLETE, never zero-cache proof. Owner action: repair and qualify the claimed-CPU admission path, then run the original 18-pair rule. Evidence: `/mnt/raid0/llm/tmp/codex-ni-td29-m4-cache-20261030/ws58-launcher.out` (snapshot SHA-256 `18b72eb1c99ddced1a44785afe6e22e5216a930603279b4b69920d7abd97e4ab`). [belief: cc] [Bounded evidence](../../artifacts/compute/ni-filing-20261031-0230/MANIFEST.json).
- **2026-10-31 FAILED-RUN `codex-ni-td29-m4-cache-r4-20261031`:** rc1 after actual normal resource admission; 18/18 case rows and 36 calls, but only 12 valid pairs. Six `file_ticket` pairs were invalid: free-form `assignee=null` violated its string schema, and typed dispatch reported missing severity, escalate, effort_points and categories. Class=unknown pending investigation of model versus integration; the declared all-18-valid rule makes the overall result INCOMPLETE. Each of the 12 valid pairs showed 17 common rendered bytes / 3 tokens and typed `cache_n=0` with token-count matches; these scoped observations do not establish a full-run no-cache conclusion. Owner action: inspect schema/dispatch mismatch and preserve all 18 original records and exposures; use a newly identified immutable qualified successor only if needed. [Evidence](../../artifacts/compute/codex3-kpf-td29-filing-20261031-0240/SHA256SUMS). [belief: cc]

##### Research intake 2026-10-31 — ws58 batch (intake-2545..2602)

Operator-approved 2026-10-31 (plan revision 2, `research/intake-stage3-plan-2026-10-31-ws58.md`, sha256 `043e502133cae214175ea3f2a395f575e6ca13b9f3ee058525ed020264ab5012`; relayed by the ws58 coordinator; budget approved: about 13 MI210-hours for the drafter pilot, 6-9 engineer-weeks for the race checker, the 95.5 GB ThinkingCap download; D1 confirmed: in-weights calculator declined, GPU reason recorded on intake-2550/2574; D2 approved: scratch upstream builds are measurement instruments only). Trigger records below are prose with no checkbox until a reviewed session confirms their condition.

- *Moved to [`model-evaluation-queue.md`](model-evaluation-queue.md) § Track: meq-carve-typed-decision-plane on 2026-11-03 (BRF-T1-MEQ, operator D2): **TD-23.D1**.*
- [x] **TD-18.1 — Pin GGUF decision backends in the TD-18 calibration receipt (intake-2593#record).** For llama.cpp decision backends, the receipt records the GGUF sha256, every decision.temperature.* metadata value (the endpoint scales probabilities by them and exposes no request-time override), the server build commit, and the -np/-b/-ub flags, because each of these changes the probabilities being calibrated. ✅ 2026-11-01 — APP `a68318e39581e7f4a0730da264657eab726b4d4e`, proof `c27680ecfe4b546a2de1d1e9dfc48b6be506e548`: 76/76 source/fixture controls in `artifacts/typed_decisions/td18-gguf-pin-20261101/`; opt-in direct JSON transport explicitly identified, no SystemOne scaling or quality claim. ROOT read-side `07cbe0026e9f0bedef8dc9bc25d04df740e86454`, proof `f677723aabf8b75085c3fc2322d665a4e320120f` in `artifacts/typed_decisions/td18-belief-pin-20261101/` (53 controls and synthetic producer-to-planner canary). [no-belief: source instrumentation and synthetic conformance]
- *Intake knowledge note, K4, row W2SP-4 (intake-2582#record):* Record in TD-23 candidate list that d1-2B/3B are VL models with LFM Open License v1.0 and that the llama.cpp path supports noul/choice/score only; routing questions are choice+score so the subset is sufficient.
- *Intake knowledge note, K4, row W3DEC-5 (intake-2593#record, intake-2595#record):* Pin the serving-safe API subset for the probe and any shim: only choice/score/noul; options within the model limit (52 openjev, 255 laya; read from the model, d1 limits unread); state must fit one ubatch (use -ub, not -b; 30073); avoid router mode with ...
- *Intake trigger record (no checkbox until it fires), M4, row W4UP-4 (intake-2601#record):* Add a GENERIC-readout arm to TD-23 (any lineup chat model, thinking off, U+22B2 label readout) as a comparator to dedicated decision backends after the systemone base is in the screen build.
- *Intake trigger record (no checkbox until it fires), M4, row W4UP-5 (intake-2602#record):* Offer/track the group-parent checkpoint fix for hybrid decision models; evaluate by prompt-token count (1254 vs 827 shape) on our model before adopting.

## Track: x-mas-text-routing
<!-- gate: none -->

> Folded from `handoffs/active/x-mas-text-routing.md` @ `b33c4e7a5fd1` on 2026-11-02 (BRF-T1-F26, route 1a, operator D1/D5; retired row RTG-45 → RTG-09). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### X-MAS Heterogeneous Text-MAS Routing Spike

**Status**: classifier/table scaffold, guarded enforce path, true function-axis 5x5 sweep, enforce-eligible `orchestration/xmas_winner_table.yaml`, live A/B harness, machine-readable held-out verdict reporting, no-inference regression diagnostics, incumbent-aware constrained enforce policy, and production enablement are all landed. The 2026-07-03 repaired quiet-window A/B for `incumbent_constrained_cheapfirst_v2` returned `decision.status=promote_candidate` with no blockers. `epyc-orchestrator` `d4a6c927` enabled `xmas_routing.mode: enforce`, reloaded the orchestrator API, and post-restart Fable5 reports `xmas_production_path=ready`; remaining work is post-enable telemetry monitoring, not another repaired-policy evidence gate.
**Created**: 2026-05-19 (post-latent-MAS-cluster deep-dive)
**Categories**: agent_architecture, cost_aware_routing, benchmark_methodology, routing_intelligence
**Priority**: HIGH (production routing is now enforcing the guarded function-axis table; monitor live telemetry and keep rollback path obvious)
**Depends on**: `routing-intelligence.md`, `routing-and-optimization-index.md`, `../completed/meta-harness-optimization.md`, `hermes-outer-shell.md`
**History**: [x-mas-text-routing-history-through-2026-06-19.md](../archived/x-mas-text-routing-history-through-2026-06-19.md) preserves the completed scaffold/sweep/A-B chronology compacted out of this active handoff.
**Source deep-dive**: [`/workspace/research/deep-dives/2026-05-19-latent-mas-cluster.md`](../../research/deep-dives/2026-05-19-latent-mas-cluster.md)

**Current-runtime correction (verified 2026-07-29):** the historical enforce cutover remains recorded below, but the current `classifier_config.yaml` has `xmas_routing.mode: shadow` (with a 2026-07-16 rollback note requiring fresh speed/quality revalidation). No API listener and no AutoPilot process were present, and the newest X-MAS A/B artifact is 2026-07-03; post-enable enforcement telemetry therefore does not currently exist to monitor. Leave the monitoring checkbox open until a future verified enforce interval has live records. The read-only Fable5 report is additionally blocked by a runtime-facts circular import, so it cannot certify the live path until repaired.

#### Objective

Replicate the X-MAS (intake-557, arxiv:2505.16997, `github.com/MASWorks/X-MAS`) domain x function optimal-model methodology on the EPYC production stack, build a domain/function winner table, and only route live traffic through it if held-out production evidence beats current routing without unacceptable latency or domain regressions.

#### Current Evidence

- The deterministic 5-domain x 5-function classifier and winner-table loader are implemented in `epyc-orchestrator/src/classifiers/xmas_routing.py`.
- The production hook is default-off and guarded: enforce requires a complete evidence-backed table, confident classification, no forced role, and downstream guard pass/fail semantics still get final say.
- The true function-axis sweep completed in `epyc-inference-research` from 500 rows and produced the enforce-eligible `epyc-orchestrator/orchestration/xmas_winner_table.yaml`.
- `epyc-orchestrator` `21d96da2` wires that table into `orchestration/classifier_config.yaml` with `mode: off`, `winner_table_path: orchestration/xmas_winner_table.yaml`, and `require_complete_table: true`; this removes the missing-table production-readiness blocker without enabling live route mutation.
- The live A/B harness exists at `epyc-orchestrator/scripts/benchmark/xmas_live_ab.py` and now emits machine-readable `decision` and diagnostics summaries without rerunning inference.
- The 25-prompt held-out rerun (`benchmarks/results/runs/xmas_live_ab/20260618-215637-heldout-resilient-rerun`) returned `decision: hold`: overall score delta `-0.35`, latency ratio `16.18x`, no lift domain, and regressions in `code`, `math`, and `reasoning`.
- `epyc-orchestrator` `209ff62e` surfaces that latest held-out A/B verdict inside `scripts/autopilot/fable5_gate_report.py --strict`, so the aggregate Fable5 pickup check now explains the X-MAS blocker rather than only reporting `mode=off`.
- The refreshed replay diagnostics in `epyc-orchestrator` `96acc5e` identify the dominant mechanism: X-MAS overrode 23/25 prompts, mostly replacing baseline `coder_escalation` with slower `worker_general`; there were 7 baseline-only quality wins, 0 X-MAS-only wins, 20 prompts with at least `3x` latency regression, and 2 X-MAS timeouts.
- The constrained policy landed in `epyc-orchestrator` `24baac4`: enforce now treats the existing route as incumbent and only replaces it when the current cell evidence evaluates both roles and proves quality lift or material speed lift within a 1.10 latency cap. A no-inference replay diagnostic against the failed held-out bundle estimates that the policy would suppress 22/23 prior replacements (`incumbent_role_not_evaluated`) and allow only the one evidence-backed speed lift.
- `epyc-orchestrator` `7f20920` stamps new X-MAS A/B artifacts with `xmas_policy=incumbent_constrained_v1` and makes the aggregate Fable5 gate require that policy id before any held-out `promote_candidate` can count as enforce evidence. Existing 2026-06-18 summaries are therefore explicitly `unknown_legacy`, so the next required run is a fresh quiet-window constrained-policy A/B rather than a replay of old rows.
- `epyc-orchestrator` `91bdf6d` hardens the X-MAS real-run quiet-window preflight: `--host-quiet-confirmed` is still required, and the runner now refuses known competing evidence/benchmark coordinators including AutoPilot, DCP/BEP A/B, DS-E1 KV measurement, seeding, migration, placement, and generic benchmark runners before any orchestrator reload or chat call.
- The 2026-06-21 quiet constrained-policy A/B (`epyc-orchestrator/benchmarks/results/runs/xmas_live_ab/20260621T112005Z-constrained-policy`) wrote 100 rows and restored `xmas_routing.mode=off`. It carried `xmas_policy=incumbent_constrained_v1` / `required_xmas_policy=incumbent_constrained_v1`, but the verdict remained `hold`: score rate regressed from `0.60` baseline to `0.35` X-MAS (`score_delta_xmas_minus_baseline=-0.25`), while latency improved (`latency_ratio_xmas_over_baseline=0.714`). Regressions were `code`, `math`, and `reasoning`; blockers were `overall score delta -0.250 < required 0.050`, `no domain improved by >= 0.050`, and `domain regressions: code, math, reasoning`.
- `epyc-orchestrator` `f517902d` repairs the same-cheap-role failure mode by preserving try-cheap-first when X-MAS enforces the configured cheap role and adds row-level `xmas_meta` capture. `epyc-orchestrator` `b108f865` versions the repaired policy as `incumbent_constrained_cheapfirst_v2` and makes that policy id the new required evidence marker.
- The 2026-07-03 repaired-policy quiet-window A/B (`epyc-orchestrator/benchmarks/results/runs/xmas_live_ab/20260703T213541Z-constrained-policy-v2`) wrote 100 rows across the same 25-prompt ABBA replay, restored `xmas_routing.mode=off`, and returned `decision.status=promote_candidate` with no blockers. Baseline score rate was `0.60`; X-MAS score rate was `0.70` (`score_delta_xmas_minus_baseline=+0.10`). Median latency improved (`latency_ratio_xmas_over_baseline=0.938`). Lift domain was `reasoning`; regression domains were none. The X-MAS arm applied the repaired policy on `21/50` rows.
- `epyc-inference-research` `7d05d03` adds this constrained-policy A/B to
  `docs/data/clean_window_measurement_manifest.json` and
  `docs/data/clean_window_measurement_commands.sh` as package `X-MAS`; the
  completed 2026-07-03 repaired-policy run is the current evidence for that
  lane.
- `epyc-orchestrator` `d4a6c927` accepts that evidence by switching
  `orchestration/classifier_config.yaml` to `xmas_routing.mode: enforce` with
  the same complete function-axis table and `confidence_threshold: 0.55`. The
  orchestrator API was reloaded as PID `2679680`; `fable5_gate_report.py
  --strict` then reported `xmas_production_path` ready with `mode=enforce`, no
  X-MAS blockers, and latest A/B `promote_candidate`. AutoPilot was restarted
  after the cutover at trial `1109` so subsequent evidence accrues post-enable;
  trial `1108` is intentionally journaled as an interrupted placeholder.

#### Current Gate

- [x] Enable production enforce only after accepting the repaired-policy evidence and recording reload/attestation. Done in `epyc-orchestrator` `d4a6c927`; current config is `mode: enforce`, table validation passes, and post-reload Fable5 reports the X-MAS section ready.
- [x] Run the repaired constrained-policy quiet-window A/B after deploying/reloading the current code/config. The current real-run artifact carries `xmas_policy=incumbent_constrained_cheapfirst_v2`, `required_xmas_policy=incumbent_constrained_cheapfirst_v2`, row-level routing metadata, and `decision.status=promote_candidate`.
- **[declined: ws58 2026-11-03 content-review: unbounded watch with no trigger; the rollback is documented in the track]** Monitor post-enable live telemetry for unexpected domain regressions, latency regressions, or guard bypasses; rollback is `xmas_routing.mode: off` plus orchestrator API reload.

#### Validation Commands

```bash
cd /mnt/raid0/llm/epyc-orchestrator
uv run pytest -q tests/unit/test_xmas_live_ab.py tests/unit/test_validate_xmas_winner_table.py tests/classifiers/test_xmas_routing.py tests/unit/test_pipeline_routing.py
uv run python scripts/validate/validate_xmas_winner_table.py --table orchestration/xmas_winner_table.yaml --require-function-axis
uv run python scripts/autopilot/fable5_gate_report.py --strict
uv run python scripts/benchmark/xmas_live_ab.py --prompts benchmarks/results/runs/xmas_live_ab/20260618-heldout-resilient/prompts.jsonl --reps 2 --host-quiet-confirmed --output benchmarks/results/runs/xmas_live_ab/$(date -u +%Y%m%dT%H%M%SZ)-constrained-policy
uv run python scripts/benchmark/xmas_live_ab.py --summarize-results benchmarks/results/runs/xmas_live_ab/20260618-215637-heldout-resilient-rerun/results.jsonl --output /tmp/xmas-replay-diagnostics
```

#### Non-Goals

- Hidden-state or latent-agent handoff work.
- Cross-tokenizer projection or Dead Weights reproduction.
- Hidden-state follow-up before the text-mediated route has post-enable telemetry.

#### References

- Deep-dive: `/workspace/research/deep-dives/2026-05-19-latent-mas-cluster.md`
- X-MAS paper: `https://arxiv.org/abs/2505.16997`
- X-MAS repo: `https://github.com/MASWorks/X-MAS` (no license — methodology only)
- Related handoffs: `routing-intelligence.md`, `routing-and-optimization-index.md`, `learned-routing-controller.md`, `hermes-outer-shell.md`, `../completed/meta-harness-optimization.md`

## Track: routing-intelligence
<!-- gate: UFH-01 -->

> Folded from `handoffs/active/routing-intelligence.md` @ `1befe3bc860d` on 2026-11-03 (BRF-T7-F16, route 1b, operator D1/D5; retired row RTG-30 → RTG-09). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Routing Intelligence: Factual-Risk Rollout

**Status**: ACTIVE. Live work is the routing audit RI-16..RI-20 (filed 2026-09-26). The factual-risk rollout (RI-10..RI-12) holds on `hold_quality_scored_no_lift` (packet 2026-07-06; § Start Here).
**Priority**: HIGH for RI-10 decision; MEDIUM for injection-risk fork after J14.
**Blocked by**: future scored factuality evidence showing enforce-arm lift, or an explicit operator-approved lower-evidence rollout decision.
**Completed ledger**: [`../completed/routing-intelligence-completed-through-2026-05-28.md`](../completed/routing-intelligence-completed-through-2026-05-28.md)
**Updated**: 2026-10-03 (RI-18 scored 2026-10-01: DROP; RI-18c filed to apply it; RI-18a/b declined. 2026-10-01: RI-16 closed, RI-24 filed)

#### Start Here

**Current priority (2026-10-03):** RI-18c, apply RI-18's pre-registered **DROP**: remove the review gate, verdict and
revision from all five call sites plus `review_low_q_threshold`. RI-18 was scored 2026-10-01: reviewing every answer
costs a net −38.3 per 100 items, and the production gate never fires. RI-16 is closed (routing costs ~0.6 s p50 / ~1.2 s
p95 before generation); RI-19, RI-24 and RI-18c cut it. The numbered steps below concern the older RI-10 factual-risk canary.

Do not implement the old Phase 4/5 sections from the completed ledger. They were superseded by RI-1 through RI-8 landing in March/April 2026. The next implementer should:

1. Pull current RI-10 canary data from logs before deciding anything; elapsed calendar time is not sufficient.
2. Confirm the current decision-ready sample still has enough arm-attributed rows in both enforce and shadow.
3. Use `scripts/analysis/ri10_canary_decision_report.py --scored-summary ...` to compare operational proxies with the attached scored factuality evidence. Current packet: `orchestration/reports/ri10_canary_decision_report_20260706T065654Z.{json,md}`.
4. Keep RI-11 frozen unless a future scored packet shows enforce-arm factuality lift, or the operator explicitly accepts a lower-evidence rollout decision.

Current 2026-07-06 refresh: live Fable/DS-E1 reads report `ri10_telemetry_collection_blocker=decision_ready`, and the scored canary response report is attached to the rollout decision packet. `epyc-orchestrator` `adf010b4` extends `ri10_canary_decision_report.py` with `--scored-summary`, generates `orchestration/reports/ri10_canary_decision_report_20260706T065654Z.{json,md}`, and records status `hold_quality_scored_no_lift`. The scored packet `ri10_canary_scored_summary_20260705T185001Z` is complete (`60/60` scored, no missing responses), but exact accuracy is tied (`3/30` enforce vs `3/30` shadow). The earlier 2026-07-04 reports (`ri10_canary_sample_report_20260704T095500Z.json`, `ri10_canary_sample_report_all_roles_20260704T005332Z.json`) and the 2026-07-05 `hold_quality_unscored` packet remain historical diagnostics only.

#### Live Tasks

- [ ] **RI-10 — Shadow-to-enforce canary decision**: current canary is configured as 25% enforce / 75% shadow on `frontdoor`, `worker_general`, and `worker_vision`, and `7647b32e` exposes the chosen arm in routing progress metadata. The 2026-07-04 deterministic sampler fix makes future arm assignment stable per task id instead of process-RNG sampled, and the 2026-07-06 refresh shows telemetry depth and scored-response completeness are ready. Decision packet `20260706T065654Z` holds on `factuality_no_enforce_lift`; do not expand to RI-11 from favorable operational proxies alone. Decision requires: Absorbs the retrain-routing "--keep-enabled bracket" decision, RI-9b, RI-11 and RI-12: on a pass, expand to frontdoor 100% + worker_general for 7 days with a rollback flag to shadow, then global enforce (dashboards/alerts and q-scorer baseline dependencies updated); a fresh threshold/Pareto sweep only if this canary suggests changing bands.
  - 2026-11-09 audit: STALE-PREMISE. The decision packet `20260706T065654Z` is four months old and the lineup changed twice since (`classifier_config.yaml:238-245` canary roles frontdoor/worker_general/worker_vision, mode canary 25%). Re-run the packet on post-07-23 traffic first (zero inference, doable now), then decide. Overlaps URE-1 and RI-15 (three signals feeding one canary decision, no shared acceptance): the packet should state one acceptance for all three.
  - 2026-11-09 EG2 boundary (RTG-EG2-1): the canary's retrieval/classifier inputs and the 0.8/0.5 classifier/verifier thresholds were tuned on BGE cosines. Regenerate: verifier head weights (05-21), the factual-risk/verifier thresholds (REPL-EMB-R5). Run the decision packet on post-07-23 traffic first (zero inference); if enforce is chosen before v11, the enforce decision must be re-confirmed after the re-embed.
  - controlled restart/window with `MEMRL_RETRIEVAL_RISK_CONTROL_ENABLED=true`; `ORCHESTRATOR_FACTUAL_RISK_MODE` is not the canary switch because it only accepts `off|shadow|enforce`;
  - >=50 arm-attributed high-risk samples or a documented reason to use a lower-powered decision; current refresh satisfies the depth gate with `31` enforce and `50` shadow high-risk rows;
  - no p95 latency regression >10%;
  - no cost regression >5% at equal factuality;
  - no unexplained escalation/review inflation >20%;
  - no 5xx/error cluster attributable to factual-risk scoring.
  - scored factuality/accuracy showing enforce-arm lift, or an explicit operator-approved lower-evidence decision. Current scored packet: `ri10_canary_scored_summary_20260705T185001Z` (`accuracy_delta=0.0`, token-F1 delta `+0.000531`).
- **[declined: ws58 2026-11-03 content-review: merged into RI-10 as stage 2]** **RI-11 — Enforce expand**: if RI-10 passes, expand to frontdoor 100% plus worker_general for 7 days. Keep a rollback flag path to shadow.
- **[declined: ws58 2026-11-03 content-review: merged into RI-10 as stage 3]** **RI-12 — Global enforce**: only after RI-11 passes; update dashboards/alerts and q-scorer baseline dependencies.
- **[declined: ws58 2026-11-03 content-review: merged into RI-10 as its conditional sweep]** **RI-9b — Threshold/Pareto sweep if thresholds change**: Package B already produced risk-distribution profiling. Run a fresh threshold sweep only if RI-10 suggests changing bands or enforcement thresholds.
- **[declined: ws58 2026-11-03 content-review: merged into DAR-6.5 (the gate it waits on)]** **RI-13 — Injection-risk classifier fork (DAR-6/J14)**: do not build until the cheap-first unconditional J14 swarm-fanout A/B clears its gate. If it clears, add an injection-risk axis to this handoff rather than burying it in DAR.
- **[declined: ws58 2026-11-03 content-review: merged into P5.2 as its conditional rollout]** **RI-X — New-model onboarding contract**: if learned-routing-controller P5.2 passes, document cold-start workflow here and link the `tools/onboard_specialist.py` wrapper from that handoff.

- [x] **RI-16 — PRIORITY: measure end-to-end routing-decision latency on live `/chat`.** ✅ 2026-10-01 (filed 2026-09-26, code+live-process audit) A routed request makes ~3-4 embed+KNN lookups — role priors (`chat_routing.py:316-343` `_heuristic_role_priors` → `ClassificationRetriever`), route (`chat_pipeline/routing_decision.py:314` → `hybrid_router.py:388`), mode (`chat_routing.py:182` → `route_with_mode`), and the post-answer review gate (`chat_review.py:57-96`) — and none is timed; the "<1 ms MLP / 10-50 ms KNN" figures in docs are claims. Add per-stage timers to routing telemetry, report p50/p95 per stage and total, and set them beside typed routing (590 ms native single-token / ~2.5 s JSON, `typed-decision-plane.md`). Wire the telemetry into the belief kernel (`vidya-belief-substrate-program.md` VB-ROUTE-LAT).
  - 2026-09-29: the operator directs RI-16, then RI-18, as workspace-8d's next work, right after that day's wrap-up.
    Next step: add per-stage timers (role priors, route, mode, review gate, and the total) to the routing telemetry,
    with unit tests (zero inference). Then land them, do an API-only reload, and read p50/p95 per stage from live
    `/chat` requests.
  - 2026-09-30: landed as orch `78847544` (per-stage timers `memrl_init`, `priors`, `route`, `xmas`, `factual_risk`,
    `failure_veto`, `difficulty`, `trinity`, `route_total`, `mode`, `routing_context`, `review_gate`,
    `review_verdict`, `total`; a stage that did not run is `None`, never 0). `routing_path` + `stage_ms` ride the
    progress JSONL `routing_decision` and `task_completed`/`task_failed` events; reader
    `scripts/analysis/routing_stage_latency.py`. Deployed to the API 2026-09-30 04:52Z (master PID 1930724) by the
    NIB2-91 planned restart (`non-inference-backlog.md`). The box stays open: it ticks when p50/p95 per stage are read
    from live `/chat`. Belief-kernel adapter: `vidya-belief-substrate-program.md` VB-ROUTE-LAT.
  - ✅ 2026-10-01 — read from live `/chat`. 30 requests from ~03:06Z (request set `/mnt/raid0/llm/tmp/ri16/ri16_load.py`,
    results `/mnt/raid0/llm/tmp/ri16/load-20260930/results.jsonl`) against orch `78847544` (deployed 2026-09-30 04:52Z).
    Reader: `python3 scripts/analysis/routing_stage_latency.py --since 2026-10-01T03:00:00Z --path all` (orchestrator).
    n=30, all on the chat path:

    | stage | p50 ms | p95 ms |
    |---|---|---|
    | priors | 156 | 275 |
    | route | 197 | 529 |
    | xmas | 26 | 96 |
    | factual_risk | 0.06 | 85 |
    | route_total | 542 | 1027 |
    | mode | 58 | 69 |
    | review_gate | 69 | 105 |
    | total | 622 | 1159 |

    `memrl_init`, `failure_veto`, `difficulty` and `trinity` are each under 2 ms at p95.
    - Routing costs ~0.6 s at p50 and ~1.2 s at p95 before generation starts. That is the same order as typed
      routing's 590 ms native single-token median. The docs' "<1 ms MLP / 10-50 ms KNN" figures do not describe the
      request path.
    - Priors plus route (embedding + KNN) are 353 ms of the 542 ms `route_total` p50. `priors` is
      `_classify_and_route` + `_should_use_direct` (`chat_routing.py:318-343`), which is the MemRL
      `ClassificationRetriever` path that RI-19 shows has 0 memories to retrieve. RI-19 is therefore worth ~156 ms p50
      / ~275 ms p95 per request, not hygiene only.
    - Caveats: n=30 from one session; the GPU was busy with workspace-76's 27B harness replays; the CPU was quiet
      under the announced DS41 pause, but production frontdoor shares cores 0-95.
    - Belief kernel: the VB-ROUTE-LAT write side now holds these 30 records; the adapter is still owed.
- [ ] **RI-17 — compare live `/chat` routing against rules-only routing** on the same frozen workload (quality, cost, latency per request), so the KNN/memory layer has to earn its lookups. Reuse the counterfactual harness from `typed-decision-plane.md` TD-10 where it fits. (filed 2026-09-26)
  - 2026-11-09 audit: SV. Frozen-workload inference run; no kernel/binary is named: state it (v10 kernel store) and prove linkage. See the EG2 note: run on both sides of the re-embed.
  - 2026-11-09 EG2 boundary (RTG-EG2-1): the KNN/memory layer's neighbours change at the re-embed, so run this on both sides: once on the BGE store (before) and once on the EG2@256 store (after), or define the workload so it can be replayed. Regenerate: nothing; the comparison itself is the deliverable.
- [x] **RI-18 — evaluate the `_should_review` Q gate** (`chat_review.py:57-96`: KNN over the ANSWER text, `avg_q < review_low_q_threshold` → architect review; callers `repl_executor.py:782`, `direct_stage.py:227`, `stream_adapter.py:346`, `chat.py:1604`): measure trigger rate, review cost, and whether reviewed answers improve; keep, retune or remove. (filed 2026-09-26) ✅ 2026-10-01 — **DROP** (pre-registered clause 1); verdict block at the end of this task, applied by RI-18c.
  - 2026-09-28: the "do reviewed answers improve" half waits on RI-22. Until RI-22 lands, the gate has not produced a
    usable verdict on the 27B, so a measurement now would count triggers and zero revisions.
  - 2026-09-29: unblocked. RI-22 is fixed in production (below), so the gate now returns real `OK`/`WRONG` verdicts on
    the 27B and an unparseable verdict is counted as `unavailable`. The "do reviewed answers improve" half can run.
  - 2026-09-29: the operator directs it next, after RI-16. Next step: read the trigger rate and review cost from the
    RI-22 verdict telemetry on live `/chat` (zero new code if RI-16's timers cover the gate), then run the
    "do reviewed answers improve" comparison.
  - 2026-09-30: live traffic cannot answer RI-18 (0 `POST /chat` from the RI-23 reload to ~00:30Z; 0 answer-review prompts and
    0 `v1_escalation` receipts in the whole tap window 2026-08-24 → 2026-09-29). Design: a forced-review
    counterfactual with exact policy evaluation, `/mnt/raid0/llm/tmp/ri18/DESIGN.md`. Instrument:
    `epyc-inference-research/scripts/benchmark/ri18_review_gate/` (research main
    `6b2366e2`). Orchestrator changes landed on orch main as `08edc054` (2026-09-30; NOT yet deployed — C1 goes
    live at the API-only reload the owning session times; the driver's in-process calls use `--code-root` at `08edc054`):
    - **C1** persistent `review_gate` tap event (`inference_tap.emit_request_event("review_gate", ...)`) for every gate
      evaluation on all five call sites; the three `_architect_verdict` callers switch to
      `_architect_verdict_with_status`.
    - **C2** `review_gate_score(state, role, answer, *, key_text=None) -> GateScore` accessor. `_should_review` is left
      untouched (gitnexus HIGH); the five call sites decide through the accessor (one KNN, timed into RI-16's
      `review_gate` stage), and a fixture-grid test pins `_should_review(...) == review_gate_score(...).triggered`,
      KNN key included.
    - **C3** `question_cap` (and `answer_cap`) on `build_review_verdict_prompt`, defaults 300/1500, so the production
      prompt is unchanged.
    - Belief-kernel wiring: `vidya-belief-substrate-program.md` VB-REVIEW-GATE (C1 events) and VB-RI18 (the
      `belief_measurements.jsonl` sidecar).
  - 2026-09-30 structural findings. These are **observations** (design §1: read-only code and data, no protocol);
    they gate nothing.
    - (a) **Answers under 50 chars skip the gate**, so it is inert on letter-only prompts. The UFH-13 frozen suite and
      pilot pool both end "Answer with the letter only"; on the A4 proxy (same base model) the median answer is 1 char
      and 58-77% are under 50 chars. So A2's review-gate trigger is structurally inert on the frozen letter-only suite
      (routed to `thesis-experiment-orchestrator-vs-strongest-model.md` TE-reopen).
    - (b) **The KNN never sees Q < 0.3 failures** (`min_q_value=0.3`): 5,484 of 33,293 frontdoor routing memories
      (16.5%) are invisible to it, and of the 27,809 retrievable ones only 8.4% have Q < 0.6. The reachable trigger
      rate is low by construction.
    - (c) **The verdict prompt truncates the question to 300 chars** (and the answer to 1,500). 86% of pilot-pool
      prompts exceed 300 chars, so the reviewer usually never sees the MC options.
  - **PRE-REGISTERED 2026-09-30, operator-approved in chat (Q1-Q3 as recommended).** Frozen 2026-09-30; changes are
    new registrations, never edits. Source: `/mnt/raid0/llm/tmp/ri18/DESIGN.md` §5 (operator questions §6).
    - **Question:** does the post-answer review (27B verdict → `worker_general` revision) improve frontdoor answers,
      and does the MemRL Q gate (`avg_q < 0.6` over an answer-keyed KNN) select the answers where it helps?
    - **Instrument:** `ri18_review_gate` driver at the served orch commit (pinned). Workload (Q2): S1 = the UFH-13
      pilot pool re-rendered, 453 items, render `ri18-brief-justify-v1` (the letter-only last line replaced by
      "Justify briefly (at most three sentences), then end with a final line `Answer: <letter>`"; sha pinned); S2 =
      `olympiadbench_hard`, 155 items (sha pinned). Not letter-only, and no LLM judge. Frozen 395 excluded (asserted).
      Production functions `_architect_verdict_with_status` / `_fast_revise` forced on every item. Gate computed
      offline against a sha-pinned store snapshot with the production retrieval config. Scorers:
      `extract_letter_answer` (S1), `math_symbolic` (S2). One sample per call. instrument_class = `serving`
      (production recipe, production functions); category OPTIMUM (production reviewer config).
    - **n:** 608 items (primary population = items with a scored original answer and the quality detector not fired;
      expected ≈ 560-600). Split: seeded (`seed=18`) 50/50 **tune (A) / confirm (B)**, stratified by suite.
    - **Primary metrics:** net(π) = fixed − broken per 100 items for π1 (review all eligible) and πQ(0.6)
      (production); AUROC of −avg_q for frontdoor-wrong; device-seconds per net fix (GPU and CPU separately).
    - **Power:** a paired test detects |net| ≥ 2.8·√D items at 80% power (D = discordant items). With D ≈ 40-120 on
      the full set, that is roughly 3-5 per 100 items; on split B alone, roughly 6-7 per 100 items. Effects below
      those are not excluded, and the verdict says so.
    - **Cost cap X (Q1):** at most 60 GPU device-seconds and at most 120 CPU device-seconds per net fix, and at most
      +20% added p50 latency on reviewed requests.
    - **Decision rule** (applied in order; each clause cites its CI):
      0. **VOID** if the canary pair fails in either direction, the `unavailable` rate exceeds 5%, the gate controls
         fail, or the served commit or store sha drifts. Fix, re-run; no decision.
      1. **DROP**: remove the gate, verdict and revision from all five call sites plus the `review_low_q_threshold`
         config. Applies if net(π1) has a 95% CI upper bound < 0, **or** if no policy in {π1, πQ(t*)} (t* tuned on A
         over t ∈ {0.30..1.00 step 0.05}, maximising net subject to review rate ≤ 50%) has a split-B net 95% CI lower
         bound > 0.
      2. **KEEP at 0.6** if πQ(0.6)'s net CI lower bound (full set) > 0, AUROC CI lower bound > 0.5, and neither
         πQ(t*) nor π1 beats it on split B by ≥ 2 net fixes per 100 items at a cost of at most 60 GPU device-seconds
         and at most 120 CPU device-seconds per net fix, with at most +20% added p50 latency on reviewed requests.
      3. **RETUNE to t*** if πQ(t*) has a split-B net CI lower bound > 0, AUROC CI lower bound > 0.5, and it beats
         πQ(0.6) on B by ≥ 2 per 100 at a cost of at most 60 GPU device-seconds and at most 120 CPU device-seconds
         per net fix, with at most +20% added p50 latency on reviewed requests.
      4. **REPLACE THE TRIGGER** (Q is uninformative): if the AUROC CI contains 0.5, π1's net CI lower bound > 0, and
         π1's cost per net fix is at most 60 GPU device-seconds and at most 120 CPU device-seconds, with at most +20%
         added p50 latency on reviewed requests. The Q gate goes, and review-all or a new trigger (e.g. the quality
         detector, or RI-9 factual risk; exploratory `avg_q_question` reported) goes to a decision package.
      5. If eligible gate@0.6 triggers number < 30, πQ(0.6)'s own net is reported **untested** (BOUNDED-NULL-1), and
         clauses 2 and 3 fall back to AUROC plus π1.
    - **Secondary (own rule; Q3 latitude granted):** V-full vs the production cap. If V-full's verdict sensitivity at
      equal or better specificity beats the cap-300 verdict on split B with a paired CI lower bound > 0, land
      `question_cap=1500` (C3) as the production reviewer prompt without a separate A/B (operator Q3, 2026-09-30:
      the reviewer verdict question cap 300 → 1500 may land under this rule), then re-run stages 3-4 on the banked
      answers only (replay, no frontdoor inference) before re-applying the rule.
    - **Reported regardless:** coverage by skip reason, precision/recall at every t (eligible and population),
      reviewer sensitivity/specificity/unavailable rate, revision fix/break/no-op rates, infra rate by reason, verdict
      and revision noise, per-stratum tables, and the external-validity caveat (closed-form tasks, not open chat).
    - **Stopping rule:** the split-B table is FINAL. No confirmation re-runs unless the result would change the
      decision.
  - 2026-09-30 **run plan** (instrument built and landed, no inference run yet). From the research repo root:
    `PY=/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python; M="-m scripts.benchmark.ri18_review_gate.run_ri18"`;
    real: `$PY $M <segment> [args] --out /mnt/raid0/llm/tmp/ri18/run-v1 --run-id ri18-v1 --code-root <orch checkout at
    08edc054 or later>`; dry-run: the same with `--dry-run --out /mnt/raid0/llm/tmp/ri18/dev/dry --run-id dry`. Every
    segment is resumable per item and fsyncs per record. rc 3 = window refused/closed mid-segment (resume next
    window), 5 = VOID, 6 = instrument fault, 7 = all `:8083` slots busy, 9 = manifest drift.
    - `snapshot --source-root /mnt/raid0/llm/epyc-orchestrator` — right before the first `answer`; no inference.
    - `answer --suite s1` (453) and `answer --suite s2` (155) — CPU window (`open`, `loop_holds_claim=false`, item +
      120 s before `est_close_at`, re-checked per item); ~35-50 and ~30-50 min.
    - `verdict` (incl. V-full on S1) and `noise-verdict` — GPU `:8083`, one slot, no CPU window; ~18-27 and ~1-2 min.
    - `revise`, then `noise-revise` — CPU window; ~25-45 and ~3-7 min. The per-call frontdoor region claim is taken by
      `llm_call` itself (the segment sets the per-region-lock flags and asserts `:8070` → frontdoor instance 0).
    - `gate` — CPU embedders, CPU window, against the snapshot; < 3 min. `score` — offline, seconds.
    - Rule readings the driver encodes (confirm before the first `score`): clause 5 → clause 2 uses π1's full-set CI
      lower bound > 0 in place of πQ(0.6)'s; clause 3 adds "π1 full-set lower bound > 0"; "beats by ≥ 2 per 100" is
      the point estimate (paired CI cited); the latency cap is median added latency on reviewed requests ≤ 0.20 ×
      the median frontdoor wall time on those same requests.
      - ✅ CONFIRMED by the operator in chat on 2026-09-30 ("Confirm all four"), before any item ran: these four
        readings are part of the pre-registration. `score` may run once the segments complete.
  - 2026-10-01 run status (read-only, `/mnt/raid0/llm/tmp/ri18/run-v1/segments.jsonl`), first pass under the announced
    DS41 pause. The `answer` segment hit its 5400 s wall budget at 366 of 453 S1 items. `verdict` also hit its budget, at
    358 items; `noise-verdict` completed (32). `revise` has been running on CPU since 05:51Z (item 191 of 274 at ~06:12Z).
    Next step: the resume pass (`/mnt/raid0/llm/tmp/sequencer-8d/run_ri18_resume_pause.sh`, per-item resume, no
    re-snapshot) covers the remaining 87 S1 items and S2 (155), then verdict, revise, noise-revise and `gate`; then
    `score`.
  - 2026-10-01 status (NOT complete): all 608 answers are in, and `verdict`, `noise-verdict`, `noise-revise` (pinned)
    and `gate` are done.
    - The gate never fired on the 579 scored items. avg_q ≈ 1.0, far above the 0.6 threshold, which matches
      structural finding (b): the KNN cannot see Q < 0.3 failures.
    - The 90 final revisions were VOIDED by the driver (`segments.jsonl` 12:59:07Z, segment
      `revise-20261001T121657Z-2fbb99`: "code_root commit drifted during the segment"). workspace-8d had
      fast-forwarded the shared orchestrator clone at 12:22Z to deploy UFH-12 (REPL-EMB-4.4). The integrity check
      worked as designed; see `INC-20261001-shared-clone-drift-voided-ri18-revise`.
    - The redo runs with `--code-root` pinned to the detached worktree
      `/mnt/raid0/llm/worktrees/orch-ri18-pin-08edc054` (the run's commit, `08edc054`), in normal DS41 windows.
      `score` runs automatically after it.
    - A `score` attempt before the redo returned VOID (clause 0: incomplete, revise missing 90). INTERIM only, not a
      verdict: AUROC of Q against wrong answers 0.56 [0.51, 0.62]; π1 net per 100 −36.8 [−41.5, −32.3].
    - Next step: let the pinned redo finish, then read `score`.
  - ✅ **2026-10-01 18:53Z — VERDICT: DROP (clause 1 fired).** The pinned revise redo (orch `08edc054`, worktree
    `/mnt/raid0/llm/worktrees/orch-ri18-pin-08edc054`) finished 90/90 in workspace-76's granted gap: segment
    `revise-20261001T181047Z-1960bd`, end `exit 0`. `score` ran automatically afterwards.
    - Evidence: `/mnt/raid0/llm/tmp/ri18/run-v1/score.json` (schema `ri18-review-gate-score/v1`, `records_sha256`
      `134d7ed3…c282f8`, `items_sha256` `af3033f0…b66a`), log `/mnt/raid0/llm/tmp/ri18/score-final.log`, belief sidecar
      `/mnt/raid0/llm/tmp/ri18/run-v1/belief_measurements.jsonl` (6 rows), manifest `run_manifest.json` (served
      `08edc054`, research `5f09e028`, reviewer `architect_critic`, store snapshot sha-pinned).
    - Population: 608 items; 29 answers returned an HTTP error, so `n_primary` = 579 (S1 447, S2 132; split A 289,
      B 290). Quality detector fired 0; verdict `unavailable` 0; revision failures 0; verdict and revision noise
      both 1.0 agreement (n 32 and 30).
    - **Clause 0 (VOID): did not fire.** The earlier void segment (`revise-20261001T121657Z-2fbb99`, code-root drift)
      is superseded by the pinned redo.
    - **Clause 1 (DROP): FIRED on its first limb.** π1 (review every eligible answer) has a full-set net of
      **−38.3 per 100 items, 95% CI [−42.7, −34.0]** (paired bootstrap, 10,000 resamples, stratified by suite):
      12 fixed, 234 broken, accuracy 72.2% → 33.9%. The upper bound is below 0. The second limb holds too: no
      policy in {π1, πQ(t*)} has a split-B lower bound above 0 (π1 B [−44.8, −32.4]; πQ(t*) B [0, 0]).
    - **t\* = 0.30.** Tuned on A, no threshold from 0.30 to 0.90 reviews anything; 0.95 reviews 1 item (net 0) and
      1.00 reviews 83 (net −32). So t* is the lowest feasible tie at net 0.
    - **Clause 5 (BOUNDED-NULL-1) applies: 0 eligible gate@0.6 triggers (< 30).** The production policy πQ(0.6) has a
      net of exactly 0 [0, 0] because it never fires, so its own net is reported **untested**. Clauses 2 and 3 fall
      back to AUROC plus π1, and π1 is net-harmful, so neither can fire.
    - **AUROC of −avg_q for frontdoor-wrong: 0.558 [0.511, 0.607].** Q carries a weak signal, but the gate cannot
      act on it: avg_q ≈ 1.0 on nearly every item, so nothing falls under any threshold below 0.95.
    - **Clause 4 (REPLACE THE TRIGGER) cannot fire.** It needs π1's lower bound above 0.
    - **Mechanism:** the cap-300 reviewer says WRONG too often. Sensitivity is 0.94 / 0.91 (A / B), but specificity
      is only 0.21 / 0.25. `worker_general`'s revision then breaks most of the correct answers it rewrites (break rate
      0.70 / 0.75) and fixes few wrong ones (fix rate 0.065 / 0.097). Reviewing every answer also adds 9.8 s of p50
      latency (p95 52 s), 1.7× the frontdoor answer wall, and costs 6,545 CPU-s plus 3,488 GPU-s over 579 items with
      no net fix, so it fails cost cap X as well.
    - **Secondary rule (V-full vs the cap-300 prompt): HOLD_CAP_300.** On B, the sensitivity delta is −0.016
      [−0.098, 0.067], so the lower bound is not above 0. Specificity improves (0.55 vs 0.29), but that is not the
      rule. `question_cap=1500` does not land.
    - **Power:** D = 246 discordant items, so the test resolves |net| down to ~7.6 per 100. The observed effect is
      five times that.
    - **Caveat (pre-registered, reported regardless):** both strata are closed-form scored tasks (MC with a brief
      justification; olympiad math), not open chat.
    - **What DROP means for production.** The gate as configured (`review_low_q_threshold` 0.6, reviewer
      `architect_critic`) is inert: on this workload it never fires. When review does run, revision is net-harmful.
      So production loses nothing by the removal, and every request saves the `review_gate` KNN stage (RI-16: 69 ms
      p50 / 105 ms p95). The pre-registered action is RI-18c below. Under the stopping rule there is no
      confirmation re-run.
    - Belief kernel: the write side is the sidecar above (`scripts/vidya/adapters/README.md` row "RI-18 review-gate
      counterfactual"). The read side is `vidya-belief-substrate-program.md` VB-RI18; the sidecar gaps against its
      contract are filed there as VB-RI18a.
  - [ ] **RI-18c — apply the DROP (clause 1's pre-registered action).** (filed 2026-10-03, from the RI-18 verdict)
    - [x] **RI-18c-CODE — gate, verdict, revision and `review_low_q_threshold` removed.** ✅ 2026-11-09 (verified: `88d885c6` is an ancestor of orchestrator origin/main; `review_low_q_threshold` appears only in a removal comment at `src/config/models.py:1317` and a docstring in `src/api/routes/chat_review.py:11`; deployed 2026-10-03) [no-belief: code removal verified by ancestry and source inspection]
    - 2026-11-09 audit: remaining part of RI-18c is only the live reading: one COMPLETED `/chat` with `review_gate`/`review_verdict` null, read with the RI-16 reader. The :8083 restore it once waited on is long past; the reading needs a running stack (compute list), so the box stays open until the relaunch.
    - **BUILT 2026-10-03, NOT DEPLOYED** (workspace-ec): orch 88d885c6 (gate, verdict and revision removed at all five
      call sites; `chat_review` verdict/revise helpers, C1-C3, the review/revision prompt builders and files, and
      `review_low_q_threshold` with its env/autopilot/swarm surfaces removed; plan review kept; RI-16 `stage_ms` keys kept,
      now always null) + 8e379f13 (docs). Integrated on orch `integ/api-reload-2-ec` 10bc5681. Not ticked: the done-when
      needs the live `/chat` reading, which follows UFH14-DEPLOY-EC (`agentic-serving-harness-fixes.md`).
    - **DEPLOYED 2026-10-03 ~14:50Z, pending live verification** (workspace-ec): merged to orch main (10bc5681, now
      aa1d6894) and deployed by an API-only reload (PID 1628390). Of the done-when, the code removal is live, and
      the suite is green: full `tests/unit` 15979 passed, 0 failed (`/mnt/raid0/llm/tmp/integ2-ec/full_unit3.log`).
      The live `/chat` RI-16 reading (`review_gate` / `review_verdict` null) is still open. It waits for the :8083
      restore (KVU-16e in `kv-unified-stack-rollout.md`; X0 hand-back ~17:15Z), tracked as UFH14-DEPLOY-EC-2. Not
      ticked until that reading exists.
    - **2026-10-03 ~15:40Z, after the :8083 restore: suggestive, NOT proof** (workspace-ec). A live `/chat` showed
      `routing_stage_ms.review_gate` and `review_verdict` both null, but the call failed with "placement timeout
      role=frontdoor": DS41 holds the CPU regions. The gate, when present, ran only after an answer existed, so a null on a call that
      never produced an answer cannot show it was removed. Still open: one COMPLETED `/chat` in a DS41 open window
      (`cpu-window.json`), read with the RI-16 reader. Not ticked.
    - Remove the gate, the verdict and the revision from all five call sites: `repl_executor.py` ~779-826,
      `direct_stage.py` ~223-242, `stream_adapter.py` ~346-360, `chat.py` ~1613-1628 and `v1_escalation.py` ~405-466.
      Also remove the `review_low_q_threshold` config.
    - C1-C3 (orch `08edc054`) go with it. Each one instruments or parameterises code that DROP deletes: C1 is the
      `review_gate` tap event, C2 is `review_gate_score`, C3 is the `question_cap`/`answer_cap` parameters. Keeping C1
      telemetry is **declined**: with no gate there is no evaluation to record. Its adapter VB-REVIEW-GATE is
      declined with it.
    - Before editing, run `gitnexus impact _should_review --direction upstream`. The 2026-09-30 build rated it HIGH.
      Delete the dead tests with the code. Land on orch main; the owning session times the API-only reload.
    - Done when: the five sites no longer call the verdict or revision; the RI-16 reader shows `review_gate` and
      `review_verdict` as `null` on live `/chat`; and the targeted suite is green.
    - Cross-handoff: removing the `v1_escalation` site removes one of the thesis experiment's two A2 escalation
      triggers. UFH-13 is parked, and TE-reopen's escalation-design review takes this in
      (`thesis-experiment-orchestrator-vs-strongest-model.md` TE-reopen, 2026-10-03 note).
  - [x] **RI-18a — the driver's `--retriever` default must mirror production's resolution.** The default is `graph`.
    Production falls back to `TwoPhaseRetriever` when the kuzu graph backend is unavailable
    (`src/api/services/memrl.py` ~488-520, "failure/hypothesis graph scoring inactive, using TwoPhaseRetriever").
    This run's `gate` used `--retriever two_phase` explicitly. Fix: resolve the default the way `memrl.py` does,
    and record the resolved retriever in the segment header. (filed 2026-10-01)
    - **DECLINED 2026-10-03** ✅ 2026-10-03. Still unfixed in the driver (research `5f09e028` defaults to `graph`). The
      scored run passed `--retriever two_phase` explicitly, so the verdict is unaffected. DROP retires what the driver
      measures, and the stopping rule forbids a re-run, so the driver has no next run. Trigger: any reuse of
      `ri18_review_gate` under a new registration fixes this first.
  - [x] **RI-18b — the wrapper scripts must read segment `end` and `void` events, not trust the process rc.** The
    VOIDED `revise` segment logged `void`, then an `end` with `exit: 5` but `reason: complete`, and the chain
    started `noise-revise` 23 s later. The `sequencer-8d` wrappers (`run_ri18_resume_pause.sh`,
    `run_ri18_revise_redo.sh`) must not rely on the process rc alone. Fix: after each segment, read its last `end` event
    from `segments.jsonl`; stop the chain on a `void` event or a non-zero `exit`. (filed 2026-10-01)
    - ✅ 2026-10-01 for the wrapper that still ran: `run_ri18_revise_redo.sh` reads the last `revise-` segment's
      `void`/`end` event and stops on a void or a non-zero `exit`. It produced the final 90 revisions. The
      `run_ri18_resume_pause.sh` half is **DECLINED** (✅ 2026-10-03): that wrapper is retired with the run. The
      root cause, that the driver's process rc can disagree with the segment's own `end` event, stays in the driver.
      It is fixed under the same trigger as RI-18a.
- [ ] **RI-19 — fix or remove the MemRL `ClassificationRetriever` path.** [too-big: owner must run the required matched 30-request comparison before deleting the branch] The store holds 0 `classification` memories, so `classify_and_route`/`should_use_direct_mode` (`keyword_matcher.py:294,:373`, enabled by `classifier_config.yaml:110,113`) always fall back to keywords while still paying a retrieval. Either seed/write classification memories and show they beat keywords, or set `use_memrl: false` and delete the dead branch. (filed 2026-09-26)
  - 2026-11-09 audit: SV. The matched 30-request comparison needs inference. See the EG2 note on thresholds.
  - 2026-11-09 EG2 boundary (RTG-EG2-1): `ClassificationRetriever` uses `min_similarity` 0.3 and the 0.85 same-item threshold, both BGE cosine calibrations; the matched 30-request comparison must use the post-re-embed thresholds (REPL-EMB-R5) if it runs after v11. Regenerate: those thresholds only (the store holds 0 `classification` memories).
  - 2026-10-01 (RI-16): this path is the `priors` stage, measured at 156 ms p50 / 275 ms p95 on live `/chat`. Next step:
    set `use_memrl: false` on a branch, re-run the RI-16 30-request set, and confirm `priors` drops to near 0 with the
    same routed roles; then delete the branch.
  - 2026-10-06 MAIN source preparation accepted: [isolated comparison branch](https://github.com/pestopoppa/epyc-orchestrator/tree/codex/ni08-ri19-disable-memrl-config-proposal-20261006) at83d530e80e7c308c9b71477eaf9ba6605b50175a (base79abe3ec) changes only `routing_classifiers.direct_mode.use_memrl` and `routing_classifiers.specialist_routing.use_memrl` to false. Both existing callers retain keyword fallback. No main integration, live store read, seeding, inference or reload. The historical store/timing baseline is not remeasured here. RI19 remains open for the owning session's identical30-request RI16/role comparison; no threshold invented and no dead-code deletion before that result.
- [ ] **RI-24 — cut the `route` stage cost (197 ms p50 / 529 ms p95 on live `/chat`, RI-16).** (filed 2026-10-01) After
  - 2026-11-09 audit: STALE-PREMISE. The 197/529 ms baseline predates RI-18c (the `review_gate` stage is now always null) and the v11 embedder, so the box reads: count duplicate embeddings across `route` and `mode` only (zero inference, doable now); the 're-run the RI-16 set' step needs a live stack and a new baseline on the relaunched stack, not a delta against 197/529.
  RI-19 removes `priors`, `route` is the largest routing stage. Next step: count the prompt embeddings per request
  across `route`, `mode` and `review_gate`. If the same text is embedded more than once, compute it once per request
  and pass it down. Then re-run the RI-16 set and report the per-stage delta. RI-17 decides whether the KNN layer
  stays at all; this task only makes it cheaper while it does.
- [ ] **RI-20 — close the `## Routing Intelligence` prompt-section gap.** The section (`prompt_builders/builder.py:323` and `:817` (was :287)) is added only on turn 0 of the streaming paths (`chat.py:1453` legacy, `chat_pipeline/stream_adapter.py:196` unified); the graph path (`graph/helpers.py:856-864` no longer holds routing code; anchor unresolved: re-locate the graph-path prompt build by text before editing) passes no `routing_context`. Decide by A/B whether it helps, then wire it into the graph path or remove it from streaming. (filed 2026-09-26)
  - 2026-11-09 audit: SV. Anchors fixed inline; the graph-path anchor is unresolved. The A/B needs inference.
- RI-21 (2026-09-28, closed by the ARCHSWAP), RI-22 (2026-09-29, the 27B review verdict now parses) and RI-23 with
  RI-23a/RI-23b (2026-09-29, OP-69 option (a): thinking-on roles on the chat-completions lane, flag
  `thinking_roles_chat_lane`, live) are done. § *Completed Scope*.

#### Dependency Graph

```text
AR-3 / production traffic
    -> RI-10 canary sample counts
        -> RI-11 expand
            -> RI-12 global enforce

RI-10 threshold pathology
    -> RI-9b threshold/Pareto sweep
        -> repeat RI-10 decision

DAR-6.5 unconditional J14 A/B pass
    -> RI-13 injection-risk classifier
        -> conditional swarm-fanout routing
```

#### Forks And Mitigations

| Condition | Action |
|-----------|--------|
| RI-10 lacks high-risk samples | Keep canary; route traffic generation through AR-3/bulk-inference rather than changing thresholds blindly. |
| Enforce improves factuality but inflates cost | Sweep thresholds with RI-9b; prefer role-specific thresholds over global rollback. |
| Enforce regresses factuality or latency | Roll back to shadow; preserve logs and add a short failure analysis before retesting. |
| Verifier role lands via tri-role coordinator | Keep factual-risk review trigger as a substrate; Verifier may subsume review execution but not the risk signal. |
| SAE-feature classifier looks attractive | Treat as audit/interpretability layer only until difference-in-means and linear-probe baselines are run on the same v2 calibration slice. |
| Deep-research classifier work is needed | Use [`minddr-deep-research-mode.md`](model-evaluation-queue.md#track-minddr-deep-research-mode); do not expand this handoff for MindDR. |
| P3 consult gating becomes downstream consumer | Provide `factual_risk_score` / `difficulty_band` / shadow-routing signals as inputs to [`internal-interaction-lifecycle.md`](routing-program.md#track-internal-interaction-lifecycle) P3 `should_consult()` policy; routing-intelligence owns signal QUALITY, not lifecycle. |

#### Key Files

| Repo | Path | Purpose |
|------|------|---------|
| epyc-orchestrator | `src/classifiers/factual_risk.py` | prompt-side factual-risk scorer |
| epyc-orchestrator | `orchestration/classifier_config.yaml` | classifier/factual-risk config and thresholds |
| epyc-orchestrator | `src/api/routes/chat.py` | cheap-first bypass and request routing surface |
| epyc-orchestrator | `src/api/routes/chat_pipeline/routing.py` | plan review gate, failure graph veto, routing metadata |
| epyc-orchestrator | `src/escalation.py` | risk-aware escalation policy |
| epyc-orchestrator | `scripts/analysis/ri10_canary_sample_report.py` | RI-10 telemetry-depth gate |
| epyc-orchestrator | `scripts/analysis/ri10_canary_decision_report.py` | RI-10 operational-proxy + factuality-readiness decision packet |
| epyc-orchestrator | `scripts/analysis/ri10_canary_score_responses.py` | RI-10 scored factuality response report after quiet-window dispatch |
| epyc-research | `scripts/benchmark/seed_specialist_routing.py` | seeding/eval harness for A/B and threshold sweeps |
| epyc-research | `orchestration/factual_risk_calibration_v2.jsonl` | 2,600-example v2 calibration dataset |

#### Completed Scope

| Scope | Outcome | Evidence |
|-------|---------|----------|
| Phase 0 telemetry | Delegation/routing telemetry fields repaired. | [completed ledger](../completed/routing-intelligence-completed-through-2026-05-28.md) |
| Phase 1 classifier module | Types/config/output parsers and keyword delegating wrappers completed. | [completed ledger](../completed/routing-intelligence-completed-through-2026-05-28.md) |
| Phase 2 MemRL classifier | `ClassificationRetriever` and exemplar seeding completed. | [completed ledger](../completed/routing-intelligence-completed-through-2026-05-28.md) |
| Phase 3 factual-risk scorer | Regex scorer and shadow logging completed. | [completed ledger](../completed/routing-intelligence-completed-through-2026-05-28.md) |
| Phase 4 enforcement code | RI-1 through RI-7 implemented and A/B tested; initial A/B underpowered. | [completed ledger](../completed/routing-intelligence-completed-through-2026-05-28.md) |
| Phase 5 seeding fields | RI-8 verified on `RoleResult`; v2 calibration dataset built via NIB2-34. | [completed ledger](../completed/routing-intelligence-completed-through-2026-05-28.md) |
| RI-10 arm telemetry repair | Routing now logs the sampled factual-risk canary arm as `routing_meta.factual_risk_mode`, and the plan-review gate reuses that persisted arm instead of resampling. Existing 2026-06-20 rows remain insufficient; collect fresh post-fix rows before a rollout decision. | `epyc-orchestrator` `7647b32e`; `uv run pytest -q tests/unit/test_factual_risk.py tests/unit/test_pipeline_routing.py` -> `110 passed` |
| RI-10 report/gate semantics hardening | `ri10_canary_sample_report.py` now distinguishes raw high-risk volume from decision-grade arm-attributed telemetry, separates historical missing-mode rows from the current telemetry-health window, and derives default canary-role scope from `classifier_config.yaml`. DS-E1/Fable5 aggregate gates stay blocked when only raw count is ready. The 2026-07-04 current report has `464` raw high-risk rows since canary start, `20` current-window high-risk rows with `0` missing mode, and all `20` current rows fall inside the widened canary role scope; the scope-free diagnostic returns the same current-window count, so the blocker is insufficient arm count/balance. | `orchestration/reports/ri10_canary_sample_report_20260704T005256Z.json`; `orchestration/reports/ri10_canary_sample_report_all_roles_20260704T005332Z.json`; `orchestration/reports/fable5_gate_report_20260704T005355Z.md` |
| RI-10 deficit surfacing | Current report consumers now expose the exact collection deficits instead of only repeating "not ready": `canary_role_sample_deficit=30`, `canary_arm_volume_deficit=30`, and balance deficits `enforce=9`, `shadow=0`, plus by-role and by-role-arm counts in DS-E1/Fable next-action evidence. DS-E1 also refreshes from live progress logs when the latest saved RI-10 artifact predates the new schema. | `epyc-orchestrator` `807939fa`; `uv run python -m pytest -q tests/unit/test_ri10_canary_sample_report.py tests/unit/test_dynamic_stack_evidence_packet.py tests/unit/test_fable5_gate_report.py` -> `47 passed` |
| RI-10 decision-ready refresh | Live Fable/DS-E1 reads now show RI-10 no longer blocks the aggregate gate: current-window arm counts are sufficient (`enforce_high_risk=31`, `shadow_high_risk=50`), role coverage is populated (`frontdoor=11/11`, `worker_general=10/23`, `worker_vision=10/16`), and the current deficit counters are zero. Treat the July 4 insufficient-sample notes above as historical pre-accrual state. | 2026-07-05 live read-only refresh; `ri10_telemetry_collection_blocker=decision_ready`; Fable gate after W8 repair blocks only on W6 audit clearance |
| RI-10 decision packet | Standalone decision report now joins current canary rows to task outcomes, escalation events, plan-review events, and optional scored-response evidence. Current packet is `hold_quality_scored_no_lift`: operational proxies favor enforce, but scored factuality has no exact-accuracy lift (`0.10` vs `0.10`). | `epyc-orchestrator` `adf010b4`; `orchestration/reports/ri10_canary_decision_report_20260706T065654Z.{json,md}`; `uv run pytest -q tests/unit/test_ri10_canary_decision_report.py tests/unit/test_ri10_canary_score_responses.py tests/unit/test_ri10_canary_request_plan.py` -> `19 passed` |
| RI-10 scored collection packet | Request planner now supports dataset-backed expected-answer rows, answer-key JSONL output, and self-leak filtering. Generated a balanced scored canary packet: `60` requests, `30` enforce / `30` shadow, `20` per canary role, answer key separated from payloads, and no nontrivial expected-answer leakage. | `epyc-orchestrator` `8455af52`; `orchestration/reports/ri10_canary_scored_request_plan_20260705T151725Z.{json,payloads.jsonl,answer_key.jsonl}`; `uv run pytest tests/unit/test_ri10_canary_request_plan.py -q` -> `7 passed`; `ruff` passed |
| RI-10 scored response scorer | Response scorer joins quiet-window response JSONL to the answer key, extracts common response shapes, scores deterministic answer equivalence, and summarizes accuracy/token-F1 by role and enforce/shadow arm. | `epyc-orchestrator` `92ab4de7`; `scripts/analysis/ri10_canary_score_responses.py`; `uv run pytest tests/unit/test_ri10_canary_score_responses.py tests/unit/test_ri10_canary_request_plan.py -q` -> `11 passed`; focused `ruff` and `py_compile` passed |
| RI-10 scored response result | Quiet-window scored response artifacts are complete: `60` rows, `60` scored, `0` missing; enforce and shadow exact accuracy tie at `3/30` each, with only a tiny token-F1 enforce delta. This closes the "unscored" blocker and replaces it with "no enforce factuality lift." | `orchestration/reports/ri10_canary_scored_summary_20260705T185001Z.{json,md}`; `orchestration/reports/ri10_canary_scored_rows_20260705T185001Z.jsonl` |
| G12 role-tier recalibration | AA-Omniscience frontdoor/worker/architect evidence completed; deterministic 4-class scoring accepted for role-tier recalibration; measured tier multipliers landed in orchestrator. Mode/canary/enforce decisions remain RI-10+ gates. | [bulk-inference-campaign](eval-tower-program.md#track-bulk-inference-campaign) |
| Research intake | AA-Omniscience, STOP, Qwen-Scope SAE caveats, BaRP/Conductor context captured. | [completed ledger](../completed/routing-intelligence-completed-through-2026-05-28.md) |
| RI-21, RI-22, RI-23 (+RI-23a, RI-23b), 2026-09-28/29 | Escalation map ends at `architect_general`; the review gate parses on the 27B; thinking-on roles speak chat-completions (OP-69 (a), live). | [completed ledger § 2026-09-29](../completed/routing-intelligence-completed-through-2026-05-28.md) |

#### Research Intake Update — 2026-07-08: J-Space Interpretability (rec-009)

**Source**: Anthropic J-space (intake-782)

**Key finding**: Anthropic's J-space work on geometric interpretability of model representations could inform routing intelligence — understanding the geometric structure of model capabilities may enable better routing decisions than current embedding-based approaches.

**Applicability to EPYC**: Our current routing relies on embedding-based similarity (MemRL, factual-risk regex scorer, difficulty-signal regex features). J-space's geometric interpretability could provide a more principled routing substrate by mapping model capability geometry rather than prompt embedding similarity.

**Integration points**:
- Could replace/augment MemRL's embedding-based retrieval with geometric routing
- May enable the learned-head routing in `outer-coordinator-learned-head.md` with geometric priors
- Complements the tri-role architecture's role-axis by providing geometric capability mapping per role

**Action**: Monitor J-space development; evaluate integration with learned-head routing when the geometric interpretability substrate is available for open-weight models.

- **[declined: ws58 2026-11-03 content-review: unbounded monitor; research intake is the watch]** **RI-JS-1** — monitor J-space interpretability tools for open-weight model compatibility
- **[declined: ws58 2026-11-03 content-review: curiosity — geometric routing as an augmentation with no measured gap it would close]** **RI-JS-2** — evaluate geometric routing as an augmentation to MemRL embedding retrieval

#### Research Intake Update — 2026-07-29: LFM2.5-Encoder-350M-Prompt-Router

**Filed as a `monitor_only` comparator, not a work item.** The MLP learned-routing controller
(Phase 1 complete; Phases 1.5–3 unfinished) owns the routing-classifier line — see
[`learned-routing-controller.md`](routing-program.md#track-learned-routing-controller). LFM2.5-Encoder-350M-Prompt-Router
is a purpose-built prompt-router encoder and is therefore a useful external reference point for what
a dedicated router head buys over our MLP; it is **not** a replacement candidate, and opening it as
one would fork an already-unfinished program.

- *Moved to [`model-evaluation-queue.md`](model-evaluation-queue.md) § Track: meq-carve-routing-intelligence on 2026-11-03 (BRF-T1-MEQ, operator D2): **RI-CMP-1**.*

#### Reporting Instructions

- Update [`routing-and-optimization-index.md`](routing-and-optimization-index.md) P6 after RI-10/11/12 status changes.
- Update [`bulk-inference-campaign.md`](eval-tower-program.md#track-bulk-inference-campaign) if AR-3/J-package traffic is used to collect RI samples.
- If a new injection-risk classifier is opened, add it here as RI-13 and cross-link DAR-6/J14.
- If a stack/model change changes role throughput or cost, update q-scorer baselines and note the dependency in the routing index.

#### Research Intake Update — 2026-08-15 (harness selection as a routing dimension; intake-1140)

**Record only — no task, no build.** Filed because a plausible misreading of this source would push
routing work in the wrong direction, and the misreading was made once already during intake.

`intake-1140` (HarnessOpt-Bench, Scale AI) reports that "model choice has a larger effect than
coding-harness choice" — 0.142 vs 0.079 mean gain movement, about 1.8×. **That is not a routing
result, and citing it as one is backwards.** The harness varied in that contrast is the **optimizer's
own coding agent** (Claude Code vs opencode vs codex vs kimi-cli), not the harness being optimized.

On the **target** axis — the one our routing work cares about — the same paper's Table 3 is a
controlled swap where the harness is the only variable (same dataset, partition, rounds and target
model), and it shows the largest effects anywhere in the paper: OfficeQA 0.341 → 0.734,
BrowseComp-Plus 0.462 → 0.701, Terminal-Bench 0.241 → 0.607, GAIA 0.000 → 0.508. Converting those to
normalized gain and comparing against the best of **111** frontier-optimizer runs — an arithmetic the
dive performed and the paper never states — **the best off-the-shelf harness is statistically
unresolved from the best optimizer run on three of four tasks, and beats every optimizer on
Terminal-Bench by about 3.6 resolution bands.**

**The citable implication is therefore the opposite of the headline**: harness/scaffold selection is
worth about as much as an entire frontier-model optimization campaign, and should be treated as a
**first-class routing dimension rather than a fixed substrate**. Cite `intake-1140#record`, never as
"model > harness".

#### Research Intake Update — 2026-09-17 (Jev typed-decision cluster; intake-1472/1473/1474/1487)

- [x] **RI-14 — Typed-decision fast path for closed-set routing questions.** Once TD-2 calibration lands, evaluate a Choice-style candidate-logit call as the routing classifier fast path; never gate on uncalibrated confidence; report agreement + calibration + wall time vs the current classifier. (Evidence: intake-1472/1473/1474/1487; owner stub `typed-decision-plane.md`, RTG-56.) ✅ 2026-09-29 — folded into TD-11 (`typed-decision-plane.md`; operator ruling Q5: TD-11 is the single typed-routing owner). The classifier comparison, the calibration rule and the intake-1501 question shape moved there.
  - *Question-shape template 2026-09-23 (intake-1501):* tier choice with criteria + ordinal effort score, with a 20-card OOD
    probe whose labels come from a distribution the arm was not tuned on.
- [ ] **RI-15 — (conditional) Generation-side comparator for factual_risk.** When factual_risk.py is assessed for shadow→enforce, report on the same rows a generation-side comparator (spec-OFF mean/min token log-prob of the served answer), not only the calibration set. Evidence: intake-1521 (zero-shot log-prob ties a simplified supervised router in distribution; no calibration measured).
  - 2026-11-09 audit: SV, conditional (only on a shadow->enforce assessment of factual_risk). The 2026-06-19 calibration sets predate the lineup; re-derive before use.
  - *Cross-link (2026-09-29, Jev-techniques map §3.2):* the same intake-1521 log-prob signal is EV-CONF-2's
    salient-token confidence source on the autopilot eval surface (`autopilot-decision-plane-audit-2026-07-22.md`).
    Different surfaces, one evidence base: reuse EV-CONF-2's spec-OFF capture rather than building a second one.
- [x] **ROUTE-COP-GUARD — Reliability floor for any router objective that uses cost-of-pass.** Cost-of-pass as the sole routing objective is gamed by a cheap near-random strategy, so any router or controller using the frontier form needs a reliability floor (pass rate at or above tau, or pass^k) before a candidate enters the frontier, and must state that retries are not independent when context carries over (intake-2262#record). Add the floor and the caveat to the router-objective section of this handoff and to the learned-routing evaluation protocol; a unit test on a synthetic frontier containing a cheap random candidate must show it excluded. Acceptance: the section edit is filed and the synthetic-frontier test passes. Estimate: 0.5-1 day. ✅ 2026-10-21
  - *(2026-10-21, dpf-specs.)* Section filed in this handoff and in learned-routing-controller.md; `cop_frontier.py` + `test_cop_frontier.py` (epyc-orchestrator orchestrator a350b690); synthetic-frontier test passes (cheap random candidate excluded).

#### Router objective: cost-of-pass needs a reliability floor (ROUTE-COP-GUARD, 2026-10-21)

Cost-of-pass (expected spend per solved task, `cost_per_attempt / pass_rate`) used as the SOLE routing objective is gamed by a cheap near-random strategy: a nearly free candidate that passes a small share of tasks has a low, sometimes frontier-leading, cost-of-pass while being useless to route to (`intake-2262#record`). Rules for any router or controller that uses the frontier form:

1. **Reliability floor before frontier entry.** A candidate enters the cost-of-pass frontier only if its pass rate is at or above a declared `tau`, or, where the surface retries, its pass^k (all k attempts pass) is at or above `tau`. `tau` and `k` are declared before the run and written next to the frontier; there is no floor-free frontier.
2. **Retries are not independent when context carries over.** `pass_rate ** k` is the optimistic independent bound. A retry that inherits the failed attempt's transcript, errors or anchoring is correlated with it, so a surface that carries context between attempts must measure its k-attempt pass rate directly and pass that in; it must not be derived from the single-attempt rate.
3. **Report the excluded set.** The frontier report lists the candidates excluded by the floor and their cost-of-pass, so a reader sees what the objective alone would have chosen.

Reference implementation and test: `epyc-orchestrator` `scripts/analysis/cop_frontier.py` and `tests/unit/test_cop_frontier.py` (synthetic frontier with a cheap random candidate; the test asserts it has the lowest unguarded cost-of-pass and is excluded under the floor). The same rule is copied into the learned-routing evaluation protocol: `learned-routing-controller.md` section "Evaluation protocol: cost-of-pass objective needs a reliability floor".

##### Research intake 2026-10-31 — ws58 batch (intake-2545..2602)

Operator-approved 2026-10-31 (plan revision 2, `research/intake-stage3-plan-2026-10-31-ws58.md`, sha256 `043e502133cae214175ea3f2a395f575e6ca13b9f3ee058525ed020264ab5012`; relayed by the ws58 coordinator; budget approved: about 13 MI210-hours for the drafter pilot, 6-9 engineer-weeks for the race checker, the 95.5 GB ThinkingCap download; D1 confirmed: in-weights calculator declined, GPU reason recorded on intake-2550/2574; D2 approved: scratch upstream builds are measurement instruments only). Trigger records below are prose with no checkbox until a reviewed session confirms their condition.

- [ ] **RI-25 — Zero-inference fold replay over delegation records (intake-2565#record).** Apply the fold criteria (fold a sub-agent only if the folded version does not score worse; inspect which tasks flip; repeat runs) to existing orchestrator delegation records: for each delegate() role (worker_math, worker_general, worker_summarize share one model), measure from records how often a chain needs the role's own context, how much of the 4,000-character truncated hand-off (src/repl_environment/routing.py:581) reaches the worker, and how often the delegated answer is re-asked by the caller. Output a per-role fold-candidate table; no serving change.
  - 2026-11-09 audit: STALE-PREMISE: the 2026-11-01 screen found ZERO replayable `delegate:<role>` records and the 4,000-char cap is not persisted, so this replay cannot run on existing data. Re-scoped: first capture delegation records (child box below); the replay stays blocked on it. Not an Autopilot wait.
  - [ ] **RI-25a — capture replayable delegation records.** Persist, per `delegate()` call: role, input, answer, the 4,000-char cap applied, and caller follow-up linkage; zero inference to build, new data accrues once the stack runs. Acceptance: a unit test showing a delegate call writes a record that the RI-25 replay can read. Owner: orchestrator delegate path.
  - 2026-11-01 bounded record-adequacy screen: [capsule](../../artifacts/analysis/ri25-delegation-screen-20261101/README.md). The frozen progress and compact runtime/benchmark JSON/JSONL prefixes contain zero `delegate:<role>` values for `worker_math`, `worker_general`, or `worker_summarize`; 500 existing benchmark delegation events target `coder_escalation` and do not carry replayable inputs, answers, or caller follow-up linkage. Source inspection confirms the 4,000-character cap is not captured in persisted call records. Context delivered, role-specific context need, caller re-asks, task flips, repeat outcomes and folded quality therefore remain UNKNOWN. This bounded screen makes no fold claim and does not satisfy the full repeat/counterfactual replay criterion; leave RI-25 unchecked and open pending adequate captures.


## Track: research-intake-harness-inference-2026-11-06

Source batch: 12 entries ingested 2026-11-06 (t3code, Foundry Local, HarnessMM + 9 expansion entries). Plan: `research/intake-stage3-plan-2026-11-06-harness-inference.md`.
- [ ] **RTG-EP-1 — Prove the AMDGPU/MIGraphX execution provider on gfx90a.** Build and register the MIT `onnxruntime-ep-amdgpu` plugin against ORT-GenAI 0.19, run one small ONNX chat model through Foundry Local's EP registration path on the MI210, and report: whether the EP loads, which ops fall back to CPU, tokens/s, and what a Linux port of the EP-selection path would cost. Acceptance: a run log with the EP name and device visible plus a port-cost estimate; no quality claim without a paired CPU run.
  - 2026-11-09 audit: stays open, NOT the lead item. ROCm is 6.2.0-66 and `/opt/rocm/lib` has no `libmigraphx*`/onnx files, so MIGraphX must be installed or built first (a build cost to estimate, not a blocker); nothing else in this handoff depends on it; needs a GPU window (`gpu_window_policy.yaml`, fails closed). ORT-GenAI 0.19 and plugin version claims are unverified.

- [ ] **RTG-VAR-1 — Emit a host-capability manifest as a compiled input.** Add `orchestration/host_capabilities.yaml` (CPU flags, NUMA nodes, GPU arch and VRAM, ROCm version, RAM) probed from the existing inventory scripts and consumed by the registry compiler. Acceptance: the manifest is generated reproducibly and a golden test pins its shape.
  - 2026-11-09 audit: `orchestration/host_capabilities.yaml` does not exist; "existing inventory scripts" are unnamed (only quarter_scheduler/stack_topology facts found) and the registry compiler is unnamed (candidates: `src/registry/model_descriptors.py` via `scripts/registry/compile_descriptors.py`, or `src/registry/stack_priors.py`). Name both before building. The host is single and fixed, so the manifest's value is as an input to RTG-VAR-2.

- [ ] **RTG-VAR-2 — Add a variant dimension to the model descriptor (rewritten 2026-11-09 for descriptor v3).** Descriptor v3 (`orchestration/model_descriptors.yaml`) is already keyed per (model, quant) with `quant`, `ctx_max`, `mem_gb`, `measured` and `role_bindings`, and its invariant is "keyed by physical model identity, never by role name". So a variant is NOT seeded from role entries: seed it from the existing per-(model, quant) records (4 physical models today) and decide whether a variant is a new sibling record per (model, quant, backend, device) or a sub-entry. Add `backend`, `device`, `path`, `sha256` (reuse the launch-time GGUF fingerprint pins from SEC-ART, 6dbc4e27, instead of re-hashing), `measured_tps`, `quality_ref`; normalise the free-form quant strings. Acceptance: schema plus a migration that resolves every existing (model, quant) record to at least one variant with no invented measurement, and `role_bindings` still resolve through the model, not the variant. Decision needed: sibling record vs sub-entry (recommend sub-entry under the (model, quant) record, so the per-(model, quant) invariant and existing readers stay unchanged).

