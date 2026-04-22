# OneVL: Dual-Objective Latent Compression — Deep Dive

**Intake ID**: intake-443
**Paper**: OneVL: One-Step Latent Reasoning and Planning with Vision-Language Explanation
**arXiv**: 2604.18486
**Source**: https://ar5iv.org/abs/2604.18486
**Ingested**: 2026-04-20
**Tier assessment**: Tier 2b (indirect relevance; training pattern transferable, domain-specific results)
**Related intake**: intake-134 (CoLaR), intake-218 (Memento KV), intake-409 (context-folding)

---

## 1. Abstract

OneVL proposes a latent chain-of-thought (CoT) architecture for
autonomous-driving planning that compresses explicit multi-step reasoning into
six latent tokens — four visual, two language — injected into the main
transformer's prefill. Unlike prior latent-CoT work (CoLaR, Coconut), OneVL
trains the latent bottleneck with **two auxiliary decoders**: a language
reconstruction head (forces latent tokens to preserve textual reasoning
content) and a world-model head (forces latent tokens to predict future
frames, i.e. causal planning content). Both decoders are **discarded at
inference** — only the latent tokens and the main planning head remain. On
NAVSIM, OneVL reaches PDM 88.84 (vs 87.30 AR-CoT baseline) with 4.46s latency
(vs 6.58s), improving ROADWork, Impromptu, and APR1 simultaneously. The key
transferable insight is architectural: **dual-objective training produces
better latent compression than single-objective**, and the prefill-only
inference pattern means the auxiliary training cost does not carry into
deployment. For EPYC, this suggests Phase 2b context-folding could benefit
from a second auxiliary training objective even though our domain is
text-only.

---

## 2. OneVL Mechanism

### 2.1 Architecture at a glance

OneVL is an end-to-end driving policy built on a vision-language backbone
(InternVL-class). The forward pass is structured as:

```
[image tokens] [instruction tokens] [4 latent vis] [2 latent lang] -> [plan tokens]
                                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                       latent CoT bottleneck
                                   (replaces explicit CoT text)
```

During **training**, two auxiliary heads attach to the latent block:
- **Language decoder** (L_lang): reconstructs the explicit CoT text tokens
  that the latent should represent (teacher-forced from a CoT ground truth).
- **World-model decoder** (L_world): predicts future frame embeddings /
  tokens from the latent block (causal planning signal).

During **inference**, both auxiliary decoders are removed from the graph.
The latent tokens are produced by the shared encoder pathway and consumed by
the main plan decoder. The supervision signal has baked the dual-objective
information into the latent representation at training time.

### 2.2 The six-token bottleneck

Four visual + two language tokens total 6 tokens. Compared to an AR-CoT
baseline emitting ~120–200 explicit reasoning tokens per decision, this is
~20–40x compression at inference. The visual/language split is deliberate:

- **Visual tokens (4)**: scene-level spatial reasoning — where the agent
  vehicle is, what obstacles exist, free space estimates.
- **Language tokens (2)**: abstract intent / policy commit — the discrete
  "turn right, yield, proceed" type of symbolic decision.

This is more structured than CoLaR's uniform latent buffer; the split
mirrors the dual-decoder supervision structure.

### 2.3 Three-stage training

OneVL uses a staged curriculum:

1. **Stage 1 — Warm-start**: freeze backbone, train latent projection +
   both auxiliary decoders on paired (image, CoT text, future frames)
   supervision. Latent tokens are initialized to match text + world
   reconstruction.
2. **Stage 2 — Joint**: unfreeze backbone, train L_lang + L_world + L_plan
   jointly with balancing weights. The latent tokens now carry gradient from
   three objectives simultaneously.
3. **Stage 3 — Plan-dominant**: reduce auxiliary weights, fine-tune plan
   head and latent projection on plan supervision. Auxiliary heads are still
   present for regularization but their gradient contribution is smaller.

