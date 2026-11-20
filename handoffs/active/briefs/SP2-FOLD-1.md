---
schema: epyc.brief.v1
id: SP2-FOLD-1
box_text_sha: 68c26b6cd01cb66c
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:docs/reference/speech/cs43-3-ggml-backend-audit.md
- epyc-root:handoffs/active/speech-and-multimodal.md
approach: 'Close the threadpool fold evidence: prove the GPU path unregressed on champion tips (qwentts GPU TTFA anchor 37.8
  ms, whisper anchors) and record; evidence-and-record task.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*SP2-FOLD-1\b' handoffs/active/speech-and-multimodal.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:docs/reference/speech/cs43-3-ggml-backend-audit.md: d376c37c5750e53f3fc4c26138d9039b043e2d25
    epyc-root:handoffs/active/speech-and-multimodal.md: a1ce81c565e416536531ace482c4753f1b356114
---
