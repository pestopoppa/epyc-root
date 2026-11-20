---
schema: epyc.brief.v1
id: LOOP-75
box_text_sha: d2e603d693d79985
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:research/refactor-audit-2026-10/packages/wave1.json
- epyc-orchestrator:scripts/autopilot/operator_candidates
- epyc-orchestrator:scripts/autopilot/collect_e9_operational_baseline.py
approach: 'P4 bloat package: one-shot operator ratifiers (B4-03) and the era-pinned family (B4-02) are historical records
  of applied operator actions; confirm each was applied via artifacts/operator and handoffs, then delete the scripts and tests
  that only exercise them (git history keeps them); then the small bugs B4-19, B4-20, B4-13, B2-16, B4-16 etc. Never delete
  files under epyc-root artifacts/operator. First step: the applied-or-not table per script.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && test ! -e scripts/autopilot/operator_candidates/ratify_and_apply_multitier_baseline_v10.py
non_goals:
- no deletion of unapplied ratifiers
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:research/refactor-audit-2026-10/packages/wave1.json: bb376c30536182d94ec0a5257025cef934db2098
    epyc-orchestrator:scripts/autopilot/operator_candidates: tree:277ee374f3db3675da34fb4e96d121ef103d1361
    epyc-orchestrator:scripts/autopilot/collect_e9_operational_baseline.py: 0c9d8dde5269ad0fac97e33c2aac1175a88e52f5
---
