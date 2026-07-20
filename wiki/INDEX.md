# Project Wiki — Knowledge Index

Compiled knowledge base for the EPYC 9655 inference optimization project. Each article synthesizes findings from research deep-dives, intake entries, handoffs, progress logs, and child repo documentation into a single navigable reference.

**Last compiled**: 2026-07-20 (merged 23 new sources — CPU-prefill barrier-fusion arc, live within-role placement SM + E1/E2/E5 batched-decode, heterogeneous CPU×GPU slot-fabric design, the reasoning∝active / 2-bit-asymmetry literature, the specced architect + reviewer model-role benches, eval-tower ECE/AUC, StreamingLLM floor, quant-asymmetric self-spec, and K28 fused-GDN research — into 8 articles; observation-heavy GPU sections remain review-gated pending post-promotion P-GPU-1.)
**Articles**: 26 compiled, 4 stub categories
**Total sources**: 580+ scanned documents across 6 source types; 2026-07-20 pass merged 23 changed/new sources into 8 articles; 2026-07-05 pass merged 49 changed/new sources into 10 articles; 2026-06-21 pass merged 36 changed/new sources into 21 articles

---

## Core Inference Optimization

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [Speculative Decoding](speculative-decoding.md) | 61+ | Every production target ships a near-free native MTP head that beats external drafters (measured dead); the surviving redesign is quant-asymmetric same-model self-spec (IQ2-GPU drafter + Q4-CPU verifier, K2 1.61×, observation-grade) |
| [MoE Optimization](moe-optimization.md) | 37 | Reasoning ∝ ACTIVE FLOPs, knowledge ∝ TOTAL params; GLM-5.2 routing is near-uniform (top_32=15%) so generic hot-expert offload/REAP is not justified; IQ2 GPU residency is two-for-two viable but caps at ~122B |
| [KV Cache](kv-cache.md) | 39 | StreamingLLM pre-v7 floor sweep failed the quality floor → no simple KV cluster admitted yet; per-token KV streaming over PCIe is an anti-pattern (7-14× slower than DDR5); GDN residents' O(1) KV make teleport KV-copy near-moot |
| [Quantization](quantization.md) | 31 | 2-bit is asymmetric — knowledge holds ~99% but reasoning halves under UNIFORM 2-bit (dynamic UD/DQ3 holds); the architect's IQ2≈Q4 Δ0.0pp parity is knowledge-only (n≈4/hard-suite), NOT reasoning-certified; architect quant UNDECIDED (bench-gated) |
| [Hardware Optimization](hardware-optimization.md) | 90+ | CPU decode is BW-exhausted but CPU *prefill* is an open compute-bound regime (hot path = OpenMP barriers, not math → default-off CONCAT dim0 lever +3-9%); GPU raw-speed frontier structurally exhausted, live frontier is residency/teleport; v7 READY but NOT promoted |

## Serving & Systems

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [Inference Serving](inference-serving.md) | 55 | Within-role full↔quarter placement SM is LIVE (3-way frontdoor 1.68×, session-handover migration, no mid-decode preemption); single `-np 8` batch server is 4.86× faster per eval; the heterogeneous CPU×GPU slot fabric is a DESIGN that EXTENDS the live fabric (gated post-v7 + E5) |
| [Local Inference](local-inference.md) | 36 | v7 READY but NOT promoted (prod stays v6+iqk); deployed-lane throughput table + living model-probe scoreboard (all observation-grade); MI210 fits everything but the 122B-Q4 architect and GLM-5.2 (238 GB) |
| [Chat Templates](chat-templates.md) | 2 | Per-family turn markers + when to use `/completion` (Qwen/gemma-3/Llama3) vs `/v1/chat/completions` (gemma-4 multi-channel) — checklist for onboarding new models without silent routing failures |

## Routing & Evaluation

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [Cost-Aware Routing](cost-aware-routing.md) | 40+ | CoT scaffold-transplant falsified in both regimes (reasoning context amplifies, doesn't substitute for, receiver capability); verifier/selector best-of-N is the forward GPU-assist path |
| [Routing Intelligence](routing-intelligence.md) | 67+ | RI-10 decision-ready but first packet is `hold_quality_unscored` (proxies favor enforce; factuality unscored); X-MAS learned route-mutation is live in enforce — first learned routing layer in production |
| [Benchmark Methodology](benchmark-methodology.md) | 83+ | Model-role selection benches (architect + reviewer) are objective-scored ONLY — model-as-judge patch-review measured near-random (AUC 0.509); architect choice UNDECIDED (specced, gated); eval-tower must track ECE/AUC not just accuracy; suites saturate at 90-94% and can't resolve top-2 models |

## Agent & Architecture

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [Agent Architecture](agent-architecture.md) | 64+ | Consult primitive went design→staged-v1 in one week, all default-off; Hermes is now one client of the shared `/v1/chat/completions` + `x_*` contract rather than a special routing path |
| [Autonomous Research](autonomous-research.md) | 87+ | Ledger authority cutover is live; planner economics pivoted to local drafting/critique, with `frontdoor` drafting and `worker_general` critique queued for the next boundary restart |
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
| [Document Processing](document-processing.md) | 4 | ODL structured metadata and default-off body warnings now reach preprocessing; the hybrid sidecar is live on `127.0.0.1:5002`, so the remaining table gap is benchmark-backed comparison and routing policy |
| [Formal Verification](formal-verification.md) | 7 | Goedel-Code-Prover 8B beats GPT-5.3-Codex at 62.0%; RustEvo2 is now the gate for Rust specialist claims |

## Knowledge & Retrieval

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [Search & Retrieval](search-retrieval.md) | 31 | K-RAG K7 seed eval picks recency-weighted recall@10, but final retrieval claim waits on the 70-case certification pool |
| [Knowledge Management](knowledge-management.md) | 18+ | K-RAG K7 certification produced a zero-miss retrieval candidate; wiki compile remains a derived wrap-up artifact |
| [RAG Alternatives](rag-alternatives.md) | 2 | SLIDERS structured-DB+SQL alternative gated behind Phase 0 falsification (GPT-4.1 hard-wired adoption blocker; not on ColBERT upgrade path) |
| [Tool Implementation](tool-implementation.md) | 40 | Dashboards were built as liveness instruments, not value instruments; the regions-lock panel now separates `/proc` owners, live tap requests, and inferred activity instead of collapsing them into one ownership story |

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

**2026-07-20 single-source stubs (not promoted to their own section this pass):**
- `cost_aware_routing` / `agent_architecture` — the [scaffold CoT cost-lever autopilot deployment](../handoffs/active/scaffold-autopilot-cost-lever-deployment.md) is a DESIGN handoff (episodic-memory-gated composite scaffold-then-nothink route; caps a beneficiary's CPU-decode tokens ~20-50×, quality benefit is headroom-conditional). All numbers are OBSERVATION-grade; nothing implemented. Its findings are already reflected in [Cost-Aware Routing](cost-aware-routing.md) (CoT scaffold-transplant falsified as a capability transplant, deployed only as a gated cost lever).

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
