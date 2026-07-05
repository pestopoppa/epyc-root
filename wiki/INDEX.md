# Project Wiki — Knowledge Index

Compiled knowledge base for the EPYC 9655 inference optimization project. Each article synthesizes findings from research deep-dives, intake entries, handoffs, progress logs, and child repo documentation into a single navigable reference.

**Last compiled**: 2026-07-05 (full backlog compile: 49 changed sources since 2026-07-04 — the deferred "47-source cross-session backlog" — merged into 10 articles: [Hardware Optimization](hardware-optimization.md) (MI210 campaign, bf16 GDN state, two-axis roadmap), [Speculative Decoding](speculative-decoding.md) (MTP-on-GPU-MoE converged ~neutral, prompt-lookup corpus retired), [Autonomous Research](autonomous-research.md) (ledger authority cutover live, planner-economics local pivot), [Benchmark Methodology](benchmark-methodology.md) (tool-use lane live, W8 sparse-baseline repair), [Routing Intelligence](routing-intelligence.md) (RI-10 decision-ready/hold, X-MAS enforce live), [Inference Serving](inference-serving.md) (launcher NUMA default flip, DS-7 codified), [Agent Architecture](agent-architecture.md) (consult v1 wired default-off, BEP arc closed), [Cost-Aware Routing](cost-aware-routing.md) (CoT scaffold falsified, verifier/selector pivot), [Context Management](context-management.md), and [Tool Implementation](tool-implementation.md) (:8100 hub, dashboards-as-value-instruments bar). Observation-heavy sections carry writer-evidence review flags pending human/measured review. Prior 2026-07-03 focused checkpoint retained in article history.)
**Articles**: 26 compiled, 4 stub categories
**Total sources**: 560+ scanned documents across 6 source types; 2026-07-05 pass merged 49 changed/new sources (MI210 speed campaign, evidence-plane/autopilot arc, dashboards, routing canary) into 10 articles; 2026-06-21 pass merged 36 changed/new sources into 21 articles

---

## Core Inference Optimization

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [Speculative Decoding](speculative-decoding.md) | 52+ | MTP-on-GPU-MoE converged ~neutral at production temp (run MTP OFF for GPU-resident MoE; MTP stays a CPU/BW-bound + GPU-dense win); corpus prompt-lookup retired after failed clean-window A/B |
| [MoE Optimization](moe-optimization.md) | 23 | REAP 25-40% expert pruning is near-lossless; 30% sometimes outperforms 20% due to routing redistribution |
| [KV Cache](kv-cache.md) | 34 | Attention Matching is production-implemented but current-stack rollout decisions still need refreshed long-context/coding evidence |
| [Quantization](quantization.md) | 25 | Hadamard+q4_0 is the proven production KV config; exotic formats (TQ3, PolarQuant, QJL) all lose to it on CPU |
| [Hardware Optimization](hardware-optimization.md) | 85+ | bf16 GDN recurrent-state kernel is the campaign's clean deployed-role win (+13–21% @B32, runtime-gated); MI210 roadmap is two axes (residency quant-ladder vs GPU drafter-farm) competing for one card |

## Serving & Systems

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [Inference Serving](inference-serving.md) | 48 | Launcher `--numa-mode` default flipped to `quarter` (closes silent oversubscription hazard); DS-7 static-prewarm profile codified; restart-applicator hardened but promotion still ledger-gated |
| [Local Inference](local-inference.md) | 16 | Cherry-picked upstream fixes unblock Qwen3.6 (0%→73.8%); fork conflict risk lower than assessed; full rebase deferred |
| [Chat Templates](chat-templates.md) | 2 | Per-family turn markers + when to use `/completion` (Qwen/gemma-3/Llama3) vs `/v1/chat/completions` (gemma-4 multi-channel) — checklist for onboarding new models without silent routing failures |

## Routing & Evaluation

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [Cost-Aware Routing](cost-aware-routing.md) | 40+ | CoT scaffold-transplant falsified in both regimes (reasoning context amplifies, doesn't substitute for, receiver capability); verifier/selector best-of-N is the forward GPU-assist path |
| [Routing Intelligence](routing-intelligence.md) | 67+ | RI-10 decision-ready but first packet is `hold_quality_unscored` (proxies favor enforce; factuality unscored); X-MAS learned route-mutation is live in enforce — first learned routing layer in production |
| [Benchmark Methodology](benchmark-methodology.md) | 70+ | Tool-use sentinel lane live under Gate-3 discipline; W8's dominant blocker was a sparse-baseline artifact (advisory-below-n=5 repair); sequential alpha-wealth exposure confirmed real |

## Agent & Architecture

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [Agent Architecture](agent-architecture.md) | 63+ | Consult primitive went design→staged-v1 in one week, all default-off (48h bake is the only gate); BEP transactional-apply arc closed; DCP's first live A/B self-classified `hold` |
| [Autonomous Research](autonomous-research.md) | 86+ | Ledger authority cutover is live (W1 archive + W4 `ledger_authoritative`); planner economics pivoted to LocalPlannerProvider after the spend breaker tripped; alpha-wealth multiplicity guard confirmed the hazard was real |
| [Memory-Augmented Models](memory-augmented.md) | 25+ | Episodic FAISS writes require cross-process locking; K-MEM Tulving is a mixed baseline with weak chronology and no memory-routing promotion |

## Context & Compression

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [Context Management](context-management.md) | 28 | 80-92% of agent context is redundant; reasoning context does not transplant capability (amplifier, not substitute); DCP-for-consult landed default-off |
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
| [Document Processing](document-processing.md) | 4 | ODL structured metadata and default-off body warnings now reach preprocessing; real hybrid table sidecar/client evidence is the remaining table gap |
| [Formal Verification](formal-verification.md) | 7 | Goedel-Code-Prover 8B beats GPT-5.3-Codex at 62.0%; RustEvo2 is now the gate for Rust specialist claims |

## Knowledge & Retrieval

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [Search & Retrieval](search-retrieval.md) | 31 | K-RAG K7 seed eval picks recency-weighted recall@10, but final retrieval claim waits on the 70-case certification pool |
| [Knowledge Management](knowledge-management.md) | 18+ | K-RAG K7 certification produced a zero-miss retrieval candidate; wiki compile remains a derived wrap-up artifact |
| [RAG Alternatives](rag-alternatives.md) | 2 | SLIDERS structured-DB+SQL alternative gated behind Phase 0 falsification (GPT-4.1 hard-wired adoption blocker; not on ColBERT upgrade path) |
| [Tool Implementation](tool-implementation.md) | 39 | Dashboards were built as liveness instruments, not value instruments — every telemetry addition now needs an outcome KPI + escalation rule; :8100 project hub live with git-derived recency |

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
