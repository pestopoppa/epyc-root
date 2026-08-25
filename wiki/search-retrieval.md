# Search & Retrieval

**Category**: `search_retrieval`
**Confidence**: verified
**Last compiled**: 2026-08-23 — wave-2 retrieval compile: the prefix-guard silent-corruption fix (`4e5e84c0`), a published "MaxSim ceiling" that is a `query_maxlen = 32` truncation artefact, our length exposure re-sited from the query side to the document side, and the ONNX export-and-contract layer; earlier 2026-08-22 note: encoder-retirement record correction, K11 lexical null result, code↔docs federation.
**Sources**: 32 documents (last additions 2026-08-22: encoder-retirement record correction, K11 lexical null result, code↔docs federation)

## Summary

The EPYC stack uses ColBERT-based multi-vector retrieval for both codebase search and document search, with a separate BGE-large single-vector system for routing memory (MemRL episodic store). The retrieval architecture has been actively upgraded through the ColBERT-Zero research integration, which replaced the docs model with GTE-ModernColBERT-v1 and designed a MemRL distillation pipeline inspired by ColBERT-Zero's 3-stage training methodology. A handoff ready for implementation adds ColBERT-Zero snippet reranking to the web_research pipeline (pre-fetch filtering via PyLate MaxSim scoring).

The codebase retrieval system (NextPLAID) uses two ColBERT models: LateOn-Code (code search, port 8088) and GTE-ModernColBERT-v1 (docs search, port 8089, upgraded from answerai-colbert-small-v1-onnx). Both use 128-dim multi-vector representations with MaxSim scoring and PLAID PQ compression at nbits=4 (IVF+PQ hybrid). The code index is 336MB, docs index 31MB. These complement the MemRL episodic store which uses BGE-large 1024-dim single-vector embeddings with FAISS IndexFlatIP for routing memory retrieval.

The GTE-ModernColBERT-v1 upgrade (Track 1 of ColBERT-Zero integration) produced significant quality improvements: 5 of 10 test queries returned better results, 4 were equivalent, and none were worse. Particularly notable improvements appeared for queries about speculative decoding and REPL environment tools, where the old model returned unrelated files but the new model returned exact chapter matches. Latency increased from 28ms to 50ms (+78%), within acceptable bounds. The model uses `[Q]`/`[D]` prefixes read automatically from `onnx_config.json`, with a 768-dim hidden size projected to 128-dim via Dense layer.

Track 2 (MemRL distillation) designed a compressed routing classifier following ColBERT-Zero's insight that supervised fine-tuning before distillation is critical. The 3-stage pipeline maps to EPYC's context: (1) unsupervised contrastive learning on episodic store embeddings, (2) supervised training on (task, best_action) pairs weighted by Q-value, (3) distillation of HybridRouter decisions into a small classifier. The prototype classifier, training scripts, and A/B test harness are all implemented. The classifier integrates into HybridRouter as a fast first-pass, falling back to full retrieval when confidence is below 0.6.

The ColBERT reranker handoff (finalized 2026-04-14, ready for implementation) adds snippet-level pre-fetch reranking to the web_research pipeline. The implementation uses GTE-ModernColBERT-v1 (already deployed, BEIR 54.67) via ONNX Runtime rather than the originally planned PyLate library, which was eliminated because `fast-plaid` and `voyager` dependencies lack cp314 wheels for the orchestrator's Python 3.14 venv. The ONNX pipeline -- `onnxruntime` + `tokenizers` (both already in venv) loading `model_int8.onnx` (144MB INT8) -- produces per-token 128-dim embeddings with MaxSim scoring in numpy, totaling ~15 lines of code. Actual benchmarks on EPYC (S4, 2026-04-14) measured 180ms median encoding for 1 query + 10 snippets through the full 150M-param model, with <1ms for MaxSim scoring. While above the original <10ms target (which assumed pre-encoded embeddings), the ROI is ~750x since each irrelevant page saved eliminates 45s of worker synthesis. Ranking quality showed perfect separation on test data: relevant snippets scored 0.93-0.96, irrelevant scored 0.91-0.92. ColBERT-Zero (BEIR 55.43, <1pp better) download deferred unless accuracy issues emerge. Fallback model: mxbai-edge-colbert 17M (Apache 2.0, 6x smaller). S1 (relevance instrumentation) and S2 (feature flag registration) are complete; S1 instruments `_web_research_impl()` with `_is_irrelevant_synthesis()` heuristic and returns `pages_irrelevant`/`irrelevant_rate` in responses. Telemetry pipeline wired through `repl_executor.py`, `chat_delegation.py`, `WebResearchTelemetry`, and `analyze_web_research_baseline.py`. Data collection folded into AR-3 Package D. S5 (implementation) gated on post-AR-3 analysis confirming >20% irrelevant page rate.

A comprehensive literature survey (2026-04-14) confirmed the architecture decisions. Reason-ModernColBERT was eliminated due to CC-BY-NC-4.0 license despite strong BRIGHT performance (22.62/30.28 NDCG@10). Jina-ColBERT-v2 (89-language multilingual, Matryoshka dims) was deemed unnecessary as no multilingual requirement exists. The production consensus in 2026 is hybrid retrieval (BM25 + dense) → rerank top-20-30 → LLM, with cross-encoders on full index causing p99 blowup. Late-interaction (ColBERT-style) on small candidate sets is the established sweet spot. CPU feasibility is confirmed via proxy data: TurkColBERT achieves 0.54ms query latency under MUVERA indexing, and mxbai-edge-colbert encodes 50K docs in ~49s vs ColBERTv2 ~154s. For reranking 10 snippets, MaxSim over pre-computed embeddings is trivially fast on 192-thread EPYC.

A local hybrid search engine for markdown knowledge bases (intake-270, tobi/qmd) was marked as adopt_component with high relevance. MemPalace (intake-326, 96.6% LongMemEval recall) and LLM Wiki (intake-268, persistent LLM-compiled knowledge bases) were also flagged as relevant patterns.

