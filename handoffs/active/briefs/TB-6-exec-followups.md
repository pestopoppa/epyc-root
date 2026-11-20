---
schema: epyc.brief.v1
id: TB-6-exec-followups
box_text_sha: 30d58ba78dcaecbd
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/context-and-token-economy.md
approach: '(d) per-model kv_bytes/token for every GPU-resident model from the launcher per-buffer VRAM decomposition (SSU-F10)
  or GGUF metadata. First step: script computing bytes/token from GGUF metadata with a test on the :8083 model.

  '
acceptance: grep -qE '^ *- \[x\] \*\*TB\-6\-exec\-followups\b' handoffs/active/context-and-token-economy.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/context-and-token-economy.md: 55a59d4e87cf3920d424f3fb6d879a3b4d8a3801
---
