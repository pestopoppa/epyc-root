---
schema: epyc.brief.v1
id: CJ-1e
box_text_sha: d5d5af5850eef573
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/benchmark-suites.md
approach: 'GPQA-diamond local run on the 27B and 35B-A3B pair (recipes in the box; champion ef81196d5 binary, re-hash before
  launch). Run 2026-09-16 left the ordering unresolved at n=198; next step is a larger-n or paired rerun per the box follow-up,
  emitted as local_benchmarks.gpqa_diamond. Stop when ordering resolves with paired CI or n exhausted.

  '
acceptance: grep -qE '^ *- \[x\] \*\*CJ\-1e\b' handoffs/active/benchmark-suites.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/benchmark-suites.md: c60d0e1b18aff6d70e814591f5dec40920697504
---
