---
schema: epyc.brief.v1
id: EP-5
box_text_sha: 5e0d886d37b9042b
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:src/graph/trajectory_artifact.py
- epyc-orchestrator:src/graph/decision_gates.py
- epyc-orchestrator:src/graph/session_log.py
approach: 'First concrete step for: EP-5 — **Re-run the probe only after the `outcome` label defects below are fixed.** The
  current - 2026-11-09 audit: SV + UNDERSPECIFIED. The EPD-1 fix landed forward-only (orch `24b43990`, 2026-09-23). Box has
  no done-when; acceptance is the closest check.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_ep_5.py
new_tests:
- tests/unit/test_ep_5.py
non_goals: []
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:src/graph/trajectory_artifact.py: de8908e18c827a95958dc9cab7103a7c9b9bf481
    epyc-orchestrator:src/graph/decision_gates.py: 80c70c998f2a7660340b540ac94cd21f0e16ac46
    epyc-orchestrator:src/graph/session_log.py: 41b42f0581971def4e8388e3ac29abf759ab2574
---
