# Non-Inference Backlog — Tasks Actionable Without Compute

**Status**: active
**Created**: 2026-04-11 (consolidated from audit of near-complete and active handoffs)
**Updated**: 2026-04-11
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
| 2 | REPL turn efficiency S3a→S4 | [repl-turn-efficiency.md](repl-turn-efficiency.md) | epyc-orchestrator | S3a contextual suggestions prototype (feature-flagged, gate on Omega improvement) is the prerequisite for S4 A/B benchmark | ~4h |
| 3 | Hermes outer shell Phase 2 completion | [hermes-outer-shell.md](hermes-outer-shell.md) | epyc-root | Phase 2 near-complete: skills done, streaming validated (Package E). Auth deferred. Remaining: E2E test of `x_disable_repl` + `x_max_escalation` with full graph (needs LG Phase 3 + inference). | ~2h |
| 4 | Dynamic stack Phase E design | [dynamic-stack-concurrency.md](dynamic-stack-concurrency.md) | epyc-orchestrator | Autoresearch exploration integration — design + code for autopilot stack assembly | ~4h |
| 5 | Tool output compression monitoring | [tool-output-compression.md](tool-output-compression.md) | epyc-orchestrator | Production monitoring setup: dashboards for compression ratios, quality impact tracking | ~2h |
| 6 | LangGraph Phase 3 flag flips | [bulk-inference-campaign.md](bulk-inference-campaign.md) Package D | epyc-orchestrator | Per-node ORCHESTRATOR_LANGGRAPH_* flag flip + production validation. No inference needed — uses existing production traffic. Start with INGEST. | ~2h |

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
