# ColBERT Reranker for web_research Pipeline

**Status**: S1–S4 complete; S5 gated on AR-3 web_research data (go/no-go analysis)
**Created**: 2026-04-05 (extracted from `04-mirothinker-worker-eval.md` intake-174)
**Updated**: 2026-04-14 (finalized: architecture resolved, model selected, work items sequenced)
**Priority**: MEDIUM
**Effort**: Medium
**Depends on**: AR-3 autopilot data — S5 requires the post-AR-3 irrelevant-page analysis to confirm >20% waste rate before implementation proceeds. No infrastructure dependency; this is a data gate. See "Post-AR-3 Analysis" section below for the go/no-go script and thresholds.

## Objective

Add a reranking stage to the `web_research` pipeline between DuckDuckGo search and page fetch. Currently the explore worker receives all fetched pages and synthesizes directly, spending tokens on low-relevance pages that DuckDuckGo ranked highly by keyword match but are semantically weak for reasoning tasks.

## Implementation Decision

### Model

| Model | Params | BEIR NDCG@10 | License | Verdict |
|-------|--------|-------------|---------|---------|
| **ColBERT-Zero** (LightOn) | <150M | 55.43 | Verify from HF card (public data training) | **PRIMARY** |
| **mxbai-edge-colbert** (Mixedbread) | 17M | Outperforms ColBERTv2 on NanoBEIR | Apache 2.0 | **FALLBACK** |
| ~~Reason-ModernColBERT~~ (LightOn) | 150M | 22.62/30.28 BRIGHT | CC-BY-NC-4.0 (non-commercial) | **ELIMINATED** |

**ColBERT-Zero** is the primary choice: strongest general-purpose BEIR score (55.43), same LightOn/ModernBERT family as our deployed GTE-ModernColBERT-v1, trained on public data only. License must be verified from HuggingFace model card during S3.

**mxbai-edge-colbert 17M** is the fallback: Apache 2.0 (license-clean), 6x smaller, 3x faster CPU encoding than ColBERTv2, still outperforms ColBERTv2. Use if ColBERT-Zero license is restrictive or if sub-ms latency is critical.

**Reason-ModernColBERT** is eliminated: CC-BY-NC-4.0 prohibits commercial use. Self-training path exists (~2hr fine-tune on ReasonIR data) but is unnecessary overhead when ColBERT-Zero exists.

### Library: ONNX Runtime (revised 2026-04-14)

**Why ONNX Runtime**: C++ engine with Python bindings, lightweight (no PyTorch), cp314-compatible, already-on-disk model (`model_int8.onnx`). Per-token 128-dim embeddings + MaxSim in numpy — the full pipeline is ~15 lines of code.

**Why NOT PyLate**: `fast-plaid` and `voyager` dependencies have no cp314 wheels. The orchestrator venv is Python 3.14. PyLate would require a separate venv or subprocess — unnecessary overhead when ONNX Runtime provides identical functionality.

**Why NOT alternatives**:
- **NextPLAID container**: Search-only API, no reranking endpoint. Designed for corpus-scale retrieval, not 10-snippet reranking.
- **RAGatouille**: Wraps ColBERT for LangChain/LlamaIndex integration. We use neither framework.
- **llama-server /reranking**: Would work (native C++ via HTTP) but requires GGUF conversion of the ColBERT model. ONNX model is already on disk.
- **sentence-transformers**: No cp314 wheels (same issue as PyLate). Would also pull PyTorch (~2GB).

### Architecture: Snippet-level pre-fetch reranking

```
DDG/Brave search (8-10 results)         ← increase max_results when flag on
  → encode snippets + query via ColBERT  ← <1ms on EPYC for 10 snippets
  → rerank by MaxSim, take top 3         ← NEW: semantic filter
  → fetch top 3 pages (15s timeout each)
  → paragraph-level SHA256 dedup
  → synthesize via explore worker (45s each)
  → return combined summaries
```

