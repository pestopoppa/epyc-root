---
schema: epyc.brief.v1
id: CS-8
box_text_sha: 013bd42fcb8f962a
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/speech/cs5_reference_job.py
- epyc-inference-research:scripts/speech/stt_bakeoff/scorer.py
- epyc-root:handoffs/active/speech-and-multimodal.md
approach: 'Epic: first step is CS-8.p1 (run the bake-off in gate order on the CS-5 harness with the cascade as same-clip baseline,
  stop at first failed gate). Needs CS-5 outputs first.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*CS-8\b' handoffs/active/speech-and-multimodal.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/speech/cs5_reference_job.py: d9ccc387fc5594e03a7cc8d7f1bede1af5e74f07
    epyc-inference-research:scripts/speech/stt_bakeoff/scorer.py: 55ae505033b3a33274f8e57d5a8afe6d6ca3c264
    epyc-root:handoffs/active/speech-and-multimodal.md: a1ce81c565e416536531ace482c4753f1b356114
---
