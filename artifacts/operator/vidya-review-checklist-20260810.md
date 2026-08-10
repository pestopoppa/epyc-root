# Alias review — 2026-08-10

**19 judgment calls, then 5 merge decisions.** Everything mechanically decidable
has been decided and moved to the appendix.

---

## How to answer

One question per row: **do A and B assert the same proposition?**

- **S** — one claim written twice.
- **D** — two claims, however similar the wording.
- blank — skipped, emits nothing.

That is the whole task. You are not judging whether the claim is true, whether the sources
are independent, or whether merging is a good idea — those are handled elsewhere and none of
them changes the answer to this question.

---

## Part 1 — Same proposition?

**1.**

> **A:** Repeated exposure outperforms coverage: repeating 2.5k samples 8x beats one-pass 20k under fixed 640-step budget

> **B:** Repeated exposure > coverage: repeating 2.5k samples 8x outperforms one-pass 20k under fixed 640-step budget

- [ ] **S**&nbsp;&nbsp;&nbsp;&nbsp;- [ ] **D**

**2.**

> **A:** Emerging directions include self-evolving harnesses and shared agent infrastructure

> **B:** Identifies emerging directions: self-evolving harnesses, shared agent infrastructure

- [ ] **S**&nbsp;&nbsp;&nbsp;&nbsp;- [ ] **D**

**3.**

> **A:** HipKittens second blog supplies a DATED Mojo datapoint: Mojo "currently provides a warp-specialized matmul kernel as of 11/06/2025".

> **B:** NEW: a DATED Mojo datapoint - Mojo "currently provides a warp-specialized matmul kernel as of 11/06/2025".

- [ ] **S**&nbsp;&nbsp;&nbsp;&nbsp;- [ ] **D**

**4.**

> **A:** Training pipeline: general PT → MT-oriented PT → SFT → RL + weak-to-strong RL

> **B:** Training pipeline: general PT + MT-oriented PT + SFT + on-policy distillation + RL

- [ ] **S**&nbsp;&nbsp;&nbsp;&nbsp;- [ ] **D**

**5.**

> **A:** Four conditions for Completely Neural Computer — Turing completeness, programmability, consistency, machine-native semantics

> **B:** Completely Neural Computer (CNC) requires: Turing completeness, universal programmability, behavior consistency, machine-native semantics

- [ ] **S**&nbsp;&nbsp;&nbsp;&nbsp;- [ ] **D**

**6.**

> **A:** Credit-assignment solved via local node rewards from an LLM judge (gpt-5-mini), with delegation bonus = MEAN child success (not sum) — explicitly prevents trivial-spawn exploit

> **B:** Credit-assignment solved with local node rewards from an LLM judge (gpt-5-mini): each node scored on (a) own sub-task success and (b) MEAN child success (mean — not sum — blocks trivial-spawn exploit)

- [ ] **S**&nbsp;&nbsp;&nbsp;&nbsp;- [ ] **D**

**7.**

> **A:** Bundles DSpark (semi-autoregressive drafter) whose released numbers claim +26.7-30.9% acceptance length over EAGLE-3 and +16.3-18.4% over DFlash on Qwen3 4B/8B/14B.

> **B:** Reports +26.7-30.9% acceptance length over EAGLE-3 and +16.3-18.4% over DFlash on Qwen3 4B/8B/14B.

- [ ] **S**&nbsp;&nbsp;&nbsp;&nbsp;- [ ] **D**

**8.**

> **A:** Three-dimensional externalization model: memory externalizes state, skills externalize procedural expertise, protocols externalize interaction structure

> **B:** Reviews the shift from model weights to externalized infrastructure: memory externalizes state, skills externalize procedural expertise, protocols externalize interaction structure

- [ ] **S**&nbsp;&nbsp;&nbsp;&nbsp;- [ ] **D**

**9.**

> **A:** Three-layer architecture (raw sources, LLM-maintained wiki, schema config) is essential

> **B:** Three-layer architecture (raw sources / wiki pages / schema)

- [ ] **S**&nbsp;&nbsp;&nbsp;&nbsp;- [ ] **D**

**10.**

> **A:** Achieves up to 7.2% prefill latency reduction and 8.1% throughput gain on A100 GPU (DeepSeek R1 8B / Qwen3 8B)

> **B:** 6.6-8.1% single-batch throughput improvement and 7.2% prefill latency reduction on A100 with DeepSeek R1 8B and Qwen3 8B

- [ ] **S**&nbsp;&nbsp;&nbsp;&nbsp;- [ ] **D**

**11.**

> **A:** Three core training tricks: (1) multi-task objective across tree depths yields automatic curriculum; (2) leave-one-out (LOO) baseline shared across rollout group reduces variance; (3) depth-level inverse-frequency weighting prevents leaf-trajectory domination

