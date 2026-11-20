---
schema: epyc.brief.v1
id: RTG-RETRAIN-1
box_text_sha: d56ede8c85601502
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:scripts/server/orchestrator_stack.py
- epyc-orchestrator:scripts/server/stack_env.py
- epyc-orchestrator:scripts/validate/stack_change_guard.py
approach: 'First concrete step for: Retrain routing classifiers on model-keyed labels, with a reproducible build. Box has
  no done-when; acceptance is the closest check.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_rtg_retrain_1.py
new_tests:
- tests/unit/test_rtg_retrain_1.py
non_goals: []
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:scripts/server/orchestrator_stack.py: a2e1f4ba481e9b9068ec80b7ae4e829884932a8c
    epyc-orchestrator:scripts/server/stack_env.py: 347d8f70f9eeb68ea19d5059763b83b96b803ce7
    epyc-orchestrator:scripts/validate/stack_change_guard.py: 977bb7c97a125ccbd159e98cf621306d6e4933eb
---
