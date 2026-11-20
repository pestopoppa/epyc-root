---
schema: epyc.brief.v1
id: CS-8.G1B
box_text_sha: ab456a8c2ebe1318
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/speech/g1_cascade/g1_cascade_language.py
- epyc-root:handoffs/active/speech-and-multimodal.md
approach: 'Extend the cascade G1 language screen to de and fr by re-running the SPQ-03 script; frozen binaries read-only;
  files per-language result.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*CS-8.G1B\b' handoffs/active/speech-and-multimodal.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/speech/g1_cascade/g1_cascade_language.py: 03d0b9f9d31b9eed8aa6a5514d83d36dd790dcb7
    epyc-root:handoffs/active/speech-and-multimodal.md: a1ce81c565e416536531ace482c4753f1b356114
---
