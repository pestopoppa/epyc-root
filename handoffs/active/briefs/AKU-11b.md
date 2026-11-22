---
schema: epyc.brief.v1
id: AKU-11b
box_text_sha: t:4a9e53722947ca04
author: owner
written: '2026-11-22'
accepted: owner
where:
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/startup_factory.py
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/provider_factories.py
approach: 'After AKU-07n-b produces a real export-backed manifest, rerun startup_factory with --provider-factory host_claim_v1
  and record the provider debt/launchable state; no activation record is created.

  '
acceptance: startup_factory exits 0 with --provider-factory host_claim_v1 on the real export and lists the provider as gated
non_goals: []
tier: local
grounded:
  at: '2026-11-22'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/startup_factory.py: 277940cbece3ded453612cfc0e8b036f70b8ed85
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/provider_factories.py: edc33de0c88d2986ce7d5a0ad7348ff51adb58bc
---
