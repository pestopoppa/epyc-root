# Episodic Memory Integrity — 2026-07-05 corruption, root cause and repair

**Status**: active — write path FIXED and proven self-healing in production; data repair DONE;
reseed STAGED and relayed to Codex 2026-07-27
**Created**: 2026-07-27
**Priority**: HIGH — this subsystem underpins routing, MemRL and SkillBank
**Categories**: agent_architecture, memory_augmented, routing_intelligence
**Parent index**: [research-evaluation-index.md](research-evaluation-index.md)
**Related**: [learned-routing-controller.md](learned-routing-controller.md) (EPD-1/2/3 label defects),
[standardized-stack-update-pipeline-finalization.md](standardized-stack-update-pipeline-finalization.md)
(SS-BENCH-GATE)

## Objective

The episodic store's vector resolution was silently corrupt from **2026-07-05T15:01:12**. Find the
root cause, repair the data, make the failure mode self-correcting, and put every write site on one
record contract so it cannot recur.

## Root cause — one bug, three symptoms

`faiss_store.save()` published `embeddings.faiss` and `id_map.npy` with **two separate renames**. Two
files cannot be renamed atomically as a pair on POSIX, so a crash between them always leaves a
mismatch — but the two directions are not equally bad, and the old code chose the unrecoverable one:

| direction | consequence |
|---|---|
| **index published first** (old) | index ends up AHEAD of id_map. Trailing vectors have no id. `_load()`'s "truncate id_map to match index" is a **silent no-op** in this direction. `add()` then returned `idx = index.ntotal` while appending the id at `len(id_map)`, so every later write inherited the offset and persisted it into `memories.embedding_idx`. **Permanent and cumulative**, +1 per interrupted publish. |
| **id_map published first** (fixed) | id_map ends up ahead. Trailing ids simply have no vector; `_load()` drops them. **Self-healing.** |

`episodic_store.py:373-381` does `_load()` → `add()` → full `save()` **per memory**, so one
interrupted publish costs exactly one id. The live store reached a drift of 42.

**19.7 GB of orphaned `.tmp` artifacts** were the fossil record — including a 0-byte
`.id_map.npy.<token>.tmp.npy` paired with a 2.79 GB `.embeddings.faiss.<token>.tmp`, i.e. the exact
failure caught in amber.

## Tasks

- [x] M-1 — Reverse the publish order; fsync each temp before its rename. ✅ 2026-07-27
      (`fe7d4498`)
- [x] M-2 — `add()` derives position from `len(id_map)`; raises `FAISSDesyncError` rather than
      writing into a desynced store. ✅ 2026-07-27
- [x] M-3 — `_load()` distinguishes the two mismatch directions instead of pretending a no-op slice
      repaired it. ✅ 2026-07-27
- [x] M-4 — `repair_faiss_id_map.py`: exact repair via id_map reverse lookup. **desync 41 → 0,
      57,721 rows fixed, 0 failures.** ✅ 2026-07-27
- [x] M-5 — Reclaim the orphaned `.tmp` artifacts (18 GB). ✅ 2026-07-27
- [x] M-6 — Seed `update_count` at INSERT + `COALESCE` in the UPDATE. ✅ 2026-07-27 (`2aef564d`)
- [x] M-7 — `memory_record.py`: one record contract. ✅ 2026-07-27
- [x] M-8 — Migrate all 5 real write sites; add a chokepoint guard in `store()`. ✅ 2026-07-27
      (`eaea2317`)
- [x] M-9 — Deploy: API reloaded to the fixed code and **verified self-healing live** — a `-2`
      desync appeared after reload and `_load()` reconciled it to 0 automatically. ✅ 2026-07-27
  - [x] M-9a — **Fix holds under production write load.** ✅ 2026-07-27. 291 memories written since
        the reload with `desync = 0` throughout (ntotal 707,276 → 707,561), **0/291 with a NULL
        `update_count`** (the pre-fix population was 22,949 of 54,960) and **0/291 with a NULL
        `embedding_idx`**. The desync fix is confirmed under live writes, not just at reload.
