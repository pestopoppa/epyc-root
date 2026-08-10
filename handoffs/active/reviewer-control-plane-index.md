# Reviewer Control Plane — Active Backlog

**Purpose**: dispatch. Reviewer roles, capability gates, control-plane policy.

**Row contract** — one row per handoff, exactly one index owns each handoff. `Next action` is a single imperative line (≤140 chars) seeded from the handoff's own first open task; **status, evidence and history do not belong in rows** — status is generated into [`master-handoff-index.md`](master-handoff-index.md) and detail lives in `handoffs/active/.index-state.json`. Contract: [`handoff-index-authoring.md`](../../docs/guides/agent-workflows/handoff-index-authoring.md).

**History**: superseded narration for this index lives in [`../archived/reviewer-control-plane-index-history-through-2026-08-10.md`](../archived/reviewer-control-plane-index-history-through-2026-08-10.md).

**IDs are stable.** `REV-NN` is a durable handle — cite it instead of a line number, and never reuse a retired one.

| ID | Track | Handoff | Next action | Deps |
|----|-------|---------|-------------|------|
| REV-01 | autopilot control plane integration | [autopilot-control-plane-integration.md](autopilot-control-plane-integration.md) | AP-3 — Classes 2/4 (spec-dec composition; per-role KV config): restart-scoped launch-arg knobs (--spec-type set, --spec-draft-n-max, tree w… | — |
| REV-02 | glm52 reviewer capability gates | [glm52-reviewer-capability-gates.md](glm52-reviewer-capability-gates.md) | GC-1a — Strict-IF / typed-emission claim-grade gate (P-REV-1): rerun on the approved claim-grade reviewer corpus/K-of-M protocol after the… | — |
| REV-03 | reviewer calibration accounting | [reviewer-calibration-accounting.md](reviewer-calibration-accounting.md) | RC-6a — operator PR + sign-off (human-amendment-only): land the drafted P-REV-1 blocks into MEASUREMENT.md §1/§2/§3 via PR-reviewed amendme… | — |
| REV-04 | reviewer decision plane | [reviewer-decision-plane.md](reviewer-decision-plane.md) | RD-12 — Per-decision latency_ms + token accounting in artifact + trace (feeds H-LB); tests incl. parse-failure fallback counting; 50-questi… | — |
| REV-05 | reviewer escalation and human gate policy | [reviewer-escalation-and-human-gate-policy.md](reviewer-escalation-and-human-gate-policy.md) | HG-1 — Threshold policy from H4/H5 reliability-by-confidence-bucket curves (per-domain). | — |
| REV-06 | reviewer latency and sampling budget | [reviewer-latency-and-sampling-budget.md](reviewer-latency-and-sampling-budget.md) | LB-1 — Reproduce + attribute the regression: which calls dominate (plan-review prompt count vs prompt length vs architect queueing) on the… | — |
| REV-07 | reviewer model ablations | [reviewer-model-ablations.md](reviewer-model-ablations.md) | RM-2 — Anchor arms (guaranteed confirmation-tier): A0 gates-only (objective-verifier floor); A1 self-review (status quo alias); A3 same-fam… | — |
| REV-08 | reviewer trace materialization | [reviewer-trace-materialization.md](reviewer-trace-materialization.md) | TM-8 — Coverage gate: % of review invocations producing trace rows over a 50-question replay — must be ~100% before H4 starts. Also verify… | — |
| REV-09 | reviewer typed artifacts | [reviewer-typed-artifacts.md](reviewer-typed-artifacts.md) | Adopt benchmrk's annotation envelope as the dual-gold schema. Its status:"invalid" decoys give us a negative-control axis we do not have an… | — |

## Cross-domain

Edges to other domains go in the `Deps` column as bare IDs (e.g. `RTG-12`). Do **not** add a second row for a handoff another index owns.

## Reporting

After changing any row: run `python3 scripts/handoffs/index_state.py` to refresh generated state, then `--check` before committing.
