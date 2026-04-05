# ColBERT Reranker for web_research Pipeline

**Status**: stub
**Created**: 2026-04-05 (extracted from `04-mirothinker-worker-eval.md` intake-174)
**Priority**: LOW
**Effort**: Medium
**Source**: [Reason-ModernColBERT (lightonai)](https://huggingface.co/lightonai/Reason-ModernColBERT)

## Objective

Add a reranking stage to the `web_research` pipeline between DuckDuckGo fetch and explore worker synthesis. Currently the explore worker receives all fetched pages and synthesizes directly, spending tokens on low-relevance pages that DuckDuckGo ranked highly by keyword match but are semantically weak for reasoning tasks.

## Background

Reason-ModernColBERT is a 150M late-interaction retriever competitive with 7B+ dense models on reasoning-intensive benchmarks (BRIGHT). Key properties:

- **150M parameters, 128-dim multi-vector, MaxSim scoring** — runs in ~5ms on CPU for 10-20 pages
- **Does NOT compete for llama-server inference slots** — separate model entirely
- **Late-interaction advantage strongest on reasoning-heavy queries** (Biology +7, Earth Science +9.6 NDCG@10 vs dense)

## Proposed Integration

1. After DuckDuckGo fetch, encode pages + query via Reason-ModernColBERT
2. Rerank by MaxSim score
3. Pass only top-K to explore worker
4. This reduces worker context pressure and improves synthesis quality on reasoning tasks

## Validation Criteria

Before implementing, measure on existing web_research sessions:
- What fraction of fetched pages actually contribute to the final synthesis?
- If >30% are discarded or contribute nothing, reranking is justified

## Work Items

- [ ] S1: Download Reason-ModernColBERT, set up inference (PyLate or colbert-ai)
- [ ] S2: Benchmark reranking latency on CPU (target <10ms for 20 pages)
- [ ] S3: Instrument existing web_research pipeline to log page contribution rates
- [ ] S4: If S3 confirms >30% waste — integrate reranking into `web_research` tool
- [ ] S5: A/B test reranked vs unranked on web_research benchmark questions

## Key Files

| Resource | Path |
|----------|------|
| web_research tool | `epyc-orchestrator/src/` (web_research implementation) |
| Explore worker config | `epyc-orchestrator/orchestration/model_registry.yaml` |
| Seeding harness | `epyc-inference-research/scripts/benchmark/seed_specialist_routing.py` |

## References

- intake-174: Reason-ModernColBERT analysis
- [BRIGHT benchmark](https://github.com/xlang-ai/BRIGHT) — reasoning-intensive retrieval benchmark
- [PyLate](https://github.com/lightonai/pylate) — late-interaction retrieval library
