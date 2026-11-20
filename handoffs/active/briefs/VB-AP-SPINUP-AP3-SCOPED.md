---
schema: epyc.brief.v1
id: VB-AP-SPINUP-AP3-SCOPED
box_text_sha: 9c5a006336d14c7c
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:orchestration/instrument_eras.yaml
- epyc-root:scripts/vidya/ingest_sources.py
approach: 'Write-side wiring for: set `AUTOPILOT_AP3_ROLE_RESTART_ENABLE=scoped` in the autopilot spin-up environment (operator
  DP-4 = A, 2026-10-21). Land the source adapter/producer hook (existing carrier, claim_tuple.grade(), no new ladder; Source
  in ingest_sources.py + README row) with a synthetic-fixture test and refusal controls. Box done-when (live, operational,
  verified after): the started daemon''s /proc environ shows the scoped value, the clone is at origin/main, the strategy store
  check is recorded and the drift reasons are acknowledged; then VB-AP-FIRST-CYCLE.

  '
acceptance: python3 -m pytest -q tests/vidya/test_vb_ap_spinup_ap3_scoped_wire.py
new_tests:
- tests/vidya/test_vb_ap_spinup_ap3_scoped_wire.py
non_goals:
- no retrospective measurement warrant
- no new grading ladder
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:orchestration/instrument_eras.yaml: 8c364783fdd41dd2fbb21b135754d72d11123725
    epyc-root:scripts/vidya/ingest_sources.py: d2da53a6a45f78f20c2426ff20bb4b15cfbdad61
---
