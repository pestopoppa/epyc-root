---
schema: epyc.brief.v1
id: TU-LED-1
box_text_sha: 8873b73bbafb14a1
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/benchmark-suites.md
approach: 'Observe-only solve-failure ledger: buckets ran-out-of-time/failed-verification/no-valid-tool-call with gains and
  give-backs; first-try-valid-call %, repair-recovery %, tokens on failing tasks. First step: the bucketer over existing logs.

  '
acceptance: grep -qE '^ *- \[x\] \*\*TU\-LED\-1\b' handoffs/active/benchmark-suites.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/benchmark-suites.md: c60d0e1b18aff6d70e814591f5dec40920697504
---
