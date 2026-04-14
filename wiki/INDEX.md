# Project Wiki — Knowledge Index

Compiled knowledge base for the EPYC 9655 inference optimization project. Each article synthesizes findings from research deep-dives, intake entries, handoffs, progress logs, and child repo documentation into a single navigable reference.

**Last compiled**: 2026-04-14
**Articles**: 24 compiled, 6 stub categories
**Total sources**: 235 documents across 6 source types

---

## Core Inference Optimization

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [Speculative Decoding](speculative-decoding.md) | 26 | Verification wall on hybrid SSM models kills all draft-verify approaches; NUMA parallelism is the dominant lever |
| [MoE Optimization](moe-optimization.md) | 23 | REAP 25-40% expert pruning is near-lossless; 30% sometimes outperforms 20% due to routing redistribution |
| [KV Cache](kv-cache.md) | 34 | Attention Matching achieves 50x compression; autopilot slot_compact integration complete with slot memory visibility |
| [Quantization](quantization.md) | 25 | Hadamard+q4_0 is the proven production KV config; exotic formats (TQ3, PolarQuant, QJL) all lose to it on CPU |
| [Hardware Optimization](hardware-optimization.md) | 19 | NUMA 4-way quarter pinning delivers 6.9x aggregate throughput; DGX Spark ($4,699) is primary GPU path |

## Serving & Systems

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [Inference Serving](inference-serving.md) | 15 | Production stack: 4-tier agent hierarchy, NUMA-pinned instances, ~515 GB deployed footprint |
| [Local Inference](local-inference.md) | 15 | Custom llama.cpp fork (23+ patches incl. Diff Attn V2), GGUF-native pipeline, 12 acceleration techniques catalogued |

## Routing & Evaluation

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [Cost-Aware Routing](cost-aware-routing.md) | 21 | 50-70% of reasoning tokens are redundant; difficulty signal has NO predictive spread at 0.15/0.35 thresholds; tool A/B slightly net-positive |
| [Routing Intelligence](routing-intelligence.md) | 17 | MemRL with 2,714 episodic memories, FAISS 35x speedup, species budget rebalancing |
| [Benchmark Methodology](benchmark-methodology.md) | 26 | All 10 seeding modules at 100% coverage; 61 integration tests; 1,290-measurement sweep overturned prior assumptions |

## Agent & Architecture

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [Agent Architecture](agent-architecture.md) | 22 | Paperclip cost governance, LangGraph comparison, OpenGauss tool pair sanitization pattern |
| [Autonomous Research](autonomous-research.md) | 19 | EvoScientist evolution manager fills AutoPilot memory gap; strategy distillation yields +10.17pp |
| [Memory-Augmented Models](memory-augmented.md) | 20 | MemAgent 437x extrapolation but CPU-infeasible; MemPalace 96.6% recall with hierarchical organization |

## Context & Compression

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [Context Management](context-management.md) | 17 | 80-92% of agent context is redundant; 6 papers converge; 32K with folding beats 327K uncompressed |
| [Context Extension](context-extension.md) | 19 | MemAgent achieves 437x extrapolation; Memento reveals 15pp KV-vs-text ceiling; YaRN is the production path for 256K-1M |
| [SSM & Hybrid Architectures](ssm-hybrid.md) | 9 | Verification latency (220ms/tok, 90% of cost) is the real speculation killer; Log-Linear GDN (ICLR 2026) could unblock via 4-10x state reduction |

## Training & Distillation

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [Training & Distillation](training-distillation.md) | 18 | ACT contrastive RL outperforms imitation learning; cross-size transfer 8B→4B works well |
| [Reinforcement Learning](reinforcement-learning.md) | 14 | AReaL ruled out (6-order compute mismatch); GRPO/DAPO ubiquitous in deep-dive research |

## Multimodal & Domain

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [Multimodal](multimodal.md) | 28 | Qwen3-TTS viable (0.6B, Apache 2.0, 97ms first-packet); Moondream 3 deferred (BSL license) |
| [Document Processing](document-processing.md) | 4 | XY-Cut++ PDF parser: 0.84 accuracy at 0.05s/page; table extraction is the biggest gap |
| [Formal Verification](formal-verification.md) | 5 | Goedel-Code-Prover 8B beats GPT-5.3-Codex at 62.0%; decomposition alone accounts for +28pp |

## Knowledge & Retrieval

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [Search & Retrieval](search-retrieval.md) | 16 | ColBERT reranker S1-S4 complete (ONNX Runtime, 180ms encoding, perfect ranking separation); S5 gated on post-AR-3 analysis |
| [Tool Implementation](tool-implementation.md) | 12 | GitNexus: context injection outperforms tools; "real REPL, mock LLM" integration test pattern; risk-weighted coverage methodology |

## Research & Analysis

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [LLM Prompting](llm-prompting.md) | 14 | CoT controllability is 0.1-15.4% (safety positive); FlowSteer blocked on hybrid SSM |

---

## Stub Categories

These categories have intake entries but insufficient depth for a compiled article. Raw sources are accessible via the query operation:

```
python3 .claude/skills/project-wiki/scripts/query_wiki.py "<category>" --human
```

| Category | Intake Entries | Notes |
|----------|---------------|-------|
| `emotion_psychology` | 18 | Persona, cognitive science of LLMs — not central to inference optimization |
| `knowledge_management` | 10 | Meta-category about this wiki and KB governance patterns |
| `mechanistic_interpretability` | 23 | Sparse autoencoders, circuit analysis — tangential to production stack |
| `rag_alternatives` | 2 | Covered by [Search & Retrieval](search-retrieval.md) |
| `safety` | 4 | Covered by [LLM Prompting](llm-prompting.md) CoT monitorability findings |
| `swarm_techniques` | 7 | Partially covered by [Agent Architecture](agent-architecture.md) and [Autonomous Research](autonomous-research.md) |

---

## How to Use This Wiki

**For humans**: Browse by section above. Each article has Summary, Key Findings, Actionable for EPYC, and Source References sections.

**For agents**: Query the knowledge base programmatically:
```
python3 .claude/skills/project-wiki/scripts/query_wiki.py "speculative decoding" --human
```

**To update**: Run the compile operation when new research is ingested:
```
python3 .claude/skills/project-wiki/scripts/compile_sources.py --full  # list sources
# Then invoke: "compile the wiki"
```

**Taxonomy**: See [SCHEMA.md](SCHEMA.md) for the full category ontology with 30 canonical categories and 34 aliases.
