# Cost-Aware Routing

**Category**: `cost_aware_routing`
**Confidence**: verified
**Last compiled**: 2026-04-28
**Sources**: 24 documents (2 deep-dives, 7 active handoffs, 17 intake entries)

## Summary

Cost-aware routing in the EPYC stack addresses a fundamental pathology of reasoning LLMs: they allocate compute inversely to problem difficulty. On trivially easy problems like "2+3=?", QwQ-32B generates 901 tokens across 13 redundant solution attempts -- a 1,953% token overhead where 95.7% of compute is pure waste. This is not an edge case: across difficulty levels, 50-70% of reasoning tokens contribute nothing to reaching the correct answer, and 92% of correct answers appear in the first solution round. The distinctness ratio of later solution attempts decays rapidly, falling 11.5 percentage points from round 3 to round 4+. After three attempts, additional reasoning is overwhelmingly redundant.

The theoretical foundation for addressing this comes from the Conditional Information Bottleneck (CIB) framework, which formally proves that flat token budgets are suboptimal. CIB's Proposition 4.1 shows that linear length penalties correspond to a uniform vocabulary prior -- implicitly assuming all tokens carry equal information, when in reality filler tokens ("Let me think about this...") and essential reasoning tokens ("Therefore x = 3 by substitution") have vastly different information content. The optimal compression objective maximizes the information the reasoning trace provides about the answer *beyond what the prompt already tells us*, while minimizing redundant information leakage from the prompt into the trace. CIB dominates the Pareto frontier: at DLER-7B scale, it achieves 53.5% accuracy at -8% tokens or 52.9% at -32%, outperforming both L1-Exact (51.5% at -29%) and L3L1 (39.7% at -65%).

The practical consequence is a three-tier compression strategy: zero-training methods (conciseness prompting, TrimR pruning, short-m@k parallel generation), activation steering (SEAL/FlowSteer control vectors on dense models), and training-based methods (OPSDC self-distillation, CIB semantic cost training). Each tier trades implementation complexity for compression quality. The EPYC orchestrator has implemented all of tier 1 and has infrastructure for tier 2, while tier 3 remains blocked on GPU training access.

A critical recent finding reshapes the entire routing cost model: the Omega metric evaluation (2026-04-09) revealed that tools and REPL pipelines *hurt* accuracy on 7 of 10 benchmark suites. Agentic tasks suffered -54.5pp, coding -44pp, general QA -26pp, and math -26pp when routed through tool-equipped paths versus direct generation. Only hotpotqa (+12pp) and gpqa (+6pp) benefited. The "cost" of routing to a tool path is not just tokens -- it is accuracy. Default routing should prefer direct mode, with REPL/tool use opt-in for known-beneficial task types.

The EPYC orchestrator has a three-band difficulty classifier (easy/medium/hard) in shadow mode at recalibrated thresholds (0.15/0.35), band-adaptive token budgets (1500/3500/7000) gated behind enforce mode, a reasoning length alarm that cancels and re-generates when think blocks exceed 1.5x the band budget, and an autopilot system continuously optimizing routing via a 4D Pareto archive. The missing piece is validation of the recalibrated thresholds -- the original 0.3/0.6 split produced 92% easy / 0% hard classification, which is useless for routing.

## Key Findings

### The Overthinking Problem

- **50-70% of reasoning tokens are waste**: Outcome efficiency (xi_O) across QwQ-32B ranges from 41.9% on trivial problems (ASDIV) to 32.8% on very hard problems (AIME24). Process efficiency (xi_P) is somewhat better but still shows 59.8% on trivial and 58.4% on very hard -- substantial compute wasted even on diverse exploration. [overthinking-info-bottleneck.md](../research/deep-dives/overthinking-info-bottleneck.md)

- **92% of correct answers appear in the first solution round**: The first round comprises less than 60% of total tokens but contains nearly all correct answers. Solution round 4+ has 11.5% lower distinctness ratio than round 3 -- later rounds restate what was already tried. The empirical ceiling for useful reasoning depth is approximately 3 solution rounds. [overthinking-info-bottleneck.md](../research/deep-dives/overthinking-info-bottleneck.md)