At inference, only the backbone + latent projection + plan head remain. The
language and world-model decoders are dropped entirely — zero inference cost.

### 2.4 Prefill-only inference

The critical inference optimization: latent tokens are produced in a single
forward pass as part of prefill, not autoregressively. Prior AR-CoT
baselines must decode 120–200 tokens sequentially before producing the
plan; OneVL produces 6 latent tokens in parallel during prefill, then
decodes the short plan. This is the source of the 4.46s vs 6.58s latency
gain.

The structural property: **the auxiliary objectives constrain the
representation but not the compute path at inference**. This decoupling is
the architectural trick.

---

## 3. Key Insight

### 3.1 Dual-objective > single-objective for latent compression

The paper's strongest empirical claim: when they ablate to a
single-objective variant (L_lang only, world-model removed), latent quality
degrades and PDM drops. Removing L_lang (world-model only) also degrades
quality. Both objectives are needed, and the combination outperforms either
alone by more than additive margin.

**Mechanism**: L_lang pulls the latent toward preserving text-level logical
structure (what would a human explain). L_world pulls the latent toward
predicting causal consequences (what will happen). The two objectives are
complementary — logical consistency + causal grounding — and training
under both constraints produces a latent that is more generalizable than
either pressure alone.

### 3.2 Why this matters for compression in general

Prior latent-compression work (CoLaR, Coconut, some OPSDC variants) uses a
single reconstruction objective: either the latent must reconstruct the
text, or the latent must drive the downstream decision. This is a
single-pressure bottleneck, and the resulting latent tends to overfit to
whichever signal dominated.

OneVL's result suggests that any latent compression scheme can benefit from
adding a second, complementary objective. The second objective doesn't need
to be world-model prediction specifically — it just needs to be
non-redundant with the primary one and tied to downstream utility.

### 3.3 Causal grounding as generalization pressure

The world-model objective specifically forces the latent to encode
**causal** information — what will change in the environment as a
consequence of the chosen action. Encoding this into the latent means the
latent carries counterfactual structure, which in turn means it generalizes
to scenarios where the surface-level text description differs but the
causal structure is similar. This is the paper's explanation for why OneVL
outperforms AR-CoT even on held-out ROADWork and Impromptu splits.

---

## 4. Reported Results (Autonomous Driving Domain)

### 4.1 NAVSIM benchmark

| Method | PDM score | Latency |
|---|---|---|
| AR-CoT baseline | 87.30 | 6.58s |
| OneVL (dual-obj) | **88.84** | **4.46s** |
| OneVL (L_lang only) | 87.6* | 4.5s |
| OneVL (L_world only) | 87.1* | 4.5s |

*Approximate ablation numbers from the paper's ablation table.

OneVL improves PDM by 1.54 points while simultaneously reducing latency by
32%. Both axes improve — the compression is net-positive, not a
latency/quality tradeoff.

### 4.2 Additional benchmarks

- **ROADWork** (held-out construction/roadwork scenarios): OneVL beats
  AR-CoT by ~2 points on scenario-level success.
- **Impromptu** (unscripted dynamic agent behavior): OneVL improves
  collision avoidance rate by 1.8 points.
- **APR1** (adversarial planning robustness): OneVL improves over
  single-objective ablations by 0.9 points, suggesting the dual-objective
  structure specifically helps with OOD/adversarial scenarios.

### 4.3 Ablation summary

The ablation pattern is consistent across all four benchmarks:
- Dual-objective > L_lang only > L_world only > no auxiliary (plan-only).
- The "plan-only" baseline matches a naive latent-CoT and performs worst —
  confirming that latent compression without explicit reconstruction
  pressure under-performs even explicit AR-CoT.

This is a strong experimental signal that the auxiliary objectives are
doing meaningful work, not just acting as regularizers.

---

## 5. Why This Is Relevant Despite the Domain Gap

### 5.1 The domain gap

