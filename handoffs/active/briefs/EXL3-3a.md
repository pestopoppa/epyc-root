---
schema: epyc.brief.v1
id: EXL3-3a
box_text_sha: 1569ae27ef0cb93e
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/fixtures.py
- epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/kernels.hip
- epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/verify_host.py
- epyc-root:handoffs/active/quantization-and-low-bit.md
approach: 'Resolve the real-fixture oracle envelope: keep exact wave64 GEMV equality, explain the MFMA mismatch (see EXL3-MFMA-FP16-ENV-1)
  and amend or justify the abs=1e-5/rel=1e-4 envelope; qualification rows in the validation dir.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*EXL3-3a\b' handoffs/active/quantization-and-low-bit.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/fixtures.py: 85b4205b3387219a5bfdc29f9d39a92a4f7d33b1
    epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/kernels.hip: 10cc7690bc1baa7bf6367fd1033ee23fd731ec43
    epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/verify_host.py: 66bc5322457dc34055f2cbe3f0cab1f6e2520325
    epyc-root:handoffs/active/quantization-and-low-bit.md: de85bd28a242412865b75d7baa5d6e48427952f2
---
