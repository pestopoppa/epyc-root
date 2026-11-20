---
schema: epyc.brief.v1
id: CJ-2e
box_text_sha: ef422bdec061f880
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/benchmark-suites.md
approach: 'Verify livecodebench_v6 discriminates across the fleet (vendor 0.839/0.804/0.804/0.789/0.566/0.771) under a key
  naming the window; run the local arm on >=2 models, paired scoring. Stop when ordering resolves or n exhausted.

  '
acceptance: grep -qE '^ *- \[x\] \*\*CJ\-2e\b' handoffs/active/benchmark-suites.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/benchmark-suites.md: c60d0e1b18aff6d70e814591f5dec40920697504
---
