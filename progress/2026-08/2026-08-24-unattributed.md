# 2026-08-24 — opencode ad-hoc session (ROUTE-A1 execution + seam verification + Step-2 evidence)

**Agent**: opencode (ad-hoc, no lane; log shard `logs/agent_audit-unattributed.log`, session
`ses_20260824_064827_1739749`). Continuation of the 2026-08-23 tier-1 session (see
`2026-08-23-unattributed.md`).

## Mandate

Operator-approved: (1) execute ROUTE-A1 step-2 smoke; (2) OP-21 decision-grade re-measure;
(3) seam mechanism exercise (c); (4) standing smoke restatement (b); (5) wrap-up.

## What happened

### ROUTE-A1 step-2 smoke EXECUTED (06:48Z, operator grant) — premise falsified, then explained

- Anchor-hold mechanism discovery: direct-port and queue-path requests do NOT acquire the anchor's
  region locks; the sanctioned mechanism is `region-lock run --regions q0,q1 --role <role> -- <cmd>`
  (region_lock_cli.py — the bench-side wrapper). Queue-path forced requests dispatch WITHOUT
  acquiring locks at all.
- Smoke: **smoke_pass=false, 3/8** — all 3 disjoint admit-expected probes ADMITTED correctly;
  **0/5 overlapping queue-expected queued**. Measured why: the placement machine RE-PLACES forced
  eval_batch requests onto the disjoint instance (`candidate_topology_idx=2` observed, reason
  "all pairs + n-way allow" — frontdoor+ingest pair is borderline → gate-allow). Both shape-aware
  flags are ON in the live API (launcher setdefault since 2026-07-06); `seam_admit` wired and
  live-reachable.

### OP-21 decision-grade attempt — gate physically unreachable

- bench-nway n=12 (overlap 8080+8185): ratio 1.198, cv 0.1044 (CV_HIGH).
- **Pooled n=21 across all three runs: mean 1.165, cv 0.118, range 0.871-1.475** — the 0.05 CV
  gate cannot be met for this pair class under live-fleet variance (MTP+SSM co-run scheduling
  noise). Matrix row (1.121 borderline) stands within noise; no change. A decision-grade number
  would need a protocol variance allowance (measurement-constitution question).

### (b) standing smoke restated — DONE (53 tests green)

`--expectation {replacement|seam}` (default `replacement`): every candidate expected to
re-place + admit; the smoke judges the OBSERVED placement — `admit_overlap` (echoed
candidate_topology_idx overlapping the anchor) is ALWAYS a failure marked `CO-PLACEMENT`;
`queued_unexpected` is a distinct failure (fires if the seam arms under the standing expectation).
`seam` mode preserves the original model byte-compatibly (replays 08-24 as 3/8 exactly).
Orchestrator `f4bf975c`.

### (c) seam exercise — VERIFIED (clean-window re-run, operator grant)

- Control: no holds → forced frontdoor admits in 1.4s (allow, idx 0).
- With q0,q1 (ingest anchor) + q2,q3 (frontdoor busy) held: all three forced probes (frontdoor,
  worker_general, ingest) → **504 at exactly the 45s queue budget** with explicit attribution:
  `error_detail="[ERROR: placement timeout role=frontdoor reason=placement_topology_overlap_timeout
  holders=[0, 2] after 45.0s]"`.
- **Complete fleet-layer overlap behavior now measured**: disjoint instances exist → re-placement;
  re-placement impossible → seam REFUSES (fail-closed queue). **The never-co-place invariant holds
  at the gate level.** Cosmetic note: ingest probe error_detail echoed `role=worker_general`
  (stale var — one-line fix candidate).

## Records

- Ledger rows: ROUTE-A1-…-executed (DONE_PASS), OP21-overlap-decisiongrade (DONE_PASS),
  ROUTE-A1-seam-verify-…-cleanwindow (DONE_PASS).
- Handoff: shape-keyed-contention-gating.md APPEND 2026-08-24 (cont.) — full evidence; RTG-35 row
  → "Step-2 flag-on decision (operator): seam refusal + re-placement both verified — evidence
  complete".
- Commits: epyc-orchestrator `33888143` (smoke artifact), `f4bf975c` (restated smoke + n=12
  artifact); epyc-root `c9121e7f` (seam verification record) — all pushed.
- Host: all my processes stopped, all region-lock holds released (verified `held: {}`); host
  returned after the operator's CPU-availability note (a parallel session's GPU-stack teardown was
  unrelated).

## Open (named, not deferred)

- Step-2 flag-on decision (operator): evidence complete — re-placement + seam refusal verified.
- Cosmetic: stale `role=` echo in the seam timeout error detail (one-line fix).
- OP-21 decision-grade: unreachable at the protocol's CV gate without a variance allowance
  (measurement-constitution question if ever needed).
