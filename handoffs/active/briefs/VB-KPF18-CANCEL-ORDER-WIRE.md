---
schema: epyc.brief.v1
id: VB-KPF18-CANCEL-ORDER-WIRE
box_text_sha: 29d71d403e3cad64
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:docs/reports/kv-cache/kpf18-g3-cancel-order-qual-20261105/qualify.py
- epyc-root:scripts/vidya/ingest_sources.py
approach: 'Write-side wiring for: preserve prospective synthetic cancellation-witness qualification observations. Land the
  source adapter/producer hook (existing carrier, claim_tuple.grade(), no new ladder; Source in ingest_sources.py + README
  row) with a synthetic-fixture test and refusal controls. Box has no code-level done-when; acceptance is the closest check.

  '
acceptance: python3 -m pytest -q tests/vidya/test_vb_kpf18_cancel_order_wire_wire.py
new_tests:
- tests/vidya/test_vb_kpf18_cancel_order_wire_wire.py
non_goals:
- no retrospective measurement warrant
- no new grading ladder
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:docs/reports/kv-cache/kpf18-g3-cancel-order-qual-20261105/qualify.py: 372a51a4d96ddcaa4dd3ad0a5a1b6c04026759a1
    epyc-root:scripts/vidya/ingest_sources.py: d2da53a6a45f78f20c2426ff20bb4b15cfbdad61
---