> **B:** Training stack: (1) multi-task objective across depths (auto-curriculum); (2) leave-one-out (LOO) baseline shared across rollout group; (3) depth-level inverse-frequency weighting

- [ ] **S**&nbsp;&nbsp;&nbsp;&nbsp;- [ ] **D**

**12.**

> **A:** 256 experts, 40B active params per token, 80 layers

> **B:** 744B total / 40B active MoE with 256 experts, 80 layers

- [ ] **S**&nbsp;&nbsp;&nbsp;&nbsp;- [ ] **D**

**13.**

> **A:** The backend LLM is hot-swappable across GPT-4.1 / Claude Opus 4.1 / Gemini 2.5 Flash, allowing per-task tradeoff of reasoning depth, cost, and speed.

> **B:** Backend LLM is hot-swappable (GPT-4.1, Claude Opus 4.1, Gemini 2.5 Flash) so users can trade reasoning depth, cost, and speed per task.

- [ ] **S**&nbsp;&nbsp;&nbsp;&nbsp;- [ ] **D**

**14.**

> **A:** TPO decouples target distribution construction from parameter optimization — constructs closed-form target q_i proportional to p_old_i * exp(u_i/eta), fits via cross-entropy loss

> **B:** TPO separates target distribution construction from parameter optimization — given scored completions, constructs q_i proportional to p_old_i * exp(u_i/eta) and fits via cross-entropy. Gradient is (p - q), vanishing at convergence.

- [ ] **S**&nbsp;&nbsp;&nbsp;&nbsp;- [ ] **D**

**15.**

> **A:** Fusion gives any model access to multi-model deliberation: the outer model invokes the tool, a panel answers in parallel, a judge compares responses, and structured analysis returns for the final answer.

> **B:** Fusion is a model-invoked server tool implementing Mixture-of-Agents: a panel answers in parallel, a judge compares, structured analysis JSON returns to the outer model for the final answer.

- [ ] **S**&nbsp;&nbsp;&nbsp;&nbsp;- [ ] **D**

**16.**

> **A:** Advanced parallelism (tensor, pipeline, data, expert, context)

> **B:** Tensor / pipeline / data / expert / context parallelism with disaggregated prefill, decode, encode

- [ ] **S**&nbsp;&nbsp;&nbsp;&nbsp;- [ ] **D**

**17.**

> **A:** MCP server integration for tool extensibility

> **B:** MCP server integration for extensible tool ecosystems

- [ ] **S**&nbsp;&nbsp;&nbsp;&nbsp;- [ ] **D**

**18.**

> **A:** Accepted to ICASSP 2026; code, finetuning recipe, and weights released open-source.

> **B:** Inference + finetuning code and model weights released; paper accepted to ICASSP 2026.

- [ ] **S**&nbsp;&nbsp;&nbsp;&nbsp;- [ ] **D**

**19.**

> **A:** 2.10% wall-clock speedup on nanochat GPT-2 training (1.76h vs 1.80h)

> **B:** 1.76h time-to-GPT-2 (down from 1.80h baseline), 2.10% wall-clock speedup

- [ ] **S**&nbsp;&nbsp;&nbsp;&nbsp;- [ ] **D**

---

## Part 2 — Five duplicate entries to merge

Same URL or arXiv id, two index entries. Three were labelled `novelty: duplicate` by the
intake pipeline and then saved as full entries anyway, so ticking those confirms a decision
already made. Merging repoints every citation to the surviving entry and folds in any claims
the duplicate has that the original lacks; nothing is removed before its citations are rehomed.

- [ ] **intake-785 → intake-772** · *Darwin Gödel Machine* · pipeline-labelled duplicate, 7 citations to repoint
- [ ] **intake-784 → intake-244** · *Meta-Harness* · pipeline-labelled duplicate, 9 citations to repoint
- [ ] **intake-797 → intake-418** · *Externalization in LLM Agents* · pipeline-labelled duplicate, 1 citation to repoint
- [ ] **intake-336 → intake-315** · *Neural Computer* · same URL, same day, both saved as new; 336 has no citations
- [ ] **keep intake-693 / 783 / 901 separate** · *fast-rlm* · one repo, three genuinely different readings; 901 is dive-verified and spawned 2 handoffs

---

## Appendix — decided without you

26 of the 45 candidates. All treated as **different**. A missed alias costs recall and
can be recovered on a later run; a wrong alias manufactures corroboration, so the default runs
that way on purpose. Skim only if you want to override one.

