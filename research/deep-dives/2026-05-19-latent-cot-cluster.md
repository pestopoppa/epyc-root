# Latent / Abstract CoT Cluster — 2026-05-19

**Cluster scope**: 5 intakes (545, 559, 560, 561, 562) that compress chain-of-thought into a non-verbal channel.
**Cross-cluster anchors**: reasoning-compression.md, per-request-reasoning-budget.md, memento-block-reasoning-compression.md, context-folding-progressive.md; intakes 110/126/127/128/129/134/289/292/276.

---

## Executive Summary

Five papers occupy distinct cells in a (training-required, representation-type) matrix. **Coconut** and **CODI** sit on the continuous-embedding-with-training axis (foundational and self-distilled respectively), **Abstract CoT** and **Token Assorted** use a discrete codebook with training (reserved-token vs VQ-VAE learned), and **Soft Thinking** is the lone training-free entry — an inference-time decoder patch that replaces argmax with a probability-weighted mixture of top-k embeddings. For the frozen-GGUF EPYC stack, only Soft Thinking is immediately deployable. The discrete-codebook track (Abstract CoT / Token Assorted) is the strongest "if we ever fine-tune" path because it preserves standard autoregressive decoding (no llama.cpp engine surgery). The continuous-latent track (Coconut/CODI) is reference-only: curriculum brittleness, GPT-2-scale validation, and loss of token-level traceability make it a poor fit for a CPU-inference agent stack where every decision is debugged through the token stream. A load-bearing experimental gate before any Soft Thinking adoption is whether top-k embedding mixtures stay on the natural model manifold when the underlying embeddings are dequantized from Q4_K_M / Q6_K — the paper tested only fp16/bf16 on H100s.

---

## Design-Space Matrix

| Method | Repr type | Training? | Curriculum? | Code public? | License | EPYC fit | Tier |
|---|---|---|---|---|---|---|---|
| **Coconut** (2412.06769) | continuous embedding (last hidden state) | yes — SFT | yes (k-stage replacement; brittle) | NOT in paper (Meta/UCSD; impl exists upstream but no link in PDF) | n/a in paper | poor — requires retraining + engine modification + loses token traceability | Tier 4 (reference) |
| **CODI** (2502.21074) | continuous embedding (aligned hidden state) | yes — single-model joint teacher/student | no (self-distillation) | NOT in paper; Appendix F has class skeleton | n/a in paper | poor — only validated at GPT-2 / LLaMA3.2-1B; unproven at 30B-A3B / 27B scale | Tier 4 (reference) |
| **Token Assorted** (2502.03275) | discrete VQ-VAE codebook (64–1024 entries) | yes — SFT with random-mix | no (random uniform sampling over replacement count) | NOT in paper (uses Llama Cookbook) | n/a | medium — preserves AR decoding, but needs DGX-class FT infra; tested up to Llama-3.1-8B | Tier 3 (if FT lands) |
| **Abstract CoT** (2604.22709) | discrete reserved vocab (M=64 tokens, m_max=128 length) | yes — policy iteration + RL (GRPO) | yes (3 iterations of bottlenecked SFT + self-distillation) | NOT in paper (datasets on HF) | n/a | medium — preserves AR decoding, but needs RL infra + reward model (gpt-oss-20b in paper) | Tier 3 (if FT lands) |
| **Soft Thinking** (2505.15778) | continuous mixture-of-embeddings (top-k weighted sum) | **NO** | n/a | **YES — github.com/eric-ai-lab/Soft-Thinking** | MIT (root) + Apache-2.0 (SGLang fork) | **HIGH** — pure inference-time decoder modification; ~150 LoC patch in llama.cpp | **Tier 1** |

Mechanically: Soft Thinking is the only entry that does not require a single weight update or a token vocabulary change. Every other entry requires either retraining a model from scratch or fine-tuning a pretrained one — neither of which is currently possible on the frozen GGUF stack.

---

