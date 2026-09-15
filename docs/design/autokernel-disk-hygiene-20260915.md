# AutoKernel Disk Hygiene: a design review

**Status:** recommendation. Nothing is implemented in the loop, and nothing was removed.
**Date:** 2026-09-15
**Audience:** the AutoKernel lane owner (bus id `inference`, task `autokernel-hardening-20260915`,
currently a Codex session) and the operator.
**Companion tool:** `scripts/system/autokernel_disk_sweep.py`, dry-run only. See §6.
**Dry-run record:** `progress/2026-09/2026-09-15-autokernel-disk-sweep-dryrun.md`

> **Removal authority.** This review and its sweep script are DRY-RUN deliverables. Every deletion
> needs the operator's manual confirmation before it executes. `--apply` runs only after the
> operator has reviewed the manifest and confirmed it, at a boundary the AutoKernel owner chooses.
> The script enforces this: `--apply` needs the manifest's exact SHA-256 plus an interactive
> operator confirmation on a TTY. No agent runs `--apply`. That matches the ratified
> evidence-retention clause (§3.7, "Operator-only, without exception", item 1): every
> pre-existing worktree under `/mnt/raid0/llm/` is operator authority.

---

## 0. TL;DR

The loop's disk cost comes from **creation without an owner-bound reaper**, not from a single
large artifact. About 607 GB of AutoKernel-shaped trees were created in 26 days (2026-08-21 to
2026-09-15). 445 GB of that came in two days (09-09 and 09-10), when roughly 186 acceptance
worktrees were made at about 2 GB each, each a full `epyc-inference-research` checkout. None of
them was ever collected.

Most of the reclaimable space is not safely reclaimable today. Most acceptance trees are
**dirty**: they hold uncommitted packet diffs, and for many of those diffs the exact blob never
reached a remote. The hard rule "never remove a dirty tree" is doing its job. The fix is upstream:
make the loop and the agents that drive it stop producing trees that end up dirty, orphaned and
unowned.

Top five, ranked by GB saved against quality risk (details in §5):

| # | Change | GB impact | Quality risk | Mitigation |
|---|---|---|---|---|
| 1 | Reaper registered where every worktree is created, on every exit path; acceptance becomes commit-or-discard | stops ~2 GB per acceptance tree (~370 GB of the current backlog is this class) | low | the reaper refuses dirty or unpushed trees and writes a tombstone. It never uses `--force`. |
| 2 | Sparse / `--no-checkout` acceptance worktrees (code-only cone) | ~1.6 of 1.8 GB per research tree (`benchmarks/` 1.1 G, `data/` 490 M, `artifacts/` 146 M) | low-medium | the cone is derived from the packet's touched paths plus its test imports. A cone miss FAILS the check (ImportError or missing fixture); it never passes. |
| 3 | Per-state-dir lane reuse: one `workers/`+`builds/` per target, not per `--state-dir` version | ~2 GB per continuous/profile/final-state version (27 versions on disk, 45.4 GB) | medium | reuse keeps `pool.reset_to_champion`'s force-reset and adds a full `clean -ffdx` outside the build dir, plus a tree-hash assert before each candidate |
| 4 | Retention by verdict: keep receipts and sealed evidence, expire E1 build trees and E2 worktrees under the ratified §3.4 predicate | build dirs 0.8–1.3 GB per candidate; `cpu-profiles` 25.5 GB in one store | low when E1/E2 conjuncts hold | tombstone written and fsynced before unlink (§3.5 ordering); patch bundle, tree hash and binary SHA stay in git |
| 5 | Three-state disk admission gate at lane/window open, host-reserve fail-closed, plus a size-attribution alarm | prevents the next 96 % event rather than reclaiming | none to quality; availability risk only | `UNKNOWN` (statvfs error, wrong mount identity) counts as refuse, never pass |

Shared ccache (§4.2) is **not** in the top five. It saves CPU time more than disk, and a
shared cache directly contradicts the loop's clean-build contract (`execution/worktree.py:95-110`).

---

## 1. Measured state (2026-09-15, dry-run)

Figures come from the dry-run manifest (see the progress note for the per-verdict table).
Sizes are allocated bytes from one `du -B1` pass, so a hardlink is counted once.

