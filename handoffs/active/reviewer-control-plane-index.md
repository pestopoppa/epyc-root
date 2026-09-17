# Reviewer Control Plane — Active Backlog

**Purpose**: dispatch. Reviewer roles, capability gates, control-plane policy.

**Row contract** — one row per handoff, exactly one index owns each handoff. `Next action` is a single imperative line (≤140 chars) seeded from the handoff's own first open task; **status, evidence and history do not belong in rows** — status is generated into [`master-handoff-index.md`](master-handoff-index.md) and detail lives in `handoffs/active/.index-state.json`. Contract: [`handoff-index-authoring.md`](../../docs/guides/agent-workflows/handoff-index-authoring.md).

**History**: superseded narration for this index lives in [`../archived/reviewer-control-plane-index-history-through-2026-08-10.md`](../archived/reviewer-control-plane-index-history-through-2026-08-10.md).

**IDs are stable.** `REV-NN` is a durable handle — cite it instead of a line number, and never reuse a retired one.

| ID | Track | Handoff | Next action | Deps |
|----|-------|---------|-------------|------|
| REV-02 | glm52 reviewer capability gates | [glm52-reviewer-capability-gates.md](glm52-reviewer-capability-gates.md) | Re-derive GLM-5.3 kpool/top_k after INF-69 T2; use its CPU-validated experimental text/MTP port | INF-69 |
| REV-03 | reviewer calibration accounting | [reviewer-calibration-accounting.md](reviewer-calibration-accounting.md) | RC-6a — operator PR + sign-off: land the drafted P-REV-1 blocks into MEASUREMENT.md §1/§2/§3 with a one-line CHANGELOG | — |
| REV-05 | reviewer escalation and human gate policy | [reviewer-escalation-and-human-gate-policy.md](reviewer-escalation-and-human-gate-policy.md) | HG-1 — Threshold policy from H4/H5 reliability-by-confidence-bucket curves (per-domain). | UFH-01 |
| REV-06 | reviewer latency and sampling budget | [reviewer-latency-and-sampling-budget.md](reviewer-latency-and-sampling-budget.md) | LB-1 — Reproduce and attribute the review-latency regression on the RD-12 replay: prompt count vs prompt length vs architect queueing | — |
| REV-07 | reviewer model ablations | [reviewer-model-ablations.md](reviewer-model-ablations.md) | RM-2 — finish the anchor arms: A4g hot-expert offload (needs skew profile + GLM repair hypothesis) and the Ref external judge | REV-02 |
| REV-09 | reviewer typed artifacts | [reviewer-typed-artifacts.md](reviewer-typed-artifacts.md) | RA-13a — run the N=20 blind read-back pilot (harness built; inference-gated) | — |

## Cross-domain

Edges to other domains go in the `Deps` column as bare IDs (e.g. `RTG-12`). Do **not** add a second row for a handoff another index owns.

## Reporting

After changing any row: run `python3 scripts/handoffs/index_state.py` to refresh generated state, then `--check` before committing.
