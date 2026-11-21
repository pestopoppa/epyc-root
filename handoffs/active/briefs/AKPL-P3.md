---
schema: epyc.brief.v1
id: AKPL-P3
box_text_sha: t:2349f14320e9cefe
author: owner
written: '2026-11-21'
accepted: auto
where:
- scripts/coordination/rowflow/rowflow.py
approach: 'Loop code in epyc-inference-research scripts/kernel_rnd/autokernel/loop/pipeline.py, loop.py, pool.py, champion.py;
  uses P0 timing data for the GO/NO-GO and the P2 chain scaffolder.

  '
acceptance: two candidates are in build/gate concurrently while a third times on the GPU; device-busy fraction rises above
  the run-11 baseline (15.8%) on a measured campaign; no keep lands on a base it was not built from.
non_goals: []
tier: local
grounded:
  at: '2026-11-21'
  blobs:
    epyc-root:scripts/coordination/rowflow/rowflow.py: 2bb57cb7b7456f26a65f19036d682e3c94c8b1a4
---
