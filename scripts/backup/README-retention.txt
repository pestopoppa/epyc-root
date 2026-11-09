Host install step (operator/host agent; this repo does not touch host crontabs or the root-owned script):

Live job: backup-claude-sessions.sh (root, host crontab 04:00). Its logs show "ROTATE kept newest 3 backups" and
"OPENCODE kept newest 7 snapshots". Replace those two inline rotation blocks:

  # ai-sessions rotation (after the tarball is written):
  python3 /workspace/scripts/backup/backup_retention.py ai-sessions --dir /mnt/raid0/llm/claude-backups --keep 1 \
      && echo "$(date -u +%FT%TZ) ROTATE kept newest verified backup" >> "$LOG"

  # opencode (per store: epyc, host-daniele, twyne), instead of unconditional compress + keep 7:
  python3 /workspace/scripts/backup/backup_retention.py opencode --dir /mnt/raid0/llm/claude-backups \
      --prefix opencode-epyc --source /mnt/raid0/llm/opencode-db/epyc.db --keep 3
  # exit 10 = unchanged, skipped (not an error); exit 3 = write/verify failed, previous snapshots kept.

Note snapshot names become <prefix>-YYYYMMDD-HHMMSS.db.zst (existing -YYYYMMDD-040001 names match the same glob).
Needs zstd on the host (not present in the dev container). Existing extra tarballs/snapshots are pruned on the first run.
