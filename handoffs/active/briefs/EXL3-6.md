---
schema: epyc.brief.v1
id: EXL3-6
box_text_sha: 0e3bcb31df3ff4bf
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/kernels.hip
- epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/runtime.hpp
- epyc-root:handoffs/active/quantization-and-low-bit.md
approach: 'Parked for the 27B. If reopened: integrate exactly one EXL3 operator into fresh experimental llama.cpp; first step
  is operator-table registration only with a parity test; gated on a model that wants it.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*EXL3-6\b' handoffs/active/quantization-and-low-bit.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: sol
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/kernels.hip: 10cc7690bc1baa7bf6367fd1033ee23fd731ec43
    epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/runtime.hpp: 63ea36c260294281134f019755a78fbda3803bb1
    epyc-root:handoffs/active/quantization-and-low-bit.md: de85bd28a242412865b75d7baa5d6e48427952f2
---
