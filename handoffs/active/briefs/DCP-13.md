---
schema: epyc.brief.v1
id: DCP-13
box_text_sha: 7924dd1cee3f9d6e
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/api/routes/chat_delegation.py
approach: 'Delegation hand-off fidelity: fix the architect decision loop that breaks on turn 0 in every branch (chat_delegation.py:203-220)
  so fetch_report is reachable. First step: failing test reproducing the unreachable fetch_report, then the fix.

  '
acceptance: grep -qE '^ *- \[x\] \*\*DCP\-13\b' handoffs/active/context-and-token-economy.md
new_tests:
- tests/unit/test_chat_delegation_fetch_report.py
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/api/routes/chat_delegation.py: b3777c27e973cac82e4735e550fd8f029947a50f
---
