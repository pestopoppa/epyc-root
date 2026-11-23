---
schema: epyc.brief.v1
id: AK-TEMP-AXIS-5
box_text_sha: t:9934c2bf48a24fd6
author: owner
written: '2026-11-23'
accepted: owner
where:
- epyc-inference-research:scripts/kernel_rnd/dice_replay/dice_replay.py
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/census.py
approach: 'Lift the replay core of dice_replay.py (research 03c100462) into loop/temperature_rescore.py with no live server
  and no GPU; a thin CLI takes an acceptance capture path and a temperature list (default 0, 0.2, 1.0); output records carry
  the AK-TEMP-AXIS-1 sampling shape. The test replays the committed 03c100462 capture and matches its RESULT.json acceptance
  numbers. dice_replay.py lives on research main only after the DICE commit lands; the census.py anchor keeps this brief grounded
  meanwhile.

  '
acceptance: python3 -m pytest -q scripts/kernel_rnd/autokernel/loop/test_temperature_axis_5.py
new_tests:
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/test_temperature_axis_5.py
non_goals: []
tier: local
grounded:
  at: '2026-11-23'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/dice_replay/dice_replay.py: null
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/census.py: 65f9e2f1080c1ad70f0dd95735f2f47586e5491a
---
