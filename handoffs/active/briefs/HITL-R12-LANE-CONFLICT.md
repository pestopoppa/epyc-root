---
schema: epyc.brief.v1
id: HITL-R12-LANE-CONFLICT
box_text_sha: abb9c50e80a22db1
author: owner
written: '2026-11-20'
accepted: owner
where:
- epyc-root:scripts/coordination/rowflow/rowflow.py
- epyc-root:scripts/coordination/tests/test_rowflow_rank_inversion.py
approach: 'In the placement/grant planner in rowflow.py: when two rows block on one grant, keep the running step-resumable
  row and requeue the other at the same rank (LANE-CONFLICT log line); exempt the case where the waiter is a champion correctness
  gate. Land behind a flag, only after a week of AUTO-* logs with no operator reversal (REPORT section 6). Needs D9-ack. Box
  has no done-when; acceptance is the closest check.

  '
acceptance: grep -q LANE-CONFLICT scripts/coordination/rowflow/rowflow.py && python3 -m pytest -q scripts/coordination/tests/test_rowflow_rank_inversion.py
non_goals:
- never preempt a running row
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/coordination/rowflow/rowflow.py: 5e76c90af8cfa49c863684663c3ca56084adfa8d
    epyc-root:scripts/coordination/tests/test_rowflow_rank_inversion.py: 74cbe20d32bd85b1b17b412c4234442a6d021968
---
