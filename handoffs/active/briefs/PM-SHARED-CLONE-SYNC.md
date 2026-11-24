---
schema: epyc.brief.v1
id: PM-SHARED-CLONE-SYNC
box_text_sha: t:77a61447acf207b5
author: wrap-up
written: '2026-11-24'
accepted: owner
where:
- epyc-root:scripts/clone-repos.sh
approach: 'Operator decides; then fast-forward the shared clone without touching other sessions'' uncommitted work (no stash/reset);
  re-run queue_status to confirm.

  '
acceptance: git -C /workspace rev-list --count HEAD..origin/main
non_goals: []
tier: local
grounded:
  at: '2026-11-24'
  blobs:
    epyc-root:scripts/clone-repos.sh: 0f83d9796c1a575fc1d13555386a0df8ed5b9b60
---
