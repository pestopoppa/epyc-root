# Search & Retrieval

**Category**: `search_retrieval`
**Confidence**: verified
**Last compiled**: 2026-04-13
**Sources**: 14 documents

## Summary

The EPYC stack uses ColBERT-based multi-vector retrieval for both codebase search and document search, with a separate BGE-large single-vector system for routing memory (MemRL episodic store). The retrieval architecture has been actively upgraded through the ColBERT-Zero research integration, which replaced the docs model with GTE-ModernColBERT-v1 and designed a MemRL distillation pipeline inspired by ColBERT-Zero's 3-stage training methodology. A stub handoff exists for adding ColBERT reranking to the web_research pipeline.

The codebase retrieval system (NextPLAID) uses two ColBERT models: LateOn-Code (code search, port 8088) and GTE-ModernColBERT-v1 (docs search, port 8089, upgraded from answerai-colbert-small-v1-onnx). Both use 128-dim multi-vector representations with MaxSim scoring and PLAID PQ compression at nbits=4 (IVF+PQ hybrid). The code index is 336MB, docs index 31MB. These complement the MemRL episodic store which uses BGE-large 1024-dim single-vector embeddings with FAISS IndexFlatIP for routing memory retrieval.

The GTE-ModernColBERT-v1 upgrade (Track 1 of ColBERT-Zero integration) produced significant quality improvements: 5 of 10 test queries returned better results, 4 were equivalent, and none were worse. Particularly notable improvements appeared for queries about speculative decoding and REPL environment tools, where the old model returned unrelated files but the new model returned exact chapter matches. Latency increased from 28ms to 50ms (+78%), within acceptable bounds. The model uses `[Q]`/`[D]` prefixes read automatically from `onnx_config.json`, with a 768-dim hidden size projected to 128-dim via Dense layer.

Track 2 (MemRL distillation) designed a compressed routing classifier following ColBERT-Zero's insight that supervised fine-tuning before distillation is critical. The 3-stage pipeline maps to EPYC's context: (1) unsupervised contrastive learning on episodic store embeddings, (2) supervised training on (task, best_action) pairs weighted by Q-value, (3) distillation of HybridRouter decisions into a small classifier. The prototype classifier, training scripts, and A/B test harness are all implemented. The classifier integrates into HybridRouter as a fast first-pass, falling back to full retrieval when confidence is below 0.6.

The ColBERT reranker handoff proposes adding Reason-ModernColBERT (150M params, 128-dim multi-vector) between DuckDuckGo fetch and the explore worker in the web_research pipeline. The reranker runs in ~5ms on CPU for 10-20 pages and does not compete for llama-server inference slots. Its late-interaction advantage is strongest on reasoning-heavy queries (Biology +7, Earth Science +9.6 NDCG@10 vs dense). The handoff is currently a stub awaiting validation that >30% of fetched pages are discarded in current web_research sessions.

A local hybrid search engine for markdown knowledge bases (intake-270, tobi/qmd) was marked as adopt_component with high relevance. MemPalace (intake-326, 96.6% LongMemEval recall) and LLM Wiki (intake-268, persistent LLM-compiled knowledge bases) were also flagged as relevant patterns.

## Key Findings

