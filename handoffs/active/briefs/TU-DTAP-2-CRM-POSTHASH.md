---
schema: epyc.brief.v1
id: TU-DTAP-2-CRM-POSTHASH
box_text_sha: 34b972e5643eacaa
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/benchmark-suites.md
approach: 'After CRM-PAIR closes its provider claim, run pinned crm_posthash.py in a separate claimed CPU row to verify the
  model post-capture.

  '
acceptance: grep -qE '^ *- \[x\] \*\*TU\-DTAP\-2\-CRM\-POSTHASH\b' handoffs/active/benchmark-suites.md
non_goals:
- no scope beyond the box text
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/benchmark-suites.md: c60d0e1b18aff6d70e814591f5dec40920697504
---