- **Candidates:** 14,536 top-level entries, 606.7 GB across `worktrees/acceptance/*` (230),
  `worktrees/mains/{ak,aku,akx,autokernel,s3-aku}*` (~35), `worktrees/inf70/*` (33), and
  `tmp/{aku*,autokernel-*,glm53-validation-*}` (14,266).
- **Count vs bytes are inverted.**
  - 13,964 `tmp/autokernel-planner-anchor-*` dirs (about 8 K each) come from a test helper that
    never cleans up: research `loop/test_unified_planner.py:204`,
    `tempfile.mkdtemp(prefix="autokernel-planner-anchor-")`.
  - 225 `tmp/aku-checkpoint.*` dirs (about 4 M each; scratch `GIT_INDEX_FILE` plus tokens).
  - Together these are under 1 GB, but they are 98 % of the entries.
  - The bytes sit in about 300 worktrees and a dozen state dirs.
- **Verdicts:** 14,225 REMOVE rows total only 34.8 GB. That is 28 worktrees (34.3 GB) plus
  14,197 tiny tmp dirs (0.6 GB). 223 trees (369.9 GB) are **KEEP-dirty**.
- **The dirty class, split by the `dirty_landed` annotation** (the exact working-tree blob of each
  dirty file, searched for in network-remote history):
  - 68 trees (109.8 GB) have *all* dirty content already on a remote. An operator-reviewed reset
    would make them removable.
  - 126 trees (212.4 GB) are partially landed.
  - 29 trees (47.7 GB) hold content that exists **nowhere else**.
  - This is the concrete cost of acceptance-ends-dirty (§2.1).
- **Disk free moved during this work,** from 154 GB (96 %) to 337 GB (91 %) on `/dev/md127`.
  Someone else reclaimed about 180 GB in the same hour. Any budget number in this doc is a
  snapshot.

### 1.1 Growth rate (derivable)

Birth time (`stat %W`) of each candidate, bucketed by day, against its current size:

| Day | New entries | GB | Cumulative GB | Where |
|---|---|---|---|---|
| 08-21 | 6 | 15.2 | 15.2 | mains |
| 08-27/28 | 8 | 15.4 | 30.7 | mains |
| 09-02 … 09-07 | 33 | 34.8 | 65.4 | inf70 lanes |
| 09-08 | 5 | 46.9 | 112.3 | tmp stores (`aku12a-glm53-five-loop-store`, `autokernel-implementation-20260908`, `glm53-validation-20260908`) |
| **09-09** | 13,474 | **266.4** | 378.8 | acceptance 195.9, tmp 52.0, mains 18.5 |
| **09-10** | 980 | **178.9** | 557.6 | acceptance 170.1 |
| 09-11 … 09-15 | 30 | 49.1 | 606.7 | tmp state dirs (continuous v1–v13, profile-proof v3–v9) |

Reading the table:

- **Burst rate:** 180–270 GB/day while agents fan out acceptance checks. That burst took the
  host to 96 %.
- **Steady-state rate:** about 8–24 GB/day from serial/continuous state dirs. Each new
  `--state-dir` version re-provisions lanes and builds (§2.3).
- **Store growth:** `aku12a-glm53-five-loop-store` went from birth on 09-08 to 40 GB on 09-15,
  about 5.7 GB/day, dominated by `cpu-profiles` (25.5 GB, `loop/cpu_profile.py:1159`).
- **Caveat:** birth time dates the directory, not its growth, so the store figure is a lower
  bound on its daily rate.

---

## 2. Where trees are created, and why they are never collected

All citations are `epyc-inference-research@origin/main` (a146fe28) unless marked as root.

### 2.1 Acceptance worktrees: 230 trees, about 370 GB. No code creates them.

- **No loop code writes to `worktrees/acceptance/`.** A search of all three repos finds only
  prose. The only hits are root `progress/2026-09/2026-09-09-autokernel-unified-20260908.md:116,1096`.
- **Agents create them by hand** to review or prove a packet: `git worktree add`, apply a patch,
  run tests. Some trees still hold hand-dropped `*.apply_patch`, `*.sha256` and `*-HANDBACK.md`
  files.
