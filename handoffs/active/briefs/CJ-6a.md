---
schema: epyc.brief.v1
id: CJ-6a
box_text_sha: 6e0d253978c8cc15
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/benchmark-suites.md
approach: 'IFBench: acquire allenai/IFBench corpus (300 prompts, size on disk), then first wiring arm on Qwen3.8-27B-Q8_0
  CPU quarter, temp 0, seed 20261031, reasoning off, max 4096; scoring judge-free. Stop when the 300 are scored.

  '
acceptance: grep -qE '^ *- \[x\] \*\*CJ\-6a\b' handoffs/active/benchmark-suites.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/benchmark-suites.md: c60d0e1b18aff6d70e814591f5dec40920697504
---
