---
schema: epyc.brief.v1
id: KPF-26.1h
box_text_sha: 016a456aa76cb785
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/roles.py
approach: 'Write-side capture: make proactive_stage log each parsed plan step (id, actor, action) to a durable journal and
  wire as a belief-kernel source; then take the >=50 real-action TERSE/WORKING-ALLOWED sample. First step: journal writer
  with unit test, plus adapters/README row.

  '
acceptance: grep -qE '^ *- \[x\] \*\*KPF\-26\.1h\b' handoffs/active/kv-cache-program.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/roles.py: 59432d52c3c5ebb661c336f70627267073cfa4cb
---
