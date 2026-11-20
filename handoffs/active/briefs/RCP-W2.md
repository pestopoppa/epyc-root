---
schema: epyc.brief.v1
id: RCP-W2
box_text_sha: d21159262af4cda7
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/eval-tower-program.md
approach: 'RD-12 paired shadow replay: same 50-question eval-tower replay shadow-OFF then shadow-ON, seed42. First step: paired
  runner invocation manifest.

  '
acceptance: grep -qE '^ *- \[x\] \*\*RCP\-W2\b' handoffs/active/eval-tower-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/eval-tower-program.md: bb00cad949830eca2617a6993062fa6973a6a1df
---
