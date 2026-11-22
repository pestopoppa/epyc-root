---
schema: epyc.brief.v1
id: AKU-06d3
box_text_sha: t:9a46caaf847c3304
author: owner
written: '2026-11-22'
accepted: owner
where:
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/source_build_preparation.py
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/actor_preparation.py
approach: 'Add a contained authoring stage with its own reservation that reads immutable source context and writes a bounded
  patch through the controller-authenticated output channel, then builds the guarded native manifest.

  '
acceptance: pytest scripts/kernel_rnd/autokernel/loop/test_source_build_execution.py -k authoring
non_goals: []
tier: local
grounded:
  at: '2026-11-22'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/source_build_preparation.py: 82f8f6196cfa2eba43d426f207f4ab1d704ca82c
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/actor_preparation.py: dc87be8f0eb9d14b688a168b41a518f200080198
---
