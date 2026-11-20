---
schema: epyc.brief.v1
id: VB-V11-122-GPU-GATE-WIRE
box_text_sha: 41ad3d4761815eca
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/vidya/ingest_sources.py
approach: 'Write-side wiring for: project the prospective C13 llguidance GPU timing packet through the existing llama-bench
  carrier. Land the source adapter/producer hook (existing carrier, claim_tuple.grade(), no new ladder; Source in ingest_sources.py
  + README row) with a synthetic-fixture test and refusal controls. Box has no code-level done-when; acceptance is the closest
  check.

  '
acceptance: python3 -m pytest -q tests/vidya/test_vb_v11_122_gpu_gate_wire_wire.py
new_tests:
- tests/vidya/test_vb_v11_122_gpu_gate_wire_wire.py
non_goals:
- no retrospective measurement warrant
- no new grading ladder
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/vidya/ingest_sources.py: d2da53a6a45f78f20c2426ff20bb4b15cfbdad61
---