## Soft Thinking as the Tier-1 Quick Win

### Exact mechanism

Standard decoding picks the next token via `t = argmax(softmax(z_t))` (or sampling) and feeds `e(t)` as the next input. Soft Thinking replaces this with a **probability-weighted mixture of the top-k token embeddings**, fed back as the next input embedding (no token is emitted into the output stream during the "soft" phase):

```
# Standard decoding (per step):
p_t = softmax(z_t / T)                       # logits → distribution
t_next = argmax(p_t)                          # or sample
e_next = embed(t_next)                        # one row of W_E

# Soft Thinking modification:
p_t = softmax(z_t / T)
p_top_k = top_k_truncate(p_t, k)              # zero non-top-k entries
p_top_k = renormalize(p_top_k)                # sum to 1
e_next  = Σ_{i in top_k} p_top_k[i] * embed(i)   # weighted sum of rows of W_E
# Feed e_next as next input embedding — DO NOT emit a token; do not write to output stream
```

Per the paper, the full equation (before truncation) is:
```
ẽ_next = Σ_{k=1..|V|} c_t[k] · e(k) = Σ_{k=1..|V|} p[k] · e(k)
```
The top-k filter is applied "to remove low-probability noise"; renormalization makes the mixture a proper convex combination on the embedding-row simplex.

### Cold-Stop heuristic (necessary for stability)

The continuous concept-token stream is OOD for an LM trained on discrete tokens. Without an exit condition, generation collapses (paper reports "extremely long output" and "generation collapse"). Cold Stop:

```
# After each step:
H_t = -Σ p[k] · log p[k]                     # entropy of the (truncated, renormalized) distribution
if H_t < tau:
    low_entropy_counter += 1
else:
    low_entropy_counter = 0
if low_entropy_counter >= k_consec:
    # Distribution has stabilized — model is "ready" to commit
    emit('</think>')                          # force exit; switch to standard argmax sampling
```

Intuition: as the soft-reasoning process converges toward an answer, the next-token distribution sharpens. Once entropy stays below `tau` for `k_consec` consecutive steps, the model is committed enough to switch back to standard token emission.

### Reported gains (exact numbers from paper)

| Model | Benchmark | Pass@1 delta | Token delta |
|---|---|---|---|
| QwQ-32B | AIME 2024 | 76.88% → **83.33%** (+6.45 pp) | 12,080 → 10,627 (−11.6%) |
| QwQ-32B | MATH-500 | 97.66% → **98.00%** (+0.34 pp) | 4,156 → 3,644 (−12.3%) |
| DeepSeek-R1-Distill-Qwen-32B | average math | +1.71 pp | **−22.4%** |
| DeepSeek-R1-Distill-Llama-70B | average math | +1.11 pp | −17.9% |

**Headline (paper abstract)**: "improving pass@1 accuracy by up to 2.48 points while simultaneously reducing token usage by up to 22.4%."

### llama.cpp implementation estimate

The patch goes in the **sampler / decode loop**, specifically wherever the post-softmax distribution is converted to a token id and that id is used to look up the next input embedding. In llama.cpp, this is in `common/sampling.cpp` (`common_sampler_sample`) and the embedding lookup is in `llama_set_inputs` / `llama_build_graph` (the embedding tensor is gathered by token id).

**Patch scope estimate**:
1. New sampler type `LLAMA_SAMPLER_TYPE_SOFT_MIX` with `(top_k, temperature, tau_cold, k_consec)` params (~30 LoC).
2. New batch-input path: instead of `inp_tokens` (int32 ids), accept `inp_embd` (fp32 vectors) for soft steps. llama.cpp already supports `llama_batch_init(..., embd=N)` so the plumbing exists — the work is wiring the sampler output to that path (~50 LoC).
3. Cold-Stop counter + entropy computation in sampler context (~20 LoC).
4. Top-k truncate + renormalize + weighted sum over `W_E.rows[top_k_ids]` (~30 LoC; reuse top-k from `llama_sampler_init_top_k`).
5. CLI / server flag wiring (`--soft-thinking-top-k`, `--soft-thinking-tau`, etc.) (~20 LoC).

