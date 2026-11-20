---
schema: epyc.brief.v1
id: VB-KPF50-COUNTERFACTUAL-WIRE
box_text_sha: ac642f8ce9a140ea
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/vidya/ingest_sources.py
approach: 'Write-side wiring for: Wire the prospective KPF-50 trunk-mask counterfactual runner at write time to preserve each
  original window, raw timing, configuration and source/build/model/library iden. Land the source adapter/producer hook (existing
  carrier, claim_tuple.grade(), no new ladder; Source in ingest_sources.py + README row) with a synthetic-fixture test and
  refusal controls. Box has no code-level done-when; acceptance is the closest check.

  '
acceptance: python3 -m pytest -q tests/vidya/test_vb_kpf50_counterfactual_wire_wire.py
new_tests:
- tests/vidya/test_vb_kpf50_counterfactual_wire_wire.py
non_goals:
- no retrospective measurement warrant
- no new grading ladder
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/vidya/ingest_sources.py: d2da53a6a45f78f20c2426ff20bb4b15cfbdad61
---
