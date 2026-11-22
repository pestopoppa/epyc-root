---
schema: epyc.brief.v1
id: AKU-10f2
box_text_sha: t:58151eed6271773e
author: owner
written: '2026-11-22'
accepted: owner
where:
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/native_retention_catalog.py
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/campaign_control.py
approach: 'Parse DT_NEEDED and RUNPATH from each built executable/DSO with a small ELF dynamic-section reader outside the
  controller mutex and add undeclared dependencies to the build_dependency owner record; unreadable ELF keeps coverage incomplete.

  '
acceptance: pytest scripts/kernel_rnd/autokernel/loop/test_native_retention_catalog.py -k elf
non_goals: []
tier: local
grounded:
  at: '2026-11-22'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/native_retention_catalog.py: 28c7e18779b7502cbf60bfab0b99e7e2a2383965
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/campaign_control.py: 04ed5ca4da1d60868e5e47cc0cfbec30806818e4
---
