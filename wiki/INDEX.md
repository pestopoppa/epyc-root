# Project Wiki — Knowledge Index

Compiled knowledge base for the EPYC 9655 inference optimization project. Each article synthesizes findings from research deep-dives, intake entries, handoffs, progress logs, and child repo documentation into a single navigable reference.

**Last compiled**: 2026-05-28 (manual incremental update: handoff-index coverage invariant)
**Articles**: 25 compiled, 5 stub categories
**Total sources**: 329 documents across 6 source types

---

## Core Inference Optimization

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [Speculative Decoding](speculative-decoding.md) | 26 | Verification wall on hybrid SSM models kills all draft-verify approaches; NUMA parallelism is the dominant lever |
| [MoE Optimization](moe-optimization.md) | 23 | REAP 25-40% expert pruning is near-lossless; 30% sometimes outperforms 20% due to routing redistribution |
| [KV Cache](kv-cache.md) | 34 | Attention Matching achieves 50x compression; autopilot slot_compact integration complete with slot memory visibility |
| [Quantization](quantization.md) | 25 | Hadamard+q4_0 is the proven production KV config; exotic formats (TQ3, PolarQuant, QJL) all lose to it on CPU |
| [Hardware Optimization](hardware-optimization.md) | 21 | NUMA 4-way quarter pinning delivers 6.9x aggregate throughput; DGX Spark ($4,699) is primary GPU path |

## Serving & Systems

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [Inference Serving](inference-serving.md) | 25 | Qwen3.6 drop-in upgrade (Q8 27.4tps, +11pp Terminal-Bench); serving indices now distinguish unresolved action from stale narration, with NUMA disagg, wdata coalescing, Qwen3.6 fixes, and launcher defaults explicitly gated |
| [Local Inference](local-inference.md) | 16 | Cherry-picked upstream fixes unblock Qwen3.6 (0%→73.8%); fork conflict risk lower than assessed; full rebase deferred |
| [Chat Templates](chat-templates.md) | 2 | Per-family turn markers + when to use `/completion` (Qwen/gemma-3/Llama3) vs `/v1/chat/completions` (gemma-4 multi-channel) — checklist for onboarding new models without silent routing failures |

## Routing & Evaluation

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [Cost-Aware Routing](cost-aware-routing.md) | 21 | 50-70% of reasoning tokens are redundant; difficulty signal has NO predictive spread at 0.15/0.35 thresholds; tool A/B slightly net-positive |
| [Routing Intelligence](routing-intelligence.md) | 29 | Cross-role contention gate plus live-affinity proof and topology-hash enforcement are required before baseline-eligible parallel routing |
| [Benchmark Methodology](benchmark-methodology.md) | 33 | Real-path canaries and live smoke tests are required; stalled seeding now has explicit infra labels instead of generic timeout ambiguity |

## Agent & Architecture

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [Agent Architecture](agent-architecture.md) | 30 | Multi-file coding failure diagnosed as REPL/BEP protocol friction, not model capability; edit transactions solve practical remediation while J8 remains only a legacy batch-edit keep/retire experiment |
| [Autonomous Research](autonomous-research.md) | 38 | AutoPilot HLE observe-only fields and rule metrics are in the journal; HALO-2 can convert live journals to OTLP spans, but analyzer runs remain operator/inference-gated |
| [Memory-Augmented Models](memory-augmented.md) | 20 | MemAgent 437x extrapolation but CPU-infeasible; MemPalace 96.6% recall with hierarchical organization |

## Context & Compression

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [Context Management](context-management.md) | 17 | 80-92% of agent context is redundant; DCP seed-bundle pre-assembly is wired advisory/default-off, with DCP-6 still inference-gated |
| [Context Extension](context-extension.md) | 19 | MemAgent achieves 437x extrapolation; Memento reveals 15pp KV-vs-text ceiling; YaRN is the production path for 256K-1M |
| [SSM & Hybrid Architectures](ssm-hybrid.md) | 9 | Verification latency (220ms/tok, 90% of cost) is the real speculation killer; Log-Linear GDN (ICLR 2026) could unblock via 4-10x state reduction |

## Training & Distillation

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [Training & Distillation](training-distillation.md) | 22 | Simula reasoning-driven synthetic data (TMLR 2026): taxonomy coverage 2x, double-critic, complexity-aware generation |
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
| [Search & Retrieval](search-retrieval.md) | 16 | ColBERT reranker S1-S4 complete (ONNX Runtime, 180ms encoding, perfect ranking separation); S5 LateOn drop-in code ready (NIB2-47); Reason-mxbai edge fallback queued |
| [Knowledge Management](knowledge-management.md) | 9 | KB-RAG ColBERT architecture (K1–K8); handoff-index coverage invariant now requires every active non-index handoff to be owned by an index or top-level tracker |
| [RAG Alternatives](rag-alternatives.md) | 2 | SLIDERS structured-DB+SQL alternative gated behind Phase 0 falsification (GPT-4.1 hard-wired adoption blocker; not on ColBERT upgrade path) |
| [Tool Implementation](tool-implementation.md) | 15 | GitNexus remains the required blast-radius tool; local `$wrap-up` skill now codifies progress/handoff/wiki/commit closeout discipline |

## Research & Analysis

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [LLM Prompting](llm-prompting.md) | 14 | CoT controllability is 0.1-15.4% (safety positive); FlowSteer blocked on hybrid SSM |
| [Mechanistic Interpretability](mechanistic-interpretability.md) | 6 | Qwen-Scope releases SAEs for production-stack Qwen3/3.5 (~687 GB FP32 full subset, qwen license); AxBench + Wang 2026 falsify SAE-steering against simpler baselines (DiffMean, prompting); Section 4 benchmark-redundancy is the strongest application — pilot first |

---

## Stub Categories

These categories have intake entries but insufficient depth for a compiled article. Raw sources are accessible via the query operation:

```
python3 .claude/skills/project-wiki/scripts/query_wiki.py "<category>" --human
```

| Category | Intake Entries | Notes |
|----------|---------------|-------|
| `emotion_psychology` | 18 | Persona, cognitive science of LLMs — not central to inference optimization |
| ~~`knowledge_management`~~ | — | Promoted to full article 2026-04-28 → [Knowledge Management](knowledge-management.md) |
| ~~`mechanistic_interpretability`~~ | — | Promoted to full article 2026-05-04 → [Mechanistic Interpretability](mechanistic-interpretability.md) |
| ~~`rag_alternatives`~~ | — | Promoted to full article 2026-04-28 → [RAG Alternatives](rag-alternatives.md) |
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
