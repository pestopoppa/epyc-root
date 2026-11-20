---
schema: epyc.brief.v1
id: KPF-22
box_text_sha: 9319311583982cd2
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:tests/unit/test_kpf22_fairness_contract.py
approach: 'Bounded LPM bypass: a waiter with longer fp_history prefix match may skip the head at most once per waiter, FCFS
  no-starvation kept; ties/below-threshold spend no budget; unfittable prefix cannot bypass. Gate code already carries an
  LPM score (line ~299) and a fairness-contract test exists, so first check how much of the box is landed; implement the remainder
  once here (absorbs KVU-6 / INF-05 KV-3).

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_kpf22_fairness_contract.py tests/unit/test_prefix_index_admission.py
non_goals:
- do not tick KVU-6 or KV-3 boxes (other owners)
tier: terra
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:tests/unit/test_kpf22_fairness_contract.py: ab81f104cd5594275f902b6f9a718a7c69288ff3
---