OneVL operates in autonomous driving with video input and geometric action
output. EPYC's reasoning/compression stack operates on text-only reasoning
traces. A literal port is not possible: we don't have "future frames" to
predict.

However, the **structural pattern** transfers:

### 5.2 Our compression stack is single-objective

- **Context-folding Phase 2a/2b**: summarizer trained/prompted to produce
  short summaries scored by helpfulness (single objective — "is this
  summary helpful to the downstream task?"). No secondary pressure for
  causal/structural content.
- **Reasoning-compression Tier 3 (OPSDC, CoLaR variants)**: latent
  compression trained under a single reconstruction objective. CoLaR in
  particular uses a single autoencoder-style latent loss.
- **Memento KV compression**: also single-objective (KV reconstruction
  fidelity).

All of these are single-pressure bottlenecks, exactly the regime OneVL
argues under-performs.

### 5.3 What OneVL suggests for our stack

If dual-objective training consistently beats single-objective in a
different domain, and the mechanism (two complementary pressures produce a
more generalizable latent) is domain-agnostic, then our stack should at
minimum evaluate whether a second auxiliary objective helps. This is
especially true for Phase 2b, which is still in design.

---

## 6. Amend / Expand / Confirm

### 6.1 Confirm

**Does OneVL reinforce the "latent compression > text compression"
finding from CoLaR and Memento?**

Yes, with a caveat. OneVL's plan-only baseline (latent without auxiliary
reconstruction) performs worse than AR-CoT — which is consistent with the
CoLaR/Memento finding that naive latent compression under-performs. But
OneVL's full dual-objective variant beats AR-CoT. So the refined claim is:

> Latent compression with sufficient training pressure (ideally
> multi-objective) beats text compression. Latent compression with
> insufficient training pressure loses to text compression.

This is an important correction. It suggests that **training signal
quality**, not latent-vs-text per se, is the dominant factor. Our existing
context-folding Phase 2b should prioritize training signal richness over
architectural choice of latent-vs-text.

### 6.2 Amend

**Does single-objective training in our existing stack under-perform what
dual-objective training could achieve?**

Likely yes, based on the strength of OneVL's ablations. The ablation
magnitude (dual-obj +1.5 PDM over L_lang-only) is substantial and
consistent across benchmarks. A 1–2 point quality gain on summarizer
output quality, if achievable, would meaningfully move
context-folding Phase 2b metrics.

**Should Phase 2b design add a second auxiliary objective?**

Recommend **yes, as a design variant to evaluate**. Specifically:
- Phase 2b currently plans a summarizer trained/prompted on helpfulness-
  scored outputs.
- A dual-objective variant would add a second head during training
  that predicts a complementary signal — e.g. task-success or tool-call
  correctness — from the summarizer's latent/hidden state.
- At inference, the second head is discarded (OneVL pattern).

This amendment should be added to the Phase 2b design document as an
experimental variant, not a default, until we can GPU-train and validate.

### 6.3 Expand

**What candidate second objectives exist for text-only reasoning?**

Concrete candidates, ordered by feasibility:

1. **Task-success prediction**: given the summarizer's hidden state,
   predict whether the downstream agent completed the task. Signal is
   available from existing eval runs. Binary classification head.
2. **Eval pass/fail prediction**: given hidden state, predict whether the
   next eval check will pass. Richer than task-success because intermediate
   eval outcomes are available.
3. **Tool-call correctness prediction**: given hidden state, predict
   whether the next tool call will succeed. Available from tool-call
   traces we already log.
4. **Next-action success prediction**: closer to OneVL's world-model —
   predict whether the next action produces a measurable state change in
   the expected direction.
5. **Retrieval-relevance prediction**: given hidden state, predict whether
   a specific strategy-store entry would be retrieved as relevant.

Option (2) — eval pass/fail — is probably the strongest because we
already log these outcomes densely, and the signal is directly tied to our
existing quality metric. Option (4) is closest to OneVL's original design
but requires an environment model we don't have.

