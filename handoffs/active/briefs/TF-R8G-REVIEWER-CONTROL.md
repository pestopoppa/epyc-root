---
schema: epyc.brief.v1
id: TF-R8G-REVIEWER-CONTROL
box_text_sha: t:49b523e68c9c6bbc
author: owner
written: '2026-11-24'
accepted: owner
where:
- epyc-root:scripts/coordination/taskflow/verify.py
- epyc-root:scripts/coordination/taskflow/dispatch.py
approach: 'Add to the reviewer prompt the packet approach lines that define the done-when control test and any sanctioned
  skip, plus one rule: a passing test that asserts the failure is raised satisfies ''fails on X'', and a packet-sanctioned
  skip carrying a real errno is not not_done. Gloss the TU-GR-1 packet done-when as ''test_reachable_grader_is_flagged passes
  by asserting GraderReachable''. Test in tests/coordination/test_taskflow_r8g_harness_fixes.py using the r8g think TU-GR-1
  acceptance log.

  '
acceptance: python3 -m pytest -q tests/coordination/test_taskflow_r8g_harness_fixes.py
new_tests:
- tests/coordination/test_taskflow_r8g_harness_fixes.py
non_goals:
- do not loosen the vacuity guard
tier: terra
grounded:
  at: '2026-11-24'
  blobs:
    epyc-root:scripts/coordination/taskflow/verify.py: 0bad2fcb96e0abd7aba4f17b361af7b723f0f758
    epyc-root:scripts/coordination/taskflow/dispatch.py: 1244813726590dc1baa1611fb79bf4750803484d
---
