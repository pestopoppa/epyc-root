# Vidya review checklist — 2026-08-10

Two decisions, both bounded. Tick a box, then tell me to apply it; nothing here is executed
until you do. Recommendations are mine and are meant to be overridden freely — the whole point
of this list is that the proposition-identity judgment is yours, not the fold's.

---

## Part 1 — Claim aliases (45 candidates)

Mark **S** (same proposition), **D** (different), or leave blank to skip. Approved rows become
`claim_alias` frames via `vidya alias-emit`, which refuses any approval without a reviewer name.

`⚠ same-source` rows are two index entries for ONE source: aliasing them is a correct identity
statement that must NOT be read as independent support. They are also evidence of a duplicate
entry — see Part 2.

### Near-verbatim (score ≥ 0.60) — recommend SAME  (5 rows)

**1.** `clm_intake_374_03` ⟷ `clm_intake_375_03`  ·  score 0.9496

> **A:** Repeated exposure outperforms coverage: repeating 2.5k samples 8x beats one-pass 20k under fixed 640-step budget

> **B:** Repeated exposure > coverage: repeating 2.5k samples 8x outperforms one-pass 20k under fixed 640-step budget

- [ ] **S** — same proposition&nbsp;&nbsp;&nbsp;- [ ] **D** — different&nbsp;&nbsp;&nbsp;*(recommend: SAME — near-verbatim restatement)*

**2.** `clm_intake_418_04` ⟷ `clm_intake_797_03`  ·  score 0.7567  ⚠ **same-source**

> **A:** Emerging directions include self-evolving harnesses and shared agent infrastructure

> **B:** Identifies emerging directions: self-evolving harnesses, shared agent infrastructure

- [ ] **S** — same proposition&nbsp;&nbsp;&nbsp;- [ ] **D** — different&nbsp;&nbsp;&nbsp;*(recommend: SAME (identity only) — one source recorded twice — aliasing is correct identity but is NOT corroboration)*

**3.** `clm_intake_962_01` ⟷ `clm_intake_966_03`  ·  score 0.7031

> **A:** HipKittens second blog supplies a DATED Mojo datapoint: Mojo "currently provides a warp-specialized matmul kernel as of 11/06/2025".

> **B:** NEW: a DATED Mojo datapoint - Mojo "currently provides a warp-specialized matmul kernel as of 11/06/2025".

- [ ] **S** — same proposition&nbsp;&nbsp;&nbsp;- [ ] **D** — different&nbsp;&nbsp;&nbsp;*(recommend: SAME — near-verbatim restatement)*

**4.** `clm_intake_595_02` ⟷ `clm_intake_596_02`  ·  score 0.6561

> **A:** Training pipeline: general PT → MT-oriented PT → SFT → RL + weak-to-strong RL

> **B:** Training pipeline: general PT + MT-oriented PT + SFT + on-policy distillation + RL

- [ ] **S** — same proposition&nbsp;&nbsp;&nbsp;- [ ] **D** — different&nbsp;&nbsp;&nbsp;*(recommend: SAME — near-verbatim restatement)*

**5.** `clm_intake_315_04` ⟷ `clm_intake_336_00`  ·  score 0.6245  ⚠ **same-source**

> **A:** Four conditions for Completely Neural Computer — Turing completeness, programmability, consistency, machine-native semantics

> **B:** Completely Neural Computer (CNC) requires: Turing completeness, universal programmability, behavior consistency, machine-native semantics

- [ ] **S** — same proposition&nbsp;&nbsp;&nbsp;- [ ] **D** — different&nbsp;&nbsp;&nbsp;*(recommend: SAME (identity only) — one source recorded twice — aliasing is correct identity but is NOT corroboration)*

### Judgement needed (0.45 ≤ score < 0.60)  (14 rows)

**6.** `clm_intake_536_01` ⟷ `clm_intake_541_01`  ·  score 0.5752

> **A:** Credit-assignment solved via local node rewards from an LLM judge (gpt-5-mini), with delegation bonus = MEAN child success (not sum) — explicitly prevents trivial-spawn exploit

