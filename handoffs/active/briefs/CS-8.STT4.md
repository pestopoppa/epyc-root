---
schema: epyc.brief.v1
id: CS-8.STT4
box_text_sha: 4a3a2f9ebd15d2de
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/speech/stt_bakeoff/scorer.py
- epyc-root:handoffs/active/speech-and-multimodal.md
approach: 'gfx90a HIP builds of the runners that passed STT2 with residency proof and CPU-identity gates; files build and
  identity receipts.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*CS-8.STT4\b' handoffs/active/speech-and-multimodal.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/speech/stt_bakeoff/scorer.py: 55ae505033b3a33274f8e57d5a8afe6d6ca3c264
    epyc-root:handoffs/active/speech-and-multimodal.md: a1ce81c565e416536531ace482c4753f1b356114
---
