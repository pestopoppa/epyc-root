---
schema: epyc.brief.v1
id: TU-MH-1
box_text_sha: a1c5bbd2ddcf543e
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/benchmark-suites.md
approach: 'Parameterize the HS-4 fixture runner and add an external driver with REPL (/chat) and OpenCode adapters. First
  step: locate the HS-4 runner (not found by name in orchestrator or research scripts) and add the adapter interface.

  '
acceptance: grep -qE '^ *- \[x\] \*\*TU\-MH\-1\b' handoffs/active/benchmark-suites.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/benchmark-suites.md: c60d0e1b18aff6d70e814591f5dec40920697504
---
