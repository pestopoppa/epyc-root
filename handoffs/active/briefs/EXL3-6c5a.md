---
schema: epyc.brief.v1
id: EXL3-6c5a
box_text_sha: d20d6a6eb56c8b70
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/kernel_rnd/exl3/evidence.py
- epyc-root:handoffs/active/quantization-and-low-bit.md
approach: 'Run evidence.py write() over the 10-04 durable copy to emit epyc.exl3.measurement.v1 rows, then ingest.

  '
acceptance: ls /workspace/repos/epyc-inference-research/scripts/kernel_rnd/exl3/evidence.py >/dev/null && grep -qE '^\s*-
  \[x\] \*\*EXL3-6c5a\b' handoffs/active/quantization-and-low-bit.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/exl3/evidence.py: 34bd146d8b8c1109d3f7e6a13aae32915ff29bdd
    epyc-root:handoffs/active/quantization-and-low-bit.md: de85bd28a242412865b75d7baa5d6e48427952f2
---
