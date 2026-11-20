---
schema: epyc.brief.v1
id: LOOP-84
box_text_sha: e9b69b8cec3e985d
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:research/refactor-audit-2026-10/packages/wave2.json
- epyc-orchestrator:tests/unit/test_llama_server.py
- epyc-orchestrator:tests/unit/test_inference_mixin.py
approach: 'D3 rest: inference hot path (llama_server lanes, _execute_turn, escalation chain): A2-22 first (cross-lane contract
  tests, test_llama_server.py:493, test_inference_mixin.py:63), then A2-06 A2-09 A2-07 A2-08 A2-10 A2-14 A2-15 A2-17..A2-21
  de-duplication. Requires O1 merged. Step: the cross-lane contract tests.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_llama_server.py tests/unit/test_inference_mixin.py
non_goals:
- no de-dup before the contract tests pass
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:research/refactor-audit-2026-10/packages/wave2.json: 69d12317bc22636855f108a0f2f3f4c906ec6d6d
    epyc-orchestrator:tests/unit/test_llama_server.py: 77dab0b510a34d2155429fa0b22b126d9beae6c1
    epyc-orchestrator:tests/unit/test_inference_mixin.py: 46be7c2f6cac5e0ba0e12db8111786048aeea09a
---