**Why snippet-level, not page-level**: DDG already returns snippets for all results. Encoding snippets (not full pages) via ColBERT is sub-ms and avoids fetching irrelevant pages entirely. This saves both fetch time (15s timeout per page) AND synthesis time (45s per page).

**Why in-process, not container**: The task is encoding 10 short strings + 1 query and computing 10 MaxSim scores. This is a matrix multiplication, not a retrieval problem. Model loaded lazily on first call with flag enabled, stays in memory.

## Existing Infrastructure

| Component | Location | Reuse? |
|-----------|----------|--------|
| NextPLAID containers (:8088/:8089) | `orchestrator_stack.py` lines 398-430 | Pattern reference only — NextPLAID is overkill for this task |
| `next_plaid_client` package | `code_search.py` lines 46-60 | Not needed (no NextPLAID container) |
| `sentence-transformers` | Already installed (CLIP vision pipeline) | PyLate builds on this — no new heavy dependency |
| `FeatureSpec` registry | `src/features.py` lines 75-129 | Use for `web_research_rerank` flag |
| GTE-ModernColBERT-v1 on :8089 | Deployed, 128-dim INT8 | Different use case (docs retrieval), validates ColBERT-family CPU feasibility |

## Pipeline Analysis (2026-04-14)

Audited `epyc-orchestrator/src/tools/web/research.py` and `search.py`:

```
DDG/Brave search (5 results)
  → fetch top 3 pages (6000 chars each, 15s timeout, parallel)
  → paragraph-level SHA256 dedup
  → synthesize ALL 3 via explore worker (Qwen2.5-7B, 512 tok, 45s timeout)
  → return combined summaries
```

**Key finding: zero relevance filtering.** All 3 fetched pages get synthesized regardless of relevance. The worker prompt says "if not relevant, say so briefly" — so a 7B model doing a 45-second inference call is the only relevance gate. Each wasted synthesis costs ~45s of worker compute.

**Cost of NOT reranking:** With 3 pages synthesized per query, even 1 irrelevant page = 33% waste in worker inference. At scale (autopilot sessions with many web_research calls), this compounds.

## combined_ops.py Relationship

`batch_web_search()` in `combined_ops.py` calls `web_search()` (DDG/Brave search returning titles/URLs/snippets), NOT `web_research()` (the full fetch+synthesize pipeline). Reranking in `research.py` does **not** automatically cover batch search in combined_ops.

**Future extension**: If reranker proves valuable, expose a `rerank_snippets(query, snippets)` utility function that `combined_ops.py` could also call.

## Post-AR-3 Analysis

After AR-3 completes (or accumulates sufficient web_research trials), run the analysis script to extract the go/no-go decision:

```bash
cd /mnt/raid0/llm/epyc-inference-research
python3 scripts/benchmark/analyze_web_research_baseline.py /mnt/raid0/llm/epyc-inference-research/benchmarks/results/eval
```

The script reports:
- Total pages synthesized across all web_research calls
- Pages classified irrelevant (count + percentage)
- **Go/no-go recommendation**: `>20%` → proceed to S3, `10-20%` → marginal, `<10%` → skip

If checkpoint data is insufficient (few web_research calls), also grep orchestrator logs as a backup:

```bash
grep "web_research relevance summary" /path/to/orchestrator.log | tail -20
```

## Work Items

- [x] **S1: Instrument relevance logging** ✅ 2026-04-14 — Added `_is_irrelevant_synthesis()` heuristic + per-page/summary logging to `_web_research_impl()`. Returns `pages_irrelevant` + `irrelevant_rate` in response dict. 5 tests added. **Data collection folded into AR-3 Package D** — AR-3 includes a `web_research` sentinel suite (50 questions) that will trigger this instrumentation automatically during autopilot runs.
  - File: `epyc-orchestrator/src/tools/web/research.py` (lines 44-69: detection, lines 376-400: instrumentation)
  - Tests: `epyc-orchestrator/tests/unit/test_web_research_dedup.py` (TestIrrelevantSynthesisDetection, 5 cases)

