---
schema: epyc.brief.v1
id: HIL-15b
box_text_sha: 9b5eda0dd7113af9
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-orchestrator:scripts/trace/hil15a_flagon_run.py
- epyc-orchestrator:scripts/trace/hil15b_v2_make_tasks.py
- epyc-orchestrator:tests/unit/test_hil15b_v2_assets.py
- epyc-root:handoffs/active/harness-program.md
approach: 'Question: with the harder 16+4 task set (hil15b_tasks.json, pass band unmeasured), do we get >=3 failed recordings
  and ~10 outcome-variance tasks to feed HIL-16a verify and HIL-18a spectrum? Heavy cohort r12 stopped INCONCLUSIVE on a harness
  defect: unit.py validate line 33 asserts auc_table n_runs==1 and n_tasks==1 but unit-17 slots with no tool use give n_runs=0.
  First step: fix that assertion (accept n_runs==0 as no-dependency slot) in the packet''s unit.py under /mnt/raid0/llm/tmp/refactor-01a16fc3/hil15b-heavy-05-20-unsealed-20261029,
  keep units 06-16 read-only, rerun units 17-20 on a CPU quarter (Qwen3.6-35B-A3B-MTP-Q8_0, v10 CPU server, -t 24 -c 16384).
  Stop-on-answer when results DONE; futility on two infra failures.

  '
acceptance: cd /workspace/repos/epyc-orchestrator && python3 -m pytest -q tests/unit/test_hil15b_v2_assets.py
non_goals:
- no redraw of exposed units 03/05
- no full-cohort completion claim
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-orchestrator:scripts/trace/hil15a_flagon_run.py: 0b584e24f76c91316d8fd62c900af3d14f4ef366
    epyc-orchestrator:scripts/trace/hil15b_v2_make_tasks.py: 007c524984810a945797cb863f24eddcb23f05ae
    epyc-orchestrator:tests/unit/test_hil15b_v2_assets.py: 2576721087b3b4bc399c373624fa7aebb8ea4fcf
    epyc-root:handoffs/active/harness-program.md: cadd2da6b668a35f911a3b0ad52a85e94ee62ea0
---
