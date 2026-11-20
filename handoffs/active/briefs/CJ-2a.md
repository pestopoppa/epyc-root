---
schema: epyc.brief.v1
id: CJ-2a
box_text_sha: d8d46bacc2ce6f2a
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/benchmark-suites.md
approach: 'Acquire the post-cutoff v5/v6 livecodebench window (size on disk before download; 158G headroom) jointly with scoring-infra-standardization.md
  2d which owns the download, so no second download; wire a representative sample by the hard-slice construction (n=53).

  '
acceptance: grep -qE '^ *- \[x\] \*\*CJ\-2a\b' handoffs/active/benchmark-suites.md
non_goals:
- no second download
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/benchmark-suites.md: c60d0e1b18aff6d70e814591f5dec40920697504
---
