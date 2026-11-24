---
schema: epyc.brief.v1
id: RSL-R7
box_text_sha: t:827425937590b00a
author: planning
written: '2026-11-24'
accepted: owner
where:
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/seed.py
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/census_families.py
approach: 'seed.py and the negatives store gain op_family + shape_class keys; a range-overlap check suppresses duplicate seeds
  across models; hand-written entries carry a per-device saving estimate that census_families.rank prices

  '
acceptance: nice -n 19 taskset -c 84-87 python3 -m pytest -q scripts/kernel_rnd/autokernel/loop/test_seed.py nice -n 19 taskset
  -c 84-87 python3 -m pytest -q scripts/kernel_rnd/autokernel/loop/test_census_families.py
non_goals: []
tier: terra
grounded:
  at: '2026-11-24'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/seed.py: 077ec0599deadb22fdfaf6e8aeaa89c633af19f9
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/census_families.py: null
---
