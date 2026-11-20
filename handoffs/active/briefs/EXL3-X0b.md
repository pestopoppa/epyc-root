---
schema: epyc.brief.v1
id: EXL3-X0b
box_text_sha: a0dc8e4779da6df8
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/benchmark/bench_canonical.sh
- epyc-root:handoffs/active/quantization-and-low-bit.md
approach: 'Operator decision gate: only reopen the 27B GGUF quant decision if AutoKernel unlocks large low-quant gains; brief
  covers the prep (collect the AK gain evidence and re-run the X0 rule), the decision stays the operator.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*EXL3-X0b\b' handoffs/active/quantization-and-low-bit.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/benchmark/bench_canonical.sh: d1c5a7becae27de77f61785af7e9420809a6ede4
    epyc-root:handoffs/active/quantization-and-low-bit.md: de85bd28a242412865b75d7baa5d6e48427952f2
---
