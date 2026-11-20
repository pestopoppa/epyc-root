---
schema: epyc.brief.v1
id: EVL-34
box_text_sha: 4a706dea39932da1
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/context-and-token-economy.md
approach: 'Natural-delegation rerun with a model that must delegate (e.g. ~1.7B front model delegating to worker_general).
  First step: run manifest and model binding per Step 2 next steps.

  '
acceptance: grep -qE '^ *- \[x\] \*\*EVL\-34\b' handoffs/active/context-and-token-economy.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/context-and-token-economy.md: 55a59d4e87cf3920d424f3fb6d879a3b4d8a3801
---
