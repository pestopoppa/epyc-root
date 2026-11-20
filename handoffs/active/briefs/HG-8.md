---
schema: epyc.brief.v1
id: HG-8
box_text_sha: t:11e205f1e1b7ddb1
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:scripts/autopilot/screening_tier_runner.py
- epyc-orchestrator:src/autopilot_core/sequential_verdict.py
approach: 'Policy A/B under P-AB-1 + P-REV-1: paired comparison of candidate review policies (threshold, verifier-disagreement,
  protected-action) on the same tasks with the sequential e-process verdict; promotion per LB-6 budget gate (threshold value
  is an operator decision, so enforce-mode flip waits). Prep: wire the policy arms into screening_tier_runner as named arms.
  Stop on e-process decision or futility.

  '
acceptance: grep -q 'HG-8 verdict' handoffs/active/reviewer-control-plane.md
non_goals:
- no promotion before LB-6
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:scripts/autopilot/screening_tier_runner.py: b0110ac99b04c08454b4d604e739f1d63f5cd43b
    epyc-orchestrator:src/autopilot_core/sequential_verdict.py: 3a946e5cadbe2d26648a856b731dfc6f7d6a9232
---
