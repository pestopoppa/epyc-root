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
- [ ] M-10 — **Reseed** (`reseed_episodic_store.py`). Relayed to Codex 2026-07-27. Needs inference
      (~58,132 BGE embeddings) and a window with no pinned CPU bench running.
  - [ ] M-10a — Acceptance is the **cosine test**, not the exit code: re-embed a row's own text and
        compare to its stored vector. Before: **mean 0.5505, 0/12 above 0.9**. Pass: **> 0.95**.
- [ ] M-11 — Wire SkillBank retrieval. All 57 skills have `embedding_idx` NULL and
      `retrieval_count = 0`, so it cannot be retrieved even in principle.
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
