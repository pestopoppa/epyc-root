---
schema: epyc.brief.v1
id: VKRC-BYTES-PLAUSIBLE
box_text_sha: t:1895c8c2acd632df
author: intake
written: '2026-11-25'
accepted: owner
where:
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/census_extract.py::extract_verify_roofline
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/testdata/census/verify_roofline.RESULT.json
approach: 'Add a pure function plausibility(rows, peak_gbps, footprint) that returns flags; call it from extract_verify_roofline
  after bytes are pooled. Analytic footprint: for GEMV/GEMM kernels, weight bytes from the model''s tensor shapes x calls
  per step; other kernels get only the peak check. Flags are report fields, never a filter: every row stays in the table.

  '
acceptance: pytest scripts/kernel_rnd/autokernel/loop -k plausib
non_goals:
- No LLM or ISA-based estimator; no change to the census ranking rule.
tier: local
grounded:
  at: '2026-11-25'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/census_extract.py: a744d50638d01901016aab54d93ddc667c0f8990
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/testdata/census/verify_roofline.RESULT.json: 458b3fa26c3267da837d29aac115a3d6f840cb09
---
