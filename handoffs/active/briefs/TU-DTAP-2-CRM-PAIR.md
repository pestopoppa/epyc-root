---
schema: epyc.brief.v1
id: TU-DTAP-2-CRM-PAIR
box_text_sha: 4d59b7fbe8c17a3b
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/benchmark-suites.md
approach: 'Run and file one source-bound live CRM control/attack diagnostic on Qwen3-0.6B Q8_0 per the box''s pinned model/build/CPU
  server; claim the provider and retain the journal. Stop on filed pair.

  '
acceptance: grep -qE '^ *- \[x\] \*\*TU\-DTAP\-2\-CRM\-PAIR\b' handoffs/active/benchmark-suites.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/benchmark-suites.md: c60d0e1b18aff6d70e814591f5dec40920697504
---
