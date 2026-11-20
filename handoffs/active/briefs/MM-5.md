---
schema: epyc.brief.v1
id: MM-5
box_text_sha: 1b785876f77d2df9
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/api/routes/chat_vision.py
- epyc-root:handoffs/active/speech-and-multimodal.md
approach: 'Dynamic-resolution normalisation for our own VL path; first step is a resize-policy function in the vision route
  with a unit test.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*MM-5\b' handoffs/active/speech-and-multimodal.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/api/routes/chat_vision.py: 2e3310aaa28908e10c17709f80744145567ba642
    epyc-root:handoffs/active/speech-and-multimodal.md: a1ce81c565e416536531ace482c4753f1b356114
---