A 2026-04-17 intake sweep (intake-405/406/407) mapped the XTR and WARP lines of the multi-vector retrieval landscape, providing architectural contrast to the deployed ColBERT approach. XTR (Google DeepMind, arXiv:2304.01982) represents an alternative scoring strategy: rather than computing MaxSim over all token interactions, XTR retrieves only the top-k scoring tokens and imputes scores for unobserved tokens, claiming 100–1000x cheaper inference. The real-world trade-off is confirmed by Witchcraft (github:dropbox/witchcraft, intake-405), a production Rust reimplementation of XTR-Warp: it achieves 21ms p95 latency on an M2 Max but only 33% NDCG@10 on NFCorpus, compared to ColBERT-Zero's 55.43 BEIR average. Witchcraft's deployment model is architecturally distinct from NextPLAID: a single zero-dependency Rust binary with embedded SQLite FTS and GGUF-quantized T5 inference via `candle`, suitable for offline or session-local indexing without a separate server process. WARP (arXiv:2501.17788, SIGIR'25, intake-406) represents a different optimization direction: keeping ColBERT's full MaxSim accuracy while achieving 3x speedup over PLAID and 41x over XTR reference through WARP_SELECT (dynamic similarity imputation skipping low-scoring candidates) and implicit decompression. WARP optimizes corpus-scale retrieval and is not relevant to the 10-snippet reranking case where MaxSim already completes in <1ms. Collectively, intake-405/406/407 validate the current ColBERT-family decision: at the snippet-reranking scale, accuracy dominates and ColBERT-Zero/GTE-ModernColBERT are the correct operating point.

A research intake deep-dive (2026-04-14) evaluated SearXNG (intake-359/360, 28.3k GitHub stars, AGPL-3.0) as a replacement for the current DDG HTML scraping + Brave fallback in `search.py`. The current `_search_duckduckgo()` function is 112 lines of fragile regex HTML parsing using subprocess curl, subject to bot detection and layout changes. SearXNG provides a self-hosted JSON API (`GET /search?q=...&format=json`) aggregating 250+ search engines with structured results including multi-engine provenance (`engines[]`, `positions[]`, `score` fields). Result merging is built-in -- when multiple engines return the same URL, they're merged with boosted score. The deployment is a Docker container (~183MB) with Granian ASGI server and optional Valkey sidecar for rate limiting. Critical caveats: (1) the limiter's API_MAX=4 requests/hour for JSON format blocks all programmatic use -- must be disabled for backend use, (2) bot detection blocks python-requests/curl user-agents when limiter is enabled, (3) JSON format is NOT enabled by default -- requires adding `json` to `search.formats` in settings.yml, (4) Google actively blocks SearXNG via TLS/HTTP2 fingerprinting, making it unreliable as an engine. Per-engine configuration supports weight multipliers, timeouts, retry policies, and proxy chains, allowing fine-tuning of individual engines. The `unresponsive_engines[]` field in JSON responses reports which engines failed per query, providing a monitoring signal without checking container logs. The SearXNG backend composes naturally with the ColBERT reranker S5: SearXNG returns top-N snippets via JSON, ColBERT reranks by MaxSim, top-3 get fetched and synthesized. An MCP server for SearXNG (intake-361, mcp-searxng, 635 stars, MIT) provides an alternative integration path for Claude Code sessions. Work items SX-1 through SX-6 are tracked in routing-and-optimization-index P12.

## Key Findings

### New (2026-04-22, DD1)

- **LightOn DenseOn/LateOn release (Apache 2.0, 2026-04)** [intake-428/430/431] is a same-family drop-in upgrade for deployed GTE-ModernColBERT-v1. LateOn: BEIR NDCG@10 **57.22** (+2.55pp over GTE-ModernColBERT-v1 at 54.67; +1.83pp over ColBERT-Zero at 55.43), decontaminated BEIR 60.36. DenseOn (dense sibling): BEIR 56.20 — first sub-150M dense model past 56, outperforms 4x-larger models. Both ModernBERT-149M. **Amended plan**: LateOn is now primary candidate for the colbert-reranker S5 swap, with GTE as fallback baseline (was ColBERT-Zero primary). Decontamination protocol (xxhash64 + 13-gram containment, threshold 0.5) adopted as EPYC-internal retrieval-eval standard. Newly unblocked: local NV-Retriever fine-tune on REPL+sentinel queries (Apache 2.0 corpora released).
- Deployed-model BEIR comparison table:

| Model | Params | BEIR NDCG@10 | Decontaminated | Deployed? | License |
|---|---|---|---|---|---|
| GTE-ModernColBERT-v1 | 149M | 54.67 | — | ✅ port 8089 | Apache 2.0 |
| ColBERT-Zero | 149M | 55.39 | — | No (was S5 primary until 2026-04-22) | Apache 2.0 |
| LateOn (intake-430) | 149M | **57.22** | **60.36** | Code ready (NIB2-47 2026-04-22; `LATEON_MODEL_PATH` env var activation) | Apache 2.0 |
| DenseOn (intake-431) | 149M | 56.20 | 57.71 | No (probe-first pool candidate) | Apache 2.0 |
| ~~Reason-ModernColBERT~~ | 150M | 22.62–30.28 BRIGHT | — | Eliminated | CC-BY-NC-4.0 |

### New (2026-07-14, backend degradation hygiene)

- **The SearXNG backend now carries an explicit degradation signal in the source record.** The 2026-07-14 audit recorded a `⚠ DEGRADED` guard when at least half the requested engines are unresponsive, so backend health can be read as environmental degradation instead of a silent query failure. The same audit also notes that brave/mojeek/bing blocks are instance or egress issues, not a reason to rewrite the search layer's architecture. Sources: [SearXNG Search Backend](../handoffs/active/searxng-search-backend.md), [Progress 2026-07-14](../progress/2026-07/2026-07-14.md).

### Existing

- Two distinct retrieval systems: ColBERT 128-dim multi-vector (codebase/docs) vs BGE-large 1024-dim single-vector (MemRL routing memory). Complementary, not competing [Ch.07 MemRL]
- GTE-ModernColBERT-v1 upgrade: 5/10 queries better, 4 same, 0 worse. Latency 28ms -> 50ms (+78%). BEIR avg 54.67, LongEmbed SOTA 88.39 [colbert-zero-research-integration.md]
- PLAID PQ compression at nbits=4 already enabled. Code index 336MB, docs 31MB [colbert-zero-research-integration.md]
- MemRL distillation prototype complete: 3-stage pipeline (unsupervised -> supervised -> distillation), A/B test harness ready, needs live seeding window [colbert-zero-research-integration.md]
- Query/document prefixes: LateOn-Code requires NO prefix (raw text only). GTE-ModernColBERT uses `[Q]`/`[D]` prefixes (auto-read from onnx_config.json). Adding prefixes to LateOn-Code would DEGRADE retrieval [colbert-zero-research-integration.md]
- ColBERT reranker S1-S4 complete: GTE-ModernColBERT-v1 via ONNX Runtime (PyLate eliminated -- no cp314 wheels). Encoding 1 query + 10 snippets: 180ms median, MaxSim <1ms. Perfect ranking separation (relevant 0.93-0.96 vs irrelevant 0.91-0.92). ROI ~750x (180ms reranking vs 45s wasted synthesis). Telemetry pipeline fully wired through 4 consumer modules. S5 implementation gated on post-AR-3 irrelevant page rate >20% [colbert-reranker-web-research.md]
- Reason-ModernColBERT ELIMINATED: CC-BY-NC-4.0 prohibits commercial use despite 22.62/30.28 BRIGHT NDCG@10. ColBERT-Zero achieves stronger general retrieval without license constraints [colbert-reranker-web-research.md]
- Late-interaction is the correct architecture: cross-encoders are 2 orders of magnitude slower, SPLADE is best as first-stage retriever not reranker, 8B dense reasoning retrievers compete for inference slots [colbert-reranker-web-research.md]
- MemRL FAISS retrieval: 0.5ms at 5K memories, 2ms at 500K, 3ms at 1M. 35x-1000x speedup over NumPy baseline [Ch.07 MemRL]
- The routing classifier provides fast first-pass routing, falling back to full HybridRouter retrieval when confidence < 0.6 [colbert-zero-research-integration.md]
- Cosine similarity > 0.85 used for deduplication in both SkillBank skill storage and episodic memory [Ch.15, Ch.07]
- SearXNG (intake-359/360) **implemented and tested** as DDG HTML scraping replacement: `_search_searxng()` in `search.py` calls the self-hosted JSON API on port 8888. Docker ~183MB + Granian ASGI. Default-on via `ORCHESTRATOR_SEARXNG_DEFAULT=1`, DDG fallback automatic. JSON response provides multi-engine provenance (`engines[]`, `positions[]`, `score`). Test results: 650-910ms latency, 3-engine consensus score ~9.9, 2-engine ~3.3, single <1. Google inactive (TLS fingerprint blocking). Engine tuning: DDG 1.2, Brave 1.1, Wikipedia 1.0, Qwant 0.9. `unresponsive_engines[]` + `search_backend` field wired into S1 relevance telemetry for AR-3 Phase 6b analysis [searxng-search-backend.md]
- mcp-searxng (intake-361, 635 stars, MIT) provides MCP bridge for SearXNG with `searxng_web_search` + `web_url_read` tools. Alternative integration path for Claude Code sessions [searxng-search-backend.md]
- **XTR (token retrieval) vs ColBERT (late interaction) is the fundamental architectural fork in multi-vector retrieval.** XTR (intake-407, Google DeepMind, arXiv:2304.01982) scores documents from a *subset* of retrieved tokens rather than all tokens, claiming 100–1000x cheaper inference at a meaningful accuracy cost. ColBERT scores using all token interactions (MaxSim over the full matrix). The Witchcraft real-world deployment confirms the trade-off: XTR achieves 33% NDCG@10 on NFCorpus vs ColBERT-Zero's 55.43 BEIR average — a ~22pp accuracy gap that validates the ColBERT choice for the 10-snippet reranking use case. [confidence: verified — intake-407/405, colbert-reranker-web-research.md 2026-04-17 section]
- **Witchcraft (intake-405) packages XTR-Warp as a zero-dependency embedded search engine** — a single Rust binary with GGUF-quantized T5 via the `candle` inference framework, hybrid BM25+semantic search, and SQLite FTS persistence. Reported p95 latency of 21ms (M2 Max), 2x faster than original XTR-WARP. The embedded/serverless deployment model (no separate server process, no network hop) is architecturally distinct from both NextPLAID containers and the ONNX reranker pipeline, and is interesting for session-local or offline document indexing use cases — not competitive with ColBERT-family for pipeline reranking accuracy. [confidence: verified — intake-405, colbert-reranker-web-research.md 2026-04-17 section]
- **WARP (intake-406, SIGIR'25, arXiv:2501.17788) achieves 3x speedup over ColBERTv2/PLAID and 41x over the XTR reference implementation** via two techniques: WARP_SELECT (dynamic similarity imputation that skips full MaxSim for low-scoring candidates) and implicit decompression (avoids materializing full PQ vectors during scoring). These are corpus-scale optimizations (millions of passages); for snippet-level reranking over 10 items, MaxSim already completes in <1ms so WARP's gains are immaterial to the current pipeline. Relevant if retrieval ever scales to large passage corpora. [confidence: verified — intake-406, colbert-reranker-web-research.md 2026-04-17 section]
- Crawl4AI (intake-372, 51K+ stars, Apache-2.0) is the preferred deep page scraping tool under the open-source-only policy. Async Playwright-based, local LLM extraction via Ollama, Docker deployment, no API keys. Complements SearXNG (search aggregation) with page content extraction for JS-heavy pages and PDFs. Evaluation gated on post-AR-3 WebFetch failure rate data [searxng-search-backend.md]
- Firecrawl (intake-364/365, 108K+ stars, AGPL-3.0) evaluation deferred: cloud-first SaaS model conflicts with self-hosted infrastructure philosophy. Self-hosted version lacks cloud parity. Credit-based pricing unpredictable [searxng-search-backend.md]
- **KB-RAG K1–K7 CERTIFIED 2026-06-13**: 70-case certification sweep (420 rows) selects `recency_w0.3_s90` (recall@10 0.6167, 0 missed-all-evidence) as the safe default candidate; `recency_w0.1_s90_rerank_w0.3` (0.6298, 3 missed) is the rank/recall@3 winner. Supersedes the seed-suite 0.6417 number, which over-reported vs the certification pool [internal-kb-rag.md]
- **MRAgent (intake-698) — active-reconstruction retrieval policy, comparator only**: evidence-conditioned retrieval-path pruning over a Cue-Tag-Content graph (LLM reasoning folded into retrieval) vs static retrieve-then-reason. Cloud-LLM-bound (no CPU/local path), loses to Mem0 on LoCoMo multi-hop F1; the transferable lever is token-cost discipline. Sits beside KB-RAG's parked self-correcting two-pass retrieval note [intake-698]

## 2026-06-13 Internal KB-RAG Status

The internal markdown KB-RAG path has moved from planned architecture to measurable retrieval system. K1-K6 are landed, and the fresh K7 build covers 577 files / 18,010 chunks / 1.2 GiB embeddings. The 20-case seed suite selected `recency_w0.1_s90` as the best recall@10 setting at 0.6417 overall; rerank variants improve early rank but can lose total recall and miss all evidence on some cases.

The live decision remains open because the 20-case seed suite is not the certification pool. The final 70-case set now exists and validates evidence file paths, protocol counts, and duplicate IDs. Retrieval claims should use the upcoming certification sweep, not the seed calibration numbers.

Source: [internal-kb-rag.md](../handoffs/active/internal-kb-rag.md).

## 2026-06-15 Update — K7 Certification, Not Just Seed Calibration

- **Internal KB-RAG has crossed from seed calibration to certification planning.** The fresh K7 build indexed 577 files into 18,010 chunks with roughly 1.2 GiB of embeddings; the 20-case seed suite chose `recency_w0.1_s90` at 0.6417 recall@10, but that number is explicitly calibration only until the 70-case certification pool runs. Source: [internal-kb-rag.md](../handoffs/active/internal-kb-rag.md).
- **The search frontend remains SearXNG plus Crawl4AI.** SearXNG provides the structured multi-engine search layer, while Crawl4AI is the local extraction path for JS-heavy pages and PDFs; `localhost:8888` stays the search endpoint and `11235` the Crawl4AI service. Source: [searxng-search-backend.md](../handoffs/active/searxng-search-backend.md).
- **RAG and search are explicitly separate from governance.** The wiki compilation pipeline still consumes handoffs and progress logs after curation, while KB-RAG handles ad hoc retrieval during agent runs; the two are complementary, not competing retrieval systems. Source: [handoff-backlog-hygiene-audit.md](../handoffs/completed/handoff-backlog-hygiene-audit.md).

## Actionable for EPYC

- **GTE-ModernColBERT-v1 is deployed**: Docs container swapped, reindexed (1992 chunks, 246s), model_registry.yaml and orchestrator_stack.py updated. Production-ready.
- **MemRL distillation A/B test**: All infrastructure ready (classifier, training scripts, test harness). Needs a live seeding window to collect fresh routing data for comparison.
- **ColBERT reranker for web_research (S1-S4 complete, S5 gated)**: Relevance instrumentation (S1), feature flag (S2), ONNX model pipeline (S3), and latency benchmark (S4) are all done. S5 (implementation in `research.py`) depends on post-AR-3 analysis confirming >20% irrelevant page rate. Run `analyze_web_research_baseline.py` after AR-3 for go/no-go decision.
- **ONNX Runtime replaces PyLate**: The existing GTE-ModernColBERT-v1 on disk (`model_int8.onnx`, 144MB) with `onnxruntime==1.24.4` provides identical encoding capability without PyTorch dependency. ColBERT-Zero download deferred unless accuracy issues arise in S6 A/B testing.
- **qmd hybrid search evaluation**: intake-270 marked adopt_component -- evaluate for markdown knowledge base search in the project wiki or handoff system.
- **MemPalace patterns**: intake-326 achieves 96.6% recall on LongMemEval. Investigate architecture patterns that could improve MemRL episodic retrieval quality.
- **SearXNG search backend (SX-1–4 done, SX-5/6 AR-3-gated, R&O P12)**: Container deployed on port 8888, `_search_searxng()` implemented, engine weights tuned, telemetry wired. Ports 8090-8095 belong to the BGE embedding pool and return llama-server 404s for SearXNG paths. Default-on. SX-5 (load test) and SX-6 (swap confirmation) folded into AR-3 Package D Phase 6b — post-AR-3 analysis compares engine failure rate, irrelevant page rate delta, and latency overhead vs DDG baseline.
- **Crawl4AI evaluation (post-AR-3, gated on WebFetch failure data)**: If web_research sentinel data shows significant JS-heavy fetch failures (>10%), deploy Crawl4AI Docker container alongside SearXNG for page content extraction. Apache-2.0 license, no API keys, local LLM extraction. Evaluate for ColBERT reranker fetch step (S5) where current WebFetch may fail on dynamic pages.

## Crawl4AI and Open-Source-Only Policy

Research intake evaluated two page-scraping tools complementary to SearXNG (which handles search aggregation, not deep page content extraction): Firecrawl (intake-364/365, 108K+ stars) and Crawl4AI (intake-372, 51K+ stars).

**Crawl4AI** (Apache-2.0) is a fully self-hosted, async Playwright-based web crawler designed for LLM consumption. Key capabilities: BM25 content filtering, LLM extraction with local models (Llama 3, Mistral via Ollama), browser pool management, and Docker deployment. No API keys required. It fills the same role as Firecrawl (converting web pages to LLM-ready markdown/JSON) but is fully local and free, matching the project's infrastructure philosophy. The integration path for EPYC is alongside SearXNG: SearXNG finds URLs via search aggregation, Crawl4AI could extract content from JS-heavy pages or PDFs that the current WebFetch tool cannot handle. It is also worth evaluating for the ColBERT reranker fetch step (S5).

**Firecrawl** (AGPL-3.0) was evaluated but deprioritized. While it has strong capabilities (scrape/crawl/map/interact APIs, P95 latency 3.4s, 96% web coverage, MCP server), its cloud-first SaaS model conflicts with the self-hosted philosophy. The self-hosted version lacks cloud parity (/agent, /browser not supported), and credit-based pricing is unpredictable (+4 credits for JSON mode, +4 for stealth per page).

**Policy decision (2026-04-14)**: Given the open-source-only infrastructure preference, Crawl4AI is the preferred evaluation target for deep page scraping. Firecrawl evaluation is deferred. Crawl4AI evaluation is gated on post-AR-3 data: if WebFetch succeeds on >90% of pages in web_research sentinel data, neither tool is needed short-term. If JS-heavy fetch failure rates are significant, Crawl4AI deployment should proceed.

> Source: [SearXNG Search Backend](/workspace/handoffs/active/searxng-search-backend.md) -- intake-364/365/372, Crawl4AI vs Firecrawl, open-source-only policy decision

## Open Questions

- What is the actual page contribution rate in current web_research sessions? (S1 instrumentation now live; AR-3 Package D will generate this data automatically via 50 web_research sentinel questions)
- Can the MemRL distillation classifier match HybridRouter quality on high-confidence decisions in production?
- Would ColBERT-Zero's general retrieval quality improve web_research synthesis measurably over DDG's keyword ranking? (GTE-ModernColBERT-v1 showed perfect separation on test data; real-world validation in S6 A/B test)
- Is the 50ms GTE-ModernColBERT latency acceptable under high-concurrency scenarios?
- Should the routing classifier's confidence threshold (0.6) be tuned via the conformal calibration system?
- What is the JS-heavy page failure rate in web_research sentinel data? This determines whether Crawl4AI deployment is needed or if WebFetch suffices for >90% of pages.

## Related Categories

- [Routing Intelligence](routing-intelligence.md) -- MemRL retrieval and routing classifier are core routing components
- [Training & Distillation](training-distillation.md) -- ColBERT-Zero 3-stage pipeline inspired MemRL distillation design
- [Cost-Aware Routing](cost-aware-routing.md) -- Reranking reduces unnecessary token consumption in web_research
- [Document Processing](document-processing.md) -- Better document parsing improves retrieval index quality

## Source References

- [ColBERT-Zero research integration](/workspace/handoffs/completed/colbert-zero-research-integration.md) -- Track 1 (GTE-ModernColBERT upgrade), Track 2 (MemRL distillation design), A/B results, implementation details
- [ColBERT reranker handoff](/workspace/handoffs/active/colbert-reranker-web-research.md) -- ColBERT-Zero snippet reranker for web_research pipeline, ready for implementation
- [Ch.07 MemRL System](/mnt/raid0/llm/epyc-orchestrator/docs/chapters/07-memrl-system.md) -- Episodic memory architecture, FAISS backend, two-phase retrieval
- [NextPLAID handoff](/workspace/handoffs/archived/nextplaid-code-retrieval.md) -- NextPLAID multi-vector code and document retrieval architecture
- [intake-174](https://huggingface.co/lightonai/Reason-ModernColBERT) Reason-ModernColBERT -- Late-interaction retriever (eliminated: CC-BY-NC-4.0 license; replaced by ColBERT-Zero)
- [intake-270](https://github.com/tobi/qmd) tobi/qmd -- Local hybrid search engine for markdown knowledge bases
- [intake-326](https://github.com/MemPalace/mempalace) MemPalace -- 96.6% LongMemEval recall local memory system
- [Progress 2026-04-14 Session 9](/workspace/progress/2026-04/2026-04-14.md) -- ColBERT reranker S1/S2 implementation, PyLate elimination, ONNX Runtime adoption, S4 latency benchmark results, telemetry pipeline wiring
- [SearXNG search backend handoff](/workspace/handoffs/active/searxng-search-backend.md) -- SearXNG JSON API replacement for DDG HTML scraping, work items SX-1–SX-6, tracked in R&O P12
- [intake-359](https://github.com/searxng/searxng) SearXNG -- Self-hosted metasearch aggregator (28.3k stars, AGPL-3.0, JSON API)
- [intake-360](https://docs.searxng.org/) SearXNG Documentation -- API reference, engine config, deployment architecture
- [intake-361](https://github.com/ihor-sokoliuk/mcp-searxng) mcp-searxng -- MCP Server for SearXNG (635 stars, MIT, TypeScript)
- [Progress 2026-04-14 Session 10](/workspace/progress/2026-04/2026-04-14.md) -- SearXNG research intake, deep-dive (6 findings), handoff integration across 6 files
- [intake-372](https://github.com/unclecode/crawl4ai) Crawl4AI -- Self-hosted async web crawler for LLMs (51K+ stars, Apache-2.0, Playwright-based, Docker deployment)
- [intake-364](https://firecrawl.dev) Firecrawl -- Web data API for AI (108K+ stars, AGPL-3.0, cloud-first SaaS -- evaluation deferred)
- [intake-405](https://github.com/dropbox/witchcraft) Witchcraft -- Rust XTR-Warp reimplementation: zero-dependency binary, GGUF T5 via candle, SQLite FTS, 21ms p95, 33% NDCG@10 NFCorpus (2x faster than original XTR-WARP)
- [intake-406](https://arxiv.org/abs/2501.17788) WARP: An Efficient Engine for Multi-Vector Retrieval -- SIGIR'25; 3x speedup over PLAID, 41x over XTR reference via WARP_SELECT + implicit decompression
- [intake-407](https://arxiv.org/abs/2304.01982) XTR: Rethinking the Role of Token Retrieval in Multi-Vector Retrieval -- Google DeepMind; token-subset scoring claims 100–1000x cheaper inference vs full MaxSim, confirmed by Witchcraft accuracy/speed profile
- [Reason-mxbai-colbert-32m deep-dive](../research/deep-dives/reason-mxbai-colbert-32m-edge-retriever.md) -- 2026-04-24: 32M-param edge-scale ColBERT fine-tuned for reasoning retrieval (BGE-reasoner + ReasonIR-HQ). On BRIGHT natural-language splits (biology 32.71, earth_science 43.88, sustainable_living 20.77, pony 20.73) it matches or beats the 150M Reason-ModernColBERT sibling — those are exactly our web_research workload pattern. The −3.6 BRIGHT full-mean gap is entirely from symbol-dense splits (leetcode, aops, theoremqa) due to case-insensitive tokenizer + sans_pos + 10-layer base depth. Extrapolated CPU latency ~40–50 ms p50 per 10-snippet call vs 180 ms for deployed 150M GTE. Targeted as the **3-slot operating-point fallback** in `colbert-reranker-web-research.md` S5 (GTE baseline / LateOn primary / Reason-mxbai fallback), conditional on ONNX INT8 parity + ≤80 ms p50 latency probe + A/B within 1pp of LateOn.
- [intake-453](https://huggingface.co/DataScience-UIBK/Reason-mxbai-colbert-v0-32m) Reason-mxbai-colbert-v0-32m -- 2026-04-22 release; widened projection head 64→128 dim preserving first 64; two-stage curriculum (VL warmup → BGE-reasoner/ReasonIR-HQ hard negatives); CachedContrastive loss; 8×H100 training on PyLate.

## Updates — 2026-04-28

This update records the internal KB-RAG architecture extension (K1–K8 plan), confirms LateOn drop-in upgrade readiness, captures Reason-mxbai-colbert-v0-32m as edge-scale fallback candidate with explicit Tier 2b caveats, and points at SLIDERS as a parallel architecture for cross-source aggregation.

### Internal KB-RAG architecture extension (2026-04-28)

Per [`internal-kb-rag.md`](../handoffs/active/internal-kb-rag.md):

- ColBERT-based RAG over the project's own wiki + handoffs + research + progress logs. Same multi-vector late-interaction architecture as web_research reranking; corpus is internal documents.
- **K1**: extracts shared encoder module from web_research path. Avoids duplicating ONNX runtime + tokenizer + MaxSim scoring code; single import surface for any reranking call site.
- **K7**: adopts Flywheel's HotpotQA + LoCoMo eval methodology. Python re-implementation of the eval harness; the harness *code* is Node/MCP/Obsidian-coupled and is NOT lifted.
- **K8** (wikilink learning-loop scorer) is deferred — see `wiki/memory-augmented.md` 2026-04-28 Updates.

### LateOn drop-in upgrade ready (NIB2-47, 2026-04-22)

Per [`colbert-reranker-web-research.md`](../handoffs/active/colbert-reranker-web-research.md) S3b/S5-amend:

- **Code complete.** PyLate parity script, `LATEON_MODEL_PATH` env var override, 13/13 tests landed.
- **Execution run deferred** pending `colbert-export` extras install (PyLate has a colbert-export optional extra needed for ONNX export of the LateOn checkpoint).
- **A/B gated on AR-3 Package D web_research data.** Comparison is LateOn (BEIR 57.22) vs deployed GTE-ModernColBERT-v1 (BEIR 54.67). Decision criterion: LateOn must show at least parity on EPYC's web_research workload before swap.

### Reason-mxbai-colbert-v0-32m edge-scale fallback candidate (intake-453)

- **Target use case**: 32M-param CPU-latency-budget candidate for ~40-50ms p50 per 10-snippet rerank, vs 180ms for the deployed 150M GTE.
- **BRIGHT performance**: 19.00 full-mean (−3.6 vs Reason-150M sibling). Matches or beats 150M sibling on the natural-language splits that resemble web_research traffic: biology 32.71, earth_science 43.88, sustainable_living 20.77, pony 20.73. The accuracy gap is concentrated in symbol-dense splits (leetcode, aops, theoremqa) due to case-insensitive tokenizer + sans_pos + 10-layer base depth.
- **ONNX INT8 export unvalidated.** PyLate→ONNX export path exists but has not been measured on this checkpoint.
- **Apache-2.0 frontmatter but CC-BY-NC-4.0 body license conflict** noted in README. Has to be resolved before any commercial-adjacent deployment.

**Caveats (Tier 2b)**:

1. README license conflict (Apache-2.0 frontmatter vs CC-BY-NC-4.0 body) must be resolved before any commercial-adjacent deployment. For our open-source-only self-hosted use this is a documentation issue, not a deployment blocker, but should be confirmed with the model authors.
2. **No ONNX INT8 variant shipped.** PyLate→ONNX export is an unvalidated dependency for our pipeline (pipeline expects `model_int8.onnx` style artifacts).
3. Base mxbai-edge-colbert-v0 authors self-describe as "proof-of-concept baseline." Reason fine-tune inherits this framing.
4. Released 2026-04-22; **no third-party replication yet**. Numbers are author-reported only.

**Action**: queue S5 as A/B candidate after AR-3 web_research sentinel data lands. Current operating-point fallback chain: GTE baseline → LateOn primary → Reason-mxbai 32M edge-scale fallback (latency-budget routes only).

### SLIDERS as alternative architecture (intake-494)

- **Cross-link to `wiki/rag-alternatives.md`.** SLIDERS targets cross-document aggregation via DB+SQL (3.9M-36M tokens per corpus); web_research reranking targets snippet selection from ~10-100 docs per query.
- **Not on the same scaling axis** as web_research reranking. Listing here as one-line pointer for index completeness only.
- Closure-inflation note: SLIDERS is a parallel architecture, not a competitor or upgrade path for ColBERT-family rerankers.

### Sources

- [`handoffs/active/internal-kb-rag.md`](../handoffs/active/internal-kb-rag.md) — K1–K8 plan, K7 Flywheel methodology
- [`handoffs/active/colbert-reranker-web-research.md`](../handoffs/active/colbert-reranker-web-research.md) — S3b/S5-amend LateOn drop-in upgrade
- [intake-453](https://huggingface.co/DataScience-UIBK/Reason-mxbai-colbert-v0-32m) Reason-mxbai-colbert-v0-32m — edge-scale fallback candidate (Tier 2b caveats)
- [`research/deep-dives/reason-mxbai-colbert-32m-edge-retriever.md`](../research/deep-dives/reason-mxbai-colbert-32m-edge-retriever.md) — full deep-dive
- intake-492 (Flywheel) — HotpotQA + LoCoMo eval methodology lifted (Python re-implementation, NOT Node/MCP runtime)
- intake-494 (SLIDERS) — parallel architecture, cross-link to `wiki/rag-alternatives.md`

## Updates — 2026-04-29

### ColGREP CLI replaces NextPLAID code container for `code_search()` (intake-355, S7)

Per [`handoffs/active/repl-turn-efficiency.md`](../handoffs/active/repl-turn-efficiency.md) S7. ColGREP is the same NextPLAID engine family (LateOn-Code-edge ColBERT) packaged as a single Rust binary with hybrid FTS5+ColBERT scoring fused via Reciprocal Rank Fusion and tree-sitter AST chunking. v1.0.6 panicked on ONNX/GPU init on the CUDA-less EPYC host; v1.2.0 (released 2026-04-10) replaced the panic with a CPU-fallback message and added `NEXT_PLAID_FORCE_CPU` / `--force-cpu`.

**Live A/B (paired, n=14 ground-truth queries, 2026-04-29)** — `_code_search()` routed through colgrep CLI vs NextPLAID HTTP, identical input:

| Engine | Top-1 | Top-3 | p50 latency | p95 latency |
|---|---|---|---|---|
| **colgrep** | **10/14 (71%)** | **13/14 (93%)** | 964 ms cold (224 ms steady-state) | 2.8 s |
| NextPLAID | 2/14 (14%) | 4/14 (29%) | 190 ms | 5.5 s |
| Top-1 agreement | 0/14 | — | — | — |

NextPLAID lost 8/14 queries to landings in `tests/` files because its index covered the whole project (8826 docs); colgrep's index covered `src/` only (312 units). For `code_search()`'s actual use case — production-code retrieval, not test code — colgrep's narrower scope is a feature, not a limitation. Default flipped to colgrep on 2026-04-29 with explicit `REPL_COLGREP=0` opt-out for instant rollback. `doc_search()` (port 8089) untouched — colgrep is code-focused via tree-sitter and a poor fit for prose.

**Operational implications**:

- One Rust binary (80 MB) replaces one Docker container (~31 GB resident). Runtime now defaults to the version-pinned local copy `/mnt/raid0/llm/UTILS/bin/colgrep-1.2.0` (`sha256:833e52aa6c40d090142fa132e3c75d3e792a4707474682a2496e3471f646f956`); `REPL_COLGREP_BIN` remains the override.
- Subprocess-per-query: every `_code_search()` call pays full ONNX runtime + ColBERT model load. A 2026-06-14 warmed production-wrapper soak measured p50 208.5 ms / p95 213 ms / max 224 ms with zero wrapper fallbacks across 32 calls after a 52s `src/` index init. Acceptable for human-paced REPL; daemon work is not active unless future live turn-frequency gates fire.
- `REPL_COLGREP_ALPHA=0.95` (overridable). Default 0.75 over-ranks `__init__.py` re-exports for symbol queries in this corpus; 0.95 weights ColBERT semantic over FTS5 keyword and recovers correct top-1 on validated cases.
- Hybrid scoring quirk: ColGREP returns FTS5+ColBERT fused scores in ~1–5 range, not NextPLAID's normalized 0–1. Frecency boost (0.3 × score multiplier) is rank-stable but downstream code that assumes 0–1 scale would need normalization.

**Soak/version gate**: closed 2026-06-14. `_exploration_log` and `_code_search_telemetry` now record ColGREP engine, latency, fallback status, and fallback reason. The warmed soak did not justify a daemon, and the default binary path is version pinned. Do not add ColGREP re-index-on-commit yet: ColGREP auto-updates on search, manual `colgrep init /mnt/raid0/llm/epyc-orchestrator/src` is enough after large source reshapes, and a hook would add CPU contention without current evidence of stale-index failures.

### Sources

- [`handoffs/active/repl-turn-efficiency.md`](../handoffs/active/repl-turn-efficiency.md) S7 — ColGREP integration, live A/B verdict, default flip, cold-start daemon options
- [`progress/2026-04/2026-04-29.md`](../progress/2026-04/2026-04-29.md) — session log
- intake-355 NextPlaid/ColGREP — v1.2.0 unblock notes
- v1.2.0 release notes (`github.com/lightonai/next-plaid` 2026-04-10) — panic→fallback, hybrid search, pipelined indexing

## Granite-Embedding-97M-Multilingual-R2 — IBM dense retriever, ModernBERT-based (2026-04-30)

**TL;DR**: IBM's `granite-embedding-97m-multilingual-r2` (Apache 2.0, 97M params, ModernBERT backbone, 32K context, claimed MTEB-ML-Retrieval 59.6 on 18 tasks) is the highest-scoring open <100M-class multilingual embedder. Worth benching as the dense first-stage retriever in front of GTE-ModernColBERT-v1 reranker for KB-RAG, web-research, and SearXNG. **No production multilingual retrieval today** — would be net-new infra (current production: English-only BGE-large-en-v1.5 routing pool on `:8090–:8095`).

### Headline numbers (caveat: most claims unverified by 3rd parties at intake date)

| Metric | Value | Caveat |
|--------|-------|--------|
| MTEB Multilingual Retrieval (18) | 59.6 | 18-task composition not enumerated; likely MIRACL (Wikipedia-only) — may not represent web snippets |
| MTEB Retrieval (eng v2) | 50.1 | — |
| Code (v1, 9 langs) | 60.5 | Trained languages: Python/Go/Java/JS/PHP/Ruby/SQL/C/C++ |
| LongEmbed (6) | 65.5 | Validates 32K-context plausibility |
| AVG | 52.1 | — |
| Throughput | 2,894 docs/s | **GPU (H100), NOT CPU** — calibrate EPYC expectations independently |
| vs multilingual-e5-small | +8.7 pts MTEB-ML-Retrieval | Same 18-task composition |
| vs gte-multilingual-base (305M) | matched quality, 3× speed | GPU figure |

**vs BGE-M3 (~63.0 MTEB)**: BGE-M3 is from MMTEB 131-task aggregation — **NOT apples-to-apples** with IBM's 18-task 59.6. Bench needs to produce same-corpus same-metric numbers to settle.

### ModernBERT compatibility — clean across the board

- **llama.cpp**: native support — `convert_hf_to_gguf.py:12452` registers `ModernBertModel(BertModel)` with `MODEL_ARCH.MODERN_BERT`, sliding-window + RoPE handling. Model card explicitly provides a `convert_hf_to_gguf.py` example.
- **Sentence-transformers**: v3.3.0+ ships OpenVINO INT8 quantization (~4× CPU speedup); requires `transformers ≥ 4.48.0`.
- **"Ollama unsupported - ModernBERT" line refers ONLY to Ollama's wrapper.** llama.cpp is fully supported.
- **Recommended deployment path on EPYC**: GGUF + `llama-server --embedding` on port `:8096` (matches existing BGE-large `:8090–:8095` pattern). The local llama.cpp build currently has `llama-server` and `llama-quantize`, but no standalone `llama-embedding` binary. The OpenVINO/sentence-transformers route requires cp312/cp313 venv (orchestrator currently cp314).

### Bench plan (handoff-driven)

`handoffs/completed/granite-97m-r2-bench-plan-completed-through-2026-08-23.md` (K2 chunker output is preferred, but the fallback code corpus is no longer blocked on K2):

- **Phase A**: fallback corpus + dry-run harness are verified as of 2026-06-20 (`100` Python snippets, `30` labeled queries, no missing relevance refs). HF sources are staged locally under `/mnt/raid0/llm/hf/` for Granite (`model.safetensors` 194,889,568 bytes), multilingual-e5-base (`model.safetensors` 1,112,201,288 bytes), and BGE-M3 (`pytorch_model.bin` 2,271,145,830 bytes; dense-only comparator path). Warm/default-off orchestrator recipes landed in `e2922d7` for Granite on `:8096`, multilingual-e5-base on `:8097`, and BGE-M3 dense on `:8098`. Remaining prep is GGUF Q8_0 + Q4_K_M conversion/quantization and a load/vector smoke.
- **Conversion env**: staged outside repo worktrees at `/mnt/raid0/llm/venvs/llama-gguf-convert`; verified imports for CPU `torch`, `transformers`, `safetensors`, `sentencepiece`, `numpy`, and `gguf`, plus `convert_hf_to_gguf.py --help`. Avoid conversion during future throughput-sensitive benchmark windows.
- **Phase B (1 inference day)**: throughput bench (1000 docs across 6 length buckets), nDCG@10 / recall@10/50, 32K context probe (validate paper-vs-card discrepancy: paper says 8K, card says 32K), end-to-end with GTE-ModernColBERT-v1 reranker.
- **Phase C decision**: adopt granite (if NDCG@10 within 3pp of BGE-M3 AND ≥3× faster) / adopt BGE-M3 (if ≥5pp better, latency acceptable) / defer both (if neither beats BGE-large-en on actual EPYC corpus).

### Code-search angle (deferred sub-track)

Granite claims 60.5 on MTEB Code (v1) across 12 tasks with explicit training on 9 programming languages. Could serve as a NL→code-context first-stage retriever — additive to GitNexus (symbol-level static analysis, different problem) and to GTE-ModernColBERT-v1 (general retrieval, not code-specialized). Defer the code-search bench until KB-RAG bench corpus lands so eval-corpus engineering happens once.

### Risks

- ModernBERT in llama.cpp is functional but newer than the BERT path — verify no edge cases on first GGUF conversion.
- 32K context claim may degrade in practice past 8K; LongEmbed (6) score 65.5 helps.
- IBM model card may revise scores post-1-day-old release as third-party leaderboard data appears.
- BGE-M3 sparse + multi-vector outputs are NOT used in this bench (we measure dense-only). For ColBERT-style multi-vector first-stage, BGE-M3 has a built-in path; granite does not.

### Sources

- [intake-519](https://huggingface.co/ibm-granite/granite-embedding-97m-multilingual-r2) Granite-Embedding-97M-Multilingual-R2 (HF model card)
- [Granite Embedding R2 paper](https://arxiv.org/abs/2508.21085) (R2 family paper)
- [Granite Embedding paper](https://arxiv.org/abs/2502.20204) (R1 family)
- llama.cpp ModernBERT support: `convert_hf_to_gguf.py:12452`
- [`research/deep-dives/granite-embedding-97m-r2-evaluation.md`](../research/deep-dives/granite-embedding-97m-r2-evaluation.md) — full bench plan, alternatives Pareto, risk register
- [`handoffs/completed/granite-97m-r2-bench-plan-completed-through-2026-08-23.md`](../handoffs/completed/granite-97m-r2-bench-plan-completed-through-2026-08-23.md) — claim-ready bench plan
- [intake-698](https://arxiv.org/abs/2606.06036) MRAgent ("Memory is Reconstructed, Not Retrieved") — active-reconstruction retrieval policy (Cue-Tag-Content graph + evidence-conditioned path pruning); cloud-LLM-bound comparator to KB-RAG's parked self-correcting two-pass retrieval; token-cost discipline is the transferable lever

## Web research pipeline — SearXNG + Crawl4AI (2026-05-06)

Self-hosted web research pipeline combining SearXNG (meta-search; localhost:8888) with Crawl4AI (page-content extraction). Documented in handoff [searxng-search-backend.md](../handoffs/active/searxng-search-backend.md). The combined pipeline replaces SaaS web-search dependencies (Exa, Tavily, Firecrawl SaaS) while preserving multi-engine consensus + structured JSON output for tool integration.

**Routing rule** (CLAUDE.md updated): prefer SearXNG (`bash scripts/search/searx.sh`) when ≥3 web searches in one phase, querying non-English sources, requiring engine-consensus, or piping through `jq`. Fall back to built-in `WebSearch` for one-shot lookups or when SearXNG health check fails (script exits 2).

### Firecrawl vs Crawl4AI comparison

Deep-dive [firecrawl-vs-crawl4ai-web-pipeline-steps-2-3.md](../research/deep-dives/firecrawl-vs-crawl4ai-web-pipeline-steps-2-3.md) compares Firecrawl (managed SaaS) vs Crawl4AI (open-source self-hostable) for the page-content + extraction stages of the research pipeline. Crawl4AI selected for the EPYC self-hosted constraint per `feedback_opensource_only.md`.

Source: [handoffs/active/searxng-search-backend.md](../handoffs/active/searxng-search-backend.md), [research/deep-dives/firecrawl-vs-crawl4ai-web-pipeline-steps-2-3.md](../research/deep-dives/firecrawl-vs-crawl4ai-web-pipeline-steps-2-3.md).

## Internal KB-RAG over markdown corpus (2026-05-06)

Standalone ColBERT-backed retrieval over the project's compiled markdown KB so Explore-agent calls can semantic-search instead of grep-blind across 53+ active handoffs + 24 wiki articles + 246 source documents. Architecture:

- **Encoder**: shared `epyc-orchestrator/src/retrieval/colbert_encoder.py` exposing `encode(text, max_tokens) → token-level embeddings`, `maxsim(q, d) → score`, lazy ONNX session + tokenizer (GTE-ModernColBERT-v1 INT8 by default; `LATEON_MODEL_PATH` env override). Two consumers: web-search reranker (`src/tools/web/colbert_reranker.py` — kept untouched for back-compat with `research.py:322` import) and KB-RAG.
- **Chunker**: heading-aware (`^#{1,3} `) with 4000-char cap and paragraph-boundary sub-split for long sections; carries `(file_path, heading_path, line_range, content_hash)` per chunk.
- **Storage**: per-chunk `.npz` of token embeddings + SQLite catalog mapping `(chunk_id, file_path, heading_path, line_range, mtime, content_hash)`. mtime + content_hash dedup makes rebuilds incremental.
- **Query**: top-K MaxSim ranking returning `{file, heading_path, line_range, snippet, score}`.
- **Index refresh**: `.claude/hooks/post_commit_kb_rag_update.sh` re-encodes only files in `git diff --name-only HEAD^` filtered by corpus globs.
- **Discovery for agents**: `.claude/skills/kb-search/SKILL.md` documents when to prefer KB-RAG over grep (semantic / cross-cutting / topical queries) and when not to (exact-string match → grep, code → GitNexus, archived/ excluded by design).

**Live build (2026-05-06)**: 409 markdown files → 13,537 chunks → 861 MiB of embeddings, 17:01 wall-time (~76 ms/chunk). Sample retrievals score 0.93+ on relevant chunks (`"context folding"` → CF deep-dive at 0.95; `"how do we handle CPU NUMA optimization"` → numa-mirror handoff at 0.94; `"ColBERT reranker"` → 2026-04-14 progress entry at 0.93).

**Design choice — additive, not refactor**: per Plan agent advisory, the new `colbert_encoder.py` is purely additive. The reranker keeps its own ONNX session; KB-RAG creates a separate session. Cost: ~280 MB total RAM if both are imported in the same process. Benefit: zero risk to the deployed reranker, no need to edit `research.py:322`. Future cleanup option: refactor reranker to delegate to the shared module.

Sources: [`handoffs/active/internal-kb-rag.md`](../handoffs/active/internal-kb-rag.md), `epyc-orchestrator/src/retrieval/`, `epyc-orchestrator/scripts/kb_rag/cli.py`, `.claude/skills/kb-search/SKILL.md`.

## Intake deep-dives: turbovec & OBLIQ-Bench (2026-06-12)

Two retrieval-adjacent intake entries (intake-686, intake-689) were deep-dived and **both down-graded** from their initial worth_investigating framing.

**turbovec (intake-686) — NO-GO / parked.** A Rust+Python MIT vector index applying Google TurboQuant (arxiv:2504.19874) to standalone retrieval: data-oblivious quantization (no training), ~8× RAM cut, FAISS-parity search via AVX-512BW/NEON nibble-LUT kernels. The pitch collapses against our **actual** baseline: the orchestrator's repl_memory/strategy_store run `faiss.IndexFlatIP` (EXACT, dim-1024 BGE-large, `faiss_store.py:103`), **not a PQ index** — so an 8×-RAM-with-PQ-parity tool has nothing to beat. Live footprint is ~304 MB (episodic ~72.8K vecs + strategy ~1.3K) of a 1.1 TB host; the 31 GB→4 GB headline assumes a 10M-doc corpus we don't have. The +12–20% QPS win is ARM/NEON-only; on EPYC's AVX-512 x86 it's PQ-parity-to-negative. **Kernel-mining rejected**: turbovec's kernel is a FastScan nibble-LUT *distance scanner* (LUT-throughput-bound) vs our BW-bound 8×8 Q8_0 GEMV — different op/layout/bottleneck. KB-RAG is multi-vector MaxSim, which turbovec's single-vector MIPS API doesn't model. **WATCH-gate**: revisit only if a single-vector corpus exceeds ~1M vectors under real RAM pressure.

**OBLIQ-Bench (intake-689) — methodology-reuse, not dataset-reuse.** A retrieval benchmark (Khattab et al., MIT) exposing a **retrieval-verification asymmetry**: reasoning LLMs reliably *verify* latent relevance once a doc is surfaced, but single-stage retrievers fail to *surface* oblique-relevant docs — BEIR/BRIGHT saturation hides this. The dataset is released (HF `dianetc/OBLIQ-Bench`, CC-BY-4.0) but its corpora (tweets / WildChat / Congress / writing-style) are **out-of-domain** for our code/doc retrieval — do NOT fold OBLIQ rows into the Phase-B reranker eval corpus. The transferable asset is the **`gap(t)=V_t−R_t` metric + 5-stage oblique-query construction recipe**, re-applied to author an oblique *code/KB* slice. Crucially, **LateOn's OBLIQ scores (NDCG@10 0.003–0.149) are floor-level/out-of-domain and must NOT be cited against LateOn adoption** — the LateOn/DenseOn upgrade gates (S3b/S4b/S5) stay on BEIR 57.22 / decontaminated 60.36. Core thesis (bottleneck = first-stage **recall**, not verification) **supports keeping/strengthening the LLM-rerank stage**. Oracle is closed GPT-5.2; reproduce only a lower-bound `gap_open` via an open verifier route.

Sources: [`research/deep-dives/2026-06-12-turbovec-vector-index.md`](../research/deep-dives/2026-06-12-turbovec-vector-index.md), [`research/deep-dives/2026-06-12-obliq-bench-retrieval-eval.md`](../research/deep-dives/2026-06-12-obliq-bench-retrieval-eval.md), [`handoffs/active/internal-kb-rag.md`](../handoffs/active/internal-kb-rag.md), [`handoffs/active/colbert-reranker-web-research.md`](../handoffs/active/colbert-reranker-web-research.md), intake-686/689.

## 2026-06-21 Update — K7 Certified + MRAgent Retrieval-Policy Comparator

- **Internal KB-RAG K1–K7 is now CERTIFIED (2026-06-13), superseding the 2026-06-15 "certification planning" framing.** The 70-case certification pool (50 HotpotQA-template + 20 LoCoMo-template) was run as a clean-window parallel sweep (420 rows, all evidence files present). The aggregate recall@10 winner is `recency_w0.1_s90_rerank_w0.3` at 0.6298 (3 missed-all-evidence cases), but `recency_w0.3_s90` is within the declared 2pp noise band at 0.6167 and is the **only** config with **0 missed-all-evidence** cases — so it is the safe default candidate, while the rerank winner is reserved for workloads that explicitly optimize first-evidence rank / recall@3. This retires the earlier caveat that the 20-case seed numbers (`recency_w0.1_s90` at 0.6417) were "calibration only" — the seed value over-reported relative to the certification pool, confirming why the seed suite was never the decision basis. K9 cross-encoder rerank stays measure-first (it raises recall@3 but misses 3–5 all-evidence cases on the certified pool); K11 FTS5 lexical signal is implemented default-off pending its own sweep. Source: [internal-kb-rag.md](../handoffs/active/internal-kb-rag.md) K7 certification result.
- **MRAgent (intake-698) is a retrieval-*policy* comparator for KB-RAG's parked self-correcting two-pass retrieval, not a deployable component.** It reframes retrieval as **active reconstruction** — interleaving LLM reasoning with memory access and doing **evidence-conditioned retrieval-path pruning** over a Cue-Tag-Content associative graph, rather than the static retrieve-then-reason pipeline that ColBERT/MaxSim reranking implements. Reported LongMemEval 86.76% vs Mem0 53.01% and ~118k tokens vs 245k–3,268k for baselines. **Cloud-LLM-bound** (Gemini-2.5-Flash / Claude-Sonnet-4.5 for both graph construction and retrieval reasoning), no CPU/local/quantized path, and it actually loses to Mem0 on LoCoMo multi-hop F1 (43.69 vs 45.17) — so accuracy/token figures are observations, not decision-gating. The **transferable lever is token-cost discipline via path-pruning**: it is a second instance of the same deferred-pending-a-consumer-signal pattern that parked KB-RAG's self-correcting two-pass retrieval, and belongs alongside that note as a comparative datapoint. Source: intake-698 (arxiv:2606.06036); [internal-kb-rag.md](../handoffs/active/internal-kb-rag.md).

## Compiled Update — 2026-07-29: the LFM2.5-ColBERT path is open — which makes it a scope question, not a cost question

**Confidence**: verified for the availability and code-path facts (repository
listings, conversion/registration sites and graph builders read at our frozen v8
pin); **observation-grade** for every vendor benchmark number quoted.

### Correction: the "no GGUF / llama.cpp" premise was false, and had been false for five months

The record held that the Liquid late-interaction retriever required a specific
Python indexing framework and had **no GGUF / llama.cpp / Transformers / ONNX /
MLX** path. This is **false for the 2.5 generation, and was already false for the
1.x generation when the line was written**: **three GGUF repositories exist** —
`LFM2.5-ColBERT-350M-GGUF` and `LFM2.5-Embedding-350M-GGUF` (both 2026-06-16) and
`LFM2-ColBERT-350M-GGUF` (**2026-01-05**, roughly five months before the claim was
recorded). Each ships **seven quants** (BF16/F16/Q4_0/Q4_K_M/Q5_K_M/Q6_K/Q8_0)
plus reference `colbert-rerank.py` / `dense-retrieve.py` scripts driving
`llama-server /embedding` with **client-side MaxSim** — i.e. the same
late-interaction shape our existing plumbing uses.

The backbone is **bidirectional** (`Lfm2BidirectionalModel`; 17 layers = 10 conv
+ 6 attention + 1 dense), not causal as previously assumed. **Our frozen v8 tree
already supports it end to end with no kernel work**: the conversion script
registers `Lfm2Model`/`Lfm2BidirectionalModel` onto a ColBERT model class with
`add_causal_attention(False)` and a `dense_2` projection; the C++ side has the
non-causal symmetric-padded conv path and a dense-output graph builder. The run
path is the vendor's one-liner: `llama-server -hf … --embeddings`. One gap is
deliberately **not** closed — the *encoder* architecture
(`Lfm2BidirectionalForMaskedLM`) is unregistered, and buys nothing until an
encoder workload exists.
[`internal-kb-rag.md`](../handoffs/active/internal-kb-rag.md) §Open Question 1 (corrected 2026-07-29)

### The counterweight the swap case never had

Correcting the availability claim does **not** make the swap attractive. On the
vendor's own numbers, against our certified incumbent GTE-ModernColBERT-v1:

| Axis | Candidate | Incumbent | Delta |
|---|---|---|---|
| English NDCG@10 | 0.687 | 0.680 | **+0.7pp — inside our declared 2pp noise floor** |
| MKQA-11 Recall@20 | 0.748 | 0.754 | **−0.6pp — the incumbent is ahead** |
| Multilingual AVG | 0.605 | 0.489 | +11.6pp |
| Arabic | 0.551 | 0.309 | +24.2pp |
| Korean | 0.590 | 0.368 | +22.2pp |

**The large gaps are entirely multilingual, and our KB corpus is English
markdown.** Expected gain is therefore ~zero unless we index non-English sources.
The correct conversion is from *swap candidate* to a **bounded probe on the
existing K7 70-case pool, gated on the 2pp noise floor** — and the open question
becomes one of **scope** (do we intend to index non-English material?) rather
than one of **cost**.

Licensing note recorded at the same time: the open license conditions commercial
use on a **$10M annual-revenue threshold** — non-binding at our scale, but not
the unrestricted license the vendor's blog describes.

### Retrieval alongside grep — a correction with the sign reversed

A relayed reading treated "14.92 / 9.84 / 8.33" as retrieval scores arguing
against an embedding index. They are **counts of `grep`/`rg`/`find` shell
invocations**, and the same paper's Table 2 has the **dense retriever winning**
(90.0/86.0 vs 89.0/83.0). The transferable finding is **behavioural
substitution** — agents reach for shell search when retrieval is absent — which
argues for retrieval **alongside** grep, not against the index. Correct this
before it informs index design.
[`internal-kb-rag.md`](../handoffs/active/internal-kb-rag.md) §2026-07-29 dive corrections

### Lexical full-text search is not similarity retrieval

The trace store's existing per-case layer is SQLite + **FTS5**, which is lexical.
The pattern-distillation/experience layer being designed on top of it needs a
genuine **embedding column** — the BGE servers already resident on `:8090-8095`
are the available substrate. Recording this because "we already have search"
(meaning FTS5) is the kind of statement that silently converts a similarity
requirement into a keyword one.
[`unified-trace-memory-service.md`](../handoffs/active/unified-trace-memory-service.md) §UTM-M2

### Treat an embedder substitution as a first-class experimental change

The one independent replication of an external memory system **failed
specifically at the retriever** after an embedder swap — precisely the
substitution we would make when porting a published design onto local BGE. Paired
with the k-ablation losing **half its benefit by k=4** (49.7 / 46.0 / 45.5 /
44.4), the operational rule is that retrieval depth and embedder identity are
**measured parameters of the port**, not implementation details of it.
[`engram-conditional-memory.md`](../handoffs/active/engram-conditional-memory.md) §Research Intake Update 2026-07-29

### A purpose-built prompt-router encoder, filed as a comparator only

The same model family ships a purpose-built **prompt-router encoder**. It is
recorded as a `monitor_only` **comparator** for what a dedicated router head buys
over our MLP learned-routing controller — explicitly **not** a replacement
candidate, because opening it as one would fork an already-unfinished program
(Phase 1 complete, Phases 1.5–3 outstanding).
[`routing-intelligence.md`](../handoffs/active/routing-intelligence.md) §RI-CMP-1

### Source References

- [`internal-kb-rag.md`](../handoffs/active/internal-kb-rag.md) — the struck PyLate/PLAID-only premise; three GGUF repos and the seven-quant/reference-script surface; the v8 conversion + graph-builder support chain; the English-vs-multilingual counterweight; K-eval re-scope; corrected grep-count reading
- [`unified-trace-memory-service.md`](../handoffs/active/unified-trace-memory-service.md) — FTS5 is lexical; the embedding column the experience layer needs; BGE servers on `:8090-8095`
- [`engram-conditional-memory.md`](../handoffs/active/engram-conditional-memory.md) — the replication that failed at the retriever after an embedder swap; k-ablation decay
- [`routing-intelligence.md`](../handoffs/active/routing-intelligence.md) — the prompt-router encoder filed as a `monitor_only` comparator

## Compiled Update — 2026-08-22: the encoder swap's stated rationale was false, the lexical signal bought nothing, and the live index has outgrown its record

**Confidence**: verified — every number below carries either a commit/rev provenance chain, a
protocol-tagged sweep result, or a cross-validated on-disk measurement. Open work items adjacent to
these findings (the record edits, the encoder fixes, the GrepSeek four-arm A/B) are deliberately
NOT compiled; only the established diagnoses and measurements are.

### The answerai→GTE retirement rationale was false when it was written — and the real win was cost, not quality

**The Feb-2026 docs-encoder swap is justified on file by "answerai unscored", and that premise is
false** (2026-08-21 Stage-2b source audit, intake-1278). Controlled same-BEIR-15 figures had existed
on the successor's own model card since 2025-05-14: **GTE-ModernColBERT-v1 54.67 vs
answerai-colbert-small-v1 53.35** (LightOn's own re-run of the published checkpoint) — a **1.32 pp
gap, inside the ~2 pp noise floor this wiki's own KB-RAG doctrine declares**. A 2026-08-22
correction-of-the-correction tightened the harness count: **two independent BEIR measurements exist,
not three** — vendor 53.79 and LightOn's re-run 53.35; the apparent third (mixedbread, arXiv
2510.14880) transcribed both ColBERT baseline rows from LightOn's model card published 36 days
earlier (15/15 exact per-task match to the re-run column, 0/15 to the vendor-reported one). The
1.32 pp figure is unaffected because it was always LightOn's own comparison.

**The cost axis the original decision never weighed is where the swap actually pays**: answerai is
4.46× fewer parameters, and its measured index footprint is **−24.3 %** (0.757×, cross-validated
against the stored `.npz` to 0.2 %) — essentially the bare 96/128 dim ratio, with the tokenizer swap
a wash at 1.026. **This does not argue for reverting**; it argues that the record should say plainly
the swap rests on a quality delta our own doctrine calls noise.

**Reconciliation with earlier sections of this page**: the internal query-level A/B compiled above
(5/10 queries better, 4 equivalent, 0 worse) is untouched — it measured our corpus directly and
remains the strongest pro-GTE evidence. What changes is only the BEIR-based retirement rationale in
`CHANGELOG.md` and the completed ColBERT-Zero handoff. Two figure-hygiene rules ride along:
**never record `54.89` as the incumbent's BEIR-15** — it does not exist on the model card (`grep -c`
= 0 at rev `25f6f7bb`); the canonical comparable figure is **54.67** (BEIR table added `78d50a16`
2025-05-14, FiQA corrected `6605e431` 2025-09-10). A `54.75` also circulates with no stated
denominator (conflict flagged on intake-430).

### Three verified encoder/catalog defects that falsify any "drop-in" swap framing

Recorded because this page carries live swap candidates (LateOn A/B, the LFM2.5 bounded probe), and
all three defects sit exactly on that path:

- **The KB-RAG ColBERT encoder cannot load ANY BERT-family late-interaction ONNX.** Such graphs
  declare `token_type_ids` as a required input with no initializer default, and `colbert_encoder.py`
  feeds only `input_ids` + `attention_mask` → `InvalidArgument: Missing Input` on the first call.
  This blocks answerai-colbert-small-v1, ColBERTv2 and Jina-ColBERT-v2 **as a class**. The fix
  already exists in-repo: `cross_encoder.py` does graph-input introspection (~3 lines to port).
- **Hard-coded limits override the model's own declaration.** `_QUERY_MAX_TOKENS = 48` overruns two
  candidate models' declared query length of 32; `onnx_config.json` fields (`query_length`,
  `document_length`, `embedding_dim`, `uses_token_type_ids`, `do_query_expansion`) are not honored;
  and prefixes are read only from `config_sentence_transformers.json`, so repos that omit it get a
  silent fallback that can select prefix tokens absent from the model's vocabulary.
- **Encoder drift past the catalog is effectively unguarded.** `_warn_on_encoder_drift` compares
  only the `encoder_model_dir` *string* and only logs; a dimension mismatch surfaces as a numpy
  shape error inside `maxsim()` and is swallowed by a broad `except`. The non-vacuous verification,
  when the fix lands: point the index at a different-dim encoder and confirm it fails *loudly* — a
  test that passes both before and after the change proves nothing.

### K11 lexical sweep: a clean null — ColBERT-only remains the default on measurement, not assumption

The FTS5 lexical blend that landed default-off got its decision sweep (2026-07-21,
`BULK-kbrag-autowiki-k11`, protocol `internal-kb-rag.k11-lexical-sweep.v1`, verdict
`DONE_MARGINAL_OBS`):

| Lexical weight | mean recall@10 | missed-all-evidence |
|---|---|---|
| 0.0 / 0.1 / 0.2 / 0.3 | 0.5048 (identical across all four) | 14 (identical across all four) |

`n=70` over the **remapped** K7 certification pool against a fresh FTS5 catalog. Zero uplift at any
weight, so **no default lexical-weight promotion; `lexical_weight=0` (ColBERT-only) stays the
default** — the earlier "implemented default-off pending its own sweep" caveat on this page is now
resolved by measurement. The 0.5048 aggregate is **not comparable** to the 2026-06-13 certification
numbers (0.6167–0.6298): those ran the original pool against the certification-era index, and pool
identity travels with the number.

### The live index is ~56 % larger than its recorded figures

Measured 2026-08-21: **943 files / 28,110 chunks / 2,199.13 MiB**, versus the certification-era
record of 577 / 18,010 / 1,227.6 MiB that still headlines the handoff. The certified figures remain
correct as facts *about the certified build*; they are no longer descriptions of the live index, and
any per-corpus tuning derived from them (pool composition, latency expectations, recall baselines)
should be re-anchored before reuse.

### Code↔docs crossover federation landed — the gap this page's KB-RAG summary named is closed

The federation query shipped 2026-07-22: the GitNexus symbol/flow graph is federated with the
ColBERT KB index in both directions (symbol/file → related handoff/wiki chunks; doc-mention → code
symbols). This is additive — GitNexus stays the code-intelligence layer, KB-RAG stays the markdown
layer, and the federation is a join, not a replacement. Two operational findings from the landing:
the orchestrator's GitNexus index was corrupt (a `lbug.wal` without `lbug.shadow` segfaulted the CLI
on every read; re-indexing took 32.9 s for 52,993 nodes and reads clean since), and the federation
tool degrades gracefully by skipping an unreadable repo rather than failing the query; its ONNX
runtime discovery is env-overridable via `FEDERATION_ORT_SITE_PACKAGES` instead of a hard-coded venv
path.

### Source References

- [`internal-kb-rag.md`](../handoffs/active/internal-kb-rag.md) — the intake-1278 C1/C2 record
  corrections with their provenance chain and the 2026-08-22 two-harness tightening; the K1/K2/K3
  encoder-defect diagnoses; the K11 sweep result; the measured live-index figures; the 2026-07-22
  federation landing.
- [`colbert-zero-research-integration.md`](../handoffs/completed/colbert-zero-research-integration.md)
  — the completed handoff carrying the "answerai unscored" retirement rationale the correction
  targets; the record edit itself is still open work.
- [`CHANGELOG.md`](../CHANGELOG.md) — the second surface carrying the stale swap rationale, plus the
  original :8089 answerai deployment and GTE upgrade-candidate entries the correction reconciles.

---

## Compiled Update — 2026-08-23 (evening): the fallback slot re-pointed to mxbai 32M, a corrected CPU figure, and the encoder class fix

**Confidence: verified** — the slot re-point reads the vendor tech report and both checkpoints' model cards; the Table 13 correction re-derives from arXiv:2510.14880v1 Table 13; the K1 landing is the shipped `epyc-orchestrator` `4e5e84c0`.

### The fallback slot is mxbai-edge-colbert-v0-32M, not the 17M (re-pointed 2026-08-23)

The web_research reranker's FALLBACK slot moved from the 17M to the **32M** sibling: BEIR **0.521 vs 0.490**, NanoBEIR **0.6520 vs 0.6405**, dim **64 vs 48** — and the 17M is the base checkpoint of the derived Reason-mxbai-32m already wired into the three-slot selector. **The 17M's headline BEIR win over ColBERTv2 is 0.2 pp (0.490 vs 0.488) with significance testing explicitly declined in the tech report itself** — the 17M was never the size that mattered here. The slot is chosen on quality and dimension, not on licence (both Apache-2.0). ~3.2× faster CPU encoding than ColBERTv2 is the vendor's own single-harness claim, with its scope limits recorded (§3 of the handoff).

### The "~49 s per 50K docs" line was a misread — CORRECTED

The previous line ("~49s per 50K docs … vs ColBERTv2 ~154s") was Table 13's CPU column **divided by 10**, over a corpus misstated as 50K. Corrected: **487 s** whole-pipeline NanoBEIR runtime on an **unnamed CPU** (vs ColBERTv2 **1540 s**), mean of 10 runs over ~67,000 documents + 650 queries. The ~3.2× ratio survives; the absolute numbers did not. Two further limits on Table 13: the CPU is never named and no variance/min/max is reported; and the paper's stack is **PyLate/PyTorch — it never mentions ONNX** — so these figures are a within-stack ratio and are **not transferable to our ONNX-Runtime INT8 serving path**. Reranking 20 pre-encoded pages is still sub-ms MaxSim.

### G14 — the Reason-mxbai slot still lacks its `onnx_config.json` (environment-prerequisite-gated)

The staged Reason-mxbai artifact ships `config_sentence_transformers.json` but **no `onnx_config.json`** — the file the NextPlaid Rust reader requires and the one `colbert_encoder._load_declared_config()` now prefers. Re-export with `pylate-onnx-export` **1.7.0 from git** (`next-plaid#subdirectory=next-plaid-onnx/python` — not the model card's `onnx/python` path, which 404s at head and at `00e26aae`, and not PyPI 0.1.0, which on this 3-Dense checkpoint emits a **truncated graph with a mislabelled `embedding_dim`**). **The real blocker is an environment prerequisite, not compute** (one CPU trace of a 32M model — seconds): 1.7.0 declares `requires-python ">=3.10,<3.13"` and this host is Python 3.13.7, so a Python 3.10–3.12 venv must exist first. Pin a PyLate ceiling too (`query_prefix_id` gained a `None` return at 1.6.0 that `export.py:264-265`'s bare `int()` would crash on). The older cp314/`fast-plaid`/`voyager` objection is stale — none of them is imported on this path.

### The ColBERT encoder class fix landed (`epyc-orchestrator` `4e5e84c0`)

The encoder could not load ANY BERT-family late-interaction ONNX (required `token_type_ids` input with no initializer default) — unblocks answerai-colbert-small-v1, ColBERTv2 and Jina-ColBERT-v2 **as a class**, not one model; the mxbai family never needed it (declares `uses_token_type_ids: false`; its real blocker was `do_lower_case`, also closed in the same commit). Embedding-dim drift between a live encoder and a stored index now **raises** instead of surfacing as a swallowed numpy shape error inside `maxsim()`. The H4 file-selection rule travels with it: mirror's `model_int8.onnx`, else upstream's **root** `model_int8.onnx`; never `onnx/`, never `vespa_colbert.onnx` — picking by folder name builds a silently wrong index. (Full landing details: [Knowledge Management](knowledge-management.md).)

### Source References (2026-08-23 evening)

- [`colbert-reranker-web-research.md`](../handoffs/active/colbert-reranker-web-research.md) — the 32M re-point with the 0.2-pp significance caveat, the Table 13 correction, G14 with its venv prerequisite, the H4 file-selection rule
- [`internal-kb-rag.md`](../handoffs/active/internal-kb-rag.md) — the K1/K2/K3 landing (`4e5e84c0`) and the H5/H6 tokenizer-identity findings (cross-listed with [Knowledge Management](knowledge-management.md))

## Compiled Update — 2026-08-23: a guard that tested the wrong predicate, a published ceiling that was a truncation setting, and where our length exposure actually lives

**Confidence**: verified. Four provenance classes are kept distinct below and a reader should never
merge them: (a) **first-party measurements** on our own hardware, corpus and artifacts — the live
catalog counts, the on-disk `onnx_config.json` reads, the encoder mutation tests; (b)
**Stage-2b dive measurements**, our own instrumentation run against *published* third-party
artifacts (tokenizer round-trips, ONNX graph parsing, the 622-query TREC ToT tokenization) — these
are ours, but they measure someone else's object; (c) **third-party reported figures** (BEIR,
NanoBEIR, LongEmbed, the TREC track overview), which under [`MEASUREMENT.md`](../MEASUREMENT.md)
gate nothing here; and (d) **vendor claims with no attached method**, which are hypotheses. Where a
figure is arithmetic rather than measured, it says so.

### The ColBERT prefix guard tested vocabulary membership; the pipeline depends on encoding. Fixed in `4e5e84c0`

**A ColBERT prefix guard that asks `token_to_id(prefix) is not None` is interrogating the BASE
VOCABULARY, and that is the wrong object.** For a prefix like `[unused0]` — present by construction
in every BERT checkpoint — the answer is yes even on a tokenizer that never promoted the string into
`added_tokens`. `encode()` then emits `['[', 'unused', '##0', ']']` (ids `1031, 15171, 2692, 1033`)
where the model expects the single id `1`. **Only the added-token trie splits a literal before
WordPiece runs, and only ENCODING observes the trie**, so membership and encoding answer different
questions and the guard was asking the one that cannot fail. Executed against both real
`tokenizer.json` files (tokenizers 0.22.2, Stage-2b dive measurement,
[`intake-1293#record`](../research/intake_index.yaml)).

**The failure is reachable from published artifacts and it is silent.** Upstream
`answerdotai/answerai-colbert-small-v1` ships exactly the dangerous pairing: a PyLate-shaped ONNX
serving config beside a tokenizer carrying **5** added tokens (`[PAD] [UNK] [CLS] [SEP] [MASK]`),
not 7. LightOn's mirror `lightonai/answerai-colbert-small-v1-onnx` differs from it in **exactly two
`added_tokens` entries and nothing else** — `[unused0]` id 1 and `[unused1]` id 2, both
`normalized: true`, `special: false`, the fingerprint of a plain `add_tokens()` call; `version`,
`truncation`, `padding`, `normalizer`, `pre_tokenizer`, `post_processor`, `decoder` and the full
30,522-entry WordPiece vocab hash identical. The mirror does not *add* those ids — they already
exist in both base vocabularies — it **promotes** them into the trie. That distinction is the whole
defect. **Anyone who "fixes" the missing config by copying the mirror's config next to an
upstream-derived tokenizer builds a silently wrong index**: guard passes, index builds, vectors are
wrong, nothing raises.

**`[Q] ` / `[D] ` were never the dangerous case.** `token_to_id` returns `None` for them and the
loader correctly refuses. This **corrects the implication carried in the 2026-08-22 section above**,
which framed the fallback risk as "prefix tokens absent from the model's vocabulary" — that is the
*safe* branch. The dangerous configuration is a prefix **present in the vocabulary and absent from
`added_tokens`**.

**The fix is an encode round-trip.** `_prefix_encodes_to_one_token()` encodes the prefix and asserts
exactly one token, optionally matching the declared `query_prefix_id` / `document_prefix_id` so the
probe tests *identity* and not merely single-token-ness — a tokenizer can encode a prefix to one
token that is not the id the model was trained against. The probe clears padding and truncation
first, because `encode()` sets both globally on the shared tokenizer and a padded probe would return
`max_tokens` ids and reject every prefix. Verified by mutation test **with controls**: the old guard
**accepts** the unpromoted tokenizer the new guard **refuses**, on the real artifacts, so the change
is observable; a single-token prefix with the wrong declared id is also refused. Checked against the
deployed `gte-moderncolbert-v1-onnx` — old and new guards agree, declared ids 50368/50369 resolve,
`do_lower_case` is `False` — so **production behaviour is unchanged**. 206 unit tests pass across
retrieval / prefix_cache / cross_encoder. (`epyc-orchestrator` `4e5e84c0`.)

**The generalisable rule: a guard must exercise the operation it protects, not a proxy for it.** The
module docstring had stated the right invariant since it was written; the predicate testing it was
the wrong one, and no test could catch that because both the guard and its test asked the same wrong
question.

**Three of the defects recorded on this page 2026-08-22 moved in the same commit.** K1 — the encoder
could not load *any* BERT-family late-interaction ONNX — is **closed**: `ensure_loaded()` captures
`_input_names` from `session.get_inputs()` and `encode()` feeds exactly the declared inputs, with
all-zero `token_type_ids` for single-segment input; an input it cannot satisfy now **raises** instead
of degrading to an empty index. That unblocks answerai-colbert-small-v1, ColBERTv2 and
Jina-ColBERT-v2 **as a class**. K2 is **half-landed** (both config filenames are now read — see
below — but the declared `query_length` / `document_length` / `embedding_dim` are readable and not
yet acted on; both call sites still hard-code 48). K3 is **half-landed**: `embedding_dim` is stamped
into `index_meta` and a live encoder of differing width now raises, but the tokenizer hash is still
not stamped — and mxbai-32m and the deployed GTE share a byte-identical vocabulary while their
`tokenizer.json` files differ, so a swap in that direction is invisible to every key now stamped.
Two further riders in the same commit: the swallowed `encode()` failure moved from `logger.debug` to
`logger.warning` with the exception type (a model that cannot be encoded *at all* used to present as
an ordinary miss), and `do_lower_case` is now honoured — applied to the **text only**, never to the
prefix, which is a literal added token that would stop matching the trie if folded.

### A published "architectural ceiling" is a `query_maxlen = 32` configuration artefact

arXiv **2604.09982** ("Reproduction Beyond Benchmarks: ConstBERT and ColBERT-v2 Across Backends and
Query Distributions", SIGIR '26 Reproducibility Track, credibility 4 / High) attributes a
performance plateau at ~20 query words to **MaxSim's uniform token weighting** — "not a limitation
of the model, but a saturation of the scoring logic" (§5.4.4). **The dive overturns the mechanism
from the authors' own artifacts, not by argument** ([`intake-1294#record`](../research/intake_index.yaml)):

- **Their released results file is bit-identical across the swept conditions.**
  `results/15_query_length_ablation.json` records MRR@10 `0.04268042157913541`, Recall@1000
  `0.25884244372990356` and nDCG@10 `0.048217164333040616` **to 17 significant figures** across the
  40, 60, 80, 100 and 121-word conditions over 622 queries against a 6.4M-document corpus, while
  `actual_mean_length` moves from 39.89 to 101.20 words. If MaxSim were summing additional filler
  similarities the sums, and therefore the rankings, would move. They do not move at all — the
  encoder saw an identical token prefix.
- **Their own code sets the limit.** `experiments/run_ablation_colbert.py:58-59` hardcodes
  `query_maxlen: 32` / `doc_maxlen: 180`; the Table 7 script truncates by **words** and then hands
  the raw string to `encode_queries()`, so the ablation varied words in and never controlled tokens
  encoded. The official Stanford ColBERT default is `query_maxlen = 32`.
- **The paper says so once and then argues past it for nine pages.** "32-token" appears exactly once
  in the whole text — in the Introduction — and never again; the abstract, §5.4.3, §5.4.4 and the
  Conclusion all attribute the plateau to MaxSim instead.
- **Stage-2b measurement over the real corpus**: tokenizing all 622 official TREC ToT 2025 test
  queries with the real BERT WordPiece vocabulary, **622/622 (100.0%) exceed the 29-token content
  budget at L=40 words**, and the truncated prefix is **identical for 622/622** between L=40 and each
  of L=60, 80, 100 and 121 — robust across content budgets of 28–40 tokens. At 20 words only **2.9%**
  overflow, which is exactly why the curve peaks there and is flat forever after. **The median ToT
  query retains 12.5% of its tokens.** A scoring operator cannot be diluted by filler it was never
  shown.
- **The framing statistic is wrong in their own data.** "Median 121 words", stated **seven times** and
  the basis of the paper's "nearly 20× longer than MS-MARCO" framing, is **182** in their own results
  file (mean 171.8, max 959 words = 210.8 / 232 wordpieces), independently reconfirmed by measuring
  the dataset. The true ratio is ~30×, and the row labelled "121 words (full)" still truncates
  **62.06%** of queries.
- **The load-bearing quantity is never measured.** "Up to 70% of the tokens are filler" appears three
  times with no table, no method, no annotation protocol and no citation — and is internally
  inconsistent with the Conclusion's "60–70%".
- **Independent and adverse.** On the identical 622-query set and 6,407,814-article corpus, the TREC
  ToT 2025 track overview (arXiv 2601.20671) puts ColBERT-v2 zero-shot at nDCG@10 **0.0607**, *above*
  the coordinators' own dense baseline `lightning-ir-dense` at 0.0189 and inside the normal band for
  unadapted first-stage retrievers — not what a catastrophic architectural failure looks like. And
  another group tested the causal mechanism directly: `bm25_hedge_aware`, a BM25 variant built
  specifically for the hedging/filler language the paper blames, scores 0.1257 against plain
  `pyterrier-bm25` 0.1223 — **+2.8% relative, essentially nil**. Separately, 300 of the 622 test
  queries (48%) are LLM-generated synthetic, prompted to be deliberately hard and to include
  "plausible but incorrect details"; the paper never mentions the composition.

**The transferable rule, and the reason this is compiled here at all: a plateau across a swept
parameter is evidence that the parameter stopped reaching the model, before it is evidence of a
ceiling.** The cheapest possible check is whether the metric is *bit-identical* across conditions.
Identical to 17 significant figures is not a saturating curve; it is the same input. This is the same
class of error as the vacuous-verification family already catalogued in this repo — a measurement
whose independent variable never reached the system under test.

**What survives and should be carried forward**: the MS-MARCO reproduction (ConstBERT within 0.05%,
38.99% vs 39.04% MRR@10; ColBERT-v2 within 0.55%); the ConstBERT/PLAID **centroid-coverage** root
cause (12.1 of 32 unique centroids, 37.9%, over 5,000 sampled docs) — the paper's best contribution,
though it has **no surface in our stack**, because KB-RAG is a brute-force scan with no ANN stage;
the BEIR asymmetry (ColBERT-v2 reproduces within 1.4% across 13 datasets while ConstBERT does not),
which cuts *against* the paper's own thesis since MaxSim generalises across 13 domains without
difficulty; and the bare observation that unadapted multi-vector retrievers score 4–6% MRR@10 on ToT.
**Explicitly declined**: using this paper to explain why encoder swaps in this family land inside our
~2 pp noise floor. The 1.32 pp answerai-vs-GTE gap compiled in the 2026-08-22 section still needs a
different explanation.

Two ecosystem facts worth keeping, because they make the local sweep cheaper if we ever want it: the
32-token default is ecosystem-wide (Stanford ColBERT, PyLate, Lightning IR, WARP/XTR), and
practitioner awareness of the wall already exists in code — ColBERT PR 226 (merged 2023) added
`full_length_search` precisely because someone hit it, RAGatouille sizes `query_maxlen` dynamically,
and `jina-colbert-v1-en`'s card instructs `query_maxlen=128`.

### Our length exposure is document-side, not query-side

**The three reranker slots declare three different query lengths, and that by itself falsifies any
shared architectural ceiling.** Read first-party from each model directory on disk 2026-08-23:
LateOn **32** (`lateon-onnx-int8/onnx_config.json`), GTE-ModernColBERT-v1 **48**
(`gte-moderncolbert-v1-onnx/onnx_config.json`), Reason-mxbai-32m **256**. An **8× spread** across
slots means a declared query length is a per-checkpoint training parameter, not an architectural
constant. Both call sites hard-code 48 (`kb_rag.py:66`, `src/tools/web/colbert_reranker.py:66`), so
**LateOn is overrun by 16 tokens** while Reason-mxbai is under-used by 208. Provenance caveat: the
256 comes from `reason-mxbai-colbert-v0-32m-onnx-int8/config_sentence_transformers.json` — that
directory ships **no `onnx_config.json` at all**. Where a local shipped value disagrees with the
upstream card (the GTE checkpoint's local 48 against upstream's 32), **the local value is
authoritative**, because it is the file the loader actually reads.

**The query side is not where we are exposed.** Our 90 curated cases (70 certification + 20 seed) run
median ~23 tokens, max 33, with **0 of 90 reaching the 48-token cap**. But note the honest gap: **no
query-length instrumentation exists anywhere in the retrieval path**, so every statement about the
caps is inferred from that curated pool and never observed from live traffic. Any instrument added
must not be vacuous — `encode()` calls `enable_truncation(max_length=max_tokens)` and
`enable_padding(length=max_tokens)`, so a count taken from `encoded.ids` is *always* exactly
`max_tokens` and an over-cap rate computed that way reads 0% forever. The count must come from a
truncation-disabled tokenization, or the metric measures the cap instead of the query.

**The document side is where we are exposed, and it is large.** `markdown_chunker.py:25` sets
`DEFAULT_MAX_CHARS = 4000` while `kb_rag.py:67` sets `_DOC_MAX_TOKENS = 256` — roughly a
1,024-character budget — so a full-size chunk has about **75% of its content silently dropped at
embed time**. Measured first-party read-only against the live catalog
(`data/kb_rag/index-qd-v1/catalog.sqlite`) on 2026-08-23: **28,155 chunks over 944 files, mean
`token_count` 170.3, and 11,410 chunks = 40.5% sit at or above the 256-token cap.** (The catalog is
live and grows; a same-day re-read returned 28,235 / 947 / 11,466 = 40.6%, so treat the ratio, not
the absolute count, as the stable figure.)

**A hazard that must travel with those numbers: `catalog.token_count` is `emb.shape[0]` — it is
post-truncation and clips at exactly 256.** Confirmed on the live catalog (`max` = 256, `min` = 4).
It can report *that* a chunk was truncated and never *by how much*, so **character coverage cannot be
derived from it at all** and must be re-tokenised with truncation disabled. This also settles an
inverted pair in the record: the 60% / 43% figures the intake-1294 dive first recorded are the
complement of the correct ones; `intake-1278#record`'s 39.6% capped / 57.2% character coverage has
the right polarity. The phenomenon and its priority are unchanged — only the magnitude was
overstated.

Both remedies are compute-gated and both are filed on
[`internal-kb-rag.md`](../handoffs/active/internal-kb-rag.md): **G13** sweeps recall@10 on the K7
70-case pool at `_DOC_MAX_TOKENS` 256 vs 300 (the incumbent's declared `document_length`) vs a
chunker `max_chunk_chars` reduced to ~1,100, batched with a punctuation-skiplist arm because both
need one shared full-corpus re-embed — the gate opens on any arm beating the **0.5690** plain-MaxSim
baseline by >2 pp. **G12** adds a verbose/narrative arm (~20 cases, 60–150 words) to the K7 pool; a
verbose arm scoring >2 pp below the short arm would be the **first local evidence of query-length
sensitivity anywhere in this repo**.

### The ONNX export-and-contract layer: two config filenames with opposite required consumers

**`onnx_config.json` is the format's mandatory config, and it is the file we were not reading.** The
NextPlaid Rust reader hard-rejects its absence (`next-plaid-onnx/src/lib.rs:682-689`, `bail!` on
"this file is required for ColBERT model configuration"), and its format-reference defaults live
beside it at `:619-641` (`uses_token_type_ids` true, `query_prefix "[Q] "`, `query_length` 48,
`embedding_dim` 128). A current `pylate-onnx-export` writes **exactly four files** — `model.onnx`,
`model_int8.onnx`, `tokenizer.json`, `onnx_config.json` — and `export.py:268-270` **deliberately does
not** write `config_sentence_transformers.json`, which until `4e5e84c0` was the only file our loader
read. A freshly exported checkpoint therefore had no config file we would open. Closed in
`4e5e84c0`: `_load_declared_config()` reads both and merges them with the **format-mandated
`onnx_config.json` winning**.

**The two filenames are not interchangeable by convention — they have opposite required consumers.**
The Rust engine reads only `onnx_config.json` and errors without it; our loader read only
`config_sentence_transformers.json`. The LightOn mirror is usable by both **only because it ships
byte-identical copies of each** (same HF blobId, sha256 `dcce63ae…`), declaring `query_prefix
"[unused0]"`, `document_prefix "[unused1]"`, prefix ids 1/2, `uses_token_type_ids true`,
`embedding_dim 96`, `query_length 32`, `document_length 300`. Upstream ships only
`onnx_config.json` — the mirror's content minus the single key `do_lower_case` — which is "NextPlaid
compatible" and *not* compatible with our loader.

**The folder-name footgun: take the ROOT `model_int8.onnx`, never anything under `onnx/`, never
`vespa_colbert.onnx`.** Upstream `answerdotai/answerai-colbert-small-v1` @ `934fa8bb` holds **11 ONNX
files / 10 distinct blobs** — 3 at root (`model.onnx`, `model_int8.onnx`, `vespa_colbert.onnx`) and 8
under `onnx/`, where `onnx/model_int8.onnx` and `onnx/model_quantized.onnx` are the same blob.
Directly parsed: the `onnx/` family terminates at `last_hidden_state [batch, seq, 384]` — **no
ColBERT projection, no L2 normalisation** — and is ir_version 10 against the root's 7.
`vespa_colbert.onnx` names its output `contextual`, a third naming convention; only the root exports
and the mirror's end at `output`. **Picking by folder name builds a silently wrong index and raises
no error.** The mirror has no `onnx/` subdirectory, so it eliminates the footgun by construction.
This also corrects the standing record's counts, which said nine files / seven under `onnx/`.

**Install caveats, because the documented path is wrong in three ways.** `pip install
pylate-onnx-export` gets PyPI **0.1.0** — the only published release, and the broken one: it writes
`config_sentence_transformers.json` instead of `onnx_config.json` (the filename its own Rust consumer
rejects), takes the projection from `pylate_model[1].linear` while reading the output dimension from
`pylate_model[-1]` (a **truncated graph with a mislabelled `embedding_dim`** on any multi-Dense
checkpoint — ours is 3-Dense), and gates architecture on a `"ModernBert" in model_class_name` string
test. Install from git at `#subdirectory=next-plaid-onnx/python`; the model card's `onnx/python` path
404s at head and at the pinned rev. 1.7.0 declares `requires-python ">=3.10,<3.13"` and this host is
Python 3.13.7, so **a 3.10–3.12 venv is the real prerequisite, not compute**. Pin a PyLate ceiling as
well — `query_prefix_id` gained a `None` return at 1.6.0 that `export.py:264-265`'s bare `int()`
would crash on. **The older "PyLate needs cp314 / `fast-plaid` / `voyager`" objection on file is
stale**: `voyager` is an optional extra gated `python_version < 3.14`, `fast-plaid` ships cp310–cp314
manylinux wheels, `pylate/__init__.py` never imports `pylate/indexes/`, and our host is 3.13.7. The
constraint runs the other way.

**Static graph parity between the mirror and the upstream root INT8 export is as strong as a static
test can get, and it still is not numerical equality.** Stage-2b parsed both byte-level: identical
ir_version 7, single opset ai.onnx 14, identical 350-initializer **payload multiset with zero residue
either way**, 72 of 73 `MatMulInteger` nodes name-and-blob identical, identical projection weight
sha256 `fb035f59…` and scale `0.0006252911989577115`, identical L2 tail
`ReduceL2 → Clip(1e-12) → Expand → Div`. The entire 60,630-byte size delta is **252 constant-folded
shape-plumbing nodes plus one module rename** (`/projection_layers.0/` vs `/linear/`). That
establishes *same weights, same quantisation parameters, same semantics* and stops there:
`DynamicQuantizeLinear` derives activation scales at runtime and 252 fewer nodes change ORT's
execution plan and therefore FP accumulation order. **Any equivalence check must be cosine / max-abs
delta and never a byte hash** — a hash returns a false negative by construction. That is **G11**,
which also folds in the INT8-vs-fp32 arm; its gate is MaxSim top-1 agreement at the incumbent's 100%
with max abs Δ within the order of the **6.60e-03** already accepted. Measured compression on the
mirror: 133,253,426 → 33,888,020 B = **3.93×**.

**Never cite the vendor's ">0.99 cosine similarity preserved" or "1.5–2× speedup" figures as
evidence.** They are `quantize.py` docstring folklore with no model, no corpus, no `n` and no method
anywhere in either repo. Under [`MEASUREMENT.md`](../MEASUREMENT.md) they are hypotheses to test, not
baselines — which is exactly what G11 is for.

### mxbai-edge-colbert: the fallback slot re-pointed to the 32M, and two figures on this page are wrong

**The S5 fallback slot moved from mxbai-edge-colbert 17M to the 32M on 2026-08-23.** On the vendor's
own full-BEIR table the 32M beats the 17M **0.521 vs 0.490**, on NanoBEIR **0.6520 vs 0.6405**, and
it carries dim **64 vs 48**; it is also the base checkpoint of the Reason-mxbai-32m already wired
into the three-slot selector. The 17M's headline "beats ColBERTv2" result is a **0.2 pp** BEIR margin
(0.490 vs 0.488) with **significance testing explicitly declined** in the tech report itself, so the
17M was never the size that mattered here.

**Correction to this page's own §Summary — the 2026-04-14 literature-survey paragraph reads
"mxbai-edge-colbert encodes 50K docs in ~49s vs ColBERTv2 ~154s". That is wrong by 10× and misstates
the corpus.** The source
figures are Table 13's CPU column — **487 s vs 1540 s**, mean of 10 runs over **~67,000 documents +
650 queries** — and the numbers on file are that column divided by ten. The ~3.2× *ratio* survives;
the absolute numbers do not. Three further limits belong with them: the CPU is never named, no
variance/min/max is reported for any of the ten runs, and the paper's stack is **PyLate/PyTorch — it
never mentions ONNX** — so these are a within-stack ratio and do not transfer to our
ONNX-Runtime INT8 serving path. Table 13's `Mem.` column is likewise **arithmetic, not measurement**:
it is the closed form `10,000 × 300 × dim × 2 bytes` in MiB, exact on all rows, carrying zero
information beyond the `dim` column.

**Corroborating the "two harnesses, not three" tightening compiled 2026-08-22**: mixedbread did not
run answerai-colbert-small-v1 or GTE-ModernColBERT-v1 on BEIR at all. All 15 per-task scores in their
answerai row match LightOn's *re-run* column 15/15 under 3-dp rounding and the vendor-reported row
**0/15**, and the GTE row matches LightOn's card 15/15 — published 36 days before submission, with no
attribution footnote (Table 12 does footnote its transcribed rows). Authorship is non-independent on
the same axis: Benjamin Clavié, author of answerai-colbert-small-v1, is the paper's second author.
Table 12 (LongEmbed) and Table 13 (NanoBEIR) **are** mixedbread's own runs — and LongEmbed is the
paper's most defensible result: mxbai-32m (32k) 0.849 and 17m 0.847 against answerai 0.441 and
ColBERTv2 0.428, a ~40 pp gap driven entirely by the 512-token positional ceiling of the BERT-family
baselines (GTE-ModernColBERT-v1 leads at 0.898).

**The projection-dimension curve does not answer the question it looks like it answers.** Table 8
sweeps 96 → 0.5991, 64 → 0.5985, 48 → 0.5967, 32 → 0.5772, 24 → 0.5423, 16 → 0.5126 — flat from 96 to
48, cliff at 32 and below. But **128 is not in the sweep**, so it is silent on the 96-vs-128 step our
incumbent actually occupies; it is a **re-training ablation, not post-hoc reduction**, so it does not
license truncating or PCA-ing an existing checkpoint's vectors; and it uses 20% of the training data
on 5 NanoBEIR subsets, not full BEIR.

**Index-footprint projection, flagged as a projection.** mxbai-edge-colbert-v0-32m and the deployed
GTE-ModernColBERT-v1 share a **byte-identical 50,280-token vocabulary** (verified first-party
2026-08-23: the two `tokenizer.json` files differ only in a pre-baked truncation/padding block, and
their `model.vocab` maps are equal with zero differing entries). Because there is no tokenizer
correction factor, the footprint ratio is the bare dim ratio **64/128 = 0.500×**, projecting the
2,199 MiB live index to **~1,100 MiB** — roughly double the 0.757× / −534 MiB *measured* for answerai
at dim 96. **This is arithmetic, not a measurement.** Two conditions on any adoption note: pin the
ONNX revision at **≥ `963e23afa147`** (2026-04-15), because the 2026-02-14 ColGREP export omitted the
Dense projection layers and emitted the wrong output dimension — any copy pulled inside that 60-day
window is silently broken; and the one open variable is the lower-casing effect on token counts
(`do_lower_case: true` on mxbai, `false` on the incumbent), a pure-tokenizer measurement needing no
model. Note also that **K1 was never a gate on the mxbai family** — both configs declare
`uses_token_type_ids: false` and the graph contains zero `token_type` strings. That family's real
blocker was `do_lower_case`, unhandled and silent, also closed in `4e5e84c0`.

### Source References

- [`epyc-orchestrator` `4e5e84c0`](/mnt/raid0/llm/epyc-orchestrator) — "ColBERT encoder: fix a silent
  prefix-corruption path, unblock BERT-family graphs". The encode-round-trip prefix guard
  (`_prefix_encodes_to_one_token`), graph-declared input feeding via `session.get_inputs()`,
  `onnx_config.json` preference in `_load_declared_config()`, `do_lower_case`, the debug→warning
  raise, and the `embedding_dim` stamp/refuse. Touches `src/retrieval/colbert_encoder.py` and
  `src/retrieval/kb_rag.py` only; the mutation checks are recorded in the commit message and are not
  yet regression-guarded in `tests/`.
- [`internal-kb-rag.md`](../handoffs/active/internal-kb-rag.md) §Research Intake Update 2026-08-23 —
  K1 landed / K2 and K3 half-landed with their re-resolved line hints; H1 (the first-party live-catalog
  doc-truncation measurement and the `token_count` clipping hazard); H2 (no query-length
  instrumentation, and why a naive instrument would be vacuous); H3 (the three-slot query_length
  spread read from disk); H4 (the ONNX file-selection rule); H5/H6 (mxbai `do_lower_case`, tokenizer
  identity, the 0.500× footprint projection); G11/G12/G13 and B6.
- [`colbert-reranker-web-research.md`](../handoffs/active/colbert-reranker-web-research.md) — the
  fallback slot re-pointed from the 17M to the 32M; the corrected Table 13 CPU figures; G14, the
  gated `pylate-onnx-export` 1.7.0 re-export that would finally give the Reason-mxbai slot an
  `onnx_config.json`.
- [intake-1293](https://huggingface.co/lightonai/answerai-colbert-small-v1-onnx) `#record` —
  answerai-colbert-small-v1-onnx mirror + `pylate-onnx-export`. The executed `token_to_id`/`encode`
  divergence, the two-entry `added_tokens` diff, the byte-identical config pair, the 11-file /
  10-blob upstream inventory and the truncated `onnx/` family, the Rust reader's mandatory-config
  bail, the exporter's four-file output, the PyPI 0.1.0 defects and the Python ceiling, and the
  static INT8 graph parity. Credibility scores 1/Low on the two *vendor claims*; the artifact facts
  above were measured in-dive and carry no such discount.
- [intake-1294](https://arxiv.org/abs/2604.09982) `#record` — "Reproduction Beyond Benchmarks:
  ConstBERT and ColBERT-v2 Across Backends and Query Distributions" (SIGIR '26 Reproducibility
  Track). The `query_maxlen = 32` truncation artefact behind the claimed MaxSim ceiling, the
  bit-identical results file, the 622-query tokenization, the median-121-vs-182 error, the
  never-measured 70%-filler quantity, the TREC ToT track-overview and `bm25_hedge_aware` counter-
  evidence, and what survives (MS-MARCO reproduction, centroid coverage, BEIR asymmetry).
- [intake-1289](https://arxiv.org/abs/2510.14880) `#record` — "Fantastic (small) Retrievers and How
  to Train Them: mxbai-edge-colbert-v0 Tech Report". The projection-dim curve and its scope limits,
  the single-harness Table 13 and its analytic `Mem.` column, the LongEmbed gap, the BEIR
  transcription/attribution finding, and the 32M-vs-17M fallback re-point.
- [`MEASUREMENT.md`](../MEASUREMENT.md) — why every third-party figure above is an observation and
  none of them gates a stack change; the G11/G12/G13 gates are the first-party replacements.

- [intake-1289](https://arxiv.org/abs/2510.14880) Fantastic (small) Retrievers and How to Train Them: mxbai-edge-colbert-v0 Tech Report -- projection-dim sweep (96→0.5991 … 16→0.5126, 128 not swept, re-training ablation only), single-harness NanoBEIR Table 13 with its analytic `Mem.` column and unnamed CPU, LongEmbed ~40 pp gap over BERT-family baselines, and the finding that its BEIR answerai/GTE rows are transcribed from LightOn's model card rather than run. Basis for re-pointing the S5 fallback slot from the 17M to the 32M.
- [intake-1293](https://huggingface.co/lightonai/answerai-colbert-small-v1-onnx) answerai-colbert-small-v1-onnx mirror + `pylate-onnx-export` -- the ONNX export-and-contract layer. `onnx_config.json` is the format's mandatory config (the NextPlaid Rust reader bails without it) while `config_sentence_transformers.json` was the only file our loader read; the two-entry `added_tokens` diff behind the silent prefix-corruption case; the root-vs-`onnx/`-vs-`vespa_colbert.onnx` file-selection footgun (11 files / 10 distinct blobs upstream); static INT8 graph parity that is NOT numerical equality.
- [intake-1294](https://arxiv.org/abs/2604.09982) Reproduction Beyond Benchmarks: ConstBERT and ColBERT-v2 Across Backends and Query Distributions -- SIGIR '26 Reproducibility Track. Its "MaxSim architectural ceiling at 20 words" is a `query_maxlen = 32` truncation artefact (authors' own results file bit-identical to 17 significant figures across the 40/60/80/100/121-word conditions; 622/622 ToT queries identical past 40 words; median query retains 12.5% of its tokens). Sound and reusable: MS-MARCO reproduction, ConstBERT/PLAID centroid-coverage root cause, BEIR asymmetry.
- [`epyc-orchestrator` `4e5e84c0`](/mnt/raid0/llm/epyc-orchestrator) ColBERT encoder fix (2026-08-23) -- encode-round-trip prefix guard replacing the base-vocab `token_to_id` predicate, graph-declared ONNX inputs, `onnx_config.json` preference, `do_lower_case`, debug→warning on encode failure, and the `embedding_dim` index stamp that now refuses a mismatched encoder.
