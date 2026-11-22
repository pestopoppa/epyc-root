---
schema: epyc.brief.v1
id: AKU-10f3
box_text_sha: t:baddf62562f95222
author: owner
written: '2026-11-22'
accepted: owner
where:
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/native_retention_catalog.py
- epyc-inference-research:scripts/kernel_rnd/autokernel/journal.py
approach: 'Add an additive journal kind carrying native_retention_owner_record.v1 at each owner hook and replay coverage from
  it, keeping legacy streams byte-identical and old readers refusing the new kind.

  '
acceptance: pytest scripts/kernel_rnd/autokernel/loop/test_native_retention_catalog.py -k journal
non_goals: []
tier: local
grounded:
  at: '2026-11-22'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/native_retention_catalog.py: 28c7e18779b7502cbf60bfab0b99e7e2a2383965
    epyc-inference-research:scripts/kernel_rnd/autokernel/journal.py: df995d9c2f097963c4cfa91b7602b01a60d6b4f7
---
