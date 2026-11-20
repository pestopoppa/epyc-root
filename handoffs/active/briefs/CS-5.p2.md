---
schema: epyc.brief.v1
id: CS-5.p2
box_text_sha: 08d5465cd546b888
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/speech/cs5_reference_job.py
- epyc-root:scripts/speech/cs5_qwen_reference.py
- epyc-root:handoffs/active/speech-and-multimodal.md
approach: 'Seal the Qwen3-Omni env and input stat receipts at revision 26291f79, run one public JFK turn through cs5_reference_job.py,
  stop at the first terminal load/native/admission failure or the deadline; record a CS-3 record with a live co-tenant sample.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*CS-5.p2\b' handoffs/active/speech-and-multimodal.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/speech/cs5_reference_job.py: d9ccc387fc5594e03a7cc8d7f1bede1af5e74f07
    epyc-root:scripts/speech/cs5_qwen_reference.py: 708cd2f8c232a29eee87bf8901762ba9de9bd5e9
    epyc-root:handoffs/active/speech-and-multimodal.md: a1ce81c565e416536531ace482c4753f1b356114
---
