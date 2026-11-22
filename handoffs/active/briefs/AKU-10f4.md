---
schema: epyc.brief.v1
id: AKU-10f4
box_text_sha: t:caaccc455b8304b7
author: owner
written: '2026-11-22'
accepted: owner
where:
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/campaign_control.py
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/test_native_capture_control.py
approach: 'Install a native catalog on a real fixture controller, append native capture evidence through the real path, and
  assert the evidence owner record advances and coverage becomes complete.

  '
acceptance: pytest scripts/kernel_rnd/autokernel/loop/test_native_capture_control.py -k coverage
non_goals: []
tier: local
grounded:
  at: '2026-11-22'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/campaign_control.py: 04ed5ca4da1d60868e5e47cc0cfbec30806818e4
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/test_native_capture_control.py: aae1e18bdbd418099f86c7cff116c6a17aa7eca0
---
