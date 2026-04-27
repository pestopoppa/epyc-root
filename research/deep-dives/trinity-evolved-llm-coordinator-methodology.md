# TRINITY: An Evolved LLM Coordinator — Methodology Deep Dive

- **Source**: arXiv:2512.04695v2 (Dec 2025, last revised Apr 2026) · OpenReview ICLR 2026 (id `5HaRjXai12`)
- **Authors**: Jinglue Xu, Qi Sun, Peter Schwendeman, Stefan Nielsen, Edoardo Cetin, Yujin Tang (Sakana AI)
- **Status at intake (2026-04-26)**: ICLR 2026 accepted; no public code/weights; described by Sakana as the core engine of the Sakana Fugu commercial product
- **Why this matters to us**: Trinity attacks the same thesis we are building around — a *lightweight, learned, multi-turn coordinator* over a heterogeneous agent pool. Even if our final architecture differs, this is the most direct prior art we have for the routing-and-coordination layer. Treat this document as standing comparative context for all orchestrator and routing work.
- **Intake entry**: [intake-474](../intake_index.yaml)

---

## TL;DR

Trinity wraps a **0.6B SLM (Qwen3-0.6B) + 10K-parameter linear head**, trained with **separable CMA-ES** against terminal task fitness, into a multi-turn coordinator that picks `(LLM, role)` per turn from a pool of seven LLMs and three roles `{Thinker, Worker, Verifier}`. It posts **86.2% on LiveCodeBench** and a **21.9% mean relative-error reduction** over the second-best multi-agent baseline across four in-distribution benchmarks. Critically, ablations show:

- **REINFORCE collapses** (25.3% LCB) vs sep-CMA-ES (61.5% LCB) at comparable budget — the loss landscape favors diagonal/black-box methods.
- **Removing the Verifier/Thinker/Worker trichotomy costs 5–8 points** across benchmarks — role assignment is a real, separable degree of freedom.
- **Reading the penultimate token instead of the final token costs >10 points on LCB** — feature-extraction position carries enormous signal.
- **Singular-value fine-tuning of the backbone adds 3–4 points** on top of the head — cheap parameter-efficient adaptation.

Our existing routing controller (BGE-large + 200K MLP, SFT on episodic Q-labels, single-shot per call) shares the *thesis* but differs in every implementation primitive. The portable pieces are: tri-role action space, ES-against-fitness as a cold-start trainer, SVD-scale backbone adaptation, and the block-ε-separability diagnostic.

---

## 1. What Trinity actually is

### 1.1 Architecture

```
                           ┌──────────────────────────────────┐
prompt + transcript ─────► │  Qwen3-0.6B  (backbone)          │
                           │   ↳ SVD-scale FT (~9K params)    │
                           └──────────────┬───────────────────┘
                                          │ penultimate-token hidden state h ∈ ℝ^d
                                          ▼
                           ┌──────────────────────────────────┐
                           │  Linear head fθ  (~10K params)   │
                           │   parallel to LM head            │
                           └──────────────┬───────────────────┘
                                          │
                          softmax-over-7  │ softmax-over-3
                          (LLM choice)    │ (role: T/W/V)
                                          ▼
                              dispatch (LLM_k, role_k) for turn k
```

Quote: *"It takes the hidden state h corresponding to the penultimate output token as its sole input. ... projects a hidden state h∈ℝ^d to an output of size L+3, which provides two sets of logits: L logits for selecting an LLM and three logits for assigning its role."*

The backbone is **NOT frozen** — they apply SVD-FT, learning only singular-value scales while keeping orthogonal matrices fixed. Total trainable parameters ≈ 19K (10K head + ≈9K SV-scales).

### 1.2 Action space

