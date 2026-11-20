---
schema: epyc.brief.v1
id: D-c1
box_text_sha: de6ab85b6032f9de
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/session/protocol.py
- epyc-orchestrator:src/api/routes/chat_pipeline/repl_executor.py
- epyc-orchestrator:src/repl_environment/state.py
approach: 'First concrete step for: Decide D-c on D-c1''s numbers, or close it if the measured re-derivation cost is negligible.
  -. Box has no done-when; acceptance is the closest check.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_d_c1.py
new_tests:
- tests/unit/test_d_c1.py
non_goals: []
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/session/protocol.py: 108ef3158a4c383b223d2dae172ee096a8babc58
    epyc-orchestrator:src/api/routes/chat_pipeline/repl_executor.py: 57c230f9f7cc16cf5076c10729601290804d6292
    epyc-orchestrator:src/repl_environment/state.py: 37be7d1c7031edfa6ff2b026cd42d573181ab9b5
---
