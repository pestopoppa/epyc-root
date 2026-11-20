---
schema: epyc.brief.v1
id: LSA-EVIDENCE-1
box_text_sha: 3607712cd19eb0a6
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/vidya/ingest_sources.py
approach: 'Write-side wiring for: Before the first conversion screen, register its native result producer in scripts/vidya/adapters/README.md
  and project complete raw-run identity, effective configuration. Land the source adapter/producer hook (existing carrier,
  claim_tuple.grade(), no new ladder; Source in ingest_sources.py + README row) with a synthetic-fixture test and refusal
  controls. Box done-when (live, operational, verified after): the first conversion screen''s native result record ingests
  through a registered source with refused=0.

  '
acceptance: python3 -m pytest -q tests/vidya/test_lsa_evidence_1_wire.py
new_tests:
- tests/vidya/test_lsa_evidence_1_wire.py
non_goals:
- no retrospective measurement warrant
- no new grading ladder
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/vidya/ingest_sources.py: d2da53a6a45f78f20c2426ff20bb4b15cfbdad61
---