- **Easy problems suffer more from overthinking than hard ones**: Within MATH500, levels 1-2 (easy) trigger 3.7 solution rounds on average while levels 4-5 (hard) trigger 3.0 rounds. The compute allocation is inverted from what efficiency demands. [overthinking-info-bottleneck.md](../research/deep-dives/overthinking-info-bottleneck.md)

### Theoretical Foundation

- **Flat token budgets are provably suboptimal** (CIB Proposition 4.1): Linear length penalties assume all tokens carry equal information -- a uniform vocabulary prior. The optimal approach assigns semantic cost via surprisal under a language model prior: low-surprisal tokens (predictable filler) are cheap to compress, high-surprisal tokens (novel reasoning) are expensive. CIB eliminates the former while preserving the latter. [overthinking-info-bottleneck.md](../research/deep-dives/overthinking-info-bottleneck.md)

- **Three distinct compression mechanisms identified**: CIB training produces (1) algorithmic generalization -- discovering mathematically superior solution paths, (2) elimination of exploration bloat -- removing trial-and-error loops and self-verification tautologies, and (3) syntactic noise filtering -- stripping conversational scaffolding while preserving computational logic. These correspond to progressively finer-grained waste identification. [overthinking-info-bottleneck.md](../research/deep-dives/overthinking-info-bottleneck.md)

- **Information density analysis validates the semantic cost approach**: Baseline models show information density valleys at ~0.1 nats (predictable filler tokens). CIB-trained models raise the floor to 0.2+ nats -- every retained token carries at least 0.2 nats of information about the answer. This is the measurable signal of effective compression. [overthinking-info-bottleneck.md](../research/deep-dives/overthinking-info-bottleneck.md)

### Compression Methods by Tier

- **SEER's MAD-based filtering doubles naive compression**: Best-of-N sampling with Median Absolute Deviation outlier filtering achieves 39.8% compression versus 18.2% for naive BoN at matched or better accuracy. N=3 saturates -- marginal returns beyond 3 candidates are negligible. MAD is more robust than mean/stddev for skewed length distributions. [reasoning-compression-s3cot-adaptive.md](../research/deep-dives/reasoning-compression-s3cot-adaptive.md)

- **Failed outputs are consistently longer than successful ones**: SEER confirms across 7B, 14B, and 32B scales. On HumanEval/129 with DeepSeek-Qwen-7B, failed cases had median 9,489 tokens versus 8,296 for successes. Length is a negative quality signal, motivating reasoning length alarms. [reasoning-compression-s3cot-adaptive.md](../research/deep-dives/reasoning-compression-s3cot-adaptive.md)

