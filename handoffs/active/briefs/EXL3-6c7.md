---
schema: epyc.brief.v1
id: EXL3-6c7
box_text_sha: 94329a7131653e0f
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/runtime.hpp
- epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/kernels.hip
- epyc-root:handoffs/active/quantization-and-low-bit.md
approach: 'Executor performance items: fold the per-op prep barrier into the producer, merged gate|up with per-segment suh,
  VNNI tier attributes; first step is the prep-barrier fold with a bit-exact test.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*EXL3-6c7\b' handoffs/active/quantization-and-low-bit.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/runtime.hpp: 63ea36c260294281134f019755a78fbda3803bb1
    epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/kernels.hip: 10cc7690bc1baa7bf6367fd1033ee23fd731ec43
    epyc-root:handoffs/active/quantization-and-low-bit.md: de85bd28a242412865b75d7baa5d6e48427952f2
---
