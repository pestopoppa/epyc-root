---
schema: epyc.brief.v1
id: TD-1d.3
box_text_sha: 5713b3ac4fa72c6b
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/typed_decisions/native.py
approach: 'First concrete step for: Build and compare checkpoint-safe isolated question branches over one shared state prefix.
  Box has no done-when; acceptance is the closest check.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_td_1d_3.py
new_tests:
- tests/unit/test_td_1d_3.py
non_goals: []
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/typed_decisions/native.py: e23ef30becc9f992905cd4ce36e77a9134bf3faf
---
