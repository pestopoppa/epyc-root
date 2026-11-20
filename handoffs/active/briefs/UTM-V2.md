---
schema: epyc.brief.v1
id: UTM-V2
box_text_sha: 3eb9b29e1d577078
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/typed_decisions/tool_choice_args.py
- epyc-orchestrator:src/api/routes/dashboard.py
- epyc-orchestrator:src/aggregation/planner.py
approach: 'First concrete step for: Add a local scoped write proposer, not an authoritative writer. Box has no done-when;
  acceptance is the closest check.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_utm_v2.py
new_tests:
- tests/unit/test_utm_v2.py
non_goals: []
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/typed_decisions/tool_choice_args.py: ff9e069f2b99bee2692f77bf843ed11c07a125e2
    epyc-orchestrator:src/api/routes/dashboard.py: 098e5c95f705b8c12517db2a1c04b9dd89910511
    epyc-orchestrator:src/aggregation/planner.py: f25c60c1cf6ee424551c6776283a2e8306791f9b
---
