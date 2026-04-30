# Granite-97M-r2 Multilingual Embedder Bench Plan

**Status**: gated on K2 chunker activation (currently STUB — see `internal-kb-rag.md`)
**Created**: 2026-04-30 (post-intake-519 deep-dive)
**Categories**: search_retrieval, knowledge_management, rag_alternatives, local_inference
**Priority**: MEDIUM (becomes HIGH the moment any of K-track / web-research-rerank / SearXNG dense-stage activates)
**Depends on**: `internal-kb-rag.md` (K2 chunker), `colbert-reranker-web-research.md` (downstream rerank), `searxng-search-backend.md` (web result ingest)
**Source deep-dive**: [`/workspace/research/deep-dives/granite-embedding-97m-r2-evaluation.md`](../../research/deep-dives/granite-embedding-97m-r2-evaluation.md)

## Objective

Determine whether IBM `granite-embedding-97m-multilingual-r2` (Apache 2.0, ModernBERT 97M, 32K context) is the right dense first-stage retriever for EPYC's planned KB / web-research / SearXNG pipelines, by benchmarking it head-to-head with BGE-M3 (quality ceiling) and multilingual-e5-base (size-class peer) on a representative EPYC-relevant eval slice.

## Research Context

| Intake ID | Title | Relevance | Verdict |
|-----------|-------|-----------|---------|
| intake-519 | Granite-Embedding-97M-Multilingual-R2 (HF model) | medium | worth_investigating |

**Independently-verified facts** (from deep-dive):

- ModernBERT is **fully supported in llama.cpp** — `convert_hf_to_gguf.py:12452` registers `ModernBertModel(BertModel)` with `MODEL_ARCH.MODERN_BERT`, sliding-window + RoPE handling. The "Ollama unsupported - ModernBERT" line on the model card refers ONLY to Ollama's wrapper.
- Sentence-transformers v3.3.0+ ships OpenVINO INT8 quantization (~4× CPU speedup); requires `transformers ≥ 4.48.0`.
- Apache 2.0 license confirmed.

**Headline-number caveats** (from deep-dive — calibrate expectations):

- **2,894 docs/s throughput is GPU (H100), NOT CPU.** Reset CPU expectations.
- **8K vs 32K context discrepancy** between paper abstract (8,192) and model card (32,768). Validate empirically.
- **18-task MTEB-ML-Retrieval composition not enumerated** — most likely MIRACL (Wikipedia-only). May not be representative of mixed-language web snippets.
- **BGE-M3 ~63.0 figure is from MMTEB 131-task aggregation** — NOT apples-to-apples with IBM's 18-task 59.6.
- No third-party reproduction yet (model 1 day old at intake date).

**EPYC retrieval state** (from deep-dive infra audit):

- **No production multilingual retrieval today.** Only English-only BGE-large-en-v1.5 routing pool on `:8090–:8095` (`/mnt/raid0/llm/epyc-orchestrator/orchestration/repl_memory/parallel_embedder.py`).
- K-track in `internal-kb-rag.md` is in **STUB status** — K1 not started.
- GTE-ModernColBERT-v1 is the active reranker on `:8088`/`:8089` (different role: multi-vector reranker, not single-vector dense retriever).

## Phased Plan

### Phase A — Inference-free engineering [2-3 days, no model serving]

#### A-1: GGUF conversion + quantization [~half day]

```bash
# Use llama.cpp's convert_hf_to_gguf.py (ModernBertModel support confirmed)
cd /mnt/raid0/llm/llama.cpp
python convert_hf_to_gguf.py \
  /path/to/granite-embedding-97m-multilingual-r2 \
  --outfile granite-97m-r2-f16.gguf \
  --outtype f16
# Q8_0 quantize for CPU
./build/bin/llama-quantize granite-97m-r2-f16.gguf granite-97m-r2-Q8_0.gguf Q8_0
# Optional Q4_K_M for footprint vs quality probe
./build/bin/llama-quantize granite-97m-r2-f16.gguf granite-97m-r2-Q4_K_M.gguf Q4_K_M
```

Acceptance: GGUF loads via `llama-embedding`, produces non-degenerate vectors on a 5-doc smoke probe.

#### A-2: Comparator model downloads + GGUF conversion [~half day, parallelizable]

- BGE-M3 (~568M, multi-vector + dense + sparse — bench DENSE-only path for fair comparison)
- multilingual-e5-base (278M)
- Existing BGE-large-en-v1.5 already deployed (English-only baseline for reference)

#### A-3: Server deployment recipe [~1 day]

Add `granite-97m-r2` to the embedder pool on port `8096` (matches existing BGE-large `:8090–:8095` pattern). Update `parallel_embedder.py` registry. Three model servers up: granite-97m-r2 (8096), multilingual-e5-base (8097), BGE-M3 (8098).

#### A-4: Build minimal eval corpus [~half day]

**Cheapest viable path** (recommended for first bench):
- 100 code snippets sampled from `epyc-orchestrator/src/` (Python)
- 30 NL queries with manual NDCG@10 labels
- Output: `eval-corpus-v0.jsonl` with `{query, doc, relevance_label}` triples
- Total ~half day of manual labeling

