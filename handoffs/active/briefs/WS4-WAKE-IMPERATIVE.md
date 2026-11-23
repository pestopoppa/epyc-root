---
schema: epyc.brief.v1
id: WS4-WAKE-IMPERATIVE
box_text_sha: t:981cc458be2d1514
author: owner
written: '2026-11-20'
accepted: owner
where:
- epyc-root:scripts/coordination/handoff_sessions.py#L530-613
- epyc-root:scripts/coordination/handoff_sessions.py#L1619-1626
- epyc-root:scripts/coordination/handoff_sessions.py#L1748-1756
- epyc-root:scripts/coordination/tmux_adapter.py#L2301-2488
- epyc-root:scripts/coordination/tests/test_handoff_sessions_turn_end.py
approach: 'Add IMPERATIVE_RE = r''(?m)^(Do|Run|Take|Read|Resolve|Act|File|Publish|Wrap)\b'' and ensure_imperative(text, line)
  -> str in handoff_sessions.py. It returns text unchanged if IMPERATIVE_RE matches; otherwise it inserts line as the 2nd
  line, right after the ''[VERSION]'' header.

  Wrap the return of the 6 builders (end/idle/continue/transfer/awaiting/proposals_prompt) with it. The default line is ''Do
  the next task in your handoff now; do not wait for further instructions.''

  In tmux_adapter.cmd_nudge, pass the typed text through the same helper (import it) before typing.

  New test test_wake_imperative.py: parametrize the 6 builders with a tmp flags dir and a minimal e dict, using the fixture
  pattern in test_handoff_sessions_turn_end.py. Assert IMPERATIVE_RE matches each output and that a text with no imperative
  gets one. The ''live woken session acts'' half of done-when is a manual check outside this acceptance.

  Line ranges: 530-613 = end/idle/continue/transfer builders, 1619-1626 awaiting_prompt, 1748-1756 proposals_prompt; read
  only those.

  '
acceptance: python3 -m pytest -q scripts/coordination/tests/test_wake_imperative.py
new_tests:
- epyc-root:scripts/coordination/tests/test_wake_imperative.py
non_goals:
- do not reword existing prompt bodies beyond inserting the imperative line
- do not change alert_wake rate limiting or dispatch logic
- do not send real tmux keystrokes in tests
tier: luna
grounded:
  at: '2026-11-23'
  blobs:
    epyc-root:scripts/coordination/handoff_sessions.py: afe71b1dd53b39c9eee61ba50865209d06ff3d57
    epyc-root:scripts/coordination/tmux_adapter.py: d795a8245300e2cc37f32b2c1bd30c6ed84e0725
    epyc-root:scripts/coordination/tests/test_handoff_sessions_turn_end.py: 538ce785678342ab00259dae72d464caffedea28
---
