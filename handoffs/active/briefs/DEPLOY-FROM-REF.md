---
schema: epyc.brief.v1
id: DEPLOY-FROM-REF
box_text_sha: t:93b6dfa67818e7ca
author: owner
written: '2026-11-21'
accepted: owner
where:
- scripts/coordination/rowflow/deploy_rowflow.sh
approach: 'Resolve the staged ref to a temp worktree or git-show the harness, re-exec from there, and refuse if the invoking
  tree differs without a flag.

  '
acceptance: 'Test: invoke from a tree with a modified harness; the deployed replay uses the staged ref version.'
non_goals:
- Changing keeper logic.
tier: local
grounded:
  at: '2026-11-21'
  blobs:
    epyc-root:scripts/coordination/rowflow/deploy_rowflow.sh: e9e664f8c71d7fd8d96dfa93b54fa3ecfb37f04f
---
