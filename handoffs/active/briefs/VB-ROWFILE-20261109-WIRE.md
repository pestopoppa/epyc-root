---
schema: epyc.brief.v1
id: VB-ROWFILE-20261109-WIRE
box_text_sha: ccee96b7233adaa1
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/vidya/ingest_sources.py
approach: 'Write-side wiring for: Write-side capture for the model-free and parser rows filed 2026-11-09 (DAR-SPLIT-1 split-half,
  M-15 id_map AUC, TD-16 six-arm readout, PIP-04 docling/LightOnOCR/ODL-hybr. Land the source adapter/producer hook (existing
  carrier, claim_tuple.grade(), no new ladder; Source in ingest_sources.py + README row) with a synthetic-fixture test and
  refusal controls. Box has no code-level done-when; acceptance is the closest check.

  '
acceptance: python3 -m pytest -q tests/vidya/test_vb_rowfile_20261109_wire_wire.py
new_tests:
- tests/vidya/test_vb_rowfile_20261109_wire_wire.py
non_goals:
- no retrospective measurement warrant
- no new grading ladder
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/vidya/ingest_sources.py: d2da53a6a45f78f20c2426ff20bb4b15cfbdad61
---
