---
schema: epyc.brief.v1
id: MF-RR-1
box_text_sha: 18ed5ec39e2bc797
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/benchmark-suites.md
approach: 'Reasoning-runaway repair: on token cap with no code/tool call retry with thinking disabled and a single-concise-action
  prompt (extends the one-shot retry at helpers.py:969-997). First step: measure runaway rate from logs, then implement with
  a unit test.

  '
acceptance: grep -qE '^ *- \[x\] \*\*MF\-RR\-1\b' handoffs/active/benchmark-suites.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/benchmark-suites.md: c60d0e1b18aff6d70e814591f5dec40920697504
---
