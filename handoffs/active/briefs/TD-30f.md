---
schema: epyc.brief.v1
id: TD-30f
box_text_sha: 45a5e59465f3d718
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/classifiers/quality_detector.py
- epyc-orchestrator:src/pipeline_monitor/anomaly.py
- epyc-orchestrator:src/llm_primitives/inference.py
- epyc-orchestrator:scripts/analysis/guard_length_replay.py
approach: 'First concrete step for: check the orchestrator''s runtime unique-ratio guards for the same length bias. Box done-when:
  each guard has a measured false-positive rate by output length, and any guard that fires on coherent long text is made length-aware
  or switched to the `degeneracy.v2` loop trigger.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_td_30f.py
new_tests:
- tests/unit/test_td_30f.py
non_goals: []
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/classifiers/quality_detector.py: ba7db6dd1caa1c2b30746245f114a8290c010470
    epyc-orchestrator:src/pipeline_monitor/anomaly.py: 0adfd25199a24c4ba3f85f97f1101c7192cf5d98
    epyc-orchestrator:src/llm_primitives/inference.py: 95df5e5fe8b106f53d2d32ab0a13f7d2085f96f2
    epyc-orchestrator:scripts/analysis/guard_length_replay.py: 9c0a55b6ba977df19f712e7190c5f3d4a5b6328d
---
