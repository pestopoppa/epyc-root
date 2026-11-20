---
schema: epyc.brief.v1
id: KEEPER-FAST-COMPLETE-FLAG
box_text_sha: f89e45b937f1db6f
author: owner
written: '2026-11-20'
accepted: owner
where:
- epyc-root:scripts/coordination/rowflow/rowflow.py
- epyc-root:scripts/coordination/rowflow/ws58-calendar-keeper-v13.sh
- epyc-root:scripts/coordination/tests/test_rowflow.py
approach: 'Keeper side only (engine frozen): where the keeper reads a grants/<id>.complete receipt (rowflow.py ~L325, L796),
  compare elapsed vs the row estimate_s and emit a FAST-COMPLETE flag (rc=0 and elapsed < 5% of estimate) to the keeper log
  and queue_status; never change the row state. Needs D9-ack. Box has no done-when; acceptance is the closest check.

  '
acceptance: grep -q FAST-COMPLETE scripts/coordination/rowflow/rowflow.py && python3 -m pytest -q scripts/coordination/tests/test_rowflow.py
non_goals:
- do not edit the frozen engine
- do not auto-fail or requeue the flagged row
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/coordination/rowflow/rowflow.py: 5e76c90af8cfa49c863684663c3ca56084adfa8d
    epyc-root:scripts/coordination/rowflow/ws58-calendar-keeper-v13.sh: 2d8391ec2ab5f3f277eb3950bfd5dd27cc224279
    epyc-root:scripts/coordination/tests/test_rowflow.py: 78e91e9f387bc36c68c48333f25760dabd0e9c2c
---
