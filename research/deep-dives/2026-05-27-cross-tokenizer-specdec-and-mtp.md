# Deep Dive — Cross-Tokenizer Speculative Decoding, MTP, and the MI200 Drafter Farm

**Date:** 2026-05-27 (initial 7 papers + 2 expansion deep-dives appended same day)
**Companion handoff:** [`handoffs/active/gpu-drafter-mi200-investigation.md`](../../handoffs/active/gpu-drafter-mi200-investigation.md)
**Intake entries:** intake-617..624 (8 new, 1 dedup against intake-042)
**Scope:** Technical reading of all 9 papers from the 2026-05-27 GPU-drafter design session and its `/research-intake` expansion: 7 from the original session (Timor SLEM/SLRS/TLI, ZeTT, EVA, Cascade Spec, SpecDec++, DeepSeek-V3 MTP, FVT) + 2 expansion finds (Gloeckle parallel MTP, FastDraft).
**Purpose:** Ground the gpu-drafter-mi200 handoff in the actual mechanisms/math/numbers, not abstract handwaving. Several handoff claims are corrected here based on close reading.

---

## Executive synthesis — what changed for the handoff

**Seven** load-bearing corrections come out of this deep dive (5 from the original 7 papers, 2 more from the expansion finds). They are wired into the per-paper sections below; flagging the headline shifts up front so the corrections are visible without reading the whole document.

1. **Timor 2025's "byte canonicalization" framing in the handoff is incomplete.** The paper presents **3 algorithms** — SLEM (string-level exact match with look-behind realign), SLRS (theoretical upper-bound, intractable), and TLI (token-level intersection, no string round-trip). The handoff's § Cross-Tokenizer should distinguish these. **TLI is the right operational starting point** for any non-Qwen drafter contingency — it's the cheapest per step (masked renorm over `T ∩ D`, no detokenize/retokenize). SLEM is the fallback when vocab overlap is too low.

2. **MTP head split is structurally bounded at $D = 1$ for current backends.** DeepSeek-V3 shipped with a single MTP module ($D = 1$); ik_llama.cpp PR #1744 ships a single MTP head for Gemma 4. The handoff's "chained-on-GPU MTP modules" design assumes $D \geq 2$, which **no production model we deploy actually has**. The split is still mechanically sound — the per-token H2D transfer of trunk hidden state ($d \cdot \mathrm{sizeof(bf16)}$ ≈ 14 KB) is negligible — but it produces *one* extra drafted token per main step, not a chain. Real chained MTP requires a model trained with deeper MTP; alternatively, EAGLE-style auxiliary drafters offer chaining without that constraint.

3. **SpecDec++ adaptive-K is structurally inapplicable at gemma4's `--draft-max 2`.** The mechanism truncates long speculation chunks early when cumulative rejection probability spikes. At $K = 2$ there is no "long chunk to truncate" — the policy almost never fires. Expected lift on current worker_general config: sub-1%. **SpecDec++ becomes interesting only after frontdoor adopts spec-dec with $K \geq 4$**, and only if per-position acceptance variance is large.

4. **ZeTT and FVT do not produce drafters competitive with native small models.** Both papers' empirical regimes are *self-consistency recovery* under tokenizer swap, not cross-target alignment for spec-dec. Acceptance against a Qwen3.6-35B target after FVT or ZeTT'ing a non-Qwen 1B would be bounded by the underlying capability gap. **Keep these on the contingency shelf; do not block matched-vocab MI200 work on them.** The handoff's framing of ZeTT/FVT as "learned vocabulary couplings" is conceptually right but operationally optimistic.

5. **CS Drafting (Cascade) suggests adding Qwen3-0.6B *below* Qwen3-1.7B for frontdoor is structurally net-positive on MI200**, but with a sharp caveat: the win depends on the *acceptance rate of Qwen3-1.7B drafting Qwen3.6*. If $\alpha_{1.7 \to 3.6} \geq 0.7$, the cascade is worth the scheduler complexity. If $\alpha_{1.7 \to 3.6} \approx 0.5$, the gain collapses toward zero. **Measure $\alpha_{1.7 \to 3.6}$ first; cascade is a Stage 3+ optimization, not Stage 1.**

6. **Parallel-MTP (Gloeckle 2024) is the architecturally correct MTP for the GPU-split design, BUT NO PUBLIC WEIGHTS EXIST.** Gloeckle's heads are mutually independent given trunk hidden state — one trunk forward + one H2D + $n$ heads execute concurrently as a batched GEMM. This is the clean GPU-split topology our handoff envisions. However: (a) Meta released no checkpoints despite ~500K GPU-hours of training, (b) fine-tuning a non-MTP model to add parallel heads "did not yield significant improvements" (Llama-2 attempt, their own quote), (c) sub-7B parallel-MTP regresses vs next-token baseline. **Operationally: the architecture is right, the supply side is empty.** Realized speedup ceiling on currently-available checkpoints (DeepSeek-V3 / gemma4, both causal-chain $D{=}1$) is one drafted token per step, not the ~3× Gloeckle ceiling. Re-read handoff § MTP Head Split with this constraint: design is sound and future-proofed for a hypothetical parallel-MTP open release, but near-term value is bounded by what's deployable.

7. **FastDraft (intake-624) sweet spot is the *coder* role, not frontdoor.** FastDraft trains custom drafters (~10B tokens, <24h on 8× Gaudi-2 / ~1-3 GPU-days on modern accelerators), matched-vocab only. Headline α: ~0.65 on HumanEval (code), only ~0.31-0.37 on general chat/summarization. They release weights only for Phi-3-mini-50M and Llama-3.1-8B-Instruct-150M — no Qwen, no Gemma, no MoE targets, no head-to-head vs EAGLE/Medusa. **Gating criterion for us:** invest in training only if measured $\alpha$(Qwen3-1.7B → target) on production traffic falls below ~0.55 at $\gamma{=}3$. For frontdoor (general chat) the off-the-shelf Qwen3-1.7B is likely sufficient; for coder_escalation (code-heavy), a code-specialized FastDraft drafter is the most likely +EV training investment. **Add this gating logic to handoff Stage 5 / Stage 3+ design.**

These corrections are folded into the per-paper "Relevance to our handoff" subsections below.

---

## Timor et al. 2025 — Lossless SD for Heterogeneous Vocabularies

**arxiv:** 2502.05202 | **Venue:** ICML 2025 | **Authors:** N. Timor et al. (Intel Labs + Weizmann) | **Intake:** intake-617

### The three algorithms

All three preserve the target distribution exactly (lossless) and require no retraining. They differ in *where* draft–target alignment is done and *what* is rejection-sampled.

- **SLEM — String-Level Exact Match (Alg. 2).** Drafter emits tokens, the run-length is *decoded to text*, then re-encoded under the target tokenizer $T$. Acceptance is checked on the resulting target-token sequence, with a "look behind" step that searches for the longest matched stretch and realigns on mismatch so non-injective tokenizers (multi-token draft strings mapping to one target token, or vice-versa) don't desynchronize the streams. Operates on canonical strings, no probability lift on the draft side.
- **SLRS — String-Level Rejection Sampling (Alg. 3).** Same string-intermediate as SLEM, but instead of exact-match it performs proper rejection sampling against $\psi(t) = \sum$ over *all* draft token sequences $(d_1\dots d_i)$ whose decoded concatenation re-tokenizes under $T$ to a sequence starting with $t$ (Thm. 3.2). Theoretically the highest acceptance of the three, but $\psi(t)$ is exponential in draft-token length — a limit-case algorithm, not a deployment one.
- **TLI — Token-Level Intersection (Alg. 4).** No string round-trip at all. The drafter's distribution is restricted and renormalized onto the *vocabulary intersection* $T \cap D$: $q'(x) = q(x) / \sum_{x \in T \cap D} q(x)$. Standard SD rejection sampling then runs against the target on that shared sub-vocabulary. Cheapest per step (no detokenize/retokenize), at the cost of throwing away any drafter probability mass on draft-only tokens.

