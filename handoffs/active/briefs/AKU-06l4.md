---
schema: epyc.brief.v1
id: AKU-06l4
box_text_sha: t:1f9c0660925ff591
author: owner
written: '2026-11-22'
accepted: owner
where:
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/operation_accounting.py
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/candidate_transactions.py
approach: 'Route a settled v2 prerequisite (with enrollment_ref) into candidate feedback and planner prerequisite refresh
  without treating enrollment as execution completion.

  '
acceptance: pytest scripts/kernel_rnd/autokernel/loop/test_operation_accounting_v2_children.py -k feedback
non_goals: []
tier: local
grounded:
  at: '2026-11-22'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/operation_accounting.py: 46fea2360590c08c461c1f991a9a28a14637280c
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/candidate_transactions.py: 3203850b0fbabff8638fec827c16fcb2e7b9d0a6
---
