---
schema: epyc.brief.v1
id: HITL-R6-IDLE-NUDGE
box_text_sha: d1385440f87ab78e
author: owner
written: '2026-11-20'
accepted: owner
where:
- epyc-root:scripts/coordination/rowflow/rowflow.py
- epyc-root:scripts/coordination/session_bus.py
- epyc-root:scripts/coordination/tests/test_rowflow_idle_why_all_rows.py
approach: 'rowflow.py L2758 produces the IDLE-WHY ''no runnable row'' reason per region. Add: when that reason has held >=
  30 min on a bin that has stale-blocked BACKLOG rows, send ONE bus nudge (with an imperative line) to the row owner, rate-limited
  once per bin per 2 h (state file next to the idle ledger). Needs D9-ack. Box has no done-when; acceptance is the closest
  check.

  '
acceptance: grep -q IDLE-NUDGE scripts/coordination/rowflow/rowflow.py && python3 -m pytest -q scripts/coordination/tests/test_rowflow_idle_why_all_rows.py
non_goals:
- no nudge to sessions that are not the row owner
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/coordination/rowflow/rowflow.py: 5e76c90af8cfa49c863684663c3ca56084adfa8d
    epyc-root:scripts/coordination/session_bus.py: 3b817976378d091df9a6814d41883de83b0a7457
    epyc-root:scripts/coordination/tests/test_rowflow_idle_why_all_rows.py: 962ffd767e608d2cb4f1eb196e783d5cbc052ab3
---
