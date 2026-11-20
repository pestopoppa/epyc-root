---
schema: epyc.brief.v1
id: JANITOR-QH-UNBOUND
box_text_sha: 777ee4fbfb3665db
author: owner
written: '2026-11-20'
accepted: owner
where:
- epyc-root:scripts/coordination/churn/disk_janitor.sh
- epyc-root:scripts/coordination/tests/test_keeper_reap_ws58_disk.py
approach: 'QH is assigned at disk_janitor.sh L75 from a file probe; the 4 JanitorQuietHostSkip tests fail with ''QH: unbound
  variable'' (reproduced: 4 failed, 1 passed). Fix the script to default QH safely or make the fixture export JANITOR_QUIET_HOST;
  decide by which side reads QH before L75 under set -u.

  '
acceptance: python3 -m pytest -q scripts/coordination/tests/test_keeper_reap_ws58_disk.py::JanitorQuietHostSkip
non_goals:
- do not change quiet-host grant semantics
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/coordination/churn/disk_janitor.sh: 57ef022d06b99d30be5850c442e55dbeb9ff74fb
    epyc-root:scripts/coordination/tests/test_keeper_reap_ws58_disk.py: d2b2c41b64e5719f3121322bd30e047585cd96e9
---
