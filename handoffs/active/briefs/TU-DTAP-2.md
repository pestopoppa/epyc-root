---
schema: epyc.brief.v1
id: TU-DTAP-2
box_text_sha: cc392dc036308a1c
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/benchmark-suites.md
approach: 'Wire the disposable DTAP runner''s live OpenAI-compatible endpoint mode to a real model under an inference grant,
  then add simulated-service effects. First step: endpoint-mode wiring with a fixture test.

  '
acceptance: grep -qE '^ *- \[x\] \*\*TU\-DTAP\-2\b' handoffs/active/benchmark-suites.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/benchmark-suites.md: c60d0e1b18aff6d70e814591f5dec40920697504
---
