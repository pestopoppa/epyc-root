---
schema: epyc.brief.v1
id: EXL3-7
box_text_sha: ea20c0246d678cb6
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/benchmark/bench_canonical.sh
- epyc-root:handoffs/active/quantization-and-low-bit.md
approach: 'Parked with EXL3-6: sweep scalar/ISA tier, cores, NUMA, huge pages, layout, K, expert shape on EPYC; files per-regime
  table.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*EXL3-7\b' handoffs/active/quantization-and-low-bit.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/benchmark/bench_canonical.sh: d1c5a7becae27de77f61785af7e9420809a6ede4
    epyc-root:handoffs/active/quantization-and-low-bit.md: de85bd28a242412865b75d7baa5d6e48427952f2
---
