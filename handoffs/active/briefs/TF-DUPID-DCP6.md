---
schema: epyc.brief.v1
id: TF-DUPID-DCP6
box_text_sha: t:2aff3db7d38c53c0
author: owner
written: '2026-11-20'
accepted: owner
where:
- handoffs/active/context-and-token-economy.md
- handoffs/active/autopilot-program.md
approach: 'Rename the autopilot-program DCP-6 sub-boxes (offline replay, deploy attestation) to DCP-6a/DCP-6b, update references.

  '
acceptance: python3 scripts/handoffs/box_index.py --help
non_goals:
- Do not change box content or ticks
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/context-and-token-economy.md: d10d6d2685bbe0c12360bcfa114ab22b83e5f22a
    epyc-root:handoffs/active/autopilot-program.md: 4089b56a36c6fec832f8696564f1c30f867e226e
---
