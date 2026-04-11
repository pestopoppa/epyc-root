# EPYC Handoff — Master Index

**Updated**: 2026-04-11
**Purpose**: Single entry point for any agent. Read this to discover active work and where to start.

---

## Quick Start

| Working on... | Read this index |
|---------------|----------------|
| Routing, orchestration, autopilot, stack config | [routing-and-optimization-index.md](routing-and-optimization-index.md) |
| Inference speed, benchmarks, model acceleration | [inference-acceleration-index.md](inference-acceleration-index.md) |
| Agent UX, conversation management, frontend | [hermes-agent-index.md](hermes-agent-index.md) |
| Pre-production research, evaluation, monitoring | [research-evaluation-index.md](research-evaluation-index.md) |
| New capability pipelines (vision, PDF, Lean, TTS) | [pipeline-integration-index.md](pipeline-integration-index.md) |
| Evaluating model candidates | See **Standalone Handoffs** below |
| Don't know where to start | See **Priority Queue** below |

---

## Priority Queue

Highest-impact work across all domains. Each item points to where the details live.

| # | Priority | Item | Index / Handoff |
|---|----------|------|----------------|
| 0 | ~~HIGH~~ | ~~llama.cpp v3~~ ✅ binary swapped 2026-04-10 (coder +101%, REAP +50%). Deferred: PPL, paged attn RSS, NUMA tests | [llama-cpp-v3-upstream-rebuild.md](llama-cpp-v3-upstream-rebuild.md) |
| 1 | HIGH | AR-3 relaunch (expand T0 sentinels, safety-hardened) | [routing-and-optimization-index](routing-and-optimization-index.md) P5 |
| 2 | ~~HIGH~~ | ~~Context folding Phase 1~~ ✅ 2026-04-04 | [routing-and-optimization-index](routing-and-optimization-index.md) CF Phase 1 |
| 2a | ~~MED~~ | ~~CF Phase 1+/2c/3a/3b~~ ✅ 2026-04-05 (code complete, 4 feature flags, 32 tests). Phase 2c ByteRover enhancement designed (intake-267). | [routing-and-optimization-index](routing-and-optimization-index.md) CF |
| 2b | MED | CF Phase 2a/2b eval + Phase 3c quality monitor (need inference) → Package C/D | [routing-and-optimization-index](routing-and-optimization-index.md) CF Phase 2 |
| 3 | HIGH | RI-10–12 routing rollout (shadow → enforce) → Package D | [routing-and-optimization-index](routing-and-optimization-index.md) P6 |
| 4 | ~~HIGH~~ | ~~B1/B2/B3/B5/B6/B7 conversation management~~ ✅ 2026-04-05 (6 modules, 99 tests, 4 feature flags) | [hermes-agent-index](hermes-agent-index.md) P0 |
| 4a | ~~MED~~ | ~~Brevity prompt upgrade~~ ✅ Actions 12-15 done, TALE eval 2026-04-11 (static limits kept) | [research-evaluation-index](research-evaluation-index.md) P0.5 |
| 5 | ~~MED~~ | ~~TrimR deployment~~ Package B ✅ 2026-04-10 (thinking +6pp GPQA, tool A/B +4pp, WS-3 validated) | [research-evaluation-index](research-evaluation-index.md) P0 |
| 6 | ~~MED~~ | ~~Tool output compression~~ Phase 2 native ✅ 2026-04-05, A/B ✅ 2026-04-10 (+4pp REPL, suite-dependent) | [research-evaluation-index](research-evaluation-index.md) P1 |
| 7 | MED | OpenDataLoader PDF integration | [pipeline-integration-index](pipeline-integration-index.md) P1 |
| 8 | ~~MED~~ | ~~CC local integration~~ Phase 0 ✅ 2026-04-05. Phases 1-3 **demoted to stub** 2026-04-11 — superseded by Hermes outer shell | [claude-code-local-constellation-routing.md](claude-code-local-constellation-routing.md) |
| 9 | LOW | Multimodal vision live validation | [pipeline-integration-index](pipeline-integration-index.md) P0 |
| 10 | LOW | Hermes outer shell Phase 2 (routing API done, skills done, streaming validated. Auth deferred.) | [hermes-agent-index](hermes-agent-index.md) P2 |

---

## Domain Indices

