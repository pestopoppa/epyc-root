---
schema: epyc.brief.v1
id: LOOP-62
box_text_sha: 30b14a416639d001
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:tests/unit/test_inference_lock_concurrent_import.py
- epyc-orchestrator:tests/unit/test_inference_lock.py
approach: 'RESUME-7: randomized 16 aliases imported concurrently fail at orchestrator baseline 84f6f6f1 and at O3 (same-alias
  24-thread races pass). The mixed test is at orchestrator 5886e5ae (already present as tests/unit/test_inference_lock_concurrent_import.py).
  Fix the cross-module cold-import cycle in the inference lock alias modules (make the alias import graph acyclic: one canonical
  module, aliases re-export lazily) so the mixed randomized test passes repeatedly.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_inference_lock_concurrent_import.py
non_goals:
- no change to the canonical lock semantics
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:tests/unit/test_inference_lock_concurrent_import.py: 2e5dd9fecafedc6c2ba616be0815f64c64a4b1ad
    epyc-orchestrator:tests/unit/test_inference_lock.py: e1d5b476af2a9903afa608349eb413c83b5111c7
---