- **L = 7** LLMs in the pool: `{GPT-5, Gemini-2.5-pro, Claude-4-Sonnet, Gemma-3-27B-It, DeepSeek-R1-Distill-Qwen-32B, Qwen-3-32B (direct), Qwen-3-32B (reasoning)}`.
- **3 roles**: Thinker (analyses + plans + decomposes), Worker (acts on the task), Verifier (checks completeness + correctness).
- Output is a flat `(L+3)`-dim logit vector, softmaxed *independently* over the L block and the 3 block — i.e., role and agent are decoupled at the policy layer.
- Termination: `τ = min{k ≤ K : R_k = V and u_k = ACCEPT}`, with `K = 5` max turns.

### 1.3 Training protocol

- **Optimizer**: sep-CMA-ES with population `λ = ⌈4 + 3 ln n⌉ ≈ 32` for `n ≈ 10K` parameters; replication `m_CMA = 16` per candidate (noise reduction).
- **Budget**: 1.5k–40k fitness evaluations end-to-end.
- **Fitness**: terminal binary reward `R(τ) ∈ {0, 1}` per rollout (1 if final answer is correct).
- **Single rollout** = one full multi-turn coordination trajectory on one test example, evaluated against ground truth.
- No SFT, no RL, no labelled routing decisions. Just the eval oracle.

### 1.4 Multi-turn protocol

- Up to `K = 5` turns. Verifier accepting ⇒ stop early.
- Inter-turn communication is the **full transcript** (not summary, not hidden-state passing).
- Coordinator constructs a brief role-specific prompt for each selected LLM, lightly post-processes the response, appends to transcript.

### 1.5 The block-ε-separability claim

Definition 1 (Hessian-based): the scaled Hessian `H_S(θ) = S^(1/2) H(θ) S^(1/2)` is *uniformly nearly block-diagonal* with inter-block coupling bounded by `ε_H ∈ [0, 1)`.

Empirical evidence: a "block-diagonal-10" head (10 disconnected blocks instead of full-rank) retains competitive mid-tier performance — the loss surface really does decompose along these blocks. Proposition 2 then gives diagonal CMA a per-iteration contraction rate `Ω(1/n)` after stabilization, vs full-rank methods that suffer from off-diagonal noise under strict budget.

This is the formal justification for why sep-CMA-ES beats REINFORCE *and* full-rank CMA-ES on this problem.

---

## 2. Methodology cross-check vs our stack

| Dimension | Trinity | EPYC orchestrator today | Status |
|---|---|---|---|
| Coordinator backbone | Qwen3-0.6B (decoder, autoregressive) | BGE-large-en-v1.5 (encoder, bidirectional) — `embedder.py` L34 | structurally different |
| Backbone tuning | SVD-scale FT (~9K extra params) | Frozen | gap |
| Head architecture | Linear, 10K params, `(L+3)` logits | 2-layer MLP, ~200K params, 6 logits — `routing_classifier.py` | larger but coarser |
| Feature position | Penultimate-token hidden state | BGE pooled embedding (CLS or mean-pool — needs audit) | different paradigm |
| Action space | (LLM × role) decoupled — agent and role each softmaxed | Single-shot per-call model selection only | **gap** |
| Training signal | Terminal binary reward on rollouts | Q-value-weighted cross-entropy over episodic distillation labels | label-dependent vs label-free |
| Optimizer | sep-CMA-ES, λ≈32, ~1.5k–40k evals | Backprop / SFT | gap |
| Multi-turn protocol | Up to 5 turns, Verifier-acceptance termination | Single-shot route + opaque external review/escalation | **gap** |
| Pool | 7 LLMs (3 closed frontier + 4 open) | Open-source-only inference pool | constrained |
| Outer driver | n/a (Trinity replaces the outer driver) | Claude (Claude Code, autopilot) | parallel system |

### 2.1 The tri-role gap is the architectural one

Our orchestrator collapses everything into model-selection. Roles in our system today (frontdoor, architect_general, coder, reviewer) are *attached to models* — a model permanently has a role. Trinity's insight is the orthogonal one: **role is a per-turn property of the dispatch, not of the model**. The same Qwen-3-32B can be Thinker on turn 1, Worker on turn 3, Verifier on turn 5.

