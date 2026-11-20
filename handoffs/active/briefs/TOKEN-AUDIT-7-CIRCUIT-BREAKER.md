---
schema: epyc.brief.v1
id: TOKEN-AUDIT-7-CIRCUIT-BREAKER
box_text_sha: adaaa3487c93947b
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/coordination/rowflow/rowflow.py
- epyc-root:scripts/coordination/rowflow2/rowflow2.py
- epyc-root:docs/reports/coordination/token-efficiency-audit-20261106.md
approach: 'Per-row parking exists (MAX_FAILS=3) in frozen rowflow.py; missing: pause the row''s successors until an owner
  clears it. The 2026-11-09 note says the pause half was removed on purpose, so the first step is a Pipeline decision: accept
  per-row parking and close, or add the successor pause in rowflow2 (supersedes link as the successor key). Recommended: close
  with parking only unless a repeat-failure incident recurs.

  '
acceptance: grep -q 'TOKEN-AUDIT-7.*accepted' handoffs/active/engineering-hygiene-backlog.md
non_goals:
- no edit to frozen rowflow.py
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/coordination/rowflow/rowflow.py: 5e76c90af8cfa49c863684663c3ca56084adfa8d
    epyc-root:scripts/coordination/rowflow2/rowflow2.py: 0215c54d7f68f0b039b8d2a697e5801be937d895
    epyc-root:docs/reports/coordination/token-efficiency-audit-20261106.md: 9d80ad333472cffc83b29dd3c4789273c896f237
---