| # | Reason | A | B |
|---|---|---|---|
| A1 | little shared wording | 262K native context (1M with YaRN) | 262K native context, extensible to 1M+ with YaRN scaling |
| A2 | little shared wording | Integrated as the attention backend in SGLang, vLLM, and MLC-Engine | Integrated into SGLang (not vLLM) |
| A3 | little shared wording | 262K native context with YaRN RoPE scaling for longer sequences | 262K native context, extensible to 1M+ with YaRN scaling |
| A4 | little shared wording | Code in Tencent/AngelSlim repo (intake-590); STQ1_0 kernel upstreamed to llama.cpp PR #22836 | Code in Tencent/AngelSlim repo (intake-590) |
| A5 | little shared wording | CVPR 2026 accepted | Accepted at ACL 2026 |
| A6 | little shared wording | 262K native context with YaRN RoPE scaling for longer sequences | 262K native context (1M with YaRN) |
| A7 | little shared wording | Liquid releases a 2.69B dense hybrid with 22 short-convolution blocks, eight GQA blocks, a 128K vocabulary, an | The released 2.69B checkpoint declares 30 layers comprising 22 short-convolution blocks and eight GQA blocks,  |
| A8 | different magnitudes | Reports 4.71x speedup at 1.5B and 5.91x speedup at 8B in tokens/sec over standard AR baselines while preservin | Reports 4.71x–5.91x decoding tokens/sec vs AR baselines; ~2.5x over EAGLE-v3 |
| A9 | little shared wording | ModelScope collection mirrors the HuggingFace tencent/hy-mt2 collection; same 3-size family (1.8B dense, 7B de | Collection of 10 model variants + IFMTBench dataset; 3-tier family (1.8B dense, 7B dense, 30B-A3B MoE), each i |
| A10 | little shared wording | Architecture is a SwiGLU structural twin with σ=ReLU instead of σ=SiLU (gated-ReLU / ReGLU). Sparsity is dynam | Sparsity is dynamic per-token, not static structured. Weights remain dense BF16 — the D2T pass repacks the pos |
| A11 | little shared wording | Sparse MoE multimodal model, 276B total / 12B active: 42-layer decoder, each token routed to 6 of 256 experts  | 42-layer decoder-only transformer, each token routed to 6 of 256 experts plus 2 shared experts active on every |
| A12 | little shared wording | Auto-create datasets from PDF, CSV, DOCX | Data Recipes: graph-node visual workflow for dataset transformation; auto-create datasets from PDF/CSV/DOCX wi |
| A13 | little shared wording | Advanced parallelism (tensor, pipeline, data, expert, context) | 3D parallelism (tensor, pipeline, expert) plus sequence parallelism |
| A14 | little shared wording | Hybrid search combining BM25 full-text and semantic retrieval with reciprocal rank fusion (RRF) | Hybrid search combining BM25 full-text, vector semantic, and LLM re-ranking |
| A15 | different magnitudes | First ColBERT model to break 57 on BEIR (57.22 NDCG@10) | First sub-150M dense model to break 56 NDCG@10 on BEIR (56.20) |
| A16 | little shared wording | vLLM and SGLang integration | Integrated into SGLang (not vLLM) |
| A17 | little shared wording | MCP adapter support for tool integration | MCP server integration for tool extensibility |
| A18 | little shared wording | Standard qwen3moe architecture — no custom code needed | Standard qwen3moe architecture, drop-in compatible |
| A19 | little shared wording | Anonymous page fetch returns HTTP 401 on both /AliesTaha/fable-traces and the API endpoint - repo is gated or  | Anonymous fetch returns HTTP 401 - gated; card content not directly inspected (all above from HF search index) |
| A20 | little shared wording | Inference uses REPL-based execution tree: child outputs are first-class Python objects, asyncio.gather enables | Inference uses a rooted execution tree on a Python REPL interface; delegation is async function (asyncio.gathe |
| A21 | little shared wording | AA-Omniscience: 6,000-question hallucination benchmark (600 public, Apache 2.0) across 6 domains/42 topics — p | 6,000 questions across 6 domains/42 economically relevant topics with 600 public (Apache 2.0) on HuggingFace |
| A22 | little shared wording | Agentic proposer with filesystem access to source code, scores, and execution traces outperforms text-only opt | Outer-loop system that searches over harness code for LLM applications using an agentic proposer with filesyst |
| A23 | different magnitudes | Qwen3.6-35B-A3B ships a native NEXTN/MTP head; unsloth bundles it in-GGUF (no separate draft file). | Qwen3.5-122B-A10B ships a native MTP head; unsloth bundles a GGUF. |
| A24 | little shared wording | Training-free framework matching fine-tuning performance | Training-free framework: no fine-tuning required on participating LLMs |
| A25 | little shared wording | Targets AI agent pipelines that need shared state via filesystem conventions | Shared state via standard filesystem conventions (subdirectories, files) |
| A26 | little shared wording | EmotionPrompt combines emotional stimuli with task prompts for LLM performance gains | Negative emotional stimuli improve LLM performance |

*Generated from `artifacts/operator/vidya-alias-worksheet-20260810.yaml`.*

