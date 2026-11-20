---
schema: epyc.brief.v1
id: WS4-WAKE-IMPERATIVE
box_text_sha: 981cc458be2d1514
author: owner
written: '2026-11-20'
accepted: owner
where:
- epyc-root:scripts/coordination/handoff_sessions.py::continue_prompt
- epyc-root:scripts/coordination/handoff_sessions.py::idle_prompt
- epyc-root:scripts/coordination/handoff_sessions.py::alert_wake
- epyc-root:scripts/coordination/session_bus.py
approach: 'Enumerate every wake/nudge builder in handoff_sessions.py (end_prompt, idle_prompt, continue_prompt, the alert
  wake text) and session_bus nudge, route each through one helper that guarantees a final imperative line (starts with a verb:
  Do/Run/Read/Resolve). New test scripts/coordination/tests/test_wake_imperative.py parametrised over the builders. The ''live
  woken session acts'' half of the done-when is a manual check, not covered by the acceptance.

  '
acceptance: test -f scripts/coordination/tests/test_wake_imperative.py && python3 -m pytest -q scripts/coordination/tests/test_wake_imperative.py
non_goals:
- do not reword prompts beyond appending the imperative
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/coordination/handoff_sessions.py: 579fe838cd5550a673e74a62509c4421a636f1fd
    epyc-root:scripts/coordination/session_bus.py: 3b817976378d091df9a6814d41883de83b0a7457
---
