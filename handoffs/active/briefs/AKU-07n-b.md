---
schema: epyc.brief.v1
id: AKU-07n-b
box_text_sha: t:78f5fb25915b030b
author: owner
written: '2026-11-22'
accepted: owner
where:
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/startup_factory.py
- epyc-orchestrator:scripts/server/autokernel_enrollment.py
approach: 'After AKU-12c repairs generated exports: produce the sealed export with autokernel_enrollment.py --instance-mode
  both, resolve it with campaign_cli, write a startup config with real provider ids, run startup_factory with --expect-export-sha256,
  then the AKU-12a installed dry run.

  '
acceptance: startup_factory exits 0 on the real export and the AKU-12a dry run passes on its startup.json
non_goals:
- compute grants or provider activation
tier: local
grounded:
  at: '2026-11-22'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/startup_factory.py: 277940cbece3ded453612cfc0e8b036f70b8ed85
    epyc-orchestrator:scripts/server/autokernel_enrollment.py: 8a2c380121f8f245bb2c8f5b17a782b5d95652d2
---
