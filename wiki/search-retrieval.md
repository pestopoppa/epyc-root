# Search & Retrieval

**Category**: `search_retrieval`
**Confidence**: verified
**Last compiled**: 2026-04-14
**Sources**: 19 documents

## Summary

The EPYC stack uses ColBERT-based multi-vector retrieval for both codebase search and document search, with a separate BGE-large single-vector system for routing memory (MemRL episodic store). The retrieval architecture has been actively upgraded through the ColBERT-Zero research integration, which replaced the docs model with GTE-ModernColBERT-v1 and designed a MemRL distillation pipeline inspired by ColBERT-Zero's 3-stage training methodology. A handoff ready for implementation adds ColBERT-Zero snippet reranking to the web_research pipeline (pre-fetch filtering via PyLate MaxSim scoring).

The codebase retrieval system (NextPLAID) uses two ColBERT models: LateOn-Code (code search, port 8088) and GTE-ModernColBERT-v1 (docs search, port 8089, upgraded from answerai-colbert-small-v1-onnx). Both use 128-dim multi-vector representations with MaxSim scoring and PLAID PQ compression at nbits=4 (IVF+PQ hybrid). The code index is 336MB, docs index 31MB. These complement the MemRL episodic store which uses BGE-large 1024-dim single-vector embeddings with FAISS IndexFlatIP for routing memory retrieval.

The GTE-ModernColBERT-v1 upgrade (Track 1 of ColBERT-Zero integration) produced significant quality improvements: 5 of 10 test queries returned better results, 4 were equivalent, and none were worse. Particularly notable improvements appeared for queries about speculative decoding and REPL environment tools, where the old model returned unrelated files but the new model returned exact chapter matches. Latency increased from 28ms to 50ms (+78%), within acceptable bounds. The model uses `[Q]`/`[D]` prefixes read automatically from `onnx_config.json`, with a 768-dim hidden size projected to 128-dim via Dense layer.

Track 2 (MemRL distillation) designed a compressed routing classifier following ColBERT-Zero's insight that supervised fine-tuning before distillation is critical. The 3-stage pipeline maps to EPYC's context: (1) unsupervised contrastive learning on episodic store embeddings, (2) supervised training on (task, best_action) pairs weighted by Q-value, (3) distillation of HybridRouter decisions into a small classifier. The prototype classifier, training scripts, and A/B test harness are all implemented. The classifier integrates into HybridRouter as a fast first-pass, falling back to full retrieval when confidence is below 0.6.

The ColBERT reranker handoff (finalized 2026-04-14, ready for implementation) adds snippet-level pre-fetch reranking to the web_research pipeline. The implementation uses GTE-ModernColBERT-v1 (already deployed, BEIR 54.67) via ONNX Runtime rather than the originally planned PyLate library, which was eliminated because `fast-plaid` and `voyager` dependencies lack cp314 wheels for the orchestrator's Python 3.14 venv. The ONNX pipeline -- `onnxruntime` + `tokenizers` (both already in venv) loading `model_int8.onnx` (144MB INT8) -- produces per-token 128-dim embeddings with MaxSim scoring in numpy, totaling ~15 lines of code. Actual benchmarks on EPYC (S4, 2026-04-14) measured 180ms median encoding for 1 query + 10 snippets through the full 150M-param model, with <1ms for MaxSim scoring. While above the original <10ms target (which assumed pre-encoded embeddings), the ROI is ~750x since each irrelevant page saved eliminates 45s of worker synthesis. Ranking quality showed perfect separation on test data: relevant snippets scored 0.93-0.96, irrelevant scored 0.91-0.92. ColBERT-Zero (BEIR 55.43, <1pp better) download deferred unless accuracy issues emerge. Fallback model: mxbai-edge-colbert 17M (Apache 2.0, 6x smaller). S1 (relevance instrumentation) and S2 (feature flag registration) are complete; S1 instruments `_web_research_impl()` with `_is_irrelevant_synthesis()` heuristic and returns `pages_irrelevant`/`irrelevant_rate` in responses. Telemetry pipeline wired through `repl_executor.py`, `chat_delegation.py`, `WebResearchTelemetry`, and `analyze_web_research_baseline.py`. Data collection folded into AR-3 Package D. S5 (implementation) gated on post-AR-3 analysis confirming >20% irrelevant page rate.

A comprehensive literature survey (2026-04-14) confirmed the architecture decisions. Reason-ModernColBERT was eliminated due to CC-BY-NC-4.0 license despite strong BRIGHT performance (22.62/30.28 NDCG@10). Jina-ColBERT-v2 (89-language multilingual, Matryoshka dims) was deemed unnecessary as no multilingual requirement exists. The production consensus in 2026 is hybrid retrieval (BM25 + dense) → rerank top-20-30 → LLM, with cross-encoders on full index causing p99 blowup. Late-interaction (ColBERT-style) on small candidate sets is the established sweet spot. CPU feasibility is confirmed via proxy data: TurkColBERT achieves 0.54ms query latency under MUVERA indexing, and mxbai-edge-colbert encodes 50K docs in ~49s vs ColBERTv2 ~154s. For reranking 10 snippets, MaxSim over pre-computed embeddings is trivially fast on 192-thread EPYC.

