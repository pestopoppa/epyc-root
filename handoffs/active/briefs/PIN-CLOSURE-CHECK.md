---
schema: epyc.brief.v1
id: PIN-CLOSURE-CHECK
box_text_sha: 251b2dfe59a85958
author: backfill
written: '2026-11-20'
accepted: pending
review: backfill
where:
- epyc-root:scripts/operator/install_supervision_cron_20260916.sh
- epyc-root:scripts/dashboard/tests/test_install_supervision_cron.sh
- epyc-root:scripts/coordination/observer_guard.sh
approach: 'Installer must verify that every file the pinned scripts source is itself pinned (closure over source/. lines),
  or run once against the pin before swapping cron. observer_guard.sh and env.sh were added to the pin (763f9ed9a, 82ef9c06d)
  but there is still no closure check. Step: add the closure check to the installer and extend test_install_supervision_cron.sh
  with a negative control (pin missing a sourced file must be refused).

  '
acceptance: bash scripts/dashboard/tests/test_install_supervision_cron.sh
non_goals:
- no cron swap in the test
tier: luna
grounded:
  at: '2026-11-20'
  blobs:
    epyc-root:scripts/operator/install_supervision_cron_20260916.sh: 0ccc0bbecee127aa1aec75db26c0e61289e1fee5
    epyc-root:scripts/dashboard/tests/test_install_supervision_cron.sh: 6f10e3dfaafa9d6fad26523ff7110352078e2d96
    epyc-root:scripts/coordination/observer_guard.sh: 19c71faae8a3c2dbdaafc59b7781d1983bcb59c2
---
