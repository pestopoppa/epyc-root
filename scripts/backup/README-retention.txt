Backup retention: installed host policy (2026-11-09, host owner; source of truth: filesystem-agent 3918872, runbook there).

Installed in daniele's crontab, not root's. Do not edit root's crontab, add a duplicate entry, or run the loop-state script as root.

  04:00  backup-claude-sessions.sh  ai-sessions keep 2, mirror-gated; opencode keep 3 per store (epyc, host-daniele, twyne), from the
         hourly read-only copies in /mnt/raid0/llm/opencode-db/ with a 2-hour freshness check
  04:45  backup_loop_state.sh  LARGE_DB_POLICY=weekly; findmnt mount guard, single-instance lock, refuses root

backup_retention.py exit codes: 0 ok, 2, 3, 4, 5 failure classes, 10 unchanged and skipped (see --help). Retention runs only when tar exits
<=1 and only against the exact --expect archive, and deletes only files verified on the mounted mirror.

Health check on the host: /home/daniele/filesystem-agent/scripts/backup-health-check.sh
Restore test: restore_test_loop_state.sh --scratch <dir> --vidya-cli /mnt/raid0/llm/epyc-root/scripts/vidya/cli.py (needs ~5 GiB, ~10 GiB on a Sunday snapshot).

Do not remove or modify opencode-epyc-pre-v2-20261106T0920Z.db; it is mirrored to the Micron and verified identical.
