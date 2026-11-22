---
schema: epyc.brief.v1
id: AKU-07h3
box_text_sha: t:39c8364b064439d2
author: owner
written: '2026-11-22'
accepted: owner
where:
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/driver_execution.py
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/campaign_control.py
approach: 'When restored settlement runs after a crash that followed native capture appends, look up the first run''s native
  record references for the same transition and include them in the settlement evidence refs instead of omitting them.

  '
acceptance: pytest scripts/kernel_rnd/autokernel/loop/test_standalone_runtime.py -k native_records
non_goals: []
tier: local
grounded:
  at: '2026-11-22'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/driver_execution.py: 5ad9b908134a01a3dbf17bdaeada9ff905ea2bd0
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/campaign_control.py: 04ed5ca4da1d60868e5e47cc0cfbec30806818e4
---