> **B:** Credit-assignment solved with local node rewards from an LLM judge (gpt-5-mini): each node scored on (a) own sub-task success and (b) MEAN child success (mean — not sum — blocks trivial-spawn exploit)

- [ ] **S** — same proposition&nbsp;&nbsp;&nbsp;- [ ] **D** — different&nbsp;&nbsp;&nbsp;*(recommend: READ IT — same subject, wording differs enough that only you can tell)*

**7.** `clm_intake_737_04` ⟷ `clm_intake_738_02`  ·  score 0.5539

> **A:** Bundles DSpark (semi-autoregressive drafter) whose released numbers claim +26.7-30.9% acceptance length over EAGLE-3 and +16.3-18.4% over DFlash on Qwen3 4B/8B/14B.

> **B:** Reports +26.7-30.9% acceptance length over EAGLE-3 and +16.3-18.4% over DFlash on Qwen3 4B/8B/14B.

- [ ] **S** — same proposition&nbsp;&nbsp;&nbsp;- [ ] **D** — different&nbsp;&nbsp;&nbsp;*(recommend: READ IT — same subject, wording differs enough that only you can tell)*

**8.** `clm_intake_418_01` ⟷ `clm_intake_797_00`  ·  score 0.5512  ⚠ **same-source**

> **A:** Three-dimensional externalization model: memory externalizes state, skills externalize procedural expertise, protocols externalize interaction structure

> **B:** Reviews the shift from model weights to externalized infrastructure: memory externalizes state, skills externalize procedural expertise, protocols externalize interaction structure

- [ ] **S** — same proposition&nbsp;&nbsp;&nbsp;- [ ] **D** — different&nbsp;&nbsp;&nbsp;*(recommend: SAME (identity only) — one source recorded twice — aliasing is correct identity but is NOT corroboration)*

**9.** `clm_intake_268_01` ⟷ `clm_intake_277_02`  ·  score 0.5411

> **A:** Three-layer architecture (raw sources, LLM-maintained wiki, schema config) is essential

> **B:** Three-layer architecture (raw sources / wiki pages / schema)

- [ ] **S** — same proposition&nbsp;&nbsp;&nbsp;- [ ] **D** — different&nbsp;&nbsp;&nbsp;*(recommend: READ IT — same subject, wording differs enough that only you can tell)*

**10.** `clm_intake_422_02` ⟷ `clm_intake_423_02`  ·  score 0.5393

> **A:** Achieves up to 7.2% prefill latency reduction and 8.1% throughput gain on A100 GPU (DeepSeek R1 8B / Qwen3 8B)

> **B:** 6.6-8.1% single-batch throughput improvement and 7.2% prefill latency reduction on A100 with DeepSeek R1 8B and Qwen3 8B

- [ ] **S** — same proposition&nbsp;&nbsp;&nbsp;- [ ] **D** — different&nbsp;&nbsp;&nbsp;*(recommend: READ IT — same subject, wording differs enough that only you can tell)*

**11.** `clm_intake_536_03` ⟷ `clm_intake_541_03`  ·  score 0.5299

> **A:** Three core training tricks: (1) multi-task objective across tree depths yields automatic curriculum; (2) leave-one-out (LOO) baseline shared across rollout group reduces variance; (3) depth-level inverse-frequency weighting prevents leaf-trajectory domination

> **B:** Training stack: (1) multi-task objective across depths (auto-curriculum); (2) leave-one-out (LOO) baseline shared across rollout group; (3) depth-level inverse-frequency weighting

- [ ] **S** — same proposition&nbsp;&nbsp;&nbsp;- [ ] **D** — different&nbsp;&nbsp;&nbsp;*(recommend: READ IT — same subject, wording differs enough that only you can tell)*

**12.** `clm_intake_279_01` ⟷ `clm_intake_281_00`  ·  score 0.5267

> **A:** 256 experts, 40B active params per token, 80 layers

> **B:** 744B total / 40B active MoE with 256 experts, 80 layers

- [ ] **S** — same proposition&nbsp;&nbsp;&nbsp;- [ ] **D** — different&nbsp;&nbsp;&nbsp;*(recommend: READ IT — same subject, wording differs enough that only you can tell)*

