---
schema: epyc.brief.v1
id: AK-KEEP-ANSWER-KEY
box_text_sha: t:9f153e4a6b6730cc
author: intake
written: '2026-11-24'
accepted: auto
where:
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/accumulate.py
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/surface_fold.py::ExperimentalKeepReceipt
approach: 'Offline only: read retained receipts and journal shards, no benchmark. Label from later evidence already on record
  (serving-gate result, LOO arm, replication row). Re-apply the current keep rule to each stored receipt to get its decision.
  Split chronologically, older half for tuning and the later half as the test. Futility stop: fewer than 10 failed keeps means
  the set cannot score a gate change; close with the count.

  '
acceptance: the answer key and a report giving the false-keep rate on the test half are committed under epyc-inference-research
  scripts/kernel_rnd/autokernel/loop/, or the report shows fewer than 10 failed keeps and closes the box as futile
non_goals: []
tier: local
grounded:
  at: '2026-11-24'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/accumulate.py: 79988034c2dd4da5a3489ce84ed65c14864c4611
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/surface_fold.py: d69e45361db5a1dc18ee3945195056645e1c922a
---
