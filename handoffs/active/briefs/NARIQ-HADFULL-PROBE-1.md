---
schema: epyc.brief.v1
id: NARIQ-HADFULL-PROBE-1
box_text_sha: 282d89b1c5dbc08a
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/benchmark/answer_scoring.py
- epyc-root:handoffs/active/quantization-and-low-bit.md
approach: 'Offline probe of Qwen3-4B-Instruct-2507 BF16 width-2560 weights: relative quantization error after 128-block Hadamard
  vs whole-slice Paley-20 rotation at fixed scalar bits; numpy script; per-tensor table plus verdict.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*NARIQ-HADFULL-PROBE-1\b' handoffs/active/quantization-and-low-bit.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/benchmark/answer_scoring.py: bb1e0fe958e16a945df56dc373cdfa7dfb1a1f90
    epyc-root:handoffs/active/quantization-and-low-bit.md: de85bd28a242412865b75d7baa5d6e48427952f2
---
