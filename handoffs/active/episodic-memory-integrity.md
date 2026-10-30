# Episodic Memory Integrity — 2026-07-05 corruption, root cause and repair

**Scratch**: `/mnt/raid0/llm/tmp/codex-ni06-main-20261006/` (NI08 record-design review). Historical NI07 integration source is preserved by APP commit `b87998e3b5a0cbb9da36c8db9fd2fcfbb69aba0d`; the completed task no longer depends on its throwaway checkout.
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
      `state.hybrid_router` is replaced by `SkillAugmentedRouter` (`services/memrl.py:645`, inside `ensure_memrl_initialized`; was :481) whenever
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
        **Composition probe (M-25a, 2026-10-21; read-only):**
        ```bash
        sqlite3 "file:orchestration/repl_memory/sessions/episodic.db?mode=ro" \
          "SELECT outcome, COALESCE(model_id,'unknown') AS model_id, COUNT(*) FROM memories \
           WHERE created_at > '2026-07-27T22:07' GROUP BY 1,2 ORDER BY 3 DESC"
        # live pool is filtered (structural_lab.py distill_skillbank, min_q_value=0.7, outcome-agnostic):
        sqlite3 "file:orchestration/repl_memory/sessions/episodic.db?mode=ro" \
          "SELECT outcome, COUNT(*) FROM memories WHERE created_at > '2026-07-27T22:07' AND q_value >= 0.7 GROUP BY 1"
        ```
        NULL `model_id` (rows before 2026-08-03) is the `unknown` bucket.
        Baseline at filing (2026-07-28T13:4x): **374**. The distillation pipeline consumes
        `objective`/`routing_decision`/`outcome` per trajectory, so readiness = enough FRESH
        post-reseed rows with real outcomes and untruncated objectives — suggest **≥2,000** (≈10
        batches at the default 20/batch over a meaningfully diverse pool) before the first run.
        The pre-distillation checkpoint in `_action_distill_skillbank` protects rollback either way.
        **M-25c/d — the first re-distil is arm-labelled (2026-10-21).** Record these with the run, never
        an unlabelled pool: (1) seed-set size in {1, 3, 5} (`intake-2169#05`, one task and one
        generator); (2) consolidator = the served worker model versus a larger teacher
        (`seed_skills.py:84-85` accepts only claude, codex or mock, so the local arm needs the
        `structural_lab` path); (3) dedup variant, baseline = two-way store-or-merge at cosine > 0.85,
        merge never rewrites text (`pipeline.py:317-358`), with `intake-2182#01` and `intake-2184#04`
        as candidate arms (ALFWorld and WildChat evidence only). Teacher-side solve rate or skill
        quality is NOT the SkillBank gate; the student-side matched A/B (M-23) is (`intake-2170#03`).
        `distill_skillbank` now returns the success/failure/escalation trajectory counts and a `pool`
        block, and the pre-distillation checkpoint note carries the pool composition.
  - [x] M-11a2a — **`model_id` capture WIRED** ✅ 2026-08-03 (orchestrator `c05bc415`). It was NULL
        on all 59,337 rows: `store()` always accepted the argument, no caller ever passed it, so
        warm-start and per-model analysis over the corpus were impossible. Wired at the three
        q_scorer `store()` sites, DERIVED from compiled priors rather than a role->model table
        (which would have drifted twice in the past week: architect_general 122B->27B,
        coder_escalation 35B->27B). Unknown action -> None, so NULL keeps meaning "unknown".
        The two SIBLING columns are deliberately left NULL and that is the fix, not an omission:
        `assigned_role` is the Trinity tri-role axis whose readers already normalise NULL->WORKER
        (TR-1.5) and whose classifier is shadow-mode/off; `sub_decision` NULL correctly means "not
        a sub-decision". Writing a SERVING role into either is a wrong value where NULL is right.
  - [x] **Live trace emission wired** ✅ 2026-08-03 (orchestrator `5acd7214`). Separate store,
        same class of gap: `data/trace/events.sqlite` held 10,488 events carrying
        role/trial/category/detail and EVERY ONE was ingested from a log file after the fact.
        Trial 1460 wrote 9 episodic rows and **0 trace events**. Emission now hooks
        `Journal.record()` — the one chokepoint every path crosses, including skips and the
        AUTOPILOT_KILLED placeholder — under a new `EventSource.AUTOPILOT_LIVE`. Fails open.
  - [x] M-11a2b — **bounded `work` capture is wired through the production write path.** ✅ 2026-10-07 (orchestrator `a4132e57`). MAIN verified six completion producers, the single redaction/bounds policy and routing/external append writers, plus the real progress-JSONL → QScorer → SQLite synthetic case in accepted115/115. Escalation carries failure metadata without task-solving work. [Exact source review and evidence](../../artifacts/ni08/m11-work-capture-source-20261007/README.md). The **2026-07-28 0of58,655** remains historical; this closure establishes wiring only, no current corpus prevalence, real-traffic accumulation, distillation usefulness or skill efficacy. M-11a re-distillation remains open.

        Historical context — the reseeded store holds 200-char
        objective stubs; rich trajectories arrive only from new live-traffic/autopilot writes, so
        the first re-distil is best run after real traffic accumulates. The 57 previous skills reference
        `source_trajectory_ids` matching 0 current rows, and were distilled from 200-char stubs — all
        57 are thin routing heuristics because that is the ceiling of the input. Re-distilling over
        real trajectories is what makes SkillBank worth its retrieval slot.
- [x] **M-24 — Advisory literal-constant lint for distilled skills, calibrated on a shipped corpus (zero inference; nothing is distilled).** ✅ 2026-10-21 Build a lint that flags skills embedding literal parameters, paths, column names or ids copied from the source trajectory (`intake-2169#02`); advisory only, never an admission gate or a quality score (`intake-2181#03`, `intake-2190#07`); note that the live teacher prompts instruct 'preserve specific model names, tier names, and port numbers' (`orchestration/repl_memory/distillation/prompts.py:39,50 @5d4ad2c0`), so the lint fires on them by design and the finding is reported, not hidden. Calibrate first on the 1,277 SKILL.md files of cxcscmu/SkillLearnBench @ 726e1f7 (`intake-2180#02`; our script reads the files only, re-clone at the pinned SHA if the scratch copy is gone; report flag rate per generator config versus human_authored), then run once on the pre-purge 57-skill backup `orchestration/repl_memory/sessions/skills.db.pre-purge-20260727T221856Z` opened read-only. M-11a stays operator-directed and inference-gated.
  - 2026-10-21 `noninf-memeval` built and calibrated, NOT ticked: orchestrator `3d31fa0b` on main (`orchestration/repl_memory/distillation/literal_lint.py`, `tests/unit/test_literal_lint.py` 3 passed), advisory only, six rule categories plus `ROLE_MODEL` fixed before the run; output [`artifacts/noninf-memeval-20261021/m24_result.json`](../../artifacts/noninf-memeval-20261021/m24_result.json). Corpus: SkillLearnBench @ 726e1f79, 1,277 SKILL.md in 24 configs, every skill matched to its task source (0 unmatched); a literal counts as "grounded" when it also appears verbatim in the task's instruction or environment text (tests excluded). Flag rate (any literal) 850 of 1,277; grounded 687 of 1,277. By method family, any / grounded: b1 one-shot 316 skills 0.611 / 0.446, b2 self-feedback 310 0.632 / 0.510, b3 teacher-feedback 348 0.713 / 0.641, b4 skill-creator 267 0.682 / 0.562, human_authored 36 skills 0.861 / 0.417. Per-config rates (24 rows) are in the JSON. Reading: the lint does NOT separate generated from human skills on the any-literal rate (humans flag highest) and only the grounded rate puts every generator family above human; it is a descriptive advisory, not a quality signal, consistent with the filing's no-gate rule. Pre-purge `skills.db.pre-purge-20260727T221856Z` (read-only): 33 of 57 skills flagged, 32 of them `ROLE_MODEL` (frontdoor, architect_general, architect_coding ...), 1 `NUM`; the role/model hits are the by-design finding from the live teacher prompt's 'preserve specific model names, tier names, and port numbers' rule, reported not hidden. No source-trajectory grounding was possible for the EPYC bank (trajectories not retained with it).
- [x] **M-25 — Make the first re-distil an arm-labelled, composition-reported pool (read-only probe, pool counts, arm labels; nothing is distilled).** ✅ 2026-10-21 (a) Extend the readiness probe (lines 143-149) from one count to `SELECT outcome, model_id, COUNT(*)` over the episodic store opened read-only, with NULL model_id (rows before 2026-08-03) as its own 'unknown' bucket, and add the q >= 0.7 filtered count because the live pool is filtered at `structural_lab.py:310,384-388 @5d4ad2c0` while the documented probe counts all outcomes; (b) surface the success/failure/escalation trajectory counts that `DistillationReport` already carries (`pipeline.py:129-131`) in the `distill_skillbank` return and in the pre-distillation checkpoint note (`actions.py:2331-2334`) so the first re-distil is not an unlabelled pool (all-failure pools are consistently worst, `intake-2190#09`); (c) record in the M-11a text that the first re-distil is arm-labelled: seed-set size {1,3,5} (`intake-2169#05`, one task and one generator), consolidator = served worker model versus larger teacher (`seed_skills.py:84-85` accepts only claude, codex or mock; the local arm needs the structural_lab path), and dedup variant (baseline: two-way store-or-merge at cosine > 0.85, merge never rewrites text, `pipeline.py:317-358`; `intake-2182#01` and `intake-2184#04` are the candidate arms, ALFWorld and WildChat evidence only); (d) add the sentence that teacher-side solve rate or skill quality is not the SkillBank gate: the student-side matched A/B (M-23) is (`intake-2170#03`).
  - 2026-10-21 `noninf-memeval` done in code and text, NOT ticked: (a) probes run read-only on `episodic.db` (mtime 2026-10-03, prefix sha `3a2e4c75d3488967`): post-reseed `success`/`failure` rows 6,237 (baseline at filing was 374); with q >= 0.7, the pool the live path actually draws, 5,452 of them; by outcome at q >= 0.7: success 5,445, failure 7, so the live pool is 99.9 percent success and the all-failure-pool concern does not apply to it. Composition by `(outcome, model_id)` over all post-reseed rows is in [`artifacts/noninf-memeval-20261021/m25_outcome_model.txt`](../../artifacts/noninf-memeval-20261021/m25_outcome_model.txt) (15 buckets; largest success/qwen3.6-35b-a3b-mtp-q8_0 2,081, success/unknown 2,005, success/qwen3-next-80b 1,160, failure/qwen3.6-35b 535; `unknown` = NULL `model_id`, 2,005 success and 41 failure). Whole store 64,514 rows, 60,323 with NULL `model_id`. (b) orchestrator `3d31fa0b`: `distill_skillbank` returns `success_trajectories`/`failure_trajectories`/`escalation_trajectories` plus a `pool` block (also on the empty-pool early return), new read-only `distill_pool_preview()` feeds the pre-distillation checkpoint note via `_action_distill_skillbank` (guarded by `getattr`, so lab fakes without it behave as before); `tests/unit/test_autopilot_actions.py` 142 passed incl. 2 new. Escalation count will read 0 because `distill_skillbank` hardcodes `escalations: []` (pre-existing, unchanged). (c) and (d) written into the M-11a text above. Nothing distilled, no inference.