The ablation evidence (`-5 to -8 points` from removing tri-role) is the strongest single empirical claim in the paper for the architectural choice. This is a real degree of freedom we are not currently exploiting at the routing-policy layer — review/escalation is a pipeline-level construct, not a per-call action.

This holds **independently of whether the routing head is trained by ES or backprop** — adding the role axis is an architectural change.

### 2.2 ES side-steps the credit-assignment problem DAR is trying to solve

`decision-aware-routing.md` documents the diagnosis: TD-style Q-value updates produce 96% uniform Q-values — zero predictive spread. DAR-2/3/4 propose decision-aware contrastive losses (SPO+, bilinear scorer) to fix this *while keeping a backprop-style learner*.

Trinity's REINFORCE result (25.3% LCB vs 86.2% for sep-CMA-ES) is a strong negative result for *pure* policy gradient on this geometry. DAR-2/3/4 are not pure PG — they are contrastive losses with closed-form gradients — so the failure mode is not directly transferable. But the deeper point is: **ES does not need a credit-assignment story at all**. Fitness is observed at the rollout level; CMA-ES updates the parameter distribution from the population's relative ranking. There is no gradient through the routing decision, no off-policy correction, no reward-shaping debate.

This is methodologically attractive precisely *because* DAR is hard. If the eval-tower fitness signal is reliable at the rollout level, ES can train a routing head against it without needing the per-decision counterfactual structure DAR is constructing.

**Caveat**: ES also discards information. With 175K episodic memories already labelled, SFT distillation (our Phase-1 recipe, 92% val acc) likely beats ES on warm surfaces. ES wins on cold surfaces where labels do not yet exist.

### 2.3 The pool-homogeneity caveat needs revision: where does Claude fit?

First-pass call was: "our open-source pool has narrower quality variance than Trinity's mixed pool, so the headroom shrinks." On reflection that under-states our setup, because **we do have a heterogeneous-quality system** — just at a different layer:

- **Inner inference pool** (epyc-orchestrator, all open-source): this is the layer where pool homogeneity holds. Frontdoor, coder, architect, worker — variance exists but is bounded, and Trinity's gain numbers should be discounted accordingly when projecting onto this surface.
- **Outer coordination layer** (Claude Code, autopilot): Claude drives delegation decisions across the inner pool. This is structurally analogous to Trinity's coordinator — except *we use a frontier model for it instead of a 0.6B + 10K head*. The Claude-vs-cheap-frontdoor-vs-specialist gradient is wider than the inner-pool gradient and closer to Trinity's regime.

Two implications:

1. **At the inner-pool layer**, Trinity is a methodology lesson, not a magnitude promise. A learned routing head replaces some of what episodic memory + Q-scoring already does. Gains will be incremental.
2. **At the outer-coordination layer**, Trinity is a more direct target. A learned coordinator that picks `(role, sub-agent)` for the *Claude-driven* loop — deciding when Claude should plan vs delegate vs verify — is the same architectural shape Trinity proposes. We currently make this decision with Claude's reasoning at every step, which is expensive and unsystematic. A 10K-parameter head trained via ES against autopilot success could plausibly automate part of this loop.

The second point is the genuinely interesting one and is currently unowned by any handoff.

---

## 3. What's portable, what's not

### Portable (recommended for spike or replication)

1. **Tri-role action space** — architectural, optimizer-agnostic. Single biggest empirical lever in their ablations. Worth a dedicated handoff.
2. **sep-CMA-ES as cold-start trainer** for new routing surfaces lacking episodic labels. Population λ≈32, m=16 reps, budget ≤2k evals first, fitness = eval-tower per-question pass rate. CPU-feasible at our 200K-param scale.
3. **Block-ε-separability diagnostic** — train identical routing heads with full-rank vs rank-10 vs diagonal weight regularization on our existing 175K episodic labels. If mid-rank ≈ full-rank, our geometry matches Trinity's and the optimizer-choice argument applies to us.
4. **SVD-scale fine-tuning** on whatever backbone we use (BGE today; could be a small autoregressive LM later). ~9K extra params, claimed +3-4 points across tasks. Cheaper than LoRA.
5. **Outer-coordination-layer learned router** — the Claude-driven decision of *which sub-agent to dispatch and in what role* is currently informal. A trained coordinator head against autopilot success is a direct Trinity analogue.

