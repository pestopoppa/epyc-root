---
schema: epyc.brief.v1
id: TF-R8G-REFUSAL-HINT
box_text_sha: t:4eb7c4b2ad7be286
author: owner
written: '2026-11-24'
accepted: owner
where:
- epyc-root:scripts/coordination/taskflow/dispatch.py
approach: 'Find where r8f fix 4 (6694fcf50) put the refusal hint and confirm why the opencode permission deny drops it (opencode
  generates the denial text, not the shell helper). Move the hint into the proxy tool-result rewrite for ''Permission denied:
  shell'', or route the commands through a wrapper that prints it. Test in tests/coordination/test_taskflow_r8g_harness_fixes.py.

  '
acceptance: python3 -m pytest -q tests/coordination/test_taskflow_r8g_harness_fixes.py
new_tests:
- tests/coordination/test_taskflow_r8g_harness_fixes.py
non_goals:
- do not widen the shell allowlist beyond lane-local file moves
tier: terra
grounded:
  at: '2026-11-24'
  blobs:
    epyc-root:scripts/coordination/taskflow/dispatch.py: 1244813726590dc1baa1611fb79bf4750803484d
---
