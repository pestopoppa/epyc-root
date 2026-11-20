---
schema: epyc.brief.v1
id: NEW-6
box_text_sha: f417c2e5c678d243
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-llama:ggml/src/ggml-cpu/iqk/iqk_gemm_iquants.cpp
- epyc-llama:ggml/src/ggml-cpu/iqk/iqk_mul_mat.cpp
- epyc-root:handoffs/active/quantization-and-low-bit.md
approach: 'Prefill headroom bundle: (a) func16 16-wide IQ kernels, (b) gated convert path, etc; first step (a): add func16
  for one IQ type in iqk and a bit-exact test on an experimental branch.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*NEW-6\b' handoffs/active/quantization-and-low-bit.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-llama:ggml/src/ggml-cpu/iqk/iqk_gemm_iquants.cpp: 45946a790f45f5ffd04558ab8076a268a87f561d
    epyc-llama:ggml/src/ggml-cpu/iqk/iqk_mul_mat.cpp: 3615388cf98bf402dbf0d2e0bd76869bcbe48b87
    epyc-root:handoffs/active/quantization-and-low-bit.md: de85bd28a242412865b75d7baa5d6e48427952f2
---
