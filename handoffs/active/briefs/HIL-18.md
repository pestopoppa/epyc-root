---
schema: epyc.brief.v1
id: HIL-18
box_text_sha: c423d4814fb375e6
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/trace/spectrum.py
- epyc-orchestrator:src/trace/spectrum_replay.py
- epyc-orchestrator:scripts/trace/spectrum_replay.py
- epyc-orchestrator:tests/unit/test_spectrum.py
approach: 'Key, ranking and wrapper are built (6bb9dc05; run refuses without WINDOW_CONFIRMED=1). Remaining: HIL-18a, replay
  10 failed tasks with pass-rate strictly in (0,1) over 20 replays at temperature >0, then report step-type ranking agreement
  with L2 categories and the human overlap sample. Needs the HIL-15b outcome-variance tasks first (see HIL-15b). Stop when
  10 eligible tasks are ranked or on futility. Role-ablation Shapley (HIL-18b) only if the ranking is usable.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 scripts/trace/spectrum_replay.py report --help
non_goals:
- no Shapley before ranking is judged usable
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/trace/spectrum.py: 4d2da094508bfbcbda42b4b2657567e323e22250
    epyc-orchestrator:src/trace/spectrum_replay.py: 80a9898282c0e2523c8c4febb9d2caed48bf69f8
    epyc-orchestrator:scripts/trace/spectrum_replay.py: 17eb07984df0b12c19dc9393e2cad2af0348ae6c
    epyc-orchestrator:tests/unit/test_spectrum.py: c61c44f5a262c1839d0eb8829273a270302731d0
---