| Domain | Index | Handoffs | Status |
|--------|-------|----------|--------|
| Routing & Optimization | [routing-and-optimization-index.md](routing-and-optimization-index.md) | 11 | P0-P4 complete, P5 AR-3 running (trial ~78), P6 RI-10 canary active (to 2026-04-15), P7-P9 pending |
| Inference Acceleration | [inference-acceleration-index.md](inference-acceleration-index.md) | 3 active + completed | KV quantization COMPLETED (moved), KV selection eval phase, **v3 PRODUCTION** (binary swapped 2026-04-10), GPU acceleration path (stub — future) |
| Agent Integration | [hermes-agent-index.md](hermes-agent-index.md) | 3 | B1-B7 ALL COMPLETE + integration wired, shell low priority |
| Research & Evaluation | [research-evaluation-index.md](research-evaluation-index.md) | 7 | tool-compression A/B done (+4pp), REPL S1-S2 done (S3a next), reasoning Actions 12-15 done, eval datasets COMPLETED (moved), KB governance COMPLETED (moved), upstream in-progress |
| Pipeline Integration | [pipeline-integration-index.md](pipeline-integration-index.md) | 4 | vision done, TTS blocked, PDF/Lean pending |

---

## Standalone Handoffs

Not covered by any sub-index. Small, focused, or cross-cutting.

| Handoff | Domain | Status | Priority | Last Updated |
|---------|--------|--------|----------|-------------|
| [colbert-reranker-web-research.md](colbert-reranker-web-research.md) | web_research pipeline | stub | LOW | 2026-04-05 |
| [mathsmith-hc-formalizer-eval.md](mathsmith-hc-formalizer-eval.md) | Formal verification | stub (S1 done) | LOW | 2026-04-05 |
| [bulk-inference-campaign.md](bulk-inference-campaign.md) | Cross-cutting eval | active (A-C+E+F done, D running — AR-3 trial ~78, RI-10 canary to 2026-04-15) | HIGH | 2026-04-11 |
| [non-inference-backlog.md](non-inference-backlog.md) | Cross-cutting code tasks | active (7 tasks, no compute needed) | MEDIUM | 2026-04-11 |
| [triattention-kv-selection.md](triattention-kv-selection.md) | KV cache selection/eviction | ACTIVE (inference tasks → bulk-inference G2/G3) | MEDIUM | 2026-04-08 |
| [memento-block-reasoning-compression.md](memento-block-reasoning-compression.md) | Block reasoning KV masking | ACTIVE (inference tasks → bulk-inference G1) | HIGH | 2026-04-09 |
| [gpu-acceleration-path.md](gpu-acceleration-path.md) | Hardware acceleration | stub (activates on GPU acquisition) | LOW | 2026-04-10 |

---

## Cross-Index Dependencies

Changes in one domain often affect others. Key coupling points:

| Source | Affects | Mechanism |
|--------|---------|-----------|
| Inference acceleration (benchmarks) | Routing & optimization (baselines) | Model speed/quality data feeds Q-scorer baselines and stack config |
| Research (reasoning compression) | Routing (difficulty signal) | `difficulty_signal.py` shared between reasoning token budgets and routing |
| Research (tool output compression) | Routing (context folding) | Upstream token reduction changes context compaction frequency |
| Hermes (B2 context compression) | Routing (context folding Phase 1) | Must sequence B2 after Phase 1 — both modify compaction |
| Routing (AR-3 autoresearch) | Routing (meta-harness) | Meta-harness Tier 1+2 validated via AR-3 autopilot runs |
| Pipeline (new models) | Routing (NUMA allocation) | Each pipeline model competes for RAM/quarters with production stack |
| Bulk inference campaign (B-E) | All 5 domains | 14 tasks → 4 optimized runs; produces data unblocking routing, research, pipeline work |
| Research (KB governance) | Root-archetype (KB linter) | KB linter + skill templates upstreamed to root-archetype; epyc-root deploys instance-specific version |
| GPU hardware acquisition | Inference acceleration, Routing (NUMA allocation) | gpu-acceleration-path.md: CPU+GPU hybrid MoE changes expert routing, NUMA quarter allocation, and v3 build flags |

---

## Freshness Protocol

| Age | Marker | Action |
|-----|--------|--------|
| < 14 days | current | None |
| 14-30 days | aging | Review if still active |
| > 30 days | **STALE** | Verify status, update or archive |

Run `scripts/validate/check_handoff_freshness.sh` to check all handoffs.

After completing work on any handoff:
1. Update the handoff document
2. Update the relevant sub-index (checkbox + status)
3. If priority queue items complete, update this master index
4. Add entry to `progress/YYYY-MM/YYYY-MM-DD.md`