- [x] **S2: Register feature flag** ✅ 2026-04-14 — Added to `src/features.py` FeatureSpec registry + Features dataclass. Registry consistency test passes. Telemetry pipeline wired: `pages_irrelevant` + `irrelevant_rate` captured in `repl_executor.py`, `chat_delegation.py`, `WebResearchTelemetry`, and `analyze_web_research_baseline.py`.
  ```python
  FeatureSpec("web_research_rerank", False, False, "WEB_RESEARCH_RERANK",
              "ColBERT snippet reranking in web_research pipeline")
  ```
  Runtime: `ORCHESTRATOR_WEB_RESEARCH_RERANK=1`
  - File: `epyc-orchestrator/src/features.py`
  - Effort: ~15min

- [x] **S3: Model + encoding pipeline setup** ✅ 2026-04-14 — **REVISED**: PyLate eliminated. Using existing GTE-ModernColBERT-v1 ONNX (already on disk at `/mnt/raid0/llm/models/gte-moderncolbert-v1-onnx/`) + `onnxruntime` (installed in orchestrator venv). No download needed.
  - **License**: ColBERT-Zero = Apache-2.0 (verified from HF model card). mxbai-edge-colbert = Apache-2.0. GTE-ModernColBERT-v1 = already deployed. All clear for commercial use.
  - **PyLate eliminated**: `fast-plaid` and `voyager` dependencies have no cp314 wheels (orchestrator venv is Python 3.14). ONNX Runtime (1.24.4) has cp314 wheels and provides the same encoding capability with zero PyTorch dependency.
  - **Pipeline**: `onnxruntime` + `tokenizers` (both already in venv) → load `model_int8.onnx` (144MB INT8) → per-token 128-dim embeddings → MaxSim scoring in numpy.
  - **Model decision**: GTE-ModernColBERT-v1 (BEIR 54.67) vs ColBERT-Zero (BEIR 55.43) — <1pp difference. GTE already on disk, verified working. ColBERT-Zero download deferred unless accuracy issues emerge in S6.
  - Model path: `/mnt/raid0/llm/models/gte-moderncolbert-v1-onnx/model_int8.onnx`
  - Dependencies added: `onnxruntime==1.24.4` (+ flatbuffers, protobuf, sympy, mpmath)

- [x] **S4: Benchmark latency on EPYC** ✅ 2026-04-14 — Benchmark complete. Results:
  - **Encoding 1 query (48 tok) + 10 snippets (64 tok max)**: median 180ms, min 180ms, max 198ms
  - **MaxSim scoring**: <1ms for 10 documents
  - **Total**: ~180ms per reranking call
  - **Note**: 180ms is well above the original <10ms target, but that target assumed pre-encoded embeddings. The 180ms includes full ONNX encoding through 150M params. Acceptable because each irrelevant page saved = 45s of synthesis. ROI: ~750x.
  - **Ranking quality**: Perfect separation on test data — all 5 relevant snippets ranked top 5, all 5 irrelevant ranked bottom 5. Score spread: relevant 0.93-0.96, irrelevant 0.91-0.92.

- [ ] **S5: Implement reranker** — Add reranking to `research.py`, gated behind `web_research_rerank` flag. When flag is ON: increase `max_results` from 5 to 8-10, encode DDG snippets via GTE-ModernColBERT ONNX, rerank by MaxSim, take top 3 for fetch. Lazy model loading on first call. **Prerequisite**: post-AR-3 analysis confirms >20% irrelevant page rate.
  - File: `epyc-orchestrator/src/tools/web/research.py` (modify `_web_research_impl`)
  - Encoding module: new `src/tools/web/colbert_reranker.py` (ONNX session, tokenizer, MaxSim)
  - Effort: ~2h, depends on S3/S4 (done) and AR-3 go/no-go
  - **Integration note**: ONNX session should be loaded lazily (first call) and cached as module-level singleton. Session is thread-safe for inference.