### Not portable (or needs adaptation)

1. **Penultimate-vs-final-token finding** is decoder-specific. BGE is an encoder — the analogous knob is "CLS vs mean-pool vs last-layer" which has its own literature and different ablation shape. Don't blindly translate.
2. **The 7-LLM heterogeneous pool with frontier closed models** is incompatible with `feedback_opensource_only.md` for the inner pool (no GPT-5/Gemini/Claude-4 inference). Inner-pool gain projections must discount accordingly.
3. **The exact 21.9% mean error reduction** — this is on benchmarks (LCB, Math500, MMLU, RLPR) using a heterogeneous pool with massive quality variance. Our benchmark suite, eval-tower targets, and inner pool are all narrower. Set expectations 2–5× lower for inner-pool replication.
4. **Trinity's training data and code** — paper claims supplementary material with code+weights, but Sakana has not opened it (Trinity is core to Sakana Fugu commercial product). Replication must work from the paper. Don't wait for a release.

---

## 4. Refined recommended actions (canonical list)

| # | Action | Type | Owner / handoff |
|---|---|---|---|
| 1 | Update `chapters/08-cost-aware-rewards.md` to add a fourth methodological class — *ES-trained routers* — alongside RL-trained (xRouter / Router-R1), preference-trained (RouteLLM), and matrix-factorization. Trinity is the canonical citation. | Doc update | epyc-inference-research/docs |
| 2 | **Block-ε-separability diagnostic** on our routing landscape: train identical 2-layer heads on existing 175K episodic labels with full-rank vs rank-10 vs diagonal weight regularization. If mid-rank ≈ full-rank, our geometry matches Trinity's and ES becomes methodologically appropriate. | Experiment | learned-routing-controller |
| 3 | **sep-CMA-ES cold-start spike** for new routing surfaces lacking episodic labels (Phase 2/3 of `learned-routing-controller.md`). Fitness = eval-tower per-question pass rate. Population λ≈32, budget ≤2k evals first to test feasibility. | Experiment | learned-routing-controller |
| 4 | **Re-examine DAR-2/3/4** for hidden REINFORCE-class pathology: do SPO+ and bilinear scorer gradients share the off-block-noise weakness REINFORCE has on block-ε-separable losses? Quick analytical check; not a full rerun. | Audit | decision-aware-routing |
| 5 | **SVD-scale fine-tuning trial** on whatever backbone we use for the routing head. ~9K params; ablation evidence for +3-4 point gains. | Experiment | learned-routing-controller |
| 6 | **Tri-role action space — new handoff stub** (pending user approval per `CLAUDE.md`). Architectural change orthogonal to optimizer choice. Independent of items 2–5. | Architecture | new handoff (pending) |
| 7 | **Audit feature-extraction position** in current routing classifier: are we feeding BGE's CLS, mean-pool, or last-layer? Trinity's 10-point swing is a reminder this matters even for encoder models. Compare options on a held-out routing-accuracy benchmark. | Audit | learned-routing-controller |
| 8 | **Outer-coordination-layer Trinity analogue** — explore whether a learned coordinator head trained against autopilot success can automate part of the Claude-driven dispatch loop. Speculative; needs scoping discussion before any handoff. | Discussion | possibly new handoff |
| 9 | **Do NOT wait for Trinity code drop.** Sakana product economics make open release unlikely. Replicate from paper. | — | — |

---

## 5. Replication budget estimate

For action 3 (sep-CMA-ES cold-start spike):

