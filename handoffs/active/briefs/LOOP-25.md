---
schema: epyc.brief.v1
id: LOOP-25
box_text_sha: a868f3dc77044d97
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/coordination/rowflow/rowflow.py
- epyc-root:scripts/coordination/churn/row_disk_budget.py
- epyc-root:.claude/skills/inference-backlog-scheduling/scripts/queue_status.py
approach: 'Disk forecast in the depth alarm: project free space from ARMED and READY est_output plus overnight growth, alarm
  before free space crosses the 150 GiB admission floor. Standalone forecast exists on unpushed branch rtg22-loop5-25 (1ef7299f0)
  but its first live run alarmed at a projected 21 GiB because ARMED rows were unfiltered and 503 rows lack est_output. Fix:
  filter to rows that can actually start, treat missing est_output as unknown (excluded and counted), land it, and wire into
  the depth alarm (ws58-ready-depth.sh lives outside git; vendor it in).

  '
acceptance: python3 -m pytest -q scripts/coordination/tests/test_disk_forecast.py
new_tests:
- scripts/coordination/tests/test_disk_forecast.py
non_goals:
- no admission change
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/coordination/rowflow/rowflow.py: 5e76c90af8cfa49c863684663c3ca56084adfa8d
    epyc-root:scripts/coordination/churn/row_disk_budget.py: c268f1f5e2fd253dfad77ecffb5fe47b848a4574
    epyc-root:.claude/skills/inference-backlog-scheduling/scripts/queue_status.py: a53b581b6ea822907905ad9bc5c2262159169870
---
