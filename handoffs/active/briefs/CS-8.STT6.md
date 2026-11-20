---
schema: epyc.brief.v1
id: CS-8.STT6
box_text_sha: d0244d897780c66e
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/speech/stt_bakeoff/scorer.py
- epyc-inference-research:scripts/speech/stt_bakeoff/private_custody.py
- epyc-root:handoffs/active/speech-and-multimodal.md
approach: 'Confirmation run of advancing STT arms on the private CS-4 confirmation stratum touched once; needs operator-recorded
  human set; files WER with CI.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*CS-8.STT6\b' handoffs/active/speech-and-multimodal.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/speech/stt_bakeoff/scorer.py: 55ae505033b3a33274f8e57d5a8afe6d6ca3c264
    epyc-inference-research:scripts/speech/stt_bakeoff/private_custody.py: 53084ce44a70d8c7c231f9d927d2dc379d3a8c74
    epyc-root:handoffs/active/speech-and-multimodal.md: a1ce81c565e416536531ace482c4753f1b356114
---
