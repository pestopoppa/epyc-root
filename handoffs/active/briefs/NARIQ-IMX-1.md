---
schema: epyc.brief.v1
id: NARIQ-IMX-1
box_text_sha: a1a5a073ea43f76b
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:tools/perplexity/perplexity.cpp
- epyc-root:handoffs/active/quantization-and-low-bit.md
approach: 'Recalibrate IQ4_XS and Q4_K of Qwen3-4B-Instruct-2507 with an agent-trace imatrix vs wiki imatrix; score masked/unmasked
  KLD vs BF16 plus EAR (needs KLD-MASK-1 build); files table.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*NARIQ-IMX-1\b' handoffs/active/quantization-and-low-bit.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:tools/perplexity/perplexity.cpp: 92f88306c74101fb4d0b496d368055d489258eb1
    epyc-root:handoffs/active/quantization-and-low-bit.md: de85bd28a242412865b75d7baa5d6e48427952f2
---
