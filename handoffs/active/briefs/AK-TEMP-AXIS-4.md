---
schema: epyc.brief.v1
id: AK-TEMP-AXIS-4
box_text_sha: t:6e3d2ac3ef56e602
author: owner
written: '2026-11-23'
accepted: owner
where:
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/gates.py#L1-60
approach: 'New spec_temperature_gate module holds the pure decision (served-temperature arm present, distribution result present
  and within bound when T>0); gates.py gets one thin call at the verdict step. First check whether SPEC-PIT.1 exists in code;
  if not, define the hook interface (TV/KL vs no-draft) and fail closed until a result is supplied.

  '
acceptance: python3 -m pytest -q scripts/kernel_rnd/autokernel/loop/test_temperature_axis_4.py scripts/kernel_rnd/autokernel/loop/test_gates.py
new_tests:
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/test_temperature_axis_4.py
non_goals: []
tier: local
grounded:
  at: '2026-11-23'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/gates.py: 9b7a5414e7833ea24061e5c5cf7be1d94dd03b69
---
