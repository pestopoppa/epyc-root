---
schema: epyc.brief.v1
id: EXL3-LB1b
box_text_sha: 02b4a810bab502bd
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/benchmark/bench_canonical.sh
- epyc-root:handoffs/active/quantization-and-low-bit.md
approach: 'Re-run 27B llama-bench pp4-pp16 with 3 B runs using the 10-04 harness and argv; pass = production-shape decode
  gain holds; files tok/s table.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*EXL3-LB1b\b' handoffs/active/quantization-and-low-bit.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/benchmark/bench_canonical.sh: d1c5a7becae27de77f61785af7e9420809a6ede4
    epyc-root:handoffs/active/quantization-and-low-bit.md: de85bd28a242412865b75d7baa5d6e48427952f2
---
