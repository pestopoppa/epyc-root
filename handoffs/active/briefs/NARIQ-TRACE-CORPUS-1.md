---
schema: epyc.brief.v1
id: NARIQ-TRACE-CORPUS-1
box_text_sha: 09ba0359e44151f9
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/benchmark/answer_scoring.py
- epyc-root:handoffs/active/quantization-and-low-bit.md
approach: 'Generate an agent-trace calibration corpus with per-token model-written masks from a local model on our own harness;
  files corpus plus README under /mnt/raid0/llm/tmp/nariq-calib/.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*NARIQ-TRACE-CORPUS-1\b' handoffs/active/quantization-and-low-bit.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/benchmark/answer_scoring.py: bb1e0fe958e16a945df56dc373cdfa7dfb1a1f90
    epyc-root:handoffs/active/quantization-and-low-bit.md: de85bd28a242412865b75d7baa5d6e48427952f2
---
