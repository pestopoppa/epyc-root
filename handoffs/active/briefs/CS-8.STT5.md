---
schema: epyc.brief.v1
id: CS-8.STT5
box_text_sha: a4a4528d2349f1fc
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/speech/stt_bakeoff/scorer.py
- epyc-root:scripts/speech/stt5_score_unified.py
- epyc-root:handoffs/active/speech-and-multimodal.md
approach: 'STT accuracy screen on public anchors, pre-declared in a run-plan commit; stop on answer; ranks and rejects only;
  files per-arm WER with CI.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*CS-8.STT5\b' handoffs/active/speech-and-multimodal.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/speech/stt_bakeoff/scorer.py: 55ae505033b3a33274f8e57d5a8afe6d6ca3c264
    epyc-root:scripts/speech/stt5_score_unified.py: f2a885037eed621c0ef66a62b83cd83e2947d437
    epyc-root:handoffs/active/speech-and-multimodal.md: a1ce81c565e416536531ace482c4753f1b356114
---
