# Dashboard freshness robustness — recurring "stale panel" resolution (2026-07-03)

Operator report: autopilot dashboard shows stale/inconsistent panel information
"every other day" — topology / cpu-region / lock / live-inference panels must be
consistent and robust. Approved a full 6-phase plan.

## Root cause (why it kept recurring)

The dashboard grew into ~15 independently-polled panels, each with ad-hoc (or
zero) freshness handling and no shared snapshot. Every past "stale panel"
incident got a point-fix; the structural gap was never closed, so a different
source desyncing each week always surfaced as "stale AGAIN". Two structural
holes: (1) no panel could report "this data is N s old" and no way to tell a
transport failure from a data stall; (2) correlated panels were fetched at
different instants from independent endpoints, so they contradicted each other.

Confirmed: the live web dashboard renders **all panels client-side as SVG/HTML
from JSON/SSE — zero server PNGs**. The `autopilot_plots/*.png` are a separate
docs/README artifact, NOT the dashboard.

## Delivered (Phases 0–4, all tested — 158 dashboard unit tests green)

- **`dashboard_freshness.py`** — pure freshness-envelope core: `fresh/aging/
  stale/dead`, gating-vs-informational sources (so an operator-curated matrix a
  week old doesn't flip a live panel to stale), transport-vs-data-stall
  distinction. 13 unit tests.
- **`dashboard_panels.py`** — central registry (SSOT) mapping every panel →
  endpoint → producer file(s) → thresholds. Path literals guarded against drift
  from dashboard.py by test.
- **8 panel endpoints stamped** with an additive `_freshness` envelope
  (topology, topology_activity, region_locks, contention, inference_tap,
  autopilot_progress, process_status, gepa).
- **Coherent snapshot (keystone)** — `/dashboard/api/snapshot` now embeds
  topology + region_locks + activity built in ONE call under one `generated_at`
  (via factored `_build_topology_nodes()` + a 3s TTL cache used only by the 2 Hz
  stream). The frontend drives the topology strip, lock grid, and activity
  overlay from this one object, so they can never reflect different instants —
  killing the "tap active beside 'no locks held'" class.
- **Frontend freshness badges** — uniform `renderFreshness()` badge on the named
  panels, ticked once/sec off the client clock so a panel that stops refreshing
  visibly ages into "stale" instead of silently showing old data. JS validated
  (node --check).
- **`/dashboard/api/health`** — folds every registered panel into one
  `ok|degraded` verdict + per-panel staleness. Anti-whack-a-mole guard: a dead
  producer now shows up loudly on curl/monitor. `test_dashboard_panels.py` (14
  tests) asserts every displayed panel has a registered source and vice-versa.

## Real bug the health check immediately caught (fixed)

`gepa` panel flagged **stale — journal 5.5 days old**. Root cause: the autopilot
rotated its journal at trial 999 → the live run (trial 1073) writes
`orchestration/autopilot_journal_1.jsonl`, but the dashboard read only the base
`autopilot_journal.jsonl` (frozen at trial 999, 2026-06-27). So the **gepa,
Pareto-frontier, and trial-progress panels had been showing 5-day-old trial-999
data** — a concrete instance of the operator's complaint. Fixed by
`_autopilot_journal_shards()`: the dashboard now reads base + all `_<n>`
rotations in trial order (matching `optimization_brief.DEFAULT_JOURNAL_PATHS`),
and the gepa freshness tracks the newest shard. Merged journal now reaches trial
1073; overall dashboard health went `degraded → ok`. 4 shard tests added.

This likely explains a chunk of the recurring "frozen frontier" reports.

## Remaining

- **Phase 5 (PNG/docs)** — reframed: the stale `docs/autopilot/*.png` (git-
  tracked, 2026-05-31 / orphan `objectives_2x2.png` from 2026-04-15 with no
  generator) are a **docs/README artifact, not the live dashboard**. Auto-
  syncing git-tracked binaries would churn history. Pending operator decision on
  scope + orphan fate.
- **Phase 6 (deploy)** — the Python endpoint changes need an orchestrator API
  restart (`uvicorn ... --workers 6`, pid 1143458); `dashboard.html` is hot-read.
  Restart is outward-facing (affects live autopilot eval dispatch) — pending
  operator go-ahead + timing.

## Files
- `epyc-orchestrator/src/api/routes/dashboard_freshness.py` (new)
- `epyc-orchestrator/src/api/routes/dashboard_panels.py` (new)
- `epyc-orchestrator/src/api/routes/dashboard.py` (envelope stamps, coherent
  snapshot, health endpoint, journal-shard resolver)
- `epyc-orchestrator/src/api/routes/dashboard.html` (freshness badges, strip-
  from-snapshot)
- `epyc-orchestrator/tests/unit/test_dashboard_freshness.py`,
  `test_dashboard_panels.py` (new)
