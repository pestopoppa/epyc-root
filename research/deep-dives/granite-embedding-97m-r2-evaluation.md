# Deep Dive: Granite-Embedding-97M-Multilingual-R2 Evaluation

**Date**: 2026-04-30
**Intake**: intake-519 (huggingface.co/ibm-granite/granite-embedding-97m-multilingual-r2)
**Paper**: arxiv:2508.21085 ("Granite Embedding R2 Models", Awasthy et al., IBM Research AI)
**Model release**: 2026-04-29
**License**: Apache 2.0 (no usage restrictions; "permissive enterprise-friendly")
**Initial verdict**: `worth_investigating`
**Refined verdict**: `KEEP — but redefine as eval-corpus-build-then-bench, not 1-day bench`

## Executive Summary

Granite-Embedding-97M-Multilingual-R2 is a **dense, single-vector, ModernBERT-base 97M-param** embedding model from IBM Research, **released six days into the past relative to this deep-dive (2026-04-29)**. It targets the sub-100M multilingual class with a claimed 59.6 MTEB Multilingual Retrieval (18 tasks) — the highest score in its size class on the IBM card and the only public score available for that class (corroborating leaderboard listing exists; independent third-party replication does not yet exist as of 2026-04-30).

The original recommended action — *"1-day A/B vs BGE-M3 + multilingual-e5-base on EPYC CPU using ONNX/OpenVINO INT8, targets KB and SearXNG retrieval pipelines"* — is **directionally correct but mechanically wrong**. The blocker is not the bench itself; the blocker is that **EPYC has no production multilingual retrieval pipeline today**, no curated KB eval corpus, and the K-track in `internal-kb-rag.md` is in stub status with K1 (encoder extraction) not yet started. A 1-day bench with no eval corpus measures nothing useful. The right framing is: **(a) confirm ModernBERT compatibility on our deployment path** (done in this deep-dive — llama.cpp natively supports ModernBERT, sentence-transformers v3.3+ ships OpenVINO INT8), (b) **build a small EPYC-local eval corpus** (50–100 query/positive/negatives over our wiki + handoffs + a SearXNG snippet sample), (c) **then run the A/B**. That sequence is ~3–5 inference-free engineering days, not 1 bench day.

Also crucial: granite-97m-r2 is a **dense single-vector model with 384 dim**, not multi-vector. It is **not a drop-in replacement for any deployed component**. It would slot in as a **new layer**: a multilingual dense first stage either (i) feeding the ColBERT reranker on the SearXNG path, (ii) acting as the KB-RAG embedder for K3/K4, or (iii) serving as a code-aware retriever for code-context lookup. The deployed BGE-large-en-v1.5 (1024-dim, English-only) on ports 8090–8095 is a **routing-classifier / research-context** embedder, not a retrieval embedder — a different role.

## 1. Independent Verification of Headline Numbers

### 1.1 MTEB Multilingual Retrieval (18 tasks) = 59.6 — partial verification

| Source | Status | Evidence |
|--------|--------|----------|
| IBM HF model card | confirmed | "59.6 on Multilingual MTEB Retrieval (18 tasks)" stated explicitly with comparator multilingual-e5-small = 50.9 (+8.7 pts) |
| Granite-R2 paper (arxiv:2508.21085) | partial | Paper exists, abstract confirms "state-of-the-art performance across diverse retrieval domains" and "19-44% speed advantages over leading competitors". Full table extraction blocked — paper's HTML v1/v2 returned 404 / English-only content; PDF binary not parseable via WebFetch |
| MTEB leaderboard | not directly extracted | Leaderboard page renders client-side; static fetch returns loading state. Web-search summaries quote 59.6 from IBM card — circular |
| Independent third-party | none found | Model released 2026-04-29 (1 day before this dive); no replication papers, no community reproductions, no MTEB-track entries from other groups |

**Comparator gap.** The IBM card lists *only* multilingual-e5-small (50.9) as an explicit numeric comparator on MTEB-ML-Retrieval. **BGE-M3 is not in the model card's table**, only mentioned indirectly. From web-aggregator sources: BGE-M3 is widely quoted at ~63.0 on MTEB Multilingual Retrieval — but this is a *different aggregation* across the wider MMTEB (131 tasks, 250+ languages), not the MTEB-ML-Retrieval-18 IBM is reporting against. **The 59.6 vs 63.0 comparison is not apples-to-apples** until both are computed on the same 18-task subset. This is an open verification gap.