**Total: ~150 LoC**, all in `common/sampling.cpp` and a small server flag pass-through. No graph changes needed — `llama_batch` already supports embedding input.

**Test bench**:
- GSM8K (200-question subset) at T=0.7, top-k ∈ {5, 10, 20, 50}, tau ∈ {0.5, 1.0, 1.5}, k_consec ∈ {3, 5, 8}.
- HumanEval or MBPP (worker_coder regime).
- Compare against baseline argmax + same temperature; primary metrics: tokens/answer (lower better) and pass@1 (higher better).

**Cost**: 1 dev-day for patch + 1 nightshift for sweep (under EPYC throughput-only mode, no concurrent inference per `feedback_no_concurrent_inference`).

**Success gate**: ≥10% token reduction at iso-pass@1 on coder bench, OR ≥1pp pass@1 at iso-tokens, on at least one production-stack quant (Q4_K_M for 30B-A3B, Q6_K for 27B).

### Quant interaction — the load-bearing concern

The paper tested **fp16/bf16 on H100s only** ("Quantization Testing: Not addressed"). Our production stack uses Q4_K_M (30B-A3B), Q4_K_M (gemma4-26B-A4B), and Q6_K (27B). For Soft Thinking, the input to the next forward pass is `Σ p_i · embed(i)` — a convex combination of embedding rows.

**Why this might break under quantization**:
- During training, the model only sees `embed(i)` for individual token ids — points on a discrete manifold.
- The mixture `Σ p_i · embed(i)` lives in the convex hull of training-time inputs. Under fp16 the convex hull is dense and smooth.
- Under Q4_K_M / Q6_K, each `embed(i)` is dequantized on the fly from a 4-bit / 6-bit block. Quantization noise is **per-row independent**. When you take a convex combination, the noise terms add: the mixture inherits Σ p_i · ε_i ≈ √k · ε (k = top-k size, ε = per-row noise).
- For Q4_K_M with typical block scales, per-row noise is ~1–3% relative. With k=10, the mixture noise could be 3–10% — potentially pushing the input off the training manifold into a regime the model genuinely never saw, even during fp16 training.

**Mitigation candidates**:
1. **Cast embeddings to fp16 before mixing** (dequantize the top-k rows, do the weighted sum in fp16, then feed that as `inp_embd`). This is essentially what we already do for the input embedding lookup — Soft Thinking only adds the weighted sum, which is cheap. The question is whether residual quantization noise on each row corrupts the sum.
2. **Validate on a quant-ladder sweep**: F16 vs Q8_0 vs Q6_K vs Q4_K_M, same model (Qwen3-8B is the smallest production candidate). If F16 shows the +2.48pp/−22% deltas and Q4_K_M shows degradation or instability, the gate fails for our stack.
3. **Restrict top-k**: smaller k → less noise accumulation but also less "soft" benefit. The paper does not sweep k; pick `k=5` for first validation.

**Risk if this fails**: Soft Thinking is then locked behind a higher-precision quant (Q8_0 or F16), making it incompatible with worker_general / worker_coder hot paths. Falls back to a Q8_0-only intervention on architect / debug_scorer where decode-time dominates.

### Stack inheritance — what models test

The paper validated on **QwQ-32B, DeepSeek-R1-Distill-Qwen-32B, DeepSeek-R1-Distill-Llama-70B**. Our production stack has:
- 30B-A3B Q4_K_M (worker_explore) — Qwen3 family, **adjacent** to the tested DeepSeek-R1-Distill-Qwen-32B.
- gemma4-26B-A4B Q4_K_M (worker_general, via ik_llama.cpp MTP) — **NOT tested** by paper.
- Qwen3-coder 30B-A3B variant — Qwen3 family, **adjacent**.
- Qwen3.6-35B (frontdoor) — Qwen3 family, **adjacent**.

