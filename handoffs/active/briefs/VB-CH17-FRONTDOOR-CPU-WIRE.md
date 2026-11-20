---
schema: epyc.brief.v1
id: VB-CH17-FRONTDOOR-CPU-WIRE
box_text_sha: 3b1f765fa4ce267f
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/vidya/ingest_sources.py
approach: 'Write-side wiring for: capture the prospective C13 frontdoor MTP-versus-none serving diagnostic at write time.
  Land the source adapter/producer hook (existing carrier, claim_tuple.grade(), no new ladder; Source in ingest_sources.py
  + README row) with a synthetic-fixture test and refusal controls. Box has no code-level done-when; acceptance is the closest
  check.

  '
acceptance: python3 -m pytest -q tests/vidya/test_vb_ch17_frontdoor_cpu_wire_wire.py
new_tests:
- tests/vidya/test_vb_ch17_frontdoor_cpu_wire_wire.py
non_goals:
- no retrospective measurement warrant
- no new grading ladder
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/vidya/ingest_sources.py: d2da53a6a45f78f20c2426ff20bb4b15cfbdad61
---
