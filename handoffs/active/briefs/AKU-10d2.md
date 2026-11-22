---
schema: epyc.brief.v1
id: AKU-10d2
box_text_sha: t:d22ee88f7446b700
author: owner
written: '2026-11-22'
accepted: owner
where:
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/campaign_control.py
- epyc-inference-research:scripts/kernel_rnd/autokernel/loop/maintenance_execution.py
approach: 'Add the controller-owned maintenance tick that builds the native view, binds a job and executes it through CampaignMaintenanceBackend
  when a registered activated broker exists; otherwise report maintenance unavailable. Live deletion still needs operator
  activation.

  '
acceptance: pytest scripts/kernel_rnd/autokernel/loop/test_maintenance_execution.py -k caller
non_goals: []
tier: local
grounded:
  at: '2026-11-22'
  blobs:
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/campaign_control.py: 04ed5ca4da1d60868e5e47cc0cfbec30806818e4
    epyc-inference-research:scripts/kernel_rnd/autokernel/loop/maintenance_execution.py: 0846dd16cdd8aee033682758a40186900b6cf584
---