Adjacency is plausible for Qwen3 family (architecturally close to QwQ-32B). Gemma4 is a coin flip — different architecture, different training distribution, and we're using ik_llama.cpp MTP which is also off the beaten path.

---

## Discrete Codebook Head-to-Head: Abstract CoT vs Token Assorted

Both preserve **standard autoregressive decoding** — they only change the vocabulary. The model emits tokens as usual; some of those tokens are from a reserved/learned reasoning codebook rather than from natural language. For llama.cpp this means **zero engine changes** — only a new model variant (different tokenizer + fine-tuned weights).

| Dimension | Abstract CoT (intake-545) | Token Assorted (intake-561) |
|---|---|---|
| Vocabulary construction | M=64 reserved tokens `<TOKEN_A>..` added to base vocab (no semantic prior; learned during training) | VQ-VAE trained on intermediate CoT chunks; codebook size 64 (ProsQA) → 1024 (math); each chunk of L=16 text tokens → L/r=1 latent code at r=16 |
| Reasoning trace structure | `<beginabstract> z_1 ... z_m <endabstract>` then answer (entirely abstract until answer) | `<boLatent> z_1 ... z_M <eoLatent>` then text tokens (hybrid: first M positions latent, rest verbal) |
| Training recipe | Policy iteration: (a) bottlenecked SFT with masked attention, (b) self-distillation via constrained decoding; 3 iterations, then GRPO RL with gpt-oss-20b as reward model | Random-mix SFT: at each epoch, uniformly sample M ∈ {0,72,128,160,192,224,256} and replace the first M tokens with VQ codes |
| Compression locus | Whole reasoning trace | Early planning steps only (later steps stay verbal) |
| Best reported compression | **11.6× on MATH-500** (90.8% acc @ 144 tokens vs 92.6% @ 1671) | **3-4× on early planning**, ~22% trace-level reduction on math (501.6 vs 646.1 tokens), 17% on Fresh-Gaokao |
| Reported regressions | **AIME'25: −1.2pp** (24.4% vs 25.6%); **GPQA-Diamond: −1.0pp** (50.5% vs 51.5%) | Poisson-Replace strategy "significantly worse"; All-Replace degrades. Hybrid (left-to-right partial replace) is the safe operating point. |
| Training infra cost | High — needs RL with separate reward model | Medium — pure SFT, no RL |
| Model scales tested | Qwen3-8B (primary) | T5 / GPT-2 (scratch); Llama-3.2-1B, 3.2-3B, 3.1-8B (FT) |
| Code release | Not in paper | Not in paper |

### Which fits a future EPYC fine-tuning workstream better?

**Abstract CoT** has the bigger compression headline (11.6×) and more thorough RL recipe but requires RL infrastructure (GRPO + reward model) that EPYC doesn't have. Reported regressions on AIME'25 / GPQA-Diamond are real and small but consistent — the seed paper frames them as "comparable" which is generous.

**Token Assorted** is pure SFT, simpler to reproduce, and has the architectural property that "compress only the early planning phase" maps well onto agent traces where the front-loaded reasoning ("decide which tool to call") is the most token-wasteful segment.

**Recommendation**: when an EPYC fine-tuning lane exists (DGX Spark or other GPU acquisition), prototype **Token Assorted first** — lower infrastructure cost, more interpretable codebook, hybrid structure preserves verbal answer reasoning. Use **Abstract CoT as the comparison baseline** if Token Assorted hits a ceiling.

Both lose verbal interpretability on the compressed portion of the trace — this is an operational regression for debug/observability. Mitigation: log the abstract tokens with their codebook indices so traces remain replayable.

---

## Continuous-Latent Foundational Track: Coconut + CODI (Tier 4 — reference only)

### Why Coconut is reference-only

