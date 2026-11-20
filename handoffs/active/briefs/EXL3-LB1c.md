---
schema: epyc.brief.v1
id: EXL3-LB1c
box_text_sha: 67995ae4c01de23f
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/benchmark/bench_canonical.sh
- epyc-llama:ggml/src/ggml-cuda/mmvq.cu
- epyc-root:handoffs/active/quantization-and-low-bit.md
approach: 'Time MMVQ vs MMQ at ne11 4-9 for Q4_K, Q6_K, IQ4_XS, IQ4_NL, IQ3_S (+Q5_K/Q3_K ref) at 27B and gemma-4-31B real
  shapes on gfx90a; set per-type crossover thresholds; files table.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*EXL3-LB1c\b' handoffs/active/quantization-and-low-bit.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/benchmark/bench_canonical.sh: d1c5a7becae27de77f61785af7e9420809a6ede4
    epyc-llama:ggml/src/ggml-cuda/mmvq.cu: 77f711be4fd5b88e514d3f4ecfb3c91e9346164f
    epyc-root:handoffs/active/quantization-and-low-bit.md: de85bd28a242412865b75d7baa5d6e48427952f2
---
