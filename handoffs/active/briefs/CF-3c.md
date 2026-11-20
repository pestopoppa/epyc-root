---
schema: epyc.brief.v1
id: CF-3c
box_text_sha: 0f24ccd389ee3efa
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/graph/session_log.py
approach: 'Validate CompactionQualityMonitor (src/graph/session_log.py) on real traffic/telemetry after upstream anti-thrashing
  lands; tune degradation thresholds only then. First step: telemetry replay harness over stored sessions that prints threshold
  trip rates; stop when the rates are filed.

  '
acceptance: grep -qE '^ *- \[x\] \*\*CF\-3c\b' handoffs/active/context-and-token-economy.md
non_goals:
- no scope beyond the box text
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/graph/session_log.py: 41b42f0581971def4e8388e3ac29abf759ab2574
---
