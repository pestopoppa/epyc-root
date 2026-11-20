---
schema: epyc.brief.v1
id: HUB-SUPERVISOR-STALE-ALARM
box_text_sha: f96d628be3c042b2
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/dashboard/refresh_hub_view.sh
- epyc-root:scripts/dashboard/hub_supervisor.sh
- epyc-root:dashboard/server.py
- epyc-root:scripts/dashboard/tests/test_hub_view_refresh.sh
approach: 'A dead supervisor writes no failure: the view froze 13:02-14:28 on 2026-11-09 while the page read 0 behind. Add
  a freshness check on .git/epyc-view-refresh.json mtime/updated_at (threshold a few multiples of the refresh interval) feeding
  /api/health (three-valued fold, not /health) and the page, with a negative control that a stale file degrades health. Honor
  the dashboard plane rule: registry entry plus probe plus freshness envelope already exist for the hub.

  '
acceptance: bash scripts/dashboard/tests/test_hub_view_refresh.sh
non_goals:
- do not change /health transport-only semantics
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/dashboard/refresh_hub_view.sh: ff5ae83073faee637efb99bb159003f1d48f050f
    epyc-root:scripts/dashboard/hub_supervisor.sh: 129feb595f871bffc31735b0724088f856a9cd61
    epyc-root:dashboard/server.py: 66558a2623df938e4c56d14c2847712c49c67aeb
    epyc-root:scripts/dashboard/tests/test_hub_view_refresh.sh: 99300dfe925deb2c09e5d5527efd9d539bcf90b7
---
