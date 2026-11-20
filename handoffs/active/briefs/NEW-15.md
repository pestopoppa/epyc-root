---
schema: epyc.brief.v1
id: NEW-15
box_text_sha: d938fc07173643f6
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:tools/perplexity/perplexity.cpp
- epyc-root:handoffs/active/quantization-and-low-bit.md
approach: 'A/B the asymmetric KV quantizer vs our rotation: -ctk q4_0 symmetric vs asymmetric on the multi-step eval; files
  quality/speed delta.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*NEW-15\b' handoffs/active/quantization-and-low-bit.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:tools/perplexity/perplexity.cpp: 92f88306c74101fb4d0b496d368055d489258eb1
    epyc-root:handoffs/active/quantization-and-low-bit.md: de85bd28a242412865b75d7baa5d6e48427952f2
---
