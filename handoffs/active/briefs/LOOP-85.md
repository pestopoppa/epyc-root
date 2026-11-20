---
schema: epyc.brief.v1
id: LOOP-85
box_text_sha: c171f740e9ec8ac5
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:research/refactor-audit-2026-10/packages/wave2.json
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/run.py
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/test_heartbeat.py
approach: 'D4: AutoKernel run.main decomposition (requires K1 and K3 merged; start with git fetch origin main and rebase).
  First replace source-text tests with behavioural ones (C1-03: test_heartbeat.py:329) and mind C1-M1: evidence identities
  hash whole source files and callable __module__, so moving code changes identities; handle as the finding says before moving
  anything. 20 findings.

  '
acceptance: cd /workspace/repos/epyc-inference-research && python3 -m pytest -q scripts/kernel_rnd/autokernel/loop/test_heartbeat.py
non_goals:
- no code movement before C1-M1 identity handling
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:research/refactor-audit-2026-10/packages/wave2.json: 69d12317bc22636855f108a0f2f3f4c906ec6d6d
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/run.py: 6b7280304b3e420ce45b984ec1ed847f5f9a04c4
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/test_heartbeat.py: 358a72a3b441433261235d8645c1c4b6b48e72c1
---