**What other patterns could serve as the second objective?**

- **Consistency objectives**: two latent views of the same input must
  agree. Cheap, domain-agnostic, well-studied (BYOL-style).
- **Contrastive objectives**: latent for a successful trajectory must be
  distinguishable from latent for a failing one. We have paired
  success/failure data from autopilot runs.
- **Reconstruction-to-different-granularity**: latent must reconstruct
  both a short summary AND a long-form trace. Forces multi-scale
  representation.

Of these, the contrastive success/failure objective is the cheapest to
add to an existing training pipeline and has the strongest theoretical
motivation for generalization.

---

## 7. Prefill-Only Inference Pattern

### 7.1 The architectural insight

The inference-time cost of OneVL is:
- Main backbone forward pass (once, standard)
- Latent projection (cheap, ~6 tokens of computation)
- Plan decode (short)

It does **not** include:
- Language decoder forward pass (dropped)
- World-model decoder forward pass (dropped)

The auxiliary decoders are pure training-time infrastructure. This is the
dual-objective version of a classic distillation pattern: teacher (with
auxiliary heads) trains student representation; student (without heads) is
deployed.

### 7.2 Application to context-folding Phase 2b

**Could we train a summarizer whose summarization head is discarded at
inference?**

The OneVL pattern, translated:
- Train summarizer to produce a **latent state** (not an explicit text
  summary).
- Attach during training: (a) a text-reconstruction head that produces
  the explicit summary, (b) a task-success prediction head that predicts
  downstream eval outcome.
- At inference, discard both heads. Inject the latent state directly into
  the main agent's context.

This would match OneVL's prefill-only pattern exactly. The main agent's
prefill absorbs the latent state; no intermediate summary decode. Latency
gains would be proportional to summary length (our summaries are ~200–500
tokens, so skipping that decode is meaningful).

### 7.3 Caveats

- The main agent must be trained jointly (or at least fine-tuned) to
  consume the latent state. You can't inject latent tokens into a frozen
  off-the-shelf LLM and expect it to use them well. OneVL trains the
  backbone to consume its latent block; we would need the same.
- This conflicts with our current "use off-the-shelf Qwen/GLM" stance. A
  full Phase 2b latent version would require custom fine-tuning.
- Our existing text-based Phase 2a (helpfulness-scored summary) is
  deployable today with no fine-tuning. A latent Phase 2b is a research
  direction, not a near-term deployment.

### 7.4 Hybrid middle-ground

A middle-ground: keep the text summary at inference (no latent), but train
the summarizer with a dual-objective signal (text reconstruction +
downstream task success prediction). This captures OneVL's training-time
benefit without requiring latent-token injection into the main agent. This
is probably the most practical path for EPYC.

---

## 8. Training Requirements

### 8.1 Compute

OneVL's three-stage training is heavy:
- Stage 1 warm-start: ~hundreds of GPU-hours (auxiliary decoder training
  with frozen backbone).
- Stage 2 joint: full-backbone fine-tune, several thousand GPU-hours.
- Stage 3 plan-dominant: smaller fine-tune, ~hundreds of GPU-hours.

Scaled down to a text-reasoning analog with a smaller backbone (e.g.
Qwen-3 14B or 30B-A3B), we'd expect single-GPU or 2-GPU weeks of training,
not the full OneVL budget — but still substantial.

### 8.2 EPYC hardware context

CPU-only EPYC can't run this. Per user_hardware.md and
project_dgx_spark_target.md, DGX Spark (GB10) has not yet been acquired.
Training is blocked on hardware.

### 8.3 When DGX Spark arrives

Once DGX Spark is available, dual-objective summarizer training becomes a
candidate Phase 2c+:
- Phase 2c: single-objective summarizer fine-tune (baseline establishment).
- Phase 2d: dual-objective summarizer fine-tune (OneVL-style).
- Comparison: does the dual-objective variant measurably improve
  summary quality / downstream task success?

