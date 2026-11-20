---
schema: epyc.brief.v1
id: TU-GR-1
box_text_sha: 7ed41a4520d860f6
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:docs/design/tu-grader-isolation-boundary.md
approach: 'Add a test that places a sentinel grader file outside any git worktree and launches the candidate process via the
  harness under the denial mechanism (bubblewrap mount namespace or separate uid per the boundary doc); assert open/traverse
  probes get ENOENT/EACCES. Negative control: with the grader deliberately reachable the test must FAIL (the done-when). Skip
  with explicit reason if bwrap is unavailable, never pass vacuously.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q scripts/autopilot/evals/dtap/tests/test_grader_isolation.py
new_tests:
- epyc-orchestrator:scripts/autopilot/evals/dtap/tests/test_grader_isolation.py
non_goals:
- no isolation claim from mocks; no judge or denominator change
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:docs/design/tu-grader-isolation-boundary.md: 7d86967f8cd2e3dad46c9b58bd650f7414dd247f
---
