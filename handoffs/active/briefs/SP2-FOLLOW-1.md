---
schema: epyc.brief.v1
id: SP2-FOLLOW-1
box_text_sha: f2cb025992e4705b
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:docs/reference/speech/cs43-3-ggml-backend-audit.md
- epyc-root:handoffs/active/speech-and-multimodal.md
approach: 'Threadpool follow-ons: (1) whisper per-token std::thread spawning, (2) parakeet.cpp compute helper in the whisper
  tree; first step is an inventory of thread creations per path.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*SP2-FOLLOW-1\b' handoffs/active/speech-and-multimodal.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:docs/reference/speech/cs43-3-ggml-backend-audit.md: d376c37c5750e53f3fc4c26138d9039b043e2d25
    epyc-root:handoffs/active/speech-and-multimodal.md: a1ce81c565e416536531ace482c4753f1b356114
---
