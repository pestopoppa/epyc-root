---
schema: epyc.brief.v1
id: NARIQ-LIBTRELLIS-MAP-1
box_text_sha: 4d53c0a5a40f27ce
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/README.md
- epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/kernels.hip
approach: 'Design note only (no code): for each libtrellis choice (4v+1528 fp16 A-fragment with sum correction, fragment-order
  activation prep, grouped launches for shared-input matrices, 64 KB LDS plan, wave64 MFMA lane ownership) state the gfx90a
  constants and mark which the existing standalone MFMA harness already covers. Appended to the exl3_gfx90a README under a
  new heading. Box has a done-when but no runnable form; acceptance is the closest check.

  '
acceptance: grep -qi 'libtrellis' /workspace/repos/epyc-inference-research/scripts/kernel_rnd/exl3_gfx90a/README.md && grep
  -q '1528' /workspace/repos/epyc-inference-research/scripts/kernel_rnd/exl3_gfx90a/README.md
non_goals:
- no kernel code changes
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/README.md: 7593c6ea2c3fa6c2d3c6f5057f08fd6ed40b85bb
    epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/kernels.hip: 10cc7690bc1baa7bf6367fd1033ee23fd731ec43
---
