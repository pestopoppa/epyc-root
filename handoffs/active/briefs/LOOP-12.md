---
schema: epyc.brief.v1
id: LOOP-12
box_text_sha: e2d75d835a95d038
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/coordination/churn/ws58-keeper-watchdog.sh
- epyc-root:scripts/coordination/churn/churn_up.sh
- epyc-root:scripts/coordination/tests/test_churn_up_supervision.py
approach: 'Watchdog has no supervisor and has never been tested against a real session crash. The supervisor is on main (1219d4438)
  and --supervise-watchdog is on a branch. Steps: land --supervise-watchdog, then a crash drill: kill the watchdog in a sandbox
  using a PID you captured yourself and observe restart within the cadence; extend scripts/coordination/tests/test_churn_up_supervision.py
  with the drill assertion.

  '
acceptance: python3 -m pytest -q scripts/coordination/tests/test_churn_up_supervision.py
non_goals:
- kill only captured PIDs
- no pkill
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/coordination/churn/ws58-keeper-watchdog.sh: 748c9b8658956e65800ec92e69cc080eccf4faf7
    epyc-root:scripts/coordination/churn/churn_up.sh: 8c07d638647f3d6a515afc81d139752271680ccf
    epyc-root:scripts/coordination/tests/test_churn_up_supervision.py: de8e087de5f0216a6de3ffec782cd6a5d7b34414
---
