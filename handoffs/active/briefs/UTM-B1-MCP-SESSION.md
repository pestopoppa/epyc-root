---
schema: epyc.brief.v1
id: UTM-B1-MCP-SESSION
box_text_sha: be7a33ebc2bc06f2
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/memory-program.md
approach: 'First concrete step for: per-session MCP launch binding. Box has no done-when; acceptance is the closest check.

  '
acceptance: python3 -m pytest -q tests/test_utm_b1_mcp_session.py
new_tests:
- tests/test_utm_b1_mcp_session.py
non_goals: []
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/memory-program.md: 5c37bb9338910d1a5015df83dd0417010e4ddfc8
---
