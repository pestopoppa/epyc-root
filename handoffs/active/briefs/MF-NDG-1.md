---
schema: epyc.brief.v1
id: MF-NDG-1
box_text_sha: 9b0ea3ceaafb5214
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/benchmark-suites.md
approach: 'Measure how often empty-code turns announce an action, then reword the nudge at helpers.py:383-386 to execute form;
  BEP sandbox rerun. First step: counting script over existing turn logs (zero compute), then reword.

  '
acceptance: grep -qE '^ *- \[x\] \*\*MF\-NDG\-1\b' handoffs/active/benchmark-suites.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/benchmark-suites.md: c60d0e1b18aff6d70e814591f5dec40920697504
---
