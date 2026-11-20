---
schema: epyc.brief.v1
id: TR-5.3
box_text_sha: 8e081cfa4d967c6d
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:scripts/benchmark/seeding_types.py
- epyc-orchestrator:src/classifiers/role_taxonomy.py
- epyc-orchestrator:src/api/routes/chat_pipeline/routing.py
approach: 'First concrete step for: Decision gate: if Δ ≥ +2 points on at least one benchmark with no regression > −1 point
  on others, promote to default-on. If flat or regression, stay OFF and document negative result in `Open Question. Box has
  no done-when; acceptance is the closest check.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_tr_5_3.py
new_tests:
- tests/unit/test_tr_5_3.py
non_goals: []
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:scripts/benchmark/seeding_types.py: 6ff00fd044bbd6ead2a1eedf141d830b63a60910
    epyc-orchestrator:src/classifiers/role_taxonomy.py: 4043f5ec49c82c43cec1eb2fcf0a0769537ac783
    epyc-orchestrator:src/api/routes/chat_pipeline/routing.py: baed61d64c9f787930b5553e6dc98dc22155bf36
---
