# Context-Folding: Progressive Session Compaction Upgrade

**Status**: COMPACTED 2026-05-28 - core context-folding phases landed; active only for L5/Phase 3c validation and design probes.
**Created**: 2026-03-17
**Updated**: 2026-06-13
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

## Decision Record: CF-DD8 / NIB2-40

**Closed 2026-06-13**: do not add a separate context-folding implementation for Claude Code-style "budget reduction" right now. The concrete per-message cap surface found in the local docs is tool-output scoped, and EPYC already has explicit ownership there via [tool-output-compression.md](tool-output-compression.md): `truncate_output()` provides an 8192-character hard cap, `_spill_if_truncated()` limits visible previews and preserves full output by pointer, and the native compression layer sits before spill/truncation.

Layer mapping:

| Claude Code layer | EPYC owner / state | Decision |
|---|---|---|
| Budget reduction | [tool-output-compression.md](tool-output-compression.md) for tool outputs; REPL token-budget knobs for generation budgets | No new CF-owned cap. Keep caps/compression/spill in the tool-output lane. |
| Snip | Segment architecture can support surgical removal, but no live need is proven for a new `trim_segment(segment_id)` API | Evidence-gated follow-up only if CF-3c telemetry shows a single large segment or failed trace is poisoning summaries. |
| Microcompact | Native tool-output compression plus spill/peek | Existing owner; sequence Phase 3d anti-thrashing before CF-3c tuning. |
| Context collapse | L4 two-level condensation / consolidated summaries | Covered; L5 validation remains the only aggressive-compression question. |
| Auto-compact | Threshold-triggered session compaction | Covered; live quality validation remains open. |

Reopen criteria: only promote new context-folding code if clean live telemetry shows context loss from non-tool session history that tool-output compression cannot address, or if `CompactionQualityMonitor` flags recurring reference misses caused by one removable segment class. In that case, prefer a narrow surgical-snip API over another global per-message cap.

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
| CF-DD8 / NIB2-40 gap analysis | Done; no separate context-folding per-message cap. Tool-output budget reduction stays in the tool-output-compression lane; surgical snip is telemetry-gated. | This file, decision record above. |

## Key Files

- `/mnt/raid0/llm/epyc-orchestrator/src/graph/session_log.py`
- `/mnt/raid0/llm/epyc-orchestrator/src/graph/session_summary.py`
- `/mnt/raid0/llm/epyc-inference-research/scripts/benchmark/`
- [tool-output-compression.md](tool-output-compression.md)
- [routing-intelligence.md](routing-intelligence.md)
- [non-inference-backlog.md](non-inference-backlog.md)

## Reporting Instructions

After any CF task, update this active handoff with command, dataset/log source, metric direction, result, and the fork decision. Update [routing-and-optimization-index.md](routing-and-optimization-index.md), [research-evaluation-index.md](research-evaluation-index.md), and [non-inference-backlog.md](non-inference-backlog.md) if task ownership or priority changes.
