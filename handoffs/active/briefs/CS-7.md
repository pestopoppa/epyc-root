---
schema: epyc.brief.v1
id: CS-7
box_text_sha: 9e9b4503e8b78315
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:docs/reference/speech/cs6-second-gpu-bench-plan.md
- epyc-root:handoffs/active/speech-and-multimodal.md
approach: 'Blocked on the second MI210 install (external event). When it lands: run the device census, place the host lane
  per the CS-6 bench plan, record the verification row. Brief covers the verification prep only.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*CS-7\b' handoffs/active/speech-and-multimodal.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:docs/reference/speech/cs6-second-gpu-bench-plan.md: a9d9508cc7dd29183e3a9a9253dff1da3fe37729
    epyc-root:handoffs/active/speech-and-multimodal.md: a1ce81c565e416536531ace482c4753f1b356114
---
