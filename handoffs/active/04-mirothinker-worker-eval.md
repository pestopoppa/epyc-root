# MiroThinker Worker Evaluation

**Status**: ACTIVE
**Created**: 2026-03-03
**Priority**: P1 — depends on #02 results for comparison baseline
**Effort**: Medium
**Depends On**: `02-nanbeige-3b-worker-eval.md` (for benchmark comparison baseline)
**Source**: [MiroThinker (github.com/MiroMindAI/MiroThinker)](https://github.com/MiroMindAI/MiroThinker)

## Research Review

### MiroThinker: Deep Research Agent
**Authors:** MiroMind AI

Open-source deep research agent with 80.8% on GAIA-Val-165. Features MiroFlow framework (tool-use agent framework), MiroVerse dataset (147K training samples), 256K context, up to 400 tool calls per task. Released at 8B/30B/235B. Uses SFT and DPO training.

**Orchestrator Relevance: HIGH.** Directly comparable to our web_research tool and deep search workflow:
- **MiroFlow framework**: Reproducible tool-use agent framework — could inform our worker graph design
- **MiroVerse dataset (147K samples)**: Open training data for agentic behavior, potential SFT source for our workers
- **400 tool calls / 256K context**: Validates our approach of long-horizon agentic tasks, but at much larger scale
- **Multi-scale variants**: Their 8B model could serve as an upgraded explore worker (currently Qwen2.5-7B)
- **GAIA benchmark methodology**: We should add GAIA to our evaluation suite

### Model Variants
| Size | Use Case | Relevance |
|------|----------|-----------|
| 8B | Explore worker replacement | HIGH — direct competitor to Qwen2.5-7B |
| 30B | Root LM alternative | MEDIUM — needs throughput testing |
| 235B | Reference only | LOW — too large for local inference |

## References

- [MiroThinker repo](https://github.com/MiroMindAI/MiroThinker)
- [MiroVerse dataset](https://huggingface.co/datasets/MiroMindAI/MiroVerse) — 147K agentic training samples
- [GAIA benchmark](https://huggingface.co/gaia-benchmark) — standard for deep research agents
- Current explore worker: Qwen2.5-7B on port 8082
- Web research tool: `/mnt/raid0/llm/epyc-orchestrator/src/` (web_research implementation)

## Implementation Steps

### 1. Acquire and convert MiroThinker-8B
- Download MiroThinker-8B from HuggingFace
- Convert to GGUF for llama.cpp
- Quantize at Q4_K_M and Q8_0
- Place in `/mnt/raid0/llm/models/mirothinker-8b/`

### 2. Benchmark against Qwen2.5-7B (and Nanbeige-3B if available)
- Run seeding suite on identical question pool
- Focus on web_research and deep search tasks specifically
- Compare: answer quality, tool-call success rate, context utilization, hallucination rate
- Use GAIA-style multi-hop questions if available in question pool

### 3. Evaluate MiroVerse dataset for SFT potential
- Download and analyze MiroVerse 147K samples
- Assess format compatibility with our training pipeline
- Identify high-quality subsets relevant to our worker tasks (REPL, web research, code review)
- Document dataset statistics and quality assessment

### 4. Test 256K context and long-horizon workflows
- Stress test with tasks requiring many turns (>50 tool calls)
- Compare context utilization vs Qwen2.5-7B at same context lengths
- Measure quality degradation curve as context fills

### 5. Decision and integration
- Compare results against #02 Nanbeige-3B benchmark
- If MiroThinker-8B outperforms: add to model registry as explore worker
- If Nanbeige-3B wins at 3B: consider MiroThinker for specialized deep-search-only role

## Acceptance Criteria

- [ ] MiroThinker-8B downloaded, converted, quantized
- [ ] Seeding benchmark completed against Qwen2.5-7B baseline
- [ ] Comparison with Nanbeige-3B results documented
- [ ] MiroVerse dataset evaluated for SFT potential
- [ ] Long-horizon stress test completed
- [ ] Decision documented: adopt / specialize / reject

## Research Intake Update — 2026-03-20

### ColBERT Reranker for web_research Pipeline (intake-174)

**Source**: Reason-ModernColBERT (lightonai) — 150M late-interaction retriever, competitive with 7B+ dense models on reasoning-intensive benchmarks (BRIGHT)

**Context**: MiroThinker achieves 80.8% on GAIA-Val-165 with up to 400 tool calls per task. Our `web_research` pipeline (search → parallel fetch → worker synthesis) currently has no reranking stage — the explore worker (Qwen2.5-7B, port 8082) receives all fetched pages and synthesizes directly. This means the worker spends tokens on low-relevance pages that DuckDuckGo ranked highly by keyword match but are semantically weak for reasoning tasks.

**Proposed addition to Step 2 (benchmark against Qwen2.5-7B)**: When benchmarking web_research tasks specifically, measure how many fetched pages actually contribute to the final synthesis. If >30% of fetched pages are discarded or contribute nothing, a reranking stage would reclaim those tokens. Reason-ModernColBERT (150M, 128-dim multi-vector, MaxSim) runs in ~5ms on CPU for reranking 10-20 pages and doesn't compete for llama-server inference slots — it's a separate model entirely. The late-interaction advantage is largest on exactly the reasoning-heavy queries where web_research matters most (Biology +7, Earth Science +9.6 NDCG@10 vs dense).

**Integration path**: After DuckDuckGo fetch, encode pages + query via Reason-ModernColBERT, rerank by MaxSim score, pass only top-K to explore worker. This reduces worker context pressure and improves synthesis quality on reasoning tasks — directly comparable to MiroThinker's approach of selecting relevant tool outputs before synthesis.
