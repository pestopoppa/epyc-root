# Routing, Autopilot & Stack — Active Backlog

**Purpose**: dispatch. Orchestrator, registry, stack lifecycle, autopilot, fleet coordination.

**Row contract** — one row per handoff, exactly one index owns each handoff. `Next action` is a single imperative line (≤140 chars) seeded from the handoff's own first open task; **status, evidence and history do not belong in rows** — status is generated into [`master-handoff-index.md`](master-handoff-index.md) and detail lives in `handoffs/active/.index-state.json`. Contract: [`handoff-index-authoring.md`](../../docs/guides/agent-workflows/handoff-index-authoring.md).

**History**: superseded narration for this index lives in [`../archived/routing-and-optimization-index-history-through-2026-08-10.md`](../archived/routing-and-optimization-index-history-through-2026-08-10.md).

**IDs are stable.** `RTG-NN` is a durable handle — cite it instead of a line number, and never reuse a retired one.

| ID | Track | Handoff | Next action | Deps |
|----|-------|---------|-------------|------|
| RTG-02 | autopilot continuous optimization | [autopilot-program.md](autopilot-program.md) | Decide selector-menu location (AP-DGM-PROV, rec. A); at hold-lift re-review AP-HOLD-RELEASE-REVIEW; new era via ratify script | — |
| RTG-08 | context folding progressive | [context-and-token-economy.md](context-and-token-economy.md) | Operator answers Enable decision (options A-D); build shadow flag; CTX-HO-1 and CTX-HO-3 are standalone | — |
| RTG-09 | decision aware routing | [routing-program.md](routing-program.md) | DAR-SPLIT-1 re-run on fresh snapshot, then RTG-DUR-1 baseline refresh; EG2 boundary in RTG-EG2-1 | — |
| RTG-22 | non inference backlog | [engineering-hygiene-backlog.md](engineering-hygiene-backlog.md) | Disk LOOP-21/22; host-run backup BK-1/2/4; prove NIB2-102.b at next stack start; refactor after promotion + AutoPilot | — |
| RTG-34 | session bus thin dispatcher | [coordination-and-churn-pipeline.md](coordination-and-churn-pipeline.md) | Screen the 32 open boxes; decide AUD-15 and bus-file untracking; finish DASH-FU-1 | — |
| RTG-100 | churn pipeline | [churn-pipeline.md](churn-pipeline.md) | Fix CHURN-UP-NO-DISPATCHER, then OBS-CHURN-UP and the per-row UNDERUSED action | RTG-34 |
| RTG-36 | stack change governance pipeline | [stack-lifecycle-program.md](stack-lifecycle-program.md) | OP-72 sign STACKCHG-HYGIENE, then SCG-PRIORS-WARM-b + DRAFT-SEL-2b; SCG-FASTPATH; SCG-TEST-ORDER | — |
| RTG-58 | kv prefix fork and paged attention | [kv-cache-program.md](kv-cache-program.md) | Qualify P1 candidate correctness; complete chunk-KV integration and repair the KPF-64 family cohort | EVL-14, INF-65 |
| EVL-10 | episodic memory integrity | [memory-program.md](memory-program.md) | Write M-12f scoring-validity note (absorbs M-12i; model-free); next re-embed is EG2 swap with EPD-3 folded | — |

## Cross-domain

Edges to other domains go in the `Deps` column as bare IDs (e.g. `RTG-12`). Do **not** add a second row for a handoff another index owns.

## Reporting

After changing any row: run `python3 scripts/handoffs/index_state.py` to refresh generated state, then `--check` before committing.
