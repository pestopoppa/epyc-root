# Routing, Autopilot & Stack — Active Backlog

**Purpose**: dispatch. Orchestrator, registry, stack lifecycle, autopilot, fleet coordination.

**Row contract** — one row per handoff, exactly one index owns each handoff. `Next action` is a single imperative line (≤140 chars) seeded from the handoff's own first open task; **status, evidence and history do not belong in rows** — status is generated into [`master-handoff-index.md`](master-handoff-index.md) and detail lives in `handoffs/active/.index-state.json`. Contract: [`handoff-index-authoring.md`](../../docs/guides/agent-workflows/handoff-index-authoring.md).

**History**: superseded narration for this index lives in [`../archived/routing-and-optimization-index-history-through-2026-08-10.md`](../archived/routing-and-optimization-index-history-through-2026-08-10.md).

**IDs are stable.** `RTG-NN` is a durable handle — cite it instead of a line number, and never reuse a retired one.

| ID | Track | Handoff | Next action | Deps |
|----|-------|---------|-------------|------|
| RTG-02 | autopilot continuous optimization | [autopilot-program.md](autopilot-program.md) | Prospectively capture menus, model/decoding identity, holdout and paired continuations; rerun sealed replay | — |
| RTG-07 | contention model device and load axes rider | [contention-model-device-and-load-axes-rider.md](contention-model-device-and-load-axes-rider.md) | Parameterize Artifact 2 capacity/VRAM fit, then Artifact 3 interference cost; retain E5 as final calibration dependency | INF-45 |
| RTG-08 | context folding progressive | [context-and-token-economy.md](context-and-token-economy.md) | CF-L5 — Run the L5 single-sentence compression check only if it answers a live question; verdict vs L3: rejected, role-limited, or tune | — |
| RTG-09 | decision aware routing | [routing-program.md](routing-program.md) | Hold until autopilot trains on the swapped stack AND UFH-13 re-opens (2026-09-29); then unfreeze DAR-LAT, DAR-SPLIT-1 first | — |
| RTG-22 | non inference backlog | [engineering-hygiene-backlog.md](engineering-hygiene-backlog.md) | Land LOOP-10..12, disk LOOP-21..25 and LOOP-26/27 (no blocking Qs unattended, filing alarm); review NIB2-98; prove NIB2-102.b | — |
| RTG-30 | routing intelligence | [routing-intelligence.md](routing-intelligence.md) | RI-18c: verify review_gate/review_verdict null on a COMPLETED live /chat in a DS41 open window; RI-19 use_memrl off; RI-24 | UFH-01 |
| RTG-34 | session bus thin dispatcher | [coordination-and-churn-pipeline.md](coordination-and-churn-pipeline.md) | AIR-6 — deploy exact guarded source and require ordinary-work refusal; then resume live canaries | — |
| RTG-36 | stack change governance pipeline | [stack-lifecycle-program.md](stack-lifecycle-program.md) | OP-72 sign STACKCHG-HYGIENE, then SCG-PRIORS-WARM-b + DRAFT-SEL-2b; SCG-FASTPATH; SCG-TEST-ORDER | — |
| RTG-48 | coordinator role failure modes | [coordinator-role-failure-modes-and-refactor.md](coordinator-role-failure-modes-and-refactor.md) | R-7 — Assign a successor to retired namespace owner mainD; then reconcile the C49 references | RTG-34 |
| RTG-52 | loop owned fleet implementation | [loop-owned-fleet-implementation.md](loop-owned-fleet-implementation.md) | P4-1 — adjudicate the 7-day role-shrink gate; then P5-1 hook-surface trust-boundary analysis and P5-2 NL-only fixture | RTG-34, RTG-48 |
| RTG-58 | kv prefix fork and paged attention | [kv-cache-program.md](kv-cache-program.md) | Qualify P1 candidate correctness; complete chunk-KV integration and repair the KPF-64 family cohort | EVL-14, INF-65 |
| RTG-63 | backlog refactor 2026-11 | [backlog-refactor-2026-11.md](backlog-refactor-2026-11.md) | BRF-T1-0: reconcile the fold plan against origin/main and commit the ordered route-1a fold list | — |

## Cross-domain

Edges to other domains go in the `Deps` column as bare IDs (e.g. `RTG-12`). Do **not** add a second row for a handoff another index owns.

## Reporting

After changing any row: run `python3 scripts/handoffs/index_state.py` to refresh generated state, then `--check` before committing.
