---
schema: epyc.brief.v1
id: ROWFLOW-IDLE-GRACE-FIELD
box_text_sha: 562726fba67e306e
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/coordination/rowflow/publish_row.py
- epyc-root:docs/design/rowflow2-20261105.md
approach: 'Add optional row field idle_grace_s (validated by publish lint, default = current IDLE-HELD threshold) so rows
  with legitimate idle phases do not warn falsely. Note docs/design/rowflow2-20261105.md:58 REJECTED a per-row idle-grace
  field: the first step is a Pipeline decision to overturn that or decline; recommended: overturn (false warnings are real),
  implement in rowflow2 publish lint.

  '
acceptance: python3 -m pytest -q scripts/coordination/tests/test_publish_row_idle_grace.py
new_tests:
- scripts/coordination/tests/test_publish_row_idle_grace.py
non_goals:
- no change to default threshold
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/coordination/rowflow/publish_row.py: f71787bda4ff97f509d88afd008069379d1d6500
    epyc-root:docs/design/rowflow2-20261105.md: b6189f226ff8fc5200cdad96ae695f62cbed2187
---