- **Parameters to optimize**: routing head ≈ 10K–200K depending on whether we replicate Trinity's 10K linear head or use our existing 200K MLP.
- **Population size**: `λ = 4 + 3 ln(n)`. For n=200K → λ≈45. For n=10K → λ≈32.
- **Replication per candidate**: m=16 (Trinity default).
- **Total per generation**: 45 × 16 = 720 fitness evaluations.
- **Per evaluation**: one rollout through the orchestrator on one eval question. Wall-clock ≈ inner-pool inference latency (1–10 s typical).
- **Per generation wall-clock**: ≈ 720 × 5 s = 60 minutes (parallelized: 720 / N_concurrent × 5 s).
- **Generations to convergence**: Trinity reports 1.5k–40k total evaluations → roughly 2–55 generations at our population size. Call it 10 generations as a feasibility-test target.
- **Total**: ≈ 10 hours at 32-way concurrency. Fits comfortably in an overnight run.

Caveats: requires the eval-tower to be wired as a fitness oracle (parallelisable, per-question scorable). Math-Verify adoption flagged as a precursor in `routing-and-optimization-index.md` cross-cutting concern #13.

---

## 6. Open questions

1. **Does our routing landscape actually have block-ε-separability?** Action 2 answers this. Without it, the optimizer-choice argument in Trinity is decorative and ES is just one option among many.
2. **Do tri-roles have semantic meaning at our scale?** Trinity's pool has 7 distinct LLMs with strong specialization; their Verifier vs Thinker distinction is informationally rich. Our inner pool has fewer, more similar models — does the Verifier/Thinker distinction collapse?
3. **Where is the right layer for a learned coordinator — inner or outer?** The outer (Claude-driven) layer is structurally closer to Trinity but is also the layer with the most expensive per-call cost (Claude tokens). Inner is cheaper to iterate on but has less headroom.
4. **What is the eval-tower's per-question scoring latency under 32-way parallelism?** This is the binding constraint on ES generation cadence.
5. **How sensitive is sep-CMA-ES to the population/replication ratio?** Trinity uses λ=32, m=16. We may want λ smaller (faster generations) or m larger (more noise reduction). No ablation in the paper.

---

## 7. Sources

- [TRINITY: An Evolved LLM Coordinator (arXiv HTML v2)](https://arxiv.org/html/2512.04695v2)
- [TRINITY: An Evolved LLM Coordinator (arXiv abs)](https://arxiv.org/abs/2512.04695)
- [TRINITY: An Evolved LLM Coordinator (OpenReview, ICLR 2026)](https://openreview.net/forum?id=5HaRjXai12)
- [Sakana AI Highlights TRINITY as core to Sakana Fugu (TipRanks, 2026)](https://www.tipranks.com/news/private-companies/sakana-ai-highlights-trinity-coordinator-as-core-to-multi-agent-product-strategy)
- [Sakana AI GitHub organization](https://github.com/SakanaAI) — no Trinity repo as of 2026-04-26; ShinkaEvolve is the closest released artifact

### Related EPYC documents

- Intake entry: [intake-474](../intake_index.yaml)
- Active handoffs: [decision-aware-routing.md](../../handoffs/active/decision-aware-routing.md), [learned-routing-controller.md](../../handoffs/active/learned-routing-controller.md), [routing-intelligence.md](../../handoffs/active/routing-intelligence.md), [routing-and-optimization-index.md](../../handoffs/active/routing-and-optimization-index.md), [meta-harness-optimization.md](../../handoffs/active/meta-harness-optimization.md)
- Chapter to update: [`08-cost-aware-rewards.md`](/mnt/raid0/llm/epyc-inference-research/docs/chapters/08-cost-aware-rewards.md)
- Prior-art intake siblings: xRouter (arxiv:2510.08439), RouteLLM (arxiv:2406.18665), Router-R1 (arxiv:2506.09033), BaRP (arxiv:2510.08429), LLM Bandit (arxiv:2502.02743) — all already in `intake_index.yaml`

---

*Last updated: 2026-04-26. Treat this document as standing comparative context for orchestrator and routing work — even if our final architecture differs, Trinity attempts to build around the same thesis, and revisions to our routing/coordination plans should reference back to it.*
