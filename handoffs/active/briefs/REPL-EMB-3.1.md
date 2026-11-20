---
schema: epyc.brief.v1
id: REPL-EMB-3.1
box_text_sha: ec45fae21cdd3b33
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/repl_environment/environment.py::_spill_output
approach: 'Replace _spill_output''s summary with the REPL-EMB design''s retrieval-backed summary while keeping head+tail+peek
  fallback; box line is truncated, so approach is the closest reading and must be checked against the REPL-EMB design before
  coding.

  '
acceptance: pytest tests/unit/test_repl_spill_summary.py
new_tests:
- tests/unit/test_repl_spill_summary.py
non_goals:
- no change to capped-turn path that runs before spill
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/repl_environment/environment.py: cd93f9e4825452efdf31e0f2e81efa7b8142aecc
---
