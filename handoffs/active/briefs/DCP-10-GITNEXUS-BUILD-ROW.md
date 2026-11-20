---
schema: epyc.brief.v1
id: DCP-10-GITNEXUS-BUILD-ROW
box_text_sha: c6ea56f0b24b48a1
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/context_discovery.py
approach: 'Build sealed private GitNexus indices for the original three bases under allocator admission (structural graph
  build, no model). First step: the build-row manifest and sealing script; stop on three indices sealed.

  '
acceptance: grep -qE '^ *- \[x\] \*\*DCP\-10\-GITNEXUS\-BUILD\-ROW\b' handoffs/active/context-and-token-economy.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/context_discovery.py: 923e748929bb163f2c45446b75a24e2528b9c7af
---