Timeline: deferred until DGX Spark lands. In the interim, experiment
proposals should be training-free probes (Section 9).

---

## 9. Concrete Experiment Proposal (Training-Free)

### 9.1 Hypothesis

**H1**: If summarizer outputs are scored with a second complementary
objective (beyond helpfulness), and that score is used as a regularizer in
strategy-store retrieval, downstream task success improves.

**H2**: Summaries that score well on both objectives (helpfulness AND
task-success predictor) are more reusable across tasks than summaries that
score well on only one.

### 9.2 Design

We do not train new models. We reuse existing components:

1. **Summarizer output corpus**: pull last N autopilot runs' summaries
   from strategy_store / checkpoint archives.
2. **Primary scorer**: existing helpfulness scorer (already in Phase 2a).
3. **Secondary scorer**: task-success classifier. Implementation options:
   - (a) Prompt-based: ask a judge LLM "given this summary, how likely is
     the downstream task to succeed?" on a 0–10 scale.
   - (b) Retrieval-based: for each summary, retrieve runs where a similar
     summary was produced, and compute the empirical task-success rate
     over those runs. Bootstrap from existing autopilot logs.
4. **Combined score**: `s = α·helpfulness + (1-α)·task_success_pred`.
   Sweep α ∈ {0.0, 0.25, 0.5, 0.75, 1.0}.
5. **Evaluation**: use the combined score to rank strategy-store entries
   for retrieval. Measure downstream task success rate on a held-out
   autopilot eval set.

### 9.3 Expected signal

- If α=1.0 (helpfulness only) performs best, the dual-objective hypothesis
  does not replicate in our domain and we defer further investigation.
- If some α<1.0 outperforms α=1.0, this is evidence that adding a
  complementary objective helps even when the addition is just at scoring
  time (not training time). This would motivate a full Phase 2c training
  experiment.
- Magnitude: if we see >2% downstream task success improvement, that
  justifies the training investment later.

### 9.4 Cost

Compute-cheap: scoring a few hundred summaries with an LLM judge is under
a few hours of inference on our existing stack. Can be run in parallel with
other work. No training, no GPU requirement.

### 9.5 Risks

- The secondary scorer is noisy. A prompted judge LLM's task-success
  prediction is imperfect and may just add variance without signal.
- The summaries in our corpus were all produced under a single-objective
  training regime. A training-time dual-objective effect (OneVL's actual
  claim) may not show up at scoring time alone.
- Selection bias: summaries in strategy_store have already been filtered
  by helpfulness; the remaining variation on task-success may be small.

Mitigation: include failing-run summaries (not just strategy_store entries)
in the corpus to broaden the distribution.

---

## 10. Risks & Tier 2b Classification

### 10.1 Domain-specific results

OneVL's improvements are measured exclusively in autonomous driving
benchmarks. The world-model objective is specifically video-frame
prediction. There is no published evidence that the dual-objective pattern
transfers to text-only reasoning. The mechanism argument (two
complementary pressures) is general but unvalidated outside the driving
domain.

### 10.2 World-model supervision may be essential

The paper's world-model objective is unusually rich: each training example
provides a dense future-frame target. Text-only reasoning may not have a
comparable rich secondary signal available. Our candidate secondary
objectives (task-success prediction, eval pass/fail) are much lower-
bandwidth than future-frame prediction. It is plausible that the
dual-objective benefit scales with the richness of the second signal, and
our thin binary task-success signal may not be enough.

### 10.3 Prefill-only pattern requires joint training

The prefill-only inference pattern requires that the main backbone was
trained to consume the latent block. We can't retrofit this onto a frozen
off-the-shelf Qwen / GLM backbone. Adopting the pattern costs us our
current deployment simplicity.

### 10.4 Three-stage training is fragile

Staged curricula are notoriously hyperparameter-sensitive. OneVL's paper
reports a single successful configuration; replication difficulty is
unknown. Our own staged-training attempts would need significant hparam
sweeping.

