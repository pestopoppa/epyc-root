---
schema: epyc.brief.v1
id: LOOP-61
box_text_sha: 6eddf1002de6297e
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:research/refactor-audit-2026-10/packages/wave2.json
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/campaign.py
approach: 'RESUME-6: before each K3 deletion stage, reconcile the current INF64 retained-module manifest and the live belief-source
  contracts (scripts/vidya adapters), with retained campaign.py and dynamic/cross-repo consumers as closure roots. Step: a
  closure script that, from the retained-module manifest plus those roots, lists modules reachable through imports, lazy/function-local
  imports, python -m and subprocess argv; run it fresh at each stage and bind the reviewed HEAD.

  '
acceptance: cd /workspace/repos/epyc-inference-research && python3 -m pytest -q scripts/kernel_rnd/autokernel/loop/test_prune_closure.py
new_tests:
- scripts/kernel_rnd/autokernel/loop/test_prune_closure.py
non_goals:
- no deletion in this box
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:research/refactor-audit-2026-10/packages/wave2.json: 69d12317bc22636855f108a0f2f3f4c906ec6d6d
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/campaign.py: abf536cc9ee0322622a6133bf3798cd22573e517
---
