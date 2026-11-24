---
schema: epyc.brief.v1
id: VB-AK-BW-CENSUS-WIRE
box_text_sha: t:0af4bde87ecb3b1a
author: owner
written: '2026-11-24'
accepted: owner
where:
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/census_update.py
approach: 'Add a census adapter under scripts/vidya/adapters that reads mi210_bandwidth_census.json, projects each record
  (source_row, result_sha256, measured_at) to a ClaimTuple, and lets claim_tuple.grade() decide; refuse records missing a
  warrant field.

  '
acceptance: python3 -m pytest -q scripts/vidya/tests/test_bw_census_adapter.py
non_goals: []
tier: local
grounded:
  at: '2026-11-24'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/census_update.py: d29f0fab3b76f8ad84e6b4910a343c9014b8036f
---