- **Owners:** research 178, root 41, orchestrator 4, `llama.cpp` 1.
- **All checkouts are full**, not sparse.
- **They are never collected, for four reasons:**
  1. **No creator, so no reaper.** The loop's own worktree creators *do* clean up, which proves the
     pattern exists and simply is not used for acceptance:
     - `controller/loop_scaffold_runner.py:1108-1117` removes its worktree in a `finally:` on
       both success and failure, and writes `worktree-cleanup.json`.
     - `controller/discovery_static_registry.py:3498-3510` runs `teardown_worktree` in a `finally:`.
  2. **The acceptance flow ends dirty.** The packet is applied *uncommitted*, reviewed, then
     landed from a different tree (often after edits). The applied diff stays behind as the only
     working-tree copy.
  3. **`git worktree prune` would not help, and is forbidden anyway.** Prune removes only
     *missing* directories, and all 178 research entries still exist, so none are prunable.
  4. **Nothing assigns ownership,** so no session will ever feel entitled to remove another
     session's tree. That instinct is correct: see the 2026-08-12 five-lane loss.

### 2.2 `source_loo`: creation with no collection, inside the loop

`loop/source_loo.py:173-176` creates one detached worktree and one build dir per kept mechanism:

```python
source = directory / f"omit-{keep.keep_id}"
build = directory / f"build-{keep.keep_id}"
surface_fold._git(repo, "worktree", "add", "--detach", str(source), assembled_commit)
```

- **Build:** `gates.compiles(source, build, ...)` then builds it (`:191`).
- **No teardown:** the only `finally:` (`:223-224`) restores CPU affinity. No `worktree remove`
  and no `rmtree` appear anywhere in the file.
- **Cost:** a leave-one-out round costs `n_keeps` × (llama.cpp tree + build) and leaves all of it
  behind.

### 2.3 Pool lanes: reuse by design, multiplied by state-dir versions

- **Provisioning:** `loop/pool.py:97-139` provisions `lane{i}` worktrees of `SOURCE_REPO`
  (`/mnt/raid0/llm/llama.cpp`, `:48`) under `worker_root`, with builds under `worker_build_root`.
- **Stated rule:** *"An existing lane directory is REUSED, never deleted"* (`:113-114`).
- **Reset:** `reset_to_champion` (`:153-180`) force-checks-out the champion sha and runs
  `clean -fd ggml/ src/`.
- **The lane rule is sound.** The leak is one level up:
  - `loop/serial_run.py:924` derives `target_root = args.state_dir / "targets"`, and `run.py:2393`
    provisions into it.
  - Every new `--state-dir` (continuous v1…v13, profile-proof v3…v9, final-gpu-state v3…v6,
    standalone-state v1/v2) gets a **fresh** `targets/<sha>/workers/lane0..6` (7 × 166 M) plus
    `builds/lane0` (827 M).
  - Old versions are never collected. `serial_run.py` deletes exactly one thing,
    `candidate_path.unlink` at `:715`, and `batches/batch-%06d` (`:1499`, `:1969`) is never pruned.
- **Registration churn:** the lane `.git` files read `llama.cpp/.git/worktrees/lane521`, so about
  520 lane registrations have been created against the **production** clone. That clone holds
  230 registered worktrees, 187 of them under `tmp/`.
