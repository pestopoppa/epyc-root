---
schema: epyc.brief.v1
id: CDR-RT9-COVER-1
box_text_sha: t:a7b5ef66553f185b
author: intake
written: '2026-11-24'
accepted: owner
where:
- epyc-inference-research:scripts/benchmark/moe_routing/skew_report.py
approach: 'Point skew_report.py at the saved RT-9 trace directory, add a --residency 0.125 option that reports cumulative
  selection coverage of the top-k experts per layer, and split rows by domain (code / prose / reasoning) and by same-domain
  vs cross-domain hot sets. Write the table into the box.

  '
acceptance: 'per-layer coverage table filed under this box with the trace digest and verdict: CLOSE the resident-expert drafter
  idea if same-domain coverage at 12.5% is below 0.6, else record the coverage for the operator HBM allotment decision'
non_goals: []
tier: local
grounded:
  at: '2026-11-24'
  blobs:
    epyc-inference-research:scripts/benchmark/moe_routing/skew_report.py: d0e7583333c211d45bdadbd199a0561317bd38bb
---
