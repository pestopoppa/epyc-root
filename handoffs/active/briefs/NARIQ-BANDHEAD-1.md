---
schema: epyc.brief.v1
id: NARIQ-BANDHEAD-1
box_text_sha: 391d8d46b06f8dba
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:tools/perplexity/perplexity.cpp
- epyc-root:handoffs/active/quantization-and-low-bit.md
approach: 'Price a banded output.weight against the served Q38FN Q6_K head using a byte census and the predicted-probability
  ranking; filed table with gather cost and MTP-shared-slab handling; complements QUANT-HEAD-1.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*NARIQ-BANDHEAD-1\b' handoffs/active/quantization-and-low-bit.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:tools/perplexity/perplexity.cpp: 92f88306c74101fb4d0b496d368055d489258eb1
    epyc-root:handoffs/active/quantization-and-low-bit.md: de85bd28a242412865b75d7baa5d6e48427952f2
---