- [ ] M-10 — **Reseed** (`reseed_episodic_store.py`). Relayed to Codex 2026-07-27; script HARDENED
      by Codex and reviewed+approved 2026-07-27 (`517a8c38`, `7b2e58a9`); execution handed back.
      Needs inference (~58,132 BGE embeddings) and a window with no pinned CPU bench running.
  - [x] M-10b — **Review of Codex's hardening: APPROVED, and it caught two real bugs of mine.**
        ✅ 2026-07-27. 82 tests pass across reseed/memory_record/faiss/parallel_embedder.
        **(i) My reseed could have silently produced a corrupt store.** It built its embedder with
        bare `TaskEmbedder()`, and `EmbeddingConfig.use_fallback` defaults to **True** — the fallback
        being a SHA-256-seeded PCG64 pseudo-embedding. A BGE hiccup mid-reseed would have written
        hash noise, passed the `id_map[embedding_idx] == id` check, and **exited 0 on a corrupt
        store** — the same "internally consistent while silently wrong" shape as the original bug.
        Codex gates it three ways: `use_fallback=False`, the new `allow_subprocess=False` (needed
        because `use_fallback` alone left the subprocess path open), and an explicit
        `ParallelEmbedderClient(EmbedderPoolConfig(use_fallback=False))` override; the terminal
        branch now raises instead of substituting.
        **(ii) `record_from_legacy_context` corrupted contract round-trips.** Mine swept every
        unrecognised key into `metrics`, so re-reading a contract-written record nested `metrics`
        inside `metrics` and filed `record_version` as telemetry — compounding on every reseed pass.
        Fixed in `7b2e58a9`; my round-trip test was strengthened to full `to_context()` equality,
        which is what exposed it.
        Also added: `verify_episodic_reseed_cosine.py` implementing the acceptance gate
        (`return 0 if len(sample) == args.sample_size and mean > 0.95 else 1` — full sample AND
        mean >0.95, so a short sample cannot pass), and `_checked_batch()` validating shape
        `(n, 1024)` and `np.isfinite` per batch.
  - [~] M-10c — **RESEED IN FLIGHT.** Codex started it 2026-07-27T22:07:15Z
        (`reseed_episodic_store_20260727T220715Z`). Backups complete
        (`*.pre-reseed-20260727T220715Z` for `embeddings.faiss` / `id_map.npy` / `episodic.db`);
        marker at `state: backups_complete`. **Do not touch the store while it holds the writer
        lock** — no reads of `embeddings.faiss`/`id_map.npy`, and do not run the cosine verifier
        until it exits.
        **NOTE**: the SS-BENCH-GATE guard added to `orchestrator_stack.py` does NOT cover this
        script — it is not a stack lifecycle action — so the "no pinned CPU bench" precondition
        remains a manual check.
  - [ ] M-10d — **Result lands automatically at `/mnt/raid0/llm/tmp/reseed_acceptance.log`** — a
        detached watcher (armed 2026-07-27T22:36Z) waits for the reseed PID, then runs the marker
        dump, the cosine verifier and a final desync check into that file. Read it first next
        session. Manually, run
        `verify_episodic_reseed_cosine.py --sample-size 12` and record the numbers here. It exits 0
        only on a full sample AND mean > 0.95. Pre-reseed baseline: **mean 0.5505, 0/12 above 0.9**.
        If it fails, roll back from `*.pre-reseed-20260727T220715Z` — do not iterate on the live
        store.
  - [ ] M-10a — Acceptance is the **cosine test**, not the exit code: re-embed a row's own text and
        compare to its stored vector. Before: **mean 0.5505, 0/12 above 0.9**. Pass: **> 0.95**.
