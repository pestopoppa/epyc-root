# Disk is a bin

`/mnt/raid0` holds every output root, every worktree and the trash. One row that fills it breaks
every other row's writes (ENOSPC), so disk is admitted the same way RAM is.

- **Admission.** Each row declares `est_output_GiB` and `scratch_root`. Admit the row only if the
  free space on `/mnt/raid0` (`df --output=avail`) minus `est_output_GiB` stays above the floor.
  The standing floor is **150 GiB**. On 10-27 an interim floor of **50 GiB** applied while space
  was reclaimed.
- **The trash frees nothing until it is swept.** `/mnt/raid0/llm/.trash` is on the same filesystem,
  so moving files with `guarded_rm.sh` reclaims zero bytes. The calendar owner schedules
  `scripts/safety/trash-sweep.sh --older-than 1` daily, and every per-task wrap-up runs it
  (wrap-up Step 7b).
- **Profiling rows are heavy.** rocprof writes about 7 GB per run. After the result is accepted,
  compress the raw output with `xz`, check that the sha256 of the decompressed stream matches the
  original, and only then remove the original. `est_output_GiB` is the raw size, not the
  compressed size.
- **Scratch is cleaned only if it was declared.** Wrap-up cleans declared `**Scratch**` roots
  only, and on 10-27 137 handoffs declared none. A new row's `scratch_root` must also appear in
  the owning handoff's `**Scratch**:` header.

Origin: raid0 reached 100 % on 10-27 (98 GB of unswept trash plus about 45 GB of HSF raw rocprof
output), and an ORCH run died with ENOSPC.

## Automatic lifecycle (operator 2026-11-07: "we can't have so much disk leak")

Nothing on this list needs a manual triage pass; every step is zero-token and runs from the disk
janitor loop or at filing:

| Bytes class | Reclaimed by | When |
|---|---|---|
| Row raw/intermediates | `file_result.py` → `reclaim_row.py --apply` (declared `raw` globs or `raw_globs=` in notes; `raw_days` retention, default 0) | at filing |
| Row scratch not declared raw | keeper `--reap-now` (keep set + INPUT RULE, 1-day hold) | every 30 min |
| Row-owned worktrees (`<scratch_root>/worktrees/<name>`, made by `row_worktree.py add`) | `reclaim_row.py` → `worktree_salvage.retire` | at filing |
| Agent worktrees (`worktrees/*`, `.worktrees/*`) | `worktree_reaper.py --apply`: clean+landed idle ≥ 3 d removed; dirty/unlanded idle ≥ 7 d salvaged (bundle + `salvage/` branch), trashed, deregistered | daily |
| Kernel builds (`kernels/builds/*`) | `kernel_store_gc.py --apply` (unreferenced, not production/champion/C7r lineage, idle ≥ 7 d) | daily |
| KEEP markers under tmp/ | `scratch_lease.py backfill --apply --ttl-days 14` (marker expires with its lease) | daily |
| Root-owned / mode-555 residue | `owner_check.py --fix-modes` flags it (`sudo chown` line) ; row end `chmod -R u+rwX` (keeper patch) | daily / at row end |
| Trash (`.trash`, `.trash-reap`) | `trash-sweep.sh --older-than 1` | hourly |
| Per-row growth vs `budget_gib` | `row_disk_budget.py --alert` (alert `disk-budget` in rowflow-alerts.jsonl) | every 30 min |
| `~/.codex` rollouts | `codex_retention_reaper.py report` + `apply --no-packages` — rollouts >7 d with a vault copy deleted (operator reversed the 2026-10-04 rule for ~/.codex on 2026-11-07) | daily |

Declare, never infer: a row says what is disposable (`raw`), what it keeps (`keep`), how much it
will write (`budget_gib`) and where (`scratch_root`). `template_lint.py` WARNs at publish when
`budget_gib` or the raw declaration is missing; `file_result.py` refuses to file a row with no
`scratch_root`. A KEEP marker at ANY depth keeps its entry (`scratch_cleanup.py`, negative
control in `tests/test_scratch_cleanup.py`).

## 2026-11-23 lessons — root `.git` bloat and the `/mnt/raid0` reclaim (pipeline-mgmt)

`/mnt/raid0` fell to 154G free; a day of reclaim brought it to about 440G. Measured causes, in order of size:

- **PII pre-commit capsules never expire.** `scripts/hooks/pii_staged_capture.py` wrote one capsule per commit
  under `.git/epyc-private/pii-gates/`, each copying ~4,000 HEAD-subtree files (`comparison-tree-N.bin`) plus the
  full index: ~30 MB and 4,222 files per capsule, with no retention. 9,095 clean capsules (25.4M files, 98.6 GB
  du) were deleted; findings (exit!=0 260, not-passed 425), receipt-less (65) and recent (719) capsules were
  kept. `.git` went 223G to 38G with a safe repack (no `gc`). The fix is `RATIFY-PII-CAPSULE-20261123`
  (custody_format 2: record HEAD + tree id, re-derive from the object store, pack the index, delete clean
  capsules older than 2 days). Until it is signed the hook still writes ~30 MB per commit.
- **Pack history of whole-file rewrites.** The largest history paths are `research/intake_index.yaml` (616 MB
  packed, 377 versions) and the big handoffs (`autokernel-loop.md` 281 MB, `vidya-belief-substrate-program.md`
  235 MB): generated or append-heavy files committed in full every time. Not rewritten (history surgery needs
  an operator decision); the lever is to stop committing generated files and to compact handoffs.
- **Worktrees and `tmp/`.** ~33 worktrees removed through `worktree_gate.py`. The stale sweep
  (`/mnt/raid0/llm/tmp/tmp-stale-sweep-20261123/REPORT.md`): 530 GB in 4,757 top-level entries, 93 GB FILED or
  STALE-ORPHAN, and 397 dirs / 65 GB LIVE-but-idle-7d pinned only by an unfiled row, a FILLERS row, a claim or a
  dryrun log. A reaper that pins on those never reclaims them (PM-REAPER-RULES).
- Rowflow disk hardening now in place (`0514eecda`): DISK-WARN at floor+40G, 2 h idle reap under 200G free,
  `LARGE-DERIVED` flag, `worktree_gate.py by-owner`.

Rule: any per-commit hook that copies tree content must carry its own retention at creation. A growth path with
no reaper is a disk leak waiting for the next incident.
