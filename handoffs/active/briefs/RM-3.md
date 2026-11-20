---
schema: epyc.brief.v1
id: RM-3
box_text_sha: t:96c0caa2c2bdfeb7
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:scripts/autopilot/screening_tier_runner.py
- epyc-orchestrator:src/autopilot_core/sequential_verdict.py
approach: 'Screening-tier protocol: small-n per-pairing FA/FR/CR with wide CIs, promotion rule to confirmation tier (Pareto
  quality-vs-cost), driven by the H8 autopilot action under no-concurrent-inference and placement-queue-not-/chat discipline.
  RM-3a/b/c built the runner, live bridge and first batch (frontdoor FA 16.7% FR 50.0%). Remaining: write the promotion rule
  (Pareto) into the runner with a test.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_screening_tier_promotion_rule.py
new_tests:
- tests/unit/test_screening_tier_promotion_rule.py
non_goals:
- no confirmation-tier run
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:scripts/autopilot/screening_tier_runner.py: b0110ac99b04c08454b4d604e739f1d63f5cd43b
    epyc-orchestrator:src/autopilot_core/sequential_verdict.py: 3a946e5cadbe2d26648a856b731dfc6f7d6a9232
---
