---
schema: epyc.brief.v1
id: VB-AK-HISTORY
box_text_sha: t:1ef8c070c9070785
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/vidya/adapters/ak_history.py
- epyc-root:tests/vidya/test_prospective_ab_carriers.py
- epyc-root:scripts/vidya/ingest_sources.py
approach: 'Write-side wiring for: Keep AK-HR-1 and AK-HR-2 retrospective and wire the prospective AK-HR-3 fields on the WRITE
  side before their first post-change run. Land the source adapter/producer hook (existing carrier, claim_tuple.grade(), no
  new ladder; Source in ingest_sources.py + README row) with a synthetic-fixture test and refusal controls. Box done-when
  (live, operational, verified after): the research-loop producer call is wired by the INF-73 loop owner and the first post-change
  AK-HR-1 re-run projects through `claim_tuple.grade()` with refused=0.

  '
acceptance: python3 -m pytest -q tests/vidya/test_sc_109_wire.py tests/vidya/test_prospective_ab_carriers.py
new_tests:
- tests/vidya/test_sc_109_wire.py
non_goals:
- no retrospective measurement warrant
- no new grading ladder
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/vidya/adapters/ak_history.py: 73bbd8726fd1cef56f8f157637bf367e73878e1f
    epyc-root:tests/vidya/test_prospective_ab_carriers.py: 75ca3a2dde222f8a3274a6757f2b547c9588f503
    epyc-root:scripts/vidya/ingest_sources.py: d2da53a6a45f78f20c2426ff20bb4b15cfbdad61
---
