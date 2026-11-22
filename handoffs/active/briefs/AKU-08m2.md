---
schema: epyc.brief.v1
id: AKU-08m2
box_text_sha: t:7990c97904c5b184
author: owner
written: '2026-11-22'
accepted: owner
where:
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/validation_consumer.py
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/validation_semantic_adapter.py
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/runtime_admission.py
approach: 'Write the runtime admission control reference and CalibrationReceipt next to each canonical receipt pair at capture,
  install RegisteredServingDecision with runtime_admission_control in the live authority, and connect the v5 transaction verifier
  to advance_validated.

  '
acceptance: pytest scripts/kernel_rnd/autokernel/loop/test_validation_final_receipt.py -k v5
non_goals: []
tier: local
grounded:
  at: '2026-11-22'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/validation_consumer.py: cb4de9e4fa21b6a5478ad34281f3ae9ab5fdf061
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/validation_semantic_adapter.py: c6f0c7a790eebd4f2d863c8e28981a440a30243e
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/runtime_admission.py: 5c3108aadf3d3adbcc2f750c8af7099759f1473d
---
