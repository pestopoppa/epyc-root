# Browser Agent Surface — interactive, goal-driven web actions

**Status**: stub (dormant until the operator decides EPYC wants an interactive browser surface)
**Created**: 2026-09-19 (via research intake, operator-approved 2026-09-19)
**Categories**: agent_architecture, tool_implementation
**Parent index**: [user-facing-harness-index.md](user-facing-harness-index.md) (UFH-10)

## Objective

Keep a ready design reference for a local browser agent that completes goals by interacting with pages
(click / type / select / scroll), built on the orchestrator's typed-decision plane rather than on a hosted
decision model, should EPYC decide it wants that surface.

Scope boundary: [searxng-search-backend.md](searxng-search-backend.md) owns *read-only* web retrieval
(SearXNG → Crawl4AI → Camofox as last-resort full browser, CA-6). This handoff covers *interactive*
goal-driven browsing, which nothing else owns.

## Research Context

| Intake ID | Title | Relevance | Verdict | Verification |
|-----------|-------|-----------|---------|--------------|
| intake-1493 | Jev Ultrafast — browser agent with a dynamic indexed action space | high | adopt_patterns | dive-verified |
| intake-1494 | Browser Harness — CDP harness + MCP server | low | worth_investigating | stage1-unverified |
| intake-524 | camofox-browser — stealth headless browser REST API (read path, CA-6) | — | — | see entry |

## Design reference (from the intake-1493 dive)

- Action space rebuilt each step from one atomic DOM snapshot, as an indexed element table. The model picks an
  index, never a selector, coordinate or code; the executor re-checks freshness and occlusion before input.
- One typed call per step: operation plus speculative per-operation target heads, consuming only the matching
  head. The local mechanism is [typed-decision-plane.md](typed-decision-plane.md) TD-12..TD-15.
- A generative model only for free-text fields, with strict single-key JSON output.
- Never retry a mutation. Log execution before re-observing. Independent outcome verification, because DONE is
  not proof of success.

## Open Questions

- Which EPYC workflow would need interactive browsing that search + Crawl4AI + Camofox cannot serve?
- Browser runtime on the shared host: Camofox (already planned for CA-6) vs a CDP harness. browser-harness
  ships opt-out telemetry that must be disabled (intake-1494, unverified).
- Can the typed-decision native path carry element tables of 100+ candidates (TD-15)?

## Notes

Dormant by design. The first task is an operator decision: name a workflow that needs this surface. Until then,
TD-12..TD-15 advance the reusable mechanism under the typed-decision plane.
