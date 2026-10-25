# Loop-state off-RAID0 backup: AutoKernel / AutoPilot / belief-kernel planning state

**Status**: OPEN, ready to dispatch. **Owner: the operator's filesystem agent** (host crontab + `/home/daniele/filesystem-agent/scripts/`). workspace-58 does not implement the host job.
**Created**: 2026-10-25 by workspace-58. Operator decision: "Nightly off-RAID0 backup (Recommended)", plus "this needs to be done by my filesystem agent".
**Parent index**: [routing-and-optimization-index.md](routing-and-optimization-index.md)
**Scratch**: none. The job writes only to its backup targets.
**Evidence**:
- `docs/reference/loop-planning-inputs-audit-2026-10-25.md`: the loops' planning inputs and their durability.
- `docs/reference/tmp-loss-reconcile-2026-10-25.md`: the reclaim losses and why backups could not restore them.

## Why
The AutoKernel and AutoPilot loops plan from state that is **single-copy on md127 (RAID0) with no backup**. The existing NIB2-92 job (`backup-claude-sessions.sh`, crontab `0 4 * * *`, local `/mnt/raid0/llm/claude-backups` keep 3, mirror on `/mnt/micron` = `/dev/nvme1n1p1`) covers only Claude and Codex transcripts and memory, plus the opencode DBs. Losing this state means losing the experimental history and seeded hypotheses the loops build on. md127 is also 94% full.

## Scope: back up exactly these (about 0.5 GiB total; sizes as of 2026-10-25)
| What | Path | Size | Notes |
|---|---|---|---|
| Belief ledger and reader state | `/mnt/raid0/llm/state/vidya/` (ledger.jsonl, ledger.jsonl.sync.json, loop-known-good/, loop-memo/, reads.jsonl) | about 45 MB | The canonical ledger, which is in no git repo. Copy while no ingest holds `ledger.jsonl.lock`, or copy under that lock. |
| AK live stores | `/mnt/raid0/llm/autokernel/campaigns/*/store*/{experiments.db,inbox/,accumulator-bundle.json,journal*,resume-claims.sqlite3}` | about 330 MB for the live set: q38fn `store-b0ba1d427` 317 MB, ds41-1017 `store/`, 27b `store/` | **Copy SQLite with `sqlite3 <db> ".backup <dst>"`**, or an equivalent online-backup API; never a plain `cp` of a live DB. The large historical DS41 DBs (4.3 GB and 1.1 GB) are a separate decision; see box 3. |
| AK loop memory | `/mnt/raid0/llm/autokernel/loop-memory/{experiments.db,inbox/}` | about 10 MB | Shared history plus 25 inbox seeds. |
| AK campaign input bundles | `/mnt/raid0/llm/autokernel/campaigns/*/inputs*/` | about 3 MB | Small JSON bundles. |
| AutoPilot state | `/mnt/raid0/llm/epyc-orchestrator/orchestration/{autopilot_state.json,autopilot_journal*.jsonl,autopilot_checkpoints/,repl_memory/strategies/,operator_hypotheses.yaml,operator_hypothesis_resolutions.jsonl}` | about 42 MB | The journal shards are gitignored and no checkpoint contains them. `strategies.db` must also be copied with `.backup`. |

Out of scope: `/mnt/raid0/llm/tmp/**`, models, builds, worktrees, and anything already in git.

## Tasks
- [ ] **BK-1** Write the job script in the filesystem agent's script dir, next to `backup-claude-sessions.sh`. It snapshots the scope above into a dated directory under `/mnt/micron/<loop-state-backups>/YYYYMMDD/`, which is off md127. Requirements:
  - SQLite DBs via online `.backup`; the ledger copied consistently.
  - A `SHA256SUMS` manifest written per snapshot.
  - Retention: keep 7 dailies and 4 weeklies.
  - Exits non-zero on any failure, with `LAST_STATUS` written the way NIB2-92 does it.
- [ ] **BK-2** Install it in the host crontab, offset from NIB2-92's 04:00 (for example 04:30), logging to a file next to `claude-backups/backup.log`.
- [ ] **BK-3** Decide the large historical AK DBs (`ak-ds41-cpu-decode-20260923/store/experiments.db` 4.3 GB, `store-b0ba1d427` 1.1 GB): weekly-only, or one-time cold copy. Record the choice here.
- [ ] **BK-4** Restore test. Restore the latest snapshot into a scratch dir, run `sha256sum -c`, and check:
  - `sqlite3 <db> "pragma integrity_check"` on every DB;
  - `python3 /workspace/scripts/vidya/cli.py --ledger <restored ledger> verify` reports chain_ok.
  Record the output here.
- [ ] **BK-5** Alarm on failure. A failed or missing nightly snapshot must be visible: the hub health probe, or the same channel NIB2-92 uses.

## Done when
BK-1..5 are ticked, two consecutive nightly snapshots exist with valid manifests, and the restore test passed.
