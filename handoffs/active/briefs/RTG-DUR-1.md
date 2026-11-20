---
schema: epyc.brief.v1
id: RTG-DUR-1
box_text_sha: 3c0012753d98661e
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:scripts/analysis/derive_duration_baselines.py
- epyc-orchestrator:src/registry/stack_priors.py
- epyc-orchestrator:src/registry/duration_baseline_freshness.py
- epyc-root:scripts/operator/ratify_autopilot_relaunch_era_20261109.sh
approach: 'First concrete step for: Refresh rule and compiler for `orchestration/derived/duration_baselines_by_role.json`.
  Box has no done-when; acceptance is the closest check.

  '
acceptance: python3 -m pytest -q tests/test_rtg_dur_1.py
new_tests:
- tests/test_rtg_dur_1.py
non_goals: []
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:scripts/analysis/derive_duration_baselines.py: bb1a3a3a26ec1987282703329cefb17ea15dfac4
    epyc-orchestrator:src/registry/stack_priors.py: 064fd13a8e2ad2f60b5407e18033e03335624d5b
    epyc-orchestrator:src/registry/duration_baseline_freshness.py: 44f6466a3901619f7e05cf5c7ddd23354a84e471
    epyc-root:scripts/operator/ratify_autopilot_relaunch_era_20261109.sh: 2fecaa5bfb5b47389276b5216e9ae11c32c162a5
---
