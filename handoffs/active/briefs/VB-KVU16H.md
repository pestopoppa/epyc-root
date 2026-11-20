---
schema: epyc.brief.v1
id: VB-KVU16H
box_text_sha: 24c5199ff7e78c31
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/vidya/ingest_sources.py
approach: 'Write-side wiring for: write side for the KVU-16h VRAM attribution (allocator shim + phase replay). Land the source
  adapter/producer hook (existing carrier, claim_tuple.grade(), no new ladder; Source in ingest_sources.py + README row) with
  a synthetic-fixture test and refusal controls. Box done-when (live, operational, verified after): the next VRAM/residency
  probe run after the hook ingests with refused=0 and `loop_beliefs.py prepare` for the 27B GPU target shows its headroom
  claim in the host tier.

  '
acceptance: python3 -m pytest -q tests/vidya/test_vb_kvu16h_wire.py
new_tests:
- tests/vidya/test_vb_kvu16h_wire.py
non_goals:
- no retrospective measurement warrant
- no new grading ladder
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/vidya/ingest_sources.py: d2da53a6a45f78f20c2426ff20bb4b15cfbdad61
---
