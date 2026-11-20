---
schema: epyc.brief.v1
id: TF-ACCEPT-CD-CLEANUP
box_text_sha: t:e135dbc4764bf460
author: owner
written: '2026-11-20'
accepted: owner
where:
- scripts/handoffs/task_lint_core.py
- scripts/handoffs
approach: 'Write a deterministic rewriter that strips a leading cd-into-shared-clone prefix from acceptance commands, run
  it over committed briefs; uncommitted ones in the pm-bfw-* worktrees on resume.

  '
acceptance: python3 scripts/handoffs/task_lint.py reports no rule f failures
non_goals:
- Do not rewrite brief content beyond the cd prefix
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/handoffs/task_lint_core.py: d0226354d9bdf21042eb3a16489be8f5d32267d2
    epyc-root:scripts/handoffs: tree:0e2683ba02ad62da3442a0f3966705032140c400
---
