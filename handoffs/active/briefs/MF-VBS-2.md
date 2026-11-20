---
schema: epyc.brief.v1
id: MF-VBS-2
box_text_sha: 5ddb43779643237c
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/benchmark-suites.md
approach: 'Add the explicit run-acceptance-before-FINAL step to INTERLEAVED_EDIT_INSTRUCTIONS and the batch-edit finish contract,
  then rerun the BEP sandbox. First step: the prompt edit with a grep test.

  '
acceptance: grep -qE '^ *- \[x\] \*\*MF\-VBS\-2\b' handoffs/active/benchmark-suites.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/benchmark-suites.md: c60d0e1b18aff6d70e814591f5dec40920697504
---
