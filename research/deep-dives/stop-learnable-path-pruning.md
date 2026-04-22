# Deep Dive: STOP — Learning to Prune Paths Early for Efficient Parallel Reasoning

**Paper**: "Cut Your Losses! Learning to Prune Paths Early for Efficient Parallel Reasoning"
**ArXiv**: 2604.16029 (ar5iv.org/abs/2604.16029)
**Intake**: intake-437
**Date**: 2026-04-22
**Status**: feasibility probe (pre-decision)

---

## 1. Abstract

STOP (Super TOken for Pruning) introduces a single **learnable token** inserted at the prefix position of a reasoning trace that acts as an early-exit arbiter for parallel reasoning samples. During multi-sample generation (best-of-k, majority@k, tree search), STOP scores each branch shortly after divergence and prunes those whose prefix tokens already encode signs of unproductive exploration — compounding error, topic drift, or wasted backtracks — before the tail of the chain is generated. The authors report GPT-OSS-20B AIME25 climbing from 84% → 90% accuracy under a fixed token budget, with consistent gains across the 1.5B–20B scale range. The paper also contributes the **first systematic taxonomy of path pruning** along two axes: *signal source* (internal to model vs external verifier) × *decision policy* (learned head vs heuristic rule). Relative to EPYC's existing Tier 1 / Tier 2 / Tier 3 reasoning-compression stack, STOP is an **internal-signal, learnable** technique — a quadrant we currently do not cover. It is compositional with TrimR, conciseness prompts, difficulty bands, and the length alarm, not a replacement.

## 2. STOP Mechanism

### 2.1 The super-token

STOP augments the tokenizer with a **single new learnable token** — call it `<STOP>` — whose embedding is trained. At inference time, the prompt is tokenized as:

```
[system] ... [user] ... <STOP> <assistant_prefix>
```

The super-token is positioned **after the user turn but before the assistant generation begins**. Its role at inference is not to be emitted as output — it is a *probe position* whose hidden state carries an aggregated representation of the upcoming reasoning trajectory (via the standard causal-attention induction from prompt to that position). A lightweight **scoring head** (a linear or shallow-MLP projection) reads the `<STOP>` hidden state and produces a "productivity score" per sample.

### 2.2 Training objective

`<STOP>` is optimized jointly with a scoring head on reasoning traces labeled by whether they ultimately produced a correct final answer. The gradient flows only through the `<STOP>` embedding and the scoring head — the backbone remains frozen (this keeps adoption costs low). The authors use a per-sample binary cross-entropy plus a pairwise ranking loss so that within a batch of k samples for the same question, the scoring head orders them by eventual correctness. Negative samples come from incorrect rollouts; positive samples come from correct rollouts. The loss shapes the `<STOP>` embedding such that, conditioned on the prompt, the model's own prefix computation surfaces a discriminative productivity signal at this probe.

### 2.3 Use at inference

Given k parallel samples for the same prompt, the procedure is:

1. Generate up to a *commit budget* C tokens per sample (typical: C = 32–128 tokens — far below the full reasoning chain length).
2. Read the scoring head output at the `<STOP>` position — or, if the head reads from *a specific downstream position* tied to the first reasoning step, wait until that position is reached.
3. Rank the k samples by productivity score.
4. **Prune** the bottom fraction (1 − α) of samples; continue generation only for the top α.
5. Final answer is taken from the surviving sample(s) via the existing aggregation (majority@m, best-of-k, or argmax).

The critical property: pruning happens *after* a tiny prefix is generated, not before. This matters because the divergence between "productive" and "doomed" branches often shows up only after 1–2 reasoning steps — e.g., an early arithmetic error or an incorrect factoring choice deterministically dooms the remaining chain.

### 2.4 First systematic taxonomy

The paper's taxonomy organizes path pruning along two axes:

