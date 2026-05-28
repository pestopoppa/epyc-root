# Context-Folding: Progressive Session Compaction Upgrade

**Status**: COMPACTED 2026-05-28 - core context-folding phases landed; active only for L5/Phase 3c validation and design probes.
**Created**: 2026-03-17
**Updated**: 2026-05-28
**Priority**: HIGH
**Categories**: context_management, session_compaction, rl_training_data
**Parent index**: [routing-and-optimization-index.md](routing-and-optimization-index.md), [research-evaluation-index.md](research-evaluation-index.md)
**Completed ledger**: [context-folding-progressive-completed-through-2026-05-28.md](../completed/context-folding-progressive-completed-through-2026-05-28.md)

## Executor Start Here

Do not reimplement Phases 0, 1, 1+, 2a, 2b L1-L4, 2c scaffolding, 3a, or 3b. The active question is whether the remaining aggressive-compression and monitoring probes justify new behavior beyond the already-landed multi-tier compaction stack.

## Outstanding Tasks

- [ ] **CF-L5 maximum-compression validation**: run the L5 single-sentence-per-segment compression check only if it answers a current production question. Compare against the known L3 sweet spot and record whether L5 is rejected, role-limited, or worth further tuning.
- [ ] **CF-3c live quality-monitor validation**: validate `CompactionQualityMonitor` on real traffic/telemetry. The class scaffold exists; tune degradation thresholds only after upstream-compressor anti-thrashing in [tool-output-compression.md](tool-output-compression.md) Phase 3d is accounted for.
- [ ] **CF-2c.0 / NIB2-43 dual-objective alpha sweep**: implement the task-success classifier or retrieval proxy, score existing summarizer outputs at alpha values `{0.0, 0.25, 0.5, 0.75, 1.0}`, and measure correlation with downstream task success.
- [ ] **CF-DD8 / NIB2-40 compaction-pipeline gap analysis**: compare Claude Code's five-layer pipeline against EPYC L1-L5 tiers and decide whether a per-message budget-reduction equivalent is warranted.

## Dependency Forks

| Outcome | Next action |
|---|---|
| L5 quality collapses or only helps non-coding roles | Keep L3 as the default sweet spot; document any role-specific exception. |
| L5 is competitive with L3 on target roles | Promote a narrow follow-up to tune L5 per role, gated by live monitor results. |
| CF-3c telemetry is noisy due to compress/uncompress oscillation | Sequence after [tool-output-compression.md](tool-output-compression.md) Phase 3d anti-thrashing work. |
| Alpha sweep shows alpha < 1.0 beats helpfulness-only by >2% | Promote the dual-objective score into the Phase 2b design variant. |
| Alpha sweep shows no signal | Park dual-objective compression until GPU/fine-tune capacity exists. |

## Completed Scope

| Scope | Result | Ledger |
|---|---|---|
| Phase 0 trigger threshold | Complete. | [completed ledger](../completed/context-folding-progressive-completed-through-2026-05-28.md) |
| Phase 1 two-level condensation | Complete. | [completed ledger](../completed/context-folding-progressive-completed-through-2026-05-28.md) |
| Phase 1+ segment cache/dedup | Code complete. | [completed ledger](../completed/context-folding-progressive-completed-through-2026-05-28.md) |
| Phase 2a summarizer eval | Done; 30B-A3B is minimum viable summarizer at 3.0/3.0. | [completed ledger](../completed/context-folding-progressive-completed-through-2026-05-28.md) |
| Phase 2b L1-L4 sweep | Done; L3 sweet spot recorded at 82% compression and 2.84/3 retention. | [completed ledger](../completed/context-folding-progressive-completed-through-2026-05-28.md) |
| Phase 2c/3a/3b code | Helpfulness scoring, process rewards, role-aware profiles, and monitor scaffold landed; live validation remains above. | [completed ledger](../completed/context-folding-progressive-completed-through-2026-05-28.md) |

## Key Files

- `/mnt/raid0/llm/epyc-orchestrator/src/graph/session_log.py`
- `/mnt/raid0/llm/epyc-orchestrator/src/graph/session_summary.py`
- `/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/`
- [tool-output-compression.md](tool-output-compression.md)
- [routing-intelligence.md](routing-intelligence.md)
- [non-inference-backlog.md](non-inference-backlog.md)

## Reporting Instructions

After any CF task, update this active handoff with command, dataset/log source, metric direction, result, and the fork decision. Update [routing-and-optimization-index.md](routing-and-optimization-index.md), [research-evaluation-index.md](research-evaluation-index.md), and [non-inference-backlog.md](non-inference-backlog.md) if task ownership or priority changes.
