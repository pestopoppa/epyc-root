---
schema: epyc.brief.v1
id: HITL-R8-USAGE-RESUME
box_text_sha: 58001bef29cd5975
author: owner
written: '2026-11-20'
accepted: owner
where:
- epyc-root:scripts/coordination/token_guards.py::width_cap
- epyc-root:scripts/coordination/token_guards.py::budget_paused_until
- epyc-root:scripts/coordination/tests/test_token_guards.py
approach: 'In token_guards.py add clear_expired_pause(): when budget.paused_until has passed, clear the pause and restore
  max_live from width_cap(); pace_multiplier is read-only here and must never be raised by this path. Test in test_token_guards.py.
  Needs D9-ack. Box has no done-when; acceptance is the closest check.

  '
acceptance: grep -q clear_expired_pause scripts/coordination/token_guards.py && python3 -m pytest -q scripts/coordination/tests/test_token_guards.py
non_goals:
- never raise pace_multiplier
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/coordination/token_guards.py: 4f0f67c198f8a49d5902085b5457fd901ecd0706
    epyc-root:scripts/coordination/tests/test_token_guards.py: 148859367354d45990301b32a7b765b5ade3dc04
---
