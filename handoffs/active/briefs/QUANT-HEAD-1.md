---
schema: epyc.brief.v1
id: QUANT-HEAD-1
box_text_sha: df843358deab1b55
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:tools/perplexity/perplexity.cpp
- epyc-inference-research:scripts/benchmark/bench_canonical.sh
- epyc-root:handoffs/active/quantization-and-low-bit.md
approach: 'AutoKernel-owned: audit and price 4-bit output.weight/token_embd on served GGUFs; first step is the byte-census
  over the served recipes then the AK seed AK-QH-A/B; files priced table.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*QUANT-HEAD-1\b' handoffs/active/quantization-and-low-bit.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:tools/perplexity/perplexity.cpp: 92f88306c74101fb4d0b496d368055d489258eb1
    epyc-inference-research:scripts/benchmark/bench_canonical.sh: d1c5a7becae27de77f61785af7e9420809a6ede4
    epyc-root:handoffs/active/quantization-and-low-bit.md: de85bd28a242412865b75d7baa5d6e48427952f2
---
