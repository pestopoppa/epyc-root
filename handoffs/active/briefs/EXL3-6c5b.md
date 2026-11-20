---
schema: epyc.brief.v1
id: EXL3-6c5b
box_text_sha: 1c8834ad71563ffa
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/kernel_rnd/exl3/evidence.py
- epyc-root:handoffs/active/quantization-and-low-bit.md
approach: 'Decide what the p1 smoke FAIL means: read the first-divergence token top-2 margin from the staged texts; verdict:
  numeric-noise vs defect; files the verdict.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*EXL3-6c5b\b' handoffs/active/quantization-and-low-bit.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/exl3/evidence.py: 34bd146d8b8c1109d3f7e6a13aae32915ff29bdd
    epyc-root:handoffs/active/quantization-and-low-bit.md: de85bd28a242412865b75d7baa5d6e48427952f2
---