**13.** `clm_intake_511_03` ⟷ `clm_intake_512_02`  ·  score 0.5165

> **A:** The backend LLM is hot-swappable across GPT-4.1 / Claude Opus 4.1 / Gemini 2.5 Flash, allowing per-task tradeoff of reasoning depth, cost, and speed.

> **B:** Backend LLM is hot-swappable (GPT-4.1, Claude Opus 4.1, Gemini 2.5 Flash) so users can trade reasoning depth, cost, and speed per task.

- [ ] **S** — same proposition&nbsp;&nbsp;&nbsp;- [ ] **D** — different&nbsp;&nbsp;&nbsp;*(recommend: READ IT — same subject, wording differs enough that only you can tell)*

**14.** `clm_intake_403_00` ⟷ `clm_intake_404_00`  ·  score 0.5018

> **A:** TPO decouples target distribution construction from parameter optimization — constructs closed-form target q_i proportional to p_old_i * exp(u_i/eta), fits via cross-entropy loss

> **B:** TPO separates target distribution construction from parameter optimization — given scored completions, constructs q_i proportional to p_old_i * exp(u_i/eta) and fits via cross-entropy. Gradient is (p - q), vanishing at convergence.

- [ ] **S** — same proposition&nbsp;&nbsp;&nbsp;- [ ] **D** — different&nbsp;&nbsp;&nbsp;*(recommend: READ IT — same subject, wording differs enough that only you can tell)*

**15.** `clm_intake_712_00` ⟷ `clm_intake_714_00`  ·  score 0.4835

> **A:** Fusion gives any model access to multi-model deliberation: the outer model invokes the tool, a panel answers in parallel, a judge compares responses, and structured analysis returns for the final answer.

> **B:** Fusion is a model-invoked server tool implementing Mixture-of-Agents: a panel answers in parallel, a judge compares, structured analysis JSON returns to the outer model for the final answer.

- [ ] **S** — same proposition&nbsp;&nbsp;&nbsp;- [ ] **D** — different&nbsp;&nbsp;&nbsp;*(recommend: READ IT — same subject, wording differs enough that only you can tell)*

**16.** `clm_intake_112_01` ⟷ `clm_intake_462_04`  ·  score 0.4729

> **A:** Advanced parallelism (tensor, pipeline, data, expert, context)

> **B:** Tensor / pipeline / data / expert / context parallelism with disaggregated prefill, decode, encode

- [ ] **S** — same proposition&nbsp;&nbsp;&nbsp;- [ ] **D** — different&nbsp;&nbsp;&nbsp;*(recommend: READ IT — same subject, wording differs enough that only you can tell)*

**17.** `clm_intake_254_04` ⟷ `clm_intake_411_04`  ·  score 0.4669

> **A:** MCP server integration for tool extensibility

> **B:** MCP server integration for extensible tool ecosystems

- [ ] **S** — same proposition&nbsp;&nbsp;&nbsp;- [ ] **D** — different&nbsp;&nbsp;&nbsp;*(recommend: READ IT — same subject, wording differs enough that only you can tell)*

**18.** `clm_intake_511_04` ⟷ `clm_intake_512_04`  ·  score 0.4581

> **A:** Accepted to ICASSP 2026; code, finetuning recipe, and weights released open-source.

> **B:** Inference + finetuning code and model weights released; paper accepted to ICASSP 2026.

- [ ] **S** — same proposition&nbsp;&nbsp;&nbsp;- [ ] **D** — different&nbsp;&nbsp;&nbsp;*(recommend: READ IT — same subject, wording differs enough that only you can tell)*

**19.** `clm_intake_177_03` ⟷ `clm_intake_179_01`  ·  score 0.4561

> **A:** 2.10% wall-clock speedup on nanochat GPT-2 training (1.76h vs 1.80h)

> **B:** 1.76h time-to-GPT-2 (down from 1.80h baseline), 2.10% wall-clock speedup

- [ ] **S** — same proposition&nbsp;&nbsp;&nbsp;- [ ] **D** — different&nbsp;&nbsp;&nbsp;*(recommend: READ IT — same subject, wording differs enough that only you can tell)*

