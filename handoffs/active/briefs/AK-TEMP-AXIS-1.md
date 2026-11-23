---
schema: epyc.brief.v1
id: AK-TEMP-AXIS-1
box_text_sha: t:043c8d95d44e3e4a
author: owner
written: '2026-11-23'
accepted: owner
where:
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/seed.py#L46-73
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/stage_bodies.py#L271-275
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/seeds/negatives.json
approach: 'New loop/sampling_axis.py holds normalize()/backfill()/is_spec_decode(); seeds/negatives.json gets a sampling field
  on every spec-decode/acceptance record (temperature 0 only for the two dtree/tree-verify records the handoff proves greedy,
  the string unknown otherwise); seed.install hashes each record WITHOUT its sampling key so legacy proposal_sha256 attempt
  identities do not move; stage_bodies._base stamps sampling from the candidate, unknown when absent. Tests in loop/test_sampling_axis.py.

  '
acceptance: python3 -m pytest -q scripts/kernel_rnd/autokernel/loop/test_sampling_axis.py scripts/kernel_rnd/autokernel/loop/test_seed.py
new_tests:
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/test_sampling_axis.py
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/sampling_axis.py
non_goals:
- do not change any existing negative's status, effect or reason
tier: local
grounded:
  at: '2026-11-23'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/seed.py: 24d4f980620289480d52427b15e3198c2888e1f1
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/stage_bodies.py: null
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/seeds/negatives.json: 949d85cfa4a652727556ced1e5a08ae022806ac6
---
