---
schema: epyc.brief.v1
id: CS-8.STT2
box_text_sha: b7058f4973aeba5a
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/speech/stt_bakeoff/scorer.py
- epyc-root:handoffs/active/speech-and-multimodal.md
approach: 'Build the candidate STT runners CPU-first in experimental directories (never in a frozen speech tree); first step
  is transcribe.cpp at the pinned commit; files build receipts.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*CS-8.STT2\b' handoffs/active/speech-and-multimodal.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/speech/stt_bakeoff/scorer.py: 55ae505033b3a33274f8e57d5a8afe6d6ca3c264
    epyc-root:handoffs/active/speech-and-multimodal.md: a1ce81c565e416536531ace482c4753f1b356114
---
