---
schema: epyc.brief.v1
id: DCP-10
box_text_sha: e5a2daded21d598c
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/context_discovery.py
approach: 'Zero-decode discovery scoring on ContextBench: per instance shallow checkout at base_commit (CONTEXTBENCH_TMP_ROOT
  on raid), run discover_candidates (src/context_discovery.py:96), score. First step: the per-instance scorer script with
  a 2-instance fixture test.

  '
acceptance: grep -qE '^ *- \[x\] \*\*DCP\-10\b' handoffs/active/context-and-token-economy.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/context_discovery.py: 923e748929bb163f2c45446b75a24e2528b9c7af
---
