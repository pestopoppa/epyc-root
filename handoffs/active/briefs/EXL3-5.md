---
schema: epyc.brief.v1
id: EXL3-5
box_text_sha: d598a75bdf98122e
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/runtime.hpp
- epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/contract.hpp
- epyc-root:handoffs/active/quantization-and-low-bit.md
approach: 'Make mixed-K MoE dispatch total and correct: device-visible half-bit K metadata, projection pointer tables, local/global
  expert domains; first step is the metadata struct in runtime.hpp with a host test.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*EXL3-5\b' handoffs/active/quantization-and-low-bit.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/runtime.hpp: 63ea36c260294281134f019755a78fbda3803bb1
    epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/contract.hpp: 822e60f2fde6fd40fc9812fb3cba7163ef3aafb3
    epyc-root:handoffs/active/quantization-and-low-bit.md: de85bd28a242412865b75d7baa5d6e48427952f2
---
