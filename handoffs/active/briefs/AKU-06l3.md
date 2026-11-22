---
schema: epyc.brief.v1
id: AKU-06l3
box_text_sha: t:5c0ef71844c3ec34
author: owner
written: '2026-11-22'
accepted: owner
where:
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/standalone_runtime.py
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/startup_factory.py
approach: 'Add operation_settlement to StartupManifest and the CLI, migrate tests that assert v1 standalone settlement bytes,
  then flip the default.

  '
acceptance: pytest scripts/kernel_rnd/autokernel/loop/test_operation_settlement_v2_standalone.py
non_goals: []
tier: local
grounded:
  at: '2026-11-22'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/standalone_runtime.py: e6d2b90d0f0dcade3e36b023718802f85171647e
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/startup_factory.py: 277940cbece3ded453612cfc0e8b036f70b8ed85
---
