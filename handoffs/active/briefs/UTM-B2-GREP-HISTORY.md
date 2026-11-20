---
schema: epyc.brief.v1
id: UTM-B2-GREP-HISTORY
box_text_sha: f8da23060882e67d
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/features.py
approach: 'Add grep_history as a REPL tool over session.verbatim.md (written by context_arm_ab.record_turn), registered only
  after first compaction boundary and behind a feature flag so the registry is byte-identical when off. Implement the output
  contract exactly as the box states.

  '
acceptance: pytest tests/unit/test_grep_history.py -q
new_tests:
- epyc-orchestrator:tests/unit/test_grep_history.py
non_goals:
- No change to the context-arm A/B conflict guard
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/features.py: 7410fd35cca156e436d981664d5304d6bf2ad3b2
---
