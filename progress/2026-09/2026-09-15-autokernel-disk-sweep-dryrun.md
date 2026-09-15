# 2026-09-15: AutoKernel disk sweep, DRY-RUN

**Scope.** This was a classification of leftover AutoKernel worktrees and tmp dirs, prepared for
the AutoKernel owner (bus `inference`, task `autokernel-hardening-20260915`, a Codex session) and
for the operator. **Nothing was removed.** No `--apply` was run, and no process was touched.

**Removal authority.** Every deletion needs the operator's manual confirmation before it
executes. `--apply` runs only after the operator reviews a manifest and confirms it, at a
boundary the AutoKernel owner chooses. The script enforces this in three ways:
- the manifest's exact SHA-256,
- an interactive TTY confirmation (typed sha prefix),
- a COMPLETE process probe. Unknown counts as busy, and the whole run is refused.

**Artifacts.**
- Tool: `scripts/system/autokernel_disk_sweep.py`, with tests in
  `tests/test_autokernel_disk_sweep.py` (15 passing, using temp git repos and a fake `/proc`).
- Design review: `docs/design/autokernel-disk-hygiene-20260915.md`.
- Full manifest (6.7 MB, not committed):
  `/mnt/raid0/llm/tmp/sub-aksweep/autokernel-disk-sweep-manifest-20260915T201303Z.json`,
  sha256 `277c222a6c9cc978697633c7b7099cb253cc37cb214f15f37fffa1b772e7a60f`.
  Two earlier manifests are in `superseded/`; their heuristics were tightened (see below).

## Result (20:13Z; 157 s; in-container, so process probe PARTIAL)

| Verdict | Count | GB | Where |
|---|---:|---:|---|
| KEEP-active-session | 18 | 68.2 | tmp 10 / 51.4 GB (five-loop store WAL live, continuous v7–v13); mains 7 / 14.2 GB; acceptance `akx-p0c-coverage-20260915` (Codex cmake cwd) |
| KEEP-live | 1 | 0.2 | `mains/ak-rebuild-20260828` (reaper script cwd) |
| KEEP-unverifiable | 31 | 95.8 | nested pool-lane worktrees of `llama.cpp` inside state dirs; nested clones in `autokernel-implementation-20260908`; 2 acceptance trees whose admin `gitdir` points into that dir |
| KEEP-dirty | 223 | 369.9 | acceptance 216 / 353.5 GB |
| KEEP-unpushed | 2 | 7.9 | `mains/autokernel-v27-integration-20260821`, `acceptance/autokernel-driver-v2-20260909` |
| KEEP-referenced | 35 | 27.2 | 23 INF-70 lanes cited by `cpu-decode-roofline-program.md` / audits; five-loop siblings; `champion2` (research recipe) |
| ARCHIVE-evidence | 1 | 2.2 | `tmp/autokernel-runtime-owner.c36411a7.PnMKzo` (210 sealed/SHA256SUMS files) |
| **REMOVE** | **14,225** | **34.8** | 28 worktrees (34.3 GB: mains 10, inf70 9, acceptance 9) plus 14,197 tmp dirs (0.6 GB: `autokernel-planner-anchor-*`, `aku-checkpoint.*`) |
| **Total** | 14,536 | 606.7 | |

**The dirty class.** The `dirty_landed` annotation never changes a verdict. Split by it:
- **68 trees (109.8 GB):** every dirty blob is already in network-remote history.
- **126 trees (212.4 GB):** partial.
- **29 trees (47.7 GB):** content exists nowhere else.

Resetting the 68 is a separate operator decision. The sweep never does it.

**Growth.** 607 GB of these trees were born between 08-21 and 09-15:
- 09-09 and 09-10 alone added 445 GB (acceptance fan-out at ~2 GB per full research checkout);
- steady state is ~8–24 GB/day from serial state-dir versions.

**Disk.** `/dev/md127` went from 154 GB to 337 GB free during the session. That was another
actor's reclaim, not this one.

## Guards added after reading the first real manifest

1. **Evidence patterns were too loose.** `receipt`/`seal` substrings matched `node_modules`
   icon packs, `__pycache__` and SEAL-paper result copies. They are now anchored patterns, and
   skip dirs are excluded.
2. **Local-path remotes.** `llama.cpp-cpu-fusion-20260829` has `origin`/`prod`/`champ` as local
   paths, so `--remotes` would have called local-only commits "pushed". Only network remotes count
   now (evidence-retention §3.4 E2).
3. **Held-store siblings.** `aku12a-glm53-five-loop-builds` was REMOVE while its store and inputs
   were live. Name-family siblings of held candidates, and paths named in their small state files,
   are now KEEP-referenced.

## Command for the owner (host, root, after operator review)

```bash
cd <checkout containing scripts/system/autokernel_disk_sweep.py>
# 1. fresh dry-run in the SAME context as the apply (host root => probe COMPLETE)
sudo python3 scripts/system/autokernel_disk_sweep.py --out-dir /mnt/raid0/llm/tmp/sub-aksweep
# 2. the operator reviews the new manifest's REMOVE rows, then on a TTY:
sudo python3 scripts/system/autokernel_disk_sweep.py --apply \
  --manifest /mnt/raid0/llm/tmp/sub-aksweep/autokernel-disk-sweep-manifest-<ts>.json \
  --manifest-sha <sha256 printed by step 1>
```

About that command:
- The in-container manifest above cannot be applied: its probe is PARTIAL and its paths are
  `/workspace`-based.
- Receipts go to `<manifest>.apply-<ts>.jsonl`.
- Manifests expire after 72 h.

## Open items (for the owner, not blockers here)

- **Backlog cause:** the 370 GB KEEP-dirty backlog comes from acceptance-ends-dirty. The fix is
  design recommendation #1 (an owner-bound reaper plus commit-or-discard).
- **Pool-lane registrations against the frozen `llama.cpp` clone** (187 under `tmp/`, lane ids up
  to `lane521`) need an explicit operator call before any `worktree remove` against that `.git`.
