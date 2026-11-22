---
schema: epyc.brief.v1
id: AKU-10g2
box_text_sha: t:983e36b6b4229199
author: owner
written: '2026-11-22'
accepted: owner
where:
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/maintenance_execution.py
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/provider_factories.py
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/host_claim_provider.py
approach: 'Implement BrokerHoldProvider over the host claim primitives used by host_claim_v1: durable hold ids bound to the
  request digest, idempotent exactly-once settle winning over late refresh, resolve by request digest, integer ms; register
  it gated like host_claim_v1.

  '
acceptance: pytest scripts/kernel_rnd/autokernel/loop/test_maintenance_broker.py -k registered
non_goals: []
tier: local
grounded:
  at: '2026-11-22'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/maintenance_execution.py: 0846dd16cdd8aee033682758a40186900b6cf584
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/provider_factories.py: edc33de0c88d2986ce7d5a0ad7348ff51adb58bc
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/host_claim_provider.py: null
---
