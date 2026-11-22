---
schema: epyc.brief.v1
id: AKU-07h5
box_text_sha: t:baededac8caa6014
author: owner
written: '2026-11-22'
accepted: owner
where:
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/startup_factory.py
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/standalone_inputs.py
approach: 'Add the native-v2 scientific adapter slots (verifier/witness adapters) to the StartupManifest and install them
  at runtime construction, refusing unknown adapter ids.

  '
acceptance: pytest scripts/kernel_rnd/autokernel/loop/test_startup_factory.py -k adapter
non_goals: []
tier: local
grounded:
  at: '2026-11-22'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/startup_factory.py: 277940cbece3ded453612cfc0e8b036f70b8ed85
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/standalone_inputs.py: f9f84ee8b03975f1f4ddb7de9689f4119eacd43e
---
