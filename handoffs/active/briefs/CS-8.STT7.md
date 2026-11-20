---
schema: epyc.brief.v1
id: CS-8.STT7
box_text_sha: a4a90b75fb11f0bc
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/speech/stt_bakeoff/fitting_screen.py
- epyc-root:handoffs/active/speech-and-multimodal.md
approach: 'Predictions-only benchmark-fitting screen and rank-delta signal for STT arms using fitting_screen.py; check first
  whether Open ASR leaderboard manifests exist; reports only.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*CS-8.STT7\b' handoffs/active/speech-and-multimodal.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/speech/stt_bakeoff/fitting_screen.py: 606b42bd71f7a6bcdda8d0f4c6625743508fdf2b
    epyc-root:handoffs/active/speech-and-multimodal.md: a1ce81c565e416536531ace482c4753f1b356114
---
