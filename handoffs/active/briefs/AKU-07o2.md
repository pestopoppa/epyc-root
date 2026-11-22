---
schema: epyc.brief.v1
id: AKU-07o2
box_text_sha: t:ed51caeaecab1660
author: owner
written: '2026-11-22'
accepted: owner
where:
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/startup_factory.py
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/lifecycle_observation.py
approach: 'Install the production kfd_consumer_reader and the MI210 device-to-KFD gpu_id mapping in the startup factory so
  GPU observations carry the census.

  '
acceptance: pytest scripts/kernel_rnd/autokernel/loop/test_startup_factory.py -k kfd
non_goals: []
tier: local
grounded:
  at: '2026-11-22'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/startup_factory.py: 277940cbece3ded453612cfc0e8b036f70b8ed85
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/lifecycle_observation.py: c0cf6ea6f69e951635f1645de9ac8b84d6a0cd05
---
