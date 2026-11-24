---
schema: epyc.brief.v1
id: C21-NOSPEC-DETERMINISM
box_text_sha: t:b29aa4579f1f64cc
author: planning
written: '2026-11-24'
accepted: owner
where:
- /mnt/raid0/llm/tmp/c21-fold-gpu-20261124-r3
- /mnt/raid0/llm/tmp/ak-c21-gpu-correctness-20261124/FINDINGS.md
approach: 'read r3 aa_c19/aa_c18/aa_gdn0 token-position stats and fork margins first; only then queue a bisection row on the
  GPU lane

  '
acceptance: named commit/knob with A/A positions per arm, or all suspects excluded
non_goals: []
tier: local
grounded:
  at: '2026-11-24'
  blobs:
    epyc-root:/mnt/raid0/llm/tmp/c21-fold-gpu-20261124-r3: tree:87686f6e51bf6f653c949f3d87a2864a60abfba7
    epyc-root:/mnt/raid0/llm/tmp/ak-c21-gpu-correctness-20261124/FINDINGS.md: 4fb0158ea3619674e5beb37451077c7ea1d91017
---
