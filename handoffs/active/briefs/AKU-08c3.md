---
schema: epyc.brief.v1
id: AKU-08c3
box_text_sha: t:25b9315c105d2c93
author: owner
written: '2026-11-22'
accepted: owner
where:
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/feed_runtime.py
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/validation_semantic_adapter.py
approach: 'Have the comparison estimator owner write a content-addressed RegisteredComparisonReceipt before the run (pair
  digests, ClaimKey, estimator conclusion/value) and journal it so ReceiptBackedFindingProjector reads it instead of the fixture.

  '
acceptance: pytest scripts/kernel_rnd/autokernel/loop/test_feed_runtime.py -k comparison_receipt
non_goals: []
tier: local
grounded:
  at: '2026-11-22'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/feed_runtime.py: 07c07414320cfc31477032ab7625b2bbc35f1ff1
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/validation_semantic_adapter.py: c6f0c7a790eebd4f2d863c8e28981a440a30243e
---
