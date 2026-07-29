# Episodic Memory Integrity — 2026-07-05 corruption, root cause and repair

**Status**: active — **CLEARED FOR SEEDING (M-18 full-surface audit, 2026-07-28; semantic gate
verified live 2026-07-29).** Write path FIXED and proven self-healing in production; reseed DONE;
standing integrity gate (M-17) blocks AutoPilot on a broken store and runs in `health_check.sh`.
The degenerate-vector guarantee extends to **every** store via `FAISSEmbeddingStore.add()`
(episodic, SkillBank, StrategyStore — commit `82fbf276`). Live state 2026-07-29: episodic
`ntotal=58749 desync=0`, round-trip 500/500, degenerate 0/500, **semantic self-match mean
cosine 0.9824 over 8 samples** (0.5505 during the incident); strategy store 1424/1424/1424
coherent, 0 degenerate; skills a clean post-purge slate. Remaining items are follow-on analysis
(M-15), the re-distil (M-11a, inference-gated), and the never-run A/B (M-12).
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
- [x] M-10 — **Reseed** (`reseed_episodic_store.py`). ✅ 2026-07-28. Codex ran the hardened
      terminal path at receipt stamp `20260727T220715Z`: **58,281** task memories re-embedded,
      0 telemetry exclusions, index/id_map `58,281/58,281`, `desync=0`, and 0 broken
      `embedding_idx` self-resolutions. Durable survey and apply logs:
      `artifacts/episodic-memory-reseed-20260727/`. The subsequent API-only reload succeeded and
      restored health to `6/6`; no full-stack restart or production-lineup change occurred.
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
  - [x] M-10c — **RESEED EXECUTED.** ✅ 2026-07-28. Started 2026-07-27T22:07:15Z
        (`reseed_episodic_store_20260727T220715Z`) after its three same-stamp backups completed;
        it exited after publishing the repaired live index and database.
  - [x] M-10d — **Acceptance captured.** ✅ 2026-07-28. The full 12-row cosine verifier produced
        mean **1.0000000496705372**, **12/12 above 0.9**, `ntotal=58,281`, `id_map_len=58,281`,
        `desync=0`, and `bad=0`; see
        `artifacts/episodic-memory-reseed-20260727/cosine-acceptance.log`.
  - [x] M-10a — Acceptance is the **cosine test**, not the exit code. ✅ 2026-07-28. The pre-reseed
        baseline was mean **0.5505**, 0/12 above 0.9; the required full sample now exceeds the
        `>0.95` gate at **1.0000000496705372**. No rollback was required.
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
  - [x] M-11a-wiring — **The `distill_skillbank` autopilot surface is REPAIRED** ✅ 2026-07-28
        (`47a3eecf`). It was a designed-in action (`actions.py:1848`, pre-distillation checkpoint
        and all) that had returned `{"status": "error"}` on every invocation ever made — wrong
        constructor kwargs plus a sync call of the async `run()`. Now mirrors `seed_skills.py`:
        teacher resolution (claude|codex|local|mock), high-Q trajectory extraction reading the
        contract `objective` key (seed_skills read only legacy `task_description` — fixed there
        too), `asyncio.run`, guarded embedder, and `faiss_path` paired with a custom `db_path`
        (my own smoke test caught the unpaired version writing vectors into the live sessions
        dir). Smoke-tested end-to-end with MockTeacher, zero inference: distill → dedup → store →
        FAISS-indexed, no live-tree side effects.
  - [ ] M-11a — **First re-distil (INFERENCE — the teacher LLM writes the skills). DO NOT run
        early; DO NOT forget to run it when ready.** Operator-directed sequence (2026-07-28):

        **seed / run live traffic first → let real trajectories accumulate → then let autopilot
        propose `distill_skillbank`** (or trigger it via `seed_skills.py --teacher claude`).

        Teacher policy is RESOLVED — operator ruling 2026-07-28: Claude CLI is the autonomous
        default, wired for a one-env-line shift when the operator decides
        (`AUTOPILOT_DISTILL_TEACHER=local` on the supervisor; `AUTOPILOT_DISTILL_LOCAL_URL`
        defaults to the frontdoor, `..._LOCAL_MODEL` for provenance; explicit action `teacher`
        still wins).

        **Readiness probe** (run this; do not guess):
        ```bash
        sqlite3 "file:orchestration/repl_memory/sessions/episodic.db?mode=ro" \
          "SELECT COUNT(*) FROM memories WHERE created_at > '2026-07-27T22:07' \
           AND outcome IN ('success','failure')"
        ```
        Baseline at filing (2026-07-28T13:4x): **374**. The distillation pipeline consumes
        `objective`/`routing_decision`/`outcome` per trajectory, so readiness = enough FRESH
        post-reseed rows with real outcomes and untruncated objectives — suggest **≥2,000** (≈10
        batches at the default 20/batch over a meaningfully diverse pool) before the first run.
        The pre-distillation checkpoint in `_action_distill_skillbank` protects rollback either way.
  - [ ] M-11a2 — **`work`-payload capture is NOT wired** (measured 2026-07-28: **0 of 58,655** rows
        carry `work`). The live write sites (`q_scorer.py:1194,1291,1402`) pass only
        objective/metrics — nothing passes `answer`/`tool_calls`/`repl_steps`/`reasoning`, so the
        contract's work-storage capability sits unused and future distillation stays
        objective+outcome-only. Wiring capture is zero-inference but design-adjacent (what to
        capture, size policy) — coordinate with
        [repl-session-memory-maturity.md](repl-session-memory-maturity.md), which owns trajectory
        richness. Until this lands, do not expect distilled skills to encode HOW a task was solved,
        only WHICH routing outcomes succeeded.

        Historical context — the reseeded store holds 200-char
        objective stubs; rich trajectories arrive only from new live-traffic/autopilot writes, so
        the first re-distil is best run after real traffic accumulates. The 57 previous skills reference
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
- [x] M-16 — **Record contract IS exercised in production.** ✅ 2026-07-28. Verified once traffic
      flowed: the last 40 rows are **40/40 on contract**, newest `2026-07-28T06:25:53`, keys
      `['objective', 'priority', 'record_version', 'source', 'task_type']`. The chokepoint guard in
      `store()` logged no non-contract warnings.
