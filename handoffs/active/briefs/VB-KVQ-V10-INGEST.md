---
schema: epyc.brief.v1
id: VB-KVQ-V10-INGEST
box_text_sha: 8249de8d9b7b4de1
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:/mnt/raid0/llm/tmp/vidya-belief-substrate-program/vidya-kvq-v10-sweep-20261117-r2/spec.json
- epyc-root:/mnt/raid0/llm/tmp/vb-runs-20261107/vidya-kvq-v10-sweep-20261107/out/run-20261108T164754Z/summary.json
- epyc-root:scripts/vidya/ingest_sources.py
approach: 'Write-side wiring for: ingest the first post-hook complete v10 KV-quant sweep. Land the source adapter/producer
  hook (existing carrier, claim_tuple.grade(), no new ladder; Source in ingest_sources.py + README row) with a synthetic-fixture
  test and refusal controls. Box done-when (live, operational, verified after): the first post-hook complete sweep ingests
  12 rows with refused=0 and `loop_beliefs.py prepare` for that target lists them. Native row `c12-cpu-validate-20261116-r5`
  must file COMPLETE for the live proof.

  '
acceptance: '{ python3 /workspace/.claude/skills/inference-backlog-scheduling/scripts/queue_status.py | grep -F c12-cpu-validate-20261116-r5
  | grep -q COMPLETE; } && python3 -m pytest -q tests/vidya/test_vb_kvq_v10_ingest_wire.py'
new_tests:
- tests/vidya/test_vb_kvq_v10_ingest_wire.py
non_goals:
- no retrospective measurement warrant
- no new grading ladder
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:/mnt/raid0/llm/tmp/vidya-belief-substrate-program/vidya-kvq-v10-sweep-20261117-r2/spec.json: 42c204bfc0c0b504c8bffd0e412bdcaf9c13365c
    epyc-root:/mnt/raid0/llm/tmp/vb-runs-20261107/vidya-kvq-v10-sweep-20261107/out/run-20261108T164754Z/summary.json: e56fd20667c5657c7de999427f74244d0316bcc5
    epyc-root:scripts/vidya/ingest_sources.py: d2da53a6a45f78f20c2426ff20bb4b15cfbdad61
---
