---
schema: epyc.brief.v1
id: CS-8.STT5-DEVICE-DECLARE
box_text_sha: e9e02f6d5148da8d
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/speech/stt5_transcribe_restore.py
- epyc-root:scripts/speech/stt5_score_baseline.py
- epyc-root:handoffs/active/speech-and-multimodal.md
approach: 'Declare the GPU device (GPU token) or hide the device in a CPU build for the STT5 baseline whisper-cli rows before
  r4 resumes; fix lives in the stt5 transcribe script and the row declaration.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*CS-8.STT5-DEVICE-DECLARE\b' handoffs/active/speech-and-multimodal.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/speech/stt5_transcribe_restore.py: 117d785dcb6c10bb86625dc7fb177f26b2da13fb
    epyc-root:scripts/speech/stt5_score_baseline.py: 8dd697753c012827a200fa9997660e26fd66876d
    epyc-root:handoffs/active/speech-and-multimodal.md: a1ce81c565e416536531ace482c4753f1b356114
---
