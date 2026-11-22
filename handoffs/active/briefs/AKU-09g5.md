---
schema: epyc.brief.v1
id: AKU-09g5
box_text_sha: t:c273f4a7fb755ef2
author: owner
written: '2026-11-22'
accepted: owner
where:
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/campaign_service.py
- epyc-root:dashboard/campaign_status.py
approach: 'During the AKU-12 monitored run, configure the standalone service in the hub registry with health probe and freshness
  envelope for projection v4 and record health/freshness/control acceptance observations.

  '
acceptance: AKU-12 run record shows hub /api/health green with v4 snapshots and control round-trips
non_goals:
- launching the loop outside AKU-12
tier: local
grounded:
  at: '2026-11-22'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/campaign_service.py: c2d7b62384e08a93cfbdfb49ef2be78cfdbf5d75
    epyc-root:dashboard/campaign_status.py: 919fcd79868a8d3ba12ffc121b1cda39d3d4676c
---
