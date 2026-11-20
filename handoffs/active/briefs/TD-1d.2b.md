---
schema: epyc.brief.v1
id: TD-1d.2b
box_text_sha: 9cbad6d3ee28f8ad
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/inference_lock.py
- epyc-orchestrator:src/typed_decisions/native.py
approach: 'First concrete step for: concurrent in-process `llm_call`s are serialized by the cross-process `inference_lock`.
  Box done-when: the lock scope is chosen with that number and the heavy_model lock note is reconciled.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_td_1d_2b.py
new_tests:
- tests/unit/test_td_1d_2b.py
non_goals: []
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/inference_lock.py: c624ec2785858404fb036149dc65fba43fe2a9af
    epyc-orchestrator:src/typed_decisions/native.py: e23ef30becc9f992905cd4ce36e77a9134bf3faf
---