- [x] **M-26 — `distill_skillbank` escalation count is always 0 (investigate; no fix assumed).** `structural_lab.distill_skillbank` builds every trajectory with `"escalations": []`, so `DistillationReport.escalation_trajectories` (and the M-25 pool label) can only read 0. Find whether the episodic store or progress JSONL carries a real escalation source per memory (an escalation flag, `assigned_role` change, or `sub_decision`) and wire it, or document in the code and this handoff why it cannot be. Zero inference. Evidence: M-25 note above. ✅ 2026-10-24 Source audit found native `MemoryEntry.action_type` is the reliable escalation indicator; the approved private orchestrator candidate `96dc99c978a00c27d9ab130318048c4f3e44adf2` emits a marker only for `action_type == "escalation"`, binds the memory ID and evidence source, marks `aggregated_memory_pattern`, and preserves captured tier endpoints or null. Role/sub-decision are not used as evidence. M-25 report keys stay compatible and include `input_unit=episodic_memory_pattern`. The calendar-granted focused job `codex-ni-m26-20261024` passed all 3 tests in 2.62 s at 2026-10-24 13:11:14Z (logs and completion receipt under `/mnt/raid0/llm/tmp/codex-ni-20261024-m26-fix/` and `/mnt/raid0/llm/tmp/codex-ni-20261024-scheduling/m26/`). Feature branch `codex-ni-20261024-m26-fix-orch` was published at `96dc99c978a00c27d9ab130318048c4f3e44adf2`; the exact three-file patch was integrated into orchestrator `main` at `f279d2debddd978a2a97d42dcad4e37662bbdc09` from fresh base `e0ba98fe6f7be12a77eeac3a487261da17f5ea5c` with identical source/test blobs; no inference, teacher call, live database access, current pool census, or skill-quality claim is established. Prospective pool-input recording/reader work is separately tracked; it does not gate this source fix.
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
  - [x] M-17c — **`semantic_self_match` re-specified: per-row verdict, not a mean.** ✅ 2026-08-04
        (`ce6e4bea`). The gate refused to start AutoPilot on a store that was otherwise healthy.
        Root cause was the METRIC. It took a **mean over a sample of 8**: measured that day, 59 of
        60 rows self-matched at ~0.996 and exactly ONE scored 0.0212, giving
        `(7×0.996 + 0.021)/8 = 0.874` against the 0.90 floor — precisely the 0.8718 reported. **One
        bad vector in 60,340 rows stopped the system.**

        The mean was also BLIND in the opposite direction, which matters more: ten vectors belonging
        to OTHER rows among ninety perfect ones averages 0.955 and **passes**. So the metric could
        both false-alarm on 0.0017% corruption and hide 10%. Replaced with a per-row verdict over 60
        rows — a cross-row hit (`< 0.55`) fails on its own because it is unambiguous, plus a 2%
        tolerated fraction below the 0.90 floor. This is a sharpening, not a weakening: it still
        FAILED after the change and named the offending row.

        Note for M-17's table above: the injected-defect validation used *whole-store* corruption,
        where a mean and a fraction agree. Neither the single-bad-row nor the partial-corruption
        case was in the fixture set, which is why the metric's two failure modes survived it.
  - [x] M-17d — **Repaired the one genuinely corrupt vector** ✅ 2026-08-04. Row
        `eaacda97-50bc-4e63-b3c1-e75a73afdb7a` (written 17:11:27 during trial 1472), idx 60336:
        re-embedded 0.0212 → 1.0000. `IndexFlatIP` rebuilt preserving every position, because
        `memories.embedding_idx` is a POSITION and `remove_ids` would shift every index above the
        removed one — silently invalidating them. Verified exactly 1 of 60,340 positions changed.
        Store passes all five checks.

        `repair_episodic_embeddings.py --diagnose-only` reported **HEALTHY** throughout: it checks
        structural coverage (id_map sync, orphans), not vector CONTENT. A content-level single-row
        defect has no tooling — see M-17e.
  - [ ] M-17e — **No tool repairs a content-corrupt vector.** The 2026-08-04 fix was a one-off
        script. `repair_faiss_id_map.py` fixes desync, `repair_episodic_embeddings.py` fixes
        coverage, `reseed_episodic_store.py` rebuilds everything — nothing targets "this row's
        vector is wrong". Promote the position-preserving single-row re-embed into
        `scripts/maintenance/` so the next occurrence is not a bespoke script.
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
        `TaskEmbedder()`** — `memrl.py:573` (was :388), `routing.py:162`, `strategy_store.py:308`,
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
  - **M-12 protocol (filed 2026-09-07 via research-intake; the run itself stays compute-gated).**
    Two instruments, run in this order, judge/scorer held fixed across every arm.
  - **OP-42 readiness package (2026-09-16, zero inference):** token stats, GPU fit, run plan, blockers B1–B7 (B1 = 200ch/20ch Tulving id collision → silent wrong ground truth), options A–D → [`progress/2026-09/2026-09-16-sub-op42-readiness.md`](../../progress/2026-09/2026-09-16-sub-op42-readiness.md). OP-42 stays open; no operator action needed now (operator 2026-09-16).
    - **Blocker status 2026-09-16 (`sub-m12-blockers`, [`progress`](../../progress/2026-09/2026-09-16-sub-m12-blockers.md)):**
      - B1, B2, B3 closed on research `sub/m12-blockers-20260916` (`b69be5b2`, `3f16537d`, `ec7fb4ab`; review
        fixes `06ae638d`), merged to research `main` at `cfbfa448`; root SC67/SC68 updates merged with
        `sub/m12-blockers-root-20260916`.
      - B4: judge = `gemma-4-26B-A4B-it-ORIG-Q8_0` (operator 2026-09-16), recipe
        `eval/gemma-4-26b-a4b-orig-q8-gpu-judge-np4`.
      - B5: recipe + smoke `a6491b9e`, `docs/m12-long-context-gpu-recipe.md`. **M-12 GPU window deferred by the
        operator 2026-09-16**; `smoke_prefix_reuse.sh` (`a6491b9e`) is ready for when it resumes.
      - B6: the merge list now also covers these two branches — both merged (research `cfbfa448`).
      - B7: add `pandas` to the research `.venv` (`uv sync --extra benchmark`, which also realigns pyarrow to
        24.0.0) — see M-12j.
  - [x] **M-12a — Tulving 200ch/100K first** (intake-408#record). Variant `Udefault_Sdefault_seed0`,
        chapters=200 (`tulving_episodic_adapter.py:_select_target_qa_files` at :463 already resolves
        this to the 196ch parquet on disk). Three prompt-matched arms: memory-OFF (question +
        answer contract, no book), memory-ON (`src/trace` retrieval fills the context), CEILING
        (full book, what the adapter does today at :637). **Headline on the five-bin Simple Recall
        Score WITH bin 0 included** — the hallucination bin is the point. Report Chronological
        Awareness separately as a diagnostic until the tau fix (M-12d) lands; report
        Entities/Times/Spaces separately from Event-contents/Full-details; identical list-only +
        "If none, say 'None'" contract on every arm. Deterministic scorer, no LLM judge.
        *2026-09-16 (B1, merged `cfbfa448`):* the M-12a command must set `TULVING_CHAPTERS=200`;
        `score_tulving_run --chapters` is now optional and must agree with the recorded rows.

        ✅ **2026-09-18 — RUN, SCORED AND INGESTED. Retrieval reaches the full-book ceiling.**
        Operator lifted the recipe's *"the operator runs everything here… Agents do not"* rule for this
        window and freed the GPU explicitly; recorded here so the next reader sees the rule was
        **waived deliberately, not missed**. Reader: `qwen3.6-35b-a3b-q8-gpu-mtp-longctx196k-np4`
        (`recipe_hash 54674144…`, argv from `m12_launch_argv.py`, never transcribed), champion build
        `/mnt/raid0/llm/tmp/build-fold-ef81196d5/bin`, linkage PASS, 4 slots × 196,608 ctx.
        `SMOKE_PREFIX_REUSE: PASS` first (receipt in the artifacts below): the 104,698-token book costs
        89.6 s cold, then a follow-up reuses 102,650 tokens in 3.2 s, and step F confirmed the book
        keeps its prefix **after an intervening 191,447-token BEAM conversation** — which is what the
        four slots are for, not throughput. Server launched and killed by the measuring session.

        **Headline — five-bin Simple Recall Score, bin 0 INCLUDED.** 686 questions per arm, 686 scored,
        0 missing ground truth, variant `Udefault_Sdefault_seed0`, `book_sha16 afa5379c27e83459`,
        196 chapters on disk. Each arm's `context_mode_by_prompt` confirms it ran the arm it claims.

        | arm | Simple Recall | avg F1 | truncated | run_id |
        |---|---:|---:|---:|---|
        | memory-OFF (`none`) | **0.1893** | 0.2487 | 7 | `20260918_142038` |
        | memory-ON (`retrieved`) | **0.6069** | 0.6432 | 5 | `20260918_143309` |
        | CEILING (`full` book) | **0.6086** | 0.6189 | 13 | `20260918_150038` |

        **Retrieval is within 0.3% of the ceiling** (0.6069 vs 0.6086) and is *ahead* on avg F1
        (0.6432 vs 0.6189). FTS5 chapter retrieval over the trace store buys essentially everything
        that putting the whole 104,725-token book in context buys — which is the question M-12 exists
        to answer.

        **The bins are the result; averaging them away hides it.** Per-bin avg F1:

        | arm | bin 0 (150 q) | bin 1 (150) | bin 2 (90) | bin 3-5 (98) | bin 6+ (60) |
        |---|---:|---:|---:|---:|---:|
        | memory-OFF | **0.927** | 0.001 | 0.002 | 0.007 | 0.010 |
        | memory-ON | 0.853 | 0.623 | 0.664 | 0.534 | 0.360 |
        | CEILING | 0.760 | **0.685** | 0.531 | 0.509 | **0.558** |

        - **Bin 0 is the unanswerable set, where the correct answer is `"None"`.** memory-OFF scores
          **0.927** there and ~0 everywhere else: it is excellent at declining and knows nothing else.
          Its headline is almost entirely the abstention bin. That frank "I don't know" is a **property
          worth keeping**, not a deficit — it is the behaviour the hallucination bin was added to detect.
        - **The full book is the WORST arm at declining** (0.760 vs retrieval's 0.853): more context
          makes fabrication on unanswerable questions *more* likely, while it helps most on the hardest
          6+ bin (0.558 vs 0.360). Retrieval keeps cleaner abstention and wins bins 2 and 3-5.
        - Reporting bin 0 separately would invert the ranking, which is exactly why the headline keeps it.

        **Chronological Awareness (diagnostic only, pending the M-12d tau fix):** 0.109 memory-OFF /
        **0.344** memory-ON / 0.290 CEILING — retrieval ahead of the full book here too.

        **Caveat, not papered over:** CEILING truncated **13** rows against memory-ON's 5 (a 104K-token
        prompt leaves less room before the length cap), so the ceiling arm is slightly understated. The
        two headline figures are within 0.3% of each other and 13/686 truncations could cover that gap —
        **treat "retrieval matches the ceiling" as established, and "retrieval beats the ceiling" as NOT
        established.** Raising the answer budget for the `full` arm would settle it.

        **Belief kernel (write side, wired):** each arm's scorer run emits
        `belief_measurements.jsonl` **beside its own artifact**, ingested via
        `cli.py ingest tulving` — 3 units matched, 3 projected, 0 declined, 0 refused, 6 rows, 18 frames.
        Rows carry `metric_direction=higher_better`, `reps` (548 recall / 138 chronological) and
        `protocol_id epyc.vidya.tulving_episodic_capture.v1`.
        Artifacts: `artifacts/m12/run_20260918/` (3 scored JSONs, 3 sidecars, the smoke receipt, the
        reader argv, the arm→file map).

        **Two defects found while running this, both worth fixing before the next window:**
        1. **The recipe's §7 command omits `--model`**, so as written `run_benchmark.py` enumerates
           **all 71 models / 80 roles**, smallest first. It began with a 0.1 GB embedder and **sent
           Tulving questions to the resident 35B reader while labelling them as the embedder role**
           before failing on `enable_thinking=False`. Silent mis-attribution; add
           `--model qwen36_35b_a3b_mtp_q8_local` to the documented line.
        2. **The belief sidecar path follows `--out-json`.** Scoring every arm into one shared
           directory makes each arm **overwrite** the previous arm's sidecar, leaving one arm's rows
           and silently losing two. Score each arm into its own run directory (or the capture's
           default location), and check the row count per arm afterwards.
        3. *(Also observed)* every result row has `prompt_tokens: null` — completion tokens are
           recorded but prompt tokens are not, so the per-question context cost of a no-book arm vs a
           104K-token arm is **not recoverable from the results file**. Relevant to any cost-per-answer
           comparison; adjacent to the RTG-47 terminal-prompt-token work.
  - [ ] **M-12b — BEAM 128K second, abstention EXCLUDED from the headline** (intake-1330#record).
        BEAM's Vanilla column = memory-off, its `pair_chunk` RAG column = naive-memory control,
        our trace/navigation surface = the only new arm. Report instruction_following,
        preference_following and event_ordering separately; headline on the five-ability
        discriminating core. Prompt-match all arms — do NOT give the memory arm a closed-book
        instruction the memory-off arm lacks.
        *2026-09-16 (B2, merged `cfbfa448`):* arms are selected with `BEAM_CONTEXT_MODE=full|rag|trace`
        and scored with `score_beam_run --arm full|rag|trace`.
  - [ ] **M-12c — pre-run do-not-copy checklist, seven items** (intake-1337#record, each traceable to
        a site in MemPalace issue #125): (1) report BEAM's own fold, never a binarised
        micro-average; (2) ingest BOTH roles, never user turns only; (3) no synthesis
        `max_tokens` below what the highest-nugget ability needs; (4) judge model != reader model,
        held FIXED across arms; (5) no SSL bypass — stage the dataset under
        `/mnt/raid0/llm/data/eval/` with a verified digest; (6) identical retrieval budget and
        identical chunking for the control and the arm under test; (7) prompt-match all arms,
        including the closed-book instruction.
  - [ ] **M-12d — external reference curves, used as floors and sanity checks, never as targets.**
        (a) Tulving: the authors' shipped 12-arm results at
        `/mnt/raid0/llm/data/eval/tulving_episodic/episodic-memory-benchmark/epbench/data/result_lenient_all_book_200.csv`
        (548 per-question rows × 12 arms) plus the 17 raw answer directories under
        `Udefault_Sdefault_seed0/answers/…nbchapters_196…` — chapter-chunk RAG beats full 100K
        in-context for all four published models (intake-408#record). (b) BEAM: issue #125's Raw
        ChromaDB arm (49.0% author fold / 55.7% BEAM fold, BEAM 100K, configuration fully
        specified) is a **sanity floor** — far below it means a configuration bug, not a finding.
        It is NOT a target: that run discarded assistant turns and capped answers at 512 tokens
        (intake-1337#record). Harness caveat: upstream BEAM's published evaluator passes
        `probing_question` to all ten evaluators but omits it from the judge prompt; all 40
        abstention prompts in the 100K split use one-item refusal rubrics, so this is not a
        question-conditioned responsiveness or multi-criterion abstention measure ([judge source](https://github.com/mohammadtavakoli78/BEAM/blob/b2da22eac88bb0874c64665f13457eb99835774a/src/evaluation/compute_metrics.py),
        [100K prompt files](https://github.com/mohammadtavakoli78/BEAM/tree/b2da22eac88bb0874c64665f13457eb99835774a/chats/100K)).
  - [x] **M-12e-a — make the Tulving adapter's dataframe load FAIL LOUDLY.** `tulving_episodic_adapter._load_qa_from_variant` ✅ 2026-10-29 (audit: raise half: research ccc41d4b "CME-4 + M-12e-a ... loud dataframe load"; remaining half: pyarrow-25.0.1 + pandas now in research .venv (dist-info mtime 2026-09-16 10:18)) [no-belief: audit-reconciliation]
    swallows a missing pandas/pyarrow and then scores every question as missing, so an M-12a run in the research venv
    (which has no pyarrow) would emit an all-zero summary that looks like a result. Raise instead, and add pyarrow to
    the research venv. Found 2026-09-15 while verifying the M-12e rescore, which had to run under the delta-Mem venv.
    *Progress 2026-09-16 (not ticked):* research `ccc41d4b` — the RAISE half is done: a missing pandas/pyarrow and any per-file parquet read error now raise
    `RuntimeError` (tests: `test_tulving_context_mode.py`). The research `.venv` still lacks pyarrow and was not
    modified; `/mnt/raid0/llm/venvs/ml-training` has pandas + pyarrow + pytest and ran the rescore. **Remains:** add
    pyarrow to the research `.venv`. That needs a package install (network), which this lane was not allowed to do.
  - [x] **M-12e — scorer prerequisites, ZERO COMPUTE, do before any arm runs** (intake-408#record).
        ✅ 2026-09-14, research `dcb769c1`. THREE defects, not two. (i) the unconditional
        `simple_inputs.append(scored)` at :121 now fires only for `get_style == "all"`; the subset is
        settled by counting, not prose — the authors' `result_lenient_all_book_200.csv` has 548 rows
        and the 196ch `df_qa.parquet` has 548 `get=="all"` rows of 686. (ii) `chronological_tau` fails
        closed at 0.0 unless the matched set covers the FULL ground truth; `chronological_tau_detail()`
        reports coverage, the uncovered `tau_raw` as a diagnostic, and a per-question status.
        (iii) FOUND IN THE SAME SCOPE: the five bins keyed on ground-truth ITEM count, but the paper
        bins on matching EVENTS — reproducing the authors' `bins_items_correct_answer` matches 686/686
        on `n_chapters_correct_answer` and 629/686 on `n_items_correct_answer`; `nb_events` now rides
        in the prompt metadata and the `nb_gt` fallback is reported, never silent. Re-scored
        `20260619_141212` offline (stored responses; no model loads, verified by reading the import
        graph) to `benchmarks/results/runs/20260619_141212/tulving_score_rescored_20260914.json` —
        the original `tulving_score.json` is untouched. **SRS 0.5530 → 0.5684** (over 366 questions,
        not 456; subset fix alone 0.5755, bin fix alone 0.5402), **CAS 0.1593 → 0.1593** — unchanged
        only because no partial-coverage question here matched ≥2 items, so the tau defect is real and
        LATENT; 37 of 45 chronological questions are now labelled partial, and 30 of those 45 have
        <2 ground-truth items so two thirds of the tau leg is structurally 0.0. `avg_f1`,
        `by_retrieval_type` and 17.27 t/s unchanged. `SCORER_VERSION = 2` now rides in the summary and
        the markdown so v1 and v2 figures cannot be compared by accident. Tests 85 → 108 in
        `scripts/benchmark/test_score_tulving_run.py` + `test_tulving_episodic_adapter.py`. The four
        wiki paragraphs quoting SRS 0.5530 / CAS 0.1593 were refreshed in the same wrap-up; draft
        at `wiki/drafts/tulving-subset-scoring-and-tau-coverage.md`.
        *Re-verified 2026-09-16 (sub-memeval, root `sub/memeval-root-20260916`):* 108/108 tests pass; an
        independent offline re-score of the only stored Tulving run (`20260619_141212`) with the pre-fix
        scorer (`dcb769c1^`) gives SRS 0.5530 / CAS 0.1593 and with v2 gives SRS 0.5684 (366 q) / CAS
        0.1593 (37 partial). The fresh v2 summary is byte-for-byte identical to the committed rescore. Three
        un-annotated SRS 0.5530 quotes remained in `bulk-inference-campaign.md` (:5, :83, :584). They now
        carry the v2 value and the scorer note.
  - [ ] **M-12f — decide whether the paper's Chronological Order score excludes single-item questions before
        CAS is ever a headline**, since 30 of the 45 `chronological` questions in the 20ch set have fewer than
        two ground-truth items (15 have zero) so ordering is undefined and two thirds of the tau leg is
        structurally 0.0 — a CAS construction question, not a scorer bug
        (`scripts/benchmark/tulving_episodic_adapter.py:325` `compute_chronological_awareness_score`) (found
        2026-09-14, noninf sweep).
  - [x] **M-12g — stop comparing SRS across book sizes until the bin sets match**: ✅ 2026-10-08; bin `6+` is empty in the
        20ch set, so the 20ch SRS averages over four bins while the 200ch figure averages over five
        (`scripts/benchmark/tulving_episodic_adapter.py` `compute_simple_recall_score`) (found 2026-09-14,
        noninf sweep).
  - [x] **M-12h — close the judge-path tau trap before any LLM judge is wired**: `_llm_judge_fallback_hook` is
        dead in the deterministic path but `compute_f1_for_result` still branches on it and returns
        `matched_gt_items: []` when a judge fires, silently giving every judged question zero tau coverage
        (`scripts/benchmark/tulving_episodic_adapter.py:685-710`) (found 2026-09-14, noninf sweep).
  - [ ] **M-12i — codify an offline re-scoring protocol before any decision cites the corrected SRS/CAS**,
        since the 2026-09-14 re-score artifact is deliberately not an admissible claim and emits no belief
        rows, so the path is a protocol and never a back-filled tuple
        (`benchmarks/results/runs/20260619_141212/tulving_score_rescored_20260914.json`) (found 2026-09-14,
        noninf sweep).
  - [x] **M-12j — sync the repo venv or correct the dependency claim**: ✅ 2026-10-08; corrected the historical
        dependency claim from the dated metadata observation; Research now has pandas 3.0.3 / pyarrow
        25.0.1 METADATA, while APP has pandas 3.0.2 and no pyarrow METADATA. Minimum bounds differ from
        exact uv.lock resolutions. No importability, native linkage or replay claim and no environment
        modification. [Durable correction](../../docs/reference/tulving-offline-scoring-dependency-correction-2026-10-08.md). ✅ 2026-10-08
  - [ ] **M-12k — frontdoor answer-quality arm (filed 2026-09-26).** Beside the Tulving/BEAM instruments, run
        memory-on vs memory-off on the live frontdoor path over a frozen answer-quality suite (same prompts,
        same seeds; memory-off = routing without episodic lookups), reporting accuracy, latency and cost per
        arm. The 2026-09-26 audit found memory is used for routing only and has never been A/B-tested.
- [x] **M-23 — SkillBank A/B readout spec (supersedes the pooled-mean go/no-go of `handoffs/completed/skillbank-distillation.md` section 19; AK-PM-4 step (c) is re-pointed by its owner; M-12 itself stays the episodic A/B).** Zero inference; the run is gated on M-11a populating a bank and on the DAR-1 regret gate (`retrain-routing-models.md:126`). The cell is role plus model pin as served (frontdoor, worker, coder, architect). Report skill-on minus skill-off per cell with a task-level bootstrap 95% CI and the share of negative role-domain cells, never one pooled delta (`intake-2190#00`, `intake-2190#03`, `intake-2190#10`); declare the minimum detectable difference at the run n before the run (run-local declaration, not a standing rule) and do not rank arms whose CIs overlap (`intake-2181#01`); promotion is per-role non-regression, not mean > 0. Report adoption beside accuracy, defined as the share of injected skills whose title is echoed or visibly applied in the routed role's trace (titles, not ids, are in the prompt, `skill_retriever.py:230-236 @5d4ad2c0`), detector derived from the skill's own rule or title and fixed before the run; adoption is a separate failure axis from correctness (`intake-2169#04`); the SkillLearnBench tool-call metric is not comparable (`intake-2180#03`). Log per-request skill_ids joined to the served role and model pin. Teacher-side solve rate or skill-quality scores are never the gate; the student-side matched A/B is (`intake-2170#03`); any LLM-judged skill-text score is advisory (`intake-2181#03`, `intake-2190#07`). Report every headline delta under both intention-to-treat and per-protocol parse handling and re-score stored outputs with a second independent scorer before a scorer-dependent delta is acted on (`intake-2171#04`, `intake-2171#06`). Prior: the sign of skill benefit is a distribution (`intake-2169#08`, `intake-2190#00`), so borrow none from either paper. When the A/B reports, compare the entry format with Harness^2's (cue, adopted tree, EXPERIENCE.md, domain-scoped index; `intake-1995#02`). ✅ 2026-10-20
  M-29 clauses apply (see "M-29 readout clauses (filed 2026-10-21)" below the M-23 sub-items).
  - [ ] **VB-SKILLBANK-AB-WRITE producer call (owed, filed 2026-10-21):** the M-23 A/B runner calls `scripts/vidya/adapters/skillbank_ab.write_belief_measurements(out_dir, run_id=..., producer=..., request_log_path=..., cells=[...])` once per run, one cell per role x model pin, before its first arm runs; carrier and reader landed in root `7335da327`.

  **M-29 readout clauses (filed 2026-10-21; additions to M-23, whose own text is unchanged).** All descriptive or report-only; none is a gate.
  (1) Per role-model cell print the paired transition counts c (failed skill-off, passed skill-on) and b (passed skill-off, failed skill-on) with an exact two-sided McNemar p on the discordant pairs beside the net delta and the negative-cell share, and report b even when the net is positive (intake-1321#record); promotion stays per-role non-regression.
  (2) A skill-off REPLICATE arm (same pinned config, independent sampling) so the flip floor of an unchanged condition is measured, with a paired flip counted as a skill effect only if it exceeds that floor; an external replicate-noise figure (intake-2238#record) is an order-of-magnitude prior, never a substitute for measuring on the local served pin.
  (3) Stratify the transition table by adoption (title echoed or visibly applied, detector fixed before the run).
  (4) One placebo arm: skill-on with entries swapped for token-matched, task-irrelevant entries of the same format at the same injection point.
  (5) If a cell reads net-negative (b greater than c) the follow-up is a Bernoulli mask arm over the entries injected in that cell (inclusion 0.5 at retrieval time, mask count from the stated power analysis, per-skill effect with a permutation test); declare the paired-task count and resulting resolution before any per-entry run, and report cell-level only if the populated cell is too small (intake-2229#record, intake-2259#record).
  (6) Report injected tokens per request and total prompt-plus-completion tokens per request or trace for both arms, and the skill-on minus skill-off delta per 1,000 injected tokens (intake-2288#record, intake-2301#record).
  (7) Record the role-prompt hash (prompt version id) beside the model pin so a prompt edit splits the cell (intake-2290#record).
  (8) Label each request general-only or general-plus-specific and, for the latter, by tercile of the top specific entry stored cosine similarity (cut points fixed before the run) (intake-2318#record).
  (9) Print the skill-off pass rate beside every cell delta and list cells at or above 95 percent skill-off as ceiling-limited, excluded from the negative-cell denominator (intake-2337#record).
  (10) Record each injected skill source role at distil time and whether the injection was same-role or cross-role, because the retriever has no role term (intake-2333#record).
  (11) Report write-side cost as LLM calls plus input and output tokens summed over every memory-construction call, judge calls excluded, beside the read-side line (intake-2311#record).

- [ ] **M-20 — telemetry and evaluation for the model-initiated `recall()` / `route_advice()` REPL tools**
      (`src/repl_environment/routing.py:81` `_recall`, `:319` `_route_advice`). Zero observed calls in
      1.7 GB of progress JSONL, and only 6 rows carry `repl_steps`. Log each call (query, hits, whether the
      answer used them), then decide from data: keep, re-prompt, or remove. (filed 2026-09-26)
- [ ] **M-21 — filter smoke/probe traffic out of episodic write-back.** Live write-back is dominated by smoke
      prompts (`"What is 17 * 3?"` alone: 8,641 Q updates). Tag probe/smoke/health traffic at the API and skip
      its write-back; add a test and a one-off count of affected rows. (filed 2026-09-26)
- [ ] **M-22 — give `recall()` a live exploration write path, or say it is seed-only.** `recall()` reads only
      the 728 seed `exploration` rows (0 updates); nothing writes exploration rows from live traffic. Either
      write exploration memories from real REPL sessions (with M-21's filter) or document recall as a static
      seed lookup and scope M-20 accordingly. (filed 2026-09-26)

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

## Research Intake Update — 2026-09-17 (typed memory writes; intake-1472/1473/1474)

- [x] **M19-RECORD — specify native memory-write diagnostic records.** MAIN accepted 2026-10-06: [APP record contract](https://github.com/pestopoppa/epyc-orchestrator/blob/be8d46f61edcf5cb795d485b1a8171c562ee4971/docs/design/memory-write-decision-record-v1.md), per-question probabilities/local confidence, honest typed/untyped provenance and unresolved states, opaque value receipts, immutable self-hash. No writer, calibrated threshold or enforcement implemented. Parent M-19 remains open.
- [ ] **M-19 — Typed decision records + confidence gate design (record spec unblocked; gate threshold needs its own calibration record).** *Corrected 2026-09-26 (operator-directed tidy): was "blocked on TD-2". TD-2 landed 2026-09-17 and was never the unlock — `fuzzy-workflow-authoring-gui.md` FW-1 §4 D-1: calibration lifts per (model pin, question catalogue) on an operator-ratified record, never globally, and TD-5 forbids enforcement without operator approval. The record spec is zero-inference and dispatchable now; only a live gate waits on a calibration record for the memory-write catalogue on its model pin.* Specify a memory-write record carrying per-question probabilities and a caller-computed confidence statistic; the gate threshold must come from a calibration record for that catalogue and model pin (TD-2 is the method; owner `typed-decision-plane.md`, RTG-56), never from candidate softmax (intake-1474 measured 65% of 7B wrong fields above 0.90 confidence).

## Work payload bound follow-on — 2026-10-07

M-11a2b closes producer-to-store wiring only. MAIN source review found that `sanitize_work_text` trusts any suffix marker for the same cap, even after an oversized prefix. This allows an untrusted marker to bypass the nominal bound and the post-truncation redaction pass. Redaction remains the existing default-on, fail-open policy; no privacy guarantee is asserted.

- [x] **M11-WORK-CAP-SOURCE — refuse oversized forged truncation markers while preserving legitimate bounded-value idempotence.** Bound both prefix and marker representation; meaningful forged suffix, oversized decimal metadata, greater-than-scanner-limit synthetic credential and legitimate second-pass controls. Full actual memory-record/work-payload source verification through VB-M11-WORK-CAP-CONFORMANCE. Preserve objective text, existing item policy and sole redaction policy. No live memory, traffic prevalence or historical rewrite. ✅ 2026-10-07 — MAIN accepted [source and original41/41](../../artifacts/ni08/m11-work-cap-source-20261007/README.md).

**M-12h complete, 2026-10-08:** [MAIN source/native acceptance](../../artifacts/ni08/sc54-mf-m12h-source-integration-20261008/README.md). Research main daa preserves deterministic counts/matches while a judge supplies scalar precision/recall/F1; match/result provenance is explicit. All eight original AST-isolated controls passed, including no-judge and low/high judge branches. Synthetic hooks exercise the actual source body without LLM calls. This fixes the source trap; it does not claim improved tau, semantic alignment, retrospective rescoring or instrument admission. M-12g/M-12i remain independent next work.

**M-12g complete, 2026-10-08:** Research main `72832ef6` gates explicit SRS comparisons before output/capture and reports populated bins/counts without changing SRS/CAS arithmetic. The original 32 whole-module controls passed, including mismatched-bin refusal and valid comparison paths. [Evidence and limits](../../artifacts/ni08/tulving-srs-workflow-controls-20261008/README.md). Matching bins do not establish equal book difficulty. M-12f metric construction and M-12i prospective offline replay remain separate.

## Research Intake Update — 2026-10-20 (harness cluster)

Operator-approved 2026-10-20 via research intake (plan sha256 1dc83054706ca0bae002602307b0d9ba6435b010be4d6ffd8a495a04605f3967). Monitor and knowledge records below are prose: no checkbox, no index next action.

- **M5 (monitor, 2026-10-20) — SkillBank re-distil and teacher follow-ons (consolidator arm, seed-set size, extractor rubric, GenericAgent, MUSE-Autoskill, SkillLens code, skills-in-the-wild, SWE-Skills-Bench).** Trigger: The first M-11a re-distil is scheduled, or the M-23 readout shows negative role cells. First step when it fires: Apply the arm labels in M-25; dive the listed sources. No immediate step remains: M-11a is operator-directed and inference-gated; the bank is empty.
- **K3 (knowledge, 2026-10-20) — Skill-benefit sign prior and SkillBank reading rules (SkillsBench -1.3, SkillGenBench about 0, SkillLearnBench +20.3, mean +2.29 with 37 of 150 cells negative; adoption separate from correctness; LLM-judged text quality advisory; four failure reason classes).** Retained use: Cited by M-23 and M-24; no prior borrowed.

## Cache-friendly injection of memory and SkillBank context — 2026-10-21

Landed on epyc-orchestrator origin/main as `fc02209d` (flag `ORCHESTRATOR_CACHE_FRIENDLY_INJECTION`, default OFF, flag-off byte-identical, 18 tests plus 290 caller tests). Shared helper `src/prompt_builders/reusable_blocks.py`; wired into `SkillRetriever.format_for_prompt` and `build_routing_context`. Purpose: byte-identical, at-least-256-token blocks so chunk-KV reuse (cacheclip port) can hit. Flag-on drops Q-values, rank order and ids from the model-visible text and adds a 160-char objective per memory.

- [ ] **CFI-1 — quality A/B of `ORCHESTRATOR_CACHE_FRIENDLY_INJECTION` on vs off (SkillBank `skill_context` and episodic recall).** Paired, same tasks, same role/model pin, report accuracy, turns/task and tokens/task. The flag stays non-default until quality is neutral or better. Needs an inference window (not zero-compute). (filed 2026-10-21)
- [ ] **CFI-2 — decide the memory-k widening needed to reach 256-token blocks on the episodic path.** `retrieve_for_routing` yields only a few memories of about 25 tokens each, so flag-on emits one short block (`meets_min=False`). Options: widen k, or include a stable memory-library prefix. Decision package with the token and latency cost; the choice blocks only this item. (filed 2026-10-21)
- [x] **M-28 — Cache-friendly layout rule for episodic-memory and SkillBank injection.** The routing context is about 75 tokens today and skills are a small library reused across many requests. Group injected memory and skill items into blocks of at least 256 tokens, serialise them deterministically (stable order by id, no per-request fields inside a block), place the blocks contiguously, and keep the per-request volatile text outside them, so a chunk-reuse path can hit when memory and SkillBank go live. Write the rule into this handoff and add a rendering test (same item set, two retrieval orders, identical blocks). Cross-reference RTE-LOG-1 and REPL-EMB-6.1 so real reuse is measured once live (intake-2311#record, intake-2297#record). It does not change which skills are selected. Acceptance: the rule is filed, the rendering test passes, and the injected text for a fixed item set is byte-identical across orders within each block. Estimate: 0.5-1 day. ✅ 2026-10-21
  - 2026-10-21 (dpf-logpfx): DONE. Rule filed below. Rendering tests already in orchestrator `fc02209d` (`TestPacking.test_order_insensitive`, `TestSkillPath.test_flag_on_deterministic_and_score_independent`, `TestRoutingContext.test_flag_on_stable_across_q_and_order`) pass in the 282-test run; cross-references to RTE-LOG-1 and REPL-EMB-6.1 are in the rule. Selection unchanged.
  - **Cache-friendly layout rule (filed 2026-10-21, lane `dpf-logpfx`).** Implemented by `src/prompt_builders/reusable_blocks.py` (orchestrator `fc02209d`), flag `ORCHESTRATOR_CACHE_FRIENDLY_INJECTION`, default OFF, flag-off byte-identical. (1) One item = one canonical text: whitespace normalised, control tokens neutralised, no score, Q-value, id, timestamp or rank in it. (2) Items are de-duplicated and ordered by sha256 of their canonical text, never by retrieval order or score, so the same item set renders to the same bytes in any retrieval order. (3) Content-defined cuts close a block once it holds at least 256 estimated tokens (maximum 1024), so adding or removing one item dirties about one or two blocks; a trailing remainder merges into the previous block; items are never split; a set below 256 tokens in total yields one short block with `meets_min=False`. (4) Stable delimiter lines; the sha256_12 of a block is exposed for logging only and is never written into the prompt. (5) Blocks are placed contiguously; per-request text (own role, suggestion, task) sits after them. (6) The kept item set is chosen by the unchanged selection and budget logic: the rule does not change which skills or memories are selected. Rendering tests: `tests/unit/test_reusable_blocks.py` (`TestPacking.test_order_insensitive`, `TestSkillPath.test_flag_on_deterministic_and_score_independent`, `TestRoutingContext.test_flag_on_stable_across_q_and_order`). Real reuse is measured once live through RTE-LOG-1 (`blocks[]` kinds `skill` and `routing`, written by `src/backends/prompt_layout.py`) and REPL-EMB-6.1. Open follow-ups are CFI-1 (quality A/B) and CFI-2 (memory-k widening to reach 256-token blocks), filed separately below; neither is part of this rule.
- [x] **M-29 — M-23 readout clauses from the skill-reliability dives (one amendment, spec only).** M-23 (above) stays the base spec; this task adds the clauses its first readout must also carry, all descriptive or report-only and none a gate. (1) Per role-model cell print the paired transition counts c (failed skill-off, passed skill-on) and b (passed skill-off, failed skill-on) with an exact two-sided McNemar p on the discordant pairs beside the net delta and the negative-cell share, and report b even when the net is positive (intake-1321#record); promotion stays per-role non-regression. (2) A skill-off REPLICATE arm (same pinned config, independent sampling) so the flip floor of an unchanged condition is measured, with a paired flip counted as a skill effect only if it exceeds that floor; an external replicate-noise figure (intake-2238#record) is an order-of-magnitude prior, never a substitute for measuring on the local served pin. (3) Stratify the transition table by adoption (title echoed or visibly applied, detector fixed before the run). (4) One placebo arm: skill-on with entries swapped for token-matched, task-irrelevant entries of the same format at the same injection point. (5) If a cell reads net-negative (b greater than c) the follow-up is a Bernoulli mask arm over the entries injected in that cell (inclusion 0.5 at retrieval time, mask count from the stated power analysis, per-skill effect with a permutation test); declare the paired-task count and resulting resolution before any per-entry run, and report cell-level only if the populated cell is too small (intake-2229#record, intake-2259#record). (6) Report injected tokens per request and total prompt-plus-completion tokens per request or trace for both arms, and the skill-on minus skill-off delta per 1,000 injected tokens (intake-2288#record, intake-2301#record). (7) Record the role-prompt hash (prompt version id) beside the model pin so a prompt edit splits the cell (intake-2290#record). (8) Label each request general-only or general-plus-specific and, for the latter, by tercile of the top specific entry stored cosine similarity (cut points fixed before the run) (intake-2318#record). (9) Print the skill-off pass rate beside every cell delta and list cells at or above 95 percent skill-off as ceiling-limited, excluded from the negative-cell denominator (intake-2337#record). (10) Record each injected skill source role at distil time and whether the injection was same-role or cross-role, because the retriever has no role term (intake-2333#record). (11) Report write-side cost as LLM calls plus input and output tokens summed over every memory-construction call, judge calls excluded, beside the read-side line (intake-2311#record). The 2026-10-21 text of M-23 is unchanged. Acceptance: the eleven clauses are filed under M-23 verbatim and M-23 points at them; no gate or MEASUREMENT.md text is touched. Estimate: 0.5 day. ✅ 2026-10-21
- [ ] **M-27 — Extend the M-24 lint and M-25 probes with the new read-only classes (zero inference).** M-24 and M-25 are filed and ticked; this adds, each advisory and report-only: (a) lint class for negative-capability claims ("X does not work", "cannot use Y") and for steps whose source trajectory ended without a labelled success, reporting flag rate on the SkillLearnBench corpus and on the first distilled pool (intake-117#record); (b) seed the path, IP, URL and identifier regexes from the NVIDIA SkillEvaluator `pii_patterns.yaml` at its pinned SHA (copy with attribution; do not install or run the tool; add model-name, port and column-name classes locally) (intake-2250#record); (c) pair mode: skills in the same task type whose stored-embedding cosine lies in 0.6-0.85 and whose literal sets differ, count and 10 examples per config (verify embeddings are readable from the backup without running the embedder) (intake-2239#record); (d) M-25 probe additions: top-k source-class composition (interactive, autopilot or eval-generated, cron-like) for a fixed set of recall queries (verify the store carries a source label), the retrieval_count distribution on the pre-purge 57-skill backup against the 5 and 20 floors with the count below effectiveness 0.3 at each floor (intake-2251#record), the source role per skill, and the distillation call and token totals in the pre-distillation checkpoint note. Run under `region-lock run --cpu-list 0-95`. Acceptance: each class has a fixture test and a first report on the pinned corpus; nothing is distilled. Estimate: 2-3 days.
  - 2026-10-21 (fillers-3c4ca599): registered as queue item `s5-m27-live-recall` (block-correctness, NOT armed: bundled into `s5-stackup-bundle`); window-ready job `/mnt/raid0/llm/tmp/fillers-3c4ca599/jobs/m27_job.sh` (subprocess embedder, no ports, real-embedding proof).
  - 2026-10-21 `dpf-skill` NOT ticked. Built: orchestrator `5a92ea4c` (`orchestration/repl_memory/distillation/{memory_probes,pii_seed,literal_lint,pipeline}.py`, `tests/unit/test_memory_probes.py`, 7 fixture tests). First report: [m27_result.json](../../artifacts/dpf-skill-20261021/m27_result.json). (a) negative-capability flags 55 of 1,277 SkillLearnBench skills, 0 of 57 on the backup; 18 of 57 backup skills have a failure source outcome; unlabelled-success is not computable on SkillLearnBench and the first distilled pool does not exist yet. (b) NVIDIA `pii_patterns.yaml` @15adf98f seeded with attribution: 8 of 1,277 SkillLearnBench, 0 of 57 backup. (c) stored vectors readable without the embedder (57 of 57, dim 1024); 416 same-task-type pairs, 357 in cosine [0.6, 0.85), 334 with differing literals, 10 examples in the JSON; SkillLearnBench has no stored embeddings. (d) retrieval_count max 2 so 0 skills reach the 5 or 20 floor; source role unresolved for all 57 (0 of 85 trajectory ids found); episodic rows carry `context.source` (progress_log 4,301, external 28,161, legacy 30,736, seed 1,316) but no interactive or cron label; teacher call and approximate token totals are in the report and `planned_teacher_calls` is in the checkpoint note. Ready for an inference window: the live top-k source-class composition over the 8 fixed recall queries (`memory_probes --live-recall`, needs the query embedder, refuses without `WINDOW_CONFIRMED=1`).
  - 2026-10-27 harvest (s5-m27-live-recall, ended 2026-10-22T10:54Z rc 0): M-27(d) live recall RAN (descriptive composition, no predeclared threshold). 8 fixed queries, k=10, real 1024-d embedder (`use_fallback=False`, norm 1.0 each). Pooled top-80: seed 53 (66%), eval_or_external 13 (16%), pre_label_legacy 8 (10%), autopilot 6 (7.5%). Pollution is concentrated: 5 of 8 queries return 10/10 `seed`; "extract fields from a csv file" is 8/10 eval_or_external; "escalate after repeated failure" is 5 eval_or_external + 1 autopilot + 4 legacy (0 seed); "which role handles long-context summarisation" is 4 autopilot + 2 legacy + 4 seed. `interactive_label_available: false` (no interactive/cron label, so only autopilot vs eval vs seed is separable). Evidence `/mnt/raid0/llm/tmp/fillers-3c4ca599/out/m27-live-recall.json` (+ `m27-linkage.txt`). [belief: cc]
  - 2026-10-28: M-27(d) top-k source-class composition (k=10, 8 queries; pooled seed 53 / eval_or_external 13 / pre_label_legacy 8 / autopilot 6) vs no predeclared rule (descriptive; the FILLERS row says only that it 'decides whether recall is polluted') → correctness-only (diagnostic observation; embedder proof use_fallback=False). Box M-27 stays unticked: parts (a)(b)(c) and the rest of (d) are not delivered by this run. Evidence: /mnt/raid0/llm/tmp/fillers-3c4ca599/out/m27-live-recall.json. [belief: cc]
  - [ ] **M-27d.1 — add an interactive/cron source label to the episodic write path, then re-run the 8-query composition.** 3 of 8 queries return non-seed rows (up to 8/10 eval_or_external) and the store cannot separate interactive from autopilot; decide whether eval/external rows belong in the default recall pool or behind a `context.source` filter (retrieval-side change needs a flagged A/B, not a silent filter). Filed 2026-10-27 harvest.

## Research Intake Update — 2026-10-21 (harness cluster, DP-F amendment)

Operator-approved Stage-3 amendment (plan sha256 2edfb0662f61e1254e7dc5e2b21888ef4f19df800a283e82b25caebeb6644746). Durable records only: no checkbox, no index next action. Each monitor row carries its trigger and first step; each knowledge row states what to rely on. Ledger ids (DPF-...) key to the Stage-3 recommendation mapping preserved in `.research-session.json` (`stage3_filing`).

### K10 — Skill reliability, SkillBank, memory and skill-format evidence

- DPF-117-117-06: Hermes [memory implementation](https://github.com/NousResearch/hermes-agent/blob/369cc6b07f26f4454f56555f1001ea9eb7d8d948/tools/memory_tool.py#L1-L12) freezes the memory/profile snapshot into the prompt at session start. Treat this as a cache-oriented implementation pattern, not evidence of improved task outcomes.
- DPF-117-117-07: Hermes [background review](https://github.com/NousResearch/hermes-agent/blob/369cc6b07f26f4454f56555f1001ea9eb7d8d948/agent/background_review.py#L1-L12) forks a conversation snapshot to propose memory/skill updates. The current dive found count-triggered updates without an outcome signal; this mechanism is not evidence that a proposed skill helped.
- DPF-1321-R6 (intake-1321): A scorer that fails an answer it cannot evaluate: 226 of 663 failing formula tasks were already correct (34%).
- DPF-1321-R7 (intake-1321): Reference paired protocol: exact McNemar on discordant pairs, Newcombe CI, Bonferroni over simultaneous cells. Newcombe CI [+0.2,+18.9] coexists with exact p=0.078 (15 gains, 6 regressions).
- DPF-1321-R10 (intake-1321): Cross-reference to 2605.23899 (intake-2190): same prior, different measurement. 2190: 37/150 net-negative cells, mean +2.29 pp, 3-run averaged. 1321: 18/18 net-positive cells, 324 task-level regressi…
- DPF-W1-AGENTSKILLS-AG-03 (intake-2226): Guide advice to protect skill content from context compaction and to deduplicate activations.
- DPF-W1-AGENTSKILLS-AG-04 (intake-2226): Eval guide has no paired statistic or replicate floor; M-23 (McNemar c/b, R2 replicate arm) is strictly stronger.
- DPF-W1-ASSAY-A2 (intake-2229): The 'over 90 percent heterogeneous' headline is noise-compatible (null FPR ~100 percent in the paper's own Table 9).
- DPF-W1-ASSAY-A4 (intake-2229): Main-table 'Ours' rows include hand-written protected templates worth +6.0 pp that the compared methods lack.
- DPF-W1-ASSAY-A5 (intake-2229): Randomized masking is the controlled intervention the intake-1321 dive says is needed to separate osmosis from presence (observational labels are not enough).
- DPF-W1-GRASP-G2 (intake-2236): Matched-compute control: run the whole probe but discard the verdict (select by proposer preference or at random) reaches only 70.8/67.2 vs 88.8 with the verdict used.
- DPF-W1-GRASP-G3 (intake-2236): Each epoch/batch accept is a look on a 36-example probe (18 positives); median accepted margin is 3 examples; no multiple-comparison correction; permutation p floor 0.10 at 3 seeds.
- DPF-W1-GRASP-G4 (intake-2236): Frozen libraries written by a stronger model lift weaker executors OOD (+21.5, +29.4); weaker-writer libraries applied to stronger executors are worse than self-training; libraries degrade under inte…
- DPF-W1-GRASP-G6 (intake-2236): Ground-truth audit of all 106 learned libraries against held-out answers; the gate consumes only pass/fail so cannot encode answers.
- DPF-W1-HONCHO-HN-03 (intake-2237): Honcho deletes outdated observations; EPYC UTM keeps superseded/previous_event_id lineage.
- DPF-W1-HUANG-DS-SKILLS-H1 (intake-2238): Fourth independent datum that generated flat skills net about zero with near-equal help and hurt (20 vs 19) and 4.5x tokens.
- DPF-W1-HUANG-DS-SKILLS-H4 (intake-2238): A user-message 'task overrides skill' sentence is a tradeoff (12 recovered, 8 new failures), not a free guard.
- DPF-W1-HUANG-DS-SKILLS-H5 (intake-2238): Only 17 of 56 tasks are in the informative 30-80 percent baseline band; ceiling/floor tasks dilute aggregates.
- DPF-W1-ID2606-10388-RF-04 (intake-2239): v1 SkillResolve zero-exposure result is withdrawn by v4.
- DPF-W1-RSEA-E1 (intake-2248): Two-tier acceptance: lateral moves allowed for the working state, strict improvement required to replace the frozen best, empty-state fallback so the delivered artifact is never worse than baseline o…
- DPF-W1-RSEA-E2 (intake-2248): Gate's own test benefit is 0.6 pp against a 33-point in-sample/test gap; the gain claimed for the gate is mostly the avoided catastrophic comparator.
- DPF-W1-RSEA-E3 (intake-2248): Unguarded online curation (Dynamic Cheatsheet) collapses WebShop 0.136 vs 0.429 and is worst on tau-bench on a 30B-A3B backbone.
- DPF-W1-SKILLCLAW-S2 (intake-2249): The validator is an LLM comparing candidate vs deployed outcomes; Qwen3-Max plays executor, evolver and validator.
- DPF-W1-SKILLCLAW-S3 (intake-2249): Evolution and scoring share the same 60 benchmark tasks; displayed scores are carried-forward best-pool values; no repeats or CIs.
- DPF-W1-SKILLCLAW-S4 (intake-2249): Accepted updates on nights 1-4 left the Safety category at 24.00 percent until Day 5: validator-accept did not translate into a user-side gain.
- DPF-W1-SKILLEVAL-SE-01 (intake-2250): M-24 supplier premise overturned: SkillEvaluator has no prose literal-constant lint.
- DPF-W1-SKILLEVAL-SE-03 (intake-2250): Activation-gated lift (INCONCLUSIVE when the skill never activated) is a shipped example of the adoption stratification in the 1321-dive R3.
- DPF-W1-SKILLEVAL-SE-05 (intake-2250): Tier 2 pair classification bands and a fully local embedding+chat recipe.
- DPF-W1-SKILLGRAPH-SG-01 (intake-2251): Success statistic credits every retrieved skill (Appendix A.3), the retrieval-time correlation that SkillBank effectiveness_score (skill_bank.py:93 "Post-retrieval outcome correlation") also uses; bo…
- DPF-W1-SKILLGRAPH-SG-06 (intake-2251): Integrity findings: flat-library control equals SkillRL row; Table 2 Avg disagrees with rows; v1->v2 headline moved 2.5 points with CI appendix removed.
- DPF-W2-AGENTSKILLS-AG2-02 (intake-2253): No src importer of skill_hub_interop: deviation is latent.
- DPF-W2-AGENTSKILLS-AG2-03 (intake-2253): Spec text does not say unknown keys are errors; the allow-list is the reference validator behaviour (demo-only per README).
- DPF-W2-COALITION-C1 (intake-2259): An outcome-only (aggregate) gate cannot say whether an accepted bank hides a harmful member: worked case admitted a -0.005 skill on a +0.006 margin, while the real carrier (insert) lost most of its m…
- DPF-W2-COALITION-C5 (intake-2259): Cross-domain reversal of a source-positive member (+0.084 to -0.035) with a target CI that includes zero.
- DPF-W2-COALITION-C6 (intake-2259): K-controlled additions net -1.38 pp but with opposite sign on LongMemEval (+2.48): bank-level sign is a distribution across benchmarks even inside one system.
- DPF-W2-GRASP-GR-03 (intake-2266): Gate uses strict improvement over 0 net gain and non-strict regressions; no variance term, no multiple-look correction (rolling cycles).
- DPF-W2-GRASP-GR-04 (intake-2266): Tool-output cache removes environment noise but not LLM noise.
- DPF-W2-SKILLS-EVAL-SE2-02 (intake-2287): Static lint scores do not rank live skill value (62 skills, CIs wide).
- DPF-W2-SKILLS-EVAL-SE2-04 (intake-2287): Headline CI ignores clustering; replicates thin (88/201 cells have 2 trials); composite includes process metrics baseline cannot earn.
- DPF-W2-SKILLS-EVAL-SE2-05 (intake-2287): Missing-trajectory imputation sensitivity (0.2153 to 0.1840).
- DPF-W2-SKILLSDONTDELP-S1 (intake-2288): Power: n=45 per arm cannot resolve +8.9 pp (about 288 runs per arm needed); the paper reports this as a resolution limit, not a zero.
- DPF-W2-SKILLSDONTDELP-S4 (intake-2288): Reading rule: the abstract says skills 'degrade' where the paper's own table shows the no-skill arm at 0/3; always check a 'degrades' claim against the baseline arm, not against another skill arm.
- DPF-W2-SKILLSDONTDELP-S5 (intake-2288): 'False lesson propagation': a lesson distilled from a few trajectories is applied in a context it does not fit and biases the agent (symbolic execution on a side-channel task).
- DPF-W2-SKILLSDONTDELP-S6 (intake-2288): Experiential (self-distilled) condition +4.4 pp, not significant, beside SkillsBench self-generated -1.3.
- DPF-W2-SKILLSVOTE-V3 (intake-2289): Responsibility classes per subtask (skill-guided, independent exploration, exploration after an irrelevant skill, environment, result signal) judged by an LLM, with no accuracy validation reported.
- DPF-W2-SKILLSVOTE-V4 (intake-2289): Evaluation quality: no CIs, single rollout on SWE-Bench Pro, online gains +0.9 to +2.7 pp, negative Hard split, verifier paths visible to offline attribution.
- DPF-W2-SKILLSVOTE-V5 (intake-2289): Recommender capability limit: GPT-5.4 mini loses at 50k and full pool; agentic search needs a capable model per task.
- DPF-W2-SKVM-K1 (intake-2290): Regression share rises as the model weakens (7 percent Opus 4.6 to 25 percent Qwen3-30B; original skill worse than none in 11 of 14 categories on Qwen3-30B + BareAgent): local pins sit at the weak en…
- DPF-W2-SKVM-K5 (intake-2290): Recompile only on systematic failures across invocations; roll back if worse; restart from the best variant so far.
- DPF-W2-SKVM-K7 (intake-2290): Concurrency extraction and a resource-aware scheduler (throttle launches, suspend running sub-agents under pressure, reuse last effective concurrency).
- DPF-W2-SKVM-K8 (intake-2290): Environment binding: extract a dependency manifest, presence-check, emit an idempotent repair script, fall back to the model.
- DPF-W3-DEMYSTIFYING-D1 (intake-2301): Rival-mechanism check: skills mainly act as procedural anchors (65.7 percent) not knowledge injection (4.5 percent), and their measurable effect is fewer execution-layer failures. The benefit over ra…
- DPF-W3-DEMYSTIFYING-D2 (intake-2301): Skills create their own failure surface: misapplied or ignored guidance in 10.0 percent of skill cases vs 0.8 raw; workflow memory instead times out (10.6 percent).
- DPF-W3-DEMYSTIFYING-D3 (intake-2301): Failure-only source pools make the skill arm worse than raw in 6 of 6 cells (e.g. Codex Terminal-Bench-2 0.5161 vs 0.5935); one success restores it. Independent of the SkillLearnBench datum behind M-…
- DPF-W3-DEMYSTIFYING-D4 (intake-2301): Outcome labels during skill creation matter once failures are in the pool (0.7462 vs 0.4000 at 3s2f); success-only pools do not need them.
- DPF-W3-DEMYSTIFYING-D6 (intake-2301): Retrieval precision collapses with pool size (29.6 to 3.3 percent) while success stays flat; exact ground-truth use is neither necessary nor sufficient.
- DPF-W3-DEMYSTIFYING-D8 (intake-2301): Evidence quality: the one significant contrast is skill vs workflow memory; skill vs raw spans zero; labels are single-judge; same-task replay.
- DPF-W3-MEMSKILL-MS1 (intake-2311): Acceptance of a skill-bank update is a best-so-far ratchet on the mean of the last 25 of 100 training-step rewards, no margin, no held-out set: a maximum over noisy tail means, which is upward biased…
- DPF-W3-MEMSKILL-MS2 (intake-2311): Headline gains are unresolved: LoCoMo test is about 2 of 10 conversations, LongMemEval about 100 samples, no seeds or intervals, and the same method moves 5.7 L-J points across five span sizes (48.11…
- DPF-W3-MEMSKILL-MS3 (intake-2311): Memory is not monotone-good: on ALFWorld four of seven memory baselines score below the No-Memory row (61.77 to 67.25 vs 68.01); the sign of memory benefit is a distribution here too.
- DPF-W3-STRIATUM-T1 (intake-2314): Primary counts for the 180 runs (n=45 per condition) with Wilson intervals computed here: all four conditions overlap heavily; Lessons minus Minimal is +4.4 pp with a half-width near 16.5 pp.
- DPF-W3-STRIATUM-T2 (intake-2314): "False lesson propagation" is not in this paper; wave-2 dive-surfaced reason for ingesting it is wrong on this point.
- DPF-W3-STRIATUM-T3 (intake-2314): Documentation size versus return: 4,147 lines vs 55 lines buys +8.9 pp (unresolved) and 3 minutes of solve time.
- DPF-W3-WILD-W1 (intake-2318): Same skills, three models, three different last-rung signs (+3.0, -2.0, -0.8 pp vs no-skill); the paper reads it as stronger models ignoring bad skills better. No intervals.
- DPF-W3-WILD-W2 (intake-2318): Loading rate and benefit decouple: 49 percent load all curated skills; Kimi loads 86 percent with no gain over forced loading.
- DPF-W3-WILD-W5 (intake-2318): Query-agnostic offline refinement (improve each skill alone with synthetic tests) gives small inconsistent gains (+1.9 and +1.9 Claude, -0.5 and +4.9 Qwen).
- DPF-W3-WILD-W6 (intake-2318): Agentic multi-query retrieval beats a single direct query by 18.7 Recall@3 points over a 34k pool, but needs a strong model per task.
- DPF-W3-WILD-W7 (intake-2318): No intervals or replicate floor on any pass rate; a +3.0 pp last-rung gain at 84 tasks by 3 runs is unresolved.
- DPF-W4-PROCMEM-PM1 (intake-2333): Static skill datum on small local-family models: handcrafted skill below no-skill for 4 of 13 models, generated skill below for 1 of 13; headline +2.8 is best-of-two. Closest fleet analogues: Qwen 3.…
- DPF-W4-PROCMEM-PM2 (intake-2333): Narrow n=1 vs diverse n=5 evolution on a Qwen 3.5-35B-A3B solver: large train gain, no held-out gain for narrow; the arm structure is the seed-set-size arm already in M-25(c).
- DPF-W4-PROCMEM-PM6 (intake-2333): Total tokens: evolved skill cut total tokens 62 percent (Claude) and 16 percent (Hermes) vs handcrafted on one task; across Table G.1 the no-skill arm sometimes uses more total tokens than handcrafte…
- DPF-W4-PROCMEM-PM7 (intake-2333): Evidence quality: 75 percent of tasks LLM-drafted, best-of-two delta, M1/M2 caption conflict, n=3 held-out in the reflector ablation, figure-only transfer numbers.
- DPF-W4-SWE-SW1 (intake-2337): Coding-skill sign datum: 39 of 49 skills exactly zero, mean +1.2 points, single model and scaffold, about 10 tasks per skill, no intervals. One task is a 10-point step, so the three negative skills a…
- DPF-W4-SWE-SW3 (intake-2337): Total tokens move independently of correctness in both directions (rho -78 to +451 percent at delta zero); cost-efficiency ratio CE = delta/rho is ill-posed: springboot-tdd and django-patterns score…
- DPF-W4-SWE-SW4 (intake-2337): Harm mechanism: a near-match template with different literal values (API version, protocol, auth modes) anchors the agent: surface anchoring, hallucinated field, concept bleed. Single qualitative cas…
- DPF-W4-SWE-SW5 (intake-2337): Abstract and body disagree on the cause of the three losses (version mismatch vs scope mismatch); only linkerd is shown to involve version values.
- DPF-W4-SWE-SW6 (intake-2337): Verifier validity: tests are derived by an LLM from the requirement document with a fixed test-engineer prompt; the text read reports no human validation of the verifiers.
- DPF-W4-TIDE-TD4 (intake-2338): Post-hoc operation without re-execution: metrics computed from recorded interaction logs of other labs.
- DPF-W4-TIDE-TD5 (intake-2338): Name collision: handoffs/active/reasoning-compression.md refers to a "TIDE post-mortem" for an unrelated early-exit project.
- DPF-W4-TIDE-TD6 (intake-2338): Evidence quality: games and web environments, difficulty confound in loop pools, horizon-dependent AUV, no intervals.

### M18 — SkillBank follow-on arms waiting on a populated bank or a net-negative cell

- DPF-117-117-08: Hermes [skill ledger](https://github.com/NousResearch/hermes-agent/blob/369cc6b07f26f4454f56555f1001ea9eb7d8d948/tools/skill_ledger.py#L1-L12) explicitly describes telemetry, not a gate; [curator invariants](https://github.com/NousResearch/hermes-agent/blob/369cc6b07f26f4454f56555f1001ea9eb7d8d948/agent/curator.py#L1-L10) retain recoverable archives. A fail-closed mutation ledger is our prospective requirement, not an upstream guarantee. — Trigger: first reviewed skill export through B3 (hs4 doc 3.7) or any autonomous prompt-mutation write path in PromptForge; at that point require content-addressed before/after records and test single-edit rollback.
- DPF-117-117-09: The current intake-117#record narrows the earlier self-improvement description; it does not establish an outcome benefit. — Trigger: upstream or intake-327 (hermes-agent-self-evolution, DSPy+GEPA) publishes an outcome-based skill evaluation; inspect that evidence before adopting an efficacy claim.
- DPF-1321-R8 (intake-1321): The Claude Code dev harness carries ~60 resident skill descriptions; the paper libraries had 3-23, and no EPYC outcome-level evidence exists. — Trigger: an EPYC A/B or audit measures task outcomes with/without resident skill descriptions in the dev harness, OR agent-file-prose-compression reports a token-cost result. Then run the three-arm design (none / descriptions only / descri…
- DPF-W1-AGENTSKILLS-AG-02 (intake-2226): Description-optimization protocol (3 runs per query, 0.5 threshold, 60/40 split, pick by validation) matches the PromptForge held-out discipline and gives a trigger-rate measurement for resident desc… — Trigger: the R8 trigger fires (dev-harness resident-description A/B). Then use trigger rate with the R2 replicate floor.
- DPF-W1-ASSAY-A3 (intake-2229): Per-task suppression conditioned on nearest development tasks (removal-only, protected skills, fallback to full library; fallback fires on 21 percent of tasks, cosine coverage 0.47-0.58). — Trigger: an M-23 cell reads net-negative AND the A1 attribution names at least one skill with a stable negative per-task effect. Then spec a retrieval-time suppression list with the full-library fallback. No task now.
- DPF-W1-ASSAY-A6 (intake-2229): Offline split of heterogeneous skills into conditional variants with a dev gate (pass rate >= original on all attribution tasks). — Decline: the orchestrator entry already carries when_to_apply; the LLM split reintroduces judgment (the paper says so), and the gate is a no-worse-on-15-tasks check with no power. Revisit only after A1 produces a named negative skill.
- DPF-W1-GRASP-G5 (intake-2236): Capacity-bounded library with ADD blocked at capacity unless paired with REMOVE; 5 skills / 5.6k tokens vs 34-53k for unbounded memories. — Trigger: the first populated SkillBank A/B reports (M-11a/M-12). Then compare the retrieval top-k injection against a capacity-capped bank with a paired REMOVE rule as an arm. No task now.
- DPF-W1-HONCHO-HN-04 (intake-2237): Surprisal-sampled dream cycles and five-level dialectic query depth (cost tiers). — Trigger: HS-4 P2 profile-on arm is scheduled; then consider a cheap level-0 query path. Surprisal code read only at the head.
- DPF-W1-HONCHO-HN-06 (intake-2237): Honcho benchmark harness (LongMemEval, LoCoMo, BEAM, OOLONG) as a reference runner for memory systems. — Trigger: CME-5 accepted with a compute window; compare its BEAM runner against ours then.
- DPF-W1-HUANG-DS-SKILLS-H6 (intake-2238): A generic Reference Note (forward-fill rule) outranks a task-specific instruction: over-general default rules, not literal constants, cause the harm. — Trigger: the M-24 calibration table is built and a human review of flagged and unflagged SkillLearnBench skills finds default-value imperatives. Then add them as a second, advisory flag class. No task now.
- DPF-W1-ID2606-10388-RF-02 (intake-2239): CleanHit@K (helpful present AND conflicting sibling absent) as the retrieval co-metric beside recall for the SkillBank A/B. — Trigger: M-24 pair census (RF-01) finds >0 conflicting pairs; then add CleanHit to the M-23 per-cell report.
- DPF-W1-ID2606-10388-RF-03 (intake-2239): Truncation makes sibling pairs identical to a 512-token reranker; SkillBank entries (title, principle, when_to_apply) are far below 512 tokens. — Trigger: first B3 export of SKILL.md folders with long bodies into a retriever with a token budget; check pair distinguishability at that budget.
- DPF-W1-ID2606-10388-RF-05 (intake-2239): Benchmark bundle github.com/jdding/SameCapRisk with CPU evaluator. — Public pools of 7.6k skills in code/math domains; no consumer until RF-01 finds exposure. Operator may override.
- DPF-W1-SKILLCLAW-S1 (intake-2249): Sessions grouped by referenced skill with a separate no-skill group give a natural-ablation readout of per-skill outcomes without a dedicated experiment. — Trigger: M-23 logging exists and a populated bank has run. Then add an exploratory, clearly-confounded table (retrieval selection and osmosis confound it, per intake-1321) of outcome by skill_id group vs the no-skill group. Not a decision…
- DPF-W1-SKILLCLAW-S5 (intake-2249): An explicit 'skip' action when evidence is insufficient, plus conservative editing that preserves behaviours validated by successes. — Trigger: M-11a is opened by its owner. Then list 'skip when evidence below N sessions' as a candidate arm beside the dedup variants. No task now.
- DPF-W1-SKILLEVAL-SE-04 (intake-2250): unicode_smuggle_patterns.yaml (tag characters, BiDi, zero-width) as an import guard; B3 scan_skill has six regexes and none for hidden characters. — Trigger: first reviewed SKILL.md import or export through B3; then add a hidden-character scan using these ranges.
- DPF-W1-SKILLGRAPH-SG-03 (intake-2251): Dependency-ordered injection (prereq edges + topological order). Largest effect (ALFWorld -33.7) is on rigid household chains with an RL-trained policy; no evidence for orchestrator tasks or local pr… — Trigger: the first SkillBank A/B (M-23) reports a role-cell regression AND the M-24 calibration shows >=10% of distilled skills reference a precondition step. Then test ordered vs unordered injection as one extra arm.
- DPF-W2-ASSAY-AS2-01 (intake-2229): re-check repo URL later
- DPF-W2-COALITION-C3 (intake-2259): CASS scores sampled coalitions (sizes 1..k) rather than single members, so antagonistic or synergistic pairs show up (joint loss differs from the sum of single margins). — Trigger: a champion promotion bundles two or more mutations and the aggregate gain is positive with no member-level readout. Then add a report-only sampled-coalition knockout arm (coalition size up to 3, N fixed in advance). No task now; C…
- DPF-W2-COALITION-C4 (intake-2259): Label-free deployment screen: score each member by whether removing it improves retrieval locality (mean cosine of top-k memories to unlabeled target queries) and mask the worst. — Trigger: A1 names no stable negative entry because the paired budget is unaffordable AND the bank is populated. Then compute the cosine-locality score for each entry over a role's unlabeled queries (read-only, CPU embedding pass) and check…
- DPF-W2-SKILLS-EVAL-SE2-03 (intake-2287): Paired design with fixed non-target decoys separates content from routing (isolation vs group, routing premium). — Trigger: M-23 bank populated and a role-cell reads net-negative. Then add isolation-vs-group arms.
- DPF-W2-SKILLSDONTDELP-S3 (intake-2288): Feedback-bandwidth moderator H1: benefit shrinks where the environment returns dense, deterministic, typed feedback (coder with test verifier, REPL typed outputs) and grows where feedback is sparse (… — Trigger: the first populated M-23 readout. Then tag each role cell dense or sparse verifier (a fixed pre-run label) and report whether /delta/ differs, as hypothesis-generating only (four roles cannot test it). Caveat: unverified, a ceilin…
- DPF-W2-SKILLSVOTE-V1 (intake-2289): Exposure control: a task-conditioned selection step in front of the injected set moved library exposure from net -3.4 to 0.0 (Hard 30 tasks, no noise floor); offline library +11.3/-3.3 to +15.3/-2.0. — Trigger: M-23 reports a net-negative role cell. Then add an exposure-set arm label (retrieved top-k vs random-k from the same bank vs all-resident), report-only, same bank and same tasks, so a negative cell can be split into 'wrong entries…
- DPF-W2-SKILLSVOTE-V2 (intake-2289): Admission only from successful subtasks with reusable exploration; failures never authorize an update (diagnostic only). — Trigger: the first M-11a re-distil is scheduled. Then add 'admission by outcome class (success-only vs mixed)' as one more arm label beside seed-set size, reported from the counts M-25(b) already surfaces. Design point only; the paper has…
- DPF-W2-SKILLSVOTE-V6 (intake-2289): Profiling rubrics (runtime requirements, write scope read/workspace/system, externality offline/online/secured, quality consistency/completeness/orientation, verifiability). — Trigger: the M-24 calibration table exists. Then consider write-scope and externality as two advisory flag classes for distilled entries that name ports, hosts or credentials. No task now.
- DPF-W2-SKVM-K3 (intake-2290): Target capability profile by microbenchmarks (26 primitives with levels; 7-31 min per model) compared with each skill's required levels to pick a transform. — Trigger: M-23 reads a net-negative cell for one pin with low adoption. Then, as a separate owner-approved inference task, profile that pin on a handful of primitives (tool.exec, follow.procedure, gen.code.shell) and tag the cell's entries…
- DPF-W2-SKVM-K4 (intake-2290): Per-target compiled variants (compensation: add examples, make instructions explicit, absolute paths) selected at runtime by the (model, harness) pair. — Trigger: K3 identifies a pin-specific gap. Then add 'per-pin rewrite (compensation only) vs raw' as an arm label. Gains unmeasured without variance; borrow no number.
- DPF-W2-SKVM-K6 (intake-2290): Promotion gate for code solidification: promote only after the signature matches on consecutive invocations, fall back to the model on any failure; weather-forecast never promoted. — Trigger: the trace store holds REPL code generations for one role. Then run a read-only count of near-identical code templates with parameter slots (signature classes) to size the solidification opportunity before any build. No task now; t…
- DPF-W3-DEMYSTIFYING-D7 (intake-2301): Compact controls (short instruction-derived plan 47.7, test-first template 59.2) do not match the skill (79.2) on 26 tasks; any-procedural-text is not the explanation. — Trigger: the H3 placebo arm is run and skill-on is indistinguishable from the placebo. Then add a relevant-but-generic scaffold arm (a role-level checklist of the same length). No task now. The 26 tasks were selected for mixed raw outcomes…
- DPF-W3-MEMSKILL-MS6 (intake-2311): Public repo ships eval scripts for LoCoMo and LongMemEval (span 512, API or local vLLM, base_url client) and two released skill banks. — Trigger: M6 fires (CME-5 accepted and a window granted). Then record MemSkill (repo f65b7973) as a candidate LoCoMo/LongMemEval comparator, to be run only as a baseline arm with a replicate floor. No task now.
- DPF-W3-STRIATUM-T4 (intake-2314): Typed tool schemas alone (Minimal) already give 77.8 percent: consistent with a dense-typed-feedback explanation (S3 / H1), but no arm removes the schemas, so it cannot support it. — Trigger as for S3 (first populated M-23 readout). Record as consistent-but-untested; do not count it as evidence for H1.
- DPF-W3-WILD-W4 (intake-2318): Query-specific refinement (explore the task, then rewrite and merge retrieved skills) buys +8.1 pp for Claude but costs a full extra exploration pass per task and lost 6.8 pp for Kimi when its self-e… — Trigger: the M-23 readout names a net-negative role cell AND the bank is non-empty. Then consider a report-only arm in which the role's own served model rewrites its retrieved entries before use, accounted with the write-side cost line fro…
- DPF-W4-PROCMEM-PM3 (intake-2333): Pool source mix: skills evolved from a pool mixing several source models transfer better than any single-model pool, and weaker source models transfer better than stronger ones (figure-only evidence). — Trigger: the M-11a re-distil is scheduled AND the pool probe shows at least two model_ids with enough successful rows each. Then add a pool-source arm (single model_id vs mixed) to the arm labels, report-only. Build cost: the model_id colu…
- DPF-W4-PROCMEM-PM5 (intake-2333): Evolution harness shape: versioned skill with parent link, rejected candidates kept as inactive branches, promotion only if validation improves by margin delta, rollback, named snapshots; adapter ide… — Trigger: UTM-R1 or the M-11a re-distil is scheduled to run. Then add a promote-only-if-validation-margin variant as an optional arm. Build cost: a validation split per role-skill cell and a margin check in the supersession path, about 1.5…
- DPF-W4-PROCMEM-PM8 (intake-2333): Run AFTER on our own worker models: static arm (no skill / handcrafted / generated) is a single generation per task plus pytest, which a local llama-server can serve. — Trigger: operator picks it up post-cap. Build cost: download the HF dataset (task JSON and inputs only; no executable is run until sandboxed), a runner that calls the worker llama-server once per task and condition (about 1 day), a pytest…
- DPF-W4-SWE-SW7 (intake-2337): Reuse the paired design on our fleet: the same 49-skill x 11-task suite run with a local model injecting SKILL.md by the orchestrator (cosine retrieval, no load decision). — Trigger: the first M-11a re-distil populates a bank AND the M-23 readout shows a coding-role cell at ceiling or negative. Build cost if triggered: replace the Claude Code file-injection with an orchestrator-side injection hook (about 1 day…
- DPF-W4-TIDE-TD3 (intake-2338): Memory Index needs a history-on vs history-off re-run; positive in partially observable, negative in fully observable tasks; benefit plateaus near 5 turns. — Trigger: a section 3.6 compaction A/B is scheduled. Then add a window-size sweep arm (last k turns, k in 1, 3, 5, 10, all). Build cost: a k-turn truncation switch in the context assembler, about 1 to 2 days, plus the inference window later…
