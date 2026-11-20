---
schema: epyc.brief.v1
id: CJ-3e
box_text_sha: e2e831c8b70c4075
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/benchmark-suites.md
approach: 'Run BFCL under ONE key across >=2 models (baseline tool_compliance_local 70.4-85.2%); native second arm Qwen3.6-35B-A3B-MTP-Q8_0
  on v10 CPU per the box contract. Stop when ordering is resolved or n exhausted.

  '
acceptance: grep -qE '^ *- \[x\] \*\*CJ\-3e\b' handoffs/active/benchmark-suites.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/benchmark-suites.md: c60d0e1b18aff6d70e814591f5dec40920697504
---
