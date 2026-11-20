---
schema: epyc.brief.v1
id: EXL3-X0c
box_text_sha: f313c715908c9d32
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/benchmark/bench_canonical.sh
- epyc-root:handoffs/active/quantization-and-low-bit.md
approach: 'Re-run the X0 production-shape comparison (Q8_0 vs Q4_K_M and seed-#1 arm), 3 launches per arm ABA at ~2k and ~50k,
  temp0 and default sampling; files tok/s with CI; bounded by the pre-registered rule.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*EXL3-X0c\b' handoffs/active/quantization-and-low-bit.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/benchmark/bench_canonical.sh: d1c5a7becae27de77f61785af7e9420809a6ede4
    epyc-root:handoffs/active/quantization-and-low-bit.md: de85bd28a242412865b75d7baa5d6e48427952f2
---
