# Recursive Reasoning Models (HRM → TRM → GRAM) — Deep Dive & EPYC Routing Implications

- **Date**: 2026-05-21
- **Source intakes**: [intake-582 GRAM](../intake_index.yaml), [intake-583 TRM](../intake_index.yaml), [intake-584 HRM](../intake_index.yaml), [intake-585 Augmented-HRM mechanistic analysis](../intake_index.yaml)
- **Related**: [`research/deep-dives/trinity-evolved-llm-coordinator-methodology.md`](trinity-evolved-llm-coordinator-methodology.md) — the direct routing-relevant prior art
- **User question that triggered this**: *"could a 7M-parameter TRM-style recursive net act as a specialized router or verifier for constraint-satisfaction subtasks on EPYC?"* — the standing thread on training a network dedicated to routing
- **Related handoffs**: [learned-routing-controller.md](../../handoffs/active/learned-routing-controller.md), [decision-aware-routing.md](../../handoffs/active/decision-aware-routing.md), [outer-coordinator-learned-head.md](../../handoffs/active/outer-coordinator-learned-head.md), [routing-and-optimization-index.md](../../handoffs/active/routing-and-optimization-index.md)

---

## TL;DR

The HRM → TRM → GRAM lineage is a sequence of *small recurrent puzzle solvers* (7M–27M params) that beat frontier LLMs on closed-world constraint problems (Sudoku, ARC-AGI, N-Queens) by **iterating a small network many times** instead of producing long autoregressive chains-of-thought. Within the lineage:

