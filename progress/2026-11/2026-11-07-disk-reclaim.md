# 2026-11-07 — disk reclamation made automatic (operator directive, session operator-adhoc-ops-20261105)

Operator: "the fact that this STILL needs to be done manually is unacceptable … we can't have so much disk leak."

## Leak accounting (du/find, 2026-11-07 12:40Z; / had 171 GB free)

| Source | Bytes | Writer | Mechanism that should reclaim it | Why it did not |
|---|---|---|---|---|
| `/mnt/raid0/llm/tmp` row scratch (manifested) | ~176 GiB blocked across 209 WAIT + 99 INPUT-ONLY + 80 BLOCKED + 13 VAULT-REFUSED groups | rows | keeper `--reap-now` (every 30 min, working) | WAIT: ended but never FILED; INPUT-ONLY: no `started=`/`published_at` → nothing deletable; BLOCKED: an active handoff names the path; VAULT-REFUSED: `keep` glob matches GGUFs > 512 MiB (brf-exp01, 56 GB) |
| tmp unmanifested dirs | 131 GiB IDLE-WAIT (<1 d), 79 GiB KEEP-MARKED (190 dirs), 56 GiB BLOCKED-referenced (312), 40 GiB BLOCKED-git (28) | agents, codex, builds | keeper idle rule (1 d) | KEEP markers had no expiry (leases backfilled 11-04, expire 11-18); handoff references keep forever; unlanded clones |
| worktrees (`worktrees/`, `.worktrees/`) | 197 GB; 193 registered: 92 protected (mains/locked), 26 referenced, 25 dirty, 5 unlanded, 21 unverifiable, 19 recent | agents | `worktree_gate.py` (manual), keeper `REAP_WORKTREES` default OFF | nothing automatic; dirty trees parked forever |
| `kernels/builds` | 110 GB, 148 builds | AutoKernel / promotions | none | no GC existed; 126 kept by name in handoffs/FILLERS |
| `~/.codex` | 26 GB (sessions 7.6 G, thread_history 7.7 G, packages 6.7 G) | Codex | `codex_retention_reaper.py` | apply permanently disabled by ratified hard rule 2026-10-04 |
| container writable layer (epyc-root) | 80 GB: `/tmp` 56 GB (comgr `.so` JIT cache 12 GB/2270 files, pytest-of 3.3 G, epyc-eval-fence 6 G, root-ci-verify 2.4 G …) | ROCm comgr, tests, codex | none | `/tmp` is outside every guarded root and outside this project's hooks |
| other containers' layers | 29 + 28 GB (twyne, mystifying_rosalind) | other projects | — | not ours |
| `.trash` | 35 GB (< 1 day) | guarded_rm | hourly sweep at 1 d (working) | by design |
| root-owned residue under tmp/ | 288 entries, 3.4 GB (uid 0), 11 unwritable dirs | docker/sudo builds | none | trash-sweep cannot delete as node (the 42 GB build-e5efhhdt case) |
| deleted-but-open | 1 file (a superseded filler_run15.sh held by a poller) | — | — | negligible |
| logs | 155 MB | — | — | negligible |

## What is now automatic (branch disk-reclaim-20261107)

See `.claude/skills/inference-backlog-scheduling/references/disk-bin.md` → *Automatic lifecycle* and the janitor row in
`docs/guides/agent-workflows/backlog-churn-runbook.md`. New: `scripts/system/{worktree_salvage,worktree_reaper,kernel_store_gc,owner_check}.py`,
`scripts/coordination/churn/{reclaim_row,row_disk_budget}.py`, `scripts/coordination/job_templates/row_worktree.py`; changed:
`file_result.py` (scratch_root gate + reclaim at filing), `scratch_cleanup.py` (KEEP at any depth), `template_lint.py` (budget/raw WARNs),
`disk_janitor.sh` (BUDGET every 30 min; daily LIFECYCLE: WTREAP, KGC, OWNER, LEASE, CODEX report). Keeper patch (operator approval, NOT deployed):
`artifacts/operator/keeper-disk-lifecycle-20261107.patch` (INPUT-ONLY fallback to manifest mtime; row-end `chmod -R u+rwX` of the tmp job dir + OWNER-RESIDUE log).

Verified: `scratch_cleanup.py` honours a KEEP at a declared root on origin/main already (7f1aa593d); the remaining gap was a KEEP below the
top level — fixed, with negative controls.
