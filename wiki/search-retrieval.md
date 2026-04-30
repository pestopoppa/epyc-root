# Search & Retrieval

**Category**: `search_retrieval`
**Confidence**: verified
**Last compiled**: 2026-04-28
**Sources**: 25 documents (added intake-428/430/431 LightOn DenseOn/LateOn)

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
- SearXNG (intake-359/360) **implemented and tested** as DDG HTML scraping replacement: `_search_searxng()` in `search.py` calls self-hosted JSON API on port 8090. Docker ~183MB + Granian ASGI. Default-on via `ORCHESTRATOR_SEARXNG_DEFAULT=1`, DDG fallback automatic. JSON response provides multi-engine provenance (`engines[]`, `positions[]`, `score`). Test results: 650-910ms latency, 3-engine consensus score ~9.9, 2-engine ~3.3, single <1. Google inactive (TLS fingerprint blocking). Engine tuning: DDG 1.2, Brave 1.1, Wikipedia 1.0, Qwant 0.9. `unresponsive_engines[]` + `search_backend` field wired into S1 relevance telemetry for AR-3 Phase 6b analysis [searxng-search-backend.md]
- mcp-searxng (intake-361, 635 stars, MIT) provides MCP bridge for SearXNG with `searxng_web_search` + `web_url_read` tools. Alternative integration path for Claude Code sessions [searxng-search-backend.md]
- **XTR (token retrieval) vs ColBERT (late interaction) is the fundamental architectural fork in multi-vector retrieval.** XTR (intake-407, Google DeepMind, arXiv:2304.01982) scores documents from a *subset* of retrieved tokens rather than all tokens, claiming 100–1000x cheaper inference at a meaningful accuracy cost. ColBERT scores using all token interactions (MaxSim over the full matrix). The Witchcraft real-world deployment confirms the trade-off: XTR achieves 33% NDCG@10 on NFCorpus vs ColBERT-Zero's 55.43 BEIR average — a ~22pp accuracy gap that validates the ColBERT choice for the 10-snippet reranking use case. [confidence: verified — intake-407/405, colbert-reranker-web-research.md 2026-04-17 section]
- **Witchcraft (intake-405) packages XTR-Warp as a zero-dependency embedded search engine** — a single Rust binary with GGUF-quantized T5 via the `candle` inference framework, hybrid BM25+semantic search, and SQLite FTS persistence. Reported p95 latency of 21ms (M2 Max), 2x faster than original XTR-WARP. The embedded/serverless deployment model (no separate server process, no network hop) is architecturally distinct from both NextPLAID containers and the ONNX reranker pipeline, and is interesting for session-local or offline document indexing use cases — not competitive with ColBERT-family for pipeline reranking accuracy. [confidence: verified — intake-405, colbert-reranker-web-research.md 2026-04-17 section]
- **WARP (intake-406, SIGIR'25, arXiv:2501.17788) achieves 3x speedup over ColBERTv2/PLAID and 41x over the XTR reference implementation** via two techniques: WARP_SELECT (dynamic similarity imputation that skips full MaxSim for low-scoring candidates) and implicit decompression (avoids materializing full PQ vectors during scoring). These are corpus-scale optimizations (millions of passages); for snippet-level reranking over 10 items, MaxSim already completes in <1ms so WARP's gains are immaterial to the current pipeline. Relevant if retrieval ever scales to large passage corpora. [confidence: verified — intake-406, colbert-reranker-web-research.md 2026-04-17 section]
- Crawl4AI (intake-372, 51K+ stars, Apache-2.0) is the preferred deep page scraping tool under the open-source-only policy. Async Playwright-based, local LLM extraction via Ollama, Docker deployment, no API keys. Complements SearXNG (search aggregation) with page content extraction for JS-heavy pages and PDFs. Evaluation gated on post-AR-3 WebFetch failure rate data [searxng-search-backend.md]
- Firecrawl (intake-364/365, 108K+ stars, AGPL-3.0) evaluation deferred: cloud-first SaaS model conflicts with self-hosted infrastructure philosophy. Self-hosted version lacks cloud parity. Credit-based pricing unpredictable [searxng-search-backend.md]

## Actionable for EPYC

- **GTE-ModernColBERT-v1 is deployed**: Docs container swapped, reindexed (1992 chunks, 246s), model_registry.yaml and orchestrator_stack.py updated. Production-ready.
- **MemRL distillation A/B test**: All infrastructure ready (classifier, training scripts, test harness). Needs a live seeding window to collect fresh routing data for comparison.
- **ColBERT reranker for web_research (S1-S4 complete, S5 gated)**: Relevance instrumentation (S1), feature flag (S2), ONNX model pipeline (S3), and latency benchmark (S4) are all done. S5 (implementation in `research.py`) depends on post-AR-3 analysis confirming >20% irrelevant page rate. Run `analyze_web_research_baseline.py` after AR-3 for go/no-go decision.
- **ONNX Runtime replaces PyLate**: The existing GTE-ModernColBERT-v1 on disk (`model_int8.onnx`, 144MB) with `onnxruntime==1.24.4` provides identical encoding capability without PyTorch dependency. ColBERT-Zero download deferred unless accuracy issues arise in S6 A/B testing.
- **qmd hybrid search evaluation**: intake-270 marked adopt_component -- evaluate for markdown knowledge base search in the project wiki or handoff system.
- **MemPalace patterns**: intake-326 achieves 96.6% recall on LongMemEval. Investigate architecture patterns that could improve MemRL episodic retrieval quality.
- **SearXNG search backend (SX-1–4 done, SX-5/6 AR-3-gated, R&O P12)**: Container deployed on port 8090, `_search_searxng()` implemented, engine weights tuned, telemetry wired. Default-on. SX-5 (load test) and SX-6 (swap confirmation) folded into AR-3 Package D Phase 6b — post-AR-3 analysis compares engine failure rate, irrelevant page rate delta, and latency overhead vs DDG baseline.
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

- One Rust binary (80 MB at `/mnt/raid0/llm/UTILS/bin/colgrep`) replaces one Docker container (~31 GB resident). Single-binary deployment removes the `orchestrator_stack.py` Docker entry for `nextplaid-code` after soak.
- Subprocess-per-query: every `_code_search()` call pays full ONNX runtime + ColBERT model load (~770 ms p50, up to ~2.3 s on first invocation). Acceptable for human-paced REPL; daemon options (homegrown sidecar vs upstream `next-plaid-client[cli]` SDK) documented in handoff S7 with concrete build-trigger criteria.
- `REPL_COLGREP_ALPHA=0.95` (overridable). Default 0.75 over-ranks `__init__.py` re-exports for symbol queries in this corpus; 0.95 weights ColBERT semantic over FTS5 keyword and recovers correct top-1 on validated cases.
- Hybrid scoring quirk: ColGREP returns FTS5+ColBERT fused scores in ~1–5 range, not NextPLAID's normalized 0–1. Frecency boost (0.3 × score multiplier) is rank-stable but downstream code that assumes 0–1 scale would need normalization.

**Soak gate**: NextPLAID code container kept running for one rollout window. `_exploration_log` records `engine: colgrep` per query; missing field signals fallback. If clean for ~1 week of normal traffic, retire the Docker container (free ~31 GB RAM). Apples-to-apples comparison (NextPLAID re-indexed on `src/` only) deferred — fairness exercise, not a production blocker.

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
- **Recommended deployment path on EPYC**: GGUF + `llama-embedding` HTTP server on port `:8096` (matches existing BGE-large `:8090–:8095` pattern). The OpenVINO/sentence-transformers route requires cp312/cp313 venv (orchestrator currently cp314).

### Bench plan (handoff-driven)

`handoffs/active/granite-97m-r2-bench-plan.md` (gated on K2 chunker activation in `internal-kb-rag.md`):

- **Phase A (2-3 inference-free engineering days)**: GGUF Q8_0 + Q4_K_M quantization; deploy on `:8096`; parallel-deploy multilingual-e5-base on `:8097`, BGE-M3 dense on `:8098`; build minimal eval corpus (cheapest fallback: 100 code snippets from `epyc-orchestrator/src/` + 30 NL queries with manual labels, ~half day; alternative: K2 chunker output on a slice of `/workspace/handoffs/active/*.md` + `/workspace/CLAUDE.md`).
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
- [`handoffs/active/granite-97m-r2-bench-plan.md`](../handoffs/active/granite-97m-r2-bench-plan.md) — claim-ready bench plan
