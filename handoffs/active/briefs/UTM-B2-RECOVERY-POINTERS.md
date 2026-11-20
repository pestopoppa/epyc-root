---
schema: epyc.brief.v1
id: UTM-B2-RECOVERY-POINTERS
box_text_sha: 33e72a1e1ce83e69
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/graph/context_arm_ab.py
approach: 'Cleared-output placeholder and compaction text carry verbatim log path plus byte offset and length (offsets recorded
  by record_turn); name grep_history only when registered. Gate behind the existing flags so flags-off output is byte-identical.

  '
acceptance: pytest tests/unit/test_recovery_pointers.py -q
new_tests:
- epyc-orchestrator:tests/unit/test_recovery_pointers.py
non_goals:
- No new flags
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/graph/context_arm_ab.py: 5f04f543e3d659b4f40e3683181386af6c9cae88
---