- [x] M-11 — **SkillBank is retrievable.** ✅ 2026-07-27. The consumer was never missing:
      `state.hybrid_router` is replaced by `SkillAugmentedRouter` (`services/memrl.py:481`) whenever
      the `skillbank` flag is on, and it is. Only the search key was absent —
      `SkillBank.store(skill, embedding=None)` takes the embedding as OPTIONAL and only assigns
      `embedding_idx` when supplied, and the distillation pipeline never supplied one, so no
      `skill_embeddings.faiss` existed at all. `backfill_skill_embeddings.py` embedded all 57 by WHEN
      THEY APPLY (title + when_to_apply + task_types — skills are matched against the incoming TASK
      embedding, so they must live in task space). **Verified**: a USACO task retrieves "Route USACO
      and competitive programming to architect_general" (0.770); a chemistry task retrieves "Route
      chemistry problems to frontdoor" (0.630). Index 57/57.
  - [x] M-11b — **Stale skills PURGED, not migrated.** ✅ 2026-07-27. Backfilling them was the wrong
        call: all 57 were distilled from the corrupt corpus (mis-assigned vectors, cost-contaminated
        labels), their `source_trajectory_ids` match 0 current rows, and **5 route to
        `architect_coding` — a role that does not exist in the live registry** (verified against
        `model_registry.yaml`). Making them retrievable put stale advice, including a dead role, into
        live routing prompts. Purged: 57 → 0, `skill_embeddings.faiss` / `skill_id_map.npy` retired,
        `skills.db` backed up to `skills.db.pre-purge-*`. Verified: bank count 0, retrieval returns
        0, so nothing stale can reach a prompt. The retrieval path itself remains wired and working —
        it just has nothing to serve until re-distillation.
  - [ ] M-11a — Re-distil skills after the reseed. The 57 existing skills reference
        `source_trajectory_ids` matching 0 current rows, and were distilled from 200-char stubs — all
        57 are thin routing heuristics because that is the ceiling of the input. Re-distilling over
        real trajectories is what makes SkillBank worth its retrieval slot.
- [x] M-13 — **A failed index load no longer destroys the store.** ✅ 2026-07-27. `_load()` swallowed
      ANY read failure and called `_create_new()`, replacing a 700k-vector store with an empty index
      that the next `save()` would publish over the real files. Same class of defect as the
      publish-order bug. Now re-raises when files exist; creates fresh only when there is nothing to
      load. 2 regression tests.
- [x] M-14 — **SS-BENCH-GATE-a landed** (in `standardized-stack-update-pipeline-finalization.md`).
      ✅ 2026-07-27. `orchestrator_stack.py` start/stop/reload now refuse while a CPU bench driver is
      running, overridable with `--allow-during-bench`. Verified live — it caught the E8 quality
      baseline reseed and the v7 quality gate on first run.
- [ ] M-15 — **Reopen intake-866 / COMP_r.** Its 2026-07-22 null (pooled AUC 0.4933) was computed
      through `memories.embedding_idx`, i.e. the broken mapping. Adversarial re-analysis with the
      correct id_map resolution moves it to **0.5570**, which no longer clears the probe's own
      close-out gate of <=0.55; its in-sample leakage anchor read 0.6427 where the report documented
      "expected ~1.0", recovering to 0.9101 under the correct mapping. The line was closed on bad
      evidence. Re-run after the reseed.
- [ ] M-16 — **Verify the record contract is actually exercised in production.** Deployed but
      unexercised as of 2026-07-27 22:0x: the API restarted 21:53:16 on code containing `eaea2317`
      (21:40:06), and exactly **1** row has been written since — at 21:53:03, i.e. 13 s BEFORE that
      process started, so it is the old process's last write. Nothing has yet gone through the new
      path. Check once traffic flows: new rows must carry `record_version`, an untruncated
      `objective`, and telemetry under `metrics`. The chokepoint guard in `store()` logs a warning
      for any non-contract write, so a silent regression is visible in the API log.
