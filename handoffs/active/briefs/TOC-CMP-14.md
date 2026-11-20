---
schema: epyc.brief.v1
id: TOC-CMP-14
box_text_sha: a04ab41a73e3af2e
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:tests/unit/test_features.py
approach: 'Operator enable decision on the compaction-quality flag set: not a brief

  '
acceptance: grep -qE '^ *- \[x\] \*\*TOC\-CMP\-14\b' handoffs/active/context-and-token-economy.md
non_goals:
- no scope beyond the box text
tier: sol
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:tests/unit/test_features.py: fa930fd770f1fbefbae07b9ba4713d0d9ceafe55
---