**The 18 tasks** that compose IBM's "MTEB Multilingual Retrieval (18 tasks)" are not enumerated on the model card. The paper presumably names them; full PDF extraction blocked in this session. Recommended follow-up: download the PDF locally and grep the appendix for the task list. From the broader MTEB taxonomy and IBM's "MIRACL benchmark, 18 languages" reference, the most likely composition is **MIRACL** (18 Wikipedia-sourced multilingual retrieval tasks). If confirmed, that means "MTEB-ML-Retrieval (18 tasks)" ≈ MIRACL, which is a **Wikipedia-only retrieval benchmark** — narrower than the wider MMTEB and not reflective of mixed-language web search snippets.

### 1.2 Other claimed numbers

| Claim | Source | Status |
|-------|--------|--------|
| LongEmbed 65.5 (6 tasks) | model card | confirmed on card; underlying tasks not enumerated on card |
| Code retrieval 60.5 | model card | confirmed; **paper card says "MTEB Code (v1) across 12 tasks", not 8 as the original recommendation cited.** The 8 figure comes from the *training-language count* (Python, Go, Java, JavaScript, PHP, Ruby, SQL, C, C++ — that's 9 in the card text, listed under "Broader code coverage"). 12 tasks ≠ 8 languages — these are different counts |
| 32K context | model card | confirmed (32,768 tokens). **Paper abstract says 8,192 — discrepancy unresolved.** Likely the paper's abstract describes the English R2 context (8K) and the multilingual variant extends to 32K via a different RoPE scaling config; verify in paper §3 or model config.json |
| 384 embedding dim | model card | confirmed |
| 2,894 docs/s throughput | model card | confirmed; **measurement on H100 GPU, NOT CPU.** Reference HW disclosed: single NVIDIA H100, 512-token sliding window. EPYC CPU throughput unknown — must measure |
| Apache 2.0 | model card | confirmed; explicitly "permissive, enterprise-friendly licenses". License-ok for our use |

### 1.3 Verdict on independent verification

**Partial.** The 59.6 number is internally consistent (model card + paper abstract + leaderboard listings) but **independent of IBM, no third party has yet reproduced it**, and the 18-task composition is unenumerated on accessible sources. The 50.9 baseline for multilingual-e5-small is also IBM-reported, not independently verified. **Treat as Tier 2b: credibility ≈3** (peer-reviewed-ish via arxiv preprint + reputable lab + open weights, but no independent replication, only-1-day-old release).

## 2. ModernBERT Compatibility Audit

### 2.1 llama.cpp — supported (definitive)

llama.cpp natively supports ModernBERT. Confirmed by direct source inspection of `/mnt/raid0/llm/llama.cpp`:

- `convert_hf_to_gguf.py` line 12452 registers `ModernBertModel`, `ModernBertForMaskedLM`, `ModernBertForSequenceClassification` with `model_arch = gguf.MODEL_ARCH.MODERN_BERT`. Class extends `BertModel` and adds sliding-window + RopeScalingType.NONE handling.
- `src/llama-graph.cpp` line 2865 references the upstream Transformers ModernBERT modular impl, indicating the graph builder has the architecture wired through.
- `convert_hf_to_gguf.py` line 1504 registers the answerdotai/ModernBERT-base tokenizer reference for vocab BPE.

**The model card's "Ollama unsupported - ModernBERT" note refers only to Ollama's wrapper, not llama.cpp itself.** The card explicitly provides a `convert_hf_to_gguf.py granite-embedding-97m-multilingual-r2 --outfile granite-embedding-97m-multilingual-r2.gguf` example, then `llama-embedding -m granite-embedding-97m-multilingual-r2.gguf -p "..."`. **GGUF conversion path is documented and working**.

### 2.2 sentence-transformers — supported (v3.3+)

- ModernBERT support in sentence-transformers requires `transformers >= 4.48.0` (architecture introduction) and any sentence-transformers version published after that (current pip is 5.x).
- sentence-transformers v3.3.0 (Nov 2024) added **OpenVINO INT8 static quantization** with a `export_static_quantized_openvino_model()` helper. CPU 4× speedup with minimal quality loss claimed. This is the deployment path the IBM card recommends:
  ```python
  model = SentenceTransformer("ibm-granite/granite-embedding-97m-multilingual-r2", backend="openvino")
  ```

**Caveat for our orchestrator venv (cp314):** `colbert-reranker-web-research.md` notes that PyLate + sentence-transformers + PyTorch lacks cp314 wheels in the orchestrator venv, which forced the ColBERT path to use raw ONNX Runtime instead. The same caveat applies to Granite — if we want a `sentence-transformers` backend, we either (a) run it in a separate cp312/cp313 venv (research repo has one), (b) use raw ONNX Runtime + manual mean-pool over the IBM-shipped `model.onnx`, or (c) GGUF-convert and embed via `llama-embedding` HTTP server (the same server type used for BGE-large on :8090–:8095).

### 2.3 ONNX/OpenVINO — pre-shipped by IBM

Per the model card, IBM ships pre-converted ONNX and OpenVINO (including INT8) artifacts. **No local export needed.** This is a meaningful improvement over the LateOn / Reason-mxbai-32m S3b/S3c work where local PyTorch→ONNX export was a deployment gate.

### 2.4 GGUF deployment recipe (recommended primary path on EPYC)

```bash
# Inside research repo venv (cp312, has torch + transformers)
python convert_hf_to_gguf.py /path/to/granite-embedding-97m-multilingual-r2 \
    --outfile granite-embedding-97m-multilingual-r2-f16.gguf

# Then quantize to Q8_0 or Q5_K (parity with bge-large-en-v1.5-f16.gguf already on disk)
llama-quantize granite-embedding-97m-multilingual-r2-f16.gguf granite-embedding-97m-multilingual-r2-Q8_0.gguf Q8_0

# Deploy as embedding server (same pattern as the 6× BGE-large pool)
llama-server -m granite-embedding-97m-multilingual-r2-Q8_0.gguf --embeddings --port 8096 -ngl 0 -t 16
```

This deployment path **reuses the existing BGE-large embedding-server pattern** (`/mnt/raid0/llm/models/bge-large-en-v1.5-f16.gguf` + ports 8090–8095). Adding granite-97m-r2 means a 7th port (or a separate pool on 8096–8101). The `ParallelEmbedderClient` (`orchestration/repl_memory/parallel_embedder.py`) is BGE-keyed (1024-dim) and **would need a sibling client for 384-dim Granite**, plus role-aware dispatch (routing classifier → BGE-EN; multilingual retrieval → Granite).

### 2.5 Summary table

| Path | Status | Effort to deploy on EPYC |
|------|--------|--------------------------|
| llama.cpp / GGUF (`llama-embedding`) | ✅ supported, recommended | <1 h conversion + quantize + server config |
| ONNX Runtime (raw, like ColBERT) | ✅ IBM ships ONNX | <1 h to wire as a Python module; cp314-friendly (no PyTorch) |
| OpenVINO INT8 (sentence-transformers backend) | ✅ IBM ships OpenVINO INT8 | needs cp312/cp313 venv + sentence-transformers; ~1 h install |
| Direct PyTorch / sentence-transformers FP32 | ✅ but heavy | needs PyTorch (~2 GB), separate venv from cp314 orch |

**Recommended primary**: GGUF path via `llama-embedding` — matches existing BGE deployment pattern, no new dependencies, multi-instance pool already understood. Recommended secondary: ONNX Runtime in cp314 if we want in-process embedding without HTTP roundtrip.

## 3. EPYC Retrieval Infrastructure State (as of 2026-04-30)

### 3.1 What's deployed

| Component | Path | Role | Embedder |
|-----------|------|------|----------|
| `bge-large-en-v1.5-f16.gguf` | `/mnt/raid0/llm/models/` | Routing classifier features (1024-dim CLS pool); research_context semantic similarity | English-only, 1024-dim |
| 6× `llama-embedding` servers | ports 8090–8095 | Probe-first parallel pool feeding ParallelEmbedderClient | BGE-large-EN |
| `gte-moderncolbert-v1-onnx/model_int8.onnx` | `/mnt/raid0/llm/models/` | Reranker (designed; S5 inference-gated on AR-3) | 128-dim multi-vector |
| ColBERT NextPLAID containers | ports 8088, 8089 | Reranking infra (deployed, used by `code_search.py`) | Different code path |

**There is no production dense first-stage retriever for KB or web search today.** The `web_search` tool returns DDG/Brave HTML snippets and pipes top-N directly to the synthesizer. The `web_research` tool fetches top-3 by DDG ranking and synthesizes via worker_explore. **Retrieval ranking is currently delegated to DuckDuckGo / SearXNG aggregator scoring**, with an instrumented "irrelevant page rate" telemetry path waiting on AR-3 data.

### 3.2 The K-track concretely (from `internal-kb-rag.md`)

K-track is the **internal-KB-RAG** plan: ColBERT-based RAG over our own markdown corpus (wiki + handoffs/active + research/ + completed handoffs + progress). Status as of 2026-04-30: **stub, not started**. Work items K1–K8:

- K1 (extract shared encoder module): not started
- K2 (corpus configuration + chunker): not started
- K3 (initial index build): not started
- K4 (query CLI + Python API): not started
- K5 (index-on-commit hook): not started
- K6 (Explore-subagent integration): not started
- K7 (Flywheel-template eval, ~2 sessions for 50 multi-hop questions over 4-5K-doc pool): not started
- K8 (wikilink learning-loop scorer, LOW priority deferred): not started

The original "1-day bench gated on K-track activation" is **gated on K1 at minimum** — there is no encoder module to plug Granite-97m into. Granite-97m-r2 evaluation **for the KB use case** can only run after K1 + K2 + a small K3 over a fixed corpus snapshot.

### 3.3 SearXNG state (from `searxng-search-backend.md`)

SX-1..SX-4 ✅ shipped, SX-5/6 inference-gated on AR-3 Package D telemetry. SearXNG returns `{title, url, snippet, score, engines[]}` JSON from a self-hosted Docker container on port 8090 (note: port collision with BGE-large-en-v1.5 server #1 — this likely means BGE pool starts at 8090 OR SearXNG is on a different port; verify with `orchestrator_stack.py`). Snippet content per result is short (typically 100–300 chars) — well below ModernBERT's 8K (let alone 32K) context. **SearXNG snippets do not stress-test long-context embeddings** — granite-97m-r2's 32K context is unused on this path.

### 3.4 What about MindDR? (from `minddr-deep-research-mode.md`)

The DeepSearchFanOutNode (MD-4) and ReportSynthesisNode (MD-5) are prompt-level pipelines. They currently consume web_search output directly. **No dedicated retrieval embedder is planned for the deep-research mode**; if KB-RAG ships, DeepSearch could call it as a tool. Granite-97m-r2's role here is **indirect**: by improving the K-track or web-research first stage, it would feed better candidates into the deep-research synthesis pipeline.

### 3.5 Production retrieval today: what does exist?

- **GitNexus** (code-only, indexed by code-intelligence pipeline; markdown invisible)
- **`research_context.py`** (in-memory semantic similarity over per-conversation research nodes via BGE-large embedding) — this is **per-session ephemeral**, not a persistent KB
- **`web_search`** (DDG/Brave HTML scrape; soon SearXNG JSON)
- **`code_search.py`** via NextPLAID containers on :8088/:8089 (GTE-ModernColBERT-v1 docs retrieval, code-specialized)

**No production dense-vector retrieval over markdown corpus, no production multilingual retrieval anywhere.** Granite-97m-r2 is a candidate for **net-new infrastructure**, not a swap-in.

## 4. Concrete Bench Plan (Refined)

### 4.1 The original "1-day bench" cannot run today

Reasons:
1. No curated KB eval corpus exists. K7 (Flywheel-template eval, 50 multi-hop questions) is stub, not built.
2. No SearXNG output sample with relevance labels exists. AR-3 Package D will produce ~50 sentinel queries with "irrelevant page" instrumentation, but that's about *binary* relevance (is the page off-topic?), not nDCG@10 over a ranked candidate set.
3. No deployment recipe has been validated for granite-97m-r2 on EPYC. No GGUF conversion has happened.
4. `multilingual-e5-base` is not on disk and not currently used.
5. BGE-M3 (568M, 1024-dim) is not on disk and not currently used.

### 4.2 Refined plan: "build eval corpus first, then bench"

**Phase A (Pre-bench, ~2–3 inference-free engineering days)**

A1. **Convert + quantize granite-97m-r2 to GGUF** (~30 min)
```bash
cd /mnt/raid0/llm/llama.cpp
huggingface-cli download ibm-granite/granite-embedding-97m-multilingual-r2 \
    --local-dir /mnt/raid0/llm/models/granite-embedding-97m-multilingual-r2-hf
python convert_hf_to_gguf.py /mnt/raid0/llm/models/granite-embedding-97m-multilingual-r2-hf \
    --outfile /mnt/raid0/llm/models/granite-embedding-97m-multilingual-r2-f16.gguf
./build/bin/llama-quantize \
    /mnt/raid0/llm/models/granite-embedding-97m-multilingual-r2-f16.gguf \
    /mnt/raid0/llm/models/granite-embedding-97m-multilingual-r2-Q8_0.gguf Q8_0
```
Verify: `llama-embedding -m granite-embedding-97m-multilingual-r2-Q8_0.gguf -p "test" --embd-output-format json | jq '.[0] | length'` should print 384.

A2. **Stand up granite-97m-r2 embedding server** on a free port (e.g., 8096) with `--embeddings -ngl 0 -t 16`. Smoke-test against an English query, a French query, a Python-code query.

A3. **Download comparators** (parallel):
- `BAAI/bge-m3` → already shipped GGUF available on HF (intfloat / Xenova mirrors); convert if needed
- `intfloat/multilingual-e5-base` → convert via convert_hf_to_gguf.py (XLM-RoBERTa backbone, supported)
- `intfloat/multilingual-e5-small` (118M) — same recipe; included as a size-class pivot

A4. **Build minimal eval corpus** — choose ONE of:
- **K-track minimal slice**: 200 randomly-sampled chunks from `wiki/` + `handoffs/active/` after K2's heading-aware chunker is implemented (cross-couples to K2). 30 hand-curated query/positive/negatives. nDCG@10. ~1 day.
- **SearXNG slice**: capture 30 SearXNG queries from AR-3 Package D telemetry once it lands. For each query, take top-20 snippets, manually label relevant/not. Compute nDCG@10. **Blocked on AR-3.**
- **Code retrieval slice**: 100 code snippets from `epyc-orchestrator/src/` + 30 NL queries (e.g., "where is BGE embedder initialized?"). Manually labeled. nDCG@10. ~half day. **Cheapest path; recommended as the first bench.**

**Phase B (Bench, ~1 day)**

B1. **Encode 1000 short docs (200–500 tokens each) per model, time it**:
```bash
# Granite-97m on port 8096
time python -c "
import urllib.request, json, time
docs = open('docs.txt').read().split('\\n')[:1000]
t0 = time.time()
for d in docs:
    r = urllib.request.urlopen('http://127.0.0.1:8096/embedding',
        data=json.dumps({'content': d}).encode())
    _ = json.loads(r.read())
print(f'{(time.time()-t0)*1000/1000:.2f} ms/doc')
"
```
Expected on EPYC NPS4 with `-t 16`: ~5–15 ms per doc for granite-97m, ~30–60 ms for BGE-M3 (3× more params).

B2. **Compute nDCG@10 on the chosen eval slice** for each of {granite-97m-r2-Q8_0, multilingual-e5-base-Q8_0, BGE-M3-Q8_0, BGE-large-en-v1.5-f16 (existing baseline as a sanity-check)}.

B3. **Latency sweep**: encode 1 query + rank against 100 docs, 10 docs, 1000 docs. Report median + p95.

B4. **Long-context probe**: encode a single 8K-token doc and a single 32K-token doc with each model. Measure latency and verify the output vector is non-degenerate (cosine vs random < 0.1, vs near-duplicate > 0.7). This tests the LongEmbed claim.

**Phase C (Decision)**

| Outcome | Action |
|---------|--------|
| Granite within 2 pp nDCG@10 of BGE-M3, faster | **Adopt as KB-RAG / SearXNG dense first stage** |
| Granite within 2 pp of BGE-M3 only on multilingual queries, English-only on par with BGE-large | **Adopt only on multilingual path; keep BGE-large for English routing** |
| Granite ≥3 pp behind BGE-M3 | **Reject for primary; consider only as compact-deployment fallback** |
| Granite long-context degrades past 8K | **Cap `max_seq_len` at 8192 and re-bench** |

### 4.3 Specific commands for encoding 1000 docs on EPYC CPU

```bash
# After A1-A2, all three models running on ports 8090-large, 8096-granite, 8097-e5-base, 8098-bge-m3
python /mnt/raid0/llm/epyc-inference-research/scripts/benchmark/bench_embedder_throughput.py \
    --servers 8090 8096 8097 8098 \
    --corpus /mnt/raid0/llm/data/embedding_eval/wiki_handoffs_chunks.jsonl \
    --n-docs 1000 \
    --threads 16 \
    --output /mnt/raid0/llm/epyc-inference-research/results/granite_r2_bench.json
```
**This script does not yet exist** — would need to be written (~1 h, follows the existing `scripts/benchmark/` patterns).

### 4.4 Effort estimate (revised)

- Original "1-day bench": **infeasible without prior work**
- Refined "Phase A + B + C": **3–5 inference-free engineering days + 1 inference day**, with Phase A4 / Phase B requiring the eval corpus to exist (which couples to K2/K7 in `internal-kb-rag.md`)

## 5. Pareto Position vs Alternatives

### 5.1 Comparison table (all numbers as quoted by sources, not independently verified)

| Model | Params | Dim | Ctx | License | MTEB-ML-Retrieval | MIRACL | LongEmbed | English MTEB | CPU latency on EPYC (estimated) |
|-------|-------:|----:|----:|---------|------------------:|-------:|----------:|-------------:|---------------------------------|
| **granite-embedding-97m-multilingual-r2** | 97M | 384 | 32K | Apache-2.0 | **59.6** (IBM) | n/a (probably ≈59.6 if 18-task=MIRACL) | 65.5 | n/a (multilingual model) | ~5–15 ms/doc Q8 (extrap. from BGE-large 5–15 ms) |
| multilingual-e5-small | 118M | 384 | 512 | MIT | 50.9 (IBM-quoted) | low-50s | n/a (512 ctx) | n/a | ~5–10 ms/doc Q8 |
| multilingual-e5-base | 278M | 768 | 512 | MIT | ~55 (general estimate) | mid-50s | n/a (512 ctx) | n/a | ~15–30 ms/doc Q8 |
| jina-embeddings-v3 | 570M | 1024 (Matryoshka) | 8192 | CC-BY-NC-4.0 | 64+ | high-50s | high | high | ~30–60 ms/doc Q8 |
| BGE-M3 | 568M | 1024 | 8192 | MIT | ~63.0 (different agg) | high-50s | mid | high | ~30–60 ms/doc Q8 |
| Snowflake-arctic-embed-l-v2.0 | 568M | 1024 | 8192 | Apache-2.0 | n/a (English-strong) | n/a | n/a | high | ~30–60 ms/doc Q8 |
| Qwen3-Embedding-0.6B | 600M | 1024 | 8192 | Apache-2.0 | 55.52 (decon.) | n/a | n/a | high | ~30–60 ms/doc Q8 |
| Qwen3-Embedding-8B | 8B | 4096 | 32K | Apache-2.0 | top-of-leaderboard | top | top | top | infeasible on EPYC (~500 ms+/doc) |
| BGE-large-en-v1.5 (deployed) | 335M | 1024 | 512 | MIT | English-only | n/a | n/a | strong | ~5–15 ms/doc f16 (measured) |

### 5.2 Pareto observations

1. **In the sub-100M-multilingual class, granite-97m-r2 is the only viable candidate.** multilingual-e5-small is at 118M with 50.9 — granite's claimed +8.7 is meaningful if real.
2. **In the 200–600M class, BGE-M3 is the quality ceiling**; jina-v3 is non-commercial-only (CC-BY-NC); Snowflake Arctic is English-strong but multilingual claims are weaker.
3. **At the very top (Qwen3-Embedding-8B), CPU EPYC is infeasible** (8B params, decode-bound). DGX Spark gating would apply.
4. **The right anchor question**: if our actual workload is **English-heavy KB + occasional multilingual web search snippets**, then:
   - For KB: **BGE-large-en-v1.5 (deployed) on the routing path is already best-in-class for English**. We don't need a multilingual model for KB unless we expect multilingual handoffs (we don't).
   - For SearXNG: snippets are short (100–300 chars) and mostly English. multilingual is a minority. **A small multilingual model that doesn't degrade English performance is the win**. Granite-97m-r2's claimed strong English performance (paper claims general SOTA in size class) makes it the right candidate.
   - For code retrieval: a different evaluation, see §6.

### 5.3 Should we benchmark BGE-M3 first?

**Yes, as a quality ceiling.** The 1-day bench only makes sense if we know the *upper bound* of CPU-feasible retrieval quality on our corpus. BGE-M3 (568M, 8K ctx) is roughly the largest model that runs on EPYC at <100 ms/doc and has documented multilingual + long-context support. **Running BGE-M3 first establishes the ceiling**, then granite-97m-r2 measures the throughput-vs-quality trade. Recommendation: **bench three models in parallel, not granite-97m-r2 alone**.

## 6. Code-Search Use Case Angle

The model card claims **60.5 on MTEB Code (v1) across 12 tasks**, with training-language coverage of Python, Go, Java, JavaScript, PHP, Ruby, SQL, C, C++.

### 6.1 EPYC code-retrieval state

We have a coder workflow (`worker_coder` = REAP-246B / 30B-A3B), a **GitNexus code-intelligence index** for symbol-level navigation, and **NextPLAID containers** on :8088/:8089 for ColBERT-based code retrieval (different code path from the markdown KB). Granite-97m-r2 as a **code embedder** would compete with whatever is running on :8088/:8089 (likely GTE-ModernColBERT-v1 or a code-specific variant).

### 6.2 Is granite-97m-r2 better than GitNexus + ColBERT for code?

- **GitNexus** does symbol-level static analysis — call graphs, impact analysis, refactor safety. **Different problem**: code structure, not natural-language → code retrieval.
- **GTE-ModernColBERT-v1** on :8088/:8089 — late-interaction ColBERT, pretrained on general retrieval. Not code-specialized.
- **Granite-97m-r2** — explicitly trained on code retrieval pairs in 9 programming languages.

**The code use case is genuinely additive.** A potential angle: use granite-97m-r2 as the **first-stage dense retriever for natural-language → code-context queries** ("where is BGE embedder initialized?"), with GitNexus providing symbol-level hop-out and ColBERT providing rerank. This is a **third deployment role** distinct from KB-RAG and SearXNG.

### 6.3 Recommendation

**Worth a separate bench, deferred until KB-RAG bench lands.** Code retrieval has its own eval corpus problem (need NL queries paired with code answers), and the GitNexus ecosystem already covers structural code search. The marginal value of granite-97m-r2 over GitNexus is **only on natural-language queries that don't map to a single symbol**.

## 7. Risk Register

| Risk | Severity | Mitigation |
|------|----------|------------|
| 59.6 score not independently replicated; IBM is sole source | medium | Wait 4–6 weeks for community reproductions on MTEB leaderboard before committing to architectural role; meanwhile, our own EPYC bench is independent verification |
| 18 tasks of MTEB-ML-Retrieval not enumerated; may be MIRACL = Wikipedia-only | medium | Read paper appendix; verify task list. If MIRACL-only, multilingual web-snippet performance may not transfer |
| 32K context vs 8K paper abstract — discrepancy | low | Read model `config.json`, verify `max_position_embeddings`. Test long-doc embedding quality at 8K, 16K, 32K boundaries in Phase B4 |
| Apache 2.0 license — verify file in HF repo | low | Per IBM card text + paper abstract: confirmed Apache 2.0, "permissive enterprise-friendly". No flag |
| Released 2026-04-29 (1 day old at deep-dive time); model artifacts may still be uploading or have file inconsistencies | low–medium | Verify HF repo file completeness before bench (check ONNX, OpenVINO, safetensors all download cleanly); model card explicitly references "Released 2026-04-29" |
| Dense single-vector with 384 dim — small dimension may be a quality limiter on long-context retrieval | medium | Phase B4 (long-context probe) measures this; if degraded past 8K, cap `max_seq_len`. Quality-vs-dim Pareto: most sub-100M models are 384–768 dim |
| GGUF conversion via `convert_hf_to_gguf.py` may have pooling-layer mismatches (CLS vs mean-pool) | low–medium | Compare GGUF output against ONNX output on 10 sample queries; if cosine ≥0.99, conversion is faithful. Otherwise, debug pooling config |
| Multilingual ≠ universal — 200 languages claim is from base encoder; only 52 get explicit retrieval-pair training. Languages outside the 52 may underperform | low | Our SearXNG traffic is dominantly EN/IT/ES/FR/DE/JA/ZH; all in the 52. Not a real risk for our workload |
| Throughput claim 2,894 docs/s is on H100 GPU, NOT CPU | low | CPU throughput must be measured in Phase B1; quoting GPU number for a CPU deployment is misleading |
| `Ollama unsupported` line on the card may confuse downstream users into thinking llama.cpp is also unsupported | low | This deep-dive corrects the misreading; llama.cpp natively supports ModernBERT |

## 8. Sequencing & Cross-Refs

### 8.1 Where this slots into existing work

| Track | Current state | Granite-97m-r2 role |
|-------|---------------|---------------------|
| `internal-kb-rag.md` K-track | stub, K1 not started | **Direct candidate as KB-RAG dense embedder** for K3/K4. Decouples from the GTE-ModernColBERT-v1 reuse plan. |
| `colbert-reranker-web-research.md` S5 | inference-gated on AR-3 | **Candidate dense first stage** before the ColBERT reranker. Encodes SearXNG snippets, ColBERT reranks top-K. |
| `searxng-search-backend.md` SX-5/6 | inference-gated on AR-3 | **No direct change to SX work items**. Granite-97m-r2 sits one layer downstream (dense rerank stage). |
| `minddr-deep-research-mode.md` MD-* | Phase 1 prompt-level, Phase 2 GPU-gated | **No direct integration**. DeepSearch agent could call KB-RAG as a tool once K-track ships. |
| Code retrieval (NextPLAID :8088/:8089) | Deployed, used by `code_search.py` | **Separate evaluation track**, deferred. |

### 8.2 Recommended next steps in priority order

1. **Now (no inference)**: convert granite-97m-r2 to GGUF + Q8_0, deploy on port 8096, smoke-test. ~30 min.
2. **Now (no inference)**: read paper PDF (full appendix), enumerate the 18 tasks, verify 32K context claim. ~1 h.
3. **Coupled to K2 (eval-corpus prereq)**: build the 50–100-question internal-KB-RAG eval corpus (matches K7 Flywheel-template work). ~1 day.
4. **Inference-gated (separate session)**: 3-way bench {granite-97m-r2, multilingual-e5-base, BGE-M3} on the eval corpus. ~1 day.
5. **Conditional on bench result**: integrate as dense first stage in either KB-RAG or SearXNG → ColBERT pipeline.

## 9. Cross-References

- `/workspace/handoffs/active/colbert-reranker-web-research.md` — ColBERT reranker (S5 / S3b LateOn / S3c Reason-mxbai). Granite slots in as dense first stage upstream of these rerankers.
- `/workspace/handoffs/active/internal-kb-rag.md` — K-track stub. Granite is a candidate K1 encoder choice.
- `/workspace/handoffs/active/searxng-search-backend.md` — SearXNG SX-5/6. Granite affects post-SearXNG ranking only.
- `/workspace/handoffs/active/minddr-deep-research-mode.md` — Indirect; tools layer.
- `/workspace/research/deep-dives/lighton-denseon-lateon-retrieval-upgrade.md` — Same-arch (ModernBERT) family for reranker side. Granite is its dense-retrieval cousin from a different lab.
- `/workspace/research/deep-dives/reason-mxbai-colbert-32m-edge-retriever.md` — Edge-scale ColBERT reranker. Granite at 97M is comparable in CPU latency class and adds the multilingual axis.
- `/workspace/wiki/search-retrieval.md` (synthesis page) — Update after bench lands.
- `/mnt/raid0/llm/llama.cpp/convert_hf_to_gguf.py` line 12452 — `ModernBertModel` registration confirms native support.
- `/mnt/raid0/llm/epyc-orchestrator/orchestration/repl_memory/parallel_embedder.py` — Existing BGE pool client; sibling for 384-dim Granite.

## 10. Final Verdict

**KEEP the original recommendation, but redefine the work scope**:

- ✅ Direction is right (CPU INT8 bench against BGE-M3 + multilingual-e5-base on EPYC)
- ❌ "1-day" is wrong — corpus prereq makes it 3–5 days minimum
- ❌ "Gated on K-track activation" is wrong — gate it on **K2 (eval corpus build) at minimum**, not K-track activation as a whole
- ❌ Original framing implies granite-97m-r2 is a swap-in — it's net-new infra with no current production role to replace
- ✅ Multi-pipeline targeting (KB + SearXNG) is correct
- ➕ Add code-search as a **third investigation angle**, deferred

**Refined recommended action**:

> **Granite-97M-r2 + comparators bench (3–5 days inference-free engineering, then 1 inference day)**, gated on **K2 chunker + minimal eval corpus existing**. Deploy via GGUF/llama-embedding pattern (port 8096) — matches existing BGE pool. 3-way bench {granite-97m-r2, multilingual-e5-base, BGE-M3} for nDCG@10 + per-doc encode latency on a 30–50-query EPYC-local eval set drawn from wiki + handoffs + (later) SearXNG snippet samples. Code-retrieval angle is a separate, deferred eval. ModernBERT compatibility on llama.cpp is **confirmed by source inspection**, sentence-transformers OpenVINO INT8 is **confirmed via v3.3.0 release**, no architectural risk on the deployment path.

## Sources

- IBM Granite Embedding 97M Multilingual R2 model card: https://huggingface.co/ibm-granite/granite-embedding-97m-multilingual-r2
- Granite Embedding R2 Models paper: https://arxiv.org/abs/2508.21085 (PDF: https://arxiv.org/pdf/2508.21085)
- llama.cpp source (ModernBERT registration): /mnt/raid0/llm/llama.cpp/convert_hf_to_gguf.py:12452
- llama.cpp source (graph builder): /mnt/raid0/llm/llama.cpp/src/llama-graph.cpp:2865
- sentence-transformers v3.3.0 OpenVINO INT8 release: https://github.com/UKPLab/sentence-transformers/releases/tag/v3.3.0
- ModernBERT paper / answer.ai: https://www.answer.ai/posts/2024-12-19-modernbert.html
- MMTEB benchmark: https://arxiv.org/abs/2502.13595
- Existing parallel embedder: /mnt/raid0/llm/epyc-orchestrator/orchestration/repl_memory/parallel_embedder.py
- Cross-handoffs: colbert-reranker-web-research.md, internal-kb-rag.md, searxng-search-backend.md, minddr-deep-research-mode.md
