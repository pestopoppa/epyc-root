---
schema: epyc.brief.v1
id: CS-5.p1
box_text_sha: f2892d4e69356bab
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/speech/cs5_reference_job.py
- epyc-root:handoffs/active/speech-and-multimodal.md
approach: 'Run a minimal torch.zeros(...).cuda() op on gfx90a via the CS-5 job wrapper and record the ROCm stack version and
  a PASS verdict in a device-proof record; stop at first failure. Feeds CS-5.p2/p3.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*CS-5.p1\b' handoffs/active/speech-and-multimodal.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/speech/cs5_reference_job.py: d9ccc387fc5594e03a7cc8d7f1bede1af5e74f07
    epyc-root:handoffs/active/speech-and-multimodal.md: a1ce81c565e416536531ace482c4753f1b356114
---
