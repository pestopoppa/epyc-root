---
schema: epyc.brief.v1
id: VB-AK-R18D-AA-WIRE
box_text_sha: d021987b8c6547d2
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/vidya/adapters/autokernel_r18d_aa.py
- epyc-root:tests/vidya/test_autokernel_r18d_aa.py
- epyc-root:artifacts/analysis/r18d-clock-diagnosis-20261109.md
- epyc-root:scripts/vidya/ingest_sources.py
approach: 'Write-side wiring for: prospectively wire R18-D pp512 A/A calibration. Land the source adapter/producer hook (existing
  carrier, claim_tuple.grade(), no new ladder; Source in ingest_sources.py + README row) with a synthetic-fixture test and
  refusal controls. Box done-when (live, operational, verified after): the first post-hook R18-D A/A run ingests through the
  AutoKernel measurement adapter with refused=0 and the AK canary for the 27B GPU target lists its settled floor. Native row
  `vidya-r18d-aa-wire-20261104` must file COMPLETE for the live proof.

  '
acceptance: '{ python3 /workspace/.claude/skills/inference-backlog-scheduling/scripts/queue_status.py | grep -F vidya-r18d-aa-wire-20261104
  | grep -q COMPLETE; } && python3 -m pytest -q tests/vidya/test_vb_ak_r18d_aa_wire_wire.py tests/vidya/test_autokernel_r18d_aa.py'
new_tests:
- tests/vidya/test_vb_ak_r18d_aa_wire_wire.py
non_goals:
- no retrospective measurement warrant
- no new grading ladder
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/vidya/adapters/autokernel_r18d_aa.py: dbe87bc151db54cc935a582aebe73d5ded3b5b40
    epyc-root:tests/vidya/test_autokernel_r18d_aa.py: b59c72c2dc622b8983854e60c7860890fb86ae1f
    epyc-root:artifacts/analysis/r18d-clock-diagnosis-20261109.md: 952b84ee48281e2db18d45462b867a620259ed70
    epyc-root:scripts/vidya/ingest_sources.py: d2da53a6a45f78f20c2426ff20bb4b15cfbdad61
---
