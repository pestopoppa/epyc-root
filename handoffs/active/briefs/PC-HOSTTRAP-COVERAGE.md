---
schema: epyc.brief.v1
id: PC-HOSTTRAP-COVERAGE
box_text_sha: t:3a91f87d58ec2cdc
author: intake
written: '2026-11-27'
accepted: auto
where:
- epyc-root:research/deep-dives/intake-nov27-kernel-systems/intake-3006.md
- epyc-root:research/deep-dives/intake-nov27-kernel-systems/intake-3020.md
- epyc-inference-research:scripts/kernel_rnd/autokernel/adapters/att_stall_classes.py
approach: 'The 6.2 ATT adapter is already the approved stall classifier. A second route only earns its cost if it maps unresolved
  PCs on a separately qualified stack. Use the original ELFs, code objects, store manifests and build IDs. Keep one other
  binary for validation. Record symbol+offset, source line or unmappable reason for each sampled PC. Only trial host-trap
  if unresolved hotspots remain and firmware/driver enumerate the capability; collect separate baseline runtime and check
  perturbation, skid and sample loss.

  '
acceptance: Use the original ELFs, code objects, store manifests and build IDs. Keep one other binary for validation. Record
  symbol+offset, source line or unmappable reason for each sampled PC. Only trial host-trap if unresolved hotspots remain
  and firmware/driver enumerate the capability; collect separate baseline runtime and check perturbation, skid and sample
  loss.
non_goals: []
tier: local
grounded:
  at: '2026-11-27'
  blobs:
    epyc-root:research/deep-dives/intake-nov27-kernel-systems/intake-3006.md: c9eaf68061870f4607b629a36f563881e827c0df
    epyc-root:research/deep-dives/intake-nov27-kernel-systems/intake-3020.md: cd852b7a93e9398d210b6e7d75a100abd42b2720
    epyc-inference-research:scripts/kernel_rnd/autokernel/adapters/att_stall_classes.py: bab81205062c232ff1adff1efd344495a3590e16
---