- **Local-path remotes:** `llama.cpp-cpu-fusion-20260829` (the INF-70 lanes' clone) has
  `origin → tmp/ak-loop-tree` and `prod → /mnt/raid0/llm/llama.cpp`. A `--remotes` containment
  check would count those local refs as "pushed", which evidence-retention §3.4 E2 forbids. The
  sweep counts only network remotes.
- **Frozen-tree caveat:** removing those registrations is `git worktree remove` against the
  frozen tree's `.git`. It needs an explicit operator call even when every lane is clean. The
  sweep marks them `KEEP-unverifiable` ("nested git worktree owned by /mnt/raid0/llm/llama.cpp").

### 2.4 Stores and validation trees

| Store | Size | What it holds | Status |
|---|---|---|---|
| `tmp/aku12a-glm53-five-loop-store` | 40 GB | `cpu-profiles` 25.5 G, `experiments.db` 4.4 G + WAL, `serving-beliefs` 3.3 G, `runtime-source-floors` 1.7 G | live: orchestrator `orchestration/launch_manifest.yaml:842` (`AUTOKERNEL_LOOP_STORE_ROOT`) and research `loop/historical_trajectory.py:169` reference it, and its WAL changed during the scan |
| `tmp/autokernel-implementation-20260908` | 27.7 GB | dispatch/result markdown plus nested `maintenance-acceptance.*` (9.1 G, 7.3 G) and `consumer-feed-*` (2.1 G each) research clones and worktrees | two registered acceptance worktrees point INTO it (`autokernel-journal-feed-audit-20260909`, `autokernel-evidence-feed-deadline-20260909`: the admin `gitdir` names `consumer-feed-current-verify/.git`). Removing the dir first would orphan them. |
| `tmp/glm53-validation-20260908` | 14 GB | `artifact` 11.3 G, build logs, baselines, candidate `bin` | cited as evidence by root `docs/reference/models/glm53-*.md` and `handoffs/active/glm53-flash-evaluation.md:122` |

### 2.5 Existing guards

- **Disk floor:** the only one is `execution/live_controls.py:675,724`,
  `PASS if shutil.disk_usage(output_root).free >= 200 GiB else FAIL`, checked at campaign open.
  It has three problems:
  - **It is two-state.** An exception in `disk_usage` is a crash, not `UNKNOWN`.
  - **It is a literal**, where the ratified clause says `storage_floor_bytes_free` is *derived*
    per campaign (evidence-retention §3.6(a)(b)(c)).
  - **It is path-keyed, not mount-keyed.** `/mnt/raid0` is `md127` on the host but can appear as
    `overlay` in a container, where `df /mnt/raid0` reports the root overlay.
- **Unguarded paths:** nothing in `pool`, `serial_run` or `source_loo` checks disk.
- **Anchor pruning:** `pool.prune_anchor_generations` (`:444`, `ANCHOR_GENERATIONS_KEPT = 1`) is
  the only in-loop reclaimer, and unified deletion is disabled in it (`:453-455`).

---

## 3. Constraints any fix must respect

1. **Never `git worktree prune`, never `git gc`, never `worktree remove --force` on a dirty tree.**
   (Five lanes destroyed on 2026-08-12. `pool.py:113` exists because of it.)
2. **Clean builds are a correctness contract,** not a performance preference:
   `execution/worktree.py:95-110` turns `GGML_CCACHE` OFF because a cache populated by another
   tree makes a "fresh build directory" not clean, and `build_dir_pre_build_digest ==
   EMPTY_TREE_SHA256` cannot see that.
3. **Evidence retention is ratified law.** Only E1 (rejected-candidate build tree), E2 (worktree
   of a retired campaign, all commits reachable from a REMOTE ref) and E3 (raw profiler trace
   older than its lineage) are expirable by the loop. Expiry requires all eight §3.4 conjuncts and
   a fsynced tombstone *before* unlink (§3.5). Anything else is operator authority (§3.7).
   (`artifacts/operator/autokernel-policy-draft/evidence-retention.draft.md`, referenced from
   `measurement/protocols/kernel-research.md:177-183` precondition 7.)
4. **`host_reserve_bytes` fails closed.** An unset reserve is non-conforming, never zero (§3.6).
5. **Frozen production clone.** Lane worktrees registered against `/mnt/raid0/llm/llama.cpp`
   touch the frozen tree's `.git`, so creating or removing them is an operator-visible act.

---

## 4. Options, each with its quality risk and a mitigation

### 4.1 Lifecycle ownership: whoever creates a tree registers its reaper at the same point

**Mechanism.** Add one context manager, `owned_worktree(repo, path, commit, *, purpose, owner,
retention)`, in `execution/worktree.py` next to `teardown_worktree` (`:2037`). It works like this:

- **At creation,** it writes an ownership record (owner bus id, task id, purpose, creator pid,
  retention class E1/E2/durable) to `<store>/worktree-ledger.jsonl`.
- **On exit** (success, exception, `KeyboardInterrupt`, or `RunAborted`) it evaluates the same
  predicate the sweep uses: clean, pushed, no live holder.
  - If the predicate holds, it removes the tree and appends a tombstone.
  - If not, it **refuses** and appends a `retained` row naming the reason.
- **For crashes it cannot catch** (SIGKILL, reboot), the ledger is how the next run finds and
  finishes the reap. No path is ever discovered by name pattern.

**Where it applies:**
- `source_loo.py:173-176`: wrap `omit-*`/`build-*`.
- Agent acceptance checks: a `scripts/system/acceptance_worktree.sh` helper that creates, runs,
  and then either commits and pushes to a `accept/<packet>` branch, or discards. **Acceptance
  must never end dirty.** Commit-or-discard is what makes it removable.
- `serial_run`: register `targets/<sha>` lanes against the state dir so that retiring a state dir
  retires its lanes.

**Quality risk.** Reaping a tree whose result is still needed: a failure left for diagnosis, or a
build binary a later confirmation needs.

**Mitigation.**
- The reaper removes *only* what the §3.4 predicate allows. A **failed** candidate's tree is kept
  under a bounded hold (`retention_hold_boundaries`) with a tombstone-on-expiry, so it is not
  deleted at exit.
- A confirmation that needs the binary declares it in `protect=` (the same shape
  `prune_anchor_generations` already takes).
- Dirty trees are never reaped. That forces the commit-or-discard discipline, which also makes
  the acceptance record reproducible, which is a quality *gain*.

### 4.2 ccache or a shared build-object cache across lanes

**GB impact.** Small on disk. It shares compiled objects, not trees, and each build dir still
links its own binaries. The main win is CPU minutes per candidate.

**Quality risk: HIGH.** This is exactly the hazard `execution/worktree.py:95-110` documents.
- A cache hit from a different tree can link stale objects and hide a compile error the snapshot
  would surface.
- For kernel candidates, a stale object in `ggml-cpu` or `ggml-hip` means the measured binary is
  not the candidate. That is the INF-70 C9 class of failure (a library that predates its own fix).

**Mitigation, if pursued at all:**
- ccache only in `direct_mode` with `hash_dir=true`, `sloppiness` unset, and the compiler
  identity included.
- Never for the promotion/confirmation build, which stays `GGML_CCACHE=OFF` and clean.
- Record `ccache_enabled` in `BuildLogFacts` (already done).
- A correctness check whose build used the cache is a **screen**, never a claim.

**Recommendation:** do not adopt for disk. Revisit only as a screen-tier throughput measure.

### 4.3 `git worktree add --no-checkout` plus sparse checkout for acceptance

**Mechanism.**

```bash
git worktree add --no-checkout <p> <c>
git -C <p> sparse-checkout set --cone <cone>
git -C <p> checkout
```

Derive `<cone>` from:
- the packet's `git diff --name-only`,
- the transitive import closure of the tests it runs (`python -m modulefinder`, or a static
  `import` scan),
- plus `pyproject.toml`/`conftest.py`.

For research, `scripts/kernel_rnd/autokernel/**` + `tests` + `conftest` is about 60 M against a
1.8 G full checkout, so roughly 90 % of the tree is excluded.

**Quality risk.** A test that reads a data fixture outside the cone (`benchmarks/`, `data/`) or
imports a module outside it. The check would then run against an incomplete tree.

**Mitigation.** Absence fails loudly:
- a missing module is `ImportError`,
- a missing fixture is `FileNotFoundError`,
- so a cone miss turns a pass into a FAIL, never a fail into a PASS.

Two exceptions and the extra guards they need:
- **Tests that skip when a fixture is missing** (`pytest.skip` on absent data) can silently pass.
  Guard: the acceptance runner fails if the skip count differs from a full-checkout baseline
  recorded once per base commit.
- **Build acceptance (llama.cpp)** should keep full checkouts. CMake globbing over a sparse tree
  can silently drop sources.

### 4.4 One reusable acceptance worktree per repo, reset between candidates

**GB impact.** Caps acceptance at one tree per repo (about 2 GB × 3) instead of one per candidate.

**Quality risk: MEDIUM-HIGH.** State leaks between candidates:
- untracked files, `__pycache__`, `.pytest_cache`, `.gitnexus`,
- a previous candidate's build dir,
- environment side effects written into the tree.

For kernel builds a leaked build dir is the ccache hazard again. `pool.reset_to_champion` shows
the partial version: `clean -fd ggml/ src/` is scoped, so files outside those dirs survive.

**Mitigation, if adopted:**
- Reset with `checkout --detach --force <sha>`, `reset --hard`, `clean -ffdx` (whole tree,
  *including ignored*), with the build dir kept **outside** the tree and recreated empty.
- Before each candidate, assert:
  - `git status --porcelain --ignored` is empty,
  - `write-tree` equals the base commit's tree,
  - the build-dir digest equals `EMPTY_TREE_SHA256` (already defined).
- Serialize candidates with a lock, because a reused tree cannot host two candidates.

**Recommendation:** prefer §4.3 plus §4.1 (sparse per-candidate trees that are reaped). A reused
tree trades a disk problem for a correctness problem that is harder to see. Use a reused tree
only for *lint-class* checks.

### 4.5 Retention policy by verdict

| Verdict / artifact | Keep | Expire (E-class) |
|---|---|---|
| Promoted or champion | everything; the incumbent archive is permanent (§3.3) | none |
| Rejected candidate | patch bundle, source-tree hash, binary and linkage SHA-256, reduced metrics, receipts (carried in git) | build tree and binaries (E1) after the terminal disposition is recorded |
| Retired campaign worktree | evidence dir verified against `SHA256SUMS`, all commits on a remote ref | the worktree (E2) |
| Profiler traces | reduction plus collection recipe in the tombstone | raw trace (E3) after supersede or re-confirm. `cpu-profiles` (25.5 G) is the largest single E3 candidate on disk. |
| Acceptance check | the verdict row plus the pushed `accept/<packet>` branch | the tree, immediately (it is E2-shaped once pushed) |
| Serial state dir, superseded version (vN when vN+k is live) | `serial-state.json`, journal, receipts, batch verdicts | `targets/*/workers`, `targets/*/builds` (E1) |

**Quality risk.** Expiring something a later audit needs, such as a replay of a rejected
candidate.

**Mitigation.**
- The retained patch, tree hash and recipe make every E1 artifact **re-derivable**. That is the
  §3.4 derivation-closure conjunct.
- A tombstone records exactly how to rebuild it.
- Nothing without a closure expires.

### 4.6 Evidence compression and archival

**Mechanism.**
- **For each** retired run dir, `tar --zstd` the evidence subset (json, jsonl, md, logs, receipts,
  `SHA256SUMS`) into `/mnt/raid0/llm/archives/autokernel/<campaign>/<run>.tar.zst`.
- **Verify before touching the source:** list the archive, re-hash it against the in-archive
  `SHA256SUMS`, and fsync it.
- **Only then** expire the non-evidence bulk under §4.5.
- **Expected ratio:** JSON and JSONL evidence typically compresses 8–15×, while build trees and
  SQLite are excluded.

**Quality risk.**
- A citation pointing at a path that is now inside an archive.
- A corrupt archive.

**Mitigation.**
- Use the ratified tombstone grammar `attest <locator> [durability=hash-and-provenance-only,
  sha256=…, tombstone=<event_id>]`, extended with `archive=<path>#<member>`, so citations resolve
  and `cite-check` can follow them.
- Archive integrity is verified at write time and re-verified by a monthly scrub.
- `experiments.db` is never archived while the store is live (WAL), and is snapshotted with
  `sqlite3 .backup` instead.

### 4.7 Disk-budget admission gate in preflight (three-state)

**Mechanism.** Replace the literal 200 GiB `live_controls.py:724` check with `disk_admission()`,
called at **lane open, window open, and window close** (P-AK-SEARCH-1 precondition 7), plus
before `pool.provision`, `source_loo` and every `serial_run` batch:

- **Floor:** read `statvfs` on each namespace root. Record the mount identity (`st_dev` plus
  mountinfo source) and refuse if a root resolves to an overlay while the declared device is
  `md127`.
- **Required:** `storage_floor_bytes_free = max(largest_contracted_artifact,
  high_water_iteration_footprint × storage_safety_factor, host_reserve_bytes)`. The high-water
  figure is *measured*: `serial_run` already has per-batch dirs to measure.
- **Result:**
  - `ADMIT` when free minus the reservation of lanes about to open is at least the floor.
  - `REFUSE` when it is below.
  - `UNKNOWN` on a statvfs error, a mount-identity mismatch, or an unset `host_reserve_bytes`.
  - **`UNKNOWN` is REFUSE**, and it enters the ratified `DISK_PRESSURE` state: quiesce at a
    boundary, persist, journal, and raise a decision package.

**Quality risk.** None to measurement quality. The risk is availability: false refusals stall the
loop. A second-order risk is that under pressure the loop "helps itself" to deletions.

**Mitigation.**
- Pressure orders already-eligible expiries and never creates eligibility (§3.6).
- `DISK_PRESSURE` is a stop state with an operator package, not a reclamation trigger.
- Reservation accounting (per-lane expected footprint) prevents eight lanes from each passing a
  gate that only one of them fits under.

### 4.8 Size-attribution dashboard and alarm, following the hub plane rule

Per `dashboard/README.md`, the data contract lives with the subsystem and the page lives on the
hub.

- **Data plane (research repo):** a loop-owned exporter writes `disk_attribution.v1` JSON at
  each iteration boundary:
  - bytes per namespace root and per class (acceptance, lane, build, store, evidence, E1/E2/E3
    backlog),
  - creator/owner from the worktree ledger (§4.1),
  - `free_bytes`, `mount_id`, `floor_bytes`, and `freshness: {source_ts, attempt_ts,
    heartbeat_ts}`.
  - `loop.process_metrics` already records store `size_bytes`
    (`artifacts/autokernel/s3-aku-10-process-metrics-20260915.json:19`). Extend that rather than
    starting a second producer.
- **View plane (root hub `:8100`):**
  - a panel on the existing `/loop` page, not a new page, so no new registry entry is needed;
  - one `dashboard/panels.py` fold entry, so `/api/health` goes `stale` when the exporter stops;
  - if it grows into a page: a registry entry, a health probe **and** a freshness envelope.
- **Alarm:** `scripts/coordination/alarm_channel.py:597` `raise_alarm("autokernel-disk-floor",
  "high", …, evidence={free, floor, top_owners})` on the transition into `DISK_PRESSURE` or on
  free space under floor + 1 day of measured growth. `clear_alarm` fires on recovery. The alarm
  notifies only on the inactive-to-active transition, so it cannot spam.

**Quality risk.** None directly. The indirect risk is a stale panel showing "fine".
**Mitigation:** the three-valued `/api/health` fold, never `/health`.

---

## 5. Ranking: GB saved against quality risk

| Rank | Option | GB saved (backlog / ongoing) | Quality risk | Verdict |
|---|---|---|---|---|
| 1 | §4.1 owner-bound reaper plus commit-or-discard acceptance | ~370 GB backlog class; ~2 GB per future check | low | **do first**; it is also what makes the backlog removable |
| 2 | §4.3 sparse acceptance trees (Python repos) | ~1.6 GB per check (≈ −90 %) | low-medium (skip-count guard) | **do** |
| 3 | §4.5 plus §2.3: expire superseded state-dir lanes and builds (E1) | ~45 GB backlog; ~2 GB per state-dir version | medium → low with closure | **do** after the ledger exists |
| 4 | §4.6 evidence archival plus E3 trace expiry (`cpu-profiles`) | ~25 GB (one store) | low with tombstones | **do** |
| 5 | §4.7 admission gate plus §4.8 alarm | 0 reclaimed; prevents the 96 % burst | none (availability only) | **do**, cheap |
| 6 | §4.4 single reused acceptance tree | ~370 GB class | medium-high (state leak) | lint-class only |
| 7 | §4.2 shared ccache | small | high (stale objects, INF-70 C9 class) | **do not** for disk |

---

## 6. The sweep tool (dry-run companion)

`scripts/system/autokernel_disk_sweep.py` classifies the existing backlog with checks (a)–(e):

- **(a)** clean,
- **(b)** HEAD and name-matched local branches contained in a remote-tracking ref,
- **(c)** no live process cwd, exe, fd, mmap or argv inside the tree,
- **(d)** not referenced by loop code/config/state, an active handoff, or a retention note,
- **(e)** not a roster lane.

On top of those it applies **KEEP-active-session**:
- the Codex session's process-tree cwds, fds and argv,
- the `inference` heartbeat task lane and its claims,
- the task id in branch or dir names,
- a `--recency-hours` guard (default 24) over max(mtime, ctime) of every entry.

Its process probe is three-state. `--apply`:
- requires the reviewed manifest's SHA-256, an interactive operator confirmation, and a COMPLETE
  probe (run as host root, because the container cannot read the cwd of other uids' processes),
- re-runs every check per row immediately before acting,
- removes worktrees only with `git -C <repo> worktree remove <path>`.

It never runs prune, gc or `--force`, and it never signals a process.

**Scan and apply must run in the same context.** `--apply` re-uses the manifest's paths, and the
container's `/workspace` is `/mnt/raid0/llm/epyc-root` on the host. The in-container dry-run was
necessarily PARTIAL (268 unreadable processes, uids 0 and 1001 among them). The reviewable
manifest for an apply is therefore a fresh dry-run **on the host as root**, followed by the
operator's review and confirmation.

The additional guards added after the first real dry-run are covered by unit tests:
- local-path remotes do not count as "pushed";
- sibling dirs in a held store's name family, and paths named in a held candidate's small state
  files, are KEEP-referenced;
- the evidence patterns were narrowed after node_modules icons and SEAL-paper copies matched. **Per the operator rule it
is run with `--apply` only after the operator reviews the manifest and confirms, at a boundary the
AutoKernel owner chooses.**

### 6.1 Archived KEEP-dirty retirement

`scripts/system/autokernel_dirty_retire.py` is the separate, fail-closed bridge between a durable
archive from `autokernel_dirty_preserve.py` and removal of one reviewed `KEEP-dirty` worktree. It
does not make an ordinary dirty tree eligible: every selected `--record` must bind the exact
reviewed sweep-manifest SHA, row, source path, HEAD, source fingerprint and content-addressed
archive. If HEAD was unpushed, the archive's standalone bundle is verified and must advertise
that exact HEAD.

The default is a read-only dry-run:

```bash
python3 scripts/system/autokernel_dirty_retire.py \
  --manifest <reviewed-sweep.json> --manifest-sha <exact-sha256> \
  --record <archive-root>/records/<source-key>/<archive-sha>.json
```

Apply requires a COMPLETE host process probe, no live holder, a target strictly below one of the
three worktree roots, and the operator typing the reviewed SHA prefix on a TTY. It then writes a
durable per-row authorization receipt, resets tracked state to the archived HEAD, unlinks only
the exact nonignored untracked paths enumerated by Git and covered by the archive, then handles
generated ignored residue through a second explicit discard stage. Every ignored path must be
enumerated by both `git ls-files --others --ignored --exclude-standard` and `git check-ignore`;
the receipt inventories its path, type, byte count, mode and hash before mutation. Nested Git
metadata, `.git` crossings, special files, escaping symlinks, and durable-evidence names refuse
the row. Evidence-name matching follows the sweep's `EVIDENCE_SKIP_DIRS`: generated names below
canonical caches such as `__pycache__`, `.pytest_cache`, `.ruff_cache`, `CMakeFiles`, and
`.mypy_cache` remain generated residue rather than false evidence. After the inventory is durably
authorized, only those exact entries are unlinked. The
helper then proves the tree completely clean and runs exactly
`git -C <owning-repo> worktree remove <exact-path>`. There is no prune, gc, force flag, wildcard,
or name discovery. Authorization checkpoints make reset, untracked removal and worktree removal
resumable after interruption without weakening any fresh probe, identity or content check.

**Known limits:**
- References are matched as `parent/basename` pairs or as distinctive basenames. A glob-shaped
  citation such as `tmp/aku-checkpoint.*` is not matched.
- The evidence heuristic is name-based (`VERDICT*.json`, `*receipt*.json[l]`, `*sealed*`,
  `SHA256SUMS`, attestation, ratification).
- `dirty_landed` is an annotation, never a verdict change.
