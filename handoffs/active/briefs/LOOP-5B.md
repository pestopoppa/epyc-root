---
schema: epyc.brief.v1
id: LOOP-5B
box_text_sha: a694fc08c3ea6a32
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/handoffs/loop_metrics.py
- epyc-root:tests/test_loop_metrics.py
- epyc-root:artifacts/engineering/loop5-source-20261031/ADOPTION.md
approach: 'Three metrics still unknown: idle-h and failed-at-entry rate are produced now, operator_messages is unknown (no
  authorized human-message producer). Step: adopt the source-pinned keeper/quarter-writer patches at the owner boundary (ADOPTION.md)
  and add an authorized operator-message producer (counter fed only from the operator-input hook, no message text), then show
  a real day with all metrics observed. Kernel-accounted idle excludes iowait; say so in the report.

  '
acceptance: python3 -m pytest -q tests/test_loop_metrics.py
non_goals:
- no message text capture
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/handoffs/loop_metrics.py: ec3acc82c6677dc83b8d36e90a5067e1e71da0a2
    epyc-root:tests/test_loop_metrics.py: 76961684de366f6097815d6b7b10b6208435db0d
    epyc-root:artifacts/engineering/loop5-source-20261031/ADOPTION.md: 2e5bc26c534452d584b6101fd2cb905e911dca5d
---