- [ ] **S6: A/B test** — Compare reranked (10 results → top 3 by ColBERT) vs current (5 results → top 3 by DDG order) on web_research benchmark questions. Metrics: synthesis quality, irrelevant page rate, total latency.
  - Effort: ~2h inference time, depends on S5

## Key Files

| Resource | Path | Role |
|----------|------|------|
| web_research tool | `epyc-orchestrator/src/tools/web/research.py` (468 lines) | Primary implementation target |
| web_search (DDG/Brave) | `epyc-orchestrator/src/tools/web/search.py` (223 lines) | Returns snippets used for reranking |
| fetch + extract | `epyc-orchestrator/src/tools/web/fetch.py` | Page fetching (unchanged) |
| feature flags | `epyc-orchestrator/src/features.py` | Register `web_research_rerank` flag |
| tool manifest | `epyc-orchestrator/src/tools/web/manifest.json` | Tool registration (unchanged) |
| Explore worker config | `epyc-orchestrator/orchestration/model_registry.yaml` | Worker model reference |
| Web research baseline | `epyc-inference-research/scripts/benchmark/analyze_web_research_baseline.py` | A/B test analysis |
| Combined ops | `epyc-orchestrator/src/repl_environment/combined_ops.py` | Uses `web_search` not `web_research` — future extension only |

## Literature Survey (2026-04-14)

### 1. Reason-ModernColBERT Status

150M params, 128-dim multi-vector, cc-by-nc-4.0 license (non-commercial; reproducible under Apache via independent ReasonIR data gen, ~2hr fine-tune). BRIGHT full-mean 22.62 NDCG@10 without reasoning traces, 30.28 with GPT-4 traces -- outperforms all models up to 7B (45x its size). Claims top spot on BrowseComp-Plus (agentic search benchmark) with 54x fewer params. No CPU latency numbers published. **Verdict: ELIMINATED** — license prohibits commercial use. ColBERT-Zero achieves stronger general retrieval without license constraints.