- [ ] M-12 — Run the memory-on vs memory-off A/B that **has never existed** in either repo. This is
      the only thing that will answer "does episodic retrieval help" with evidence.

## Why the reseed is necessary (and what it will NOT fix)

M-4 repaired `memories.embedding_idx → id_map` exactly. But `id_map position → vector` is *also*
misaligned by a region-dependent offset, which pointer arithmetic cannot fix. Measured: re-embedding
a row's own text and cosining against its stored vector gives **mean 0.5505** — random-pair
territory. The vectors do not belong to their rows.

**The reseed produces a correct index of 200-char stubs.** 40,982 objectives were truncated *at write
time*, so that text is gone; answers/tool-calls/REPL-steps/reasoning were never written at all.
Trajectories arrive only from **new** writes through the fixed path, which is already live. Do not
expect the reseed to deliver the trajectory store — it delivers the clean baseline underneath it.

Also expected: the index shrinks ~707,276 → ~58,132 vectors, because it currently spans
`memories_appendonly_legacy` (680,922 archive rows). No code reads that table (verified).

## The store carries real signal — this is worth fixing

On a held-out temporal split (train pre-2026-06-06, test after), picking the highest-q action per
suite gives macro test failure **0.1964** vs **0.2518** random and **0.1790** oracle — **76% of
achievable headroom, permutation p = 0.0025**. It survived adversarial attack as a writer-path
artifact (partial corr unchanged at −0.875) and as a popularity artifact (frequency-greedy 0.2211 ≈
random). Measured *within* suite across actions, so it is not suite identity.

## Corrections to earlier claims in this investigation

Recorded because three findings were reported before being verified, and two share a mechanism.

1. **"52% of vectors are degenerate"** — wrong diagnosis at first. They were mis-*resolved*, not
   mis-*computed*. But note M-10's finding: the vectors genuinely do not match their rows either, for
   a different reason (id_map→vector offset). Both mattered; the first framing did not.
2. **"The BGE server is non-deterministic under concurrency"** — FALSE. 16 concurrent embeddings of
   one text agree at pairwise cosine **1.0000**. The artifact came from hashing float32 bytes;
   sub-ULP jitter breaks a hash but not a cosine. **Compare embeddings with cosine, never a hash.**
3. **"27,123 of 54,960 rows are telemetry with no task text"** — FALSE. Measured properly:
   `objective` only 30,571; `task_description` only 27,562; both 0; **neither 0**. Both writer paths
   carry real task text — only the KEY NAME differs. The classification checked one key. The external
   path also embedded the text, not the telemetry.
4. **"EPD-2: cost penalties are a dominant label defect"** — overstated. It explains ~4.3% of live
   failure labels. And the related `reward == 0.0 → failure` is **correct behaviour**:
   `success_reward(passed) = 1.0 if passed else 0.0`, with genuine no-signal cases dropped earlier as
   `INFRA_SKIP`.

Common cause of 2 and 3: **asserting a negative without checking the alternative encoding.**

## Key files

| file | role |
|---|---|
| `orchestration/repl_memory/faiss_store.py` | publish order, `add()` position, `_load()` reconciliation, `FAISSDesyncError` |
| `orchestration/repl_memory/memory_record.py` | the record contract |
| `orchestration/repl_memory/episodic_store.py` | `update_count` seed, chokepoint guard |
| `scripts/maintenance/repair_faiss_id_map.py` | exact pointer repair (done) |
| `scripts/maintenance/reseed_episodic_store.py` | staged reseed |
| `tests/unit/test_faiss_store.py` | `TestDesyncCorruptionRegression` (5 cases) |
| `tests/unit/test_memory_record.py` | contract (16 cases) |

## Reporting

Update M-10/M-10a with the Codex reseed result including the **cosine acceptance numbers**. If
acceptance fails, roll back from `*.pre-reseed-*` and record why — do not iterate on the live store.
