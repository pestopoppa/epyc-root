---
schema: epyc.brief.v1
id: DCP-12
box_text_sha: b098741b2a76b7b1
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:scripts/autopilot/paired_stats.py
approach: 'DCP-6 power prerequisite: >=2 identical-arm reruns of the same role+prompt set to measure local run-to-run flip
  rate, then size the paired sample for exact McNemar. First step: rerun manifest and the sizing calculator with a unit test.

  '
acceptance: grep -qE '^ *- \[x\] \*\*DCP\-12\b' handoffs/active/context-and-token-economy.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:scripts/autopilot/paired_stats.py: faba05796e424014a3291d92432927c6fc28fed4
---
