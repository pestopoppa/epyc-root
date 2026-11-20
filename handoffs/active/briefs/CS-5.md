---
schema: epyc.brief.v1
id: CS-5
box_text_sha: 285e2e0df59ee02d
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/speech/cs5_reference_job.py
- epyc-root:scripts/speech/cs5_qwen_reference.py
- epyc-root:scripts/speech/cs5_step_reference.py
- epyc-root:handoffs/active/speech-and-multimodal.md
approach: 'Epic with four sub-rows (p1..p4): first step is CS-5.p1, the gfx90a PyTorch-ROCm device proof, then the sealed
  Qwen and Step JFK reference runs through cs5_reference_job.py. Run is measurement-only per D4; decision it feeds is the
  CS-8 bake-off gate order.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*CS-5\b' handoffs/active/speech-and-multimodal.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/speech/cs5_reference_job.py: d9ccc387fc5594e03a7cc8d7f1bede1af5e74f07
    epyc-root:scripts/speech/cs5_qwen_reference.py: 708cd2f8c232a29eee87bf8901762ba9de9bd5e9
    epyc-root:scripts/speech/cs5_step_reference.py: 80c905e50637ba213cde3df88dfe1ea04ebaf054
    epyc-root:handoffs/active/speech-and-multimodal.md: a1ce81c565e416536531ace482c4753f1b356114
---
