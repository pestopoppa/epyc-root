---
schema: epyc.brief.v1
id: AK-PLATEAU-STOP-1
box_text_sha: t:584ad217ff521e04
author: planning
written: '2026-11-24'
accepted: auto
where:
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/actors.py
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/same_state_stop.py
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/exploration_policy_replay.py
approach: 'Add a plateau evaluator beside same_state_stop.py that reads the closed journal per target and computes best, anchor
  and roofline, then ranks open families by gap using the per-family escape state read in actors.py. Emit the STATUS block
  and a PLATEAU_STOP verdict flagged observe-only, distinct from PLANNER_DEGRADED. Drive it from exploration_policy_replay.py
  over the closed campaigns, and guard it with a unit test on a fixture journal containing one plateau.

  '
acceptance: the offline replay over closed campaigns emits the STATUS block and PLATEAU_STOP fires on at least one known plateau,
  observe-only, with the commit SHA and replay output filed under this box
non_goals:
- the PACEvolve plateau pack declined 2026-11-03
tier: luna
grounded:
  at: '2026-11-24'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/actors.py: 65912177ec9a3b00df6621e1715f88471e3648a4
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/same_state_stop.py: 1bfa0ab6d816a2d9830f591ca2b8c44610980df8
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/exploration_policy_replay.py: 024bcd6ec15fe513002797e4209fc870df7b043a
---
