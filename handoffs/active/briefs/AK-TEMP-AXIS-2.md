---
schema: epyc.brief.v1
id: AK-TEMP-AXIS-2
box_text_sha: t:48997579619cc124
author: owner
written: '2026-11-23'
accepted: owner
where:
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/dispatch_guard.py#L170-267
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/sampling_axis.py
approach: 'Add sampling_axis.reopen_scope(row, served) returning ''greedy'' for a spec-decode/acceptance record whose sampling
  set lacks a served-regime arm. In dispatch_guard.characterised_reason, drop such rows from the matches list before the 3-answer
  threshold so the mechanism is not do-not-repeat; render the scope on the prior_experiments row so the planner sees do_not_repeat_scope:
  greedy. Served regimes come from sampling_axis.served_temperatures() (registry role defaults + :8083 = 1.0).

  '
acceptance: python3 -m pytest -q scripts/kernel_rnd/autokernel/loop/test_sampling_axis.py scripts/kernel_rnd/autokernel/loop/test_dispatch_guard.py
new_tests:
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/test_sampling_axis.py
non_goals:
- do not change the refusal for non-spec-decode or covered mechanisms
tier: local
grounded:
  at: '2026-11-23'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/dispatch_guard.py: 5f543a92be14571b5bcaab34c88053f6616e8016
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/sampling_axis.py: null
---
