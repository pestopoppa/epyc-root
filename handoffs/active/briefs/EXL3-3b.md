---
schema: epyc.brief.v1
id: EXL3-3b
box_text_sha: 650a455cfa027483
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/claimed_run.py
- epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/test_claimed_run.py
- epyc-root:handoffs/active/quantization-and-low-bit.md
approach: 'The claimed-run teardown guard must pass a binary that passes; source fix landed, so first step is the synthetic
  device rerun by the inference owner and the test_claimed_run.py regression; files the rerun verdict.

  '
acceptance: cd /workspace/repos/epyc-inference-research && python3 -m pytest -q scripts/kernel_rnd/exl3_gfx90a/test_claimed_run.py
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/claimed_run.py: b4288b05f14bc94e674f0800340b06c5392e4352
    epyc-inference-research:scripts/kernel_rnd/exl3_gfx90a/test_claimed_run.py: 1cf6849e68fbee7d8cf5e751e70c534096ca0257
    epyc-root:handoffs/active/quantization-and-low-bit.md: de85bd28a242412865b75d7baa5d6e48427952f2
---
