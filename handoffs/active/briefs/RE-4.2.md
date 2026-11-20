---
schema: epyc.brief.v1
id: RE-4.2
box_text_sha: 3e68ce7af14998ab
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-inference-research:scripts/benchmark/score_longcot_run.py
approach: 'Non-saturation probe: frontdoor-only two-phase R=4096 on 30 stratified rows scored with score_longcot_run.py; gate
  on overall accuracy band. First step: launcher manifest for a quiet window.

  '
acceptance: grep -qE '^ *- \[x\] \*\*RE\-4\.2\b' handoffs/active/eval-tower-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/benchmark/score_longcot_run.py: bdc2c20a672ac9b7f9c2559733ca0e675e3da5eb
---
