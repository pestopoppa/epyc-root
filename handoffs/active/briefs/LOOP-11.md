---
schema: epyc.brief.v1
id: LOOP-11
box_text_sha: ea77456970ec4d78
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/coordination/rowflow/rowflow.py
- epyc-root:scripts/coordination/rowflow2/rowflow2.py
- epyc-root:scripts/coordination/rowflow/grant_ok_launcher.py
approach: 'rowflow.py (frozen) already stops a verified job-free poller on refusal; remaining is the ordering: arm checks
  must run BEFORE the poller is spawned (arm_one currently runs before admit). Since rowflow.py is frozen, the fix lands in
  rowflow2 arming (shadow-only today) and must carry this rule at cutover: run grant_ok_launcher before spawning the poller.
  Step: a rowflow2 test that a refused admission spawns no poller.

  '
acceptance: python3 -m pytest -q scripts/coordination/rowflow2/tests/test_no_poller_on_refusal.py
new_tests:
- scripts/coordination/rowflow2/tests/test_no_poller_on_refusal.py
non_goals:
- do not unfreeze rowflow.py
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/coordination/rowflow/rowflow.py: 5e76c90af8cfa49c863684663c3ca56084adfa8d
    epyc-root:scripts/coordination/rowflow2/rowflow2.py: 0215c54d7f68f0b039b8d2a697e5801be937d895
    epyc-root:scripts/coordination/rowflow/grant_ok_launcher.py: f25b9b6f312a38e9dad9f990e479805761d3fc81
---
