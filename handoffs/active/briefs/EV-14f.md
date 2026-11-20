---
schema: epyc.brief.v1
id: EV-14f
box_text_sha: 2aee174ae0e2a7f6
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/eval-tower-program.md
approach: 'Known-null corpus: run the optimizer on inputs with no failures and assert it proposes nothing. First step: null
  corpus fixture and assertion test.

  '
acceptance: grep -qE '^ *- \[x\] \*\*EV\-14f\b' handoffs/active/eval-tower-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/eval-tower-program.md: bb00cad949830eca2617a6993062fa6973a6a1df
---