- **Requires retraining** with a multi-stage curriculum. The k-stage curriculum is **brittle**: the paper itself reports "w/o curriculum" collapses to 14.4% on GSM8K vs 34.1% with curriculum (and 42.9% for verbal CoT). The 14.4% number is essentially the model failing to discover useful continuous thoughts from question-answer pairs alone.
- **Underperforms verbal CoT on GSM8K**: 34.1% ± 1.5 vs 42.9% ± 0.2 — an **8.8pp regression**. The seed paper attributes this to GSM8K requiring "complex contextual understanding" that benefits from explicit language. This is exactly the workload regime where worker_coder operates on EPYC.
- **Loses token-level traceability**: continuous thoughts don't decode to anything inspectable. For agent tool-call introspection (which is the dominant debug pattern on EPYC), this is a hard regression.
- **Engine surgery**: the "feed last hidden state as next input embedding" loop is not a llama.cpp primitive. Would require a custom decode path that bypasses the embedding lookup table entirely.

Where it shines: **ProsQA 97.0% vs 77.5% CoT** (FLOPS-matched, ~14 latent steps). This is logical-deduction with implicit branching — a workload type EPYC doesn't have in production.

### Why CODI is reference-only

- **GPT-2 scale validation only**: the largest model is LLaMA3.2-1B. GSM8K: 55.6% with CODI at 3.1× compression. Claim of "first implicit CoT method to match explicit CoT at GPT-2 scale" is real but does not generalize.
- **Deterministic by design**: the paper notes "CODI's current configuration is fully deterministic, whereas one advantage of CoT is its inherent stochasticity" — this is a self-reported limitation. For our use case, we generally run greedy / low-temperature, so determinism is less of a hit, but the lack of sampling diversity in the latent phase removes a tool from the orchestrator's belt.
- **Same engine-surgery and interpretability costs** as Coconut.

Architectural strength: self-distillation (single model, two forward passes per training step, hidden-state alignment loss `L_KD = (1/M) Σ_l |sg[h_teacher^l] − h_student^l|`) avoids Coconut's curriculum brittleness. If continuous-latent CoT ever becomes EPYC-relevant, CODI is the cleaner training recipe.

---

## Tier 2b — Consolidated Failure Modes

This is the "what could go wrong" register for the entire cluster, cross-referenced with adjacent intakes.

1. **Latent-CoT capability gap (exploration vs computation)** — `arxiv:2602.01148` documents a 63pp gap: 97% on ProsQA (exploration / branching) vs 34% on GSM8K (multi-step arithmetic computation). Latent CoT helps when the bottleneck is breadth-of-search; it hurts when the bottleneck is precise sequential computation. Agent traces are a mix — likely closer to the GSM8K regime for tool-call argument computation.