### 10.5 Tier classification rationale

**Tier 2b (indirect relevance)** because:
- Structural pattern (dual-objective training, prefill-only inference) is
  transferable and motivates concrete experiments in our stack.
- Domain and compute requirements mean no direct reuse.
- Training-free probe proposal (Section 9) is cheap to run and gives us a
  quantitative signal on whether to escalate to Tier 2a.

If the Section 9 experiment shows positive signal, OneVL promotes to Tier
2a and the dual-objective training becomes a high-priority Phase 2c+
research direction.

---

## 11. Cross-References

### 11.1 Active handoffs

- `/workspace/handoffs/active/context-folding-progressive.md` — Phase 2b
  design should include a dual-objective variant as an experimental path.
  Current Phase 2a is single-objective (helpfulness-scored). Amendment
  captured in Section 6.2.
- `/workspace/handoffs/active/reasoning-compression.md` — Tier 3 latent
  compression (OPSDC, CoLaR) should be re-evaluated under the
  single-vs-dual objective framing. OneVL suggests Tier 3's
  under-performance may be training-signal related, not architecture
  related.
- `/workspace/handoffs/active/memento-block-reasoning-compression.md` —
  KV-level compression is single-objective (reconstruction). Memento and
  OneVL together suggest a dual-objective KV compression variant (e.g.
  reconstruction + downstream-task-signal prediction from compressed KV)
  is worth prototyping when GPU arrives.

### 11.2 Research deep dives

- `/workspace/research/deep-dives/colar-latent-compression.md` — CoLaR is
  a direct single-objective predecessor. OneVL's dual-objective
  contribution can be read as "CoLaR + world model head". Reading both
  together clarifies the contribution space.
- `/workspace/research/deep-dives/memagent-rl-memory.md` — MemAgent's
  RL-based memory update is another single-objective (task-return)
  formulation. OneVL-style auxiliary losses could plausibly regularize
  MemAgent memory representations too.
- `/workspace/research/deep-dives/memento-iterative-reasoning-cluster.md`
  — Memento family is latent/KV compression; similar single-objective
  critique applies.

### 11.3 Wiki entries

- `/workspace/wiki/context-management.md` — Add a compiled summary of the
  dual-objective latent compression pattern with pointer to this deep dive.
- `/workspace/wiki/memory-augmented.md` — Note OneVL as evidence that
  latent memory representations benefit from multi-objective training.

### 11.4 Open questions for follow-up intake

- Are there text-only reasoning papers that have validated the
  dual-objective latent pattern? (Worth a targeted literature probe —
  the keyword "auxiliary decoder" + "latent reasoning" should surface
  related work.)
- What is the minimum richness of the secondary objective for the pattern
  to work? (Theoretical question; informs whether our thin binary
  task-success signal is enough.)
- Is there a theoretical treatment of why two complementary objectives
  produce more generalizable latents? (Information-bottleneck /
  multi-task-learning literature likely has this.)

---

## 12. Summary Recommendation

**Dual-objective latent compression belongs in the EPYC roadmap — deferred.**

- Immediate: run the Section 9 training-free probe (α-sweep scoring
  experiment). Cost: hours of inference, no training.
- Near-term (Phase 2b design doc): add dual-objective training as an
  experimental variant with explicit deferral to post-DGX-Spark.
- Post-DGX-Spark: Phase 2c/2d dual-objective summarizer fine-tune as a
  candidate Phase 2c+.
- Long-term: if validated in our domain, extend to reasoning-compression
  Tier 3 and Memento-family KV compression.

The prefill-only inference pattern is architecturally elegant but requires
joint backbone training; defer until we have both GPU compute AND a
validated quality signal from the training-free probe.

---

**Deep-dive author**: Claude (opus-4-7, 1M context)
**Date**: 2026-04-20
**Review status**: initial draft, pending user approval for handoff updates
