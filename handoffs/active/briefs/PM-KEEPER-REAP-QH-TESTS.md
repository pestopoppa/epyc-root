---
schema: epyc.brief.v1
id: PM-KEEPER-REAP-QH-TESTS
box_text_sha: t:9632096e6e9639af
author: wrap-up
written: '2026-11-24'
accepted: owner
where:
- epyc-root:scripts/coordination/tests/test_keeper_reap_ws58_disk.py
- epyc-root:scripts/coordination/tests/test_keeper_reap_oob.py
approach: 'Reproduce; find the shell snippet under set -u that reads QH without a default; give it a default or export it
  in the fixture; do not change keeper policy constants.

  '
acceptance: pytest scripts/coordination/tests/test_keeper_reap_ws58_disk.py scripts/coordination/tests/test_keeper_reap_oob.py
non_goals: []
tier: local
grounded:
  at: '2026-11-24'
  blobs:
    epyc-root:scripts/coordination/tests/test_keeper_reap_ws58_disk.py: d2b2c41b64e5719f3121322bd30e047585cd96e9
    epyc-root:scripts/coordination/tests/test_keeper_reap_oob.py: 2194db42302318b13a137883f0160306ce5282db
---