- [HuggingFace model card](https://huggingface.co/lightonai/Reason-ModernColBERT)
- [LightOn blog](https://lighton.ai/lighton-blogs/lighton-deep-tech-simple-delivery)

### 2. Competing Late-Interaction Models

| Model | Params | Key Result | Verdict |
|-------|--------|-----------|---------|
| **ColBERT-Zero** (LightOn, Feb 2026) | <150M | 55.43 NDCG@10 on BEIR, outperforms GTE-ModernColBERT. Fully pre-trained on public data only. | **PRIMARY — strongest general-purpose ColBERT, open data** |
| **GTE-ModernColBERT-v1** (LightOn) | ~150M | 54.67 BEIR avg, 88.39 LongEmbed. Base for Reason variant. | Already deployed on :8089 — validates CPU feasibility |
| **mxbai-edge-colbert** (Mixedbread, Oct 2025) | 17M/32M | 17M outperforms ColBERTv2 (110M) on NanoBEIR. 3x faster CPU encoding than ColBERTv2. | **FALLBACK — best for latency-critical CPU path, Apache 2.0** |
| **Jina-ColBERT-v2** (Jina AI) | ~110M | +6.5% over ColBERTv2, 89-language multilingual, Matryoshka dims (128/96/64). | Not needed — no multilingual requirement |
| **SauerkrautLM-Multi-Reason-ModernColBERT** (VAGO) | ~150M | Community multilingual fork of Reason-ModernColBERT. | monitor_only |

Key paper: Chaffin et al., "ColBERT-Zero: To Pre-train Or Not To Pre-train ColBERT models," arXiv:2602.16609, Feb 2026.

- [ColBERT-Zero on HuggingFace](https://huggingface.co/lightonai/ColBERT-Zero)
- [mxbai-edge-colbert tech report](https://arxiv.org/html/2510.14880v1)
- [Jina-ColBERT-v2](https://huggingface.co/jinaai/jina-colbert-v2)

### 3. CPU Inference Feasibility

No published PyLate CPU benchmarks for ColBERT-Zero specifically. Proxy data:

- **PLAID engine** (ColBERTv2): 45x speedup on CPU vs vanilla; tens-of-ms for 140M passage corpus.
- **mxbai-edge-colbert 17M**: ~49s per 50K docs encoding (vs ColBERTv2 ~154s). Reranking 20 pre-encoded pages would be sub-ms MaxSim.
- **TurkColBERT study**: ColmmBERT-base achieved 0.54ms query latency under MUVERA indexing.
- **Key insight**: For reranking (not full retrieval), only MaxSim scoring over pre-computed embeddings is needed. 20 pages x 128-dim tokens = trivially fast on 192-thread EPYC. **Target <10ms is achievable with any model in this class.**

### 4. Integration Patterns

- **RAGatouille** (AnswerDotAI): Wraps ColBERT for LangChain/LlamaIndex. Supports rerank-only mode (no index build needed). Latest: v0.0.9, May 2025.
- **PyLate** (LightOn): Native library for all ModernColBERT variants. Voyager HNSW indexing. More control but less framework integration.
- **LlamaIndex**: NodePostprocessor API accepts any reranker. Standard pattern: retrieve top-20/30, rerank, pass top-K to LLM.
- **Production consensus (2026)**: Hybrid retrieval (BM25 + dense) -> rerank top-20-30 -> LLM. Cross-encoders on full index cause p99 blowup; late-interaction on small candidate sets is the sweet spot.
- **No DuckDuckGo-specific patterns found** -- DDG returns pre-ranked HTML pages, not embeddings. Our pipeline would encode fetched page text at rerank time.

Rivera & Menolascina, "ModernBERT + ColBERT: Enhancing biomedical RAG," arXiv:2510.04757, Oct 2025 -- confirms ColBERT reranker improves Recall@3 by 4.2pp but requires joint fine-tuning of retriever+reranker.

### 5. Alternatives to Late-Interaction Reranking

- **SPLADE** (learned sparse): Acts as "smarter BM25" with term expansion. Inverted-index compatible. Best as first-stage retriever, not reranker. Does not replace ColBERT for reranking.
- **Dense rerankers (cross-encoders)**: Higher quality ceiling but 2 orders of magnitude slower than ColBERT. Unusable at our latency target.
- **BrowseComp-Plus findings**: Dense reasoning-specialized retrievers (Qwen3-8B) dramatically outperform BM25 for agentic search. But 8B models compete for inference slots -- ColBERT at 150M does not.
- **Verdict**: Late-interaction is the correct architecture for our use case (CPU reranking of 10-20 web snippets, no GPU budget, no inference slot competition).

## References

- intake-174: Reason-ModernColBERT analysis (eliminated — license)
- intake-175: PyLate library evaluation (MIT, selected)
- [BRIGHT benchmark](https://github.com/xlang-ai/BRIGHT) — reasoning-intensive retrieval benchmark
- [PyLate](https://github.com/lightonai/pylate) — late-interaction retrieval library
- [BrowseComp-Plus](https://github.com/texttron/BrowseComp-Plus) — agentic search benchmark (ACL 2026)
- [ColBERT-Zero paper](https://arxiv.org/abs/2602.16609) — Feb 2026, SOTA ColBERT pre-training
- [mxbai-edge-colbert report](https://arxiv.org/html/2510.14880v1) — Oct 2025, tiny ColBERT for edge/CPU
- [ModernBERT+ColBERT biomedical RAG](https://arxiv.org/abs/2510.04757) — Oct 2025
- [Jina-ColBERT-v2 paper](https://arxiv.org/abs/2408.16672) — multilingual late-interaction
- [RAGatouille](https://github.com/AnswerDotAI/RAGatouille) — ColBERT wrapper for LangChain/LlamaIndex
