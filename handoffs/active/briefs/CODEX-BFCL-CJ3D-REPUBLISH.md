---
schema: epyc.brief.v1
id: CODEX-BFCL-CJ3D-REPUBLISH
box_text_sha: t:8d5eae9e27ddff2c
author: owner
written: '2026-11-20'
accepted: owner
where:
- handoffs/active/benchmark-suites.md
- scripts/coordination/rowflow/publish_row.py
approach: 'Republish via publish_row.py with the corrected estimate, region and max_window once the codex lane has budget;
  supersede the old row.

  '
acceptance: python3 .claude/skills/inference-backlog-scheduling/scripts/queue_status.py
non_goals:
- Do not launch compute while compute is paused
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/benchmark-suites.md: 351616d9db7472d148f19f8920a2732cacd9000a
    epyc-root:scripts/coordination/rowflow/publish_row.py: null
---