### Probably different (score < 0.45) — recommend DIFFERENT  (26 rows)

**20.** `clm_intake_186_02` ⟷ `clm_intake_387_03`  ·  score 0.4468

> **A:** 262K native context (1M with YaRN)

> **B:** 262K native context, extensible to 1M+ with YaRN scaling

- [ ] **S** — same proposition&nbsp;&nbsp;&nbsp;- [ ] **D** — different&nbsp;&nbsp;&nbsp;*(recommend: DIFFERENT — shared vocabulary, likely different propositions)*

**21.** `clm_intake_458_03` ⟷ `clm_intake_567_04`  ·  score 0.4392

> **A:** Integrated as the attention backend in SGLang, vLLM, and MLC-Engine

> **B:** Integrated into SGLang (not vLLM)

- [ ] **S** — same proposition&nbsp;&nbsp;&nbsp;- [ ] **D** — different&nbsp;&nbsp;&nbsp;*(recommend: DIFFERENT — shared vocabulary, likely different propositions)*

**22.** `clm_intake_152_05` ⟷ `clm_intake_387_03`  ·  score 0.4363

> **A:** 262K native context with YaRN RoPE scaling for longer sequences

> **B:** 262K native context, extensible to 1M+ with YaRN scaling

- [ ] **S** — same proposition&nbsp;&nbsp;&nbsp;- [ ] **D** — different&nbsp;&nbsp;&nbsp;*(recommend: DIFFERENT — shared vocabulary, likely different propositions)*

**23.** `clm_intake_591_03` ⟷ `clm_intake_593_03`  ·  score 0.4322

> **A:** Code in Tencent/AngelSlim repo (intake-590); STQ1_0 kernel upstreamed to llama.cpp PR #22836

> **B:** Code in Tencent/AngelSlim repo (intake-590)

- [ ] **S** — same proposition&nbsp;&nbsp;&nbsp;- [ ] **D** — different&nbsp;&nbsp;&nbsp;*(recommend: DIFFERENT — shared vocabulary, likely different propositions)*

**24.** `clm_intake_433_03` ⟷ `clm_intake_591_04`  ·  score 0.4221

> **A:** CVPR 2026 accepted

> **B:** Accepted at ACL 2026

- [ ] **S** — same proposition&nbsp;&nbsp;&nbsp;- [ ] **D** — different&nbsp;&nbsp;&nbsp;*(recommend: DIFFERENT — shared vocabulary, likely different propositions)*

**25.** `clm_intake_152_05` ⟷ `clm_intake_186_02`  ·  score 0.4217

> **A:** 262K native context with YaRN RoPE scaling for longer sequences

> **B:** 262K native context (1M with YaRN)

- [ ] **S** — same proposition&nbsp;&nbsp;&nbsp;- [ ] **D** — different&nbsp;&nbsp;&nbsp;*(recommend: DIFFERENT — shared vocabulary, likely different propositions)*

**26.** `clm_intake_1006_00` ⟷ `clm_intake_1014_00`  ·  score 0.4211

> **A:** Liquid releases a 2.69B dense hybrid with 22 short-convolution blocks, eight GQA blocks, a 128K vocabulary, and 131,072-token context, post-trained for tool use and multi-turn agency.

> **B:** The released 2.69B checkpoint declares 30 layers comprising 22 short-convolution blocks and eight GQA blocks, a 128K vocabulary, and a 131,072-token context window.

- [ ] **S** — same proposition&nbsp;&nbsp;&nbsp;- [ ] **D** — different&nbsp;&nbsp;&nbsp;*(recommend: DIFFERENT — shared vocabulary, likely different propositions)*

**27.** `clm_intake_633_01` ⟷ `clm_intake_634_02`  ·  score 0.421

> **A:** Reports 4.71x speedup at 1.5B and 5.91x speedup at 8B in tokens/sec over standard AR baselines while preserving competitive quality

> **B:** Reports 4.71x–5.91x decoding tokens/sec vs AR baselines; ~2.5x over EAGLE-v3

