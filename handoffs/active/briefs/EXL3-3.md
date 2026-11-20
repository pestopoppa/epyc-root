---
schema: epyc.brief.v1
id: EXL3-3
box_text_sha: 55f81aece1bca82c
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/build.py
- epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/kernels.hip
- epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/contract.hpp
- epyc-root:handoffs/active/quantization-and-low-bit.md
approach: 'Epic: first step is freezing the ROCm 6.2 build contract through build.py (compiler, target ID, code-object version,
  XNACK/SRAMECC, object hash, disassembly) and recording it; GEMV validation follows.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*EXL3-3\b' handoffs/active/quantization-and-low-bit.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/build.py: 9ae405683275eea7691de05bb8fd524c0e2dbef5
    epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/kernels.hip: 10cc7690bc1baa7bf6367fd1033ee23fd731ec43
    epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/contract.hpp: 822e60f2fde6fd40fc9812fb3cba7163ef3aafb3
    epyc-root:handoffs/active/quantization-and-low-bit.md: de85bd28a242412865b75d7baa5d6e48427952f2
---
