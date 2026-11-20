---
schema: epyc.brief.v1
id: EXL3-LB1
box_text_sha: 77ff8705aff0b08d
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/benchmark/bench_canonical.sh
- epyc-llama:ggml/src/ggml-cuda/mmvq.cu
- epyc-root:handoffs/active/quantization-and-low-bit.md
approach: 'Epic: low-bit GPU decode kernels as an AutoKernel GPU target; first step is LB1b (confirm seed #1 at production
  shape) then LB1c per-type MMVQ-vs-MMQ sweep.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*EXL3-LB1\b' handoffs/active/quantization-and-low-bit.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/benchmark/bench_canonical.sh: d1c5a7becae27de77f61785af7e9420809a6ede4
    epyc-llama:ggml/src/ggml-cuda/mmvq.cu: 77f711be4fd5b88e514d3f4ecfb3c91e9346164f
    epyc-root:handoffs/active/quantization-and-low-bit.md: de85bd28a242412865b75d7baa5d6e48427952f2
---
