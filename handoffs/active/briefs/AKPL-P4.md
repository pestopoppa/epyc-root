---
schema: epyc.brief.v1
id: AKPL-P4
box_text_sha: t:5c5d262849526b45
author: owner
written: '2026-11-21'
accepted: auto
where:
- docs/reference/kernel-manifests/README.md
approach: 'Read champion lineage from epyc-inference-research scripts/kernel_rnd/autokernel/loop/champion.py and kernel_coverage.py
  (DS41-C116); emit the fold list and presence manifest; never touches production-consolidated-v10.

  '
acceptance: the C-next fold list and presence gate are generated, not written, and the manager refuses a fold missing a test
  (DS41-C116 gate).
non_goals: []
tier: local
grounded:
  at: '2026-11-21'
  blobs:
    epyc-root:docs/reference/kernel-manifests/README.md: 673e25f3bd50f598ddf586b7c58c9da44c58df10
---