- [ ] **S** — same proposition&nbsp;&nbsp;&nbsp;- [ ] **D** — different&nbsp;&nbsp;&nbsp;*(recommend: DIFFERENT — shared vocabulary, likely different propositions)*

**28.** `clm_intake_587_00` ⟷ `clm_intake_588_00`  ·  score 0.415

> **A:** ModelScope collection mirrors the HuggingFace tencent/hy-mt2 collection; same 3-size family (1.8B dense, 7B dense, 30B-A3B MoE) + FP8 + GGUF (vanilla / 2-bit / 1.25-bit on 1.8B)

> **B:** Collection of 10 model variants + IFMTBench dataset; 3-tier family (1.8B dense, 7B dense, 30B-A3B MoE), each in BF16 + FP8; 1.8B additionally in vanilla GGUF, 2-bit GGUF, 1.25-bit GGUF

- [ ] **S** — same proposition&nbsp;&nbsp;&nbsp;- [ ] **D** — different&nbsp;&nbsp;&nbsp;*(recommend: DIFFERENT — shared vocabulary, likely different propositions)*

**29.** `clm_intake_529_02` ⟷ `clm_intake_530_04`  ·  score 0.4147

> **A:** Architecture is a SwiGLU structural twin with σ=ReLU instead of σ=SiLU (gated-ReLU / ReGLU). Sparsity is dynamic per-token — weights remain dense BF16; D2T repacks the post-activation hidden every forward pass.

> **B:** Sparsity is dynamic per-token, not static structured. Weights remain dense BF16 — the D2T pass repacks the post-ReLU hidden vector every forward pass.

- [ ] **S** — same proposition&nbsp;&nbsp;&nbsp;- [ ] **D** — different&nbsp;&nbsp;&nbsp;*(recommend: DIFFERENT — shared vocabulary, likely different propositions)*

**30.** `clm_intake_942_00` ⟷ `clm_intake_955_01`  ·  score 0.4144

> **A:** Sparse MoE multimodal model, 276B total / 12B active: 42-layer decoder, each token routed to 6 of 256 experts plus 2 shared experts.

> **B:** 42-layer decoder-only transformer, each token routed to 6 of 256 experts plus 2 shared experts active on every token.

- [ ] **S** — same proposition&nbsp;&nbsp;&nbsp;- [ ] **D** — different&nbsp;&nbsp;&nbsp;*(recommend: DIFFERENT — shared vocabulary, likely different propositions)*

**31.** `clm_intake_325_04` ⟷ `clm_intake_654_03`  ·  score 0.4143

> **A:** Auto-create datasets from PDF, CSV, DOCX

> **B:** Data Recipes: graph-node visual workflow for dataset transformation; auto-create datasets from PDF/CSV/DOCX with no dataset required

- [ ] **S** — same proposition&nbsp;&nbsp;&nbsp;- [ ] **D** — different&nbsp;&nbsp;&nbsp;*(recommend: DIFFERENT — shared vocabulary, likely different propositions)*

**32.** `clm_intake_112_01` ⟷ `clm_intake_323_01`  ·  score 0.4059

> **A:** Advanced parallelism (tensor, pipeline, data, expert, context)

> **B:** 3D parallelism (tensor, pipeline, expert) plus sequence parallelism

- [ ] **S** — same proposition&nbsp;&nbsp;&nbsp;- [ ] **D** — different&nbsp;&nbsp;&nbsp;*(recommend: DIFFERENT — shared vocabulary, likely different propositions)*

**33.** `clm_intake_151_03` ⟷ `clm_intake_270_00`  ·  score 0.4017

> **A:** Hybrid search combining BM25 full-text and semantic retrieval with reciprocal rank fusion (RRF)

> **B:** Hybrid search combining BM25 full-text, vector semantic, and LLM re-ranking

- [ ] **S** — same proposition&nbsp;&nbsp;&nbsp;- [ ] **D** — different&nbsp;&nbsp;&nbsp;*(recommend: DIFFERENT — shared vocabulary, likely different propositions)*

**34.** `clm_intake_430_00` ⟷ `clm_intake_431_00`  ·  score 0.3899

> **A:** First ColBERT model to break 57 on BEIR (57.22 NDCG@10)

