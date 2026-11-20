---
schema: epyc.brief.v1
id: UTM-B2-VERBATIM-WITH-COMPACTION
box_text_sha: 03574ede69030a8d
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/graph/session_summary.py
approach: 'Allow record_turn/session_log_verbatim to run with session_compaction on when context_arm_ab is off; keep settings()
  conflict list unchanged for arm mode (existing test_toc_mp2i_context_arms.py must pass unchanged). Register the verbatim
  log as an artifact for the owning task only.

  '
acceptance: pytest tests/unit/test_verbatim_with_compaction.py -q
new_tests:
- epyc-orchestrator:tests/unit/test_verbatim_with_compaction.py
non_goals:
- Do not touch arm-mode conflict list
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/graph/session_summary.py: a0441f76772b6ad113645439417fd97336173f4d
---
