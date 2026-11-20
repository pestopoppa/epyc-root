---
schema: epyc.brief.v1
id: CS-5.p4
box_text_sha: 4572aedf58cacecf
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/speech/cs5_reference_job.py
- epyc-root:handoffs/active/speech-and-multimodal.md
approach: 'Package reference-run outputs and publish the CS-5 qualification row citing the device proof and CS-3 records;
  leave parent CS-5 unticked for both arms and gfx90a.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*CS-5.p4\b' handoffs/active/speech-and-multimodal.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/speech/cs5_reference_job.py: d9ccc387fc5594e03a7cc8d7f1bede1af5e74f07
    epyc-root:handoffs/active/speech-and-multimodal.md: a1ce81c565e416536531ace482c4753f1b356114
---