2. **Curriculum-learning necessity proof** — `arxiv:2602.01148` provides a theoretical argument (sketched in the Coconut paper's discussion) that direct training without curriculum cannot recover latent-CoT competence because the model has no signal connecting hidden-state-as-input to useful reasoning. Coconut's own ablation confirms this empirically (14.4% w/o curriculum). This makes Coconut-class methods inherently brittle to fine-tune.

3. **SIM-CoT instability at high compression** — `arxiv:2504.05081` + ICLR 2026 follow-up document that as the compression ratio increases, the latent CoT becomes increasingly OOD relative to training, and accuracy degrades non-linearly. The threshold varies by model and task — there is no universal "safe" compression ratio.

4. **Abstract CoT's own reported regressions** — AIME'25 −1.2pp, GPQA-Diamond −1.0pp despite 2.7×–7.9× token savings on those benchmarks. The paper frames these as "nearly matching" — but a real production decision on whether to deploy a 1pp accuracy hit for 3-8× token savings depends on workload cost asymmetry. For agent traces (long-tail tool-call reasoning) the token savings are large; for high-stakes math (AIME-style), 1pp matters.

5. **Soft Thinking OOD collapse** — paper acknowledges "feeding in continuous concept tokens during inference places the model in an out-of-distribution (OOD) regime. This can lead to model collapse if the reasoning process continues for too long." Cold-Stop mitigates but does not eliminate. **Validation cost**: longer-trace agent runs may hit this collapse mode where short-bench tests do not.

6. **Loss of human-readable trace** — for Coconut/CODI/Soft-Thinking, the intermediate computation has no surface-form representation. This is an operational regression for the orchestrator's debug-scorer path: when an agent makes a wrong call, we currently inspect the verbal trace. Latent-CoT removes that affordance. For Abstract CoT / Token Assorted, the trace IS made of (opaque) discrete tokens — replayable but not interpretable without the trained codebook.

7. **Quantization-noise interaction (Soft Thinking specific)** — see "Quant Interaction Concern" section. Untested in the seed paper; an experimental gate before production adoption.

---

## EPYC-Specific Integration Path

### 1. SOFT THINKING SPIKE (Tier 1 — training-free)

- **Branch**: `llama.cpp-experimental` (per `feedback_experimental_repo`).
- **Patch locations**:
  - `common/sampling.cpp` — new sampler type, top-k mixture computation, Cold-Stop entropy tracking.
  - `common/sampling.h` — extend `common_sampler_params` with `soft_thinking_*` fields.
  - `examples/server/server.cpp` + `common/arg.cpp` — wire CLI flags (`--soft-thinking-top-k`, `--soft-thinking-temperature`, `--soft-thinking-tau`, `--soft-thinking-k-consec`).
  - Decode path: when in soft-thinking mode, populate `llama_batch` with embedding vectors instead of token ids (the API already supports this via `batch.embd`).
- **Cost**: ~150 LoC, 1 dev-day for patch + 1 nightshift for sweep.
- **Test bench** (no concurrent inference per `feedback_no_concurrent_inference`):
  - GSM8K-200 subset on Qwen3-8B at F16 / Q8_0 / Q6_K / Q4_K_M to verify quant manifold stability.
  - HumanEval on worker_coder (30B-A3B Q4_K_M).
  - Per quant: sweep top-k ∈ {5, 10, 20}, tau ∈ {0.5, 1.0, 1.5}.
- **Success gate**: ≥10% token reduction at iso-pass@1 on coder bench on at least one production quant. Stretch: replicate +2.48pp / −22% on F16 to validate the patch is correct before quant-degradation investigation.
- **Kill criterion**: if F16 shows the paper's gains but Q4_K_M shows >2pp accuracy regression OR generation collapse, restrict to Q8_0+ workloads only or shelve.

### 2. TOKEN ASSORTED / ABSTRACT COT (Tier 3 — if fine-tuning ever lands)

- **Blocking dependency**: DGX Spark or equivalent GPU acquisition (per `project_dgx_spark_target` — not yet acquired).
- **Pick winner by EPYC-relevant metric**: tokens/decision at parity accuracy on agent traces (frontdoor + worker_coder).
- **Token Assorted first** (simpler — pure SFT, no RL infra needed), Abstract CoT as comparison.
- **Hard requirement**: indexed by model (per `feedback_model_not_role_indexing`) so retraining doesn't invalidate prior baselines.

### 3. COCONUT / CODI (Tier 4 — reference only)

- Cite when explaining why discrete-token approaches are preferred for EPYC.
- Do not pursue implementation under any current scope.

---

## Quant Interaction Concern (CRITICAL — load-bearing gate for Soft Thinking)

When llama.cpp evaluates a batch, the input embeddings are gathered via `ggml_get_rows(W_E, token_ids)`. `W_E` is stored in the model's native quant (e.g., Q4_K_M). The gather op dequantizes the relevant rows to fp16 (or bf16/fp32 depending on graph) before downstream computation. **Each row carries independent quantization noise** because Q4_K_M is block-wise: scales are per-block (typically 32 weights), and the dequantized values for different rows come from different blocks.

For Soft Thinking, the input becomes `ẽ = Σ_{i ∈ top_k} p_i · dequant(W_E[i])`. Let `dequant(W_E[i]) = e_true[i] + ε_i` where `ε_i` is the per-row quantization noise. Then:

```
ẽ = Σ p_i · e_true[i] + Σ p_i · ε_i
```

The first term is the "true" mixture (what fp16 training would see). The second term is a noise vector whose variance is `Σ p_i² · Var(ε_i)` — for a uniform top-k (`p_i = 1/k`), this is `(1/k) · Var(ε)`, which is **smaller** than the per-row noise. But mixtures are rarely uniform; the typical case is a peaked distribution where one or two entries dominate, in which case the noise floor is close to single-row Q4_K_M noise.

**Why this might still break the manifold**:
- The model has **never** seen a convex combination of embedding rows during training — the input distribution is exclusively `e(i)` for individual `i`. Even in fp16 there is some distribution-shift risk; Soft Thinking's reported gains suggest this risk is small for fp16.
- Under quantization, the mixture has correlated noise structure that single-row inputs don't have. Specifically, even when noise magnitude is comparable, the **direction** of the noise vector in embedding space is different from the directions the model saw during training (where it only saw `dequant(W_E[i])` directly, on the discrete manifold).
- The combination of OOD (mixture is off the discrete manifold) and quant noise (mixture's noise vector has unfamiliar structure) could compound.

**Search of paper + code**: paper does NOT test quantized models. The GitHub repo (eric-ai-lab/Soft-Thinking) ships an SGLang-based implementation; SGLang typically runs models in fp16/bf16 on GPUs. No INT8/INT4 path is documented in the repo description.

**Pre-adoption gate**: a side-by-side sweep on a small open model (Qwen3-8B) across F16 / Q8_0 / Q6_K / Q4_K_M, measuring pass@1 and generation-collapse rate on a 200-question GSM8K subset. If Q4_K_M loses more than 2pp pass@1 vs F16 (after the fp16 gain over baseline is established), the technique should be restricted to Q8_0+ quants in production. Estimated cost: 1 nightshift.

---

## Revised EPYC Priority

The intake-level entries treated these as `worth_investigating` (medium-to-high). The deep-dive confirms and refines:

- **Soft Thinking — promoted to Tier 1 active prototype candidate**. The reasoning-compression handoff already lists this as the highest-priority no-training quick win. The deep-dive adds: (a) a concrete patch-scope estimate (~150 LoC), (b) a quant-validation gate that must be cleared before claiming the paper's gains apply to EPYC, (c) Cold-Stop is non-optional — naive port without it will collapse.

- **Abstract CoT and Token Assorted — remain Tier 3 (training-required)**. Order them as Token Assorted-first when fine-tuning infra lands. Do not invest in reproducing either until the FT lane is real.

- **Coconut and CODI — confirmed Tier 4 (reference only)**. The deep-dive adds explicit reasons: (a) Coconut's GSM8K regression is large and the curriculum is brittle; (b) CODI is scale-limited (largest validated model is LLaMA3.2-1B); (c) both lose token-level traceability, which is an operational regression for agent debugging.

No promotion of any Tier-3/Tier-4 entry above Soft Thinking. No demotion.

---

## Open Questions for User

1. **Quant-gate priority**: Should we run the F16/Q8/Q6/Q4 sweep on Qwen3-8B for Soft Thinking before or in parallel with the llama.cpp patch? A pre-patch sweep would use a transformers-based reference implementation (paper code is SGLang-based) — would need to set that up.
2. **Soft Thinking patch scoping**: Is `llama.cpp-experimental` the right branch, or should this go directly into the production fork given how small the patch is (~150 LoC, all in sampler/server)?
3. **Cold-Stop hyperparameter defaults**: paper does not publish a recommended `(tau, k_consec)` per model family. Should we sweep these on EPYC, or assume defaults from the GitHub repo?
4. **Token Assorted vs Abstract CoT prioritization**: if fine-tuning infra materializes (DGX Spark or equivalent), is Token Assorted-first correct, or do you want Abstract CoT's larger compression ratio investigated first despite the RL infra cost?
5. **Cluster-level deferral**: should the entire continuous-latent track (Coconut / CODI) be marked as **closed** in the reasoning-compression handoff (not just Tier 4 reference), to clear the active investigation queue?

---

## References

### Primary sources (this cluster)

- **Abstract CoT** — Ramji, Naseem, Astudillo (IBM Research). "Thinking Without Words: Efficient Latent Reasoning with Abstract Chain-of-Thought." `arxiv:2604.22709`. No code release; datasets on HuggingFace (Dolci-Think-SFT, Dolci-Think-RL).
- **Coconut** — Hao, Sukhbaatar, Su, Li, Hu, Weston, Tian (Meta / UCSD). "Training Large Language Models to Reason in a Continuous Latent Space." `arxiv:2412.06769`. COLM 2025. No code link in paper.
- **CODI** — Shen, Yan, Zhang, Hu, Du, He. "CODI: Compressing Chain-of-Thought into Continuous Space via Self-Distillation." `arxiv:2502.21074`. No code link in paper; Appendix F has Python skeleton.
- **Token Assorted** — Su, Zhu, Xu, Jiao, Tian, Zheng (Meta). "Token Assorted: Mixing Latent and Text Tokens for Improved Language Model Reasoning." `arxiv:2502.03275`. No code link in paper; uses Llama Cookbook.
- **Soft Thinking** — Zhang, He, Yan, Shen, Zhao, Wang, Shen, Wang. "Soft Thinking: Unlocking the Reasoning Potential of LLMs in Continuous Concept Space." `arxiv:2505.15778`. **Code: https://github.com/eric-ai-lab/Soft-Thinking** (MIT + Apache-2.0 dual license).

### Cross-references (existing intakes / handoffs)

- `intake-110` (OPSDC) — self-distillation at token level; orthogonal compression family.
- `intake-126` (FlowSteer), `intake-127` (TrimR), `intake-128`, `intake-129` (short-m@k) — text-level CoT pruning.
- `intake-134` (CoLaR) — continuous latent compression (related to Coconut/CODI family).
- `intake-289` (Memento) — block-level reasoning compression.
- `intake-292` (InftyThink), `intake-276` — adjacent compression strategies.
- `arxiv:2602.01148` — latent-CoT capability gap and curriculum-necessity proof (Tier 2b reference).
- `arxiv:2504.05081` + ICLR 2026 follow-up — SIM-CoT instability evidence (Tier 2b reference).
- `arxiv:2505.15400` — adaptive thinking bimodal-brittleness evidence (ASRR ~32.5% budget reduction at ~1.2pp accuracy loss).

### Active handoff anchors

- `/workspace/handoffs/active/reasoning-compression.md` — primary anchor; this deep-dive integrates with §"Latent / Abstract CoT cluster" (lines 471–489).
- `/workspace/handoffs/active/per-request-reasoning-budget.md` — secondary anchor for budget-controlled deployment of Soft Thinking.
- `/workspace/handoffs/active/memento-block-reasoning-compression.md` — composability candidate (Memento KV-side + Soft Thinking token-side compression).
- `/workspace/handoffs/active/context-folding-progressive.md` — adjacent (different compression axis).

### EPYC infrastructure references

- `feedback_cpu_decode_bw_bound` — CPU decode is DRAM-BW-bound; fewer decode steps = wallclock reduction.
- `feedback_experimental_repo` — all llama.cpp experimental work goes in `llama.cpp-experimental`.
- `feedback_no_concurrent_inference` — bench sweeps must be sequential, not concurrent.
- `feedback_model_not_role_indexing` — any retrained-model artifact must be indexed by model + quant, never by orchestrator role.
- `project_dgx_spark_target` — DGX Spark not yet acquired; fine-tuning lane is currently blocked.
