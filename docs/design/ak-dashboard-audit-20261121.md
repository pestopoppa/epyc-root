# AutoKernel dashboard audit (2026-11-21)

Scope: the hub's Kernel R&D page `/loop` (`dashboard/static/loop.html`, registry id `autokernel-loop`), compared
with the handoff dashboard `/` (`handoffs.html` + its pipeline section). Trigger: AKPL P0-P6 landed offline.

## What an operator needs at a glance, and where `/loop` stands

| Need | `/loop` today | Handoff page equivalent |
|---|---|---|
| What is running now | Only the legacy single-process loop's step (`loop-status.json`, **25 days stale**). AK rows running under rowflow grants are invisible. | Sessions table + compute regions, live |
| Champion head + lineage | Good: champion vs frozen production headline, trajectory, capabilities | n/a |
| Keeps and drops | Dispositions/recent iterations exist but are legacy-loop only; rowflow-era AK verdicts (filing-done) are not shown | Board columns |
| What is blocked and why | Not shown (holds, open gates, refusal caps) | "Handoffs by what blocks them" |
| Decisions needed | Not shown; `akloop/decisions.py` (P6) has no surface | Operator decision queue in the index |
| Loop flow | No flowchart; the new parallel-loop shape (P2-P6) is not drawn anywhere | DET/AI flowchart with live counts |

## Readability findings

1. **Stale body dominates.** 14 sections render first from a dormant producer; the one live fact (AK rows moving
   through rowflow) is absent. Stale is bannered correctly, but nothing current replaces it.
2. **Jargon.** Ticket ids as headings/labels (R23-44, R24-8, R23-52b, AKX, "accumulator", "compound-then-gate",
   "serial target routing") with no gloss. Handoff page labels nodes in plain verbs.
3. **Density.** ~3k lines of page, every card expanded; no "start here" strip.
4. **Freshness.** Envelopes are per-card and honest (good), but there is no envelope for rowflow-era AK activity
   and no `/api/health` panel covering it.
5. **No DET vs LLM separation.** Which steps are code and which are an LLM is not visible; the design doc's split
   (planner/critic/author vs chain/gate/file) exists only in prose.

## Fixes (ranked)

1. **Add an "At a glance" strip at the top of `/loop`**: AK rows running / queued, candidates emitted, decisions
   needed (P6 detector, with each item), with its own freshness envelope. **Implemented.**
2. **Add the live parallel-loop flowchart** (DET boxes, AI dashed pills, reused pipeline styling), each node with
   count / in-flight / queued / last event / age, click for items. Data contract `epyc.akloop.flow.v1` in
   `scripts/coordination/akloop/flow_status.py` (plane rule), served at `/api/akflow`, probe `/api/akflow/health`,
   panel `akflow` in `dashboard/panels.py` (enters `/api/health`). **Implemented.**
3. **Mark the legacy-loop sections as legacy when stale** (one line under the strip naming the dormant producer
   and its age). **Implemented** (the strip says it; the cards keep their own banners).
4. Gloss or rename ticket-id headings (R23-44 etc.) in plain words. **Deferred**: touches many cards with their
   own tests; separate pass.
5. Collapse legacy-only cards (accumulator, serial routing, hotspots) under one `<details>` when the legacy
   producer is stale. **Deferred**: needs operator view on what stays visible by default.
