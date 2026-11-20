---
schema: epyc.brief.v1
id: CS-8.RT1
box_text_sha: 7000730da6c40d53
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:docs/reference/speech/turn-taking-measurands.md
- epyc-root:handoffs/active/speech-and-multimodal.md
approach: 'Measure /v1/realtime first-output latency and turn contract on EPYC CPU quarter and MI210 with the STT8 scratch
  build and LFM3-Audio-2B; files latency table.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*CS-8.RT1\b' handoffs/active/speech-and-multimodal.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:docs/reference/speech/turn-taking-measurands.md: 88ec1fe3d9a0f1833a164a0ce52ba17a4dc00473
    epyc-root:handoffs/active/speech-and-multimodal.md: a1ce81c565e416536531ace482c4753f1b356114
---