Spectrum: TLI = token-level, online, cheap, lossy on acceptance. SLEM = string-level, online, canonical-string match. SLRS = string-level, theoretical upper-bound, intractable in general.

### Acceptance criterion (math)

Expected acceptance probability per draft step (paper's Table 2):

- Vocab-union baseline (Alg. 1): $\sum_{t \in T \cap D} \min\{p(t), q(t)\}$
- SLEM (Alg. 2): $\sum_{t \in T} p(t) \cdot \psi(t)$
- SLRS (Alg. 3): $\sum_{t \in T} \min\{p(t), \psi(t)\}$
- TLI (Alg. 4): $\sum_{t \in T \cap D} \min\{p(t), q(t)/\sum_{x \in T \cap D} q(x)\}$

where $p$ is the target distribution over $T$, $q$ the drafter distribution over $D$, and $\psi(t)$ aggregates the drafter mass on *every* draft tokenization that canonicalizes (under $T$) to a target-token-string starting with $t$. Canonical tokenization is *not* assumed unique; $\psi$ handles the multi-pre-image case at the cost of exponential enumeration. For SLEM in practice, the re-tokenization step (decode under $D$, encode under $T$, compare prefix; on mismatch, look behind for longest match and resync) replaces the explicit $\psi$ sum with a deterministic alignment search, and KV-cache state is kept in the *target* tokenization between iterations.

### Empirical results — concrete numbers

Targets: Llama-3.1-70B, Gemma-2-9b, Mixtral-8x22B, Phi-3-medium, CodeLlama-13b. Drafters: Vicuna-68m, Qwen2-0.5B, Gemma-2-2b. Datasets: CNN/DailyMail (summarization), SCROLLS (long-context), code (Appendix). Greedy and sampling tested.

Selected output tok/s at $T = 0$ (Table 1):

| Target | Domain | Drafter | AR baseline | Hetero | Δ |
|---|---|---|---|---|---|
| Gemma-2-9b | CNN/DM | Vicuna-68m | 27.7 | 37.5 (SLEM) | +35% |
| Gemma-2-9b | CNN/DM | Gemma-2-2b | 27.7 | 26.0 | −6% |
| Gemma-2-9b | SCROLLS | Vicuna-68m | 13.4 | 23.8 (TLI) | +78% |
| Gemma-2-9b | SCROLLS | Gemma-2-2b | 13.4 | 30.5 (TLI) | +128% |

Headline ≤2.8× hits on long-context summarization (SCROLLS). Worst case: Gemma-2-9b + Gemma-2-2b on CNN/DM at $T=10^{-7}$ regressed 27.3 → 11.7 tok/s (**−57%**) — a matched-architecture draft pair where heterogeneous machinery was unnecessary overhead. Vocab overlap $|T \cap D| / |T \cup D|$ ranged 12–85% across pairs (Table 5) and explains most speedup variance.

### Limitations & scope

Authors' own callouts: (i) acceptance is *lower* than a same-vocab drafter when one is available — heterogeneous SD is a contingency, not a default; (ii) SLRS's $\psi(t)$ is intractable for drafters with long tokens; (iii) **block-verification (Medusa/EAGLE-style tree verification) is "non-trivial to generalize" to heterogeneous vocabs** and is not solved here; (iv) target sizes capped at ~70B (no 400B-class targets); (v) generation modes restricted to greedy + low-temp sampling.

### Relevance to our handoff

For the MI200 frontdoor + matched-vocab Qwen drafter primary path, this paper is **irrelevant** — same-vocab SD will outperform any of the three algorithms here. The paper itself states matched-vocab SD wins when available.

Where it *does* matter is the contingency clause: if a non-Qwen drafter ever becomes the cheapest option for a role, **TLI is the right starting point** — purely distributional, no detokenize/retokenize on the hot path, integrates into existing rejection-sampling kernels with a single masked renormalization over $T \cap D$. SLEM is the fallback if vocab overlap is too low (the SCROLLS data shows TLI dominates when overlap is high; SLEM wins on CNN/DM where the intersection is narrower). SLRS is reference-only.

**The handoff's "byte canonicalization" framing is too narrow.** Timor's primary trick is *string-level*, not byte-level, and is one of three techniques — TLI doesn't touch strings at all. Update the handoff's § Cross-Tokenizer accordingly.

A HuggingFace Transformers PR (#35029) is the reference implementation; **llama.cpp port is the critical path to making this usable in our stack.**

---

## Minixhofer & Ponti 2024 — Zero-Shot Tokenizer Transfer (ZeTT)

**arxiv:** 2405.07883 | **Venue:** NeurIPS 2024 | **Authors:** B. Minixhofer, E. M. Ponti (Edinburgh + Cambridge) | **Intake:** intake-618

### Hypernetwork architecture

A **3-layer bidirectional Transformer** with hidden dim equal to the host LM's $d_\text{model}$ and an FFN expansion of $2 \times$ (vs RoBERTa's $4 \times$), Post-LN. Constant-depth regardless of host LM size — at Mistral-7B scale it costs **132.1M FLOPs/token ≈ 0.9%** of the host's 15.4G FLOPs/token, effectively free.

**Input representation:** *not* raw bytes and *not* the new token ID. Each new token $t \in V_b$ is **re-tokenized by the original tokenizer $T_a$** and embedded with the original embedding table $E_{\phi_a}$; the hypernet attends over that sub-sequence to predict a single embedding for $t$. This is the trick that makes it tokenizer-agnostic — the input space is always the old vocab.

**Outputs:** input embedding $\phi_\text{in}$ and output embedding $\phi_\text{out}$ only. Two separate prediction heads when the host has untied embeddings. **No LM-head bias, no intermediate layers, no LoRA.**

**Shared-token init:** there's no special init for $V_a \cap V_b$ — instead it's handled by training (auxiliary loss below) and by a **10k-step MIMICK-style warmup** in which the hypernet is trained to reproduce the original $E_{\phi_a}$ table before the LM loss kicks in.

### Training objective and data

Primary loss is **standard CLM/MLM on the host LM with the embeddings swapped to hypernet predictions** — i.e., $L_\theta(T_b(x), H_\theta(V_b, T_b), \psi)$ with $\psi$ (the rest of the LM) frozen. So it is *language-modeling distillation against the host itself*, not contrastive and not against a teacher.

**Auxiliary loss** (weight $\alpha = 0.5$): for every token in $V_a \cap V_b$, L2-penalty between the hypernet prediction and the original embedding. This is the actual "shared-token anchor".

**Data:** MADLAD-400 (English) + StarCoder (code) at $7:3$, 200k steps, batch 128, seq-len 128. **Tokenizer is resampled per batch with lognormal-noised merge counts** — what gives zero-shot generalization to unseen tokenizers.

### Empirical results — concrete numbers

- **XLM-R on XNLI (encoder, multilingual):** avg accuracy 72.6 → 71.2 (**−1.0pp**), worst Turkish −3pp, best Vietnamese +1pp. Sequence-length reduction ~14% avg, >16% wall-clock speedup from quadratic attention.
- **Mistral-7B + GPT2 tokenizer (NL):** 0-shot avg 76.9 → **73.0** (−3.9pp); after 800M tokens of continued training **74.9** (−2.0pp).
- **Mistral-7B + StarCoder tokenizer (HumanEvalPack pass@1):** 28.1 → **23.2** zero-shot (−4.9pp); after 800M tokens **27.6** (−0.5pp). Code sequences ~10% shorter.
- **vs FOCUS baseline on code:** FOCUS 13.3% pass@1, ZeTT **23.2%** zero-shot — **+9.9pp**. FOCUS on decoders is near-random in worst case.
- Multilingual MMLU still drops **8–15pp** even with the hypernet — non-trivial residual gap.

### What ZeTT actually modifies

**Only $\phi_\text{in}$ and $\phi_\text{out}$.** All attention, FFN, LayerNorm, and (when present) LM-head bias parameters of the host LM are **frozen and untouched**. There is no adapter, no LoRA, no intermediate-layer surgery. The hypernet is discarded at inference — you keep just the two predicted embedding matrices and the original transformer. Byte-fallback to handle non-UTF8 / Mark-category tokens adds 162–522 extra rows.

### Limitations & failure modes

- **Decoder transfer is markedly harder than encoder transfer** — XNLI's −1pp does not generalize; Mistral with GPT2 tokenizer loses ~4pp zero-shot and needs 800M tokens of recovery training to come within 2pp.
- **Continued training is effectively mandatory** for decoder LMs to close the gap; "zero-shot" in the title is a capability claim, not the recommended deployment.
- Pretokenization is assumed fixed (a regex split) — works for SentencePiece/BPE-family, breaks for tokenizers with materially different pretok rules.
- No mechanism for vocab-size mismatch beyond byte fallback.
- Auxiliary anchor presupposes meaningful $V_a \cap V_b$ — if vocabs are near-disjoint across script families, the regularizer carries no signal.

### Relevance to our handoff

ZeTT is **model-side tokenizer replacement**, not draft/target alignment — the connection to our handoff is indirect and operationally weak.

1. **What it could do for us:** retrofit a non-Qwen pretrained small LM to emit Qwen3 tokens, giving us a matched-vocab drafter for a Qwen target without training from scratch.
2. **Why it's fragile for spec-dec:** spec-dec needs **distributional agreement** with the target, not just lexical compatibility. ZeTT preserves the retrofitted model's *own* behavior under a new tokenizer; the post-ZeTT 1B is still a 1B trained on its original data, now spelling its outputs in Qwen tokens. Acceptance against a Qwen3.6-35B target is bounded by the underlying capability gap. The 800M-token continued-training is the bare minimum to recover *self-consistency*, let alone target alignment.
3. **Honest verdict:** keep on contingency shelf; do not block matched-vocab MI200 work on it.

---

## Xu, Lu, Zhang 2024 — EVA (Bridging Vocabularies for LLM Ensemble)

**arxiv:** 2404.09492 | **Venue:** NAACL 2024 | **Authors:** Y. Xu, J. Lu, J. Zhang (CASIA) | **Intake:** intake-619

### Vocabulary alignment procedure

Two-stage, computed **once offline**, no per-step learning:

1. **Embedding-space projection (learned, supervised on overlap).** On the set of tokens that appear verbatim in both vocabs $Q$ and $P$ (identity-string overlap), fit an orthogonal transform $U_{QP}$ via VecMap (normalize → whiten → orthogonal Procrustes → re-weight → de-whiten), minimizing $\sum_{(i,j) \in \text{overlap}} \| E^Q_i \cdot U_{QP} - E^P_j \|^2$ (Eq. 1). **Overlapping tokens are not mapped via identity in the output space — they are the training pairs that anchor the learned rotation** between the two embedding tables.
2. **Similarity matrix on all tokens (no learning).** Once embeddings are co-aligned, the full mapping $W^{QP} = \text{SIM}(E^Q \cdot U_{QP}, E^P)$ is built using **CSLS** (cross-domain similarity local scaling), yielding a dense $|Q| \times |P|$ similarity. They then *sparsify* with three filters: top-$t$ truncation ($t=10$), threshold ($0.1$), and variance truncation ($\sigma=0.0001$, $c=5$) which kills tokens that look similar to "everything" (special/padding artifacts). Result: ~1 MB sparse $W^{QP}$ per model pair.

Non-overlapping tokens are handled purely by embedding similarity — **no byte/char fallback, no edit distance.**

### The unified projection space

The pivot is **one model's vocabulary**, selected as the model with the *largest* vocab (no third superset, no byte space). Every other model $\ell$ has its native softmax $q_\ell$ post-multiplied by its sparse alignment matrix: $p_\ell(\cdot | x_{<i}) = q_\ell(\cdot | x_{<i}) \cdot W^{\ell\rho}$ (Eq. 6). Fusion averages projected distributions in pivot-vocab space.

**Critical asymmetry for our purposes:** decoding is **token-by-token in pivot space**, with each ensembled model run independently from the same prefix. There is **no handling of subword-boundary misalignment** — they implicitly assume all models advance one token per step on the same string prefix. Re-tokenization between steps is not discussed. (Human eval in App. E confirms ~5% of alignments are semantically off-target — "research→study", "(→H".)

### Empirical results — concrete numbers

7 ~7B models. Best-individual vs EVA (Table 3):

- **GSM8K: 32.30 (InternLM) → 42.91 (+10.61)** — headline
- ASDiv: 60.52 → 65.05 (+4.53)
- AddSub: 62.39 → 64.22 (+1.83)
- NQ (EM): 28.59 → 30.64 (+2.05)
- TriviaQA: 62.77 → 64.29 (+1.52)
- Flores Zh→En BLEU: 29.18 (Baichuan2) → 31.16; LLM-Blender (3B fusion) gets 27.18 — EVA beats both best individual and dedicated fusion baseline.

EVA beats LLM-Blender on 6/8 generation tasks. **No confidence intervals, error bars, or significance tests reported.** Greedy decoding only.

### Compute cost per token

$N \times$ inference cost — every ensembled model runs on every token. Authors note "those inferences can be executed in parallel" (Limitations) but provide **zero wall-clock numbers**. Alignment matrices are precomputed and free at runtime (sparse matmul on a softmax-sized vector). **Not viable as drop-in for latency-sensitive serving** without parallel-replica infrastructure.

### Limitations & breakdown modes

- Requires "adequate" overlap; Fig. 3 shows ~53% TigerBot↔LLaMA overlap but no quantified breakdown curve.
- Hyperparameter $n$ (filter strictness) needs heavy task tuning: $n=40$ for NLG, $n=3$ for GSM8K — >10× swing, so the method is *not* task-agnostic.
- Special/padding tokens detected post-hoc by variance truncation, not pre-excluded.
- Greedy only; no beam, no sampling, no temperature studies.

### Relevance to our handoff

EVA solves a **related but structurally different problem** from spec-dec.

1. **EVA is symmetric distributional averaging; spec-dec needs asymmetric likelihood-of-token.** Spec-dec needs $p_\text{target}(t_\text{draft} | \text{context})$ where $t_\text{draft} \in \text{vocab}_\text{draft}$. EVA never computes this; it pushes both into pivot space and averages. The analogous operation for us is the *inverse* direction: given a token from $\text{vocab}_\text{draft}$, find its image in $\text{vocab}_\text{target}$ — which is precisely what a row of $W^{\text{draft} \to \text{target}}$ gives. So **the precomputed alignment artifact is directly reusable**, but the acceptance test would be $p_\text{target} \cdot W^{\text{draft} \to \text{target}}[t_\text{draft}]$ rather than EVA's averaging step.
2. **Token-position misalignment is unsolved.** EVA assumes both models advance one token per step on the same prefix; it does not handle subword-boundary misalignment. Any application of EVA-style alignment in our setting requires a separate string-level realignment layer (likely byte-level rollback, as in Timor's SLEM).
3. **Their sparse top-10 mapping is too lossy for verification.** A spec-dec verifier needs the *full* target distribution support for rejection-sampling correctness. Truncating at top-10 + threshold 0.1 destroys the tail mass that determines acceptance. EVA's filters are tuned for ensembling, not for unbiased probability transport.
4. **The orthogonal-Procrustes-on-overlap recipe is the cheapest viable bootstrap.** ~1 MB artifact, no per-step training, identity-string overlap as supervision — worth replicating as a baseline before anything learned end-to-end.

Bottom line: EVA validates that *learned-rotation + CSLS on string-overlap anchors* is sufficient to get usable cross-vocab probability mass, but its averaging operator and aggressive sparsification mean we cannot lift it wholesale — reuse the alignment construction, not the fusion step.

---

## Chen et al. 2023 — Cascade Speculative Drafting (CS Drafting)

**arxiv:** 2312.11462 | **Venue:** NeurIPS 2024 | **Authors:** Z. Chen et al. (UIUC) | **Intake:** dedup against existing intake-042

### Vertical cascade

A recursive **drafter-of-the-drafter** chain: target $M_t$ is reviewed by neural drafter $M_{d1}$, which is itself drafted-for by smaller neural drafter $M_{d2}$, which is in turn drafted-for by a **statistical bigram model called Max-Gram (MaG)** — a stateless token-matcher with parameter count ≈ tokenizer size. Cascade depth in the paper's experiments: 3 levels (base → small → MaG) for FLAN-T5, 2 levels (160M → MaG) for LLaMA-2-7B. Termination is by construction: recursion bottoms out at non-neural MaG (Algorithm 1 ends when `draftList` is empty). The **only autoregressive draft step is the smallest neural drafter** above MaG; MaG itself is non-autoregressive (substring lookup). The largest drafter is *not* autoregressive in the usual sense — it batches a window of tokens proposed by the level below.

### Horizontal cascade

Token importance is defined **purely positionally**, not by entropy or a learned scorer. Under the Bernoulli acceptance model used by Leviathan, the probability that the $n$-th drafted token survives is $p^n$, so the *expected value* of drafting position $n$ decays geometrically. CS Drafting allocates the **larger/more-accurate drafter to early positions** (high expected payoff) and progressively **smaller/cheaper drafters (down to MaG) to later positions**. Hyperparameters $k_{ij}$ set how many tokens each drafter contributes at each cascade depth. The acceptance test at every position is the unchanged Leviathan rejection rule, so target distribution is preserved regardless of which drafter produced the token.

### Mathematical correctness

Distribution preservation is inherited from Leviathan et al. 2023 — the standard rule `accept iff M_d(x) ≤ M_t(x), else reject with prob 1 − M_t(x)/M_d(x)` is applied unchanged at the **target boundary**. The paper's one novel knob, **Lenience** $l \in [1, \infty)$, relaxes the acceptance test to $M_d(x) \leq l \cdot M_t(x)$ but is applied **only at intermediate drafter-reviews-drafter boundaries**; when the target reviews, $l \leftarrow 1$ is forced. This is the trick that gives lenience speedup *without* altering the final output distribution. Optimal walltime objective: $T(k, \alpha, c) = (\sum_i \prod_j \alpha_j) / (1 + \sum_i c_i)$ (Theorem 4.5), with $\partial T/\partial \alpha_1 > \partial T/\partial \alpha_k$ — the formal justification for front-loading capable drafters.

### Empirical results — concrete numbers

Walltime speedups vs autoregressive target (Tables 2–3):

| Target | Dataset | Vanilla spec-dec | CS Drafting | Δ vs spec-dec |
|---|---|---|---|---|
| FLAN-T5-XXL | MMLU | 3.97× | 4.88× | +23% (=+81% over autoregressive baseline gain) |
| FLAN-T5-XXL | GSM8K | 3.38× | 3.88× | +15% |
| LLaMA-2-7B-chat | MMLU | 2.12× | 2.64× | +25% |
| LLaMA-2-7B-chat | GSM8K | 2.48× | 2.86× | +15% |

Headline +81% is the gain over autoregressive on top of vanilla spec-dec on FLAN-T5/MMLU — *not* a 1.81× multiplier over vanilla. Gains shrink toward 0 when (a) smallest neural drafter already has high acceptance with the target or (b) per-position acceptance $p$ is low enough that horizontal allocation has no geometric tail to exploit.

### Compute and memory cost

Per accepted token: ≈ $1 + \sum c_i$ drafter forwards where $c_i$ is the parameter ratio of drafter $i$ to target. For FLAN-T5-XXL with base+small+MaG, dominated by $c_\text{base} \approx 250\text{M}/11\text{B} \approx 2.3\%$ — overhead vs single-drafter spec-dec is a few percent. VRAM overhead small: adding FLAN-T5-small (60M) below base (250M) costs ~250 MB; **MaG is essentially free**.

### Limitations

- Hyperparameter surface (`k_11, k_12, k_22, lenience l`) must be tuned per workload.
- **Anti-intuitive drafter sizing**: with MaG, *larger* intermediate drafters beat *smaller* ones — opposite of single-drafter spec-dec heuristics.
- No help when target/drafter alignment is already weak: low $p$ collapses the geometric tail.

### Relevance to our handoff

For frontdoor (Qwen3.6-35B-A3B target) on MI200, the candidate cascade is **Qwen3-0.6B → Qwen3-1.7B → Qwen3.6**. CS Drafting predicts this is net-positive **only if** Qwen3-0.6B's acceptance rate against Qwen3-1.7B is high enough that the geometric tail of Qwen3-1.7B drafting is dominated by Qwen3-0.6B+MaG-style cheap proposals.

Breakeven from Theorem 4.5: $\alpha_{0.6 \to 1.7} > (1 + c_{0.6} + c_{1.7})/(1 + c_{1.7}) \approx 1 + c_{0.6}/(1 + c_{1.7}) \approx 1.013$ if $c_{0.6} \approx 0.6/35 \approx 1.7\%$. Since acceptance is bounded by 1, the inequality reduces to: **adding Qwen3-0.6B wins as long as it is not actively harmful** — the cost coefficient is so small relative to the 35B target that even modest acceptance pays off.

Dominant risk on MI200 is **not compute** but **kernel-launch / scheduling overhead** of running three forward graphs on one GPU, which the paper does not model.

**Recommendation:** stand up Qwen3-1.7B-only first, measure $\alpha_{1.7 \to 3.6}$, then add Qwen3-0.6B *only if* $\alpha_{1.7 \to 3.6}$ is high (≥0.7). If $\alpha_{1.7 \to 3.6}$ is mediocre (~0.5), the cascade gain shrinks toward zero and is not worth scheduler complexity.

---

## Huang, Guo, Wang 2024 — SpecDec++ (Adaptive Candidate Length)

**arxiv:** 2405.19715 | **Venue:** COLM 2025 | **Authors:** K. Huang, X. Guo, M. Wang (Princeton) | **Intake:** intake-620

### MDP formulation and threshold policy

State $s = (x_\text{prefix}, (Y_1, \dots, Y_k))$ where $x_\text{prefix}$ is prompt + already-accepted tokens and $(Y_1, \dots, Y_k)$ are draft candidates already sampled from $q$. Action space binary: $\{\text{stop}, \text{continue}\}$. Reward is wall-clock latency: each `continue` costs $c_1 = t_\text{draft}$, each `stop` triggers target verification costing $c_2 = t_\text{target} - t_\text{draft}$. A slack term $\Delta$ absorbs expected rollback cost from rejected tail tokens.

**Theorem 3.1 (optimal stopping):** stop is optimal iff

$$P(\exists \, 1 \leq i \leq k, Y_i \text{ rejected} \mid x_\text{prefix}) \geq (c_2 + \Delta) / (c_1 + c_2 + \Delta)$$

The probability is the *cumulative* chain-rule rejection probability over the $k$ drafted tokens. Threshold is purely a function of drafter/target speed ratio — for a slow target and fast drafter the threshold approaches 1 (keep drafting); for near-equal-cost drafter it approaches 0 (stop early).

### The acceptance prediction head

Sits on the **drafter** side. Architecture: a $(D+1)$-layer ResNet MLP with SiLU (best $D=3$), consuming the drafter's final-layer hidden embedding $e_i$ of the last drafted token and emitting $\sigma(f_\theta(e_i))$ — scalar estimate of that token's acceptance probability. Parameter count is small (hundreds of K to low millions vs the 7B drafter); overhead reported as 0.0004 s/step, indistinguishable from noise.

Trained on 40k Alpaca prompts: target generates responses, drafter samples alternatives with 15% of positions force-mixed from the target distribution (BERT-style masking) to densify the positive class. Loss is weighted BCE with $w_\text{rej} \in \{1, 3, 6, 12\}$ (best $w_\text{rej} = 6$). Fires every drafted token inline.

### Runtime decision rule

```
p_hat ← 1
for i = 1, 2, …:
    q_i ← drafter forward
    y_i ← sample from q_i
    p_hat ← p_hat * sigmoid(f_theta(e_{i-1}))     # cumulative accept prob
    if (1 - p_hat) > h: break                     # threshold h ≈ 0.7
    if i >= 20: break                             # hard cap
verify y_1..y_i against target
```

### Empirical results — concrete numbers

Single drafter/target pair: **Llama-2-Chat 7B → 70B, greedy, ctx ≤ 512.** Fixed-K baseline tuned over $K \in \{2, 4, 6, 8, 10, 12, 14\}$.

| Dataset | Baseline (tuned K) | SpecDec++ | Δ |
|---|---|---|---|
| Alpaca | 1.90× | 2.04× | +7.2% |
| HumanEval | 2.00× | 2.23× | +11.1% |
| GSM8K | 2.07× | 2.26× | +9.4% |

Paper never reports raw per-token acceptance $\alpha$, never reports which fixed $K$ was optimal per dataset, never reports SpecDec++'s mean $K$. A single $(w_\text{rej}=6, D=3, h=0.7)$ config achieves >99.3% of per-dataset-tuned best — predictor generalizes across these three datasets with the same model pair.

### Sensitivity and transferability

Threshold $h$ robust at 0.7 across datasets. **Cross-model-pair transferability not evaluated** — every reported number is Llama-2 7B/70B. Implicit assumption: head must be retrained per (drafter, target) pair.

### Limitations

- MoE target: not evaluated.
- Long context: max length 512 tokens.
- Sampling: greedy only.
- Drafter regime: authors note "for a weak draft model the acceptance prediction head may perform badly."

### Relevance to our handoff

The SpecDec++ gain (+7–11% vs *tuned* fixed K) is realized in a regime where best fixed $K$ lies well inside $\{2, \dots, 14\}$ and chunks routinely run to ~10+ tokens — the policy's job is mostly to **truncate long chunks early** when cumulative rejection probability spikes.

Our gemma4 worker_general is the opposite operating point: `--draft-max 2` with 76.9% MTP acceptance means a chunk is at most 2 tokens, and cumulative rejection probability after one drafted token is ≈ 0.23 — well below $h = 0.7$. The adaptive policy almost never fires a `stop` inside such a short chunk; **expected lift at our current config: marginal (sub-1%).** For MTP at $K=2$ glued by architecture, SpecDec++ is structurally inapplicable.

For frontdoor (no spec-dec today): start with a fixed K sweep first (e.g., $K \in \{2, 4, 6, 8\}$). Adaptive K only earns its complexity once optimal fixed K is ≥ ~4–6 and rejection-probability variance across positions is large.

**Path:** instrument K-sweep + per-position empirical acceptance histograms first; only adopt SpecDec++ if histogram shows wide spread (some contexts want $K=8+$, others want $K=1$) within a single workload.

---

## DeepSeek-AI 2024 — DeepSeek-V3 MTP (Multi-Token Prediction)

**arxiv:** 2412.19437 | **Venue:** technical report | **Authors:** DeepSeek-AI | **Intake:** intake-621

### MTP module architecture

One MTP module at depth $k$ is **not** a bare norm+linear head and **not** a full duplicate trunk — it is a single transformer block wrapped by a fixed pre/post-processing recipe. Each module owns:

- A unique transformer block $\mathrm{TRM}_k(\cdot)$ (one block, one set of attention + FFN weights).
- A unique projection matrix $M_k \in \mathbb{R}^{d \times 2d}$ that fuses two normed inputs.
- Two `RMSNorm` instances.
- A **shared** embedding table $\mathrm{Emb}(\cdot)$ and a **shared** output head $\mathrm{OutHead}(\cdot)$ — both tied to the main trunk.

### Causal chain across depths

The chain is strictly **sequential along depth**:

$$h'^k_i = M_k\, [\mathrm{RMSNorm}(h^{k-1}_i)\,;\,\mathrm{RMSNorm}(\mathrm{Emb}(t_{i+k}))] \quad \text{(Eq. 21)}$$

$$h^k_{1:T-k} = \mathrm{TRM}_k(h'^k_{1:T-k}) \quad \text{(Eq. 22)}$$

where $h^{k-1}_i$ is the previous depth's hidden state ($h^0_i$ = the **main trunk's last hidden state** at position $i$), and $\mathrm{Emb}(t_{i+k})$ is the embedding of the ground-truth (during training) or just-predicted (during inference) token. Module $k$ requires **both** previous module's hidden state and embedding of previous token — no parallel path.

Weight sharing: $\mathrm{Emb}$ shared across main + all MTP depths; $\mathrm{OutHead}$ shared similarly; $\mathrm{TRM}_k$ and $M_k$ unique per depth.

### Training loss

Per-depth cross-entropy (Eq. 24): $\mathcal{L}^k_\text{MTP} = -\frac{1}{T} \sum_{i=2+k}^{T+1} \log P^k_i[t_i]$.

Aggregated (Eq. 25): $\mathcal{L}_\text{MTP} = \frac{\lambda}{D} \sum_{k=1}^{D} \mathcal{L}^k_\text{MTP}$. Weighting schedule: $\lambda = 0.3$ for first 10T tokens, then $\lambda = 0.1$ for remaining 4.8T. **The released DeepSeek-V3 was trained at $D = 1$** — the deployed model has exactly one MTP module beyond main head.

### Inference-time use as spec-dec

Paper's framing: "MTP is for training; it can be repurposed for spec-dec." Mechanics not spelled out in §2.2. With $D = 1$, only one extra draft token per main step, and SD verification is the next main forward (already needed to update $h^0$).

### Acceptance rates by depth

**Paper publishes no per-depth acceptance numbers.** The "85–90% for depth 2" figure circulates from DeepSeek's external release notes, not §2.2. The paper's MTP empirical evidence is Table 4 (pretraining gains from auxiliary loss). Because the shipped model is $D = 1$, the paper cannot report depth-3+ collapse — that data does not exist in this report.

### Per-module compute cost

One MTP module ≈ one trunk transformer block + a $d \times 2d$ projection + two RMSNorms. For DeepSeek-V3 (61-layer trunk), one MTP module ≈ **1/61 of trunk FLOPs and params**. Small in absolute terms but **not a thin linear head** — carries a full MLA-attention + MoE-FFN block.

### Relevance to our handoff (MTP head split feasibility)

Read Eq. 21 carefully. For $k = 1$, $h^{k-1}_i = h^0_i$ = **the main trunk's last hidden state**. The first MTP module is hard-pinned to consuming the trunk's hidden state for the just-decoded position. This is a **per-token sync point**: every drafted token needs the trunk's $h^0_i$ before the MTP head can produce a logit. If trunk runs on CPU and MTP head runs on GPU, you pay one $d$-sized H2D transfer per accepted token ($d \cdot \text{sizeof(bf16)}$ — for $d = 7168$ that's ~14 KB, negligible vs PCIe bandwidth).

The chained-on-GPU question — can MTP modules at $k > 1$ run on GPU without further CPU sync? — depends on the deployed model's depth. **For DeepSeek-V3 specifically: $D = 1$, so the question is moot — there is no second MTP module to chain.** For gemma4-26B-A4B (depth-1 head per PR #1744), same answer.

**The "chained-on-GPU" design therefore only composes for an MTP model trained with $D \geq 2$** — and even then, Eq. 21 says $h^k$ depends on $h^{k-1}$, so depths $k \geq 2$ chain entirely on whatever device $\mathrm{TRM}_k$ lives on, with no further trunk dependency until verification.

**Bottom line:** MTP-split design is mechanically sound (per-token H2D of $h^0$ is cheap, MTP block is ≈ 1/N_layer of trunk so fits trivially on small VRAM), but **expected speedup with current production models is bounded by $D = 1$**: one drafted token per main step. To unlock chained-on-GPU drafting at $D > 1$, we either need a model trained with deeper MTP (none of our current backends ship one), or we use EAGLE-style auxiliary drafters, not DeepSeek-style MTP.

---

## Gee et al. 2024 — Fast Vocabulary Transfer (FVT)

**arxiv:** 2402.09977 | **Venue:** EMNLP 2022 Industry Track (arXiv upload Feb 2024) | **Authors:** L. Gee, A. Zugarini, L. Rigutini (Expert.ai / U. Siena), P. Torroni (U. Bologna) | **Intake:** intake-622

### The transfer procedure

FVT operates on two tokenizers — a *general* $\mathcal{T}_\text{gen}$ with vocabulary $\mathcal{V}_\text{gen}$ (donor's) and an *in-domain* $\mathcal{T}_\text{in}$ with vocabulary $\mathcal{V}_\text{in}$ (target).

"Overlap" is defined by **surface-form (string) identity** of the token entry, not BPE-merge equivalence: if $t_i \in \mathcal{V}_\text{in} \cap \mathcal{V}_\text{gen}$ then $E_\text{in}(t_i) := E_\text{gen}(t_i)$ — embedding row copied verbatim. There is no normalization of casing, whitespace markers (Ġ / ▁), or pre-tokenization scheme; in practice **FVT as published only cleanly applies when both tokenizers share the same pre-tokenization family** (the paper's experiments are all WordPiece→WordPiece on BERT).

For a **new token** $t_i \in \mathcal{V}_\text{in} \setminus \mathcal{V}_\text{gen}$, the surface string is re-tokenized **using the old (general) tokenizer**, yielding a sub-token sequence. The new embedding is the **uniform arithmetic mean** of those old rows: $E_\text{in}(t_i) = \frac{1}{|\mathcal{T}_\text{gen}(t_i)|} \sum E_\text{gen}(t_j)$. No frequency weighting, no positional weighting, no learned mixture. The paper does not formally specify a fallback when the old tokenizer cannot decompose a surface string.

### Continued pretraining recipe

After embedding init, **one epoch of MLM** on the in-domain corpus (same dataset downstream task uses), then standard fine-tuning. Hyperparameters: LR $3 \times 10^{-5}$, batch size 64, seq-len 64–128. Optimizer unspecified. **The entire model is unfrozen** — no embedding-only stage. Note: "one epoch on $\mathcal{D}_\text{in}$" is *tiny* (ADE ≈ thousands of sentences) — closer to a warm-up than ZeTT-scale continued pretraining.

### Empirical results — concrete numbers

Tasks: ADE (medical NER), LEDGAR (legal clause classification), CoNLL03 (general NER control). Test F1 (Table 2, no distillation):

| Task | Original ($\mathcal{T}_\text{gen}$) | FVT ($\mathcal{T}_\text{in}$, retokenized) | Δ |
|---|---|---|---|
| ADE | 90.80 | 90.77 | −0.04 |
| LEDGAR | 80.93 | 80.93 | 0.00 |
| CoNLL03 | 89.43 | 87.87 | −1.75 |

I.e., for in-domain tasks FVT essentially **matches** the original BERT-base at a smaller, domain-adapted vocab; general-domain CoNLL03 regresses by ~1.7 F1. The paper does **not** report a random-init-new-rows ablation against the same MLM budget — notable hole — but a "VT" variant (overlap-copy only, new rows random) consistently underperforms FVT.

### Compute cost

FVT init step: **single forward pass over the new vocabulary** — effectively free (seconds on CPU; not reported). Continued PT is one MLM epoch on small in-domain corpus — minutes-to-low-hours on a single GPU for BERT-base. Paper reports neither wall-clock nor FLOPs nor hardware. Inference speedup from shorter sequences: 1.07–1.40× (Table 5), 2.76× combined with distillation.

### Failure modes

Paper is **near-silent on failure modes**. No analysis of: (i) morphologically complex tokens where uniform averaging mis-locates the semantic centroid, (ii) bytes/characters absent from $\mathcal{T}_\text{gen}$, (iii) cross-family transfer (BPE↔SentencePiece↔WordPiece) — every experiment is WordPiece BERT in, WordPiece BERT out, vocabulary *reduced* not *replaced*. ZeTT and Timor's paper both cite FVT as the *floor baseline* for these unaddressed regimes.

### Relevance to our handoff

FVT is the **cheap lower bound**, not a realistic production lever. Concretely: re-tokenizing a Llama-3.2-1B to Qwen's 151k BPE vocab via FVT would require (a) cross-family pre-tokenization reconciliation FVT does not specify, (b) ≫ one-epoch continued PT — Qwen's vocab is ~4× BERT's and the embedding distribution shift is far larger than the in-domain WordPiece *shrinkage* the paper validates.

ZeTT (2405.07883) and Minillm-style retokenization both report FVT-initialized drafters losing several perplexity points vs native small models trained on the target tokenizer; for spec-dec, where drafter acceptance is exponentially sensitive to drafter–target distribution KL, **that gap will erase the spec-dec wallclock win**.

Bottom line: cite as training-free floor and as initialization for a longer continued-PT run, but a Llama→Qwen FVT drafter is **not a credible substitute** for Qwen3-0.6B/1.7B native drafters on our MI200 path.

---

## Gloeckle et al. 2024 — Parallel Multi-Token Prediction (Meta FAIR)

**arxiv:** 2404.19737 | **Venue:** NeurIPS 2024 spotlight | **Authors:** F. Gloeckle, B. Y. Idrissi, B. Roziere, D. Lopez-Paz, G. Synnaeve (Meta FAIR) | **Intake:** intake-623

### MTP head architecture

Gloeckle's model is a **shared trunk** $f_s$ followed by **$n$ independent output heads** $f_{h_1}, \dots, f_{h_n}$, each implemented as one or a small number of transformer layers, plus a **shared unembedding matrix** $f_u$. Per-head prediction:

$$P_\theta(x_{t+i} \mid x_{t:1}) = \mathrm{softmax}\big(f_u(f_{h_i}(f_s(x_{t:1})))\big) \quad (i=1,\dots,n)$$

**The load-bearing fact for our handoff:** each head $f_{h_i}$ takes only the shared trunk's final hidden state $z_{t:1} = f_s(x_{t:1})$ as input. It does *not* read the previous head's output, and it does *not* read $\mathrm{Emb}(t_{i+k-1})$. This is the structural opposite of DeepSeek-V3's MTP (Eq. 21–22), where $h^k_i = M_k[\mathrm{RMSNorm}(h^{k-1}_i); \mathrm{RMSNorm}(\mathrm{Emb}(t_{i+k}))]$ chains depth-wise. Gloeckle's heads are "$n$ independent output heads … to predict in parallel each of the $n$ future tokens." In parameter-matched setups, the trunk is shortened (layers removed) when $n-1$ auxiliary heads are added, holding total parameter count constant against $n=1$. Each head is typically a single transformer block.

Appendix B ablates three alternatives — **parallel** (chosen), **causal** (head $i$ composed on top of head $i-1$, like DeepSeek-V3), and **anticausal**. Parallel wins (Table S4: 33.8% vs 30.0% MBPP@1 against causal).

### Parallelism / dependency structure

Because each head consumes only $z_{t:1}$, **all $n$ heads are mutually independent given the trunk hidden state.** At inference, one trunk forward yields $z_t$; from $z_t$, the $n$ heads can be evaluated in any order, including fully concurrently as a batched matmul. This is explicit in the paper's framing of heads as "independent" — exactly what makes self-speculative decoding work for them: $n$ draft tokens from a single trunk pass, no inter-head sequential dependency.

### Training loss and weighting

Unweighted sum of next-$i$-token cross-entropies:

$$L_n = -\sum_t \sum_{i=1}^n \log P_\theta(x_{t+i} \mid x_{t:1})$$

No depth-weighting, no curriculum. A training-memory trick processes heads sequentially and frees per-head logits, reducing peak memory from $O(nV+d)$ to $O(V+d)$.

### Empirical results — pretraining gains

Tested sizes: 300M, 600M, 1.3B, 3B, 6.7B, 13B. Headline finding: **MTP helps only at scale**.

- **<1B**: regressions or flat (300M HumanEval: 1.0 → 1.2 with $n=4$, slight regression).
- **3B**: +0.8 HumanEval, +1.2 MBPP.
- **6.7B**: +2.0 HumanEval, +2.1 MBPP.
- **13B**: +4.5 HumanEval, +4.5 MBPP (+12% relative HumanEval, +17% relative MBPP).

Depth ablation at 7B / 200B tokens: $n=4$ optimal for BPE token models; gains saturate or invert beyond $n=4$. Byte-level models prefer $n=8$. **NLP choice-tasks (MMLU-style) regress** at $n=4$ on 7B — gains are concentrated in generative code / math / summarization.

### Self-speculative decoding results

The paper *does* explicitly evaluate the MTP heads as a drafter:

- **7B, code domain, $n=4$ heads:**
  - 2 heads: 1.85 tok/forward, **1.79× speedup**
  - 3 heads: 2.57 tok/forward, **2.35× speedup**
  - 4 heads: 3.12 tok/forward, **2.74× speedup** (headline "up to 3× on code")
- **Byte-level, $n=8$:** up to **6× speedup.**

Acceptance rates higher than post-hoc-finetuned drafters because the heads were trained end-to-end with the trunk.

### Limitations

(a) **Small-model regression** under 1B; (b) **NLP choice-tasks regress** at $n=4$ on 7B — gains live in generative tasks; (c) **Fine-tuning is ineffective**: "We tried to finetune Llama 2 with 4-token prediction but this did not yield significant improvements" — MTP benefits must come from pretraining, not bolted on; (d) Gains diminish as training-token budget grows past ~200B (sample-efficiency improvement, not loss-floor improvement); (e) **No public checkpoints** — 500K GPU-hours trained, none shipped.

### Relevance to our handoff

**Q1 (chained-on-GPU feasibility):** **Confirmed.** Each head reads *only* $z_t = f_s(x_{t:1})$, with no dependency on previous-head outputs and no dependency on $\mathrm{Emb}(t_{i+k-1})$. The MTP-split design therefore reduces to: (i) trunk forward on CPU produces $z_t$; (ii) one H2D transfer of $z_t$ (single $d$-dim vector per generation step, ~kilobytes); (iii) all $n$ heads execute as one batched GEMM (or $n$ parallel small kernels) on GPU; (iv) $n$ candidate tokens returned in one D2H roundtrip. **No further CPU↔GPU sync between heads.** This is exactly the structural property the GPU-split design needs, and it is *not* available with DeepSeek-V3-style causal-chain MTP.

**Q2 (acceptance vs depth):** Highest $D$ evaluated for BPE models is $n=4$. At $n=4$ on 7B-code, marginal per-head acceptance decays: 2 heads → 0.93/head; 3 heads → 0.86/head; 4 heads → 0.78/head. **Practical speedup ceiling for our design with a parallel-MTP model: ~3× on code workloads, less on chat/NL.**

**Q3 (public checkpoints):** **No.** Paper releases no weights. No HuggingFace links, no GitHub, no `facebook/mtp-7B`. This is "train your own" territory.

**Q4 (drop-in to gemma4 D=1):** **No clean upgrade path.** To go from gemma4's $D=1$ → $D=4$ parallel-MTP, must add 3 *new, untrained* transformer-block heads consuming $z_t$, and *re-pretrain* (or at minimum heavy continued-pretrain) the trunk + all 4 heads jointly. Gloeckle's own fine-tuning failure (Llama-2 → 4-token MTP) is direct counterexample to a cheap retrofit. Heads 2–4 cannot be cold-started without pretraining-scale compute.

**Bottom line:** the architecture is right (parallel MTP is the trivially-GPU-splittable case), but the supply side is empty. Decision pivots on: (a) wait for a parallel-MTP open-weight release, (b) commit to a custom parallel-MTP pretrain (multi-100K GPU-hour), or (c) accept the $D=1$ speedup ceiling of currently-available checkpoints (gemma4). DeepSeek-V3 is ruled out for this design by its causal-chain structure, independently of $D$.

---

## Zafrir et al. 2025 — FastDraft (Drafter Training Pipeline)

**arxiv:** 2411.11055 | **Venue:** ENLSP@NeurIPS 2024 / Findings of ACL 2025 | **Authors:** O. Zafrir, I. Margulis, D. Shteyman, S. Guskin, G. Boudoukh (Intel Labs) | **Intake:** intake-624

### Training pipeline

Three sequential stages, total ~10B tokens, single 8× Gaudi-2 node, <24h wall-clock:

1. **Pre-training (PT)** — causal LM on ~10B tokens of FineWeb (dedup web text). Drafter initialized from scratch with target-matched architecture skeleton (same tokenizer, smaller hidden/layer counts).
2. **Continued pre-training (CP)** — ~5B tokens of The Stack v2 (code) + ~2.5B tokens FineWeb (text). Ablations show **text-first then code-mix beats code-first or pure-mixed.**
3. **Fine-tuning / alignment (FT)** — sequence-level knowledge distillation on synthetic instruction data: Alpaca + OIG-small-chip2 + Evol-Instruct prompts re-generated by the **target** at $T \in \{0.6, 0.8, 1.0\}$. This is the step that aligns the drafter's distribution to the target's.

Drafters are always **smaller, separate** architectures (not LoRA, not same-arch fine-tunes). Sizes evaluated: 50M and 120M against Phi-3-mini-4k (3.8B) — 76× and 32× reductions; 150M against Llama-3.1-8B-Instruct — ~53× reduction. Architecture search explicitly out of scope.

### Loss and objective

FT uses **sequence-level KD**: cross-entropy on tokens sampled from the target (behavioral cloning of target completions, not from gold answers). Optional token-level KD variants (0.5 CE + 0.5 KL or TVD against target logits, with top-k sparsified logits to cut storage 6-9×) are evaluated but the paper concludes "token-level KD benefits are not definitive" — sequence-level CE on target generations is recommended default. **No RL, no reward shaping.**

### Vocabulary handling (matched vs heterogeneous)

**Matched only.** Quote: "any LM can function as a draft model, provided it shares the same vocabulary." FastDraft trains drafters from scratch with the target's tokenizer; there is no cross-tokenizer machinery. For heterogeneous vocab, must compose with Timor 2025 (intake-617).

### Empirical results — concrete numbers

Acceptance rate $\alpha$ (block $\gamma=3$, multinomial $T=0.6$, post-FT):

| Drafter | Target | CNN-DM | TinyStories | Dolly | HumanEval |
|---|---|---|---|---|---|
| Phi3-50M | Phi-3-mini 3.8B | 0.369 | 0.306 | 0.370 | **0.562** |
| Llama-150M | Llama-3.1-8B-Instruct | 0.307 | 0.266 | 0.334 | **0.649** |

Headline: **up to 3× memory-bound speedup on code, ~2× on natural language**; on Intel Core Ultra (Lunar Lake) wall-clock 1.5× summarization, 2× code completion. The marketing "67% acceptance" figure is HumanEval-only and is the best case. Greedy-only / general-chat $\alpha$ is materially lower (0.27–0.37).

### Comparison to alternatives

**No head-to-head with EAGLE, Medusa, or off-the-shelf small drafters.** EAGLE/Medusa cited only in related-work. Baselines are internal ablations (PT-only vs PT+CP vs PT+CP+FT, text-first vs code-first mix, sequence- vs token-level KD). **This is a real gap when comparing to our existing Qwen3-1.7B-as-drafter option — we have to bridge it ourselves.**

### Compute cost

Reference run: ~10B tokens, 8× Gaudi-2, <24h. 120M drafter ~2× training time of 50M. On 8× H100 / 8× MI250 should be similar or faster. Conservatively: **1–3 GPU-days on 8 modern accelerators per drafter**, ≪$1k on spot cloud, trivial on institutional compute. Latency from "target exists" to "drafter ready" is dominated by synthetic-data generation from the target (FT corpus), not by gradient updates.

### Public artifacts

**Weights released as OpenVINO-int8 on HuggingFace:**
- `OpenVINO/Phi-3-mini-FastDraft-50M-int8-ov`
- `OpenVINO/Llama-3.1-8B-Instruct-FastDraft-150M-int8-ov`

No training code, no Qwen / Gemma / coder-specific checkpoints. fp16/bf16 originals not on the HF org page.

### Limitations

- Matched-tokenizer requirement (no cross-vocab).
- No architecture search.
- Hardware-specific wall-clock; authors lean on MBSU as hardware-agnostic metric.
- Targets evaluated are dense models <10B; **no MoE, no Qwen, no targets ≥30B.**
- No head-to-head vs EAGLE/Medusa/self-draft; speedup claims are vs no-SD baseline only.
- $\alpha$ drops sharply outside HumanEval; the 3× number is code-only.

### Relevance to our handoff

**Q1 (vs off-the-shelf Qwen3-1.7B):** FastDraft has *not* been evaluated on Qwen / MoE / 30B-class targets. On comparable size ratios (~50× reduction, dense target) they report $\alpha \approx 0.31\text{–}0.37$ on chat/summarization — which is **not obviously better** than what a well-aligned same-family Qwen3-1.7B (~20× reduction, shared tokenizer, same instruction-tuning lineage) is likely to produce off-the-shelf. Dominant signal: **before training, measure $\alpha$ of Qwen3-1.7B → Qwen3.6-35B-A3B on our traffic mix.** FastDraft is most likely to win on the *code* slice (HumanEval $\alpha=0.65$ is the standout), less likely on general chat.

**Q2 (cascade composability):** Yes, trivially. FastDraft drafters are plain causal LMs with the target's tokenizer; CS Drafting / cascade (intake-042) only needs drop-in autoregressive drafters. Could train a ~30M tiny and a ~300M medium against the same target and stack them. The paper doesn't evaluate cascades but nothing in the recipe blocks it; FT step (synthetic data from target) is *more* valuable for the medium tier.

**Q3 (gating criterion to invest in training):** Train a custom FastDraft drafter **only if all three hold**:
- (a) measured $\alpha$(Qwen3-1.7B → Qwen3.6-35B-A3B) on production-mix prompts is **below ~0.55** at $\gamma=3$ (block efficiency $\tau^3 < 2.65$, leaving headroom an aligned drafter could plausibly recover);
- (b) the role is high-volume / latency-critical enough that 1.5–2× decode wins amortize ~2 GPU-days of training + ongoing target-side synthetic-data regeneration on each target update;
- (c) matched-vocab preserved end-to-end (Qwen3-1.7B and Qwen3.6-35B share tokenizer — yes; otherwise must compose with Timor TLI/SLEM).

If $\alpha \geq 0.55$ off-the-shelf, the marginal lift FastDraft reports (~+0.05–0.10 $\alpha$ post-FT vs PT-only in their ablations) does not justify the training pipeline and target-drift maintenance burden.

**Q4 (coder_escalation applicability):** **This is where FastDraft is most likely to pay off for us.** Target = Qwen3-Coder-30B-A3B, vocab = Qwen (matched-vocab drafter exists: Qwen3-1.7B), domain = code (their strongest result, $\alpha=0.56\text{–}0.65$). The CP-on-Stack-v2 + FT-on-target-generated-code recipe is directly applicable. **Gating:** if measured $\alpha$(Qwen3-1.7B → Coder-30B) on a code-heavy eval falls below ~0.55, a FastDraft-style code-specialized drafter is the right next step. MoE caveat: Coder-30B-A3B is MoE; FastDraft has not been validated on MoE targets, so verify target-generated synthetic data captures expert-routing distribution adequately (small risk, but unmeasured).

---

## Action items distilled from this deep-dive

Prioritized; each maps to a specific handoff or chapter.

1. **Update `gpu-drafter-mi200-investigation.md` § Cross-Tokenizer** to distinguish Timor's SLEM / SLRS / TLI rather than collapsing to "byte canonicalization". Identify **TLI as the operational starting point** for any non-Qwen drafter contingency. *Owner: handoff maintainer.* ✓ done in this session.
2. **Update `gpu-drafter-mi200-investigation.md` § MTP Head Split** to acknowledge $D = 1$ bound on current production models AND that parallel-MTP (the architecturally correct design) has no public weights. Reframe "chained-on-GPU" as gated on either a parallel-MTP open release, a custom multi-100K-GPU-hour pretrain, or pivoting to EAGLE-style auxiliary drafters. *Owner: handoff maintainer.*
3. **Rewrite Chapter 01 (speculative-decoding.md) § Tokenizer Compatibility Constraints** — flagged by intake-617; current text is factually outdated post-ICML 2025. *Owner: epyc-inference-research maintainer.*
4. **Port Timor SLEM / TLI to llama.cpp** — reference impl is HuggingFace Transformers PR #35029 (merged). Unblocks the entire non-Qwen-drafter contingency. *Critical-path engineering item.*
5. **Train SpecDec++ acceptance head on Qwen3-1.7B + Qwen3.6 frontdoor** — but **only after** Stage 1 fixed-K sweep is complete and per-position acceptance variance is measured. Don't ship adaptive K from day one.
6. **Measure $\alpha$(Qwen3-1.7B → Qwen3.6) on production-mix prompts** — load-bearing for THREE downstream decisions: (a) whether cascade (intake-042) is worth scheduler complexity at Stage 3+, gate $\alpha \geq 0.7$; (b) whether FastDraft custom training is +EV, gate $\alpha < 0.55$; (c) whether to invest in SpecDec++ adaptive-K, gate optimal fixed $K \geq 4$. **This single measurement gates the entire downstream investment ladder.** Implement via dedicated llama-server flag or log-analysis once spec-dec is enabled at frontdoor.
7. **Measure $\alpha$(Qwen3-1.7B → Qwen3-Coder-30B-A3B) on code-heavy eval** — gates FastDraft code-specialist drafter training for coder_escalation. Gate $\alpha < 0.55$ → train; else skip.
8. **Monitor for parallel-MTP open-weight releases** (Meta, DeepSeek, Qwen, Mistral, anyone). Pin a memory or alert in research-intake when a parallel-MTP checkpoint surfaces — this unlocks the GPU MTP-split design from "future option" to "available now."
9. **Add Gloeckle's parallel-vs-causal MTP architecture distinction to `gemma4-mtp-drafter-evaluation.md`** as a closed/known limitation: gemma4's MTP is causal-chain $D=1$; chained-on-GPU drafting is not available without a parallel-MTP retrain. *Owner: gemma4 handoff maintainer.*

---

## Cross-references

- Handoff: [`handoffs/active/gpu-drafter-mi200-investigation.md`](../../handoffs/active/gpu-drafter-mi200-investigation.md)
- Handoff: [`handoffs/active/gemma4-mtp-drafter-evaluation.md`](../../handoffs/active/gemma4-mtp-drafter-evaluation.md) (updated by intake)
- Handoff: [`handoffs/active/peer-verifier-speculation-spike.md`](../../handoffs/active/peer-verifier-speculation-spike.md) (updated by intake)
- Handoff: [`handoffs/active/moe-spec-cpu-spec-dec-integration.md`](../../handoffs/active/moe-spec-cpu-spec-dec-integration.md) (updated by intake)
- Index: [`handoffs/active/inference-acceleration-index.md`](../../handoffs/active/inference-acceleration-index.md) (intake summary table)
- Chapter rewrite flag: `epyc-inference-research/docs/chapters/01-speculative-decoding.md` § Tokenizer Compatibility Constraints
