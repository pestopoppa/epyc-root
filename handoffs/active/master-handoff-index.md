# EPYC Handoff — Master Index

**Updated**: 2026-04-05
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
| 1 | HIGH | AR-3 relaunch (expand T0 sentinels, safety-hardened) | [routing-and-optimization-index](routing-and-optimization-index.md) P5 |
| 2 | ~~HIGH~~ | ~~Context folding Phase 1~~ ✅ 2026-04-04 | [routing-and-optimization-index](routing-and-optimization-index.md) CF Phase 1 |
| 2a | MED | Context folding Phase 1+/2/3 (segment dedup, helpfulness scoring, role-aware compaction) | [routing-and-optimization-index](routing-and-optimization-index.md) CF Phase 2 |
| 3 | HIGH | RI-10–12 routing rollout (shadow → enforce) | [routing-and-optimization-index](routing-and-optimization-index.md) P6 |
| 4 | HIGH | B1 user modeling + B2 context compression | [hermes-agent-index](hermes-agent-index.md) P0 |
| 5 | MED | TrimR deployment (reasoning compression Tier 1) | [research-evaluation-index](research-evaluation-index.md) P0 |
| 6 | MED | RTK / tool output compression evaluation | [research-evaluation-index](research-evaluation-index.md) P1 |
| 7 | MED | OpenDataLoader PDF integration | [pipeline-integration-index](pipeline-integration-index.md) P1 |
| 8 | MED | CC local integration (READY TO IMPLEMENT) | [routing-and-optimization-index](routing-and-optimization-index.md) subsystem table |
| 9 | LOW | Multimodal vision live validation | [pipeline-integration-index](pipeline-integration-index.md) P0 |
| 10 | LOW | Hermes outer shell Phase 2 | [hermes-agent-index](hermes-agent-index.md) P2 |

---

## Domain Indices

| Domain | Index | Handoffs | Status |
|--------|-------|----------|--------|
| Routing & Optimization | [routing-and-optimization-index.md](routing-and-optimization-index.md) | 11 | P0-P4 complete, P5 AR-3 active, P6-P9 pending |
| Inference Acceleration | [inference-acceleration-index.md](inference-acceleration-index.md) | 2 active + archived | Most work complete, monitoring phase |
| Agent Integration | [hermes-agent-index.md](hermes-agent-index.md) | 3 | B1/B2 high priority, shell low priority |
| Research & Evaluation | [research-evaluation-index.md](research-evaluation-index.md) | 7 | reasoning-compression active, rest stubs/monitoring |
| Pipeline Integration | [pipeline-integration-index.md](pipeline-integration-index.md) | 4 | vision done, TTS blocked, PDF/Lean pending |

---

## Standalone Handoffs

Not covered by any sub-index. Small, focused, or cross-cutting.

| Handoff | Domain | Status | Priority | Last Updated |
|---------|--------|--------|----------|-------------|
| [02-nanbeige-3b-worker-eval.md](02-nanbeige-3b-worker-eval.md) | Model candidate | active | P0 | 2026-03-03 STALE |
| [04-mirothinker-worker-eval.md](04-mirothinker-worker-eval.md) | Model candidate | active (depends on #02) | P1 | 2026-03-20 |
| [mathsmith-hc-formalizer-eval.md](mathsmith-hc-formalizer-eval.md) | Formal verification | stub | LOW | 2026-03-29 |

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
