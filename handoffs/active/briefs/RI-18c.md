---
schema: epyc.brief.v1
id: RI-18c
box_text_sha: 157ab69684b4bc51
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/api/services/memrl.py
approach: 'First concrete step for: apply the DROP (clause 1''s pre-registered action). Box done-when: the five sites no longer
  call the verdict or revision; the RI-16 reader shows `review_gate` and `review_verdict` as `null` on live `/chat`; and the
  targeted suite is green.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_ri_18c.py
new_tests:
- tests/unit/test_ri_18c.py
non_goals: []
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/api/services/memrl.py: 9592cec9f52c9921dcf5fe679443208515793166
---