- Two distinct retrieval systems: ColBERT 128-dim multi-vector (codebase/docs) vs BGE-large 1024-dim single-vector (MemRL routing memory). Complementary, not competing [Ch.07 MemRL]
- GTE-ModernColBERT-v1 upgrade: 5/10 queries better, 4 same, 0 worse. Latency 28ms -> 50ms (+78%). BEIR avg 54.67, LongEmbed SOTA 88.39 [colbert-zero-research-integration.md]
- PLAID PQ compression at nbits=4 already enabled. Code index 336MB, docs 31MB [colbert-zero-research-integration.md]
- MemRL distillation prototype complete: 3-stage pipeline (unsupervised -> supervised -> distillation), A/B test harness ready, needs live seeding window [colbert-zero-research-integration.md]
- Query/document prefixes: LateOn-Code requires NO prefix (raw text only). GTE-ModernColBERT uses `[Q]`/`[D]` prefixes (auto-read from onnx_config.json). Adding prefixes to LateOn-Code would DEGRADE retrieval [colbert-zero-research-integration.md]
- Reason-ModernColBERT: 150M params, ~5ms CPU for 10-20 pages, strongest on reasoning-heavy queries. Does not compete for LLM inference slots [colbert-reranker-web-research.md]
- MemRL FAISS retrieval: 0.5ms at 5K memories, 2ms at 500K, 3ms at 1M. 35x-1000x speedup over NumPy baseline [Ch.07 MemRL]
- The routing classifier provides fast first-pass routing, falling back to full HybridRouter retrieval when confidence < 0.6 [colbert-zero-research-integration.md]
- Cosine similarity > 0.85 used for deduplication in both SkillBank skill storage and episodic memory [Ch.15, Ch.07]

## Actionable for EPYC

- **GTE-ModernColBERT-v1 is deployed**: Docs container swapped, reindexed (1992 chunks, 246s), model_registry.yaml and orchestrator_stack.py updated. Production-ready.
- **MemRL distillation A/B test**: All infrastructure ready (classifier, training scripts, test harness). Needs a live seeding window to collect fresh routing data for comparison.
- **ColBERT reranker for web_research (stub)**: Before implementing, instrument existing web_research pipeline to measure page contribution rates. If >30% of fetched pages contribute nothing, proceed with Reason-ModernColBERT integration.
- **Download Reason-ModernColBERT**: 150M model, set up inference via PyLate or colbert-ai. Benchmark reranking latency on CPU (target <10ms for 20 pages).
- **qmd hybrid search evaluation**: intake-270 marked adopt_component -- evaluate for markdown knowledge base search in the project wiki or handoff system.
- **MemPalace patterns**: intake-326 achieves 96.6% recall on LongMemEval. Investigate architecture patterns that could improve MemRL episodic retrieval quality.

## Open Questions

- What is the actual page contribution rate in current web_research sessions? (Needed to justify ColBERT reranker)
- Can the MemRL distillation classifier match HybridRouter quality on high-confidence decisions in production?
- Would Reason-ModernColBERT's reasoning-task advantage improve web_research synthesis quality measurably?
- Is the 50ms GTE-ModernColBERT latency acceptable under high-concurrency scenarios?
- Should the routing classifier's confidence threshold (0.6) be tuned via the conformal calibration system?

## Related Categories

- [Routing Intelligence](routing-intelligence.md) -- MemRL retrieval and routing classifier are core routing components
- [Training & Distillation](training-distillation.md) -- ColBERT-Zero 3-stage pipeline inspired MemRL distillation design
- [Cost-Aware Routing](cost-aware-routing.md) -- Reranking reduces unnecessary token consumption in web_research
- [Document Processing](document-processing.md) -- Better document parsing improves retrieval index quality

## Source References

- [ColBERT-Zero research integration](/workspace/handoffs/completed/colbert-zero-research-integration.md) -- Track 1 (GTE-ModernColBERT upgrade), Track 2 (MemRL distillation design), A/B results, implementation details
- [ColBERT reranker handoff](/workspace/handoffs/active/colbert-reranker-web-research.md) -- Reason-ModernColBERT proposal, validation criteria, work items
- [Ch.07 MemRL System](/mnt/raid0/llm/epyc-orchestrator/docs/chapters/07-memrl-system.md) -- Episodic memory architecture, FAISS backend, two-phase retrieval
- [NextPLAID handoff](/workspace/handoffs/archived/nextplaid-code-retrieval.md) -- NextPLAID multi-vector code and document retrieval architecture
- [intake-174](https://huggingface.co/lightonai/Reason-ModernColBERT) Reason-ModernColBERT -- Late-interaction retriever for reasoning tasks
- [intake-270](https://github.com/tobi/qmd) tobi/qmd -- Local hybrid search engine for markdown knowledge bases
- [intake-326](https://github.com/MemPalace/mempalace) MemPalace -- 96.6% LongMemEval recall local memory system
