---
schema: epyc.brief.v1
id: CS-5.p3
box_text_sha: 36e07b34a197074d
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/speech/cs5_reference_job.py
- epyc-root:scripts/speech/cs5_step_reference.py
- epyc-root:handoffs/active/speech-and-multimodal.md
approach: 'Same as CS-5.p2 for Step-Audio-2-mini at its pinned native source with the same stop rule.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*CS-5.p3\b' handoffs/active/speech-and-multimodal.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/speech/cs5_reference_job.py: d9ccc387fc5594e03a7cc8d7f1bede1af5e74f07
    epyc-root:scripts/speech/cs5_step_reference.py: 80c905e50637ba213cde3df88dfe1ea04ebaf054
    epyc-root:handoffs/active/speech-and-multimodal.md: a1ce81c565e416536531ace482c4753f1b356114
---
