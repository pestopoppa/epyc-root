---
schema: epyc.brief.v1
id: RM-4
box_text_sha: t:a4ca88ac688505fb
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/autopilot_core/sequential_verdict.py
- epyc-orchestrator:scripts/autopilot/screening_tier_runner.py
approach: 'Confirmation-tier protocol: fully paired (same tasks, prompts, grammar, stop, verifier budget), N>=100 per arm,
  paired flips via sequential_verdict.quality_trial_statistic, Holm across metric families, per-domain reporting. Step: implement
  the confirmation protocol driver (arms from a promotion list, pairing check refusing unpaired data, Holm) with unit tests.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_confirmation_tier_protocol.py
new_tests:
- tests/unit/test_confirmation_tier_protocol.py
non_goals:
- no live run in this box
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/autopilot_core/sequential_verdict.py: 3a946e5cadbe2d26648a856b731dfc6f7d6a9232
    epyc-orchestrator:scripts/autopilot/screening_tier_runner.py: b0110ac99b04c08454b4d604e739f1d63f5cd43b
---
