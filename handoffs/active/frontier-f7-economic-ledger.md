# Frontier F7 — The Economic Ledger

**Status**: SPEC'D, not started (created from the Fable 5 strategic-frontiers review)
**Created**: 2026-06-12
**Priority**: LOW-MED — piggybacks existing logs
**Spec**: [fable5-findings-07-strategic-frontiers.md](fable5-findings-07-strategic-frontiers.md) §F7 — read before claiming
**Related**: [fable5-findings-04-impl-plan.md](fable5-findings-04-impl-plan.md) (digest wiring); `scripts/autopilot/digest.py`

## Why

The autopilot optimizes local quality×speed, but the lab's real costs are
operator-minutes and cloud-API dollars per decision. The out-of-credits halt was
an economic event the system couldn't see coming. The ledger also quantifies
F2/F3 ROI — e.g. "planner cloud spend X/month" prices the planner-distill project.
All inputs already exist in logs; this is aggregation, not new instrumentation.

## Waypoints

- [ ] **W1 — ledger script** (1 day): `scripts/economics/ledger.py` — weekly aggregates: cloud spend by purpose from `planner_archive.jsonl` cost/duration fields (claude CLI reports cost; codex via account export or manual entry into `orchestration/cloud_costs.yaml`); local inference-hours by consumer (sum `eval_wall_s` by trial type, campaign windows from progress logs); operator decision throughput (gated-row state changes + halt→resume latencies from journal/state timestamps). Acceptance: one weekly report generated from real logs.
- [ ] **W2 — digest wiring** (half day): 5-line economics section in the existing daily digest (`scripts/autopilot/digest.py`). Acceptance: section appears in nightly digest.
- [ ] **W3 — standing decision rules** (reviewed monthly): planner cloud spend > threshold ⇒ raise F3-W3a (planner-distill) priority; median operator gate-latency > 3 days ⇒ invest in the decision-queue surface (prepared-evidence one-click approvals; e-value verdict blocks are the template). Acceptance: rules documented + first monthly review logged.

## Gates & pitfalls

- Codex costs may not be programmatically available — plan for manual monthly entry into `orchestration/cloud_costs.yaml`; don't block W1 on automation.
- Cost fields in `planner_archive.jsonl` only cover archived calls — confirm failed-call archiving (F3-W1a controller_io.py patch) before trusting cloud-spend totals.
- These are reporting numbers feeding monthly decisions — label estimation method per MEASUREMENT.md; no false precision.
- Keep it small: aggregation over existing logs only; no new telemetry services.

## Reporting

Tick waypoints here, update master index row, one-line progress entry on each landing. Move to `completed/` once W3's first monthly review runs.
