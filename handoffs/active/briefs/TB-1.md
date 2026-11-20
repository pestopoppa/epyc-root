---
schema: epyc.brief.v1
id: TB-1
box_text_sha: 6c8bf11cadd6da65
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/backends/serving_params.py
approach: 'Per-model budget curve on a truncation-inducing suite for each stack model. First step: sweep manifest per model;
  stop on filed curves.

  '
acceptance: grep -qE '^ *- \[x\] \*\*TB\-1\b' handoffs/active/context-and-token-economy.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/backends/serving_params.py: bc1361d931cf2e226e9cbdef19e936742c112c93
---
