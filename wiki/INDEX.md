# Project Wiki — Knowledge Index

Compiled knowledge base for the EPYC 9655 inference optimization project. Each article synthesizes findings from research deep-dives, intake entries, handoffs, progress logs, and child repo documentation into a single navigable reference.

**Last compiled**: 2026-07-24 (incremental — merged 14 new sources into 7 articles: the WP-12 fleet-layer flip + case-10 live gate (C10-F1 per-role `Semaphore(1)` finding) and the big+quarters lineup restoration into Inference Serving; the E5 NUMA×batch W0 scout (69/69 cells, C3-quarters-optimal-everywhere, model-dependent C1b) and the cross-architecture GPU np×context throughput surface into Hardware Optimization; the architect-bench well-powered NULL + R7 scorer-artifact correction + scoring-infra fragmentation audit into Benchmark Methodology; the IQ2-vs-Q4 termination-defect refutation + CPU A2 arm into Quantization; the MiniCPM-o promotion runbook + worker_vision trigger gate into Multimodal; the per-model MTP-depth/batching architecture-dependence into Speculative Decoding; and the measured reasoning-effort ladder + token-budget study into Cost-Aware Routing. Earlier 2026-07-21 pass merged 28 changed/new sources into 2 articles; 2026-07-20 pass merged 23 new sources into 8 articles.)
**Articles**: 26 compiled, 4 stub categories
**Total sources**: 590+ scanned documents across 6 source types; 2026-07-24 pass merged 14 changed/new sources into 7 articles; 2026-07-21 pass merged 28 changed/new sources into 2 articles; 2026-07-20 pass merged 23 changed/new sources into 8 articles; 2026-07-05 pass merged 49 changed/new sources into 10 articles; 2026-06-21 pass merged 36 changed/new sources into 21 articles

---

## Core Inference Optimization

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [Speculative Decoding](speculative-decoding.md) | 63+ | Every production target ships a near-free native MTP head that beats external drafters (measured dead); per-model MTP depth is now measured for all 3 architect candidates (122B-IQ2 n-max=2, 27B-dense/35B-A3B n-max=4) and batching interacts with spec-dec **architecture-dependently** — the "don't batch long-context" rule is 122B-IQ2-specific, not generic MoE |
| [MoE Optimization](moe-optimization.md) | 37 | Reasoning ∝ ACTIVE FLOPs, knowledge ∝ TOTAL params; GLM-5.2 routing is near-uniform (top_32=15%) so generic hot-expert offload/REAP is not justified; IQ2 GPU residency is two-for-two viable but caps at ~122B |
| [KV Cache](kv-cache.md) | 39 | StreamingLLM pre-v7 floor sweep failed the quality floor → no simple KV cluster admitted yet; per-token KV streaming over PCIe is an anti-pattern (7-14× slower than DDR5); GDN residents' O(1) KV make teleport KV-copy near-moot |
| [Quantization](quantization.md) | 33 | The architect's degenerate `\boxed{}` repetition loop tracks the MODEL not the quant (Q4 loops identically to IQ2 on the same item — 2-bit-EOS-damage hypothesis REFUTED); fenced CPU-Q4 arm tracks at-or-above GPU-IQ2 on hard reasoning, undercutting the case for a real IQ2 reasoning penalty |
| [Hardware Optimization](hardware-optimization.md) | 93+ | CPU decode is BW-exhausted but CPU *prefill* is an open compute-bound regime; v8 is frozen as `production-consolidated-v8`; E5 W0 scout (69/69 cells) shows 4×quarters beats any big-instance shape for EVERY production model, and cross-architecture GPU batching is architecture-dependent (small-MoE ≫ dense > large-MoE-IQ2, with the large-MoE arm uniquely collapsing at long context) |

## Serving & Systems

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [Inference Serving](inference-serving.md) | 61 | The v7-cutover quarters-only launch was ruled an accidental regression and the big+quarters lineup was restored same-day via a new additive, no-outage `--numa-mode both` promotion path; the WP-12 fleet layer flipped live and its case-10 gate found production within-role concurrency comes from 6-process OS fan-out, not a role-level semaphore (which resolves to `Semaphore(1)` for every role); within-role placement SM's live KV-migration path re-ratified on the restored lineup (fwd 6/rev 1, 0 aborts) |
| [Local Inference](local-inference.md) | 36 | v8 frozen as `production-consolidated-v8`; deployed-lane throughput table + living model-probe scoreboard (all observation-grade); MI210 fits everything but the 122B-Q4 architect and GLM-5.2 (238 GB) |
| [Chat Templates](chat-templates.md) | 2 | Per-family turn markers + when to use `/completion` (Qwen/gemma-3/Llama3) vs `/v1/chat/completions` (gemma-4 multi-channel) — checklist for onboarding new models without silent routing failures |

## Routing & Evaluation

| Article | Sources | Key Insight |
|---------|---------|-------------|
| [Cost-Aware Routing](cost-aware-routing.md) | 42+ | CoT scaffold-transplant falsified in both regimes; the reasoning-effort ladder got its first real measurements — the accuracy lever is the PROMPT (+32pp CoT-in-content), not native `<think>` (loses via a non-termination tail, fixable with a budget cap); `max_tokens` is a silent third quality axis (a ~57pp finished-vs-truncated swing measured) coupled to admission control via per-architecture KV/slot cost |
| [Routing Intelligence](routing-intelligence.md) | 67+ | RI-10 decision-ready but first packet is `hold_quality_unscored` (proxies favor enforce; factuality unscored); X-MAS learned route-mutation is live in enforce — first learned routing layer in production |
| [Benchmark Methodology](benchmark-methodology.md) | 94+ | Architect model-selection bench reached a well-powered, scorer-corrected NULL across 7 measurements (A1≈A3≈A4, quality-tied); a stale extractor nearly manufactured a false-significant result (R7), triggering a fragmentation audit that found ~10+ duplicated scoring implementations stack-wide, one on the autopilot RL reward path (unaudited, high risk) |

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
| [Multimodal](multimodal.md) | 42+ | Benchmark deployed Qwen-VL field-placement before adding LocateAnything; Gemma 4 stays benchmark-first, not model-card-dismissed; the MiniCPM-o `vision_escalation` cutover now has a deterministic, model-agnostic promotion/rollback runbook, and `worker_vision` quartering has a quantitative demand/capability trigger gate replacing an unmeasured "in principle" |
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
