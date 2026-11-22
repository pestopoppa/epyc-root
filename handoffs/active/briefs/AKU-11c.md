---
schema: epyc.brief.v1
id: AKU-11c
box_text_sha: t:ba8d7388279acaaf
author: owner
written: '2026-11-22'
accepted: owner
where:
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/host_claim_provider.py
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/claim.py
approach: 'Extend HostClaimProvider with the AKU-20 build role (pinned CPUs, bounded jobs) and GPU gpu-quiet exclusive phase
  receipts, reusing the existing claim primitives.

  '
acceptance: pytest scripts/kernel_rnd/autokernel/loop/test_host_claim_provider.py -k build
non_goals: []
tier: local
grounded:
  at: '2026-11-22'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/host_claim_provider.py: null
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/claim.py: ed867701c441423ea37003a38f3332c02c82320c
---
