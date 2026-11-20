---
schema: epyc.brief.v1
id: TB-6-exec
box_text_sha: 8e581835ab982673
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/context-and-token-economy.md
approach: 'A2/CPU np x context surface on Qwen3.8-Flash-Next UD-IQ4_XS on architect_general (handed to CPU lineage). First
  step: sweep manifest for the surface; stop on filed surface.

  '
acceptance: grep -qE '^ *- \[x\] \*\*TB\-6\-exec\b' handoffs/active/context-and-token-economy.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/context-and-token-economy.md: 55a59d4e87cf3920d424f3fb6d879a3b4d8a3801
---
