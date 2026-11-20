---
schema: epyc.brief.v1
id: LOOP-79
box_text_sha: 41a9fc4a70a9cb64
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:research/refactor-audit-2026-10/packages/wave2.json
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop
approach: 'K3: prune of the three approved unreachable AutoKernel planes (unified/standalone control plane, discovery_*/gpu_source_*
  stack, release plane) staying current with main: at each stage fetch/rebase, bind the reviewed HEAD, re-prove reachability
  including lazy imports, dynamic imports, python -m, subprocess argv, units, cron. Depends on LOOP-61 closure script. First
  step: stage list with per-stage closure proof; delete one plane per commit.

  '
acceptance: cd /workspace/repos/epyc-inference-research && python3 -m pytest -q scripts/kernel_rnd/autokernel/loop -x -q
non_goals:
- no pruning of unapproved planes
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:research/refactor-audit-2026-10/packages/wave2.json: 69d12317bc22636855f108a0f2f3f4c906ec6d6d
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop: tree:03e6fdb8fb734c0d70c79c708923fc9eb6c41c5f
---
