---
schema: epyc.brief.v1
id: AK-TEMP-AXIS-3
box_text_sha: t:e96766786324af2e
author: owner
written: '2026-11-23'
accepted: owner
where:
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/production_surfaces.py#L36-56
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/serving.py#L398
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/resolved_recipe.py#L868-874
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/served_shape_cases.py#L215-260
approach: 'Recipe.temperature and canonical_recipe_projection default become None and _validate_workload refuses None; _is_greedy
  requires an explicit 0 or top_k 1; Surface gains a required temperature from sampling_axis (registry role defaults plus
  :8083 = 1.0); served_shape_cases lanes gain served temperatures; the ne11 / accepted-length census key gains the temperature
  axis, legacy rows read as unknown. Recipe hashes of shipped recipes must not move.

  '
acceptance: python3 -m pytest -q scripts/kernel_rnd/autokernel/loop/test_temperature_axis_3.py scripts/kernel_rnd/autokernel/loop/test_production_surfaces.py
new_tests:
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/test_temperature_axis_3.py
non_goals: []
tier: local
grounded:
  at: '2026-11-23'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/production_surfaces.py: 6cb2ff92b3136b97d0f5c0b99eb72a2c33fcf6ff
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/serving.py: b66af859cc76b01a6d047d322115f8976f5a8cc9
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/resolved_recipe.py: 39968a070ffc23eef98ed8bc13e83c006ee9d93d
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/served_shape_cases.py: e9f3b2eaee6c803db085867eaa3a95939f97df0e
---
