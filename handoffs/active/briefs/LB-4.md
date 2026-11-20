---
schema: epyc.brief.v1
id: LB-4
box_text_sha: t:e0bf272628c513b6
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/autopilot_core/sequential_verdict.py
- epyc-orchestrator:scripts/autopilot/screening_tier_runner.py
approach: 'Paired throughput A/B per policy under P-AB-1 + P-SPEED-OBJ: task-rate axis with the e-process, never single-trial;
  parallel-reviewer wall-clock modeled as SUM on-host (exception: NUMA-split or MI210-offloaded reviewer). Prep: arm definitions
  per policy and the throughput metric in the runner. Stop on e-process decision or futility.

  '
acceptance: grep -q 'LB-4 verdict' handoffs/active/reviewer-control-plane.md
non_goals:
- no single-trial claims
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/autopilot_core/sequential_verdict.py: 3a946e5cadbe2d26648a856b731dfc6f7d6a9232
    epyc-orchestrator:scripts/autopilot/screening_tier_runner.py: b0110ac99b04c08454b4d604e739f1d63f5cd43b
---
