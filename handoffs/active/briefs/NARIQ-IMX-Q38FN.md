---
schema: epyc.brief.v1
id: NARIQ-IMX-Q38FN
box_text_sha: 400f581c6a388492
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:tools/perplexity/perplexity.cpp
- epyc-root:handoffs/active/quantization-and-low-bit.md
approach: 'If the pilot keeps: re-imatrix the served Q38FN UD-IQ4_XS recipe on agent traces and compare masked/unmasked KLD
  vs current with fixed bytes/types; files table.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*NARIQ-IMX-Q38FN\b' handoffs/active/quantization-and-low-bit.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:tools/perplexity/perplexity.cpp: 92f88306c74101fb4d0b496d368055d489258eb1
    epyc-root:handoffs/active/quantization-and-low-bit.md: de85bd28a242412865b75d7baa5d6e48427952f2
---
