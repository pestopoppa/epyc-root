---
schema: epyc.brief.v1
id: PM-PUBLISH-REHEARSAL
box_text_sha: t:c3d1d2b818dd2bed
author: wrap-up
written: '2026-11-24'
accepted: owner
where:
- epyc-root:scripts/coordination/rowflow/publish_row.py
approach: 'Define a REHEARSE=1 launcher contract (verify inputs, sha, env, server argv, exit before compute); call it from
  publish_row.lint; warn-only first per PM-RULES-WARN-FIRST, then enforce at zero failures.

  '
acceptance: pytest scripts/coordination/tests -k rehearsal
non_goals: []
tier: local
grounded:
  at: '2026-11-24'
  blobs:
    epyc-root:scripts/coordination/rowflow/publish_row.py: 47cce8a1c377c112e27a8ad4c8fe0bd11c9cbcb4
---
