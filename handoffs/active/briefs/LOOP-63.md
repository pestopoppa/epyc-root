---
schema: epyc.brief.v1
id: LOOP-63
box_text_sha: 806f00ba4286b85d
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:tests/unit/test_inference_lock.py
approach: 'Merge refactor/hermetic-tests (1 commit ahead of origin/main) into epyc-orchestrator main; every orchestrator branch
  contains it. Step: rebase on origin/main, run the unit suite, push through serialized_push to main. Acceptance is the ancestor
  check.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && git merge-base --is-ancestor refactor/hermetic-tests origin/main
non_goals:
- no other branch merged in this box
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:tests/unit/test_inference_lock.py: e1d5b476af2a9903afa608349eb413c83b5111c7
---
