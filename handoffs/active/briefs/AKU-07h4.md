---
schema: epyc.brief.v1
id: AKU-07h4
box_text_sha: t:b1a6c01d3f73db0c
author: owner
written: '2026-11-22'
accepted: owner
where:
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/standalone_runtime.py
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/driver_execution.py
approach: 'Extend the standalone tick dispatch table so actor and continuous-feed selections reach their existing owners (actor
  preparation, feed runtime) with the same retained-transition recovery as runtime/profile work.

  '
acceptance: pytest scripts/kernel_rnd/autokernel/loop/test_standalone_runtime.py -k dispatch
non_goals: []
tier: local
grounded:
  at: '2026-11-22'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/standalone_runtime.py: e6d2b90d0f0dcade3e36b023718802f85171647e
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/driver_execution.py: 5ad9b908134a01a3dbf17bdaeada9ff905ea2bd0
---
