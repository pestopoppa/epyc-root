---
schema: epyc.brief.v1
id: KPF-17.4d
box_text_sha: 4a08325321f5c08a
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/coordination/kvfork/kpf174d-prospective/bound_custody.py
approach: 'Re-judge GPU c1 FAILs against layout-matched controls with a predeclared near-tie-aware rule before compute. First
  step: write the predeclared rule file, then rerun judge over stored c1 outputs.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KPF\-17\.4d\b' handoffs/active/kv-cache-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/coordination/kvfork/kpf174d-prospective/bound_custody.py: b4b8e8053cdf77de76982dea11969fe6d40d8245
---
