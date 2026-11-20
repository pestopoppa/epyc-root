---
schema: epyc.brief.v1
id: EV-6c
box_text_sha: 1a044f9a89d67435
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/eval-tower-program.md
approach: 'Give llm_judge a non-Qwen judge (3,806 pool items currently same_family). First step: pick a non-Qwen served judge
  from the registry and add the binding with a test that the label flips to cross_family.

  '
acceptance: grep -qE '^ *- \[x\] \*\*EV\-6c\b' handoffs/active/eval-tower-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/eval-tower-program.md: bb00cad949830eca2617a6993062fa6973a6a1df
---
