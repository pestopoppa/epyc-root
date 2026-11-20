---
schema: epyc.brief.v1
id: HITL-R9-BOUNDARY-PROMPT
box_text_sha: d706179f28a1a507
author: owner
written: '2026-11-20'
accepted: owner
where:
- epyc-root:scripts/coordination/handoff_sessions.py::end_prompt
- epyc-root:scripts/coordination/handoff_sessions.py::TURN_END_LINE
- epyc-root:scripts/coordination/tests/test_handoff_sessions_turn_end.py
approach: 'Add a BOUNDARY_LINE constant (''file results, update handoffs, wrap-up, review unticked tasks''; index rows PREPARE
  only) and append it to end_prompt() next to TURN_END_LINE; update test_handoff_sessions_turn_end.py to pin it. Box has no
  done-when; acceptance is the closest check.

  '
acceptance: grep -q BOUNDARY_LINE scripts/coordination/handoff_sessions.py && python3 -m pytest -q scripts/coordination/tests/test_handoff_sessions_turn_end.py
non_goals:
- do not edit continue_prompt/idle_prompt
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/coordination/handoff_sessions.py: 579fe838cd5550a673e74a62509c4421a636f1fd
    epyc-root:scripts/coordination/tests/test_handoff_sessions_turn_end.py: 538ce785678342ab00259dae72d464caffedea28
---
