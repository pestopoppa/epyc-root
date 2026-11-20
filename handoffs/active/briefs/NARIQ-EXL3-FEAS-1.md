---
schema: epyc.brief.v1
id: NARIQ-EXL3-FEAS-1
box_text_sha: 7c61a52f3024d12b
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/README.md
- epyc-root:handoffs/active/quantization-and-low-bit.md
approach: 'Determine whether the exllamav3 converter can run CPU-only or on MI210 for a small model and cost one agent-trace
  recalibration; note with converter version and hardware path.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*NARIQ-EXL3-FEAS-1\b' handoffs/active/quantization-and-low-bit.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/README.md: 7593c6ea2c3fa6c2d3c6f5057f08fd6ed40b85bb
    epyc-root:handoffs/active/quantization-and-low-bit.md: de85bd28a242412865b75d7baa5d6e48427952f2
---
