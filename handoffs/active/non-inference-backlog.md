# Non-Inference Backlog — Tasks Actionable Without Compute

**Status**: active
**Created**: 2026-04-11 (consolidated from audit of near-complete and active handoffs)
**Updated**: 2026-04-11 (tasks 2/5/6 completed)
**Priority**: MEDIUM
**Purpose**: Index of all remaining tasks across active handoffs that do NOT require model servers / inference compute. Can be tackled while compute is unavailable or occupied by bulk-inference-campaign Package D.

> **Notes**:
> - Claude Code integration Phase 1 removed (2026-04-11) — superseded by Hermes outer shell. See [claude-code-local-constellation-routing.md](claude-code-local-constellation-routing.md).
> - Root-archetype upstream tasks (linter testing, init-project.sh, README) removed — those are root-archetype repo work, not epyc-root. Tracked in [root-archetype-linter-templates-upstream.md](root-archetype-linter-templates-upstream.md).

---

## Task List (ordered by estimated impact)

### P0 — High impact, low effort

| # | Task | Source Handoff | Target Repo | Description | Effort |
|---|------|---------------|-------------|-------------|--------|
| ~~1~~ | ~~Brevity prompt upgrade (Action 12)~~ | ~~[reasoning-compression.md](reasoning-compression.md)~~ | ~~epyc-orchestrator~~ | ✅ DONE (Actions 12-15 complete, TALE eval done 2026-04-11). Static limits kept, TALE deferred. | — |

### P1 — Medium impact

| # | Task | Source Handoff | Target Repo | Description | Effort |
|---|------|---------------|-------------|-------------|--------|
| ~~2~~ | ~~REPL turn efficiency S3a~~ | ~~[repl-turn-efficiency.md](repl-turn-efficiency.md)~~ | ~~epyc-orchestrator~~ | ✅ DONE (2026-04-11). S3a contextual suggestions prototype implemented (`suggestions.py`, `_SuggestionsMixin`, 17 tests). Feature flag: `REPL_SUGGESTIONS` (default OFF). S4 A/B benchmark still needs inference. | — |
| 3 | Hermes outer shell Phase 2 completion | [hermes-outer-shell.md](hermes-outer-shell.md) | epyc-root | Phase 2 near-complete: skills done, streaming validated (Package E). Auth deferred. Remaining: E2E test of `x_disable_repl` + `x_max_escalation` with full graph (needs inference). LG Phase 3 now complete — escalation cap enforcement unblocked. | ~2h |
| ~~4~~ | ~~Dynamic stack Phase E design~~ | ~~[dynamic-stack-concurrency.md](dynamic-stack-concurrency.md)~~ | ~~epyc-orchestrator~~ | ✅ DONE (2026-04-11). DS-6 QuarterScheduler (health monitor, burst drain, idle tracking) + DS-7 stack templates (schema, loader, validator, default.yaml, --stack-profile CLI). 26 tests. Phase E autoresearch integration awaiting AR-3 results. | — |
| ~~5~~ | ~~Tool output compression monitoring~~ | ~~[tool-output-compression.md](tool-output-compression.md)~~ | ~~epyc-orchestrator~~ | ✅ DONE (2026-04-11). Compression metrics wired into TaskState, helpers.py, diagnostic JSONL, API response, seeding harness. Analysis script: `scripts/analysis/compression_stats.py`. | — |
| ~~6~~ | ~~LangGraph Phase 3 flag flips~~ | ~~[bulk-inference-campaign.md](bulk-inference-campaign.md)~~ | ~~epyc-orchestrator~~ | ✅ DONE (2026-04-11). All 7 per-node flags enabled in `orchestrator_stack.py`. Fixed append-field bug in `_run_via_langgraph` (role_history delta handling). 72 LG tests + 4495 unit tests pass. | — |

### P2 — Lower priority / future

| # | Task | Source Handoff | Target Repo | Description | Effort |
|---|------|---------------|-------------|-------------|--------|
| 7 | Meta-harness documentation | [meta-harness-optimization.md](meta-harness-optimization.md) | epyc-orchestrator | Document Tier 1 + Tier 2 implementation for AR-3 operator guide | ~2h |

---

## Completion Protocol

After completing any task:
1. Update the source handoff (checkbox + status)
2. Update this backlog (strikethrough completed items)
3. If the source handoff becomes fully complete, move it to `handoffs/completed/`
