---
schema: epyc.brief.v1
id: CJ-6e
box_text_sha: fa6c35ae61610b3d
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:scripts/autopilot/paired_stats.py
approach: 'Record the IFBench noise floor before wiring (n=300: 0.33pp/item, paired CI) via scripts/autopilot/paired_stats.py;
  second fleet arm Qwen3.6-35B-A3B-MTP-Q8_0 CPU. Stop when paired noise floor is filed.

  '
acceptance: grep -qE '^ *- \[x\] \*\*CJ\-6e\b' handoffs/active/benchmark-suites.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:scripts/autopilot/paired_stats.py: faba05796e424014a3291d92432927c6fc28fed4
---