- [x] M-17 — **Standing integrity assertion, so the store cannot rot unobserved again.**
      ✅ 2026-07-28. This is the item that closes the incident's *real* defect: the store was wrong
      for 22 days and nothing noticed, because nothing looked. Every component was internally
      consistent the whole time.

      `scripts/maintenance/check_episodic_integrity.py` asserts the four properties that were
      actually violated — index/id_map sync, `embedding_idx` round-trip, vector diversity, and
      (decisively) **semantic self-match**: re-embed a row's own objective and cosine it against its
      stored vector. No amount of internal consistency can fake that one.

      **Validated against deliberately-broken stores, not just the happy path** — a monitor that only
      ever passes is indistinguishable from no monitor:

      | injected defect | check that fired | measured |
      |---|---|---|
      | index-ahead desync | `index_id_map_sync` | desync=5, exit 1 |
      | mis-resolving mapping (the incident) | `embedding_idx_roundtrip` + `semantic_self_match` | 0/200 resolve; **cosine 0.4372** |
      | vector collapse | `vector_diversity` | 1 vector / 200 objectives |

      The 0.4372 sits right next to the **0.5505** measured during the live incident — the check
      reproduces the incident signature, which is the evidence that it would have fired on day one.
  - [x] M-17a — Wired into `scripts/session/health_check.sh` §6 (metadata-only, **0.23 s**, no
        inference, no BGE dependency). ✅ 2026-07-28
  - [x] M-17b — Wired into AutoPilot as a **fail-closed startup gate**
        (`_enforce_episodic_integrity_gate`, called from `cmd_start`), running the decisive
        `--semantic` check. A broken store now blocks the run with exit 2 rather than degrading it,
        because a trial on a broken store produces evidence that *looks valid* — which is precisely
        what the last 22 days of trials were. Documented override:
        `AUTOPILOT_SKIP_EPISODIC_GATE=1`, logged loudly. ✅ 2026-07-28
  - [x] M-17c — 9 regression tests (`tests/unit/test_episodic_integrity_check.py`), one per injected
        defect plus the skip path. Full episodic suite **157 passed**. ✅ 2026-07-28
  - [x] M-17d — **A bug in my own check, caught and pinned.** The first version divided distinct
        vectors by *row count* and reported the healthy store as collapsing (ratio 0.114). Benchmark
        traffic legitimately replays the same objectives — 500 recent rows carry only **57 distinct
        objectives** — and identical text *should* share a vector. Correct denominator is distinct
        objectives; the store reads **57/57, ratio 1.000**. Pinned by
        `TestDiversityDenominator`. ✅ 2026-07-28
  - [x] M-17e — **Embedder-outage hole CLOSED — and it was much worse than "gated on metadata
        only".** ✅ 2026-07-28. Investigating the skip turned up a live, unfixed corruption path.

        **`use_fallback` defaults to `True`** in both `EmbeddingConfig` (`embedder.py:48`) and
        `EmbedderPoolConfig` (`parallel_embedder.py:53`), and **every live site builds a bare
        `TaskEmbedder()`** — `memrl.py:388`, `routing.py:162`, `strategy_store.py:308`,
        `seed_loader.py:412`, `classification_retriever.py:306`, `procedure_registry.py:135`,
        `tools/llm.py:22,33`. The only site that sets `use_fallback=False` is the reseed script
        Codex hardened. So a BGE outage does **not** fail a write — it silently stores a SHA-256
        pseudo-vector.

        **Measured over 5,000 real task texts, the fallback is numerically broken, not merely
        "semantically meaningless" as its docstring claims:**

        | outcome | share | consequence |
        |---|---|---|
        | **all-zero** | **89.0%** | float32 `norm` overflows to `inf`; `norm > 0` is True for inf; `v/inf == 0` |
        | contains NaN | 2.8% | permanently unretrievable — FAISS scores the row `-inf` |
        | unit-normalised | 8.1% | well-formed, semantically meaningless, passes every cheap check |

        **The blind spot was exact**: the well-formed 8.1% pass index/id_map sync and the
        `embedding_idx` round-trip, so the *only* detector was `semantic_self_match` — which
        requires the very embedders whose absence produced them. **The condition that causes the
        corruption is the condition that disables its detector.**

        Audited the live store for this: **0 hash-fallback vectors across all 58,322 rows.** Clean,
        because the reseed used `use_fallback=False` and BGE has been up.
  - [x] M-17f — **Chokepoint refusal.** `EpisodicStore.store()` now raises
        `DegenerateEmbeddingError` on all-zero, non-finite, or exact-hash-fallback embeddings.
        Placed at the single chokepoint (`store_immediate` delegates to it) rather than at the ~8
        constructor sites, so a new caller cannot lose the guarantee. Detection is **exact**, not
        heuristic — the fallback is a pure function of the text. Override:
        `EPISODIC_ALLOW_DEGRADED_EMBEDDINGS=1`, logged at ERROR. ✅ 2026-07-28
  - [x] M-17g — **`degenerate_vectors` check, which needs no embedder.** This is what actually
        closes the blind spot at the detection layer: all-zero and NaN are text-independent, so
        91.8% of fallback corruption is now detectable *in exactly the condition that causes it*.
        ✅ 2026-07-28
  - [x] M-17h — **AutoPilot gate: retry then fail closed.** Waits out an embedder boot window
        (`AUTOPILOT_EPISODIC_GATE_WAIT_S`, default 180 s, polling every 15 s) and then **refuses**.
        Justified rather than merely strict: with BGE down the write path now raises anyway, so
        AutoPilot could not record memories. Structural failures skip the window and block in
        **0.3 s**; healthy startup costs **0.9 s**. ✅ 2026-07-28
  - [x] M-18 — **Pre-seeding audit of the ENTIRE memory surface (operator-requested re-audit).**
        ✅ 2026-07-28, commit `82fbf276`. Findings and dispositions:

        | # | Finding | Disposition |
        |---|---------|-------------|
        | 1 | The chokepoint guard did NOT cover SkillBank or StrategyStore — both persist FAISS vectors without touching `EpisodicStore.store()`; strategy's `_embed()` docstring *advertised* "hash-based fallback if no model available" | **FIXED** — `DegenerateVectorError` in `FAISSEmbeddingStore.add()`, the single function every vector passes to reach ANY index |
        | 2 | `StrategyStore._hash_embed` emits well-formed RandomState vectors — undetectable after the fact | **FIXED** — `_embed()` fails closed on both fallback branches at the source |
        | 3 | `DistillationPipeline._embed_skill` called `self.embedder.embed()` — a method TaskEmbedder does not have; the AttributeError was swallowed, so with a real embedder every distilled skill silently landed UNINDEXED | **FIXED** — `embed_text` + fallback refusal |
        | 4 | TWO skill-embedding conventions (backfill task-space vs pipeline `"{title}: {principle}"`) — the exact defect class that produced the episodic incident | **FIXED** — canonical `skill_embedding_text()` in `skill_bank.py`, both writers import it |
        | 5 | API callers of `score_external_result` | **VERIFIED SAFE** — both wrap in `except Exception` → a refused write is a lost write with a loud log, not a 500 |
        | 6 | Query-side embedder outage (garbage query vector at retrieval) | **VERIFIED SELF-NEUTRALIZING** — zero/NaN queries score 0.0/-inf against every row and fall below `min_similarity`; retrieval degrades to empty, not wrong |
        | 7 | Strategy store coherence (never audited) | **VERIFIED CLEAN** — 1424 = 1424 = 1424 (sqlite = faiss = id_map), 0 degenerate vectors |
        | 8 | Two `skills.db` files | **VERIFIED HARMLESS** — canonical is `sessions/skills.db` (all consumers agree); root-level twin is an empty fossil; both 0 rows post-purge |
        | 9 | One 911 MB pre-reseed `.tmp` orphan | **REMOVED** |
        | 10 | Newest 25 episodic rows | **VERIFIED** — 25/25 on contract, `update_count` NULLs = 0, live traffic flowing through the fixed path |
        | 11 | `structural_lab.distill_skillbank` constructs `DistillationPipeline` with nonexistent kwargs and calls sync `run()` on an async method | **NOT fixed** — broken-but-loud (returns `{"status": "error"}`); a real fix needs teacher-model wiring (inference). Absorbed into M-11a below |

        Final state, all five checks: `ntotal=58386 id_map=58386 desync=0`, round-trip 500/500,
        diversity 67/67 (1.000), degenerate 0/500, **semantic self-match 0.9956**. AutoPilot gate:
        PASS. Touched-surface suite: 453 passed (single failure = pre-existing env-var flake).
        **Verdict: cleared for seeding via AutoPilot and/or live traffic.**
  - [x] M-17i — 14 further tests (`tests/unit/test_degenerate_embedding_guard.py`), including the
        measured fallback distribution, so a future "fix" that makes the fallback well-formed —
        which would be *more* dangerous, not less — fails loudly instead of passing silently.
        ✅ 2026-07-28

        **Two defects in my own detector, caught by measuring instead of assuming:**
        a cosine test at 0.99 had a **45% false-positive rate** against random unit vectors (the
        overflowed reference vector is unnormalised and dots high with anything) — replaced with
        exact comparison, now **0 false positives over 3,000 live BGE vectors**; and I first wrote
        that hash vectors are "maximally diverse and defeat `vector_diversity`", which is wrong —
        at 89% all-zero they collapse, and that check *would* fire.
  - [x] M-17j — **Semantic health + Q-score poisoning guard live checkpoint.** ✅ 2026-07-29.
        Orchestrator main contains `93d8349b` and `ec087da1`: the health check requires the
        repository Python and a completed semantic self-match rather than silently skipping it;
        external Q-score updates reject fallback/degenerate embeddings and require exact normalized
        objective, task-type, and action identity after FAISS candidate lookup. An API-only reload
        activated the guards. Live semantic check: `ntotal=58749`, `id_map=58749`, `desync=0`,
        round-trip 500/500, and mean cosine **0.9824** over 8 samples. Focused memory tests passed;
        the integrated checkpoint ran 322 E8 tests plus those focused memory tests.
  - [x] M-17k — **Generic missing-service health visibility.** ✅ 2026-07-29. The independent
        re-audit found that dead services could vanish from automated status when their launch-state
        row was missing. Orchestrator `b63e03e5` now reconciles current manifest-declared
        non-optional services against the state file and reports a distinct `state-missing` status
        as `healthy` or `unavailable`; inactive warm roles remain absent by design. The existing
        optional-auxiliary row continues to expose Whisper as `unavailable_optional`, and declared
        NextPLAID services can no longer disappear silently. **44 focused stack tests** passed,
        with Ruff and `git diff --check` clean. This closes the health-observability residual; it
        does not change the production lineup or the episodic-store acceptance result.
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

As observed: the index shrank from ~707k legacy-inclusive vectors to **58,281** live task vectors,
because it previously spanned
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

M-10/M-10a are closed with the durable cosine result above. Next memory work is M-11a, M-12,
M-15, and M-16; do not reopen the reseed unless a new evidence-backed integrity failure appears.
