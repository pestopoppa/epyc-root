---
schema: epyc.brief.v1
id: V11-FA8-RERUN-PINNED
box_text_sha: e079240cb7f4bbac
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:handoffs/active/kv-cache-program.md
approach: 'Rerun v11-fa8 impact pinned to flash_attn_ext_f16_process_tile with scan_complete and partial=false (r6 failed
  on a partial scan, cfac40240). First step: rerun the impact row with the pin.

  '
acceptance: grep -qE '^ *- \[x\] \*\*V11\-FA8\-RERUN\-PINNED\b' handoffs/active/kv-cache-program.md
non_goals:
- no scope beyond the box text
tier: local
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:handoffs/active/kv-cache-program.md: 430ad95801c442eb37544739ff60db62ed4d2965
---
