---
schema: epyc.brief.v1
id: C-L3-Q38FN
box_text_sha: c966b8aa999a8e59
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/benchmark/bench_canonical.sh
- epyc-llama:tools/perplexity/perplexity.cpp
- epyc-root:handoffs/active/quantization-and-low-bit.md
approach: 'Make Q38FN low-bit decode faster than the served recipe: evidence NEW-13 PASS recovers 28% of KLD gap; first step
  is the IQ3_XXS decode arm speed A/B on the quiet host; files tok/s and KLD.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*C-L3-Q38FN\b' handoffs/active/quantization-and-low-bit.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/benchmark/bench_canonical.sh: d1c5a7becae27de77f61785af7e9420809a6ede4
    epyc-llama:tools/perplexity/perplexity.cpp: 92f88306c74101fb4d0b496d368055d489258eb1
    epyc-root:handoffs/active/quantization-and-low-bit.md: de85bd28a242412865b75d7baa5d6e48427952f2
---