> **B:** First sub-150M dense model to break 56 NDCG@10 on BEIR (56.20)

- [ ] **S** — same proposition&nbsp;&nbsp;&nbsp;- [ ] **D** — different&nbsp;&nbsp;&nbsp;*(recommend: DIFFERENT — shared vocabulary, likely different propositions)*

**35.** `clm_intake_324_04` ⟷ `clm_intake_567_04`  ·  score 0.3887

> **A:** vLLM and SGLang integration

> **B:** Integrated into SGLang (not vLLM)

- [ ] **S** — same proposition&nbsp;&nbsp;&nbsp;- [ ] **D** — different&nbsp;&nbsp;&nbsp;*(recommend: DIFFERENT — shared vocabulary, likely different propositions)*

**36.** `clm_intake_144_03` ⟷ `clm_intake_254_04`  ·  score 0.3885

> **A:** MCP adapter support for tool integration

> **B:** MCP server integration for tool extensibility

- [ ] **S** — same proposition&nbsp;&nbsp;&nbsp;- [ ] **D** — different&nbsp;&nbsp;&nbsp;*(recommend: DIFFERENT — shared vocabulary, likely different propositions)*

**37.** `clm_intake_186_03` ⟷ `clm_intake_187_02`  ·  score 0.3878

> **A:** Standard qwen3moe architecture — no custom code needed

> **B:** Standard qwen3moe architecture, drop-in compatible

- [ ] **S** — same proposition&nbsp;&nbsp;&nbsp;- [ ] **D** — different&nbsp;&nbsp;&nbsp;*(recommend: DIFFERENT — shared vocabulary, likely different propositions)*

**38.** `clm_intake_775_01` ⟷ `clm_intake_778_02`  ·  score 0.3876

> **A:** Anonymous page fetch returns HTTP 401 on both /AliesTaha/fable-traces and the API endpoint - repo is gated or auth-walled; card content could not be inspected directly.

> **B:** Anonymous fetch returns HTTP 401 - gated; card content not directly inspected (all above from HF search index).

- [ ] **S** — same proposition&nbsp;&nbsp;&nbsp;- [ ] **D** — different&nbsp;&nbsp;&nbsp;*(recommend: DIFFERENT — shared vocabulary, likely different propositions)*

**39.** `clm_intake_536_02` ⟷ `clm_intake_541_02`  ·  score 0.3857

> **A:** Inference uses REPL-based execution tree: child outputs are first-class Python objects, asyncio.gather enables parallel children, child reasoning stays out of parent context (automatic context isolation)

> **B:** Inference uses a rooted execution tree on a Python REPL interface; delegation is async function (asyncio.gather for parallel independent children); child outputs are first-class Python objects parent inspects/slices BEFORE loading into context

- [ ] **S** — same proposition&nbsp;&nbsp;&nbsp;- [ ] **D** — different&nbsp;&nbsp;&nbsp;*(recommend: DIFFERENT — shared vocabulary, likely different propositions)*

**40.** `clm_intake_381_00` ⟷ `clm_intake_383_01`  ·  score 0.3716

> **A:** AA-Omniscience: 6,000-question hallucination benchmark (600 public, Apache 2.0) across 6 domains/42 topics — penalizes guessing, rewards abstention

> **B:** 6,000 questions across 6 domains/42 economically relevant topics with 600 public (Apache 2.0) on HuggingFace

- [ ] **S** — same proposition&nbsp;&nbsp;&nbsp;- [ ] **D** — different&nbsp;&nbsp;&nbsp;*(recommend: DIFFERENT — shared vocabulary, likely different propositions)*

**41.** `clm_intake_244_02` ⟷ `clm_intake_784_00`  ·  score 0.3701  ⚠ **same-source**

> **A:** Agentic proposer with filesystem access to source code, scores, and execution traces outperforms text-only optimizers

> **B:** Outer-loop system that searches over harness code for LLM applications using an agentic proposer with filesystem access to source code, scores, and execution traces of all prior candidates

