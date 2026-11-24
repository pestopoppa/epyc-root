---
schema: epyc.brief.v1
id: AK-ROOFLINE-TRIPWIRE-1
box_text_sha: t:4ea014448bd17744
author: planning
written: '2026-11-24'
accepted: auto
where:
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/gates.py
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/keep_screen.py
approach: 'In gates.py add a plausibility check that converts a keep measured speedup and the op byte traffic into achieved
  GB/s and compares it with the census parity ceiling for the lane (mi210_bandwidth_census.json: GPU 1500, CPU quarter 129,
  CPU full host 520), returning a SUSPECT hold verdict instead of a rejection. Wire the verdict into the keep path in keep_screen.py
  so a SUSPECT keep waits for a correctness and residency re-check. Replay it over the recorded keeps and guard it with a
  unit test on a fixture pair of one keep above and one below its ceiling.

  '
acceptance: the replay over recorded keeps flags any keep above its ceiling as SUSPECT, with zero false holds on verified
  keeps, with the commit SHA and replay table filed under this box
non_goals: []
tier: luna
grounded:
  at: '2026-11-24'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/gates.py: 9b7a5414e7833ea24061e5c5cf7be1d94dd03b69
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/keep_screen.py: 1f2d3da6eacb5a1f86d4f83ec3f47654158f3d95
---
