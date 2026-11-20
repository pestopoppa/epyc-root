---
schema: epyc.brief.v1
id: EXL3-MFMA-FP16-ENV-1
box_text_sha: 1ee8b8ab5c3977c3
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/README.md
- epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/fixtures.py
- epyc-inference-research:scripts/kernel_rnd/exl3/fixtures
approach: 'Host-side numpy model: round activations to fp16 with a power-of-two scale per 128 inputs, compute predicted deviation
  vs the fp32 oracle for each saved real fixture, compare with the observed 1.65e-5..1.8e-5 MFMA errors, and append the note
  (covers / does not cover) to the exl3_gfx90a README, amending the EXL3-3a envelope or leaving the cause open with the reason.
  No GPU run.

  '
acceptance: grep -qi 'fp16 activation rounding' /workspace/repos/epyc-inference-research/scripts/kernel_rnd/exl3_gfx90a/README.md
non_goals:
- no device or MFMA run; saved fixtures only
- do not loosen the envelope without the computed prediction
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/README.md: 7593c6ea2c3fa6c2d3c6f5057f08fd6ed40b85bb
    epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/fixtures.py: 85b4205b3387219a5bfdc29f9d39a92a4f7d33b1
    epyc-inference-research:scripts/kernel_rnd/exl3/fixtures: tree:05622f64e40dee25e32f8b1ce24b3d9f9d4caf98
---
