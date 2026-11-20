---
schema: epyc.brief.v1
id: CS-8.G1B-CUSTODY-20261101
box_text_sha: 9626ad2f2c5a5753
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/speech/stt_bakeoff/custody.py
- epyc-root:handoffs/active/speech-and-multimodal.md
approach: 'Bind and qualify the predeclared Whisper screen using the intermediate review input binding (520-cell audit); first
  step is custody qualification via stt_bakeoff/custody.py.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*CS-8.G1B-CUSTODY-20261101\b' handoffs/active/speech-and-multimodal.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/speech/stt_bakeoff/custody.py: 26a6cd7450591b2402c761c723d78d9daedfcab2
    epyc-root:handoffs/active/speech-and-multimodal.md: a1ce81c565e416536531ace482c4753f1b356114
---
