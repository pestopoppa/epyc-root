---
schema: epyc.brief.v1
id: 2b-agentic-smoke
box_text_sha: 59a3c0a52d606ac7
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/eval-tower-program.md
approach: 'Live smoke of the agentic harness on one instance (GPU-gated): step 0 confirm git status --porcelain is empty inside
  the container at the start of trial 2; then one instance end to end. Stop on filed trial result.

  '
acceptance: grep -qE '^ *- \[x\] \*\*2b\-agentic\-smoke\b' handoffs/active/eval-tower-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/eval-tower-program.md: bb00cad949830eca2617a6993062fa6973a6a1df
---
