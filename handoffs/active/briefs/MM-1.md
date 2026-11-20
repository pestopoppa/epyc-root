---
schema: epyc.brief.v1
id: MM-1
box_text_sha: 909a7574665c9b68
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/api/routes/vision.py
- epyc-root:handoffs/active/speech-and-multimodal.md
approach: 'Repoint experiment: set DASHSCOPE_BASE_URL to http://127.0.0.1:8087/v1 with no real key and run the DashScope-client
  path against the local server; record behavior.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*MM-1\b' handoffs/active/speech-and-multimodal.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/api/routes/vision.py: 68d1c3d4b1189b7826f82475163d82c32a603326
    epyc-root:handoffs/active/speech-and-multimodal.md: a1ce81c565e416536531ace482c4753f1b356114
---
