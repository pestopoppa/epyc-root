---
schema: epyc.brief.v1
id: TF-R8G-PATHSPEC-LRANGE
box_text_sha: t:00ed6e6a0b9dd5e5
author: owner
written: '2026-11-24'
accepted: owner
where:
- epyc-root:scripts/coordination/taskflow/verify.py::brief_paths
- epyc-root:scripts/coordination/taskflow/brief.py#L100-110
approach: 'In verify.brief_paths, after rest.split(''::'')[0], drop a trailing #L<a>(-<b>)? using the pattern brief.py uses.
  Add tests/coordination/test_taskflow_r8g_harness_fixes.py with the r8g WS4 case (where names scripts/coordination/tmux_adapter.py#L2301-2488
  and the lane modified scripts/coordination/tmux_adapter.py, so outside_pathspec returns []) and a forbidden_hits case.

  '
acceptance: python3 -m pytest -q tests/coordination/test_taskflow_r8g_harness_fixes.py
new_tests:
- tests/coordination/test_taskflow_r8g_harness_fixes.py
non_goals:
- do not widen pathspec beyond the named files
tier: terra
grounded:
  at: '2026-11-24'
  blobs:
    epyc-root:scripts/coordination/taskflow/verify.py: 0bad2fcb96e0abd7aba4f17b361af7b723f0f758
    epyc-root:scripts/coordination/taskflow/brief.py: 8c29f06952e13a0bfe513c0619362460659bfa89
---