**Alternative** (only if K2 chunker activates first):
- Use K2 chunker output on a slice of `/workspace/handoffs/active/*.md` + `/workspace/CLAUDE.md` as the doc corpus
- ~50 NL queries against handoff content
- Higher relevance to actual KB-RAG use case but blocks on K2

#### A-5: Bench script [~1 hour]

Write `/workspace/scripts/benchmark/bench_embedder_throughput.py`:

```bash
python scripts/benchmark/bench_embedder_throughput.py \
  --servers 8090 8096 8097 8098 \
  --corpus eval-corpus-v0.jsonl \
  --output bench-results-2026-MM-DD.json
```

Measures: t/doc encode latency, NDCG@10, recall@10, recall@50, per-context-length latency at 8K/16K/32K.

### Phase B — Bench execution [1 inference day]

**No concurrent inference allowed without per-run approval** (memory `feedback_no_concurrent_inference.md`). Coordinate with autopilot/benchmarking to ensure exclusive EPYC access.

#### B-1: Throughput bench — 1000 docs per model

Encode 1000 docs of varying length (256, 1024, 4096, 8192, 16384, 32768 tokens) for each of granite-97m-r2 (Q8_0 + Q4_K_M), multilingual-e5-base, BGE-M3, BGE-large-en (reference). Record t/doc per length bucket.

#### B-2: Quality bench — NDCG@10 / recall@10/50 on eval-corpus-v0

Run all queries through each model as first-stage retriever (top-50 candidates). Compute metrics. **Add ColBERT reranker (GTE-ModernColBERT-v1 on :8088) as a downstream stage** for the 3 candidates → measure end-to-end retrieve+rerank quality.

#### B-3: 32K context probe — empirical validation

Encode 10 long documents (32K tokens each) per model. Compare against 8K/16K splits of the same documents. Identify quality cliff (if any).

### Phase C — Decision + deployment recommendation [post-bench]

Three possible outcomes:

| Outcome | Trigger | Action |
|---------|---------|--------|
| **Adopt granite-97m-r2** | NDCG@10 within 3pp of BGE-M3 AND ≥3× faster | Promote to production multilingual dense retriever; keep BGE-large for English-only paths |
| **Adopt BGE-M3** | NDCG@10 ≥5pp better than granite, latency acceptable | Use BGE-M3; close granite track |
| **Defer both** | Neither meaningfully outperforms BGE-large-en on actual EPYC corpus | Stay on English-only BGE-large until K2 produces a representative multilingual corpus |

Document outcome in `/workspace/research/deep-dives/granite-97m-r2-bench-results-2026-MM-DD.md`.

## Code-search angle (DEFERRED, separate sub-track)

Granite claims 60.5 on MTEB Code (v1) across 12 tasks with explicit training on 9 programming languages (Python, Go, Java, JS, PHP, Ruby, SQL, C, C++). Could serve as a NL→code-context first-stage retriever — additive to GitNexus (symbol-level static analysis) and to GTE-ModernColBERT-v1 (general retrieval, not code-specialized).

**Defer code-search bench until KB-RAG bench (above) lands.** Reuse the eval-corpus engineering, then add a code-NL eval slice on top.

## Risks

- ModernBERT in llama.cpp is functional but newer than the BERT path — verify no edge cases on first GGUF conversion.
- 32K context claim may degrade in practice past 8K (paper abstract says 8K, model card says 32K).
- IBM model card may revise scores post-1-day-old release as third-party leaderboard data appears.
- OpenVINO/sentence-transformers backend requires cp312/cp313 venv — orchestrator venv is currently cp314, so the PRIMARY deployment path is GGUF + `llama-embedding`, not OpenVINO INT8.
- BGE-M3 sparse + multi-vector outputs are NOT used in this bench (we measure dense-only). If we later want ColBERT-style multi-vector first-stage, BGE-M3 has a built-in path; granite does not.

## Open Questions

- Is the K2 chunker scoped to ship before this bench wants to run? If not, Phase A-4 falls back to the code-corpus path.
- Should we add Qwen3-Embedding-0.6B as a 4th comparator? (smaller than e5-base, plausibly competitive at lower latency)
- Post-bench: which orchestrator role consumes the dense retriever first — KB-RAG, web-research, or SearXNG? This determines deployment ordering.

## Reporting Instructions

After Phase B completes, update:

- This file with bench results table and final status (`completed-adopt-granite` / `completed-adopt-bgem3` / `completed-defer`)
- `internal-kb-rag.md`, `colbert-reranker-web-research.md`, `searxng-search-backend.md` — replace 2026-04-30 intake-update sections with concrete bench results
- `progress/2026-MM/2026-MM-DD.md` with one-paragraph summary

## Cross-references

- Deep-dive: `/workspace/research/deep-dives/granite-embedding-97m-r2-evaluation.md`
- Intake entry: intake-519
- Active handoffs: internal-kb-rag, colbert-reranker-web-research, searxng-search-backend, minddr-deep-research-mode, searxng-bash-websearch-bridge
- Existing infra: `/mnt/raid0/llm/epyc-orchestrator/orchestration/repl_memory/parallel_embedder.py` (BGE-large pool)
- llama.cpp ModernBERT support: `/mnt/raid0/llm/llama.cpp/convert_hf_to_gguf.py:12452`
