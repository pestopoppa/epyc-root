---
schema: epyc.brief.v1
id: UFH14-B4f
box_text_sha: 9464783dc0d50579
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/vidya/adapters/README.md
- epyc-orchestrator:scripts/analysis/prefix_cache_report.py
approach: 'Add the per-port prefix-cache report rows as a projection under the B5 serving_calls adapter row in scripts/vidya/adapters/README.md
  (row text was prepared at /mnt/raid0/llm/tmp/wrapup-ec-kvu16/INDEX_ROWS.md; if that file is gone, redraft from prefix_cache_report.py''s
  output fields). Read side rides VB-SERVE-TIMING-1. Do not write a new grading rule.

  '
acceptance: grep -q 'prefix_cache_report' scripts/vidya/adapters/README.md
non_goals:
- no new grading rule
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/vidya/adapters/README.md: e3c2ef4730581badb912189e13072542bc78a2cf
    epyc-orchestrator:scripts/analysis/prefix_cache_report.py: dbf69f359009287e90c0db9e6645185adee48d99
---
