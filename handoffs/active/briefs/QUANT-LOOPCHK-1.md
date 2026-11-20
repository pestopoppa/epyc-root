---
schema: epyc.brief.v1
id: QUANT-LOOPCHK-1
box_text_sha: 133e828b9e48995c
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/benchmark/answer_scoring.py
- epyc-root:handoffs/active/quantization-and-low-bit.md
approach: 'New stdlib script scripts/benchmark/quant_loopchk.py (imports answer_scoring for wrong): labels each generation
  wrong/looped/cut-off at a fixed token cap vs the reference answer (looped = repeated n-gram tail over a threshold; cut-off
  = hit cap without a terminator). Add the gate text to the quantization-and-low-bit.md track body. Fixture test: a synthetic
  looping output is labelled looped.

  '
acceptance: cd /workspace/repos/epyc-inference-research && python3 -m pytest -q scripts/benchmark/test_quant_loopchk.py
new_tests:
- epyc-inference-research:scripts/benchmark/test_quant_loopchk.py
non_goals:
- no model runs or inference; fixtures only
- do not edit box text; gate text goes in the track body
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/benchmark/answer_scoring.py: bb1e0fe958e16a945df56dc373cdfa7dfb1a1f90
    epyc-root:handoffs/active/quantization-and-low-bit.md: 1abd0476512f3c2836d6ade7f1b61c642be1e0cd
---