- [ ] **S** — same proposition&nbsp;&nbsp;&nbsp;- [ ] **D** — different&nbsp;&nbsp;&nbsp;*(recommend: SAME (identity only) — one source recorded twice — aliasing is correct identity but is NOT corroboration)*

**42.** `clm_intake_721_00` ⟷ `clm_intake_722_00`  ·  score 0.3701

> **A:** Qwen3.6-35B-A3B ships a native NEXTN/MTP head; unsloth bundles it in-GGUF (no separate draft file).

> **B:** Qwen3.5-122B-A10B ships a native MTP head; unsloth bundles a GGUF.

- [ ] **S** — same proposition&nbsp;&nbsp;&nbsp;- [ ] **D** — different&nbsp;&nbsp;&nbsp;*(recommend: DIFFERENT — shared vocabulary, likely different propositions)*

**43.** `clm_intake_215_01` ⟷ `clm_intake_555_02`  ·  score 0.3676

> **A:** Training-free framework matching fine-tuning performance

> **B:** Training-free framework: no fine-tuning required on participating LLMs

- [ ] **S** — same proposition&nbsp;&nbsp;&nbsp;- [ ] **D** — different&nbsp;&nbsp;&nbsp;*(recommend: DIFFERENT — shared vocabulary, likely different propositions)*

**44.** `clm_intake_282_04` ⟷ `clm_intake_283_03`  ·  score 0.3609

> **A:** Targets AI agent pipelines that need shared state via filesystem conventions

> **B:** Shared state via standard filesystem conventions (subdirectories, files)

- [ ] **S** — same proposition&nbsp;&nbsp;&nbsp;- [ ] **D** — different&nbsp;&nbsp;&nbsp;*(recommend: DIFFERENT — shared vocabulary, likely different propositions)*

**45.** `clm_intake_196_00` ⟷ `clm_intake_197_00`  ·  score 0.3596

> **A:** EmotionPrompt combines emotional stimuli with task prompts for LLM performance gains

> **B:** Negative emotional stimuli improve LLM performance

- [ ] **S** — same proposition&nbsp;&nbsp;&nbsp;- [ ] **D** — different&nbsp;&nbsp;&nbsp;*(recommend: DIFFERENT — shared vocabulary, likely different propositions)*

---

## Part 2 — Duplicate-locator groups (5 groups, 11 entries)

Three of these were labelled `novelty: duplicate` by the intake process itself and then
persisted as full entries anyway, each with its own `key_claims`. Ticking those is confirming
a decision the pipeline already made, not making a new one.

| # | Group | What the evidence says | Recommendation |
|---|---|---|---|
| D5.1 | intake-772 · **intake-785** | 785 is `novelty: duplicate`, ingested 5 days later via `expansion`, `arxiv_id` stripped. 785 is cited by 7 entries. | **Merge into 772**, repoint 7 citations |
| D5.2 | intake-244 · **intake-784** | Same shape. 784 is cited by 9. 244 is `integrated` and cited by 17. | **Merge into 244**, repoint 9 citations |
| D5.3 | intake-418 · **intake-797** | Same shape. 797 cited by 1. | **Merge into 418**, repoint 1 citation |
| D5.4 | intake-315 · intake-336 | Same URL, same day, both `novelty: high`, both operator input, 4–5 claims each. Not flagged by the pipeline at all — the sweep missed a same-session collision. 336 is cited by nobody. | **Merge into 315** (or keep both if the two readings differ substantively — your call) |
| D5.5 | intake-693 · intake-783 · intake-901 | Same repo URL, three genuinely different artifacts: a structured-outputs reading, a re-read of repo features, and an X-post session demo. 901 is `dive-verified` and spawned 2 handoffs. | **Keep all three**, record why they differ — this is the companion-artifact case the rules protect |

- [ ] D5.1 merge 785 → 772
- [ ] D5.2 merge 784 → 244
- [ ] D5.3 merge 797 → 418
- [ ] D5.4 merge 336 → 315
- [ ] D5.5 keep 693/783/901, record the distinction

A merge means: repoint every `cross_references.intake_entries` pointer to the surviving entry,
fold any claims the duplicate has that the original lacks into the original, then remove the
duplicate. Nothing is deleted without its citations being rehomed first.