- **HRM** (Sapient, June 2025, 27M params, [code](https://github.com/sapientinc/HRM)) introduced the two-frequency recurrent design.
- **TRM** (Samsung SAIL Montreal, October 2025, 7M params, [code](https://github.com/SamsungSAILMontreal/TinyRecursiveModels)) showed HRM's dual-module bio-motivation is not load-bearing — a single 2-layer net wins.
- **GRAM** (Ahn lab, May 2026, 10M params, ICLR 2026 workshop, [project page](https://ahn-ml.github.io/gram-website/)) makes the recursion *stochastic* (amortized variational inference over latent trajectories), unlocking parallel-trajectory inference-time scaling and multi-solution coverage.

A separate mechanistic analysis (Ren & Liu, **arxiv:2601.10679**, intake-585) demonstrates that **HRM is not "reasoning" — it is converging-to-fixed-point pattern matching**, and that most of its claimed gains can be reproduced by data augmentation + input perturbation + bootstrapping on a vanilla architecture (Augmented-HRM hits 96.9% on Sudoku-Extreme vs the original 54.5%).

**Bottom line for EPYC routing**: the three papers are *not* a path to a recursive-net router. The architectural lever (recursion + heavy data aug on closed vocabularies) does not transfer cleanly to natural-language routing inputs, and Trinity (intake-474) is the more direct prior art for the routing problem we have. The genuinely novel idea that *does* survive contact with our stack is **GRAM-as-verifier**: a per-decision constraint-satisfaction head that checks "is the MLP's routing decision likely correct?" — distinct from anything currently in the routing roadmap. Recommendation: scope it (no code) before committing to build.

---

## 1. What the three papers actually claim

### 1.1 HRM (intake-584, June 2025)

**Architecture**: two interacting recurrent modules.
- High-level (H) module: slow abstract planner.
- Low-level (L) module: fast detailed computer.
- L runs N inner steps per H update; both share a Transformer cell with attention + FFN.
- 27M params total, RoPE, vanilla Transformer block as the recurrent cell.

**Training recipe**:
- ~1000 puzzle examples per task (Sudoku-Extreme, Maze-Hard, ARC-AGI).
- No pretraining, no CoT data, no labeled intermediate steps.
- Single forward pass at inference (no explicit intermediate supervision).
- Sapient open-sourced the code, July 2025 ([sapientinc/HRM](https://github.com/sapientinc/HRM)).

**Headline result**: near-perfect Sudoku/maze with 27M params; outperforms much larger LLMs on ARC-AGI.

**Per GRAM (intake-582) re-benchmark**: Sudoku-Extreme 55.0%, ARC-AGI-1 40.3%, ARC-AGI-2 5.0%. Weakest of the three recursive baselines in GRAM's compute-matched comparison.

### 1.2 TRM (intake-583, October 2025)

**Architecture**: one 2-layer net with hidden dim 512.
- RMSNorm, RoPE, SwiGLU (modern Transformer block).
- **MLP-only variant** for small contexts (Sudoku, 81 tokens) — drops self-attention entirely, MLP-Mixer style.
- **Attention retained** for larger tasks (ARC-AGI 900 tokens, Maze 30×30).
- Q-head for halting (ACT-style, simplified — single forward pass per optimization step).
- 7M params total.

**Training recipe**:
- Sudoku-Extreme: 1K train (1000× aug) / 423K test on 1 L40S × ~36hr.
- Maze-Hard: 1K train (8× aug) / 1K test on 4 L40S × 24hr.
- ARC-AGI: 960 train (1000× aug) on 4 H100 × 3 days.
- 42 effective recursions per supervision step (T=3 high-level cycles × 6 latent steps + 1 final). 16 supervision steps at test time.
- Inference: take the mode over 1000 data-augmentation evaluations.

**Headline result**: 7M parameters, ARC-AGI-1 45%, ARC-AGI-2 8% — beats Deepseek R1 / o3-mini / Gemini 2.5 Pro at <0.01% of their params.

**Key architectural simplification**: HRM's dual-module design dropped — a single 2-layer net trained recursively wins. The bio-inspired multi-timescale framing was illusion; the real lever is recursion + heavy augmentation + ACT.

### 1.3 GRAM (intake-582, May 2026)

**Architecture**: 10M params, hidden=512, 8 heads, FFN=512, RoPE encoder + Transformer-block recursive core (h, l states) + linear decoder. For image tasks: shallow conv encoder + patch embedding.

**Novelty over TRM/HRM**: Gaussian noise injection at each recursion step with **learned mean μ_θ(u_t) and variance σ²_θ(u_t)**. This turns the deterministic latent trajectory into a stochastic one. Posterior q_φ(τ|x,y) shares the same Markov structure as the prior — *not* a separate encoder; just target-conditioned μ_φ, σ²_φ MLPs over the deterministic update.

**Training objective**: per-supervision-step truncated ELBO,
```
log p_θ(y|x) ≥ E_qφ [log p_θ(y|τ,x)] − KL(q_φ(τ|x,y) ‖ p_θ(τ|x))
```
optimized via amortized variational inference. Per-step truncation for memory.

**Two-axis inference-time scaling**:
- **Depth**: 16 supervision steps × T=3 × K=6 = 288 forward passes per single trajectory.
- **Width**: N independent trajectories sampled in parallel; take majority/coverage.

**Compute**: 8× RTX 4090 for 2hr (Sudoku) → 5 days (ARC-AGI). Batch size 768, AdamW lr=1e-4 wd=1.0.

**Headline result (compute-matched)**: GRAM 16-iter + N=20 samples reaches Sudoku-Extreme 97.0% — beats TRM at 320 iter (90.5%) at comparable compute budget. N-Queens 8×8 with N=20 samples: 99.7% accuracy, 90.3% solution coverage vs deterministic baselines max 36.1% coverage. Unconditional MNIST generation demonstrates p_θ(x) capability.

**Ablations (load-bearing)**:
- Remove guidance (set μ_θ=0, keep σ²_θ): Sudoku maintained at 94.88%; **N-Queens collapses to 50.27%** — structured guidance is essential on multi-solution tasks.
- Remove stochasticity (set σ²_θ=0): **0% on both Sudoku and N-Queens** — variational framework, not noise per se, is the source of gains.
- Add naive noise to TRM (stochastic decoder + random init): **no improvement** — gains tied to the amortized VI structure.

---

## 2. Tier 2b — what the mechanistic critique reveals

**Ren & Liu, "Are Your Reasoning Models Reasoning or Guessing? A Mechanistic Analysis of Hierarchical Reasoning Models"** (arxiv:2601.10679, intake-585).

Three findings:

1. **HRM fails on trivial puzzles**: extremely simple Sudoku instances with minimal unknowns expose HRM. The "fixed-point property" — the foundational assumption that HRM converges to a single solution attractor — is violated in practice. The model sometimes can't represent the trivial answer.

2. **Grokking dynamics, not progressive reasoning**: progress across recursive steps is **not** uniform. There exists "a critical reasoning step that suddenly makes the answer correct" — abrupt pattern recognition consistent with grokking, not step-by-step logical deduction.

3. **Multiple-fixed-points trap**: the model converges to the first available fixed point regardless of correctness and stays there. This is structurally inconsistent with the "reasoning" framing.

**The productive payload**: Augmented-HRM using (a) data augmentation, (b) input perturbation, (c) model bootstrapping bumps Sudoku-Extreme from **54.5% → 96.9%** without architectural change. Most of HRM's missing performance came from missing training tricks, not missing biological inspiration.

**Why this matters for our intake**: HRM's headline numbers and its TRM/GRAM successors inherit the same architectural framing. If "recursive reasoning" is mostly "convergence-to-attractor pattern matching with heavy data augmentation," then the relevant transfer signal for EPYC is **pattern matching with iterative refinement on a small parametric net**, not "reasoning." Routing IS pattern matching, so this actually re-opens the question rather than closing it — but it reframes the lever.

---

## 3. Where this lineage sits in the EPYC routing landscape

### 3.1 Current router (per [learned-routing-controller.md](../../handoffs/active/learned-routing-controller.md))

```
Request ─► BGE-large (300MB) ─► 1024-d embedding ─► 200K-param MLP ─► 5-class softmax
                                                                       │
                                       conf >= per-class threshold? ───┤
                                       ├── Yes ► route immediately (<1ms after BGE)
                                       └── No  ► fallback to FAISS KNN + Q-ranking (10–50ms)
```

- 92.0% val accuracy on 174K labels (snapshot at 2026-04-15; live episodic.db is at 8K, FAISS reset).
- Per-class calibrated precision ≥ 0.9.
- Feature flag `ORCHESTRATOR_ROUTING_CLASSIFIER=1` (already enabled).
- Phase 2 hidden-state probe endpoint built; needs live test.
- Phase 4 (Trinity-derived) includes sep-CMA-ES cold-start, SVD-FT, block-ε-separability diagnostic.

### 3.2 Adjacent routing work

| Handoff | What it covers | Why it isn't this lineage |
|---|---|---|
| `learned-routing-controller.md` | MLP routing classifier, label-normalized SFT, hidden-state probe, Trinity Phase 4 | Inner-pool routing only; uses existing pretrained BGE encoder |
| `decision-aware-routing.md` | SPO+ / contrastive Q-scorer alignment; predict-then-optimize → decision-aware | Loss-function refinement of Q-scorer, not a new head |
| `outer-coordinator-learned-head.md` | Trinity-style learned head over Claude-driven outer loop | SCOPING ONLY; gated on tri-role + DAR landing |
| `routing-and-optimization-index.md` | Cross-cutting routing meta-coordination | Index document, no implementation |

### 3.3 Why HRM/TRM/GRAM don't cleanly map

| Property | HRM/TRM/GRAM (closed-world puzzles) | EPYC routing |
|---|---|---|
| **Input** | Token grids, vocab size 11–12 | 1024-d continuous BGE embedding from natural language |
| **Input size** | Fixed (81 / 900 / 196 tokens) | Variable-length natural-language requests |
| **Output** | Grid token reconstruction (vocab 11–12) | 5-way categorical role |
| **Training data shape** | 1K examples × 1000× augmentation | 174K labeled examples (no clear augmentation scheme) |
| **Train compute** | 1 L40S × 36hr (Sudoku) up to 4 H100 × 3 days (ARC-AGI) | Today: <1 min CPU on 174K samples |
| **Fixed-point structure** | Constraint satisfaction has a natural attractor | Routing has no obvious "iterate until convergence" semantics |
| **Inference cost** | 42 recursions × T=3 × 16 steps = 672 forward passes | Single 200K MLP forward pass (<1ms) |

The mismatch is **not** that recursion is bad for routing — it's that the recursion lever HRM/TRM/GRAM exploits (a closed-vocabulary fixed-point attractor with 1000× input augmentation) is not the lever routing offers (high-dimensional one-shot classification on natural language).

The mechanistic-analysis finding — *"this is pattern matching with iterative refinement, not reasoning"* — is interesting precisely because **routing is pattern matching**. But the question becomes: can iterative refinement of a routing decision buy us anything an MLP doesn't already capture? See §4.

---

## 4. Three concrete hypotheses for using these papers in EPYC routing

### Hypothesis A — TRM-as-router (the naïve port)

Replace the 200K-param MLP with a 7M-param TRM-style 2-layer recursive net trained end-to-end on the 174K routing labels.

| Aspect | Detail |
|---|---|
| **Input adapter** | 1024-d BGE embedding → tokenize into a synthetic "constraint grid" (e.g., 32×32 with embedding projections per cell)? Or skip tokenization entirely and feed embeddings as a single soft-token? No clear precedent. |
| **Output adapter** | TRM grid decoder → 5-way categorical over roles |
| **Training** | 174K labels, ~1 min CPU per epoch on the data we have today |
| **Inference cost** | 42 effective recursions × hidden=512 ≈ 21K state updates × 5–10ms = ~50–100× slower than current MLP |
| **Expected accuracy** | Unknown; Occam's razor says MLP already saturates the signal at 92% |
| **Engineering cost** | 3–4 sessions to port the input adapter, adapt the SamsungSAIL repo to a CPU-only training mode, wire into the existing routing infrastructure |
| **Risk** | HIGH that latency wipes out any accuracy gain; HIGH that there is no accuracy gain (MLP is the saturating model on label-rich classification) |

**Verdict**: do not pursue. Trinity (sep-CMA-ES over a small head on top of a 0.6B backbone) is the more justified design point for routing — bigger backbone, smaller head, ES against terminal fitness. TRM's lever requires closed-vocabulary puzzles + 1000× aug, neither of which we have for routing.

### Hypothesis B — GRAM-multi-trajectory at inference

Use GRAM's width-scaling idea: sample N=10 parallel routing trajectories from a stochastic head, take the mode, fall through on disagreement.

| Aspect | Detail |
|---|---|
| **Already exists in degenerate form** | The current MLP + per-class threshold IS a degenerate multi-trajectory ensemble: 1 trajectory + a confidence gate. Multi-sample MC-dropout on the existing MLP would emulate this for free. |
| **What GRAM adds** | A *trained* variational posterior that diversifies trajectories on purpose (rather than dropout noise). Useful for multi-solution tasks like N-Queens. |
| **Routing analogue** | Routing rarely has multiple equally-valid actions (rare ties). Most decisions have a single right answer. The "coverage" benefit GRAM demonstrates on N-Queens doesn't obviously apply. |
| **Engineering cost** | LOW: implement MC-dropout over the existing MLP first as a cheap proxy. If it materially improves precision/recall, then consider a trained variational head. |
| **Risk** | MEDIUM that MC-dropout buys anything over deterministic argmax at 92% val acc; LOW that further variational training pays off on top of MC-dropout. |

**Verdict**: cheap proxy first (MC-dropout). If the proxy moves the needle, escalate to a variational head. If it doesn't, this hypothesis is closed.

### Hypothesis C — GRAM-as-verifier (the genuinely novel framing) ★

Don't replace the router. Use a TRM/GRAM-style small recursive net as a **per-decision verifier** that takes `(request_embedding, proposed_action)` and emits `P(action is correct)`.

| Aspect | Detail |
|---|---|
| **Why this is novel** | Today's router has no separate verifier — confidence comes from softmax magnitude over the same MLP head. A distinct verifier head trained on a distinct objective (correctness prediction, not class prediction) is a real architectural advance. |
| **Why the recursive framing fits** | A verifier IS a constraint-satisfaction problem: "given the proposed action, do the implicit constraints (quality > threshold, cost OK, escalation unlikely) hold?" This is exactly the closed-world puzzle structure HRM/TRM/GRAM target. |
| **Training data** | 10,528 positive escalation memories (MLP was wrong) + 56,457 negative (MLP was right). Per the existing handoff: labels exist, classifier already trained on them. |
| **Architecture sketch** | 1024-d BGE embedding ⊕ 5-d one-hot action → small recursive net (7M–10M params) → scalar P(correct). N=4 parallel trajectories give a calibrated probability via majority vote. |
| **Inference cost** | Verifier only fires when MLP is moderately confident (i.e., would have routed). N=4 × ~250 forward passes × small net ≈ 2–5ms CPU. Adds <5% to current routing latency, only on the MLP fast-path. |
| **Wiring** | MLP top class → verifier → high P(correct) ⇒ route via MLP / low P(correct) ⇒ fall through to FAISS KNN. Replaces the per-class confidence threshold with a learned verifier. |
| **Engineering cost** | 4–6 sessions: design + port + train + A/B vs existing per-class-threshold gate |
| **Risk** | MEDIUM. The verifier may or may not improve recall over the existing confidence threshold. It's a real experiment, not an obvious win. |
| **Expected ROI** | HIGH if it works (a per-decision verifier is a primitive missing from every routing handoff today); LOW if it doesn't (we lose ~5 sessions of work). |

**Verdict**: scope first (no code, no model). Write a 1-session scoping document that answers:
1. Is the existing per-class threshold + FAISS-fallback already doing what a verifier would do?
2. What's the calibration target — Platt-scaled P(correct), or a margin-style score?
3. Can a 200K-param MLP verifier do this without going to a 7M recursive net? (Occam's razor — if yes, no recursion needed.)
4. If recursion does buy something, is N>1 trajectory sampling load-bearing or can we get away with deterministic recursion?

If the scoping document indicates a verifier is materially distinct from existing gates, this becomes a Phase 6 task under `learned-routing-controller.md` or a new sub-handoff. If not, archive the idea.

---

## 5. Decision matrix

| Option | Engineering cost | Risk | Expected ROI | Decision |
|---|---|---|---|---|
| Continue planned Phase 2 hidden-state probe | 2–3 sessions (already planned) | LOW | MEDIUM | Continue as-is |
| Continue planned Phase 4 Trinity sep-CMA-ES (cold-start, P4.4) | ~10h overnight (already scoped) | MED-HIGH | HIGH for cold-start surfaces | Continue as-is |
| **Hypothesis A — TRM-as-router** | 4–5 sessions | HIGH | LOW | **Do not pursue** |
| **Hypothesis B — GRAM multi-trajectory via MC-dropout proxy** | 1 session (MC-dropout); 4–6 sessions if escalated to trained variational head | LOW for proxy; MED if escalated | LOW–MED | **Cheap proxy first, escalate only if proxy moves needle** |
| **Hypothesis C — GRAM-as-verifier (scoping only)** | 1 session (scoping) | LOW | HIGH if it survives scoping | **Scope first, no code** |

---

## 6. Recommended position

1. **Do not branch a new TRM/HRM/GRAM-as-router handoff.** The lineage is interesting but the architectural lever (closed-vocabulary fixed-point recursion + 1000× input aug) is mis-matched to natural-language routing. Trinity (intake-474, already in Phase 4 of `learned-routing-controller.md`) is the more justified prior art for the same problem.

2. **Do ingest the mechanistic-analysis paper** (arxiv:2601.10679, intake-585) — it is direct Tier 2b on HRM, materially changes the interpretation of the lineage, and produces the Augmented-HRM training recipe (data augmentation + input perturbation + model bootstrapping) which IS portable if we ever attempt the Hypothesis A port.

3. **Do scope Hypothesis C (GRAM-as-verifier) as a 1-session no-code task** under `learned-routing-controller.md` Phase 6 or as a sub-handoff. The verifier framing is genuinely missing from today's routing roadmap — neither `learned-routing-controller.md`, `decision-aware-routing.md`, nor `outer-coordinator-learned-head.md` proposes a per-decision verifier trained on correctness labels. If the scoping doc concludes the existing per-class threshold subsumes a verifier, archive the idea; if not, escalate.

4. **Do cheap MC-dropout proxy for Hypothesis B** (1 session) the next time the MLP is being retrained anyway. If multi-pass dropout over the existing MLP materially improves precision/recall, the empirical case for a trained variational head strengthens.

5. **Do not chase TRM-as-router (Hypothesis A).** Estimated payoff is dominated by Trinity-style designs we already plan to evaluate, and current MLP saturates the available signal at 92% on 174K labels.

---

## 7. Open questions

1. **Verifier vs decision-aware**: does the `decision-aware-routing.md` SPO+ / contrastive Q-scorer work (DAR-2 onwards) already do what Hypothesis C proposes from the other end? DAR sharpens *which action is best*; a verifier predicts *whether the proposed action is correct*. They're related but not the same loss. Worth a 1-paragraph audit before committing to scope Hypothesis C separately.

2. **Trinity Phase 4 overlap**: `learned-routing-controller.md` Phase 4.4 (sep-CMA-ES cold-start) and a hypothetical Hypothesis C verifier would both consume eval-tower fitness signals if a verifier were trained via ES. Is there a unified workstream here, or should Hypothesis C live entirely in the SFT-on-escalation-memories regime?

3. **Should we re-open mechanistic Augmented-HRM** (intake-585) for an honest second-pass benchmark of HRM in our intake? HRM (intake-584) is now in our index with mid-tier credibility — the augmented-HRM result (54.5% → 96.9% on Sudoku-Extreme from data tricks alone) deserves explicit cross-reference, which intake-585 will provide.

4. **GRAM code availability**: monitoring https://ahn-ml.github.io/gram-website/ for code/checkpoint release. If checkpoints land, a 1-session port to llama.cpp / GGUF + EPYC bench would let us validate the lineage on its native task before committing to a routing experiment.

---

## 8. Sources

- [GRAM (intake-582) arXiv](https://arxiv.org/abs/2605.19376) · [project page](https://ahn-ml.github.io/gram-website/) · [OpenReview](https://openreview.net/forum?id=Vxu6kcIjwV)
- [TRM (intake-583) arXiv](https://arxiv.org/abs/2510.04871) · [official code (Samsung SAIL Montreal)](https://github.com/SamsungSAILMontreal/TinyRecursiveModels) · [community port (lucidrains)](https://github.com/lucidrains/tiny-recursive-model)
- [HRM (intake-584) arXiv](https://arxiv.org/abs/2506.21734) · [official code (Sapient)](https://github.com/sapientinc/HRM)
- [Augmented-HRM mechanistic analysis (intake-585) arXiv](https://arxiv.org/abs/2601.10679)
- [Trinity deep-dive (intake-474)](trinity-evolved-llm-coordinator-methodology.md)
- [Curriculum-Guided Adaptive Recursion for TRM (follow-up, not yet ingested)](https://arxiv.org/abs/2511.08653)
