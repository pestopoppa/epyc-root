---
schema: epyc.brief.v1
id: TOC-CMP-10
box_text_sha: 5718d3dd9e2fe472
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/context-and-token-economy.md
approach: 'Step 3 conditional substrate replacement (~400-800 LoC), gated on delegation-positive retest. First step: record
  the gate state and, if positive, the substrate interface stub with a test.

  '
acceptance: grep -qE '^ *- \[x\] \*\*TOC\-CMP\-10\b' handoffs/active/context-and-token-economy.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/context-and-token-economy.md: 55a59d4e87cf3920d424f3fb6d879a3b4d8a3801
---
