---
schema: epyc.brief.v1
id: RE-4.3
box_text_sha: 6d3575142745a2a4
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/benchmark/score_longcot_run.py
approach: 'Full reference run (only if RE-4.2 in-band): both roles two-phase R=4096 over all 402 rows with score_longcot_run.py.
  First step: manifest entry conditional on RE-4.2.

  '
acceptance: grep -qE '^ *- \[x\] \*\*RE\-4\.3\b' handoffs/active/eval-tower-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/benchmark/score_longcot_run.py: bdc2c20a672ac9b7f9c2559733ca0e675e3da5eb
---
