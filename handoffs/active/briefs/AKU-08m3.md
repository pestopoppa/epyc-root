---
schema: epyc.brief.v1
id: AKU-08m3
box_text_sha: t:1c8c3a7d365eae34
author: owner
written: '2026-11-22'
accepted: owner
where:
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/test_feed_runtime.py
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/test_validation_semantic_adapter.py
approach: 'Isolate the ROOT adapter module load (sys.modules/registry state) between the two test files so the receipt projector
  tests are order-independent.

  '
acceptance: pytest scripts/kernel_rnd/autokernel/loop/test_validation_semantic_adapter.py scripts/kernel_rnd/autokernel/loop/test_feed_runtime.py
non_goals: []
tier: local
grounded:
  at: '2026-11-22'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/test_feed_runtime.py: 098a0a2339017965084435526f46b917dff0bdda
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/test_validation_semantic_adapter.py: b481c1fb3437e4466183cd2e73f27ca9e9c27304
---
