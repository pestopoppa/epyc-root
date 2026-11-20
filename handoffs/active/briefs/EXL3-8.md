---
schema: epyc.brief.v1
id: EXL3-8
box_text_sha: 98c47d83a445b164
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/runtime.hpp
- epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/test_runtime.hip
- epyc-root:handoffs/active/quantization-and-low-bit.md
approach: 'Epic: failure-atomic HIP registered shared arena, byte-exact DMA, async streams, deterministic teardown; first
  step is the arena ownership/teardown design in runtime.hpp with a host test; only after parity gates.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*EXL3-8\b' handoffs/active/quantization-and-low-bit.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: sol
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/runtime.hpp: 63ea36c260294281134f019755a78fbda3803bb1
    epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/test_runtime.hip: 556ae92e73e20171e4bf14620dbfdd759528e684
    epyc-root:handoffs/active/quantization-and-low-bit.md: de85bd28a242412865b75d7baa5d6e48427952f2
---
