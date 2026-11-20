---
schema: epyc.brief.v1
id: NUMA-DECOUPLE-1
box_text_sha: t:301913b8a35fbe93
author: owner
written: '2026-11-20'
accepted: owner
where:
- epyc-inference-research:scripts/benchmark/server_numa_np_sweep.py::summarize_cell
- epyc-inference-research:scripts/benchmark/server_numa_np_sweep.py::_apply_basis_caveat
- epyc-inference-research:scripts/benchmark/tests/test_server_numa_np_sweep.py
approach: 'In summarize_cell (server_numa_np_sweep.py ~L1501), delete the ''empty_trimmed_window'' entry from decision_grade_blockers.
  Add row key ''trimmed_window_empty'': (not trimmed_window_ready) and a ''caveats'' list carrying the same text. Leave trimmed_aggregate,
  tasks_per_hour_trimmed and TRIM_DEFINITION untouched.

  In _apply_basis_caveat (~L2469), also demote status decision_grade -> decision_grade_caveated when any member cell has trimmed_window_empty,
  appending a reason.

  Update the two existing asserts in test_server_numa_np_sweep.py (~L1045, ~L1240) to the new blocker lists.

  New test_decision_grade_decouple.py: copy the fixture pattern of test_empty_trimmed_window_demotes_decision_grade_cell and
  assert decision_grade True, trimmed_window_empty True, tasks_per_hour_trimmed == 0.0. Add one _apply_basis_caveat case.

  Re-grading the 5 banked cells is an offline re-summarize of the existing run dirs, done after the code lands; it is not
  part of acceptance.

  '
acceptance: cd /workspace/repos/epyc-inference-research && python3 -m pytest -q scripts/benchmark/tests/test_decision_grade_decouple.py
  scripts/benchmark/tests/test_server_numa_np_sweep.py
new_tests:
- epyc-inference-research:scripts/benchmark/tests/test_decision_grade_decouple.py
non_goals:
- do not amend TRIM_DEFINITION or change any banked throughput number
- no new measurement runs or inference
- do not touch capture-failure or cache-reset blockers
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-inference-research:scripts/benchmark/server_numa_np_sweep.py: de2c6388247191d27d739df13d3f223070a6c788
    epyc-inference-research:scripts/benchmark/tests/test_server_numa_np_sweep.py: 71ece2a77a472b0f1f4c2aeefa9de1d067c7ee05
---