| | **Learnable policy** | **Heuristic policy** |
|---|---|---|
| **Internal signal** (from model's own activations / logprobs) | STOP (this paper), COIN | Length-alarm (our Action 9), logprob thresholds, entropy spikes |
| **External signal** (from verifier, critic, or second model) | Process-reward models (PRMs), learned verifiers | TrimR (verifier + paragraph pruning), self-consistency voting |

This is the first deep-dive source we have that lays this out as a grid. Prior compression papers (OPSDC, FlowSteer, CoLaR, short-m@k, TrimR) each occupy one cell but do not relate themselves to the others along both axes.

The taxonomy additionally has a third (implicit) axis the paper underplays: **intervention timing**. STOP intervenes at the *prefix-selection* stage (after commit budget C, before full generation). TrimR intervenes at the *post-generation* stage (after the full chain is emitted). SEAL/FlowSteer intervene *during* generation (activation steering every `\n\n`). Length alarm intervenes *mid-generation* (at overrun). These four timings are orthogonal to signal source and policy form, and EPYC's deployed stack already touches all four — which means STOP is additive rather than substitutive.

### 2.5 Parallel-inference friendly

STOP is explicitly designed to reduce the cost of parallel reasoning (majority-vote, best-of-k, tree-of-thoughts). Because pruning happens after a small prefix, saved compute scales roughly linearly with k — at k=8, α=0.25, commit budget C=64 on a 4,000-token reasoning chain, the expected token savings is ≈ 73% relative to running all 8 samples to completion. The authors emphasize that STOP is *orthogonal* to the choice of aggregator (majority@m, self-consistency, PRM-best) because it only changes which samples make it to the end.

## 3. Reported Results

### 3.1 Headline claims

| Model | Task | Baseline | STOP | Δ | Compute |
|---|---|---|---|---|---|
| GPT-OSS-20B | AIME25 | 84% | **90%** | +6pp | Fixed token budget |
| Qwen2.5-14B | MATH | — | — | +3–4pp | Fixed token budget |
| DeepSeek-R1-Distill-Qwen-7B | GSM8K/MATH | — | — | consistent gain | — |
| 1.5B model | MATH | — | — | smaller but positive | — |

The central narrative is that STOP scales across 1.5B → 20B — the range that contains our worker (30B-A3B) and coder (Qwen3-Coder) tiers. The paper also shows STOP ≥ majority@k baselines at **equal or lower** token budgets.

### 3.2 Commit budget sensitivity

The authors show a small ablation: commit budget C in {16, 32, 64, 128, 256}. Productivity discrimination already emerges at C=32 on math tasks (where arithmetic errors are fast-visible), requires C=128 on code (where compilation-style error signals show up later), and degrades slightly if C is too small (C=16: not enough prefix for the probe to tell productive from unproductive).

### 3.3 Aggregator interaction

STOP composes with both majority@m and best-of-k. On MATH with k=8, majority@8 improves from X → X+3.1pp with STOP (survivors fewer but higher quality). On best-of-k, STOP shortens total generation time by 30–60% depending on α.

### 3.4 Caveats in the paper itself

- AIME25 is a 30-question set. +6pp is 2 questions. Confidence intervals are not given. Replication needed.
- The paper does not ablate *which layer's hidden state* feeds the scoring head — this is a non-trivial design choice.
- Training data provenance is partially described: they use correct/incorrect pairs from existing RL traces (OpenR1-Math-style). Training data *itself* was not released at submission.
- Baseline aggregator choice (majority@k vs best-of-k vs self-consistency) is not uniformly held across model sizes, making cross-scale comparison slightly noisy.
- Scaling results from 1.5B → 20B are reported on a mix of models whose pre-training data overlap with the eval sets is not disclosed. The 20B result (GPT-OSS) may be upper-biased if AIME-adjacent data is in pre-training.

### 3.5 What the paper does NOT claim

Useful to separate: STOP does not claim to *improve* the best sample. It claims to *select* the best sample cheaper. If the majority@k answer is wrong for fundamental reasons (e.g., prompt is beyond model capability), STOP cannot rescue it. This bounds the expected gains to the slack between majority@k and oracle@k — which, per the short-m@k paper's oracle numbers (up to 34.5pp gap), is large on reasoning tasks but near zero on tasks where all k samples agree by convergence.

## 4. Existing EPYC Reasoning-Compression Landscape — STOP Taxonomy Mapping

Our current stack (per `handoffs/active/reasoning-compression.md`) is organized by implementation effort. Mapped onto STOP's signal × policy grid:

### 4.1 Tier 1 — Zero-training, inference-time

| EPYC technique | Signal axis | Policy axis | Notes |
|---|---|---|---|
| TrimR (intake-127) | **External** (verifier/debug_scorer) | **Heuristic** (paragraph pruning rule) | Deploy-ready; GPQA 58.3 → 52.6 / 45.7 validates on hard tasks |
| short-m@k / length-alarm (Action 9) | **Internal** (own token count) | **Heuristic** (1.5× band budget threshold) | Deployed behind flag |
| Conciseness prompts (Actions 1, 12, 13) | — (pre-generation control) | — | Prompt-only, no policy head |
| Difficulty band (`difficulty_signal.py`) | **Internal-proxy** (prompt regex features, not activations) | **Heuristic** (weighted regex → threshold) | Shadow mode; NIB2-32 re-validation pending n≥100 new records |
| Band-adaptive token caps (Action 5) | Derived from difficulty band | Heuristic cap | Gated on difficulty `enforce` |
| N-gram loop detection (Action 4) | **Internal** (token stream) | **Heuristic** (3-gram/4-gram repetition threshold) | Deployed |

### 4.2 Tier 2 — Activation steering

| EPYC technique | Signal axis | Policy axis | Notes |
|---|---|---|---|
| FlowSteer (intake-126) | **Internal** (activations) | **Learned** (MLP velocity field) | Blocked on Qwen3.5 `build_cvec()` missing; SEAL linear baseline deployable for dense Qwen3 |
| SEAL control vectors | **Internal** (activations) | **Learned** (linear) | Generator prep done; awaiting model servers |
| S3-CoT | **Internal** (activations) | **Learned** (activation steering) | Incompatible with Qwen3.5 hybrid SSM |

### 4.3 Tier 3 — Training required

| EPYC technique | Signal axis | Policy axis | Notes |
|---|---|---|---|
| OPSDC (intake-110) | Self-distillation loss | Learned (policy update) | 8×H200 training; not currently actionable |
| CoLaR (intake-134) | Latent-space prediction | Learned (Latent Head MLP) | Full model retrain; only tested 1–1.5B |
| Memento cluster (intake-289/290/292/293/294) | Block boundaries + KV retention | Learned (SFT + RL) | vLLM-only; llama.cpp port non-trivial |

### 4.4 The gap

Our current stack has **no internal-signal, learnable, prefix-probe** technique. The closest is SEAL/FlowSteer, but those are *steering* interventions (they change the generation trajectory) rather than *selection* interventions (ranking parallel samples). We have no device for answering: "given a single prompt and an in-progress reasoning prefix from the model itself, is this branch worth finishing?" This is precisely STOP's niche.

## 5. Amend / Expand / Confirm

### 5.1 Confirm — Does STOP validate our layered approach?

**Yes, strongly.** STOP is compositional with every Tier 1 technique in our stack:

- Conciseness prompting shifts the length distribution before STOP gets to probe.
- Difficulty bands can gate *whether* STOP is invoked at all (cheap prompts do not need k samples).
- TrimR acts after generation; STOP acts after a short prefix. The two intervene at different pipeline stages.
- Length alarm (Action 9) re-rolls a single sample on overrun; STOP ranks across samples up-front. Orthogonal.
- N-gram loop detection fires during generation; STOP fires at a specific probe position. Orthogonal.

The paper's taxonomy also *explicitly* argues that combining techniques across the signal × policy grid is the productive direction — which is essentially the design-thesis of our handoff.

### 5.2 Amend — Does STOP REPLACE any existing technique?

For each existing Tier 1 technique, the compositional verdict:

| Existing technique | Verdict vs STOP | Rationale |
|---|---|---|
| **TrimR** | **COMPOSES WITH** | Different pipeline stage (prefix-selection vs post-hoc paragraph pruning). TrimR still runs on the survivor(s). |
| **short-m@k / length alarm** | **COMPOSES WITH** | Length alarm is a single-sample re-roll on overrun; STOP is multi-sample selection. Can run both. |
| **Conciseness prompts** | **COMPOSES WITH** | Prompt-level style control is upstream of any branch-selection policy. |
| **Difficulty signal** | **COMPOSES WITH** (gating role) | Difficulty band can decide *whether to spawn k samples at all*. Easy prompts: k=1 (no STOP). Hard prompts: k=4–8 (STOP active). This is a natural extension of enforce mode. |
| **Band-adaptive caps** | **COMPOSES WITH** | Cap is a hard budget; STOP chooses which sample gets the budget. |
| **N-gram loop detection** | **COMPOSES WITH** | In-flight loop detection fires independently of probe-time selection. |

None of our current techniques are **SUPERSEDED BY** STOP. STOP does not **REPLACE** anything.

### 5.3 Expand — Taxonomy coverage gap

Our stack has a hole in the **internal-signal × learnable** quadrant. Every one of our Tier 1 heuristics occupies the heuristic column; every one of our learnable techniques (FlowSteer/SEAL/S3-CoT) is a *steering* intervention, not a *selection* head. STOP is the first candidate for the internal-learnable-selection cell.

Also missing: we have no **external-signal × learnable** selection head (e.g., a trained PRM/verifier). Our only external signal is TrimR-style heuristic scoring. A learned PRM would be the natural external-signal counterpart to STOP.

Expansion recommendation: treat the `difficulty_signal.py` prompt-side predictor and a STOP-style prefix-side predictor as **two ends of the same axis**. Prompt-side difficulty is a zero-latency, high-noise estimator. Prefix-side STOP is a short-latency (C tokens), lower-noise estimator that benefits from having seen the model's own initial reasoning step. Together they form a **two-stage cascade**:

```
prompt → difficulty_signal → decide k, C, α → spawn k samples
       → generate C tokens  → STOP probe     → prune to α·k
       → full generation    → TrimR          → aggregate
```

## 6. Compositional Feasibility on EPYC

### 6.1 llama.cpp implementation requirements

STOP needs:

1. **A learnable added token** in the tokenizer/model vocabulary — requires extending the GGUF model file with one extra embedding row, OR inserting the super-token as a reserved unused token already in the vocab and just training its embedding. The second path is feasible in llama.cpp without format changes (Qwen3 has many reserved `<|unused_*|>` tokens).
2. **A scoring head** that reads a hidden state at the super-token position — llama.cpp has a logits head and an embeddings output. Reading per-layer hidden states at an arbitrary position can be done via the existing `--embeddings` path or the `llama_get_embeddings_ith()` API. A small external scoring head (linear or 2-layer MLP) running in our orchestrator's Python tier avoids modifying llama.cpp itself.
3. **A probe-and-decide loop**: generate C tokens for each of k samples, read the hidden state at the configured probe position, score, prune.

This is implementable entirely in the orchestrator layer. No llama.cpp C++ changes are strictly required if we use the reserved-unused-token path and run the scoring head in Python. This is a major advantage over FlowSteer (which needed an ODE solver inside the compute graph) and CoLaR (which needs dual-head inference inside the engine).

### 6.2 Composition with `difficulty_signal.py`

Natural. In enforce mode, the difficulty band becomes the gate:

- `easy` → k=1 (no STOP, no multi-sample cost)
- `medium` → k=2 or k=4 with STOP α=0.5
- `hard` → k=4–8 with STOP α=0.25, longer commit budget C

This preserves our existing single-sample worker path for cheap prompts and only incurs parallel-sample cost where it matters. It also creates the operational experiment we need for NIB2-32: the difficulty signal acts not only as a routing signal but as a *parallelism dial*.

### 6.3 Interaction with `<think>` reasoning-budget infrastructure

STOP's probe position can be placed *before* the first `<think>` token, *inside* the `<think>` block (after C tokens of thinking), or *at* `</think>`. Per our existing band-budget framework (Action 5), the most natural placement is *after* the first band-proportional chunk of thinking — e.g., probe at ¼ of the `easy` band (≈ 375 tokens), ¼ of `medium` (≈ 875), ¼ of `hard` (≈ 1,750). This gives STOP some think content to discriminate on while still leaving most of the budget for the survivors.

Compatibility with `</think>` stop sequences is good: our infrastructure already supports stop sequences mid-stream, so cancelling non-survivor streams at the probe point is the same operation as the length-alarm kill.

### 6.4 CPU inference-time cost

On our EPYC CPU setup, the dominant cost is **running k samples in parallel**, not the scoring head itself. Scoring is one forward-pass-ish computation per sample at the probe position, which we already have because we have generated the prefix. The scoring head (linear 1×d_model → 1) is negligible at CPU speeds (microseconds).

The real constraint: CPU inference throughput scales with NUMA node count, not "free parallelism" like a GPU. k parallel samples either:
(a) share a single server with `-np k` (slots), which we already do for the worker tier with `np=2–4`, or
(b) dispatch to multiple worker-tier servers with different model weights (weakens majority voting — not recommended for STOP).

For the worker tier (30B-A3B) running with `-np 2–4` on NUMA-bound slots, STOP with k=2–4 is native. For architect-tier models that run `-np 1`, STOP is not usable — same blocker as short-m@k Phase 1.

Overhead estimate at k=4 on worker tier, commit budget C=128:
- Prefix tokens generated across 4 streams: 4×128 = 512 tokens (roughly, amortized across slots).
- After pruning to α=0.5 (survive 2 of 4): remaining tokens = 2×(T−128) where T is full chain length.
- At T=3,500 (medium band): total tokens with STOP ≈ 512 + 2×3,372 = 7,256 tokens.
- Without STOP (4 parallel): 4×3,500 = 14,000 tokens.
- Savings: ~48%.

For a single sample (k=1), there is nothing to prune, so STOP is a no-op. STOP earns its keep only when the orchestrator actually spawns parallel samples — which requires a policy decision we currently do not make.

### 6.5 Wall-clock vs token-budget distinction

On our NUMA-concurrent worker stack, wall-clock saving ≠ token saving. If all k slots already run in parallel, cancelling (k − α·k) streams at commit budget C frees those slots back to the pool but does not shorten the wall-clock time of the survivors. The survivor tail still runs to completion on whatever slot it occupies. Wall-clock saving only materializes when:

(a) the orchestrator has other queued prompts that can immediately fill freed slots, or
(b) the survivors migrate to freed slots (which our current NUMA pinning does not support cleanly), or
(c) we configure STOP to actually early-exit all k streams and take just α·k of them as final answers (equivalent to short-m@k at the probe point).

For (c), we get wall-clock parity with short-m@k but with a learned selection rule rather than a length heuristic. This is the most promising configuration for our single-user workload (no queue behind the current request).

## 7. Training Requirements

STOP is "learnable" — which in this paper's framing means the super-token embedding and the scoring head are trained, but the backbone is **frozen**.

### 7.1 What must be trained

- Embedding for the `<STOP>` super-token (or the repurposed reserved unused token): shape `[d_model]`, e.g. 5,120 floats for the 30B-A3B worker.
- Scoring head: linear `[d_model → 1]` or 2-layer MLP. Negligible parameter count.

### 7.2 Training data

Correct / incorrect rollout pairs from the same model on reasoning tasks. This is something we have in principle (benchmark runs, Package B/C/D diagnostics) but have not packaged. Roughly:

- ≥ 5k–10k reasoning rollouts with ground-truth correctness labels.
- Balanced across problem types for generalization.

### 7.3 Compute required

The frozen-backbone constraint is the key: we only need gradients through the super-token embedding and the scoring head. A single forward pass through the frozen backbone at each rollout's probe position, cached once; gradient flows through a `[d_model → 1]` head and into the embedding row.

On a single workstation GPU (24 GB), this is feasible overnight. On CPU-only it is 10–50× slower but not blocked — scoring-head gradient is trivial, the bottleneck is forward passes to collect probe activations, and those can be cached offline.

### 7.4 DGX Spark relevance

DGX Spark is **not required** for STOP. Unlike OPSDC (needs 8×H200) or FoldGRPO/RLVR-style training, STOP's frozen-backbone design makes it the *cheapest* learnable technique in our compression taxonomy. It is actionable today on our existing EPYC hardware, provided we can run frozen forward passes to extract probe activations on enough rollouts. DGX Spark would *accelerate* data collection (forward-pass throughput) but is not a precondition.

This is an important reframing relative to CoLaR and OPSDC: "learnable" does not always mean "blocked on GPU". STOP's training story is closer to LoRA / control-vector training than to full RL.

## 8. Experiment Plan

Goal: validate whether STOP yields measurable quality-per-token gains on EPYC's worker/coder tier over our current Tier 1 stack.

### 8.1 Phase 0 — Instrumentation (~1 day)

- Reserve an unused token in Qwen3-30B-A3B vocabulary as the probe token. Verify tokenizer round-trip in llama.cpp.
- Add an orchestrator hook that fetches the hidden state at a specific position via `llama_get_embeddings_ith()` or equivalent (may require minor llama-server API work).
- Extend `seeding_diagnostics.jsonl` to record probe-position hidden states alongside existing correctness labels (piggyback on NIB2-35 persistence infrastructure).

### 8.2 Phase 1 — Data collection (~2 days, inference-gated)

- Run worker tier on a mixed reasoning benchmark (GSM8K + MATH + GPQA subset, ~1k prompts, k=4 per prompt, using `-np 4` slots).
- For each prompt × sample: record full generation, correctness label, probe-position activation at several candidate commit budgets (C ∈ {32, 64, 128, 256}).
- Target: 4,000 labeled rollouts with activations.

### 8.3 Phase 2 — Train the probe head (~0.5 day, offline)

- Train a linear scoring head `[d_model → 1]` with BCE + pairwise ranking loss on the collected activations.
- Report probe AUC at each commit budget C. Select the smallest C that achieves AUC ≥ 0.75.
- Fit the super-token embedding: this requires gradient through the backbone forward pass, so collect the probe activations with the super-token *present* as a null-initialized embedding, then iteratively update the embedding using the scoring head gradient (the "prompt-tuning" variant — frozen backbone, learn only the inserted embedding).

### 8.4 Phase 3 — Online eval (~1 day, inference-gated)

- A/B: baseline (majority@4, no STOP) vs STOP (k=4, α=0.5, best C from Phase 2) on held-out GSM8K + MATH + GPQA.
- Metric: accuracy @ fixed token budget; tokens @ fixed accuracy.
- Success criterion: ≥ 1.5pp accuracy at equal tokens, or ≥ 25% token reduction at equal accuracy.

### 8.5 Phase 4 — Integration (~1 day)

- Gate STOP behind difficulty-signal band: easy=no-STOP, medium=k=2, hard=k=4.
- Compose with TrimR on survivors.
- Add telemetry: probe score distribution, prune decisions, survivor accuracy vs pruned-would-have accuracy.

Total effort: ~5 days of inference + 1.5 days of code, **gated on worker-tier `-np ≥ 2` being enabled** for parallel sampling.

## 9. Risks & Tier 2b

### 9.1 Reproducibility risks

- **AIME25 sample size**: 30 questions. +6pp = 2 questions flipped. Confidence interval likely overlaps the baseline at 95%. Independent replication strongly recommended before adoption.
- **No released training data**: The paper describes data provenance but does not release the training set. We would build our own from our benchmark runs — which is actually an advantage for our distribution (domain match) but a risk for claimed-result replication.
- **Layer selection unspecified**: The paper does not ablate which transformer layer's hidden state feeds the scoring head. This is a free hyperparameter we must tune.

### 9.2 Generalization risk

- STOP is evaluated on math benchmarks (AIME, MATH, GSM8K) and partially on code. Our worker tier serves general + math + factual + agentic tasks. Transferability of the productivity signal to non-math domains is not empirically established.
- Training data bias: if the super-token learns "long = doomed" as a proxy, it may discriminate against hard prompts that legitimately need long chains (the OPSDC asymmetry: easy prompts compress 56–59%, hard prompts only 35%).

### 9.3 Architectural risk

- Qwen3.5 hybrid SSM may exhibit the same compatibility issues as with control vectors (`build_cvec()` missing from `qwen35.cpp`, 75% of layers are recurrent). On Qwen3.5, activation-level probes may not carry the same signal as on dense transformers. **Initial target: dense Qwen3-30B-A3B worker only.**
- If we use a reserved unused token rather than adding a new vocabulary entry, there is a small risk the frozen backbone has already assigned that token an arbitrary initialization that biases the probe. Verify the unused token's initial embedding is close to zero-mean before training.

### 9.4 Contradicting evidence to search for

Before committing implementation effort, scan for:

- Papers showing that prefix-level activation probes do **not** generalize across prompt distributions.
- Any reports of STOP-style methods failing at scale > 20B (the paper tops out at 20B).
- Overlap with SEER / short-m@k's length-only heuristic: if length alone explains most of the discriminative signal, a learned probe adds little. The paper's Table comparing STOP to length-threshold would show this directly — worth extracting on re-read.
- Whether the diversity-collapse finding (intake-441) means post-training models' prefix activations are already too homogeneous for a productivity probe to discriminate.

### 9.5 Tier 2b — what would kill this

Concrete kill criteria (pre-declared to avoid motivated reasoning):

- Phase 1 probe AUC < 0.65 at any C ≤ 256 on our collected rollouts → STOP's probe has insufficient signal on our model/distribution. Abandon.
- Phase 3 accuracy A/B gap < 0.5pp AND token savings < 15% → not worth the operational complexity. Revert to short-m@k heuristic and TrimR.
- Probe generalization gap: AUC on math > 0.8 but AUC on general > 0.6 → STOP is math-specific. Deploy only for math routing; do not generalize.
- Qwen3-30B-A3B MoE routing interacts badly with probe (different experts activated per sample → non-comparable hidden states) → restrict to dense tiers only.
- Diversity-collapse (intake-441) empirically blocks discrimination: all k samples produce near-identical probe states → STOP degenerates to random selection. Fall back to temperature-forced diversity at sampling time.

### 9.6 Classification

`worth_investigating` with a clear experiment plan. Not yet `new_opportunity` — upgrade depends on Phase 1 data showing probe AUC ≥ 0.75 at C ≤ 128 AND Phase 3 showing ≥ 1.5pp accuracy or ≥ 25% token savings at parity. Until then, our deployed Tier 1 stack (TrimR + length alarm + difficulty bands + conciseness) remains the production path.

## 10. Cross-References

### 10.1 Handoffs

- [`handoffs/active/reasoning-compression.md`](../../handoffs/active/reasoning-compression.md) — canonical Tier 1/2/3 taxonomy; add STOP as Tier 1.5 (internal-signal learnable; frozen-backbone, prefix-probe, selection policy).
- [`handoffs/active/non-inference-backlog.md`](../../handoffs/active/non-inference-backlog.md) NIB2-32 — difficulty_signal re-validation provides the natural gating substrate for STOP.
- [`handoffs/active/routing-intelligence.md`](../../handoffs/active/routing-intelligence.md) — STOP's k-sampling gate belongs in the routing enforce-mode policy.

### 10.2 Deep dives

- [`research/deep-dives/short-mk-parallel-reasoning.md`](short-mk-parallel-reasoning.md) — parallel reasoning + heuristic-length selection. STOP is the learnable upgrade of short-m@k's selection rule.
- [`research/deep-dives/flowsteer-concise-reasoning.md`](flowsteer-concise-reasoning.md) — learnable activation intervention (steering, not selection). STOP is the selection counterpart.
- [`research/deep-dives/reasoning-compression-s3cot-adaptive.md`](reasoning-compression-s3cot-adaptive.md) — activation-steering baseline.
- [`research/deep-dives/colar-latent-compression.md`](colar-latent-compression.md) — model-level compression requiring full training; STOP avoids this cost entirely.
- [`research/deep-dives/overthinking-info-bottleneck.md`](overthinking-info-bottleneck.md) — theoretical backing: unproductive branches carry less mutual information with the answer, which is precisely what STOP's probe is trying to measure.
- [`research/deep-dives/sft-generalization-reasoning-patterns.md`](sft-generalization-reasoning-patterns.md) — branching density as a runtime quality signal; STOP's probe may learn to detect this.

### 10.3 Related intakes

- intake-110 OPSDC — Tier 3 self-distillation; costly GPU path.
- intake-126 FlowSteer — steering counterpart to STOP.
- intake-127 TrimR — heuristic external-signal pruner; composes with STOP post-selection.
- intake-129 short-m@k — heuristic internal-signal selector; STOP upgrades its selection rule.
- intake-134 CoLaR — latent compression; orthogonal, training-heavy.
- intake-378 branching patterns → generalization; validates that prefix-level features can discriminate productive from unproductive chains.
- intake-404 TPO — if any Tier 3 RL materializes, STOP's probe gradient may share infrastructure.
- intake-437 — this deep dive.
- intake-441 diversity collapse — caveat for probe generalization.

### 10.4 Wiki pages

- [`wiki/speculative-decoding.md`](../../wiki/speculative-decoding.md) — STOP is not spec-dec but uses parallel sampling; note the distinction.
- [`wiki/context-management.md`](../../wiki/context-management.md) — STOP's prefix probe is a form of early-exit; add to context-compaction-related techniques.
- [`wiki/routing-intelligence.md`](../../wiki/routing-intelligence.md) — STOP belongs in the enforce-mode policy decision tree.
- [`wiki/cost-aware-routing.md`](../../wiki/cost-aware-routing.md) — STOP is a cost-aware mechanism (cheaper selection than full majority@k).

### 10.5 Relationship to diversity and parallelism

STOP's effectiveness depends on k samples being meaningfully diverse. Two failure modes:

- **Under-diverse** (intake-441 diversity collapse): post-trained models produce near-identical k samples. Probe discrimination collapses. Mitigation: force temperature ≥ 0.7 at sampling, add nucleus sampling diversity, or use prompt-level perturbation.
- **Over-diverse** (temperature too high): probe scores become noisy; correct sample may be pruned by chance. Mitigation: calibrate α conservatively (α ≥ 0.5 to keep at least half of samples).

The sweet spot aligns with short-m@k's observation that correct reasoning is consistent and incorrect reasoning wanders — meaning k samples at moderate temperature naturally separate into clusters, and the probe is trained to identify which cluster is the "correct" one. This is also the theoretical justification for the paper's result scaling with model size: larger models have sharper cluster separation at the same temperature, making the probe's job easier.

### 10.6 Code touchpoints

- `/mnt/raid0/llm/epyc-orchestrator/src/classifiers/difficulty_signal.py` — gating signal for whether STOP is invoked.
- `/mnt/raid0/llm/epyc-orchestrator/src/graph/helpers.py` — integration point for probe-and-prune loop (alongside existing length alarm).
- `/mnt/raid0/llm/epyc-orchestrator/scripts/server/orchestrator_stack.py` — worker tier `-np` parameter; must be ≥ 2 for STOP to function.
- `/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/seeding_types.py` — extend `RoleResult` to carry probe-position activation (piggyback on NIB2-35).
- `/mnt/raid0/llm/llama.cpp/src/llama-api.cpp` `llama_get_embeddings_ith()` — the API surface for extracting the probe hidden state.

---

## Bottom Line

STOP fills a genuine gap in EPYC's reasoning-compression taxonomy: the internal-signal × learnable × selection quadrant. Unlike CoLaR or OPSDC, it does not require backbone retraining and can be implemented on our existing EPYC hardware without a GPU farm. Unlike FlowSteer, it does not require `build_cvec()` and hybrid-SSM support. Its composition with our existing Tier 1 stack is clean: difficulty signal gates k, STOP prunes parallel samples, TrimR compacts survivors, length alarm fires on overruns. The headline AIME25 84 → 90 result is underpowered (30 questions) and should be independently validated before adoption, but the mechanism is sound and the experiment plan is 5 inference-days away from a live verdict on our worker tier.

**Compositional verdicts (per Tier 1 technique)**:
- TrimR: COMPOSES WITH
- short-m@k / length alarm: COMPOSES WITH
- Conciseness prompts: COMPOSES WITH
- Difficulty signal (+ band caps): COMPOSES WITH (gating role)
- N-gram loop detection: COMPOSES WITH

No existing technique is REPLACED or SUPERSEDED by STOP.

**Next action**: keep STOP on the reasoning-compression handoff as a `worth_investigating` Tier 1.5 entry with the Phase 0–4 experiment plan attached. Do not commit to implementation until NIB2-32 produces a live difficulty-signal verdict (the natural gating substrate for k-sampling), at which point STOP becomes the first learnable technique we can add without GPU training cost.
