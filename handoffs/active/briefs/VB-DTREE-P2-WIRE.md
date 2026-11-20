---
schema: epyc.brief.v1
id: VB-DTREE-P2-WIRE
box_text_sha: 75f0c2ac3aa9a593
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:docs/reports/df2-dtree-27b-oracle-verdict-20261119.md
- epyc-root:scripts/vidya/ingest_sources.py
approach: 'Write-side wiring for: project prospective DTREE-P2 oracle/speed producer records through the existing measurement
  carrier and prove the planning-context canary. Land the source adapter/producer hook (existing carrier, claim_tuple.grade(),
  no new ladder; Source in ingest_sources.py + README row) with a synthetic-fixture test and refusal controls. Box has no
  code-level done-when; acceptance is the closest check.

  '
acceptance: python3 -m pytest -q tests/vidya/test_vb_dtree_p2_wire_wire.py
new_tests:
- tests/vidya/test_vb_dtree_p2_wire_wire.py
non_goals:
- no retrospective measurement warrant
- no new grading ladder
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:docs/reports/df2-dtree-27b-oracle-verdict-20261119.md: daf2f0880c028d0ef1b373488330273a2a38dc7e
    epyc-root:scripts/vidya/ingest_sources.py: d2da53a6a45f78f20c2426ff20bb4b15cfbdad61
---
