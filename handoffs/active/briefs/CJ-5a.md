---
schema: epyc.brief.v1
id: CJ-5a
box_text_sha: 7cde2d72e3b5f263
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:proposed/cj567/PUBLIC-REGISTRATION.md
approach: 'Record each local result under an explicit benchmark key in the public_benchmarks.yaml schema (local_benchmarks
  / absent_from_card), never merging keys; use the lane-local public_benchmark_registration.py validator (22 synthetic controls
  pass). First step: land review fragments for results that exist.

  '
acceptance: grep -qE '^ *- \[x\] \*\*CJ\-5a\b' handoffs/active/benchmark-suites.md
non_goals:
- no scope beyond the box text
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:proposed/cj567/PUBLIC-REGISTRATION.md: 8a83068e08afc27c01f84351a5eecd51c4f14480
---