- **Easy problems tolerate aggressive compression; hard problems resist it**: OPSDC achieves 56-59% compression on easy problems with accuracy parity or improvement. Hard problems tolerate only 35% compression with 3.4-5.4pp accuracy drops on AIME-class tasks. This validates difficulty-adaptive budgets. [intake-110](https://arxiv.org/abs/2603.05433)

- **SimPO with FCS+Reflection achieves 37-48% token reduction**: Across difficulty levels, accuracy is preserved (only -0.2% on MATH500). For fine-tuning scenarios, this is the empirically validated recipe: shortest correct response as positive, longest correct response as negative. [overthinking-info-bottleneck.md](../research/deep-dives/overthinking-info-bottleneck.md)

- **TrimR is valuable on hard tasks, irrelevant on easy ones**: Evaluation (2026-04-09) showed GPQA: full 58.3% vs think-strip 52.6% vs trimr 45.7% (thinking helps ~6pp). GSM8K: all strategies identical at 66% (model barely generates think tokens on easy math). Aligns perfectly with difficulty-adaptive routing. [reasoning-compression handoff]

### Routing Intelligence

- **Tools/REPL hurt accuracy on 7/10 suites**: Omega metric evaluation found agentic tasks -54.5pp, coder -44pp, general -26pp, math -26pp when using tools versus direct generation. Only hotpotqa (+12pp) and gpqa (+6pp) benefit. The implication is that default routing should prefer direct mode, with tool use as an opt-in for known-beneficial task types. [reasoning-compression handoff]

- **Tool output compression is slightly net-positive (+4pp REPL overall)**: Controlled A/B test (100q ON vs 99q OFF, 5 suites, WS-3 bug fixed) showed compression helps math (+25pp, noise reduction) but hurts hotpotqa (-25pp, retrieval context lost). Coder/general/gpqa near-neutral. Default kept ON. The test also exposed a routing bug (WS-3): `routing.py` hardcoded `task_type="chat"` causing 100% web search in Arm B -- fixed with role-to-task_type derivation. [bulk-inference-campaign.md]

- **Risk signal does not predict escalation need**: Package B risk distribution analysis (2,433 decisions) found low-risk prompts escalate MORE (64.4%) than high-risk prompts (50.0%), counterintuitively. However, the high-risk sample was tiny (n=16), too small for reliable conclusions. The RI-10 canary window has been extended to 2026-04-27 to accumulate at least 50 high-risk samples. [bulk-inference-campaign.md]

- **OPSDC's length ratio is a free difficulty signal**: Comparing output length with and without a conciseness prompt yields a difficulty estimate at zero additional cost. Large ratio = easy (compressible); small ratio = hard (reasoning is load-bearing). Alternatively, just add a conciseness instruction: short output = easy, long output = hard. [intake-110](https://arxiv.org/abs/2603.05433)

- **Explicit word limits outperform vague conciseness**: intake-276 deep-dive revealed that "be concise" prompts are the weakest tested form. Explicit numeric limits (e.g., "answer in under 15 words for factual questions") based on CCoT's 30-60 word sweet spot significantly outperform open-ended brevity instructions. Worker prompts have been upgraded accordingly. [reasoning-compression handoff]

### Methodological Taxonomy of Learned Routers (2026-04-26 — Trinity deep-dive)

The cost-aware-routing literature now divides cleanly into **four methodological classes** of learned router. Tracking these explicitly so design discussions can place new proposals on the map. Chapter 08-cost-aware-rewards in `epyc-inference-research/docs/chapters/` is queued for an update reflecting this (P19.7 in `routing-and-optimization-index.md`).

| Class | Representative | Training | Action space | When applicable |
|---|---|---|---|---|
| RL-trained end-to-end | xRouter (arxiv:2510.08439, Salesforce 2025), Router-R1 (arxiv:2506.09033) | DAPO / GRPO with cost-aware reward; 7B router; multi-GPU | (model) | Cloud routing with API-cost reward; not CPU-feasible |
| Preference / matrix-factorisation | RouteLLM (arxiv:2406.18665, LMSYS ICLR 2025) | Preference data; matrix factorization or BERT classifier | Binary strong/weak | Two-model routing with preference data |
| Backprop on contrastive / decision-aware loss | DAR-2/3/4 (this stack), SPO+, bilinear scorer | Closed-form gradient on contrastive Q or SPO+ surrogate | (model) | When labelled routing decisions are available; CPU-feasible |
| **Black-box ES against task fitness** (NEW 2026-04-26) | **Trinity (arxiv:2512.04695, ICLR 2026, Sakana AI)** | sep-CMA-ES on terminal binary reward; no labels, no gradients | (model, role) decoupled | When labels do not yet exist (cold-start); when loss is block-ε-separable; CPU-feasible at 10K-param head |

**Trinity (intake-474)** is the canonical example of class 4. Reports 86.2% on LiveCodeBench v6 (claimed coordinator-system record), 21.9% mean relative-error reduction over 2nd-best multi-agent baseline. **Crucial for class-3 vs class-4 choice**: Trinity's REINFORCE ablation collapses to 0.253 LCB vs 0.615 for sep-CMA-ES at the same budget — pure policy gradients drown in off-block noise on block-ε-separable losses. The block-ε-separability of *our* routing landscape is testable (LRC P4.2) and gates whether class-4 ES becomes a viable cold-start trainer for our setup. Deep-dive: [`research/deep-dives/trinity-evolved-llm-coordinator-methodology.md`](../research/deep-dives/trinity-evolved-llm-coordinator-methodology.md). [intake-474]

## Updates — 2026-04-28

### New findings (BaRP + LLM Bandit + design-space landscape)

- **Bandit-feedback training pattern (BaRP, intake-495, arxiv:2510.07429).** Production logs only record the chosen specialist's outcome, not counterfactuals — closes a real train/test mismatch in EPYC's routing data. BaRP solves this with REINFORCE on bandit feedback. For the EPYC stack the rationale is adopted into DAR-3 SPO+ design: convex surrogate loss with 10% epsilon-greedy exploration manufactures counterfactual data; the SPO+ surrogate avoids REINFORCE's high-variance gradient. Source: [`decision-aware-routing.md`](../handoffs/active/decision-aware-routing.md) DAR-3.

- **2-D performance-cost preference vector at inference time (BaRP).** Trained router can be modulated at test time via `ω = (ω_perf, ω_cost)` on the simplex, shifting the routing decision distribution **without retraining**. Per-tenant or per-task ω override (e.g., interactive ω_perf=0.8, batch ω_perf=0.3). Calibrated cost scaling τ exposed as a runtime knob (env var `DAR_COST_TAU`). Implementation footprint: ~50–100 LoC across `retriever.py` selection scoring + `routing.py` ω plumbing. Adopted as **DAR-4b** — orthogonal to DAR-4 bilinear scorer; can ship independently if DAR-4 slips. Source: [`decision-aware-routing.md`](../handoffs/active/decision-aware-routing.md) DAR-4b; intake-495.

- **IRT score predictor for prompt features (LLM Bandit, intake-496, arxiv:2502.02743).** Per-prompt `(latent_difficulty, latent_discrimination)` over BGE pooled output, fitted to observed model outcomes. Discrimination scores stratify prompt selection — high-discrimination prompts separate model abilities; low-discrimination prompts are uninformative. Feeds DAR-5 (Q-value feature engineering) and LRC P4.1.3 (feature-position audit). Calibrated via Platt scaling. Source: [`learned-routing-controller.md`](../handoffs/active/learned-routing-controller.md) P4.1.3 / P5.1; intake-496.

- **Model identity vectors (LLM Bandit).** Replace the hard-coded `v_model = [baseline_tps, baseline_quality, memory_cost, param_count_log, is_moe, quant_bits]` with a learned d-dim model identity vector trained jointly with the bilinear scorer. Initialized from spec features so cold-start is preserved. Adopted as **DAR-5** (~150 LoC, conditional on DAR-4). Source: [`decision-aware-routing.md`](../handoffs/active/decision-aware-routing.md) DAR-5; intake-496.

- **Methodological taxonomy of learned routers extended to four published reference points.** The class table above (RL-trained end-to-end / preference-MF / contrastive-DA / black-box ES) now has named representatives at each point: BaRP (intake-495) is the canonical bandit-feedback class-1 with 2-D ω knob; LLM Bandit (intake-496) sits at the class-3 boundary with IRT prompt features + learned model identity; Trinity (intake-474) anchors class-4; Conductor (intake-493, arxiv:2512.04388, ICLR 2026 Sakana AI) sits at class-1 with `(worker_id, NL_subtask, access_list)` action space and 7B GRPO on 2× H100 80GB. Conductor is **competitive intelligence only** — GPU-required, out of CPU stack — and informs OC-0.6 design-space comparison but is not a target architecture. Source: intake-474, intake-493, intake-495, intake-496.

- **Class-4 black-box ES is the new methodological insight.** When the routing loss is block-ε-separable and labels do not yet exist, ES outperforms REINFORCE at our scale (Trinity: 0.615 vs 0.253 LCB at matched budget). This is the unique class-4 lever and the realistic cold-start trainer for new role surfaces lacking episodic labels. Empirical block-ε-separability of EPYC's routing landscape is **testable on our own 175K-label episodic dataset** (LRC P4.2 diagnostic: full-rank vs rank-10 vs diagonal weight regularization). The diagnostic gates whether sep-CMA-ES ever becomes a viable trainer for our setup. Source: [`learned-routing-controller.md`](../handoffs/active/learned-routing-controller.md) P4.2 / P4.4.

- **Closure-inflation discipline (2026-04-28).** Do not generalize "Conductor 7B GRPO is out of CPU stack" to "no learned coordinator could ever work". The four published reference points (BaRP, LLM Bandit, Trinity, Conductor) occupy distinct positions in (action-space × optimizer × scale × hardware) space; only Conductor is GPU-bound at our review-pass-quality threshold. BaRP, LLM Bandit, and Trinity are each individually CPU-feasible at the head-size scales we operate.

### Cost-side actionables added

- **DAR-3 (SPO+ + 10% epsilon-greedy)** → ~100 LoC; cost-side rationale for the convex surrogate is "no high-variance REINFORCE gradient on bandit-feedback data".
- **DAR-4b (2-D ω preference vector + cost τ)** → ~50–100 LoC; pure runtime knob, no retraining; immediate per-tenant cost steering.
- **DAR-5 (IRT prompt features + learned model identity)** → ~150 LoC; conditional on DAR-4 land.
- **LRC P4.1.3 (IRT-feature variant inside P4.1 audit)** → +1 session.
- **LRC P5.2 (cold-start IRT-stratified A/B vs on-disk full sweep)** → highest-leverage single experiment from intake-495/496; if validated, every model swap compresses from a multi-hour sweep to ~30 min.

### Open questions added

- Empirical block-ε-separability of EPYC's routing loss surface — gates whether sep-CMA-ES (Trinity-class) becomes a viable cold-start trainer for new role surfaces (LRC P4.2).
- Optimal exposure of `ω = (ω_perf, ω_cost)` and `τ` to autopilot vs production traffic — should ω be a per-request knob, a per-tenant default, or an autopilot-tuned Pareto-archive coordinate?
- Does IRT-stratified onboarding (50 prompts) actually agree with on-disk full benchmark sweeps within ≤5% on every baseline feature? If yes, model-onboarding latency drops from hours to ~30 min; if no, the onboarding pipeline must keep the full sweep.

### Cross-references

For the routing-architecture impact (tri-role axis, DAR phase plan, design-space comparison table) see [Routing Intelligence](routing-intelligence.md). For the optimizer-design-space (sep-CMA-ES vs REINFORCE vs GRPO; class-4 ES) see [Reinforcement Learning](reinforcement-learning.md).

## Actionable for EPYC

### Implemented (Production)

- **Q-scorer with sweep-verified TPS baselines**: Calibrated quality scoring for routing, using benchmark-derived throughput baselines per model/quant combination.
- **Difficulty classifier** (`difficulty_signal.py`): 7 regex features producing 3-band classification. Shadow mode with recalibrated thresholds (0.15/0.35 for ~40/40/20 split).
- **Band-adaptive token budgets**: `_repl_turn_token_cap()` returns 1500/3500/7000 by difficulty band when enforce mode is active. Derived from overthinking efficiency metrics.
- **Conciseness prompting with explicit word limits**: Format-specific limits on worker_general.md (MC: letter+1 sentence, factual: under 15 words, open: under 60 words) and worker_math.md (MC: letter+1 sentence, numeric: under 50 words, proof: under 100 words). Architect has aggressive "<150 tokens" limit. Coder uses "code only".
- **N-gram loop detection**: `detect_think_block_loop()` catches repetition within reasoning traces.
- **Reasoning length alarm**: `_check_reasoning_length_alarm()` cancels and re-generates when think blocks exceed 1.5x band budget. Double-gated (feature flag + enforce mode), retry includes conciseness nudge.
- **Answer-tag stop sequences**: `<answer></answer>` XML tags with `</answer>` in stop sequences eliminate post-answer rumination loops across all benchmark prompts.
- **OAA metric**: `eval_metrics.py` with alpha-penalized excess token scoring and per-token intelligence metric for benchmark evaluation.

### In Progress

- **Difficulty signal validation at new thresholds (FAILING)**: Original 0.3/0.6 thresholds yielded 92% easy / 0% hard -- useless. Recalibrated to 0.15/0.35 for ~40/40/20 split. However, Package B large-sample validation (2,433 routing decisions, 2026-04-09) showed NO predictive spread: escalation rates are flat at 62.2%/60.7%/62.2% across easy/medium/hard bands. The difficulty signal at current thresholds does not differentiate routing needs. Recommendation: re-examine feature weights or add semantic features before moving to enforce mode. [bulk-inference-campaign.md]
- **SEAL control vector generation for Qwen3-32B**: Contrastive pair generator (80 problems) and evaluation script (scaling sweep at 0.3/0.5/0.7) prepared. Awaiting model servers. Works via existing `--control-vector` flag in llama.cpp on dense models. Blocked on Qwen3.5 hybrid SSM (no `build_cvec()` in `qwen35.cpp`).
- **Autopilot GEPA integration**: GEPA evolutionary prompt optimization now runs 30% of PromptForge trials via `OrchestratorGEPAAdapter`. 35x fewer rollouts than GRPO. Comparing acceptance rates against LLM mutation in AR-3 journal.

### Planned

- **Enforce mode activation**: Route easy problems to worker tier (fast, cheap), hard problems to architect tier (expensive, accurate). Requires validated difficulty signal at new thresholds.
- **Direct-mode-first routing**: Based on Omega findings, default routing should prefer direct generation over REPL/tool paths. Tool use opt-in only for known-beneficial types (hotpotqa, gpqa).
- **Outcome efficiency telemetry** (xi_O per band): Instrument REPL turns with total tokens, correctness, and first-correct tokens. Calibrate band thresholds until xi_O is roughly uniform (target 60-70%) across bands.
- **Information density monitoring**: Track token-level log-probabilities during generation. Rolling surprisal below 0.2 nats for 50+ consecutive tokens indicates filler. Start with post-hoc analysis before real-time stopping.
- **Surprisal-based adaptive stopping** (Phase 3, research-grade): If information density monitoring shows a clear filler detection signal, replace token cap entirely with content-aware stopping. The CIB framework predicts this should be strictly better than any fixed budget.

### Not Actionable

- **CIB semantic token cost training**: Requires GRPO training with frozen language model prior on GPU. Theoretically optimal but requires training infrastructure we do not operate.
- **FlowSteer nonlinear activation steering**: MLP ODE solve at intervention points has no llama.cpp infrastructure. Only the weaker SEAL linear baseline is deployable, and only on dense models.
- **CoLaR latent reasoning compression**: Model-level training at 1B-1.5B scale only. Incompatible with speculative decoding.
- **TALE dynamic budget estimation**: A/B test (2026-04-11) showed static word limits outperform TALE on OAA metric (static -3.48 vs TALE -5.95). Pre-pass adds latency without benefit. Deferred.

## Open Questions

- What are the recalibrated difficulty thresholds' predictive power? Package B validation (2,433 decisions) shows zero predictive spread -- escalation rate is flat across all three bands. The 7-feature regex classifier may lack sufficient signal. Options: (a) add semantic features (embedding-based difficulty), (b) use OPSDC length-ratio signal, (c) accept that difficulty is not reliably predictable from prompt alone and use runtime feedback instead.
- Does the Omega finding (tools hurt on 7/10 suites) replicate with the current orchestrator version? Specific model and tool configurations may have improved since evaluation.
- Can OPSDC's length-ratio difficulty signal be used at runtime, or is it too expensive (requires generating two responses)?
- How does TrimR interact with speculative decoding acceptance rates? Pruning reasoning tokens changes the distribution, which may affect draft model alignment.
- What is the right enforcement strategy for band-adaptive budgets -- hard truncation, soft penalty (reduced temperature), or retry with conciseness nudge? The current reasoning length alarm uses retry, but the optimal approach may vary by difficulty band.
- Is the ~5pp accuracy drop on AIME-class problems under any compression method an irreducible cost of the task structure, or can per-problem adaptive budgets (finer than per-band) recover it?
- Should the autopilot shift budget allocation from NumericSwarm to PromptForge/StructuralLab based on the finding (intake-265) that architectural changes outperform parameter tuning on broken baselines?

## Decision-Aware Routing

The predict-then-optimize architecture of the Q-scorer has been identified as a fundamental pathology in cost-aware routing. The Q-scorer learns Q-values per model independently via TD update (`Q_new = Q_old + alpha * (reward - Q_old)`), then selects models by argmax over `selection_score = Q_value - cost_lambda * (expected_cost / cold_cost)`. This architecture separates prediction from the routing decision -- the gradient is unaware of whether a Q-value change would actually flip the routing choice.

> Source: [decision-aware-routing.md](/workspace/handoffs/active/decision-aware-routing.md)

### DAR-1: 96% Uniform Q-Values

Offline regret analysis (DAR-1, 2026-04-15) over 7,211 routing decisions confirmed the predict-then-optimize pathology empirically:

- **96% of Q-values are uniform** (spread < 0.001) -- the Q-scorer has barely learned model preferences after thousands of decisions.
- Selection score spread is non-trivial (median 0.107) but comes entirely from cost and similarity terms, not from learned Q-values.
- 25% of decisions have trivial spread (< 0.01); 75% have meaningful differentiation only via cost terms.
- 3,355 learned decisions vs 3,856 rules/classifier decisions.

The implication is stark: Q-values are decorative, not decision-driving. Cost and similarity dominate all routing choices. This explains the zero predictive spread in the difficulty signal (Package B, n=2,433) -- the upstream Q-values feeding the routing pipeline carry almost no learned signal.

> Source: [decision-aware-routing.md](/workspace/handoffs/active/decision-aware-routing.md) DAR-1

### SPO+ Formulation

Decision-aware learning aligns training with the routing DECISION rather than prediction accuracy. The SPO+ (Smart Predict-then-Optimize) loss provides a convex surrogate with closed-form gradients:

```
L_SPO+ = sum(max(0, 2*c_hat[j] - c_true[j])) - c_hat[i*] + c_true[i*]
```

where `c_hat` = predicted costs, `c_true` = true costs, `i*` = true optimal model. The gradient is zero when the routing decision is already correct -- learning signal only flows when the prediction would lead to a wrong decision. Because the EPYC action space is trivially small (N=3-5 models), the intractability concerns from the operations research literature (differentiating through LP/MIP solvers) do not apply. SPO+ and contrastive losses are cheaper than the current TD updates.

DAR-3 (planned) will implement SPO+ with 10% epsilon-greedy exploration routing to accumulate the counterfactual data needed for decision-aware training.

> Source: [decision-aware-routing.md](/workspace/handoffs/active/decision-aware-routing.md) DAR-3

### Contrastive Q-Score

DAR-2 (implemented, 2026-04-15) adds a contrastive adjustment to the Q-scorer reward signal. The `_compute_contrastive_adjustment()` method in `q_scorer.py` retrieves top-10 similar routing memories, compares the selected model's Q-value against alternatives with learned Q-values, and computes a bounded adjustment (max +/-0.1, margin=0.05) that sharpens the decision boundary between models. The adjustment is zero when ranking is already correct with sufficient margin. It skips the 96% of memories at default Q=0.5 (unlearned) and only fires when alternatives have real learned Q-values. Gated by `CONTRASTIVE_Q_UPDATES` feature flag (ON by default).

> Source: [decision-aware-routing.md](/workspace/handoffs/active/decision-aware-routing.md) DAR-2

### Bilinear Model-Feature Scorer (Zero Cold-Start)

DAR-4 (planned) replaces per-action Q-value tables with a bilinear scorer: `Q(prompt, model) = sigmoid(v_model^T W v_prompt + b)`. Model features are already available in `ScoringConfig` (baseline_tps, baseline_quality, memory_cost, param_count_log, is_moe, quant_bits). When a new model joins the fleet, its features are known from specs -- no routing history is needed for cold-start. This eliminates the current bootstrapping problem where new models receive default Q=0.5 until enough traffic accumulates.

> Source: [decision-aware-routing.md](/workspace/handoffs/active/decision-aware-routing.md) DAR-4

### Validation Campaign

Package I in the bulk inference campaign consolidates the decision-aware routing validation tasks: I1 (DAR-3 SPO+ exploration with sustained traffic for counterfactual data), I2 (DAR-4 bilinear scorer A/B test against per-action Q-tables), and I3 (EV-5 ThinkPRM-1.5B for T2 process verification). I1 is highest priority as it generates the counterfactual data needed for all downstream decision-aware training.

> Source: [bulk-inference-campaign.md](/workspace/handoffs/active/bulk-inference-campaign.md) Package I

## Related Categories

- [Context Management](context-management.md) -- Compression techniques reduce context pressure, which is the primary cost driver; tool output compression is a routing-adjacent optimization
- [LLM Prompting](llm-prompting.md) -- Conciseness prompting is a tier-1 zero-cost routing optimization; controllability research bounds its effectiveness, especially on RL-trained workers
- [Context Extension](context-extension.md) -- Larger effective context windows change the cost calculus for routing by reducing the need for aggressive compression

## Source References

- [Overthinking + Information Bottleneck](../research/deep-dives/overthinking-info-bottleneck.md) -- xi_O/xi_P efficiency metrics, CIB theory (Propositions 4.1/4.2), difficulty-adaptive budgets, surprisal-based filler detection, three compression mechanisms
- [Reasoning Compression (S3-CoT + SEER)](../research/deep-dives/reasoning-compression-s3cot-adaptive.md) -- SEER MAD-based filtering, failed-longer-than-successful finding, integration paths A-D, n-gram loop parameters
- [FlowSteer Concise Reasoning](../research/deep-dives/flowsteer-concise-reasoning.md) -- SEAL linear baseline compatibility, Qwen3.5 hybrid SSM blocker, FlowSteer MLP infeasibility
- [CoLaR Latent Compression](../research/deep-dives/colar-latent-compression.md) -- Latent compression trade-offs, not-actionable assessment
- [Reasoning Compression handoff](../handoffs/active/reasoning-compression.md) -- OPSDC analysis, 3-tier approach taxonomy, TrimR/Omega evaluation results, all action items
- [Autopilot Continuous Optimization handoff](../handoffs/active/autopilot-continuous-optimization.md) -- 4D Pareto archive, species-based optimization, GEPA integration, safety gates
- [intake-110](https://arxiv.org/abs/2603.05433) OPSDC -- 57-59% compression with accuracy gains; difficulty adaptation is emergent; length-ratio routing signal
- [intake-125](https://arxiv.org/abs/2602.01982) S3-CoT -- Self-sampled activation steering; progressive curriculum; VL-D in residual stream
- [intake-126](https://arxiv.org/abs/2602.05539) FlowSteer -- Nonlinear activation steering; SEAL linear baseline; +6% accuracy at 14.5% reduction
- [intake-127](https://arxiv.org/abs/2505.17155) TrimR -- Verifier-based inference-time pruning; valuable on hard tasks, irrelevant on easy
- [intake-128](https://arxiv.org/abs/2509.14093) SEER -- Best-of-N + MAD filtering; N=3 saturation; 73-97% loop elimination
- [intake-129](https://arxiv.org/abs/2505.17813) short-m@k -- Parallel generation with early stopping; 34.5% more accurate than longest chains
- [intake-130](https://arxiv.org/abs/2412.21187) Overthinking analysis -- 50-70% token waste; inverse difficulty allocation; distinctness ratio decay
- [intake-133](https://arxiv.org/abs/2603.08462) CIB theory -- Formal unification of budget forcing; Pareto-dominant compression; semantic token cost
- [intake-134](https://arxiv.org/abs/2505.16552) CoLaR -- Latent reasoning embeddings; 2-5x chain reduction; speculative decoding incompatibility
- [intake-276](https://arxiv.org/abs/2604.00025) Brevity constraints -- Explicit word limits outperform vague conciseness instructions
- [Decision-Aware Routing](/workspace/handoffs/active/decision-aware-routing.md) -- DAR-1 regret analysis (96% uniform Q-values), DAR-2 contrastive Q-score, DAR-3 SPO+ formulation, DAR-4 bilinear model-feature scorer
- [Bulk Inference Campaign](/workspace/handoffs/active/bulk-inference-campaign.md) -- Package B validated findings: difficulty signal has no predictive spread at 0.15/0.35, risk signal counterintuitively anti-correlated with escalation (n=16 high too small), tool A/B compression slightly net-positive (+4pp), WS-3 routing bug fixed; Package I consolidates DAR-3/4 + EV-5 validation
