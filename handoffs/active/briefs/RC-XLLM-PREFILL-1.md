---
schema: epyc.brief.v1
id: RC-XLLM-PREFILL-1
box_text_sha: c888401d8fb82858
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/context-and-token-economy.md
approach: 'Execute the smallest released bound native teacher/student endpoint-prefill smoke: resolve Part II S teacher directory
  artifact and matching student from the pinned catalog. First step: resolver script with a fixture check, then the smoke.

  '
acceptance: grep -qE '^ *- \[x\] \*\*RC\-XLLM\-PREFILL\-1\b' handoffs/active/context-and-token-economy.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/context-and-token-economy.md: 55a59d4e87cf3920d424f3fb6d879a3b4d8a3801
---