A local hybrid search engine for markdown knowledge bases (intake-270, tobi/qmd) was marked as adopt_component with high relevance. MemPalace (intake-326, 96.6% LongMemEval recall) and LLM Wiki (intake-268, persistent LLM-compiled knowledge bases) were also flagged as relevant patterns.

A research intake deep-dive (2026-04-14) evaluated SearXNG (intake-359/360, 28.3k GitHub stars, AGPL-3.0) as a replacement for the current DDG HTML scraping + Brave fallback in `search.py`. The current `_search_duckduckgo()` function is 112 lines of fragile regex HTML parsing using subprocess curl, subject to bot detection and layout changes. SearXNG provides a self-hosted JSON API (`GET /search?q=...&format=json`) aggregating 250+ search engines with structured results including multi-engine provenance (`engines[]`, `positions[]`, `score` fields). Result merging is built-in -- when multiple engines return the same URL, they're merged with boosted score. The deployment is a Docker container (~183MB) with Granian ASGI server and optional Valkey sidecar for rate limiting. Critical caveats: (1) the limiter's API_MAX=4 requests/hour for JSON format blocks all programmatic use -- must be disabled for backend use, (2) bot detection blocks python-requests/curl user-agents when limiter is enabled, (3) JSON format is NOT enabled by default -- requires adding `json` to `search.formats` in settings.yml, (4) Google actively blocks SearXNG via TLS/HTTP2 fingerprinting, making it unreliable as an engine. Per-engine configuration supports weight multipliers, timeouts, retry policies, and proxy chains, allowing fine-tuning of individual engines. The `unresponsive_engines[]` field in JSON responses reports which engines failed per query, providing a monitoring signal without checking container logs. The SearXNG backend composes naturally with the ColBERT reranker S5: SearXNG returns top-N snippets via JSON, ColBERT reranks by MaxSim, top-3 get fetched and synthesized. An MCP server for SearXNG (intake-361, mcp-searxng, 635 stars, MIT) provides an alternative integration path for Claude Code sessions. Work items SX-1 through SX-6 are tracked in routing-and-optimization-index P12.

## Key Findings

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
- SearXNG (intake-359/360) evaluated as DDG HTML scraping replacement: self-hosted JSON API aggregating 250+ engines. Docker ~183MB + Granian ASGI. JSON response provides multi-engine provenance (`engines[]`, `positions[]`, `score`). Limiter API_MAX=4/hr MUST be disabled for backend use. Google engine unreliable (TLS fingerprint blocking). Per-engine weight/timeout/retry tuning available. `unresponsive_engines[]` provides upstream failure monitoring [searxng-search-backend.md]
- mcp-searxng (intake-361, 635 stars, MIT) provides MCP bridge for SearXNG with `searxng_web_search` + `web_url_read` tools. Alternative integration path for Claude Code sessions [searxng-search-backend.md]

## Actionable for EPYC

- **GTE-ModernColBERT-v1 is deployed**: Docs container swapped, reindexed (1992 chunks, 246s), model_registry.yaml and orchestrator_stack.py updated. Production-ready.
- **MemRL distillation A/B test**: All infrastructure ready (classifier, training scripts, test harness). Needs a live seeding window to collect fresh routing data for comparison.
- **ColBERT reranker for web_research (S1-S4 complete, S5 gated)**: Relevance instrumentation (S1), feature flag (S2), ONNX model pipeline (S3), and latency benchmark (S4) are all done. S5 (implementation in `research.py`) depends on post-AR-3 analysis confirming >20% irrelevant page rate. Run `analyze_web_research_baseline.py` after AR-3 for go/no-go decision.
- **ONNX Runtime replaces PyLate**: The existing GTE-ModernColBERT-v1 on disk (`model_int8.onnx`, 144MB) with `onnxruntime==1.24.4` provides identical encoding capability without PyTorch dependency. ColBERT-Zero download deferred unless accuracy issues arise in S6 A/B testing.
- **qmd hybrid search evaluation**: intake-270 marked adopt_component -- evaluate for markdown knowledge base search in the project wiki or handoff system.
- **MemPalace patterns**: intake-326 achieves 96.6% recall on LongMemEval. Investigate architecture patterns that could improve MemRL episodic retrieval quality.
- **SearXNG search backend (SX-1–SX-6, R&O P12)**: Deploy SearXNG Docker container on port 8090 with `limiter: false` and `search.formats: [html, json]`. Replace 112-line `_search_duckduckgo()` regex parser with ~15-line JSON API call. Tune engine weights (favor DDG/Brave/Wikipedia/Qwant, disable Google). Wire `unresponsive_engines[]` telemetry. Load test under EPYC query volume. Composes with ColBERT reranker S5.

## Open Questions

- What is the actual page contribution rate in current web_research sessions? (S1 instrumentation now live; AR-3 Package D will generate this data automatically via 50 web_research sentinel questions)
- Can the MemRL distillation classifier match HybridRouter quality on high-confidence decisions in production?
- Would ColBERT-Zero's general retrieval quality improve web_research synthesis measurably over DDG's keyword ranking? (GTE-ModernColBERT-v1 showed perfect separation on test data; real-world validation in S6 A/B test)
- Is the 50ms GTE-ModernColBERT latency acceptable under high-concurrency scenarios?
- Should the routing classifier's confidence threshold (0.6) be tuned via the conformal calibration system?

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
