---
schema: epyc.brief.v1
id: EXL3-6c5
box_text_sha: ea3f8a9a15da1243
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/kernel_rnd/exl3/evidence.py
- epyc-inference-research:scripts/benchmark/bench_canonical.sh
- epyc-root:handoffs/active/quantization-and-low-bit.md
approach: 'Full-model window: load plus greedy smoke, then speed (codified recipe, GGML_FUSED_DECODE_OFF=1) and PPL vs UD-IQ4_XS;
  main-session memory-heavy run; files rows via evidence.py.

  '
acceptance: grep -qE '^\s*- \[x\] \*\*EXL3-6c5\b' handoffs/active/quantization-and-low-bit.md
non_goals:
- no scope beyond this box; no box-text edit, no tick
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/exl3/evidence.py: 34bd146d8b8c1109d3f7e6a13aae32915ff29bdd
    epyc-inference-research:scripts/benchmark/bench_canonical.sh: d1c5a7becae27de77f61785af7e9420809a6ede4
    epyc-root:handoffs/active/quantization-and-low-bit.md: de85bd28a242412865b75d7baa5d6e48427952f2
---
