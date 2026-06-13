# Project Wiki — Knowledge Index

Compiled knowledge base for the EPYC 9655 inference optimization project. Each article synthesizes findings from research deep-dives, intake entries, handoffs, progress logs, and child repo documentation into a single navigable reference.

**Last compiled**: 2026-06-13 (manual incremental update: Fable 5 evidence-plane, routing truth, K-RAG K7, security hardening, repo-readiness, batch-serving gaps, stack-prior contract)
**Articles**: 26 compiled, 4 stub categories
**Total sources**: 513 scanned documents across 6 source types; 2026-06-13 pass compiled the highest-value Fable/evidence/routing/K-RAG/stack-prior clusters

---

## Core Inference Optimization

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [Speculative Decoding](speculative-decoding.md) | 26 | Verification wall on hybrid SSM models kills all draft-verify approaches; NUMA parallelism is the dominant lever |
| [MoE Optimization](moe-optimization.md) | 23 | REAP 25-40% expert pruning is near-lossless; 30% sometimes outperforms 20% due to routing redistribution |
| [KV Cache](kv-cache.md) | 34 | Attention Matching achieves 50x compression; autopilot slot_compact integration complete with slot memory visibility |
| [Quantization](quantization.md) | 25 | Hadamard+q4_0 is the proven production KV config; exotic formats (TQ3, PolarQuant, QJL) all lose to it on CPU |
| [Hardware Optimization](hardware-optimization.md) | 58 | Batch=1 decode micro-opts are closed, but frontdoor spec-dec, DSA, batched eval serving, and MI210-as-eval-engine remain live angles |

## Serving & Systems

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [Inference Serving](inference-serving.md) | 36 | Multi-instance serving is mature; stack-priors are the serving truth contract; single-instance batched decode remains the unmeasured gap |
| [Local Inference](local-inference.md) | 16 | Cherry-picked upstream fixes unblock Qwen3.6 (0%→73.8%); fork conflict risk lower than assessed; full rebase deferred |
| [Chat Templates](chat-templates.md) | 2 | Per-family turn markers + when to use `/completion` (Qwen/gemma-3/Llama3) vs `/v1/chat/completions` (gemma-4 multi-channel) — checklist for onboarding new models without silent routing failures |

## Routing & Evaluation

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [Cost-Aware Routing](cost-aware-routing.md) | 30 | Task-rate/goodput telemetry exposes token bloat; stack-priors now anchor cost/TPS truth for q_scorer and seeding migrations |
| [Routing Intelligence](routing-intelligence.md) | 50 | Routing truth repair is live-attested; DAR-1 replay shows 0.00% identifiable regret, so routing expansion stays frozen |
| [Benchmark Methodology](benchmark-methodology.md) | 54 | T1 instrument repair and per-question ledgers are the new benchmark priority; claims need protocol, reps, date, and attestation |

## Agent & Architecture

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [Agent Architecture](agent-architecture.md) | 48 | Fable 5's strategic spine is real-task corpus -> reviewed self-running lab jobs -> data flywheel, gated by evidence and quarantine |
| [Autonomous Research](autonomous-research.md) | 62 | AutoPilot's binding constraint is decision-grade evidence; hotfixes landed, ledger/event-sourcing work remains the restart inflection point |
| [Memory-Augmented Models](memory-augmented.md) | 25 | Episodic FAISS writes require cross-process locking; llama RAM drift needs residency telemetry/recycle, not drop_caches |

## Context & Compression

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [Context Management](context-management.md) | 17 | 80-92% of agent context is redundant; DCP seed-bundle pre-assembly is wired advisory/default-off, with DCP-6 still inference-gated |
| [Context Extension](context-extension.md) | 19 | MemAgent achieves 437x extrapolation; Memento reveals 15pp KV-vs-text ceiling; YaRN is the production path for 256K-1M |
| [SSM & Hybrid Architectures](ssm-hybrid.md) | 9 | Verification latency (220ms/tok, 90% of cost) is the real speculation killer; Log-Linear GDN (ICLR 2026) could unblock via 4-10x state reduction |

## Training & Distillation

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [Training & Distillation](training-distillation.md) | 30 | LoRAX/S-LoRA are the code-backed adapter-serving references; MinT remains a closed-source scaling datapoint |
| [Reinforcement Learning](reinforcement-learning.md) | 14 | AReaL ruled out (6-order compute mismatch); GRPO/DAPO ubiquitous in deep-dive research |

## Multimodal & Domain

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [Multimodal](multimodal.md) | 34 | Benchmark deployed Qwen-VL field-placement before adding LocateAnything; Gemma 4 stays benchmark-first, not model-card-dismissed |
| [Document Processing](document-processing.md) | 4 | XY-Cut++ PDF parser: 0.84 accuracy at 0.05s/page; table extraction is the biggest gap |
| [Formal Verification](formal-verification.md) | 7 | Goedel-Code-Prover 8B beats GPT-5.3-Codex at 62.0%; RustEvo2 is now the gate for Rust specialist claims |

## Knowledge & Retrieval

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [Search & Retrieval](search-retrieval.md) | 31 | K-RAG K7 seed eval picks recency-weighted recall@10, but final retrieval claim waits on the 70-case certification pool |
| [Knowledge Management](knowledge-management.md) | 18 | K-RAG has a fresh 18K-chunk index and certification pool; repo-readiness scoring turns governance gaps into deterministic criteria |
| [RAG Alternatives](rag-alternatives.md) | 2 | SLIDERS structured-DB+SQL alternative gated behind Phase 0 falsification (GPT-4.1 hard-wired adoption blocker; not on ColBERT upgrade path) |
| [Tool Implementation](tool-implementation.md) | 24 | Security-review, source-quarantine validation, and repo-readiness scoring extend governance tooling without autonomous index edits |

## Research & Analysis

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [LLM Prompting](llm-prompting.md) | 14 | CoT controllability is 0.1-15.4% (safety positive); FlowSteer blocked on hybrid SSM |
| [Mechanistic Interpretability](mechanistic-interpretability.md) | 6 | Qwen-Scope releases SAEs for production-stack Qwen3/3.5 (~687 GB FP32 full subset, qwen license); AxBench + Wang 2026 falsify SAE-steering against simpler baselines (DiffMean, prompting); Section 4 benchmark-redundancy is the strongest application — pilot first |
| [Safety](safety.md) | 4 | External-source text is now quarantined as data; security review uses exploit-path-gated STRIDE/OWASP/LLM checks |

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
| ~~`safety`~~ | — | Promoted to full article 2026-06-13 → [Safety](safety.md) |
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
