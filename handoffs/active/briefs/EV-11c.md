---
schema: epyc.brief.v1
id: EV-11c
box_text_sha: 221a14b2cf5f61c7
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/eval-tower-program.md
approach: 'Fresh math re-baseline (inference, batch manifest): gated on EV-11a fix and EV-11b decision; production temp+seed42;
  record dataset_sha256 and test_profile per arm; era-label supersede. First step: the batch manifest entry.

  '
acceptance: grep -qE '^ *- \[x\] \*\*EV\-11c\b' handoffs/active/eval-tower-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/eval-tower-program.md: bb00cad949830eca2617a6993062fa6973a6a1df
---
