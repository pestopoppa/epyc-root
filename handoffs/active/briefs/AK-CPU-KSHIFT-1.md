---
schema: epyc.brief.v1
id: AK-CPU-KSHIFT-1
box_text_sha: t:3db37d81678306ce
author: intake
written: '2026-11-24'
accepted: auto
where:
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop
approach: 'Clone kernel-shift at 610e835 into a research scratch dir. Patch kgen/check.py and kgen/autovec.py to accept x86_64,
  add an avx512 tier in config/kernel_contracts.yaml, and write a C++ wrapper calling ggml_vec_dot_q8_0_q8_0 and iqk as the
  expert baseline. Generate workloads from served-shape traces, calibrate the SQNR floor, then run the ISA arms via -march
  flags on one quarter and count instructions with objdump.

  '
acceptance: scratch-copy SHA, the task files, and the C21 baseline geomean with its A/A floor per ISA arm filed under this
  box; FUTILITY recorded if the task only reproduces the existing served_shape_cases verdicts
non_goals: []
tier: local
grounded:
  at: '2026-11-24'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop: tree:1e2a88f37e8448821d5920547e5c3550854db31f
---
