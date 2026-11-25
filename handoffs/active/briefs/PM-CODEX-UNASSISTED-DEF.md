---
schema: epyc.brief.v1
id: PM-CODEX-UNASSISTED-DEF
box_text_sha: t:9cfcc4e150c87042
author: wrap-up
written: '2026-11-25'
accepted: owner
where:
- scripts/coordination/codex_lane/drive.py
approach: 'Update the unassisted definition in the codex-lane driver and docs; have drive.py run the lane''s done-when under
  nice+taskset 84-87 and push via serialized_push; log per-lane assisted/unassisted; gate the DISPATCH-DETERMINISTIC port
  on a count of 5

  '
acceptance: python3 -m pytest scripts/coordination/tests/test_codex_lane_drive.py
non_goals: []
tier: local
grounded:
  at: '2026-11-25'
  blobs:
    epyc-root:scripts/coordination/codex_lane/drive.py: 48ba9d9d4854087081c3931573994a98f75c5749
---
