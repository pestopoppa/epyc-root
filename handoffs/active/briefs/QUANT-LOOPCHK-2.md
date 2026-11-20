---
schema: epyc.brief.v1
id: QUANT-LOOPCHK-2
box_text_sha: bcfffe2c5bcf5e55
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/benchmark/bench_canonical.sh
- epyc-inference-research:scripts/benchmark/answer_scoring.py
- epyc-root:handoffs/active/quantization-and-low-bit.md
approach: 'Run the loop/truncation counter (QUANT-LOOPCHK-1) once on the incumbent 27B low-bit arm vs Q8_0 to calibrate the
  secondary gate; files rates.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*QUANT-LOOPCHK-2\b' handoffs/active/quantization-and-low-bit.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/benchmark/bench_canonical.sh: d1c5a7becae27de77f61785af7e9420809a6ede4
    epyc-inference-research:scripts/benchmark/answer_scoring.py: bb1e0fe958e16a945df56dc373cdfa7dfb1a1f90
    epyc-root:handoffs/active/quantization-and-low-bit.md: de85bd28a242412865b75d7baa5d6e48427952f2
---
