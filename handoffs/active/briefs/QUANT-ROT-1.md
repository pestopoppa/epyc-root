---
schema: epyc.brief.v1
id: QUANT-ROT-1
box_text_sha: 579126a7dec8dd2b
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:tools/perplexity/perplexity.cpp
- epyc-root:handoffs/active/quantization-and-low-bit.md
approach: 'AutoKernel-owned: offline activation-rotation probe at fixed per-32-block budget (seed AK-QR-1); first step is
  the probe script on one tensor set; files error table.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*QUANT-ROT-1\b' handoffs/active/quantization-and-low-bit.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:tools/perplexity/perplexity.cpp: 92f88306c74101fb4d0b496d368055d489258eb1
    epyc-root:handoffs/active/quantization-and-low-bit.md: de85bd28a242412865b75d7baa5d6e48427952f2
---
