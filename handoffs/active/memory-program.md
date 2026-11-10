# Episodic Memory Integrity — 2026-07-05 corruption, root cause and repair

> **Fold destination** (BRF-T7-F14, BRF-T7-1, route 1b, 2026-11-03): every former handoff of this plan target is a `## Track:` with its own gate marker: `memory-program`, `dev-harness-trace-mining` (rows EVL-52 retired into EVL-10). The former `memory-program.md` body is `## Track: memory-program`; tracks those handoffs already had are lifted verbatim after their owner.

> **Fold destination** (BRF-T1-F24, BRF-T1-1, route 1a, 2026-11-02): renamed from `episodic-memory-integrity.md`; absorbs 2 handoff(s) as `## Track:` sections at the end of this file (`repl-session-memory-maturity.md`, `unified-trace-memory-service.md`). The body above the first track is the former `episodic-memory-integrity.md`.

**Scratch**: `/mnt/raid0/llm/tmp/codex-ni06-main-20261006/` (NI08 record-design review). Historical NI07 integration source is preserved by APP commit `b87998e3b5a0cbb9da36c8db9fd2fcfbb69aba0d`; the completed task no longer depends on its throwaway checkout.
**Status**: active — **CLEARED FOR SEEDING (M-18 full-surface audit, 2026-07-28; semantic gate
verified live 2026-07-29).** Write path FIXED and proven self-healing in production; reseed DONE;
standing integrity gate (M-17) blocks AutoPilot on a broken store and runs in `health_check.sh`.
The degenerate-vector guarantee extends to **every** store via `FAISSEmbeddingStore.add()`
(episodic, SkillBank, StrategyStore — commit `82fbf276`). Live state 2026-07-29: episodic
`ntotal=58749 desync=0` (HISTORICAL, superseded 2026-11-09: 08-09 reseed, see the audit refresh below), round-trip 500/500, degenerate 0/500, **semantic self-match mean
cosine 0.9824 over 8 samples** (0.5505 during the incident); strategy store 1424/1424/1424
coherent, 0 degenerate; skills a clean post-purge slate. Remaining items are follow-on analysis
(M-15), the re-distil (M-11a, inference-gated), and the never-run A/B (M-12).
**Created**: 2026-07-27
**Priority**: HIGH — this subsystem underpins routing, MemRL and SkillBank
**Categories**: agent_architecture, memory_augmented, routing_intelligence
**Parent index**: [research-evaluation-index.md](research-evaluation-index.md)
**Related**: [learned-routing-controller.md](routing-program.md#track-learned-routing-controller) (EPD-1/2/3 label defects),
[standardized-stack-update-pipeline-finalization.md](stack-lifecycle-program.md#track-standardized-stack-update-pipeline-finalization)
(SS-BENCH-GATE)

## 2026-11-09 audit refresh

*Premise reset.* The stack has been off for a long time and no traffic is flowing; Autopilot is on operator HOLD (last true run 2026-08-09T19:29Z, trial 1503). The goal is to have the stack running by end of November 2026; a new era will be set up for the relaunch. Every box below that said "let real traffic accumulate" now reads "after the stack is back and traffic is flowing, or via a non-traffic path".

- **Store state (verified read-only 2026-11-09).** First full re-embed: M-10, receipt `20260727T220715Z`, 58,281 rows. **Second full re-embed (was unrecorded): `reseed_episodic_store_20260809T160329Z`, state `published`, 63,786 rows embedded, ntotal = id_map = 63,786** (`orchestration/repl_memory/sessions/reseed_episodic_store_20260809T160329Z.receipt.json` in the orchestrator repo; six earlier same-day attempts are stuck in `backups_complete` and left ~5-6 GB of backups; deleting them needs operator confirmation). Live store now: **64,514 rows** (732 written after the reseed), read-only, **last write 2026-10-03T03:48**, zero writes since. Alignment was checked structurally only (sizes/row counts); the integrity check needs the embedder and was not run.
- **The next full re-embed is NOT owned here:** it is the EG2 swap (REPL-EMB-2.x in `harness-program.md`), with EPD-3 (`routing-program.md`, drop `priority` from `MemoryRecord.embedding_text()`) folded into it by operator decision so the store is re-embedded once. See the pointer box after M-15. No box in this handoff re-embeds.
- **Index row `Next action` was stale.** M-12i was declined and merged into M-12f on 2026-11-03. The real next action is the M-12f scoring-validity write-up; it is a model-free offline re-score and needs NO bench release and NO exclusive claim.
- **Doable now (no compute):** M-12f write-up, M-12c checklist, M-15, M-19, CFI-2, M-20 code, M-27d.1, D-f2, D-g..D-RI design and code, UTM-V1/V2, DHM-8/9/11 proposals (hook edits need D9 ack; check in-flight edits first).
- **Needs an inference window (not Autopilot):** M-11a, M-12 and children, M-12k, CFI-1, D-RI-PREVIEW-1.1 re-run, UTM-V3 semantic/V4/V6, DHM-5.2. **Needs the stack/API up:** D-f1, D-c1. **Needs a profile store:** UTM-V7.
- Anchor fixes this pass: `compute_chronological_awareness_score` is `scripts/benchmark/tulving_episodic_adapter.py:543`; `_recall` is `routing.py:93`, `_route_advice` `:339`.

## Track: memory-program
<!-- gate: none -->

> Folded from the body of `handoffs/active/memory-program.md` (row EVL-10), from its first `##` section on, @ `ec0a9febab21` on 2026-11-03 (BRF-T7-F14, route 1b, operator D1/D5). Headings demoted two levels; every box kept its text and ID.

#### Objective

The episodic store's vector resolution was silently corrupt from **2026-07-05T15:01:12**. Find the
root cause, repair the data, make the failure mode self-correcting, and put every write site on one
record contract so it cannot recur.

#### Root cause — one bug, three symptoms

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

#### Tasks

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

        > **2026-11-09 premise update:** no traffic is accumulating (stack off; last episodic write
        > 2026-10-03; Autopilot on HOLD). The accumulate-then-propose path cannot fire before the stack is
        > back (target: end of November 2026). The readiness threshold is already met on the existing pool
        > (M-25 measured 6,237 post-reseed rows, 5,452 at q>=0.7, 99.9% success) but that pool is
        > eval/external-dominated. The non-Autopilot path `seed_skills.py --teacher claude` needs no traffic
        > and no Autopilot; it is an inference-class run (teacher calls), not HOLD-blocked.
        > **Decision needed (operator):** (a) distil now from the existing 99.9%-success eval/external pool
        > via `--teacher claude`; (b) wait for real traffic after relaunch. Recommendation: (b) for the
        > headline bank (the pool has no failure signal and holds 200-char stubs), but (a) is acceptable as
        > a labelled pilot (M-25 arm labels) if a bank is needed earlier for M-23/VB-SKILLBANK-AB-WRITE.

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
        the first re-distil is best run after real traffic accumulates (once the stack is running again; none is accumulating as of 2026-11-09). The 57 previous skills reference
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
- [x] M-15 — **Reopen intake-866 / COMP_r.** ✅ 2026-11-09 pooled AUC under the id_map on the reseeded store = 0.5913 (> 0.55), so COMP_r reopens as a routing-signal candidate (recommend only, nothing wired; the probe's own reading is the weak band, do not wire). [belief: cc] Its 2026-07-22 null (pooled AUC 0.4933) was computed
      through `memories.embedding_idx`, i.e. the broken mapping. Adversarial re-analysis with the
      correct id_map resolution moves it to **0.5570**, which no longer clears the probe's own
      close-out gate of <=0.55; its in-sample leakage anchor read 0.6427 where the report documented
      "expected ~1.0", recovering to 0.9101 under the correct mapping. The line was closed on bad
      evidence. Re-run after the reseed. Done when pooled AUC under the correct id_map is recomputed on the reseeded store: <= 0.55 closes the line for good, > 0.55 reopens COMP_r as a routing signal candidate. *2026-11-09:* both reseeds have happened (07-27 and 08-09, 63,786 rows published); run it on the live 64,514-row store, pure offline analysis, record the embed-text convention (still includes `priority`) with the result; not blocked by the HOLD.
      - 2026-11-09 (apr2 rtg09-evl10-code) partial: `scripts/analysis/comp_region_probe.py` (orchestrator branch `apr2/rtg09-evl10-code-20261109`, `212d583f`) gains `--resolve-id-map` (default off; resolves each row through `id_map.npy`, logs mapped/unmapped/`embedding_idx` disagreement), test `tests/unit/test_comp_region_probe_id_map.py`. The pooled-AUC run itself is NOT done: the probe's role-bank matmul over the 64,514-row store is well over a few CPU seconds, so it needs a bounded CPU row. Stays open. [no-belief: tooling change, no AUC computed]
  - 2026-11-09 (apr2 prep-memrout): row `m15-comp-auc-idmap-20261109` (rank 21, CPU, model-free) published; the keeper's smoke ran the whole 15 s job once on a read-only snapshot of the reseeded store (62668 routing rows, 0 `embedding_idx` disagreements with `id_map`, mapped 62668): pooled AUC 0.5913 under the id_map resolution (identical on the `embedding_idx` control), in-sample anchor 0.9985, 5431 counterfactual objectives. That is above the 0.55 close-out gate, which would reopen COMP_r as a routing-signal candidate; a smoke does not count, so the box waits for the granted run to file it. Not ticked. [no-belief: smoke preview, not a graded result]
  - **2026-11-09 FILED from the granted run (row `m15-comp-auc-idmap-20261109`, rc 0, 16 s, model-free, one core; orchestrator `0227696e`, `comp_region_probe.py --resolve-id-map`; result `/mnt/raid0/llm/tmp/m15-comp-auc-idmap-20261109/out/RESULT.json`):** read-only snapshot of the reseeded store (sha256: episodic.db `e4c82f6b...`, embeddings.faiss `4e4eabf5...`, id_map.npy `39512fd1...`; 64,514 faiss vectors, 62,668 routing rows, 7,576 canonical objectives, 5,431 counterfactual objectives, 23,955 counterfactual instances, base rate 0.713). **Pooled AUC (success given role, leave-one-objective-out, counterfactual set; higher = better) = 0.5913**, all-objective pooled 0.5965, macro 0.5901; in-sample leakage anchor 0.9985 (documented expectation about 1.0, so the mapping is now right). Per role AUC (n instances): worker_general 0.632 (4,349), ingest_long_context 0.616 (4,826), coder_escalation 0.576 (4,884), architect_general 0.568 (4,798), frontdoor 0.565 (5,028); worker_vision 0.574 (63), worker_math 0.6 (6), toolrunner n/a (1). The `embedding_idx` control gives the identical 0.5913 because this reseeded store has 0 `embedding_idx` vs `id_map` disagreements (mapped 62,668, unmapped 0), so on this store the mapping choice cannot matter (the earlier 0.4933 and 0.5570 were computed on the pre-reseed store); the granted run reproduces the smoke preview's 0.5913 to the four digits that preview reported, so the preview number is now final. Rule applied: <= 0.55 closes, > 0.55 reopens; 0.5913 > 0.55 reopens, but it sits in the probe's 0.55-0.65 weak band, with only worker_general and ingest_long_context above 0.6. Embed-text convention: still includes `priority` (EVL10-REEMBED-POINTER below), not recorded in the run's RESULT.json. Observation per MEASUREMENT.md, no protocol id. Follow-up: whether a 0.59 AUC is worth a routing feature is a design question for the owner, not filed as work (declined: the probe says do not wire, and EVL10 re-embeds the store once, which would move this number).
- [ ] **EVL10-REEMBED-POINTER — the next full re-embed is the EG2 swap, with EPD-3 folded in (pointer box; nothing re-embeds from this handoff).** Owners: REPL-EMB-2.x in `harness-program.md` (`scripts/migration/reembed_stores_eg2.py run --apply --assume-stopped`, BGE-1024 to EmbeddingGemma2@256; bound to the v11 stack change since `gemma-embedding2` is absent from production v10) and EPD-3 in `routing-program.md` (drop `priority` from `MemoryRecord.embedding_text()`, 34,938 rows carry `priority:interactive`). Operator decision: EPD-3 is folded into the EG2 swap so the store is re-embedded ONCE; do not run EPD-3 as a separate re-embed, and never change the recipe code before the re-embed. Done when both owners record that the single re-embed landed and the integrity gate (M-17) passes on the result. (added 2026-11-09)
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
  - [x] M-17e — **No tool repairs a content-corrupt vector.** The 2026-08-04 fix was a one-off ✅ 2026-10-31 — APP `def3e2c08dbe5939ecbbc3e4c862f6110f29fda3`; `tests/unit/test_repair_episodic_vector.py` 17 native tests passed; [durable evidence](../../artifacts/non-inference/codex-ni-next-accepted-20261031/CAPSULE.md#m-17e-content-vector-repair). Future apply requires stopped cached readers; no live mutation/deployment. [no-belief: tooling-repair]
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
      - B4: judge = `Qwen3.8-27B-Q8_0` (re-scoped 2026-11-03; was `gemma-4-26B-A4B-it-ORIG-Q8_0`, operator 2026-09-16), recipe
        `eval/gemma-4-26b-a4b-orig-q8-gpu-judge-np4`. (2026-11-09: recipe now exists, `epyc-inference-research` `artifacts/serving-recipes/eval/qwen3.8-27b-q8-gpu-judge-np4.json`, branch `apr2/prep-memrout-20261109`, DFlash2 on, untested as a judge. Still missing before M-12/M-12b/M-12k can be rows: a 5-question judge smoke, a reader server row on the GPU with a long-context window, the `judge_beam_run.py` path needs the orchestrator `request_llm_judge_text` (B6 merge), and the judge-family question below.)
      - B5: recipe + smoke `a6491b9e`, `docs/m12-long-context-gpu-recipe.md`. **M-12 GPU window deferred by the
        operator 2026-09-16**; `smoke_prefix_reuse.sh` (`a6491b9e`) is ready for when it resumes.
      - B6: the merge list now also covers these two branches — both merged (research `cfbfa448`).
      - B7: add `pandas` to the research `.venv` (`uv sync --extra benchmark`, which also realigns pyarrow to
        24.0.0) — see M-12j. (re-scoped 2026-11-03 from judge gemma-4-26B-A4B-it-ORIG-Q8_0: deleted; judge now Qwen3.8-27B-Q8_0 (GPU), recipe to be re-pinned and held fixed across arms)
      - **Judge decision 2026-11-09 (operator): Qwen3.8-27B judges, with the same-family caveat accepted.** Rules that travel with it: (1) **same-family bias must be recorded in every claim** that uses this judge (a claim line or tuple field naming reader family, judge family and that they overlap); (2) the **fallback in which the 27B reader judges its own answers is BANNED**, so if the judge cannot be served, the judged leg is NOT RUN rather than self-judged; (3) going forward, **qwen3.8-27b results will likely be judged by qwen3.8-flash-next**, so the judge identity is a pinned field per run and arms are never mixed across judges. This closes the judge-family question; it does not close B4's remaining items (5-question judge smoke, long-context reader server row, `request_llm_judge_text` merge). [no-belief: operator decision note]
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
        and scored with `score_beam_run --arm full|rag|trace`. Absorbs UTM-B2/UTM-B3: the `trace` arm is the FTS5 store + navigation.py (RRF k=60) backend, and the run artifact records the ingest FILTER (which turns were indexed, at what granularity) as a first-class experimental parameter.
    - 2026-11-02 evidence recovery: research `benchmarks/results/runs/20260918_195111`,
      `20260918_221626`, and `20260918_232546` contain reader, judged, scored and belief
      artifacts for full, rag and trace respectively (400 questions each). The saved judge is
      Gemma 4 26B and the reader is Qwen 3.6 35B; per-row context modes identify each arm.
      The saved 10-ability macro scores (0.624526, 0.625852, 0.649611) are **not** the
      specified five-ability headline. The five abilities are not enumerated in this task or
      the saved score files; trace their original definition before computing the headline.
      Recorded truncations are 2/400, 3/400 and 3/400 respectively. Run directories lack
      receipts establishing matched reader prompts/settings, both-role ingestion, matched
      retrieval budgets/chunking and runtime dataset digest verification. Recover those
      receipts before treating the M-12c controls or this checkbox as satisfied. [belief: cc]
  - [ ] **M-12c — pre-run do-not-copy checklist, seven items** (intake-1337#record, each traceable to
        a site in MemPalace issue #125): (1) report BEAM's own fold, never a binarised
        micro-average; (2) ingest BOTH roles, never user turns only; (3) no synthesis
        `max_tokens` below what the highest-nugget ability needs; (4) judge model != reader model,
        held FIXED across arms; (5) no SSL bypass — stage the dataset under
        `/mnt/raid0/llm/data/eval/` with a verified digest; (6) identical retrieval budget and
        identical chunking for the control and the arm under test; (7) prompt-match all arms,
        including the closed-book instruction. Item (8), absorbing M-12d: use the external reference curves only as floors and sanity checks — Tulving's shipped 12-arm results (`result_lenient_all_book_200.csv`) and BEAM issue #125's Raw ChromaDB arm (49.0% author fold / 55.7% BEAM fold); far below the floor means a configuration defect, never a result.
    - 2026-11-02 staged-input check: `/mnt/raid0/llm/data/eval/beam/data/100K-00000-of-00001.parquet`
      hashes to `c0519be25907005ba873c927c50877471d550873039d96c041554d0075a78ace`, matching
      the staged `PROVENANCE.txt` for revision `3205395e897e7318c7b094ef4e6047b9b82dbb03`.
      This verifies the file now; it is not a receipt that the 2026-09-18 runs checked its digest
      or satisfied the other checklist items. [belief: cc]
    - **2026-11-09 (apr2 third-pass) PARTIAL, box stays OPEN:** research branch `apr2/third-pass-20261109` `c9aac169b`. `scripts/benchmark/beam_prerun_checklist.py` checks items 1-8 mechanically (PASS / FAIL / UNKNOWN with evidence; `cleared` only when all eight PASS) from the run's scored summary plus a per-arm `beam_run_receipt.json` (schema in the module docstring: reader model/max_tokens/prompt sha256/closed-book flag, ingest roles/chunking/retrieval budget, dataset path+sha256). 11 fixture tests pass (`--noconftest`). **Run on the three 2026-09-18 runs** (`full`=20260918_195111, `rag`=221626, `trace`=232546): item 1 PASS (all `beam_macro`), item 4 PASS (one fixed judge `gemma-4-26B-A4B-it-ORIG-Q8_0`, reader differs), item 8 PASS (rag/trace headlines 0.626/0.650 vs the 0.557 floor); items 2, 3, 5, 6, 7 UNKNOWN: no receipt exists (item 3 also shows truncated rows 2/3/3 of 400). So the Sep runs are NOT cleared, and the gap is now machine-visible. **Not done:** the launcher does not yet WRITE `beam_run_receipt.json`; until it does no new run can clear items 2, 3, 5, 6, 7, and the minimum `max_tokens` the highest-nugget ability needs is a parameter (default 1024), not a measured need. [no-belief: checker and fixtures; historical result is UNKNOWN, not a finding]
  - **[declined: ws58 2026-11-03 content-review: merged into M-12c as its item (8); a reference note, not a task]** **M-12d — external reference curves, used as floors and sanity checks, never as targets.**
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
        (`scripts/benchmark/tulving_episodic_adapter.py:543` `compute_chronological_awareness_score`, research repo; anchor was :325 until 2026-11-09) (found
        2026-09-14, noninf sweep). **Next action (2026-11-09):** write the scoring-validity note; it is a model-free offline re-score over existing results (rescored artifact `/mnt/raid0/llm/epyc-inference-research/benchmarks/results/runs/20260619_141212/tulving_score_rescored_20260914.json`, research repo, not under `/workspace/benchmarks`) and needs **no bench release and no exclusive claim**. Absorbs M-12i: the same write-up codifies the offline re-scoring protocol, so a corrected SRS/CAS can be cited as a protocol result and never as a back-filled tuple.
    **2026-11-09 (apr2 rtg09-evl10-code) partial:** scoring-validity note written, [docs/reference/tulving-scoring-validity-m12f-2026-11-09.md](../../docs/reference/tulving-scoring-validity-m12f-2026-11-09.md); model-free re-score reproduced from stored rows: CAS 0.1593 as committed, 0.0704 excluding the 30 single/zero-item questions (zero-fill inflates CAS), -0.0462 on the 8 fully scored. Box stays open: the paper's convention for single-item questions is unverified, so the headline decision is not made. [no-belief: offline re-score is a protocol result, not a claim tuple]
  - [x] **M-12g — stop comparing SRS across book sizes until the bin sets match**: ✅ 2026-10-08; bin `6+` is empty in the
        20ch set, so the 20ch SRS averages over four bins while the 200ch figure averages over five
        (`scripts/benchmark/tulving_episodic_adapter.py` `compute_simple_recall_score`) (found 2026-09-14,
        noninf sweep).
  - [x] **M-12h — close the judge-path tau trap before any LLM judge is wired**: `_llm_judge_fallback_hook` is
        dead in the deterministic path but `compute_f1_for_result` still branches on it and returns
        `matched_gt_items: []` when a judge fires, silently giving every judged question zero tau coverage
        (`scripts/benchmark/tulving_episodic_adapter.py:685-710`) (found 2026-09-14, noninf sweep).
  - **[declined: ws58 2026-11-03 content-review: merged into M-12f (one scoring-validity write-up)]** **M-12i — codify an offline re-scoring protocol before any decision cites the corrected SRS/CAS**,
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
        *2026-11-09:* needs the stack (frontdoor) running and an inference window; the suite, seeds and the memory-off switch are still unnamed (underspecified; resolve before filing a row). Not Autopilot-dependent; the episodic store it reads is frozen at 64,514 rows.
- [x] **M-23 — SkillBank A/B readout spec (supersedes the pooled-mean go/no-go of `handoffs/completed/skillbank-distillation.md` section 19; AK-PM-4 step (c) is re-pointed by its owner; M-12 itself stays the episodic A/B).** Zero inference; the run is gated on M-11a populating a bank and on the DAR-1 regret gate (`retrain-routing-models.md:126`). The cell is role plus model pin as served (frontdoor, worker, coder, architect). Report skill-on minus skill-off per cell with a task-level bootstrap 95% CI and the share of negative role-domain cells, never one pooled delta (`intake-2190#00`, `intake-2190#03`, `intake-2190#10`); declare the minimum detectable difference at the run n before the run (run-local declaration, not a standing rule) and do not rank arms whose CIs overlap (`intake-2181#01`); promotion is per-role non-regression, not mean > 0. Report adoption beside accuracy, defined as the share of injected skills whose title is echoed or visibly applied in the routed role's trace (titles, not ids, are in the prompt, `skill_retriever.py:230-236 @5d4ad2c0`), detector derived from the skill's own rule or title and fixed before the run; adoption is a separate failure axis from correctness (`intake-2169#04`); the SkillLearnBench tool-call metric is not comparable (`intake-2180#03`). Log per-request skill_ids joined to the served role and model pin. Teacher-side solve rate or skill-quality scores are never the gate; the student-side matched A/B is (`intake-2170#03`); any LLM-judged skill-text score is advisory (`intake-2181#03`, `intake-2190#07`). Report every headline delta under both intention-to-treat and per-protocol parse handling and re-score stored outputs with a second independent scorer before a scorer-dependent delta is acted on (`intake-2171#04`, `intake-2171#06`). Prior: the sign of skill benefit is a distribution (`intake-2169#08`, `intake-2190#00`), so borrow none from either paper. When the A/B reports, compare the entry format with Harness^2's (cue, adopted tree, EXPERIENCE.md, domain-scoped index; `intake-1995#02`). ✅ 2026-10-20
  M-29 clauses apply (see "M-29 readout clauses (filed 2026-10-21)" below the M-23 sub-items).
  - [ ] **VB-SKILLBANK-AB-WRITE producer call (owed, filed 2026-10-21):** [too-big: missing native request logs, adoption and role/model cell contract require owner integration] the M-23 A/B runner calls `scripts/vidya/adapters/skillbank_ab.write_belief_measurements(out_dir, run_id=..., producer=..., request_log_path=..., cells=[...])` once per run, one cell per role x model pin, before its first arm runs; carrier and reader landed in root `7335da327`.

    - 2026-11-02 execution-order correction: the carrier's current `write_belief_measurements`
      requires positive scored counts, adoption and a hash of the completed request log. It
      cannot truthfully be called before the first arm. Before any arm, freeze the protocol,
      suite, cells, detector, scorer and MDD in the run manifest and open the native request log;
      after all arms and scoring finish, finalize that log and call the writer once with the
      resulting cells. Do not invent completed measurements or change the log after hashing it.
      The M-23 served-task runner has not been found; offline retrieval replay is not that runner.
      This corrects the call timing above; the producer integration remains open. [belief: cc]

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
      (`src/repl_environment/routing.py:93` `_recall`, `:339` `_route_advice`; anchors re-resolved 2026-11-09). Zero observed calls in
      1.7 GB of progress JSONL, and only 6 rows carry `repl_steps`. Log each call (query, hits, whether the
      answer used them), then decide from data: keep, re-prompt, or remove. (filed 2026-09-26)
      - 2026-11-09 (apr2 rtg09-evl10-code) partial: orchestrator `212d583f` adds default-off telemetry (`ORCHESTRATOR_RECALL_TELEMETRY=1`, optional `ORCHESTRATOR_RECALL_TELEMETRY_PATH` JSONL), one record per `recall()`/`route_advice()` call (tool, role, query, status, hits, best, confidence); test `tests/unit/test_repl_recall_telemetry.py`. Whether the answer used the hits is not captured (needs answer-side attribution), and the keep/re-prompt/remove decision needs data from a live stack. Stays open. [no-belief: instrumentation only]
- [x] **M-21 — filter smoke/probe traffic out of episodic write-back.** Live write-back is dominated by smoke prompts (`"What is 17 * 3?"` alone: 8,641 Q updates). Tag probe/smoke/health traffic at the API and skip its write-back; add a test and a one-off count of affected rows. (filed 2026-09-26) ✅ 2026-10-31 — APP `6de0e31dce409d3b974be3b78979f02dadcdc473`; [tests](../../artifacts/compute/codex3-m21-20261031/FINAL-v2.log); [read-only literal count](../../artifacts/compute/codex3-m21-20261031/COUNT.log). [belief: cc]
      - 2026-10-31 audit correction: original task text restored verbatim (line wrapping only); its historical attribution is not established by the literal count. Existing implementation/evidence scope follows. [no-belief: task-identity correction]
      Explicit smoke/probe/health tags on `/chat` and `/chat/stream` enter durable task-start records and suppress immediate and replayed episodic scoring; untagged requests remain eligible. Literal count: one matching row, 8,641 updates, historical request provenance UNKNOWN. Explicit external-reward APIs are separate and not covered by this replay filter; no historical memory was changed.
- [x] **M-22 — give `recall()` a live exploration write path, or say it is seed-only.** `recall()` reads only <!-- evidence-integrity: Orchestrator `4c55fdd462d1d186963f7aedfb33fc388fdb8986`; test: tests/unit/test_repl_recall_v1.py; artifact: artifacts/engineering/m22-recall-scope-20261031/EVIDENCE.json --> <!-- completion: ✅ 2026-10-31 [belief: cc] -->
      the 728 seed `exploration` rows (0 updates); nothing writes exploration rows from live traffic. Either
      write exploration memories from real REPL sessions (with M-21's filter) or document recall as a static
      seed lookup and scope M-20 accordingly. (filed 2026-09-26)

  <!-- task-evidence-integrity:start M-22 -->
  - Completed 2026-10-31 via the documented-population alternative: implementing APP `4c55fdd462d1d186963f7aedfb33fc388fdb8986` ([published tests](https://github.com/pestopoppa/epyc-orchestrator/blob/4c55fdd462d1d186963f7aedfb33fc388fdb8986/tests/unit/test_repl_recall_v1.py)); [original source-check evidence](../../artifacts/engineering/m22-recall-scope-20261031/EVIDENCE.json). Recall responses now declare seed/import/explicit-write exploration lookup and no automatic live REPL exploration writeback. Explicit Python, direct-store and import writers remain possible. Eight related real temporary-store/journal tests, actual make gates and focused Ruff pass. The historical728-row/zero-update figure above was not remeasured. No automatic writer, deployment or live-learning result is claimed. [belief: cc]
  <!-- task-evidence-integrity:end M-22 -->

  <!-- task-evidence-integrity:start M-20-scope -->
  - M-22 scope clarification: the recall arm evaluates the pinned exploration seed/import population and records explicit writes during the study, not learning from normal live REPL exploration completion. `route_advice()` retains its separate live-routing-memory scope. M-20 telemetry and efficacy acceptance remain open; no new traffic, observed-use count or evaluation is claimed. [belief: cc]
  <!-- task-evidence-integrity:end M-20-scope -->

#### Why the reseed is necessary (and what it will NOT fix)

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

#### The store carries real signal — this is worth fixing

On a held-out temporal split (train pre-2026-06-06, test after), picking the highest-q action per
suite gives macro test failure **0.1964** vs **0.2518** random and **0.1790** oracle — **76% of
achievable headroom, permutation p = 0.0025**. It survived adversarial attack as a writer-path
artifact (partial corr unchanged at −0.875) and as a popularity artifact (frequency-greedy 0.2211 ≈
random). Measured *within* suite across actions, so it is not suite identity.

#### Corrections to earlier claims in this investigation

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

#### Key files

| file | role |
|---|---|
| `orchestration/repl_memory/faiss_store.py` | publish order, `add()` position, `_load()` reconciliation, `FAISSDesyncError` |
| `orchestration/repl_memory/memory_record.py` | the record contract |
| `orchestration/repl_memory/episodic_store.py` | `update_count` seed, chokepoint guard |
| `scripts/maintenance/repair_faiss_id_map.py` | exact pointer repair (done) |
| `scripts/maintenance/reseed_episodic_store.py` | staged reseed |
| `tests/unit/test_faiss_store.py` | `TestDesyncCorruptionRegression` (5 cases) |
| `tests/unit/test_memory_record.py` | contract (16 cases) |

#### Reporting

M-10/M-10a are closed with the durable cosine result above. Next memory work is M-11a, M-12,
M-15, and M-16; do not reopen the reseed unless a new evidence-backed integrity failure appears.

#### Research Intake Update — 2026-09-17 (typed memory writes; intake-1472/1473/1474)

- [x] **M19-RECORD — specify native memory-write diagnostic records.** MAIN accepted 2026-10-06: [APP record contract](https://github.com/pestopoppa/epyc-orchestrator/blob/be8d46f61edcf5cb795d485b1a8171c562ee4971/docs/design/memory-write-decision-record-v1.md), per-question probabilities/local confidence, honest typed/untyped provenance and unresolved states, opaque value receipts, immutable self-hash. No writer, calibrated threshold or enforcement implemented. Parent M-19 remains open.
- [x] **M-19 — Typed decision records + confidence gate design (record spec unblocked; gate threshold needs its own calibration record).** *Corrected 2026-09-26 (operator-directed tidy): was "blocked on TD-2". TD-2 landed 2026-09-17 and was never the unlock — `fuzzy-workflow-authoring-gui.md` FW-1 §4 D-1: calibration lifts per (model pin, question catalogue) on an operator-ratified record, never globally, and TD-5 forbids enforcement without operator approval. The record spec is zero-inference and dispatchable now; only a live gate waits on a calibration record for the memory-write catalogue on its model pin.* Specify a memory-write record carrying per-question probabilities and a caller-computed confidence statistic; the gate threshold must come from a calibration record for that catalogue and model pin (TD-2 is the method; owner `typed-decision-plane.md`, RTG-56), never from candidate softmax (intake-1474 measured 65% of 7B wrong fields above 0.90 confidence).
  - 2026-11-09 apr2 second-pass: record spec written as unwired code. Orchestrator branch `apr2/second-pass-20261109` (worktree `/mnt/raid0/llm/worktrees/apr2-second-pass-orch-20261109`) 311e7c4c adds `src/typed_decisions/memory_write_record.py`: `MemoryWriteRecord` (op, target, content hash, per-question probabilities, caller-computed `ConfidenceStatistic`, catalogue id+version, model pin, source events), `CalibrationRecord` and `evaluate_gate`. A statistic named as candidate softmax is refused; the threshold exists only in a `CalibrationRecord` matching catalogue+version, model pin and statistic; without one the verdict is `unscored`, with an unratified one `shadow_pass`/`shadow_hold` (never enforced), enforcement only with `operator_ratified`. 9 tests pass. The live gate still waits on a calibration record for the memory-write catalogue on its model pin (typed-decision-plane.md, RTG-56). Spec accepted by the box text; the gate threshold stays open. [no-belief: unwired spec and synthetic tests only]

#### Work payload bound follow-on — 2026-10-07

M-11a2b closes producer-to-store wiring only. MAIN source review found that `sanitize_work_text` trusts any suffix marker for the same cap, even after an oversized prefix. This allows an untrusted marker to bypass the nominal bound and the post-truncation redaction pass. Redaction remains the existing default-on, fail-open policy; no privacy guarantee is asserted.

- [x] **M11-WORK-CAP-SOURCE — refuse oversized forged truncation markers while preserving legitimate bounded-value idempotence.** Bound both prefix and marker representation; meaningful forged suffix, oversized decimal metadata, greater-than-scanner-limit synthetic credential and legitimate second-pass controls. Full actual memory-record/work-payload source verification through VB-M11-WORK-CAP-CONFORMANCE. Preserve objective text, existing item policy and sole redaction policy. No live memory, traffic prevalence or historical rewrite. ✅ 2026-10-07 — MAIN accepted [source and original41/41](../../artifacts/ni08/m11-work-cap-source-20261007/README.md).

**M-12h complete, 2026-10-08:** [MAIN source/native acceptance](../../artifacts/ni08/sc54-mf-m12h-source-integration-20261008/README.md). Research main daa preserves deterministic counts/matches while a judge supplies scalar precision/recall/F1; match/result provenance is explicit. All eight original AST-isolated controls passed, including no-judge and low/high judge branches. Synthetic hooks exercise the actual source body without LLM calls. This fixes the source trap; it does not claim improved tau, semantic alignment, retrospective rescoring or instrument admission. M-12g/M-12i remain independent next work.

**M-12g complete, 2026-10-08:** Research main `72832ef6` gates explicit SRS comparisons before output/capture and reports populated bins/counts without changing SRS/CAS arithmetic. The original 32 whole-module controls passed, including mismatched-bin refusal and valid comparison paths. [Evidence and limits](../../artifacts/ni08/tulving-srs-workflow-controls-20261008/README.md). Matching bins do not establish equal book difficulty. M-12f metric construction and M-12i prospective offline replay remain separate.

#### Research Intake Update — 2026-10-20 (harness cluster)

Operator-approved 2026-10-20 via research intake (plan sha256 1dc83054706ca0bae002602307b0d9ba6435b010be4d6ffd8a495a04605f3967). Monitor and knowledge records below are prose: no checkbox, no index next action.

- **M5 (monitor, 2026-10-20) — SkillBank re-distil and teacher follow-ons (consolidator arm, seed-set size, extractor rubric, GenericAgent, MUSE-Autoskill, SkillLens code, skills-in-the-wild, SWE-Skills-Bench).** Trigger: The first M-11a re-distil is scheduled, or the M-23 readout shows negative role cells. First step when it fires: Apply the arm labels in M-25; dive the listed sources. No immediate step remains: M-11a is operator-directed and inference-gated; the bank is empty.
- **K3 (knowledge, 2026-10-20) — Skill-benefit sign prior and SkillBank reading rules (SkillsBench -1.3, SkillGenBench about 0, SkillLearnBench +20.3, mean +2.29 with 37 of 150 cells negative; adoption separate from correctness; LLM-judged text quality advisory; four failure reason classes).** Retained use: Cited by M-23 and M-24; no prior borrowed.

#### Cache-friendly injection of memory and SkillBank context — 2026-10-21

Landed on epyc-orchestrator origin/main as `fc02209d` (flag `ORCHESTRATOR_CACHE_FRIENDLY_INJECTION`, default OFF, flag-off byte-identical, 18 tests plus 290 caller tests). Shared helper `src/prompt_builders/reusable_blocks.py`; wired into `SkillRetriever.format_for_prompt` and `build_routing_context`. Purpose: byte-identical, at-least-256-token blocks so chunk-KV reuse (cacheclip port) can hit. Flag-on drops Q-values, rank order and ids from the model-visible text and adds a 160-char objective per memory.

- [ ] **CFI-1 — quality A/B of `ORCHESTRATOR_CACHE_FRIENDLY_INJECTION` on vs off (SkillBank `skill_context` and episodic recall).** Paired, same tasks, same role/model pin, report accuracy, turns/task and tokens/task. The flag stays non-default until quality is neutral or better. Needs an inference window (not zero-compute). (filed 2026-10-21)
- [ ] **CFI-2 — decide the memory-k widening needed to reach 256-token blocks on the episodic path.** `retrieve_for_routing` yields only a few memories of about 25 tokens each, so flag-on emits one short block (`meets_min=False`). Options: widen k, or include a stable memory-library prefix. Decision package with the token and latency cost; the choice blocks only this item. (filed 2026-10-21)
- [x] **M-28 — Cache-friendly layout rule for episodic-memory and SkillBank injection.** The routing context is about 75 tokens today and skills are a small library reused across many requests. Group injected memory and skill items into blocks of at least 256 tokens, serialise them deterministically (stable order by id, no per-request fields inside a block), place the blocks contiguously, and keep the per-request volatile text outside them, so a chunk-reuse path can hit when memory and SkillBank go live. Write the rule into this handoff and add a rendering test (same item set, two retrieval orders, identical blocks). Cross-reference RTE-LOG-1 and REPL-EMB-6.1 so real reuse is measured once live (intake-2311#record, intake-2297#record). It does not change which skills are selected. Acceptance: the rule is filed, the rendering test passes, and the injected text for a fixed item set is byte-identical across orders within each block. Estimate: 0.5-1 day. ✅ 2026-10-21
  - 2026-10-21 (dpf-logpfx): DONE. Rule filed below. Rendering tests already in orchestrator `fc02209d` (`TestPacking.test_order_insensitive`, `TestSkillPath.test_flag_on_deterministic_and_score_independent`, `TestRoutingContext.test_flag_on_stable_across_q_and_order`) pass in the 282-test run; cross-references to RTE-LOG-1 and REPL-EMB-6.1 are in the rule. Selection unchanged.
  - **Cache-friendly layout rule (filed 2026-10-21, lane `dpf-logpfx`).** Implemented by `src/prompt_builders/reusable_blocks.py` (orchestrator `fc02209d`), flag `ORCHESTRATOR_CACHE_FRIENDLY_INJECTION`, default OFF, flag-off byte-identical. (1) One item = one canonical text: whitespace normalised, control tokens neutralised, no score, Q-value, id, timestamp or rank in it. (2) Items are de-duplicated and ordered by sha256 of their canonical text, never by retrieval order or score, so the same item set renders to the same bytes in any retrieval order. (3) Content-defined cuts close a block once it holds at least 256 estimated tokens (maximum 1024), so adding or removing one item dirties about one or two blocks; a trailing remainder merges into the previous block; items are never split; a set below 256 tokens in total yields one short block with `meets_min=False`. (4) Stable delimiter lines; the sha256_12 of a block is exposed for logging only and is never written into the prompt. (5) Blocks are placed contiguously; per-request text (own role, suggestion, task) sits after them. (6) The kept item set is chosen by the unchanged selection and budget logic: the rule does not change which skills or memories are selected. Rendering tests: `tests/unit/test_reusable_blocks.py` (`TestPacking.test_order_insensitive`, `TestSkillPath.test_flag_on_deterministic_and_score_independent`, `TestRoutingContext.test_flag_on_stable_across_q_and_order`). Real reuse is measured once live through RTE-LOG-1 (`blocks[]` kinds `skill` and `routing`, written by `src/backends/prompt_layout.py`) and REPL-EMB-6.1. Open follow-ups are CFI-1 (quality A/B) and CFI-2 (memory-k widening to reach 256-token blocks), filed separately below; neither is part of this rule.
- [x] **M-29 — M-23 readout clauses from the skill-reliability dives (one amendment, spec only).** M-23 (above) stays the base spec; this task adds the clauses its first readout must also carry, all descriptive or report-only and none a gate. (1) Per role-model cell print the paired transition counts c (failed skill-off, passed skill-on) and b (passed skill-off, failed skill-on) with an exact two-sided McNemar p on the discordant pairs beside the net delta and the negative-cell share, and report b even when the net is positive (intake-1321#record); promotion stays per-role non-regression. (2) A skill-off REPLICATE arm (same pinned config, independent sampling) so the flip floor of an unchanged condition is measured, with a paired flip counted as a skill effect only if it exceeds that floor; an external replicate-noise figure (intake-2238#record) is an order-of-magnitude prior, never a substitute for measuring on the local served pin. (3) Stratify the transition table by adoption (title echoed or visibly applied, detector fixed before the run). (4) One placebo arm: skill-on with entries swapped for token-matched, task-irrelevant entries of the same format at the same injection point. (5) If a cell reads net-negative (b greater than c) the follow-up is a Bernoulli mask arm over the entries injected in that cell (inclusion 0.5 at retrieval time, mask count from the stated power analysis, per-skill effect with a permutation test); declare the paired-task count and resulting resolution before any per-entry run, and report cell-level only if the populated cell is too small (intake-2229#record, intake-2259#record). (6) Report injected tokens per request and total prompt-plus-completion tokens per request or trace for both arms, and the skill-on minus skill-off delta per 1,000 injected tokens (intake-2288#record, intake-2301#record). (7) Record the role-prompt hash (prompt version id) beside the model pin so a prompt edit splits the cell (intake-2290#record). (8) Label each request general-only or general-plus-specific and, for the latter, by tercile of the top specific entry stored cosine similarity (cut points fixed before the run) (intake-2318#record). (9) Print the skill-off pass rate beside every cell delta and list cells at or above 95 percent skill-off as ceiling-limited, excluded from the negative-cell denominator (intake-2337#record). (10) Record each injected skill source role at distil time and whether the injection was same-role or cross-role, because the retriever has no role term (intake-2333#record). (11) Report write-side cost as LLM calls plus input and output tokens summed over every memory-construction call, judge calls excluded, beside the read-side line (intake-2311#record). The 2026-10-21 text of M-23 is unchanged. Acceptance: the eleven clauses are filed under M-23 verbatim and M-23 points at them; no gate or MEASUREMENT.md text is touched. Estimate: 0.5 day. ✅ 2026-10-21
- [ ] **M-27 — Extend the M-24 lint and M-25 probes with the new read-only classes (zero inference).** M-24 and M-25 are filed and ticked; this adds, each advisory and report-only: (a) lint class for negative-capability claims ("X does not work", "cannot use Y") and for steps whose source trajectory ended without a labelled success, reporting flag rate on the SkillLearnBench corpus and on the first distilled pool (intake-117#record); (b) seed the path, IP, URL and identifier regexes from the NVIDIA SkillEvaluator `pii_patterns.yaml` at its pinned SHA (copy with attribution; do not install or run the tool; add model-name, port and column-name classes locally) (intake-2250#record); (c) pair mode: skills in the same task type whose stored-embedding cosine lies in 0.6-0.85 and whose literal sets differ, count and 10 examples per config (verify embeddings are readable from the backup without running the embedder) (intake-2239#record); (d) M-25 probe additions: top-k source-class composition (interactive, autopilot or eval-generated, cron-like) for a fixed set of recall queries (verify the store carries a source label), the retrieval_count distribution on the pre-purge 57-skill backup against the 5 and 20 floors with the count below effectiveness 0.3 at each floor (intake-2251#record), the source role per skill, and the distillation call and token totals in the pre-distillation checkpoint note. Run under `region-lock run --cpu-list 0-95`. Acceptance: each class has a fixture test and a first report on the pinned corpus; nothing is distilled. Estimate: 2-3 days.
  - 2026-10-21 (fillers-3c4ca599): registered as queue item `s5-m27-live-recall` (block-correctness, NOT armed: bundled into `s5-stackup-bundle`); window-ready job `/mnt/raid0/llm/tmp/fillers-3c4ca599/jobs/m27_job.sh` (subprocess embedder, no ports, real-embedding proof).
  - *(2026-11-05, INF-22 main session, operator-directed review)* `s5-stackup-bundle` is SUPERSEDED: all 16 rows filed under it are COMPLETE, each on its own private kernel-store llama-server (:18971/:18973/:18976/:18977/:18978) or a subprocess embedder; none needed the production stack. The operator authorised a one-time bring-up, but it would run zero sub-rows, so the stack stays down. Remaining offline work (HIL-15a AUC write-up, HIL-15b pass band, HIL-16b four-arm flip) runs on private packets. [no-belief: bookkeeping]
  - 2026-10-21 `dpf-skill` NOT ticked. Built: orchestrator `5a92ea4c` (`orchestration/repl_memory/distillation/{memory_probes,pii_seed,literal_lint,pipeline}.py`, `tests/unit/test_memory_probes.py`, 7 fixture tests). First report: [m27_result.json](../../artifacts/dpf-skill-20261021/m27_result.json). (a) negative-capability flags 55 of 1,277 SkillLearnBench skills, 0 of 57 on the backup; 18 of 57 backup skills have a failure source outcome; unlabelled-success is not computable on SkillLearnBench and the first distilled pool does not exist yet. (b) NVIDIA `pii_patterns.yaml` @15adf98f seeded with attribution: 8 of 1,277 SkillLearnBench, 0 of 57 backup. (c) stored vectors readable without the embedder (57 of 57, dim 1024); 416 same-task-type pairs, 357 in cosine [0.6, 0.85), 334 with differing literals, 10 examples in the JSON; SkillLearnBench has no stored embeddings. (d) retrieval_count max 2 so 0 skills reach the 5 or 20 floor; source role unresolved for all 57 (0 of 85 trajectory ids found); episodic rows carry `context.source` (progress_log 4,301, external 28,161, legacy 30,736, seed 1,316) but no interactive or cron label; teacher call and approximate token totals are in the report and `planned_teacher_calls` is in the checkpoint note. Ready for an inference window: the live top-k source-class composition over the 8 fixed recall queries (`memory_probes --live-recall`, needs the query embedder, refuses without `WINDOW_CONFIRMED=1`).
  - 2026-10-27 harvest (s5-m27-live-recall, ended 2026-10-22T10:54Z rc 0): M-27(d) live recall RAN (descriptive composition, no predeclared threshold). 8 fixed queries, k=10, real 1024-d embedder (`use_fallback=False`, norm 1.0 each). Pooled top-80: seed 53 (66%), eval_or_external 13 (16%), pre_label_legacy 8 (10%), autopilot 6 (7.5%). Pollution is concentrated: 5 of 8 queries return 10/10 `seed`; "extract fields from a csv file" is 8/10 eval_or_external; "escalate after repeated failure" is 5 eval_or_external + 1 autopilot + 4 legacy (0 seed); "which role handles long-context summarisation" is 4 autopilot + 2 legacy + 4 seed. `interactive_label_available: false` (no interactive/cron label, so only autopilot vs eval vs seed is separable). Evidence `/mnt/raid0/llm/tmp/fillers-3c4ca599/out/m27-live-recall.json` (+ `m27-linkage.txt`). [belief: cc]
  - 2026-10-28: M-27(d) top-k source-class composition (k=10, 8 queries; pooled seed 53 / eval_or_external 13 / pre_label_legacy 8 / autopilot 6) vs no predeclared rule (descriptive; the FILLERS row says only that it 'decides whether recall is polluted') → correctness-only (diagnostic observation; embedder proof use_fallback=False). Box M-27 stays unticked: parts (a)(b)(c) and the rest of (d) are not delivered by this run. Evidence: /mnt/raid0/llm/tmp/fillers-3c4ca599/out/m27-live-recall.json. [belief: cc]
  - [ ] **M-27d.1 — add an interactive/cron source label to the episodic write path, then re-run the 8-query composition.** 3 of 8 queries return non-seed rows (up to 8/10 eval_or_external) and the store cannot separate interactive from autopilot; decide whether eval/external rows belong in the default recall pool or behind a `context.source` filter (retrieval-side change needs a flagged A/B, not a silent filter). Filed 2026-10-27 harvest.
    - 2026-11-09 (apr2 rtg09-evl10-code) partial: orchestrator `212d583f`: with `ORCHESTRATOR_EPISODIC_SOURCE_LABEL=1` (default off) the API journals the request source (`interactive|autopilot|benchmark|repl_experiment`) at task start and the scorer stamps it in the row's `extra.request_source` (excluded from the embedding; no retrieval change). Test `tests/unit/test_m27d1_source_label.py`. Not done: the 8-query composition re-run (needs labelled writes) and the eval/external-in-default-pool decision (flagged A/B). Stays open. [no-belief: write-path label only]

#### Research Intake Update — 2026-10-21 (harness cluster, DP-F amendment)

Operator-approved Stage-3 amendment (plan sha256 2edfb0662f61e1254e7dc5e2b21888ef4f19df800a283e82b25caebeb6644746). Durable records only: no checkbox, no index next action. Each monitor row carries its trigger and first step; each knowledge row states what to rely on. Ledger ids (DPF-...) key to the Stage-3 recommendation mapping preserved in `.research-session.json` (`stage3_filing`).

##### K10 — Skill reliability, SkillBank, memory and skill-format evidence

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
- DPF-W4-TIDE-TD5 (intake-2338): Name collision: handoffs/active/context-and-token-economy.md refers to a "TIDE post-mortem" for an unrelated early-exit project.
- DPF-W4-TIDE-TD6 (intake-2338): Evidence quality: games and web environments, difficulty confound in loop pools, horizon-dependent AUV, no intervals.

##### M18 — SkillBank follow-on arms waiting on a populated bank or a net-negative cell

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

## Track: repl-session-memory-maturity
<!-- gate: none -->

> Folded from `handoffs/active/repl-session-memory-maturity.md` @ `b1bf3f3f7ade` on 2026-11-02 (BRF-T1-F24, route 1a, operator D1/D5; retired row EVL-36 → EVL-10). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### REPL Session Memory — Maturity Deltas

**Scratch**: `/mnt/raid0/llm/tmp/repl-session-memory-maturity/` · worktrees: `/mnt/raid0/llm/worktrees/repl-session-memory-maturity-*`

**Status**: active — D-a/D-a2/D-a3/D-a4/D-a6, D-b, D-e all landed 2026-07-27 (no
inference, no instrument-era surface). **An adversarial review broke the first pickle boundary the
same day; fixed in orchestrator `9d30bb60` — see *Security review — round 2*.** Remaining: D-c/D-c2
(decide on real-workload numbers), D-a5 (columnar codec, only if a workload needs DataFrames),
D-e1 (caps default, folded into D-c1), D-d (curation layer; acceptance extended 2026-09-26).
**Created**: 2026-07-27 (via research intake, operator-approved 2026-07-27)
**Priority**: MEDIUM
**Categories**: agent_architecture, context_management, memory_augmented
**Parent index**: [research-evaluation-index.md](research-evaluation-index.md)
**Related**: [repl-turn-efficiency.md](harness-program.md#track-repl-turn-efficiency),
[internal-interaction-lifecycle.md](routing-program.md#track-internal-interaction-lifecycle),
[rlm-contested-claims-self-evaluation.md](benchmark-suites.md#track-rlm-contested-claims-self-evaluation) (E2 rescoped
2026-07-27 — the code-log measurement lives here as D-c1, on real traffic, not as a synthetic arm
there)

#### Objective

Close the specific, verified gaps between our REPL session persistence and fast-rlm's, identified by
Stage-2 dive D1 (2026-07-27) reading both codebases. D-a/D-b/D-e require **no inference** and touch
**no instrument-era surface**.

#### Research Context

| Intake ID | Title | Relevance | Verdict | Verification |
|-----------|-------|-----------|---------|--------------|
| intake-901 | fast-rlm REPL memory / resumable sessions (re-review 2026-07-27) | high | adopt_patterns | dive-verified |
| intake-783 | fast-rlm — feature-rich RLM implementation (re-review Jul 2026) | high | adopt_patterns | (pre-lifecycle entry) |

#### What we already have — do not re-derive

Dive D1 **overturned** the Stage-1 hypothesis that our checkpointing loses variables silently. It
does not. Existing surface in `epyc-orchestrator`:

- `checkpoint()` / `restore()` — `src/repl_environment/state.py:391` / `:519` (re-resolved 2026-09-07)
- `SessionPersister` + SQLite store — `src/session/persister.py`, `src/session/sqlite_store.py`
- Non-serializable globals are collected into `skipped_user_globals` (declared `state.py:445`, appended `:478` — re-resolved 2026-09-07) **and reported
  to the model**, not just the logger — `src/session/models.py:462-465` renders
  `"Skipped non-serializable variables: ..."` into the resume summary, alongside a restored-variable
  inventory at `models.py:452-461`.
- `variable_lineage` already records role, execution count, timestamp and value type per variable
  (`state.py:444-476`; `_lineage()` defined at `:450-462` — re-resolved 2026-09-07). It records no
  shape field of any kind.

**Design boundary, not a gap:** fast-rlm documents *one live query per session directory — concurrent
queries race*. We must not inherit that. We run NUMA-concurrent by design and our session state is
SQLite-backed rather than a single `state.json`. No task is filed for it.

#### Tasks

- [x] D-a — **Serialization tier.** ✅ 2026-07-27 — operator-decided (hardened pickle boundary),
      implemented with four independent layers. See *Why D-a needed a decision* and *Security review*
      below.
  - [x] D-a1 — `/security-review` run on the implemented surface ✅ 2026-07-27. Four issues found and
        fixed before landing.
- [x] D-a2 — **Follow-up: pandas — DECLINE CONFIRMED, NOT-FEASIBLE.** ✅ 2026-07-27, empirical audit
      (19 DataFrame/Series shapes × 5 pandas versions, static `pickletools` enumeration cross-checked
      against a `find_class`-tracing unpickler, 36 = 36 agreement). Three independent disqualifiers,
      any one sufficient:
      1. **The inert-types invariant cannot hold.** 36 globals required; 8 are executable factories
         invoked via REDUCE with attacker-chosen args — `_unpickle_block`, `_new_Index`,
         `_new_DatetimeIndex`, `__pyx_unpickle_NDArrayBacked`, `__pyx_unpickle_IntervalMixin`,
         `BlockManager`/`SingleBlockManager.__setstate__`. `_new_Index(cls, d)` literally does
         `cls(**d)`.
      2. **The pyarrow branch is a proven memory-disclosure primitive.** With pyarrow installed, a
         plain string column needs `pyarrow.lib._restore_array`, which reconstructs an Arrow array
         from raw offset/data buffers **with no validation**. Demonstrated: offsets `[0, 4096]` over
         a 2-byte data buffer produced a **4096-byte heap over-read** returning adjacent process
         memory. `validate()` catches it but is never called on this path. Critically, it is built by
         *ordinary REPL calls* — no `__reduce__` defined — so the AST layer never fires.
      3. **A pinned allowlist is unmaintainable.** 3.0.2 vs 2.2.3 share only **14 of 57** required
         globals (2.x pickles everything under private `pandas.core.*` paths; 3.0 moved them to
         public). Worse, the set depends on whether `pyarrow` is *installed* — a transitive
         `uv sync` silently changes what a DataFrame requires.
      Also surfaced: `builtins.slice` is required by 18 of 19 cases and is not allowlisted, so no
      partial pandas allowlist would have worked as written anyway.
- **[declined: ws58 2026-11-03 content-review: unbounded conditional ("file only if a real workload needs it") with no workload named; the codec design stays readable here]** D-a5 — **If DataFrame persistence is ever wanted, use a typed columnar codec, not the
      allowlist.** Encode to a plain dict of `{str: ndarray | list | str | int}` with a closed dtype
      tag set and explicit index encodings, then pickle *that*; reconstruction happens in our code via
      public `pd.DataFrame(...)`, never in the unpickler. Prototyped during the audit: **17 of 19
      cases round-trip exactly** under `assert_frame_equal`, requiring **zero** new allowlist entries.
      ~250-350 LoC + ~150 LoC tests. Not scheduled — file only if a real workload needs it.
- [x] D-a4 — **Layer-4 broadened.** ✅ 2026-07-27. 3-arg `type()` is now rejected outright rather
      than only its literal-dict form. Superseded in scope by D-a6 below.
- [x] D-a6 — **BYPASS FOUND AND CLOSED (adversarial review, 2026-07-27).** ✅ See *Security review —
      round 2* below. The boundary landed earlier the same day was **broken end-to-end** and is now
      fixed (orchestrator `9d30bb60`).
- [x] D-a3 — **Allowlist drift guard.** ✅ 2026-07-27. `ALLOWED_GLOBALS` is pinned to a reviewed
      golden set (`TestAllowlistDriftGuard`), so any addition or removal is a deliberate, reviewable
      edit rather than a silent widening — plus structural guards that no entry reaches a
      side-effecting module and every `builtins` entry resolves to a type. **This is the mechanism
      that would have forced a review of the `numpy.ndarray` entry that D-a6 later showed was a
      memory-corruption primitive.** Note the framing changed: the invariant is no longer
      "inert data types only" (that claim was false), it is "every entry individually assessed for
      constructor-reachable primitives".
#### Why D-a needed a decision, not just effort (verified 2026-07-27)

The original problem statement: `state.py` gates on `_is_json_serializable`, so REPL-defined
functions/classes, numpy arrays, DataFrames and any built index fell into `skipped_user_globals` and
were lost across a resume.

**Why the obvious fix was not obviously safe.** `pickle` is *already* in
`ASTSecurityVisitor.FORBIDDEN_MODULES` (`src/repl_environment/security.py:29`), alongside `os`,
`sys`, `subprocess`, `socket`, `ctypes`. D-a proposes building host-side exactly the capability
the sandbox names as forbidden, over data the sandboxed model authored.

The chain is concrete. `FORBIDDEN_ATTRS` (`security.py:62-83`) does list `__reduce__`,
`__reduce_ex__`, `__getstate__`, `__setstate__` — but `visit_Attribute` only fires on attribute
*access* (`obj.__reduce__`). A class that **defines** `__reduce__` as a method is an
`ast.FunctionDef` inside a `ClassDef`, not an `ast.Attribute`. **Measured: our visitor returns
zero violations** for:

```python
class Index:
    def __init__(self, docs): self.docs = docs
    def __reduce__(self): return (__import__, ("os",))
cached_index = Index([1, 2, 3])
```

Such an object is precisely D-a's motivating case — a built index JSON cannot hold. Under D-a we
would pickle it, and `pickle.loads` at restore invokes the `__reduce__` callable in the
orchestrator process with real builtins, no restricted `__import__`, and no AST visitor. That
converts "model may write restricted Python" into "model may execute arbitrary code in the API
process", and the payload persists in the SQLite session store to re-fire on every resume.

That gap was **latent, not exploitable** before this work — no pickle path existed. Operator
decision 2026-07-27: build it behind a hardened boundary rather than decline it or use a
non-executable format.
- [x] D-b — **Post-restore reconciliation.** ✅ 2026-07-27. `restore()` now reconciles against the
      **live namespace** and returns/stores `{restored, unavailable, claimed, dropped_at_save}`
      (`state.py`), `get_state()` renders a `## Not Restored (do not reference these — rebuild if
      needed)` section so the model is told what is missing rather than only what is present, and the
      executor reports the reconciled count. Tests: `TestRestoreReconciliation` (5 cases) in
      `tests/unit/test_repl_state_extended.py`.
  - [x] D-b1 — **Latent telemetry bug found and fixed.** ✅ 2026-07-27.
        `repl_executor.py` set `restored_globals = len(restore_payload["user_globals"])` — the count
        the checkpoint *claimed*. A name dropped at restore time (builtin collision) was invisible:
        the metric reported success for a variable that never landed. Now sourced from the
        reconciliation, with new `claimed_globals` and `unavailable_globals` fields alongside.
- **[declined: ws58 2026-11-03 content-review: merged into D-c1 — the operator said measure first; the design question is D-c1's decision]** D-c — **Code-log resume.** Carry the executed code log into the resume preamble instead of
      prose findings. **Do not design for this yet** (operator, 2026-07-27): the source's own caveat
      says the code dump only stays cheap when follow-ups add a line or two, and "a session where
      every query does heavy multi-step work is the case to watch" — which is our regime. Rather than
      replicate a synthetic n=1 result, measure it on real traffic and let the cost/benefit decide.
  - [ ] D-c1 — **Measure from real workloads, not a synthetic arm.** Instrument resumed sessions to
        record (a) resume-preamble size with the current prose summary, (b) what a code-log preamble
        *would* have cost, and (c) re-derivation work observed after a resume (repeat greps/reads for
        state that was dropped). T3's hard-workflow/tool-use/REPL probe slice is the natural carrier —
        it is already the exploration target for the current era. Zero added inference: this rides
        traffic that is already running. *2026-11-09 premise update:* no traffic is running (stack off, no writes since 2026-10-03); this box starts when the stack is back (target end of November 2026), and the carrier must be the relaunch era's T3 slice. Decision rule (absorbs D-c, D-c2 and D-e1): if the measured re-derivation work after a resume exceeds the cost of a code-log preamble on real traffic, design D-c (code-log resume) and revisit the 12/8 defaults in the same change; if it is negligible, close D-c and D-e1 here with the numbers.
    - 2026-11-02 readiness audit: the code-log instrumentation in `REPLState` is not the full
      measurement. `Checkpoint` and both production checkpoint constructors omit `code_log` and
      `code_log_metrics`, so they do not survive that persistence path; the audit also found no
      paired rendered-preamble sizing or post-resume re-derivation attribution. Implement and test
      transport and measurement, including belief write-side capture, before collecting on a
      verified real-traffic carrier. The backlog's CPU-row classification does not override the
      zero-added-inference requirement. [no-belief: source inspection; no measurement collected]
  - **[declined: ws58 2026-11-03 content-review: merged into D-c1 as its decision rule]** D-c2 — Decide D-c on D-c1's numbers, or close it if the measured re-derivation cost is
        negligible.
  - **M-MP1 (monitor, 2026-10-30 intake) — pointer-only cross-session resume as a D-c variant.** Mainplane continues a session with one sentence plus the old session's log path and no summary (intake-2523). Our resume path returns summary + findings (`build_resume_context`, `src/api/routes/sessions.py:171`), and past-session search (`SQLiteSessionStore.search_sessions` / `search_by_embedding`, `src/session/sqlite_store.py:1449,1572`) is reachable only from the API/CLI, not the REPL. Trigger: D-c1 resumed-session numbers exist AND tool-output-compression TOC-MP-4 shows pointer-only recall >= summary+pointer. Then file a D-c arm that resumes from the log pointer alone and exposes past-session search to the REPL. No checkbox until the trigger fires.
- **[declined: ws58 2026-11-03 content-review: no workload demand named; by its own text lowest priority with an existing substitute (variable_lineage); the admission-gate spec stays readable here]** D-d — **Curation layer.** An agent-facing annotate/pin call layered over the existing auto-save,
      plus comment-to-variable binding. Lowest priority — we already have `variable_lineage`.
  - **D-d acceptance (added 2026-09-26, research intake).**
    - *Admission gate for shared or pinned notes.* A deterministic grounding check comes first: a note's cited span must appear verbatim in its source, and a note that claims a result must reference an execution present in the session record. Only after that, an optional worker-tier semantic check. Admission is never routed to the architect. The one ablated DeLM component is admission verification (LongBench-v2, GPT-5.4, a single model; 60.1 → 55.2 without it) [intake-1803#6]; its cheapest form is a verbatim reference check [intake-1803#4]. Cost bound (intake-1820#1, intake-1820#3, intake-1820#4): writes are event-triggered (a subtask result or a new grounded fact), never every step; the verbatim-anchor check runs against the writer's own tool/REPL output at 0 LLM calls; summary/gist compression and any LLM faithfulness stage stay OFF unless an A/B on a fact-pooling workload shows they pay; budget ≤1 extra model call per admitted note. The only independent cost curve for a DeLM-style board (synchronous, every agent writes every step, 5N calls per round) runs 10.8–12.6× no-communication at every N, and its one win is fact pooling.
    - *Any notes block injected into delegated or REPL-worker prompts is a prefix by construction:* rendered append-only, byte-identical across viewers, and placed before any per-worker, per-step or tools content. Acceptance is a static check that the rendered block is a prefix-stable function of the note log, plus a reuse reading from `/slots` `n_prompt_tokens_cache` / `timings.cache_n` (`wiki/benchmark-methodology.md:1870`). DeLM's released prompts break all three conditions — the dive overturned the paper's own prefix-placement claim [intake-1803#record]; that is the failure mode this guards against. The migration-side analogue is `dynamic-stack-concurrency.md` "(Z) Guard the prefix-stability assumption"; do not fork it.
    - *Belief kernel (rigor, 2026-09-26):* When D-d is built, file a VB row for the `/slots` reuse reading before its first run (the repl-turn-efficiency.md :159 measurement has none today).
- [x] D-e — **Truncation caps.** ✅ 2026-07-27 (justified, not raised). Extracted to named
      `MAX_RESUME_VARIABLES` / `MAX_RESUME_SKIPPED` constants and made them per-call overridable on
      `format_for_injection()`; `0` means no limit. **Defaults deliberately left at 12/8** — raising
      them changes live prompt content for every resumed session, which is a measured decision, not a
      default flip. Also fixed a real defect while there: the skipped-variable list was truncated to
      8 with **no elision indicator**, so a session with 30 dropped variables silently claimed 8; it
      now reports `(and N more)`.
  - **[declined: ws58 2026-11-03 content-review: merged into D-c1 (its own text says fold it there)]** D-e1 — Decide whether to raise the 12/8 defaults. Same evidence question as D-c
        (prompt-size vs re-derivation cost) — fold into **D-c1's real-workload measurement**, not a
        synthetic arm.

#### Open Questions

- Does a pickle tier introduce a deserialization surface we are unwilling to accept for
  model-authored objects, even with a size cap? (D-a is gated on this answer, not on effort.)
- Is source-serialization of REPL-defined functions safe given that restore re-executes definitions?
  fast-rlm's stated invariant is *"saved code is shown, never re-executed"* — with function/class
  definitions the sole exception, justified as deterministic.

#### Security review (2026-07-27, on the implemented diff)

Reviewed as a deserialization-of-untrusted-input surface: the pickled objects are authored by
model-written REPL code, and unpickling happens in the orchestrator API process.

**Four layers, each independently verified:**

1. **`find_class` allowlist** (load-bearing). Only explicit `(module, name)` pairs from
   `ALLOWED_GLOBALS` resolve. Verified: a `__reduce__` returning `(__import__, ("os",))` is rejected;
   so is one returning `eval`; so is a hostile object nested inside an object-dtype numpy array; so
   is a correctly-HMAC-signed hostile blob. Model-defined classes live in `__main__`, which is not
   allowlisted, so they cannot be reconstructed at all.
2. **HMAC** over the blob — tampering at rest only. It does not establish content safety, because we
   are the ones pickling model-authored objects. Layer 1 is what makes content safe.
3. **Size cap**, checked from the encoded length before decoding.
4. **AST rule** refusing REPL code that binds a serialization hook.

**Four issues found during review and fixed before landing:**

- **numpy `multiarray.scalar` nested-unpickle gadget.** An object-dtype scalar carries a nested
  pickle in its data buffer that numpy deserializes with plain `pickle.loads` — escaping the
  allowlist entirely. Installed numpy (2.4.4) already refuses it, but that is a *numpy-version-
  dependent* invariant this allowlist must not silently rely on. Now wrapped by
  `_guarded_numpy_scalar`, which rejects object dtypes itself. `scalar` cannot simply be dropped from
  the allowlist — it is required for numpy scalar values such as `np.int64`, though not for arrays.
- **HMAC key race producing an empty key.** The original `O_CREAT|O_EXCL` write published a
  zero-length file before writing; a concurrent worker calling `exists()` in that window read `b""`
  and would have used an *empty, guessable* HMAC key. Now written to a private temp file and
  `os.replace`d atomically, so a reader sees either no file or the complete key.
- **`.strip()` on raw random key bytes.** A 32-byte random key can begin or end with whitespace
  bytes, which `strip()` would silently remove. The key is now hex-encoded on disk, and a short or
  unparseable read is rejected rather than used.
- **Two layer-4 AST bypasses.** The hook could be bound without a `FunctionDef` — via a class-body
  assignment (`__reduce__ = lambda ...`) or `type('C', (), {'__reduce__': ...})`. Both measured as
  passing, both now flagged. Layer 1 held in each case; this was defense-in-depth only.

**Residual risk (tracked, not blocking):**

- The allowlist is a standing invariant, not a one-time check — hence D-a3. Anything added with a
  nested-deserialization path reopens the class of issue found in numpy `scalar`.
- HMAC provenance is meaningful only while the key file stays readable by the orchestrator user
  alone (created 0600). A host-level compromise that can read it can forge envelopes — but such an
  attacker already has the process.
- `dumps()` validates by round-tripping through the allowlist unpickler, so construction happens at
  *save* time as well as restore. Same allowlist, same process, no additional privilege — noted so
  it is not mistaken for a pure-validation step.

#### Security review — round 2 (2026-07-27, adversarial): the boundary was BROKEN

An adversarial agent was asked to break the boundary landed hours earlier
(orchestrator `d4f84288`). **It succeeded.** Fixed in `9d30bb60`. Recorded in full because the
lesson generalizes past this module.

**The bypass.** Model-authored REPL code that passes `ASTSecurityVisitor` could produce a checkpoint
variable that, once signed and restored, dereferences an attacker-controlled pointer in the
orchestrator process. Verified end-to-end: `dumps()` accepted and HMAC-signed the object; a fresh
process loading the signed envelope and touching the value exited **139 (SIGSEGV)**.

**Primary defect — "allowlisted" is not "inert".** `numpy.ndarray` was on the allowlist as a nominal
data type. Its constructor form is a memory-corruption primitive:

```python
np.ndarray((1,), dtype('O'), buffer=struct.pack("P", addr))   # element IS the object at addr
```

numpy performs **no** validation on an object-dtype buffer. Round 1 guarded `multiarray.scalar` for
exactly this shape and left `ndarray` unguarded — the guard was written against the *instance*
found, not the *class* of defect.

*Fix*: `numpy.ndarray` now resolves to a **non-callable type token**. A legitimate numpy pickle never
calls `ndarray` — it passes the class as `_reconstruct`'s subtype and fills data via `__setstate__`
(verified against the real opcode stream), so the legitimate path is untouched. `_reconstruct` is
wrapped to unwrap the token and reject any other subtype. Plus `_assert_array_safe`, a
**metadata-only** check (reads `dtype`/`nbytes`, never an element, so it is safe against a forged
pointer) run on every value entering and leaving the module, rejecting object-dtype arrays and
oversize logical arrays.

**Size-cap evasion, same gadget.** `ndarray((4_000_000_000,), dtype('u1'), b'\x00', 0, (0,))` is a
**104-byte** signed pickle describing a 4 GB stride-0 view. The byte cap bounds the *encoded* payload,
never the *logical* object — hence `MAX_ARRAY_BYTES`.

**Secondary defect — layer 4 was bypassable six ways**, all installing a hook with no `FunctionDef`:
a metaclass `__new__` mutating the namespace under a **computed key**
(`ns["__redu" + "ce__"] = fn`), `dict(__reduce__=fn)`, `ns.update(dict(...))`, and subscript
assignment.

*Fix*: reject custom metaclasses and `dict(<hook>=...)`, and extend the subscript check.
The insight: **a computed key can never be caught statically — but it is inert unless the dict is
installed as a class namespace**, and that has exactly two routes (`type(n,b,d)`, metaclass). Both
closed. The module docstring now states plainly that this layer is depth, never the guarantee.

**What held up** (clean results, reported as such): `defaultdict`/`Counter`/`deque` factory abuse —
the factory is only *stored*, never called at unpickle, and `find_class` gates it; numpy object-*array*
contents are inlined in the outer stream so `find_class` catches them; classic nested-list pickle
bombs are defeated by memoization; HMAC is used correctly (`compare_digest`, verified **before** any
unpickling, size checks first); no `dumps`/`loads` parse differential.

**Three lessons worth carrying:**
1. A type on an allowlist is not automatically inert — assess each entry for
   **constructor-reachable primitives**, which is now what D-a3's guard enforces.
2. Guarding the *instance* of a defect (`scalar`) while leaving its *class* unguarded (`ndarray`)
   is how the same bug survives a review. Round 1 did exactly that.
3. "Verify by doing the dangerous work" — `dumps()` validates by actually constructing — means a
   gadget fires at **save** time too, not only restore.

#### Implementation log

**2026-07-27 — D-a + D-b + D-e landed.** Files changed in `epyc-orchestrator`:

- `src/repl_environment/safe_pickle.py` (**new**) — the hardened boundary: `ALLOWED_GLOBALS`,
  `_AllowlistUnpickler` (with `persistent_load` refused and `_guarded_numpy_scalar`), HMAC signing
  with atomic hex key provisioning, 5,000,000-byte cap, `dumps`/`loads`.
- `src/repl_environment/security.py` — `FORBIDDEN_METHOD_DEFS` plus `visit_FunctionDef`,
  `visit_AsyncFunctionDef`, `visit_Assign`, and a `type(..., {...})` check in `visit_Call`.
- `src/session/{models,protocol,sqlite_store}.py` — `pickled_globals` plumbed through the
  dataclass, restore-protocol normalization, and the SQLite schema (with an additive migration and
  a `_json_col` helper tolerating pre-migration rows).
- `tests/unit/test_safe_pickle.py` (**new**) — 31 cases across all four layers, including the
  adversarial ones.
- `src/repl_environment/state.py` — `restore()` returns a reconciliation dict and stores it on
  `_restore_reconciliation`; reconciles against the live namespace rather than trusting the payload;
  `get_state()` gained the `## Not Restored` section.
- `src/api/routes/chat_pipeline/repl_executor.py` — telemetry sourced from the reconciliation; new
  `claimed_globals` / `unavailable_globals` fields.
- `src/session/models.py` — `MAX_RESUME_VARIABLES` / `MAX_RESUME_SKIPPED` constants,
  `format_for_injection()` overrides, skipped-list elision indicator.
- `tests/unit/test_repl_state_extended.py` — new `TestRestoreReconciliation` (5 cases).
- `tests/unit/test_repl_executor.py` — mock updated to the new `restore()` contract and asserts the
  new telemetry fields.

Verification: 31 passed on the new `test_safe_pickle.py`; **929 passed** on
`-k "session or repl or checkpoint or security or pickle"`. No inference consumed; no instrument-era
surface touched. Nothing committed.

#### Notes

Provenance: 2026-07-27 research intake of intake-901, Stage-2 dive D1 against primary source at
pinned SHA `f25f310b` plus a read of our own tree. Full evidence in intake-901 `dive_corrections`.

#### 2026-08-07 — process-safe ownership and uncertain-effect recovery (intake-1009/1010)

- [x] **D-f — Add a cross-process session lease with fencing, not a process-local mutex.** ✅ 2026-09-17 —
  `epyc-orchestrator` `0d6d1dd2`. New `src/session/lease.py`: a `session_leases` table in the existing
  session DB (holder, host, boot id, PID + `/proc` start ticks, monotonic per-session fencing token,
  acquired/heartbeat/expires/released timestamps); acquire runs under `BEGIN IMMEDIATE`; a live lease is
  reclaimable only on expiry or PROVEN owner death (PID gone, PID reused, host rebooted), and a
  foreign-host owner can only expire; heartbeat refuses an expired or reclaimed lease; release is
  idempotent and never frees a successor. `SQLiteSessionStore.update_session`/`save_checkpoint`/
  `delete_session` take `fencing_token` and check it inside the write transaction (a live lease refuses
  unfenced writes; with no live lease they still work), and `save_checkpoint` now bumps
  `last_checkpoint_at` in the same transaction. `_execute_repl` holds the lease for the whole turn and
  fences its save; a session owned elsewhere past the wait budget (`ORCHESTRATOR_SESSION_LEASE_WAIT_S`,
  default 30 s; TTL `..._TTL_S`, 60 s) runs stateless and reports `lease_error`. The sessions API maps
  refusals to 409; reads are untouched. 15 tests in `tests/unit/test_session_lease.py` run the
  mandatory fixtures in real forked processes (6-way simultaneous acquire → one winner; 6 processes ×
  8 leased read-modify-writes → 48/48, where an unleased control kept 8/48; owner crash; delayed stale
  writer refused with no half-write), plus PID reuse / reboot / foreign host via seams and 2 executor
  cases. Original task text: Acquire
  ownership transactionally in the existing SQLite session store using `session_id`, owner identity,
  PID plus process-start identity, monotonically increasing fencing token, heartbeat/expiry, and
  acquired/released timestamps. Every mutating checkpoint/session write must present the current
  fencing token. A stale lease may be reclaimed only after liveness/expiry reconciliation; PID reuse,
  simultaneous acquire, owner crash, delayed stale writer, and idempotent release are mandatory
  regression fixtures. Preserve read-only concurrent inspection.
  - [ ] **D-f1 — Verify the lease under the live 6-worker API** once the API is back up (relaunch target: end of November 2026; the operator owns reload timing): two concurrent
    `/chat` requests on one `session_id` must serialize (second reports a later `lease_token`, both
    checkpoints land, none lost), and `session_leases` must show no live row after both return. In the same live-API check confirm `graph_snapshots` volume under the landed retention defaults (newest 100 runs / 100 rows per run, orch 0151a3dbe) — absorbs D-f3a.
  - [ ] **D-f2 — Decide whether findings, documents and tags are fenced too.** D-f fences the session row,
    checkpoints and delete only; `add_finding`/`add_tag`/`add_document` remain unfenced append-style
    writes. Either fence them or record why concurrent appends are safe.
  - [x] **D-f3 — Fix the graph snapshot writers that never land.** ✅ 2026-09-17 — `epyc-orchestrator`
    `f853764f`. The snapshots were NOT routed into `checkpoints`: `get_latest_checkpoint()` drives REPL
    restore, so a snapshot row would shadow the real globals checkpoint, and the turn snapshot is keyed on
    `task_id`, not a session. Instead, a new append-only `graph_snapshots` table has its own writer,
    `SQLiteSessionStore.save_graph_snapshot(run_id, data, snapshot_type, *, session_id, fencing_token)`
    (plus `get_graph_snapshots`). A session-scoped write runs `check_fence` inside the insert
    transaction. `TaskDeps` gains `session_id`/`session_fencing_token`, which `_execute_repl` sets only
    while the turn holds the lease; otherwise snapshots are run-scoped. `SQLiteStatePersistence` takes an
    optional `fencing_token`. Both swallowed-error paths now log at WARNING. A repo-wide grep found no
    other mismatched `save_checkpoint` caller (`PersistenceManager.save_checkpoint(repl_env)` is a
    different API). Tests: `tests/unit/test_df3_graph_snapshot_writes.py` has 9 cases, and 8 fail on the
    old code; one is an AST guard over every `save_checkpoint` call in `src/`. Also updated: the two
    adapter mock tests that asserted the broken call, and the two D-f executor cases, which now pin the
    deps wiring. Original text: `src/graph/persistence.py:_write` and
    `src/graph/helpers.py` (turn snapshot) call `store.save_checkpoint(session_id=..., data=...,
    checkpoint_type=...)`, a signature `SQLiteSessionStore.save_checkpoint(checkpoint)` has never had;
    the `TypeError` is swallowed at debug level, so those snapshots are silently dropped (pre-existing,
    found 2026-09-17). Route them through a real snapshot write (fenced) or delete the dead calls.
    - **[declined: ws58 2026-11-03 content-review: merged into D-f1 — source landed 2026-10-30; only the live-volume confirmation remains and it rides D-f1]** **D-f3a — Give `graph_snapshots` a reader or a retention bound.** [too-big: source landed; live API volume confirmation belongs to D-f1 owner] Nothing reads the table yet
      (`SQLiteStatePersistence.load_next()` is still `None` by design, TM-7). With
      `STATE_HISTORY_SNAPSHOTS` on, it grows by one row per turn without bound. Either wire a consumer
      (trace/debug view) or add a prune (keep the last N runs), and confirm the volume on the live
      API as part of D-f1.
      Source implementation published 2026-10-30 in epyc-orchestrator `0151a3dbe3564a09b0e78e23c1a0b2b0bf2b42b2`: configurable defaults keep the newest 100 runs and newest 100 rows per retained run, including oversized legacy history on the next write. Pruning and insertion share the existing fenced transaction and roll back together. Twenty-three tests cover limits, ties, legacy data, cross-session scope, stale-fence refusal and rollback. Checkpoints, results and native evidence are untouched. The original item remains unchecked until its live API volume confirmation is performed with D-f1; no live database or service was changed. [no-belief: implementation/tooling; live verification remains pending]

- [ ] **D-g — Journal uncertain external side effects before resume can replay them.** Add a durable
  per-action record with stable action/idempotency key, tool and normalized arguments hash, attempt
  number, `prepared|dispatched|confirmed|failed|uncertain|reconciled` state, timestamps, result/evidence
  reference, and reconciliation policy. Persist `prepared` before dispatch and terminal evidence after
  return. After a crash between dispatch and confirmation, resume must not blindly repeat: probe the
  external state or require an explicit retry/skip resolution, append the reconciliation outcome, and
  retain the original uncertain row. Test crashes before dispatch, after dispatch, after effect but
  before confirmation, duplicate callback, and non-idempotent tool behavior.
  - **D-g mutation acceptance refinement (operator-approved intake, 2026-10-04):** Before mutating
    capabilities are admitted, worker death cannot undo a dispatched parent effect; record
    prepared/dispatched/confirmed/uncertain state and reconcile before retry. Preserve the existing
    journal states, evidence and crash fixtures above. This refines D-g, not a second implementation.
    Contract: [approved P2 operational integration](../../research/intake-stage3-plan-2026-10-03-decision-tools.md#p2-operational-integration--contain-execution-then-exercise-monty-on-real-operations)
    at `3911ec91`, “Dependencies, execution and broader work”.
- [ ] **D-h — The namespace digest is NOT a rendering job; shape capture must be ADDED first**
  (intake-1316#record). `variable_lineage` records name, type, provenance and tier but **never
  shape** (`state.py:450-462`, re-verified 2026-09-07), so a digest built from lineage alone
  would silently lie about shape. Worse, lineage is written only for variables surviving the
  checkpoint filter, so such a digest would omit exactly the un-picklable variables most worth
  naming. Note that the source's own digest is weaker than its paper claims (name/type/SIZE, a
  delta appended to the cell result, not a full listing prepended to every call) — we are not
  copying a validated design, we are building the thing the paper describes.
  - **Comparator rendering (D-RI-PREVIEW-1, 2026-10-21; intake-2245#record).** Before any digest renderer is built, evaluate the bounded-preview grammar `name = type(len=N, first k: [...], last k: [...])` with the TRUE length stated, against today's `get_state()` rendering (`src/repl_environment/state.py:61`: name, type and `repr[:80]`, no true length). Renderings in the comparison: `current`, `bounded_k3`, and `half_first25` (the test case itself: first half of the batch shown, length not stated). The grammar's fit to model training data is the source authors' assertion; it is tested on our served worker roles, not assumed.
  - **Test case.** A 50-item batch whose visible half hides a rule (items 25-49 add returns, tag R, that subtract). Task: net quantity over the whole batch. The scorer separates three failures mechanically from the final answer: `retyping_loss` (answer equals the net over only the items the model could see and copy), `blind_rule_fit` (answer equals the rule fitted on the visible half applied to everything), and `correct`. Per role x rendering: correct / blind_rule_fit / retyping_loss / other counts, with the sample size stated. Fixture and scorer exist: `epyc-orchestrator` `tests/fixtures/repl_preview/batch50.json`, `scripts/benchmark/repl_preview_fixture.py`, `tests/unit/test_repl_preview_fixture.py`. The inference run takes its own window.
- [ ] **D-i — Enumerate and BOUND every kernel-to-context channel; make auto-rendering of the cell
  final expression opt-IN** (intake-1316#record). Do **not** adopt "make `print` the sole
  kernel-to-context egress": the source does not implement it (seven channels; the final
  expression is auto-printed by default and the model must opt OUT). The reframed version is
  strictly stronger than the source and equally cheap.

#### Research Intake Update — 2026-10-04

Operator-approved [P2](../../research/intake-stage3-plan-2026-10-03-decision-tools.md#p2--preserve-repl-state-and-contain-unbounded-execution) at `3911ec91`. Its pinned code evidence and acceptance conditions are part of this filing. The constructor/timeout repairs are independent of backend adoption; containment precedes the comparative Monty slice.

- [x] **D-RI-PICKLE-PASS — Preserve pickled_globals through both existing checkpoint constructors.** ✅ 2026-10-06 — [Contract](../../docs/reference/signed-checkpoint-payload-transport.md), APPc61c4e8e/ROOT881afccf; original37465024500 TRUE116/116 after MAIN3361Git+2context/all3371original custody review. Both producers/SQLite/restore/tamper/unsupported controls, combined persister caps and deterministic eviction; existing signed boundary/fencing unchanged. Prior setup/collectionNULL preserved; no live session/model/kernel/host tests.
- [x] **D-RI-TIMEOUT-STATE — make timed-out REPL terminal for reuse and persistence.** ✅ 2026-10-06 — [Contract](../../docs/reference/repl-terminal-timeout-state.md), original37469999403 TRUE123/123 after MAIN3369Git+4contexts/all3431original-member review; APP733623f4/ROOTf8ba8487. Sticky timeout rejects reuse/checkpoints, suppresses FINAL/artifact rescue; bounded late-worker and lease cleanup controls. No worker termination/host-effect isolation or live lease acceptance.

**Acceptance and consumers.** Tests must fail against the current constructors and timeout path, then pass through the real existing store boundary. Include legacy checkpoints, tampering, lease/fencing loss and a delayed-worker case; never use an infinite background fixture. Consumers are /chat resume, SessionPersister and graph REPL execution. No model calls or holdout are needed for these deterministic invariants.

##### Contained CPython and restricted Monty slice

- [ ] **D-RI-CONTAIN — Add a killable, resource-limited CPython execution lane behind the existing REPL interface.** Keep an opt-in spawned/exec'd child warm across a request's cells; acquire the existing session lease before restore. Keep SQLite, signing and fenced persistence in the parent. Initially support JSON-compatible restored state, existing text/context operations and explicitly bounded read-only capabilities; refuse unsupported state, mutations and unbounded callbacks. Broker existing callbacks as bounded value messages with parent-owned authorization, request identity, deadline and lease revalidation; never serialize callable authority. Reuse pinned sandbox launch/teardown mechanisms with private scratch, no direct network/secrets/session-DB access, finite CPU/memory/file/fd budgets and bounded output/IPC before accumulation. Use owned cgroup process/memory limits, not a small UID-wide process limit. On timeout, cancellation, lease loss or crash revoke callback admission, terminate/reap only the captured child, verify owned descendants are gone, reject late replies and resume from the last completed checkpoint. Fail closed if required containment controls are unavailable; never silently fall back to inline execution. Validate successful-cell, state, FINAL/artifact and callback parity; preserve the existing full CPython path outside this explicitly selected lane.
- [ ] **D-RI-MONTY-SLICE — Implement and run a restricted Monty adapter on twelve existing EPYC REPL cases.** Return the existing ExecutionResult shape and exercise persistent feeds for peek/grep, list/dict/comprehension, artifact/FINAL and state-continuity operations; bridge only their bounded existing callbacks. Compare warm standard CPython, contained CPython and the pinned OSS Monty runtime on identical code/inputs where supported, recording adaptations and refusals. Begin with JSON checkpoint export/import through the existing parent boundary, not opaque Monty dumps. Include denied/delayed callbacks, terminal resource errors and worker disposal. Retain the runnable adapter if it preserves admitted semantics and offers a useful containment or overhead tradeoff; do not enable it by default or infer whole-REPL fitness from this slice.
- [x] **D-RI-PREVIEW-1 — Bounded-preview grammar comparator for D-h and the blind-generalisation test case.** Append to D-h, as a comparator rendering to evaluate before a digest renderer is built: the preview grammar type(len=N, first k, last k) with the true length stated (today `get_state()` at `src/repl_environment/state.py:61` shows name, type and repr[:80], no true length), plus a test case where a preview shows only half of a 50-item batch on the served worker role and the run counts blind rule-fitting and retyping loss. The fit of the grammar to model training data is the authors assertion, so it is tested on our served worker roles (intake-2245#record). The inference part takes its own window. Acceptance: the comparator is specified in D-h and the test-case fixture exists. Estimate: 0.5 day plus a window. ✅ 2026-10-21
  - 2026-10-21 (fillers-3c4ca599): registered as queue item `s5-dripreview1` (NOT armed, bundle): model driver missing (fixture and classify() exist).
  - 2026-10-21 (queue-builders-3; orchestrator `5eef71f0`, `9159e317`, pushed) model driver, role set and sample size built and frozen: `scripts/benchmark/run_repl_preview.py` (per role x rendering tally with `classify()`, isolated execution of the reply code, `WINDOW_CONFIRMED=1`, port-ownership proof, resumable `--cell-dir`, `--mock`), spec `artifacts/queue-builders-3-20261021/dripreview1/PREDECLARED.md` (root, frozen before any run). Role set decided: ONE role `worker_general`, because the registry binds worker/worker_general/worker_math/worker_explore/worker_summarize/frontdoor to the single GGUF Qwen3.6-35B-A3B-MTP-Q8_0; n = 30 per cell x 3 renderings, temp 0.7, one fixture batch (so it generalises to this batch only). Decision: becomes a FILLER (`s5-dripreview1`, cpu, private server on :9461, correctness-class, resumable) via `scripts/benchmark/dripreview1_filler_job.sh`, tested under the real `filler_run.sh` with a stub region-lock and a fake server (pid captured, own-port proof, torn down dead). Launcher not yet started (needs the pushed job in the shared clone). Belief wiring: VB-DRIPREVIEW-WRITE before the result is filed. The inference run itself is not done; this entry ticks nothing.
  - 2026-10-27 harvest (s5-dripreview1, ended 2026-10-22T09:22Z rc 0): **run is INVALID, no comparator result exists.** `/mnt/raid0/llm/tmp/dripreview1-out/result.json` (`complete: true`, n=30 per cell, worker_general x {current, bounded_k3, half_first25}, temp 0.7) scored 0/90 `correct`, 0/90 `blind_rule_fit`, 0/90 `retyping_loss`, 90/90 `no_answer` with `how=bad_final` in every cell (`run_reply` found no int/str `FINAL(...)` value: FINAL never called or non-scalar), against fixture expectations correct 965 / retyping_loss 10, 91, 550 / blind_rule_fit 1725; every reply was 33 tokens (server.log) and replies were not retained, so the cause is unverified. A degenerate all-`no_answer` tally cannot rank the renderings and is not a null for the preview grammar. [no-belief: invalid run, scoring harness returned no classified reply]
  - [ ] **D-RI-PREVIEW-1.1 — fix the scorer/driver defect behind 90/90 `bad_final`, then re-run `s5-dripreview1` once.** (a) Retain the raw reply text in each `cells/*.jsonl` row and replay 3 replies through `run_reply` to see whether FINAL is missing, called with a list/None, or the model emits a non-```python block; (b) add a guard that voids a cell when `no_answer` exceeds a predeclared share (suggest 20%) instead of reporting a tally; (c) re-arm the filler (cpu, :9461, ~5 min, correctness class) and read `result.json` against `PREDECLARED.md`. Filed 2026-10-27 harvest.
    - 2026-11-02 readiness audit: the old replies were not saved, so the precise cause cannot be
      recovered from them. The current driver has no invalid-cell guard and the old launcher
      defaults to the already-complete output directory. Repair and test the driver, predeclare
      the validity threshold, and use a fresh result and cell directory before publication.
      [no-belief: source inspection; invalid run remains uninterpretable]
    - 2026-11-02: root `4cd2010cb3bd` hardens the belief adapter itself: it rejects missing or
      false validity, incomplete role-by-rendering coverage, malformed counts, and any cell
      over 20% `no_answer`, even if invoked independently of the driver. The focused suite
      passed 25 tests. Driver and launcher repairs still need orchestrator integration and the
      rerun remains open. [no-belief: implementation and tests; no comparator result]
    - 2026-11-09 (apr2 prep-memrout): (a) and (b) written on orchestrator branch `apr2/prep-memrout-20261109`: every cell row keeps the raw `reply`, `--replay <cell>.jsonl` re-runs retained replies through `run_reply` and prints the cause, a cell whose `no_answer` exceeds 20% voids the run (`valid:false`, rc 3, stops once more than 6 of 30 are unanswered, never a tally), and the result carries `valid`/`void_cells` (the belief adapter already requires `valid`). Found while publishing: the keeper job env has no `ss`, so the old own-port proof (`ss`, `fl_wait_own_port`) could never succeed; the driver and job now prove ownership from `/proc` (`scripts/benchmark/own_port_proof.py`). Job pins the v10 CPU store binary by sha256 `4483bcfc...b648c` and `--version 10303`, fresh out dir `dripreview1-out-r2-20261109`. Part (c) is the keeper row (rank 22). The cause of the 90/90 `bad_final` stays unrecovered until the rerun's retained replies are replayed. Box stays open. [no-belief: implementation and tests; no comparator result]
  - **2026-11-09 FILED, box stays OPEN, n = 0 (rows `dripreview1-r2-20261109` and `dripreview1-r3-20261109` never produced a measurement):** neither row ever received a grant; both failed the keeper's DRY RUN and were unpublished (`dryrun/<id>/FAIL-1.json` + `unpublished.json`): r2 ended rc=7 after 909 s with no first record; r3 ended rc=4 after 10 s with `port 9461 already listening: not ours, refusing` (a second server held the port during the dry run; the job's own-port proof refused as designed). `out/results.jsonl` is empty in both; no cell, tally or comparator number exists, and the 90/90 `no_answer` cause is still unrecovered. Next step is a fix-and-republish `-r4` (pick a free port or find what holds 9461; dry-run once by hand per the publishing discipline) by the row owner. [no-belief: no measurement]
  - [x] **D-RI-PREVIEW-1.1-R4 — republish the comparator after the r3 dry-run port refusal.** Find what held port 9461 during the 13:47Z dry run, read the r2 rc=7 log (`compute-flags/dryrun/dripreview1-r2-20261109/launcher.out`), then republish as `-r4` with `supersedes`. Done when a granted run writes the 3-rendering x n=30 tally or a valid-false void with replayed replies. ✅ 2026-11-09 rc=3 (granted run, valid-false void): row `dripreview1-r4-20261109` ended `job-rc-3:exited` 16:12Z, `result.json` written with `valid:false, complete:false, stopped:invalid-cell, void_cells:[worker_general|current]`, replies replayed (see the FILED note). Not a model result. [no-belief: void run, driver/prompt finding, no measurement]
    - 2026-11-09 apr2 rerun-fixes (partial, box stays open): what held port 9461 at 13:47Z was the r2 smoke (same port, 13:37 to 13:52, rc=7 own-pid proof without `ss`), still running when r3's smoke started, so r3's own refusal (`port already listening: not ours`, rc 4) was correct. r4 `dripreview1-r4-20261109` uses its own port 9463, fresh out dir, pin orchestrator `apr2/rerun-fixes-20261109` @ `6fa88ace`; published (rank 22, supersedes r3), smoke queued. Rule: a row's rerun never shares a port with an id whose smoke is in flight. [no-belief: not-a-result]
    - **2026-11-09 FILED, parent D-RI-PREVIEW-1.1 stays OPEN (row `dripreview1-r4-20261109`: `.ended` rc=3, no `.complete`, because the driver voided the run by design, not a crash):** first attempt (cpus 76-79) ended rc=75 with no cell; the second (cpus 48-71) generated 7 of the 90 calls in the `worker_general|current` cell, all 7 `no_answer` (`bad_final`), crossing the 6-of-30 stop threshold, so the driver wrote `valid:false`, rc 3, and skipped the belief sidecar (`belief_status: skipped partial result`). The other two renderings never ran, n = 0 valid cells, no tally and no comparator number. Cause (replayed the 3 retained replies through `run_repl_preview.py --replay`, python only, no model call): all 7 retained replies are the same line, ```FINAL = sum(item['qty'] if item['tag'] == 'S' else -item['qty'] for item in batch)```. The model writes `FINAL = ...` (an assignment) instead of the call `FINAL(<integer>)` the prompt asks for; the assignment rebinds the harness's injected `FINAL` function in the exec namespace, nothing is appended to the output list, and `run_reply` scores `bad_final`. That is a prompt/scorer-contract defect (the driver never accepted an assignment), a driver/prompt finding per the box's own rule, not a model result. Also visible and unadjudicated: the 7 replies are textually identical across seeds 1000-1006 at temperature 0.7. [no-belief: void run, driver/prompt finding, no measurement]
  - [x] **D-RI-PREVIEW-1.1-R5 — make the comparator's FINAL contract unambiguous, then re-run once (found 2026-11-09 from r4).** On the worker GGUF Qwen3.6-35B-A3B-MTP-Q8_0 served by the v10 CPU production kernel, replays show the worker model answers with the assignment `FINAL = <expr>` where the harness only honours the call `FINAL(<expr>)`. Pick and predeclare ONE fix before running (the scorer and fixture are frozen, so do not make the scorer accept assignments mid-study): either strengthen the prompt (explicit example `FINAL(42)`, 'FINAL is a function, never assign to it') in a new pre-registered prompt revision, or make the harness bind `FINAL` immune to rebinding and record the assignment form as its own tally class. Then replay 3 replies locally to prove at least one cell yields `answer != null` BEFORE publishing `-r5` (new port, fresh out dir, `supersedes` r4). Done when a granted run writes a valid 3-rendering x n=30 tally or a second valid-false void with replayed replies. [no-belief: native-pending:VB-DRIPREVIEW-WRITE] ✅ 2026-11-10 dripreview1-r5 filed pass: valid, complete, 0 no_answer; worker_general correct current 30/30, bounded_k3 30/30, half_first25 29/30. The FINAL-call prompt fix removed bad_final (r4 had 7/7). All cells are at ceiling, so this one-fixture batch cannot separate the renderings; a harder fixture is needed. Result: /mnt/raid0/llm/tmp/dripreview1-out-r5-20261109/result.json [no-belief: row verdict filed by agent; driver belief sidecar at repl_preview.beliefs.jsonl not yet ingested]
    - 2026-11-09 follow-up (row `dripreview1-r5-20261109` smoke passed, run waiting for a free quarter; box stays open): r4 showed byte-identical replies across seeds at temperature 0.7, unexplained. The R5 result must check this before any verdict: compare replies across seeds per rendering; if they are identical again, treat it as a harness defect (seed or temperature not reaching the server, cache or prompt-cache reuse) and void the run, not read it as a stable model. [no-belief: not-a-result]
    - **2026-11-09 PREDECLARED FIX (R5, before any run; row `dripreview1-r5-20261109`, supersedes r4):** ONE change, a prompt revision, identical in all three renderings and all 90 samples. The fixture task text (frozen) says "set FINAL to the net quantity", which is what invites `FINAL = <expr>`; the wrapper prompt's last sentence becomes: "... ending with a call FINAL(<integer>). FINAL is a function already defined in the REPL: call it, for example FINAL(42). Never assign to it (not `FINAL = ...`)." Chosen over the harness-rebind option because that option still scores assignments no_answer (the run would void again) and, if it accepted them, would change the scorer mid-study. Unchanged: scorer, fixture, `run_reply`, seeds 1000-1029, temperature 0.7, n=30, max_tokens 700, 20% void rule, stop at 6-of-30 no_answer. An assignment reply still scores `bad_final`; nothing is repaired or inferred. The driver is a byte copy of apr2/rerun-fixes-20261109 @ 6fa88ace under `/mnt/raid0/llm/tmp/dripreview1-r5-20261109/driver/` with that one string changed (diff is 2 lines; fixture and port-proof `cmp`-equal to the clean pinned tree in precond). No-model replay: r4's 7 retained replies through r4 `run_reply` = 7 bad_final, through r5 `run_reply` = 7 bad_final (scorer identical, nothing repaired); a conformant `FINAL(sum(...))` reply scores 965 (the fixture value) with how=code; `--mock` through the r5 driver gives no_answer 0 in all cells. Shape: quarter, 24 cores, port 9464, fresh out dir `dripreview1-out-r5-20261109`; decode is bandwidth-bound so no wider width. Note the r4 7 replies were textually identical across seeds at temperature 0.7 (seed handling unadjudicated); if r5 shows the same collapse, report n_distinct replies per cell. R5 stays open until the run reports. [no-belief: predeclaration, no measurement]
  - *(2026-10-21, dpf-specs.)* Comparator specified under D-h; fixture `tests/fixtures/repl_preview/batch50.json`, `scripts/benchmark/repl_preview_fixture.py`, unit test (epyc-orchestrator orchestrator a350b690). The inference run still needs its own window.

**Inputs and six controls.** Freeze twelve cases from the existing REPL environment and artifact/FINAL tests identified in [approved P2 operational integration](../../research/intake-stage3-plan-2026-10-03-decision-tools.md#p2-operational-integration--contain-execution-then-exercise-monty-on-real-operations), capability policy, budgets and runtime/source identities. Use eight development and four untouched acceptance cases plus independently prepared fault fixtures. Compare the current warm persistent CPython baseline and the two explicit lanes; record cold launch, warm cell, checkpoint/restore and teardown separately. Keep per-case outputs, errors, state/FINAL/artifact differences, callback sequence, wall/CPU time, in-window memory, output bytes and verified termination. Count every refusal, incompatible import/state, timeout, crash and missing replay input; distinguish admitted-case parity from total coverage. Predeclare zero incorrect successful results, unauthorized effects, stale writes or unverified teardown; fault fixtures use a one-second deadline and at most two additional seconds for teardown. Timing is descriptive screening evidence, not a twelve-case p95 or production speed claim. A compatibility repair consumes its holdout; use a fresh acceptance set before subsequent activation.

**Dependencies, execution and broader work.** D-RI-CONTAIN follows timeout poisoning and uses the existing D-f lease. Its process/callback/persistence blast radius merits impact review and rollback tests; HIGH/CRITICAL risk would increase safeguards, not erase the task. Monty requires a pinned acquired runtime reconciled with the persisted security corrections. Scientific imports, non-JSON persisted state and arbitrary host callbacks remain explicit coverage limits. No UFH-13 marker prohibits these interpreter-only tests; any later model-bearing comparison uses its actual coordinated window. Before mutating capabilities are admitted, apply the D-g acceptance refinement above. Signed restoration and D-f remain completed; D-f1 retains live lease verification.

**K8 / M2 qualification.** Capabilities, host deadlines, disposal and measured slice coverage govern acceptance; historical fixes are not a security certification. Broader capability expansion requires a specific measured useful workload needing a named missing capability. Default activation requires containment/semantic acceptance and a reviewed cutover. These are durable conditions, not additional checkboxes. New decision-bearing containment/slice probes require the selected producer's write-side capture/projection under [VB-RI-OPS-WIRE](../../research/intake-stage3-plan-2026-10-03-decision-tools.md#approval-and-exact-stage-4-filing-scope) before their first run.

## Track: unified-trace-memory-service
<!-- gate: none -->

> Folded from `handoffs/active/unified-trace-memory-service.md` @ `b1bf3f3f7ade` on 2026-11-02 (BRF-T1-F24, route 1a, operator D1/D5; retired row RTG-41 → EVL-10). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Unified Trace / Memory Service

**Scratch**: `/mnt/raid0/llm/tmp/unified-trace-memory-service/` · worktrees: `/mnt/raid0/llm/worktrees/unified-trace-memory-service-*`

**Status**: T1-T6 LANDED 2026-05-06 — `epyc-orchestrator/src/trace/` package: SQLite store with FTS5 + 5 indices, agent_audit parser (JSON + legacy text dual-format), autopilot parser (no-op-when-absent for hosts without journals), progress markdown parser, query CLI (`python -m src.trace.cli {ingest,query,stats}`), 13 unit tests. Live ingest of 11,963 events (re-counted 2026-09-07) from `/workspace/logs` + `/workspace/progress` in <1s; idempotent re-ingest verified. Note that the append-only property covers the `event` table and its ledgers (INSERT OR IGNORE) but NOT the co-located `working_state` table (`harness_schema.py:570`, `:755` `UPDATE … SET superseded = 1`). T6 received a first-class trial-context API/CLI refresh on 2026-06-28 (`epyc-orchestrator` `d20f85b7`) via `trial_context(...)` and `python3 -m src.trace.cli trial-context --trial N`, returning exact trial rows plus nearby cross-source timeline context. T7 Hermes ingest deferred until Hermes graduates to daily use.
**Created**: 2026-04-25 (from local-RAG architecture review of friend's stack — "Trace / Memory Service" box)
**Categories**: agent_architecture, knowledge_management, autonomous_research
**Priority**: MEDIUM
**Effort**: ~1–2 inference-free days end-to-end (minimal version: read-only query layer over existing logs)
**Depends on**: nothing — read-only over already-persisted logs. Optional incremental ingest is additive.

> **Fable 5 review (2026-06-12)**: this service is the designated substrate for two new programs: [frontier-f1-real-task-corpus.md](../completed/frontier-f1-real-task-corpus.md) task_record capture (W2) and coordination with the per-question eval ledger schema in [evidence-plane-ledger-and-sequential-verdicts.md](autopilot-program.md#track-evidence-plane-ledger-and-sequential-verdicts) — align event schemas before implementing EXM-1.

#### Objective

Collapse the three fragmented audit/trace formats we already write — `logs/agent_audit.log`, `progress/YYYY-MM/*.md` (+ JSONL), and autopilot's `autopilot_state.json` + `autopilot_journal.{tsv,jsonl}` — into a single queryable provenance store with a thin Python/CLI API. After a long autopilot or nightshift run, "why did we decide X?" should be one query, not a walk across three formats with three different schemas.

#### Why This Matters

| Question post-nightshift | Files we currently walk |
|---|---|
| "When did this trial fail and what was the species?" | `autopilot_journal.jsonl` + `autopilot_state.json` |
| "What was the agent doing in the 2-hour window before the regression?" | `agent_audit.log` (timestamps) + `progress/2026-04/2026-04-DD.md` (narrative) |
| "Why was this Pareto entry accepted?" | `autopilot_journal.tsv` (one row per trial) + `journal.jsonl` (full detail) + safety_gate logs in `agent_audit.log` |
| "Which evidence sources were consulted for this decision?" | `progress/` narrative + `agent_audit.log` task starts/ends + (no provenance link) |
| "Did this conversation reference a prior session's findings?" | Hermes `MEMORY.md` + our `progress/` — no shared timeline |

Three data points, three formats, no join keys. The gap is acute during autopilot debugging (per `feedback_phased_plan_gates.md` — "Long multi-phase plans MUST re-audit at phase start") and during multi-day handoff continuity.

#### What "Unified" Means Here

A read-only **query layer** over the existing files — not a replacement, not a migration. The source files keep their current writers (`agent_log.sh`, autopilot's `experiment_journal.py`, the progress markdown convention). The new layer:

1. Ingests on demand from the existing files (or incrementally via tail-watch).
2. Normalizes records into a single SQLite schema with stable join keys (timestamp range, session_id, trial_id, role, file_path mentioned).
3. Exposes a small query API and CLI.

This is **not** a memory architecture upgrade for autopilot or Hermes — both retain their domain-specific stores (autopilot's `repl_memory/strategy_store.py`, Hermes's `MEMORY.md`). The unified service is for cross-source *provenance queries*, not for production routing or evolutionary memory.

#### Sources to Ingest

| Source | Format | Cadence | Granularity |
|---|---|---|---|
| `logs/agent_audit.log` | tab/space-separated text | streaming (append on every `agent_task_start/end`) | per-action |
| `progress/YYYY-MM/YYYY-MM-DD.md` | markdown narrative | manual (post-session) | per-day session summary |
| `progress/YYYY-MM/YYYY-MM-DD.jsonl` | JSONL (where present) | streaming during sessions | per-task |
| `epyc-orchestrator/orchestration/autopilot_journal.tsv` | TSV | per-trial | per-trial summary row |
| `epyc-orchestrator/orchestration/autopilot_journal.jsonl` | JSONL | per-trial | full per-trial detail |
| `epyc-orchestrator/orchestration/autopilot_state.json` | JSON snapshot | per-trial | controller state at trial boundary |
| (optional) Hermes `~/.hermes/sessions/*.json` | JSON | per-session | conversation transcript + tool calls |

**Schema (minimum viable)**:

```sql
CREATE TABLE event (
  id INTEGER PRIMARY KEY,
  ts_utc TEXT NOT NULL,           -- ISO8601 with microseconds
  source TEXT NOT NULL,           -- 'agent_audit' | 'progress' | 'autopilot_journal' | 'autopilot_state' | 'hermes_session'
  source_path TEXT NOT NULL,      -- file the record came from
  source_line INTEGER,            -- line number where applicable
  session_id TEXT,                -- agent_log session UUID, autopilot trial id, etc.
  trial_id INTEGER,               -- autopilot trial number where applicable
  role TEXT,                      -- orchestrator role / species / agent task type
  category TEXT,                  -- task_start | task_end | mutation | safety_verdict | pareto_accept | session_summary | ...
  status TEXT,                    -- success | failure | skip | null
  summary TEXT,                   -- short human-readable line
  detail_json TEXT                -- full record as JSON for downstream parsing
);

CREATE INDEX event_ts ON event(ts_utc);
CREATE INDEX event_session ON event(session_id);
CREATE INDEX event_trial ON event(trial_id);
CREATE INDEX event_source ON event(source);
```

Two virtual tables (FTS5) for full-text search across `summary` and `detail_json`.

#### Architecture (proposed)

```
existing writers (unchanged):
  agent_log.sh ──> logs/agent_audit.log
  experiment_journal.py ──> autopilot_journal.{tsv,jsonl} + autopilot_state.json
  manual / hooks ──> progress/YYYY-MM/*.md + .jsonl
                                      │
                                      ▼
                       ┌──────────── ingest workers ─────────────┐
                       │  parse → normalize → upsert into SQLite │
                       └───────────────────┬─────────────────────┘
                                           ▼
                                  data/trace/events.sqlite (+FTS5)
                                           ▲
                       ┌───────────────────┴─────────────────────┐
                       │  query CLI / Python API                  │
                       │   - by time range                        │
                       │   - by session_id / trial_id             │
                       │   - by role / category / status          │
                       │   - full-text over summary + detail_json │
                       └──────────────────────────────────────────┘
```

**Ingest model**: idempotent batch from current file state on every invocation (small enough corpus that a full re-ingest takes seconds). Optional `--watch` mode (inotify or polled tail) for live append. Records are keyed by `(source_path, source_line)` for dedup.

#### Work Items

- [x] **T1: Schema + ingest skeleton** — `epyc-orchestrator/src/trace/store.py` with the SQLite schema above + `ensure_schema()` + idempotent upsert helpers. Unit tests on synthetic records. ~2 h.
- [x] **T2: agent_audit.log parser** — Parse `logs/agent_audit.log` produced by `scripts/utils/agent_log.sh` (lines like `[ts] [session_uuid] [task_name] [status]`). Emit normalized events. ~2 h.
- [x] **T3: autopilot journal parser** — Parse `autopilot_journal.tsv` (one row per trial) + `autopilot_journal.jsonl` (full detail). Cross-link via `trial_id`. Optionally include `autopilot_state.json` snapshots as `category=controller_snapshot` events. ~2 h.
- [x] **T4: progress/ markdown parser** — Walk `progress/YYYY-MM/*.md` for date-keyed sessions; treat each top-level `## ` heading as a session record with `summary` from the heading and `detail_json` from the section body. Where a sibling `.jsonl` exists, prefer that for granular events. ~2 h.
- [x] **T5: CLI + Python API** — `python -m epyc.trace query [--from TS] [--to TS] [--session ID] [--trial N] [--role R] [--category C] [--text "..."] [--limit N]` returning ranked event rows. Python module exports `query(...)` returning dicts. ~2 h.
- [x] **T6: Cross-source join recipes** — Document 3–4 high-value recipes in the handoff body or a `docs/` page: (a) "all events for trial N" (autopilot + agent_audit by time range), (b) "session timeline for date D" (progress + agent_audit), (c) "all failures + their preceding 5 actions". ~1 h. **2026-06-28 refresh**: `trial_context(...)` and `python3 -m src.trace.cli trial-context --trial N` now provide the primary trial recipe directly, with exact trial events and configurable nearby agent/progress/autopilot context.
- **[declined: ws58 2026-11-03 content-review: unbounded watch — gated on Hermes entering production use, which nothing schedules; ~2 h to refile if it ever does]** **T7 (optional): Hermes session ingest** — Walk `~/.hermes/sessions/*.json` if present, normalize into events. Gated on whether Hermes goes into production use (currently CLI-only validation). ~2 h. Defer until Hermes outer-shell graduates from validation to daily use.
- [x] **UTM-P1 — Add pairing keys to the unified trace event schema**: harness identity, seed, and a horizon/turn ordinal, at `src/trace/store.py:94-197`. Today **two runs cannot be paired on the same task across harnesses at all**, and `EventSource.HERMES_SESSION` (`store.py:36`) is a declared constant with **no ingester and no producer** — the dead constant is T7's stub. This blocks ANY cross-harness comparison, not just one metric, and it bites the moment HS-4 closes and a second harness goes live (soft-blocks HS-4 follow-through). **Schema-only change, no inference.** `intake-1341#04`. Zero compute. ✅ 2026-09-17 — orchestrator `dd24ed10` (on `origin/main`): event schema v2 adds nullable `harness` / `seed` / `turn_ordinal` / `task_key` plus a per-row `schema_version` (`src/trace/store.py` `EVENT_SCHEMA_VERSION`, `EVENT_PAIRING_COLUMNS`, `migrate_event_pairing_columns`). v1 stores migrate by idempotent additive ALTER with no back-fill (legacy rows read `schema_version` NULL = "never captured"); `query()` NULL-projects the columns on an unmigrated store and gains pairing filters; new `paired_runs(task_key, seed=...)` returns `{turn_ordinal: {harness: [events]}}`; the live-emit content key includes the pairing keys only when set (pre-v2 keys unchanged); `ReviewTracingProcessor` threads `harness`/`seed`/`task_key` from `Trace.metadata` and `turn_ordinal` from span data. `task_key` was added beyond the three named keys because "same task" has no other cross-harness identity. Tests: `tests/unit/test_trace_pairing_keys.py` (13); 180 adjacent trace/ledger tests green.
  - [x] **UTM-P1a — wire producers to stamp the pairing keys**: no live producer sets `harness`/`seed`/`turn_ordinal`/`task_key` yet (the AutoPilot live push `autopilot_live` and the eval tower are the first candidates; the file ingesters have nothing to stamp). Until one does, `paired_runs()` returns `{}` on the real store. Zero compute.
    ✅ 2026-09-17 (orchestrator `9a7181f2`) — **first producer wired: the review plane**
    (`ArchitectReviewService`, all 12 emit sites, source `review_plane`). Chosen as the cheapest HONEST
    producer after checking the two the box named: `autopilot_live` can stamp only `harness` (a `JournalEntry`
    has no RNG seed, no turn index, and `trial_id` is autopilot-only), and the eval tower emits no trace events
    at all today. The review plane already emits live AND carries a real cross-harness identity in
    `TaskIR.task_id`. Stamps `harness` on every row (injectable; `None` → NULL), `task_key` on `review()` as
    pass-through of `spec["task_id"]`, and `turn_ordinal` from `step_index` on `build_plan_reminder`.
    Everything else stays NULL = "never captured" — in particular **`task_key` is never derived from
    `subtask_id`** ("S1" recurs across unrelated tasks; a fabricated key would silently pair unrelated runs,
    which is worse than an empty pairing). `src/trace/` needed no change. 24 tests, including two harnesses
    pairing through a real store and legacy v1 rows reading back unstamped beside new ones.
    - [x] **UTM-P1a.2 — second producer, so `paired_runs()` is cross-harness on real data.** Three named
      candidates: `review_replay_50.py` passing `harness="review_replay"` + `task_key=q["task_id"]` (needs
      `review_candidate` to accept `task_key`) so replay pairs against live on the corpus id; the delegator
      passing its review-iteration index as `turn_ordinal`; and UTM-P1b's Hermes ingest using the same
      `TaskIR.task_id` convention. One producer alone can only pair a harness against itself.
      ✅ 2026-09-17 (orchestrator `7887e7ae`) — candidates 1 and 2 wired; UTM-P1b dropped from scope (Hermes was
      not selected). Replay stamps `harness="review_replay"` + `task_key` = the corpus `task_id`; the delegator
      passes its per-step review-iteration index as `turn_ordinal`. Deliberately NOT stamped: the RD-10b
      final-aggregate review and the parallel step executor, both one-shot — a `0` there would be an invented
      ordinal, so they stay NULL. 8 tests, incl. a real temp store where `paired_runs("rr50-001")` returns both
      harnesses; 302 passed across the adjacent slices.
      - [ ] **UTM-P1a.3 — make the pairing reachable on REAL data.** The keys are now stamped on both sides, but
        three things still stand between that and a real pairing, and none is a stamping problem:
        (a) **separate stores** — replay writes its own `--trace-db` and `run_shadow` *unlinks* a pre-existing DB
        under the TM-8 fresh-run rule, while `paired_runs()` reads ONE `db_path`; needs a non-destructive replay
        mode or a merge/attach step, and the destructive default is the part to decide first;
        (b) **no shared ids** — live tasks carry TaskIR/uuid ids, not `rr50-NNN`, so nothing feeds the pinned
        corpus through the live path;
        (c) **turn alignment** — delegator rows land on ordinals 0..n and replay rows on NULL, so a real pairing
        would be cross-harness but not turn-aligned until replay drives a looped review.
        Running the replay itself needs inference, so this is gated on a window.

  - [x] ~~**UTM-P1b — T7 (Hermes ingest) must stamp `harness="hermes"` plus `task_key`/`seed`/`turn_ordinal`** when it lands, or Hermes rows cannot be one side of a pair.~~ (closed 2026-10-29 audit: OBSOLETE → unified-trace-memory-service.md ~line 131: "UTM-P1b dropped from scope (Hermes was not selected)" (orchestrator 7887e7ae, 2026-09-17))

##### Research intake 2026-10-22 — Locals + Beacon (intake-2386..2460)

- [x] **UTM-LB1 — Verify the existing conversation backup is live and covers each of the nine dev-harness stores, read-only: confirm the nightly cloud-llm-vault sync (02:00Z, immutable), the 14 retained ai-sessions tarballs in claude-backups (backup.log status) and the micron snapshots (keep 60) are current, then check per store whether the vault or a tarball holds it and from which date: Claude Code transcripts with subagent transcripts, ~/.claude/history.jsonl, the Claude memory dirs, Codex rollouts, the Codex state sqlite, opencode.db, the per-agent agent_audit shards and orchestrator logs, serving_calls.jsonl and planner_archive; report every store NOT covered as a gap for the operator; build no parallel backup, copy nothing and change no retention setting (live ~/.claude/projects keeps about 30 days, but the vault retains transcripts from 2026-08-02) (intake-2389, intake-2397).** ✅ 2026-10-22
  - Checker: `scripts/system/backup_coverage.py report|precondition` (read-only; root branch `f8/locals-b1-root-20261022`).
    Job is LIVE: backup.log `STATUS OK` 2026-10-22T02:16:37Z, LAST_STATUS 11:43Z (an extra root-owned run at 11:28Z
    also wrote `opencode-{epyc,host-daniele}-20261022-132850.db.zst` — not logged in backup.log); vault 31G/34194 files
    immutable. Coverage (tarball = `ai-sessions-20261022-132850` listing): Claude transcripts+subagents COVERED (vault
    6681 files, content from 2026-02-03; tarball 1854); Claude memory COVERED (vault 443, tarball 381); Codex rollouts
    COVERED (vault 20548, content from 2026-04-13; tarball 20548); opencode.db PARTIAL (one-off .db.zst only);
    NOT COVERED: `~/.claude/history.jsonl`, Codex `state_5`/`thread_history_1` sqlite, agent_audit shards + orchestrator
    logs, `serving_calls.jsonl`, `planner_archive.jsonl` (all only on raid0 md127; micron snapshots hold the vault only).
    Job anomalies: only 6 of 14 ai-sessions tarballs on disk (Oct 4–17 missing although ROTATE logs "kept 14"); no
    BACKUP/STATUS lines 2026-08-03..10-03 (62 d; rsync code-23 errors on immutable host/claude dirs); host:claude count
    flat at 1714–1715 since 10-04; `/mnt/micron` not mounted in the container (only the log attests 31 snapshots).
  - [x] **UTM-LB1.D — operator decision on the uncovered stores** — operator 2026-10-22: "Ignore this. I'm handling it through my root filesystem agent." Backup coverage is owned outside this repo; no backup work here. NIB2-LB1.2 waits on the operator's root-agent outcome. ✅ 2026-10-22
    Options: (A) extend the EXISTING root cron job's include list to history.jsonl, the Codex state sqlite (online
    `.backup`, not a raw copy of a live WAL db), `/workspace/logs/agent_audit*.log`, orchestrator `logs/` incl.
    serving_calls + planner_archive, and make the 2026-10-22 opencode `.db.zst` step nightly + logged — one job, no
    parallel backup; cost ~+0.5–1 GB/night (opencode zst 0.64 GB, codex sqlite ~8 GB raw → compressed). (B) accept
    raid0-only for the small derived logs (agent_audit 1.9 MB, planner_archive 12 MB, serving_calls 188 KB are
    reproducible-ish telemetry) and back up only history.jsonl + opencode — cheapest, loses audit history on a disk
    loss. (C) status quo — every uncovered store dies with md127; the opencode event reaper keeps pruning an uncovered
    store. Recommendation: (A), plus explain the missing Oct 4–17 tarballs and the 62-day gap. The operator owns the
    root cron job; no agent builds a backup.
    **Update 2026-10-22 (operator, root-filesystem agent delivered):** opencode is now covered by hourly consistent
    `sqlite3 .backup` snapshots, read-only (root:root 0444, `journal_mode=DELETE`, full cumulative history, at most ~1 h
    stale; nightly zstd + 72 hourly copies on `/mnt/micron/opencode-vault`): `/mnt/raid0/llm/opencode-db/{epyc.db,host-daniele.db}`
    (symlink to `/mnt/raid0/llm/opencode/readonly/`). Claude Code + Codex stay in `/mnt/raid0/llm/cloud-llm-vault/{host,twyne,epyc}/{claude,codex}/`.
    **Scope ruling: mine EVERYTHING** — both opencode DBs and Claude/Codex from host, twyne and epyc; every Unit/event/session
    record carries a `source` tag (`epyc|host|twyne`). `backup_coverage.py` counts `opencode_db` as `covered` while the newest
    snapshot is under 3 h old (judged by snapshot freshness, not the nightly job). Mining readers open snapshots only
    (`?mode=ro` + `PRAGMA query_only=1`, one retry, never the `event` table) and REFUSE the live stores
    (`~/.local/share/opencode`, `/mnt/raid0/llm/opencode/<src>/`); `dh_privacy` lists `/mnt/raid0/llm/opencode{,-db}` as never-write roots.
    Code: root `f8/opencode-ro-root-20261022`, orchestrator `f8/opencode-ro-orch-20261022`, research `f8/opencode-ro-research-20261022`.
- [x] **UTM-LB2 — Build the private dev-harness transcript projector reading from the existing backup (cloud-llm-vault copies and the ai-sessions tarballs; live stores only for data newer than the last nightly sync) over Claude Code JSONL, Codex rollouts and opencode V1/V2, read-only, into events with OTel GenAI names in detail_json (operation, tool call id, usage normalized to inclusive OTel input tokens per each harness's convention with the raw tuple kept, conversation and agent lineage), Beacon-style collection_method and observed/inferred fidelity markers, keyed-HMAC 64-token block hashes, Claude usage dedupe by message id, Codex usage read from token_usage_record (never summed token_count), spawn-vs-fork edge kinds, a composite source-schema key per session, the semconv commit stamped, and a session-to-commit join from commit hashes in tool results; outputs private only (intake-2387, intake-2403, intake-2419, intake-2434#record, intake-2438).** ✅ 2026-10-22
  - `scripts/dev_harness/{dh_sources,projector,dh_privacy}.py`; outputs `dev-harness-{event,session,commit-join,projection-run}.v1`
    under `/mnt/raid0/llm/private/dev-harness-traces/projections/<run>/` (0700/0600; content → keyed-HMAC 64-token
    block hashes, key in `keys/`). Semconv stamped `semantic-conventions-genai@9ffc7e00` (gen-ai-dev/1.42.0-dev).
    Sample run `sample-20261022` (8 Claude + 8 Codex + 4 opencode main sessions, 66 units incl. 46 subagents, 16006
    events, 2.2 s, 64 MB RSS, nice 19); 27 tests in `tests/dev_harness/`. The sample read the live db `immutable=1`; since
    2026-10-22 opencode is read from the read-only snapshots `/mnt/raid0/llm/opencode-db/{epyc,host-daniele}.db`
    (`?mode=ro`), default tenant is all of `epyc,host,twyne`, outputs land under `events/<harness>/<source>/` (see UTM-LB1).
  - [x] **UTM-LB2.1 — Full-corpus projector + AgentRun run** under `nice -n 19`, off the inference windows:
    `python3 scripts/dev_harness/projector.py --claude 0 --codex 0 --opencode 0 --max-file-mb 0 --run-id full-<date>`
    then the same flags on `agentrun.py`; the default `--tenant all` already covers epyc, host and twyne plus both opencode snapshot DBs (`--opencode 0`). Estimate from the
    sample (~45 MB/s single core): ~31 GB vault → ~12–15 min each, ~6 GB + ~4.5 GB private output (raid0 has 608 GB).
  - *(2026-10-22 13:33Z, workspace-f8.)* ✅ 2026-10-22 projection COMPLETE, run `full-20261022T1310Z`: 42,744 units (claude_code 4,907, codex 20,547, opencode 17,290), 3.2M events, 4,066 commits joined, 858 s; private output only. Evidence: `/mnt/raid0/llm/private/dev-harness-traces/projections/full-20261022T1310Z/run.json`.
  - [ ] **UTM-LB2.2 — Ingest projector events into the unified trace store** (`src/trace/`, new EventSource for
    dev-harness events, detail_json passthrough, dedupe on (source_path, source_line)), private DB path only.
- [x] **UTM-LB3 — Point the agent_audit ingester at the per-agent agent_audit shard files; its default is the frozen legacy /workspace/logs/agent_audit.log (src/trace/ingest_agent_audit.py:24) (intake-2387).** ✅ 2026-10-22
  - orchestrator `08670ddd` (branch `f8/locals-b1-orch-20261022`): `parse_source()` reads every
    `agent_audit*.log` under `/workspace/logs` (same glob as root `agent_log_files()`), CLI `--agent-audit` takes a
    file or a dir; 18 passed in `tests/unit/test_trace_store.py`.
- [x] **UTM-LB4 — Run one short claude -p session with the console OTel exporter and every content toggle off, to list the fields this harness version emits (ttft, hook events, compaction, agent lineage); persist no setting and change no global env (intake-2419).** ✅ 2026-10-22
  - *(2026-10-22, workspace-f8 / clerical.)* `claude -p` authenticates headless here with no env or settings change. One session (`claude -p "Reply with the single word ok." --max-turns 1`), env on that one command only: `CLAUDE_CODE_ENABLE_TELEMETRY=1 OTEL_METRICS_EXPORTER=console OTEL_LOGS_EXPORTER=console OTEL_METRIC_EXPORT_INTERVAL=1000 OTEL_LOGS_EXPORT_INTERVAL=1000 OTEL_LOG_USER_PROMPTS=0 OTEL_LOG_TOOL_DETAILS=0 OTEL_LOG_TOOL_CONTENT=0`; rc 0, output scratch removed. Content toggles hold: `prompt`, `prompt_text`, `response` all `<REDACTED>` (lengths still emitted: `prompt_length`, `response_length`). METRICS: `claude_code.session.count`, `.token.usage`, `.cost.usage`, `.active_time.total` (attrs: model, effort, query_source, type, start_type). LOG EVENTS (`event.name` + `event.sequence`, `event.timestamp`, `prompt.id`, `session.id`): `api_request` (`ttft_ms`, `duration_ms`, `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_creation_tokens`, `cache_creation_5m_tokens`, `cache_creation_1h_tokens`, `cost_usd`, `cost_usd_micros`, `model`, `effort`, `speed`, `query_source`, `request_id`, `client_request_id`); `hook_registered` (`hook_event`, `hook_source`, `hook_type`); `hook_execution_start` (`hook_event`, `hook_name`, `hook_source`, `num_hooks`, `managed_only`); `hook_execution_complete` (`total_duration_ms`, `num_success`, `num_blocking`, `num_non_blocking_error`, `num_cancelled`, `num_outputs_persisted`, `stdout_chars`, `additional_context_chars`, `system_message_chars`, `initial_user_message_chars`); `user_prompt` (`prompt_length`, `message.uuid`); `assistant_response` (`response_length`, `message.uuid`, `request_id`); `mcp_server_connection` (`status`, `transport_type`, `server_scope`, `duration_ms`, `is_plugin`); `plugin_loaded` (`plugin.name`, `plugin.scope`, `has_hooks`, `has_mcp`, `skill_path_count`, `agent_path_count`, `command_path_count`); `managed_settings_resolved`. Resource attrs on every record: `user.id`, `user.email`, `user.account_id`, `user.account_uuid`, `organization.id`, `service.name`, `service.version`, `terminal.type`, `os.type`, `os.version`, `host.arch` (identifying: strip before any commit). GAPS in this one-turn session: no compaction event, no agent/sub-agent lineage field (no `agent_id`/`parent`), no tool-call events (no tool ran). Those need a longer session with a tool and a sub-agent; `ttft_ms` and hook timing ARE present, which closes the console-field check for those two.
  - [x] UTM-LB4.1 — close the two remaining OTel field gaps: one short `claude -p` session, same per-command env and content toggles off, that runs one tool call (a read-only Bash) and spawns one sub-agent; record the tool-call event fields and whether any agent/sub-agent lineage field (`agent_id`, parent id) appears. Strip resource identity attrs before anything is committed; persist no setting. Cloud tokens only, no local compute. (filed 2026-10-22, f8 evening wrap-up) ✅ 2026-10-24
    - Compaction via OTel: not filed because forcing a compaction needs a context-filling session, and the transcript projector already records compaction boundaries from the JSONL (`dh_sources.py` `compact_boundary` / opencode `compacted` -> `operation=compaction`).
    - *(2026-10-24, workspace-f8 sweep.)* **Ran one `claude -p` session** (CLI 2.1.308, `--model haiku --max-turns 6`, cwd a scratch dir under `/mnt/raid0/llm/tmp`, so no project settings). It used the same per-command env as UTM-LB4, set on that command only, and saved no setting. It made one read-only `ls` Bash call and spawned one built-in general-purpose sub-agent. rc 0, 64 records.
      - **The raw output is deleted.** It carried `user.email`, account/org ids and `session.id` on every record. Only an identity-free field-name summary was kept, in `/mnt/raid0/llm/tmp/f8-utm-lb41-20261024/fields_summary.json`.
      - **Tool-call events.**
        - `tool_decision` carries `tool_name`, `tool_use_id`, `decision`, `source`, `tool_source`, `permission_mode` and `classifier_verdict`.
        - `tool_result` carries `tool_name`, `tool_use_id`, `success`, `duration_ms`, `tool_input_size_bytes` and `tool_result_size_bytes`.
        - The content toggles held: neither event carries arguments or output.
      - **Lineage.** No event carries `agent_id` or any parent id.
        - The sub-agent shares the parent's `session.id`.
        - The only marker on its `api_request` and `assistant_response` is `query_source` = `agent:builtin:general-purpose`, plus `agent.name` on `api_request` and on the token and cost metrics.
        - A new event, `subagent_completed`, carries `agent_type`, `agent.source`, `is_async`, `is_built_in`, `model`, `final_model`, `model_swapped`, `duration_ms`, `total_tokens` and `total_tool_uses`. It has no id that links it to the spawning `Agent` tool call.
        - **Gap:** `tool_decision`/`tool_result` carry neither `query_source` nor `agent.name`. A tool call made INSIDE the sub-agent (it called `SubagentHandback`) cannot be told apart from a parent call. The only way to separate them is the `tool_use_id` join to the transcript JSONL, which does keep sidechain lineage.
      - Other events seen: `managed_settings_resolved`, `mcp_server_connection`, `plugin_loaded` and `retention_sweep`.
      - Bearing on the trigger-gated "Native harness OTel" item: OTel-only fields the transcripts lack are `ttft_ms`, per-request `duration_ms`, tool `duration_ms` and `tool_decision` `source`/`classifier_verdict`. Lineage is the reverse case, a field the transcripts carry and OTel lacks.

Trigger-gated (no checkbox until the trigger fires):
- Local pushback judge calibration and SWE-chat in-the-wild checks — open once the operator labels the 100-item sheet (and, for SWE-chat, provides an HF login) (intake-2397#record, intake-2406#record).
- Anchored replay A/B with a validated local user simulator, trim-vs-full memory index A/B, reactive hook hints, CODESKILL-prompt candidate pilot, precondition-gated session selection, Beacon rubric as a local typed-decision workload, a raw-trajectory arm and the SkillBank student-memory arm — open when the lesson time-series pilot shows a measurable lesson effect or none for prose-only lessons (intake-2396#record, intake-2410#record, intake-2427#record, intake-2431#record).
- Check-after-write in the REPL and tests-as-judge best-of-K — open when recorded sessions show a high test-run step fraction or batched decode supports K>1 (intake-2386#record).
- LLM layer of the local failure-mode clustering (small-model facet extraction and naming via llama-server; OpenClio's prompts as reference, write from scratch because OpenClio is vLLM-bound and Kura has no licence; cluster-purity check on a hand-labelled sample; summary-first fallback) and a local rubric judge or self-hosted Docent viewer — open when the no-LLM baseline (DHM-7) shows clusters worth naming and operator labels exist (intake-2443#record, intake-2444#record, intake-2446#record, intake-2447#record).
- Native harness OTel (hook timing, TRACEPARENT into actors) and semconv re-check — open after the console field check lists gaps the transcripts leave, or when the GenAI spec leaves Development (intake-2403#record, intake-2419#record).

#### Open Questions

1. **Append-only vs mutable**: SQLite is mutable; the source files are append-only-ish. Should the unified store mirror append-only semantics (never UPDATE rows, only INSERT or skip duplicates)? **Tentative answer**: yes — append-only with `(source_path, source_line)` dedup. Easier to reason about, no data loss on re-ingest.
2. **Retention**: keep all history forever, or roll older months out? Source files are already authoritative, so the unified store can be regenerated. **Tentative answer**: keep all history while size is small (<1 GB); add a rolloff policy only if the store grows beyond that.
3. **Hermes session ingest**: do we need it for the v1, or is it a follow-up? **Tentative answer**: defer (T7 marked optional). Not needed until Hermes is in regular use.
4. **Live tail**: is on-demand re-ingest enough, or do we need an inotify watcher? **Tentative answer**: on-demand for v1. Re-ingest cost should stay below 5 s for typical sizes; revisit if it doesn't.
5. **Coupling with autopilot's strategy_store**: autopilot already has FAISS-indexed strategy retrieval (`repl_memory/strategy_store.py`). The unified trace store is **not** a replacement — strategy_store retrieves *insights*, not *events*. Cross-link: include trial_id in both so a strategy_store insight can link back to its source events here.

#### Non-Goals (explicit)

- **Not a memory architecture upgrade for autopilot** — autopilot's evolutionary memory (episodic store, skill bank, strategy store) is unchanged.
- **Not a replacement for Hermes's MEMORY.md / Honcho** — those are for user/conversation modeling, distinct concern.
- **No write path** — the unified store never writes back to source files. Source files remain the single source of truth.
- **No auth/scopes** — single-user, local-only.
- **Not a real-time dashboard** — query API only. A dashboard could be built on top later if useful.

#### Evaluation capture versus RL eligibility — 2026-10-04

Operator-approved clarification from [P3 operational integration](../../research/intake-stage3-plan-2026-10-03-decision-tools.md#p3-operational-integration--exercise-both-real-tool-loops-and-improve-sft-input-selection) and [K6/K9](../../research/intake-stage3-plan-2026-10-03-decision-tools.md#why-the-general-critiques-are-beliefs-not-work-packets), plan `3911ec91`: UTM is a provenance/query service, not a training rollout engine. Harness/task/seed/turn pairing supports evaluation joins; generic trace validity does not establish exact original token IDs, behavior-logprob or authoritative-mask eligibility for off-policy RL. Evaluation, independently verified complete offline-SFT targets and off-policy RL remain separate consumer contracts. Original behavior logprobs are unnecessary for offline SFT and mandatory only for the distinct off-policy RL consumer.

[M3](../../research/intake-stage3-plan-2026-10-03-decision-tools.md#broader-follow-ons--distinct-from-the-immediate-integrations) requires a named model/workload/objective and eligible original rollouts before full multi-harness RL; implement exact-token export only for that actual consumer. TU-MH-1 and S2-CGE-1 retain their respective evaluation and SFT owners. UTM-P1a.3 remains the existing real-data pairing task, including its store, shared-ID, turn-alignment and inference-window conditions. This clarification adds no implementation checkbox or schema/export work.

#### Cross-References

- **Autopilot memory** (peer, distinct concern): [`autopilot-continuous-optimization.md`](autopilot-program.md) § Memory Architecture (episodic store + skill bank + strategy store).
- **Hermes conversation logs** (peer, distinct concern): [`hermes-outer-shell.md`](../completed/hermes-outer-shell.md) § Two-Layer Memory Architecture.
- **Existing audit infra**: `scripts/utils/agent_log.sh` (writer) + `scripts/utils/agent_log_analyze.sh` (current analysis CLI — narrower scope than the unified service).
- **Routing & optimization index**: `routing-and-optimization-index.md` § Cross-Cutting Concerns 5 ("Conversation Logs Feed All Three") — the unified service operationalizes that cross-cutting concern.

#### Key Files (proposed)

| Path | Purpose |
|---|---|
| `epyc-orchestrator/src/trace/store.py` | SQLite schema + upsert helpers (T1) |
| `epyc-orchestrator/src/trace/ingest_agent_audit.py` | T2 parser |
| `epyc-orchestrator/src/trace/ingest_autopilot.py` | T3 parser |
| `epyc-orchestrator/src/trace/ingest_progress.py` | T4 parser |
| `epyc-orchestrator/src/trace/query.py` | T5 query API |
| `epyc-orchestrator/scripts/trace/cli.py` | `python -m epyc.trace ...` CLI (T5) |
| `data/trace/events.sqlite` | Output store (gitignored — derived data) |

#### Deep-Dive Task Proposals — 2026-05-25 (intake-607 Code-as-Agent-Harness §3.2.1 / §3.2.3)

The Code-as-Agent-Harness memory taxonomy (§3.2) reframes two design choices for the trace/episodic stores. Audit pass converts the brainstorm into concrete schema/query additions.

- [x] **EXM-1 — Index FAILED trajectories as first-class avoidance cases.** §3.2.3 (experiential memory; ExpeL / Evo-Memory / MemGovern) argues failures should be stored and *retrieved for pattern-matched avoidance*, not just logged. We have a `failure_graph` (partial). Extend the unified trace store with a queryable "failure case" view: given a current (task, context) signature, return prior failed trajectories with similar signatures so a role can avoid repeating them. Minimum fields for a `failure_case` view/table: `failure_id`, `task_signature`, `suite`, `role_path`, `tool_sequence_hash`, `files_touched`, `error_class`, `root_cause_label`, `avoidance_advice`, `evidence_event_ids`, `resolved_by_event_id`, `governance_level`, and `validity_score`. Retrieval should combine lexical FTS, structured filters, and optional embedding similarity only after a cheap first pass. *(Highest-value here — cheap, reuses the store.)* **DONE 2026-06-27** in `epyc-orchestrator` `f470c519`: the schema already had the minimum `failure_case` fields; this slice added `failure_case_fts`, rebuild-on-schema-ensure for existing rows, insert-time indexing, exact-match-first lexical retrieval, and `_match_type`/`_matched_terms` annotations so callers can explain why a prior failure was surfaced. GitNexus impact was LOW for `find_failure_cases` and `insert_failure_case`; `GovernanceLevel` was LOW (`impactedCount=20`, import-level dependants). Validation: `python3 -m py_compile src/trace/harness_schema.py tests/unit/test_harness_schema.py`; `uv run ruff check src/trace/harness_schema.py tests/unit/test_harness_schema.py`; `uv run pytest -q tests/unit/test_harness_schema.py tests/unit/test_trace_store.py` -> `30 passed`.
- [x] **EXM-2 — Externalize working state (LLMs fail at latent-state persistence).** §3.2.1 cautions that raw LLMs lose working state across long horizons, so working memory should be *externalized* rather than held in-context. Audit where the orchestrator relies on the model to "remember" mid-task state vs. where it externalizes to the trace/scratchpad store; pull the former into the store where cheap. Add a `working_state` record family with `state_id`, `scope` (`request|trial|session|handoff`), `owner`, `key`, `value_json`, `created_from_event_id`, `expires_at`, and `supersedes_state_id`. Complements context-folding (which evicts) by keeping authoritative state outside the window. **DONE 2026-06-27** in `epyc-orchestrator` `25b3d4fc`: the scoped `working_state` table and supersession helpers already existed; this slice closed the missing lifecycle rule by marking expired live rows `superseded=1` before reads/writes so stale state is preserved for history but no longer returned as current. GitNexus impact was LOW for `set_working_state`, `get_working_state`, and `WorkingStateScope`. Validation: `python3 -m py_compile src/trace/harness_schema.py tests/unit/test_harness_schema.py`; `uv run ruff check src/trace/harness_schema.py tests/unit/test_harness_schema.py`; `uv run pytest -q tests/unit/test_harness_schema.py tests/unit/test_trace_store.py` -> `32 passed`.
- [x] **EXM-3 — Governed-experience tier (MemGovern).** Distinguish *governed* experiences (human-reviewed/approved outcomes) from raw trajectories when scoring retrieval relevance, so high-trust cases outrank noisy ones. Ties to the URE-2 approval-as-harness-state record in [`decision-aware-routing.md`](routing-program.md). Proposed levels: `raw`, `auto_verified`, `human_reviewed`, `approved_baseline`, `deprecated`. Retrieval should down-rank raw failures when a governed resolution exists, and should never present deprecated advice without a warning. **DONE 2026-06-27** in `epyc-orchestrator` `2af20d53`: `find_failure_cases()` now annotates retrieval rows with `_governance_rank` and `_governance_warning`; raw rows warn when a governed alternative exists for the same task signature, and deprecated rows warn when explicitly included. GitNexus impact was LOW for `find_failure_cases` and `GovernanceLevel` (`impactedCount=20`, import-level dependants). Validation: `python3 -m py_compile src/trace/harness_schema.py tests/unit/test_harness_schema.py`; `uv run ruff check src/trace/harness_schema.py tests/unit/test_harness_schema.py`; `uv run pytest -q tests/unit/test_harness_schema.py tests/unit/test_trace_store.py` -> `34 passed`.

**Audit refinements / missed gaps**:

1. **Failure retrieval can cause negative transfer.** EXM-1 must show why a prior failure is similar and what changed since then. Include content hashes/config snapshot IDs where possible; stale failures should be marked `suspected` rather than blindly retrieved.
2. **Avoidance advice needs provenance.** A failure case without evidence event IDs and a resolution link is just folklore. Keep it searchable, but do not elevate it to governed memory.
3. **Working state needs lifecycle rules.** EXM-2 should distinguish short-lived request state from durable handoff state. Add expiry/supersession so the store does not become an unbounded pile of stale scratchpad facts.
4. **Governance should affect ranking, not delete history.** Raw and deprecated records remain auditable; ranking and warnings handle trust. This preserves forensic value after regressions.
5. **Unify with HLE/BSV schemas.** Failure cases should link to harness metrics, oracle adequacy, behavior signatures, and URE approval records via event IDs so a future query can answer: "what failed, why was it accepted, who/what approved it, and what behavior changed?"

Roll-up: [`routing-and-optimization-index.md`](routing-and-optimization-index.md) P24 § Additional task additions. Source: intake-607 `deep_dive` in `research/intake_index.yaml`.

#### Shared Harness/Trace Schema — OWNED HERE (gap-fix 2026-05-25)

**This handoff owns the single shared event schema** that the 2026-05-25 intake-607 cluster (HLE / BSV / URE / EXM) all write to. Four handoffs independently assumed a common trace/journal event family; without a designated owner that becomes four divergent schemas and the promised cross-queries ("what failed, why was it accepted, what behavior changed?") break. The schema lives in `epyc-orchestrator/src/trace/store.py` + `src/trace/harness_schema.py` (extends the existing T1–T6 store) and MUST be implemented **before** the consuming tasks (HLE-1, HLE-4, BSV-1, URE-2) land their writes. *(Implemented + tested; MERGED to epyc-orchestrator main 2026-05-26, tip `15350fe`.)*

| Record family | Owning task | Written by | Read by |
|---|---|---|---|
| `harness_metrics` (execution_fidelity, feedback_interpretation, planning_stability, memory_coherence, recovery_rate + `evidence_event_ids`, `confidence`, `metric_schema_version`) | HLE-1 (meta-harness) | eval tower / trace ingest | HLE-4 (autopilot Pareto), HALO/P20 |
| `oracle_adequacy` (`oracle_type`, `coverage_claim`, `known_blind_spots`, `shortcut_risk`, `requires_external_answer`, `deterministic`, `reviewed_by`) | HLE-2 (meta-harness) | suite registration | HLE-1/HLE-4, autopilot gating |
| `behavior_signature` (per-sentinel outcome, answer hash, route/tool/escalation path hashes, latency/token buckets, harness-metrics ref, oracle-adequacy version) | BSV-1 (autopilot) | archive accept path | BSV-2/BSV-3 diff |
| approval/escalation record (`request_id`, uncertainty components, trigger reason, approval boundary, linked behavior_signature) | URE-2 (decision-aware-routing) | router/escalation | EXM-3 governance, audit |
| `failure_case` + `working_state` (fields enumerated in EXM-1/EXM-2 above) | EXM-1/EXM-2 (here) | trace ingest | role retrieval, all of the above |

**Contract rules**: (1) every record carries `metric_schema_version` and is keyed by stable `event_id`; (2) cross-references use `event_id` links, never duplicated payloads; (3) schema changes are additive + versioned (no silent field repurposing); (4) consumers must tolerate missing fields (`signature_confidence=partial` for backfilled rows). Implementation order is pinned in [`routing-and-optimization-index.md`](routing-and-optimization-index.md) P24 § "Implementation spine".

#### Research Intake Update — 2026-07-11

##### New Related Research
- **[intake-800] "From Passive Retrieval to Active Memory Navigation"** (arxiv:2607.05794, "NapMem"; **Alibaba Qwen team** + ShanghaiTech — deep-dive corrected the first-pass "Microsoft Research" attribution)
  - Relevance: reframes long-term memory from system-level passive retrieval to an **agent-navigated structured action space** — directly informs how this service exposes trace/memory to consuming agents rather than only storing it.
  - Key techniques worth mining (adopt_patterns, not a drop-in): (1) **four-tier provenance pyramid** (L1 raw conversations → L2 typed memory records `fact/event/instruction/preference` → L3 topic tracks → L4 user profile) mirroring our tiered event families; (2) memory exposed as **5 tools** (`search_records/search_conversation/get_records/get_conversation/read_file`) — a plain store API, no model-specific machinery; (3) **RRF hybrid vector+keyword retrieval** at k=60 (weaker than [[colbert-reranker-web-research]], which already exceeds it — contrast not adoption); (4) an RL (GRPO) **tool-call-frugality reward** (3.97→2.15 calls/query; unnecessary GPQA-D calls 34.51%→6.90%).
  - **Deep-dive (2026-07-11) load-bearing finding:** the Table-4 ablation, read on the conversational-memory subset that matches our use case (LoCoMo+LongMemEval), shows the **borrowable store+navigation half contributes MORE than the RL policy** (+11.94 vs +7.92 L-J); prompt-only navigation over the same store reaches **~89% of full-system quality**. So we do **NOT** need their (unreleased) trained 9B — **adopt_patterns confirmed, not adopt_component**. RL's durable unique value is call-frugality, a later optional efficiency lever.
  - Reported (self-graded L-J, no code release): LongMemEval F1 57.41 / L-J 80.33; 4.83 GiB storage vs Mem0's 10.44. Credibility 3. Note metric non-comparability: not comparable to MemPalace 96.6% R@5 (intake-326) — NapMem is orthogonal (navigation interface), not better/worse.
- **[declined: ws58 2026-11-03 content-review: merged into UTM-B1 — duplicate; UTM-B1 registers exactly this already-built navigation.py surface (RRF k=60); the gap is registration]** Operator-review candidate: prototype a **read-only 5-tool navigation surface over the already-landed `src/trace/` FTS5 store — NO RL** (search/get by `event_id` + `read_file` on a progress summary), plus an **RRF(k=60) hybrid** fusing FTS5 lexical + a vector index (existing BGE embedders :8090-8095). ~89%-of-value path; days of inference-free work. Cadence to copy: records flush at 1/2/4/5-turn boundaries; tracks >20 new records; profile >50.
  - [x] Read-only navigation primitive landed in `epyc-orchestrator` commit `d364835a`: `src/trace/navigation.py` exposes `search_records`, `search_conversation`, `get_records`, `get_conversation`, allowlisted/size-bounded `read_file`, and pure RRF(k=60) fusion over caller-supplied vector candidates. No ingestion/schema/runtime mutation and no embedding-server calls. ✅ 2026-07-11
  - [x] CLI access for the five read tools landed in `epyc-orchestrator` commit `e1e6d271`: `trace search-records`, `trace search-conversation`, `trace get-records`, `trace get-conversation`, and `trace read-file`, covered by `tests/unit/test_trace_cli.py`. ✅ 2026-07-11
  - Note 2026-09-16 (sub-trace-bm25), **integrated** (orchestrator merge `21172688`, pushed in `d748b4c7`): `query(text=...)` / `search_records` claimed bm25 ranking but ordered by `ts_utc DESC`, so a limited search kept the newest matches and RRF fused a recency rank. Fixed on orchestrator branch `sub/trace-bm25-20260916` at `6302b381`: text queries now default to bm25 ranking applied before LIMIT; an explicit `order="recency"` option (CLI `--order`) is available; filter-only callers are unchanged and now pass recency explicitly. No recorded result used the old ordering: CME-4's retriever (research `ccc41d4b`) fetches every match and re-ranks by bm25 itself, and UTM-B2/B4 have not been run.
  - **Extend with [intake-809] AutoMem's WRITE half (deep-dive 2026-07-11):** the NapMem surface above is the read/PLAN half; AutoMem's net-new, inference-free contribution is the **LOG/write ops as first-class agent actions** — `APPEND`/`CREATE` + **coordinate/key-keyed `UPSERT` dedup** + auto-synced `status`/`inventory`/`strategy` files (cut per-step memory growth −95% in their NetHack run). Note: `src/trace/` is **read-only by design** (No-write-path non-goal), so this write surface targets an **agent-facing memory tool over autopilot's episodic/strategy store**, not the trace store. Scaffold carries 85–95% of AutoMem's value; its LoRA memory-specialist is deferred (see [[meta-harness-optimization|completed ledger]] P3).
  - [x] AutoMem write-schema primitive landed in `epyc-orchestrator` commit `bf315b11`: `orchestration/repl_memory/memory_actions.py` adds default-inert `APPEND`/`CREATE`/`UPSERT` actions with coordinate/key dedup and generated `status`/`inventory`/`strategy`/`plan`/`log` projections under the agent-facing memory path. `src/trace/` remains read-only. ✅ 2026-07-11

#### Research Intake Update — 2026-07-16

##### New Related Research — GCP "always-on memory agent" (adopt_patterns, one transferable idea)
- **[intake-825] "Always-On Memory Agent"** (GoogleCloudPlatform/generative-ai demo; Google ADK + Gemini + plain SQLite)
  - Correction to the first-pass assumption: the sample uses **plain SQLite with NO vector DB and NO embeddings** (a deliberate non-RAG stance) + Google ADK — NOT Vertex AI Agent Engine / Memory Bank. That makes the *pattern* portable but the *stack* irrelevant to us.
  - Transferable pattern (adopt_patterns, not a component): a **timer-triggered background consolidation loop** (default 30-min) that scans *unconsolidated* memories, generates cross-cutting insights, and compresses — gated by an **ingest-time 0–1 importance score** — over a two-state (unconsolidated→consolidated) store. Analogous to sleep-time-compute / autopilot-nightshift overnight passes; conceptually already covered by intake-155 (AgentFold) and intake-413/418 (hierarchical memory distillation), so novelty is low.
  - Fit vs the landed `src/trace/` surface: this service is **read-only by design**; a consolidation/insight pass is a *write/derive* step, so it targets the **agent-facing memory store** (the AutoMem write half above / B1 User Modeling per [[delta-mem-reproduction]]), not the trace store. Zero empirical results (demo-grade) — pattern-adoption only.
- **[declined: ws58 2026-11-03 content-review: curiosity — "consider" an AutoMem extension with no measured need and no decision; memory has not yet shown a benefit (M-12k)]** Operator-review candidate: consider an **importance-scored background consolidation pass** (periodic insight-generation + compaction over the agent-facing episodic/strategy store) as an optional extension of the AutoMem write surface — inference-free, mirrors the GCP loop, and is distinct from the read-only trace store.

#### Research Intake Update — 2026-07-29 (agent-memory dives: ReasoningBank / CORE / SkillOS / EvoMemBench)

_Via `/research-intake` Stage-4 (intake-930 ReasoningBank, intake-888 CORE, intake-935 SkillOS, intake-936 EvoMemBench; intake-899 is the internal falsification precedent). All external figures are OBSERVATION-grade under MEASUREMENT.md. These items target the **agent-facing** experience/memory layer and the trace store's retrieval surface — `src/trace/` itself stays read-only._

##### Store shape and layering

- [x] **UTM-M1 — Adopt the ReasoningBank STORE SHAPE: append-only, raw trajectory retained alongside derived `{title, description, content}` items.** ✅ 2026-07-29 — `epyc-orchestrator`'s default-inert `MemoryActionStore` now has an additive `pattern` channel. Each non-tombstone pattern requires an immutable bounded `source_event_ids` list, `title`, `description`, `content`, applicability boundary (`when_not_to_use`), `embedding_version`, and explicit `retention_state`; it is persisted to the append-only JSONL ledger and rendered as a separate projection. Existing raw trajectories remain authoritative in their current stores; no trace migration, embedding backfill, runtime wiring, or live BGE request occurred. The legacy high-blast-radius `SkillBank` contract was deliberately left untouched.
- [x] **UTM-M2 — Scope the dual-layer experience bank as an ADDITIVE upper layer on `src/trace/`. ✅ 2026-07-29** The per-case lower layer remains `src/trace`'s read-only `events.sqlite` + FTS5 store. The upper layer is a separate agent-memory ledger: immutable raw-event references plus derived pattern records, each with source-event ids, an applicability boundary, embedding version, and retention state. Retrieval must fuse FTS5 and vector candidates only at an explicit agent-facing consumer; it must not mutate or become a dependency of trace ingestion/query. Start with bounded per-pattern provenance and a declared capacity/eviction policy before any embedding backfill; no live BGE request, trace-store migration, or runtime wiring is authorized by this scope.
- [x] **UTM-M3 — Adopt SkillOS's three-verb write API (`insert` / `update` / `delete`) plus its "When NOT to Use" section** in every stored skill/pattern record. ✅ 2026-07-29 — default-inert `MemoryActionStore` now accepts append-only `DELETE` tombstones: a matched delete removes the current generated projection but retains the prior row, tombstone rationale, actor, and `previous_event_id` in `memory_actions.jsonl`; a missing delete is a non-mutating `missing` result. Strategy records require and render a `When Not To Use` applicability boundary. Focused suite: `tests/unit/test_memory_actions.py` 11 passed.
- [x] **UTM-M4 — Mine the Apache-2.0 ReasoningBank repo for the three prompts** (extraction-on-success, extraction-on-failure, binary judge; plus the MaTTS contrast prompt) **and the JSON store schema.** ✅ 2026-07-29 — source audit of `google-research/reasoning-bank`: `SUCCESSFUL_SI` / `FAILED_SI` each cap non-overlapping generalizable items at 3 with `{Title, Description, Content}` Markdown fields; `build_text_eval_prompt` is the binary judge (`Status: success|failure`) with completeness, grounding, and exact-target checks; `PARALLEL_SI` is the MaTTS contrast prompt (success/failure comparison, ≤5 transferable items). `induce_memory.py` persists JSONL rows with `task_id`, `query`, `think_list`, `action_list`, `status`, `memory_items`, and `template_id`. Import prompts + schema only — **not** the BrowserGym/Vertex-coupled harness.

##### The measurement that does not exist yet — EPYC-original, blocked on no one

- [x] **UTM-M5 — Build the PER-WINDOW (non-cumulative) success-rate-vs-store-size instrument.** ✅ 2026-07-29 — `epyc-orchestrator` `05e0b8bf` adds read-only `scripts/analysis/memory_store_growth_curve.py`: chronological, non-cumulative success rate per window, cumulative store size, and unknown outcomes reported separately from a SQLite `mode=ro` connection. Focused suite `tests/unit/test_memory_store_growth_curve.py` 2 passed; Ruff and `git diff --check` clean. Output is observation-grade until a named protocol and attestation exist; it gates no adoption decision by itself. **No paper in the set reports this curve** — not ReasoningBank (intake-930), not CORE (intake-888), not SkillOS (intake-935), not EvoMemBench (intake-936); SkillOS's own Future Work concedes the gap. ReasoningBank's Figure 1 is **cumulative** and therefore structurally incapable of showing intake-899-style late decay: a per-window curve can fall while the cumulative curve still rises.

##### Context-budget competition at long context (intake-936) — NOT the same failure as intake-899

- [x] **UTM-M6 — File the EvoMemBench 128K finding as a distinct failure mode.** Independent third party, **DeepSeek-V3.2 backbone**: at a **128K** context budget, **six of fifteen memory methods score BELOW the no-memory baseline** (worst: MemoryOS **−7.0pp**). Counts by budget are **3 / 4 / 3 at 16K / 32K / 64K and DOUBLE at 128K**. **CRUCIAL: the mechanism is context-budget COMPETITION — injected memory displacing live history — NOT store growth.** It must **not** be conflated with intake-899 (late decay from store growth). Two different diseases; conflating them will produce the wrong fix. ✅ 2026-07-29 — source-backed in `intake-936` (`dive-overturned`): its fixed-update-schedule context-budget sweep isolates prompt-space competition, while intake-899 concerns accumulated-store decay.
- [x] **UTM-M7 — Make trace/memory retrieval BUDGET-CONDITIONAL (design consequence (a)).** ✅ **Re-implemented and integrated 2026-09-16** (`sub-utm-m78`, orchestrator `74418b3c`, merge `d748b4c7` on `main`; `tests/unit/test_trace*.py` 44 passed). The original 2026-07-29 tick was false: `select_budgeted_records()` had never been committed to any epyc-orchestrator ref. — `src/trace/navigation.py` now provides default-off `select_budgeted_records()`: it returns no retrieval rows when `history_is_truncated` is false (the untruncated history fits), and otherwise requires the caller to declare both history/window tokens and the pressure threshold. It does not search, infer token counts, call embeddings, or inject prompts; caller wiring remains a separately reviewed change.
- [x] **UTM-M8 — Cap injection as a FRACTION OF REMAINING BUDGET, not a fixed k (design consequence (b)).** ✅ **Re-implemented and integrated 2026-09-16** (same change as UTM-M7: orchestrator `74418b3c`, merge `d748b4c7`). The 2026-07-29 tick was false (code never committed). — the same pure selector admits only rows carrying an explicit positive `estimated_tokens` value and caps their total at `remaining_budget_fraction × (window_tokens - history_tokens)`. This makes unknown token cost fail closed and prevents a fixed count from overrunning a nearly-full context. No runtime retrieval/injection behavior changed.
- [ ] **UTM-M9 — Add a NO-MEMORY control arm to the eval tower for every memory A/B.** Six published methods lose to no-memory at 128K and **would have shipped undetected without one**. Eval-tower rows are a human-amendment-only trust boundary (MEASUREMENT.md) — this is an operator-gated ask, filed here as the owning rationale.

##### Correction — ReasoningBank's standing (do not carry "best overall" forward)

- [x] **UTM-M10 — Correct the ReasoningBank standing in every place this repo restates it ✅ 2026-07-29.** Root `683f70de` had introduced the stale wording in intake-930; this correction fixes it: intake-936 places ReasoningBank **LAST of 13** memory methods on **Cross-Episode Knowledge (Easy split)**; the earlier "second behind ACE" reading was **wrong**. It **is** best-among-memory-methods on **In-Episode Execution at 16K / 32K / 128K** — but even there a **long-context baseline beats all fifteen** methods. SkillOS-base also wins the WebShop-like domain, so no family-wide gradient-free ranking remains. Keep the store-shape adoption (UTM-M1), drop the "best overall" framing wherever it appeared.

#### 2026-08-07 — verifiable memory operations, default-inert shadow path (intake-1008#record, intake-1015#record, intake-1017#record, intake-1018#record, intake-1022#record, intake-1023#record)

- [ ] **UTM-V1 — Complete the append-only memory-operation envelope and state-transition engine.** Add
  typed `ADD|UPDATE|DELETE|RETRIEVE|FILTER|SELECT_EPISODE|SUMMARIZE|NOOP` proposals over the existing
  raw-event authority. Every operation carries operation/session/actor ids, immutable source-event
  references, before/after value hashes, version and supersession links, applicability boundary,
  proposer/verifier versions, `proposed|validated|committed|rejected|rolled_back` state, and error or
  rollback provenance. `UPDATE` creates a new version; soft `DELETE` creates a tombstone and preserves
  history; physical privacy erasure is a separate explicit state and must not be claimed from a
  tombstone. Implement restore/rollback and stale-fencing fixtures. Existing raw traces are never
  overwritten or made unrecoverable. Sequencing: start UTM-V1..V6 only after M-12k/M-12 show memory-on >= memory-off on the frontdoor; a verified-operation envelope over a store that has not yet shown a benefit has no substrate to protect.
  - **2026-11-09 (apr2 third-pass) PARTIAL, box stays OPEN, unwired:** epyc-orchestrator branch `apr2/third-pass-20261109` `446c1e0b`: `orchestration/repl_memory/memory_operations.py` (+29 tests, `tests/unit/test_memory_operations.py`, `--noconftest`). Typed `MemoryOperation` envelope (all eight op types; operation/session/actor/subject ids, source-event ids, before/after hashes, version, supersession, applicability, proposer/verifier versions, `proposed|validated|committed|rejected|rolled_back`, error/rollback provenance) and a `MemoryEngine` with a legal-transition table, an append-only transition log (optional JSONL mirror), versioned items (UPDATE appends; soft DELETE appends a tombstone; history never lost), stale fencing re-checked at commit, rollback (head only; versions kept, numbers never reused) and a separate `erasure_requested`/`erased` state that needs an explicit receipt (a tombstone never claims erasure). It does NOT write `MemoryActionStore` or any live store; source existence is a caller-supplied resolver. Built although the sequencing note says V1..V6 start after M-12k/M-12: the program's own "Doable now" line names V1/V2, and nothing consumes it, so it asserts no store benefit. **Not done:** mapping committed ops onto `MemoryActionStore`, real-trace replay. [no-belief: source and fixtures only] [2026-11-09 wrap-up verification: `446c1e0b` is an ancestor of epyc-orchestrator origin/main; box state unchanged — landing is code only, acceptance still as the box states]

- [ ] **UTM-V2 — Add a local scoped write proposer, not an authoritative writer.** Combine Mem0's
  user/agent/run scoping, recent-message context, top-k conflict retrieval, and four-way mutation
  proposal with VerMem's stronger envelope. Record actor versus subject so one model's inference
  cannot silently become another actor's fact. Run in shadow on recorded traces first; compare
  proposed operations with current append-only behavior and human-labelled cases. Do not copy the
  current Mem0 branch's ADD-only default as the target and do not allow lossy facts to replace raw
  evidence.
  - **2026-11-09 (apr2 third-pass) PARTIAL, box stays OPEN, shadow-only:** same module. `ScopedWriteProposer` (user/agent/run applicability, top-k conflict retrieval kept inside the declared scope AND subject, deterministic 4-way default: exact duplicate NOOP, overlap >= 0.6 UPDATE, else ADD; DELETE only via an injected `decide_fn`; an undecidable proposal becomes NOOP) returns `proposed` operations with actor and subject recorded and never commits; `agreement_report` compares against human labels and counts unlabelled proposals as unlabelled, not agreement. **Not done:** the shadow run on recorded traces and the human-labelled comparison (no labelled cases exist), and any model-backed proposer.

- [ ] **UTM-V3 — Separate structural and semantic verification and calibrate both.** Structural checks
  deterministically enforce schema, scope, provenance, version, tombstone, rollback, source existence,
  and transition legality. A separately versioned semantic judge scores local operation correctness
  and global memory coherence. Build human-labelled conflicting, stale, poisoned, private, strategically
  manipulated, duplicate, missing-source, and delete/restore cases; report false-pass/false-fail by
  class. The released VerMem rule verifier is only the structural baseline and cannot inherit the
  paper's DeepSeek semantic-verifier result.
  - 2026-10-21 UTM-V7 criteria added here: the profile-write audit checklist ([docs/reference/profile-write-audit-checklist.md](../../docs/reference/profile-write-audit-checklist.md)) applies to ProfileStore and `user_conclude` writes (one fact per entry, about the target user, no conversational mechanics, no paraphrase duplicates, references and dates resolved).
  - **2026-11-09 (apr2 third-pass) PARTIAL, box stays OPEN, structural half only:** `memory_operations.structural_check` (epyc-orchestrator `446c1e0b`) is the deterministic host verifier: schema (types, enums, hash agreement, per-op required fields), scope (applicability scope vs user/agent/run ids), provenance (mutations need sources; dangling source ids REJECT, via the caller's resolver), version (must be max+1), tombstone, stale `before_hash`, head supersession, rollback-only-of-head and transition legality; one fixture per reason class. `calibration_report` tabulates per-class false-pass/false-fail from labels an author supplies and omits classes with no cases. **Not done (needs a window and humans):** the separately versioned semantic judge, the human-labelled conflicting/stale/poisoned/private/manipulated/duplicate/missing-source/delete-restore cases (none exist; the synthetic UTM-V3-SYNTHETIC fixtures are not gold), and the VerMem structural baseline comparison. Poisoned/private/manipulated are semantic and are NOT assessed by the structural check. [no-belief: source and fixtures only]

- [ ] **UTM-V4 — Test answer-time evidence distillation independently of memory writing.** Preserve
  Memory-R1's manager/distiller separation: retrieve a bounded candidate set, then have the answer
  path select evidence with source ids before answering. Sweep the retrieval/distillation budget
  rather than assuming sixty entries is optimal. Score answer quality, evidence precision/recall,
  unsupported claims, tokens, latency, and raw-source recoverability against no-distiller retrieval.

- **[declined: ws58 2026-11-03 content-review: no consumer — per-operation credit for an RL policy we do not train (Memory-R1 releases no training code); the structural/semantic fields it would emit already belong to UTM-V3]** **UTM-V5 — Emit per-operation credit in shadow, without RL training.** Record deterministic
  structural result, calibrated local/global semantic result, downstream task outcome, evidence
  recall, operation cost, and rollback/recovery outcome as separate fields. Compare task-only credit
  with operation-level credit. No learned policy may consume this signal until deterministic and
  supervised baselines, conversation-isolated splits, verifier calibration, and reproducible data
  show a measured advantage; the official Memory-R1 repository currently releases no training code.

- [ ] **UTM-V6 — Run a complete memory evaluation matrix with a mandatory no-memory control.** Include
  no-memory/raw full context, current append-log retrieval, current Context-Folding, Mem0-style shadow
  proposals, VerMem operations, answer distillation, and the CF-AM-1 parallel-gist arm. Measure within-
  task, crash/restart, cross-session, conflict/staleness, poisoning, actor scope, tombstone, physical
  erasure, rollback, and raw-evidence recovery. Account for extraction, write, embedding, retrieval,
  answer, verifier, training (if later permitted), tokens, latency, wall time, and storage separately.
  Use conversation-level splits and repeated end-to-end seeds; judge repeats alone are not uncertainty.

#### 2026-09-07 — memory-service surface + the BEAM/Tulving retrieval arm (research-intake)

- [ ] **UTM-B1 — Register the already-built read surface as a model-facing `ms.search` / `ms.expand`
      tool** (`intake-1316#record`). `src/trace/navigation.py` already IS an ms-shaped read surface
      (`search_records`, `search_conversation`, `get_records`, `get_conversation`, allowlisted
      `read_file`, pure RRF k=60) with no ingest, no schema mutation and no embedding call. **The
      gap is registration, not construction.** Correction to the bearing dive text: it is not
      "zero consumers" — re-grepped 2026-09-07, it has exactly **one non-test consumer,
      `src/trace/cli.py:22`**, and **no MCP registration and no orchestrator wiring**. That is the
      gap. Absorbs the 2026-07-16 "read-only 5-tool navigation surface + RRF hybrid" candidate: registration as an MCP/orchestrator tool is the whole gap; no new construction.
      **2026-11-09 audit:** the MCP registration now EXISTS (`ms.search` / `ms.expand` in `src/trace/mcp_tools.py:21,27`, orchestrator commit `715b49ae` 2026-10-07, ancestor of main; wired in `src/mcp_server.py`; test `test_trace_mcp_tools.py`); the "no MCP registration" text above is stale. Left unticked: **Decision needed (owner/operator):** does "model-facing" require a REPL/orchestrator tool too, or is the MCP server enough? Options: (a) MCP only, tick now; (b) also register in the REPL tool surface. Recommendation: (a), since the box's own text names "MCP/orchestrator tool" and the REPL already has `recall()`; open (b) as a separate box only if M-20 shows REPL tools are used.
- **[declined: ws58 2026-11-03 content-review: merged into M-12b — duplicate; M-12b's trace arm (BEAM_CONTEXT_MODE=trace, merged cfbfa448) is this run]** **UTM-B2 — Expose the FTS5 store + `navigation.py` (RRF k=60) as the memory backend for a
      BEAM 128K run** (`intake-1330#record`) — the cheapest first-party test of the append-only-log
      thesis. BEAM's driver reuses one retriever/prefix across all 20 questions of a conversation
      with no cross-question accumulation, so the arm is embarrassingly parallel and
      order-independent. COMPUTE-GATED: filed, not run.
- **[declined: ws58 2026-11-03 content-review: merged into M-12b as a recorded run parameter]** **UTM-B3 — Record the ingest FILTER in the run artifact as a first-class experimental
      parameter, not plumbing** (`intake-1337#record`). Record exactly which turns were indexed and at
      what granularity: a silent role filter or chunking choice moves the score more than the
      retrieval algorithm does. COMPUTE-GATED rider on UTM-B2.
- [x] **UTM-B4 — Route the Tulving `retrieved` arm through this surface** — the backend half of
      CME-4 in [conversational-memory-eval-instrument.md](conversational-memory-eval-instrument.md)
      (`intake-408#record`). Zero compute to write. ✅ 2026-10-07 — MAIN accepted [existing source and original23/23](../../artifacts/ni08/utm-b4-tulving-source-20261007/README.md).

**Note on UTM-M9** (mandatory no-memory control arm for every memory A/B, above): it is already
flagged in-file as an operator-gated MEASUREMENT.md trust-boundary ask. M-12a/M-12b satisfy its
intent; **do not tick UTM-M9** — the eval-tower registration is the operator's.

#### MAIN-reviewed JEV refinement — 2026-10-06 (UTM-V3)

Prepare the semantic-verifier case manifest and mocked parser/readout fixtures using the existing `judge_redundancy.py` fixture/receipt pattern: frozen case and rubric hashes, explicit criterion outcomes, unresolved parse/transport failures and denominators, and reader agreement reported separately from accuracy against gold. Reuse `Question`/`DecisionResult` only for genuinely closed rubric choices; memory payloads and explanations remain source data. Structural schema/scope/provenance/transition checks remain deterministic host checks.

UTM must author and adjudicate its own human-labelled conflicting, stale, poisoned, private, manipulated, duplicate, missing-source and delete/restore cases. CJ's synthetic rubric truth does not transfer to memory semantics. Mocked conformance proves representation and failure handling only; the separately versioned live semantic judge still needs UTM-V3's per-class false-pass/false-fail calibration. Add no belief grading ladder and grant no write authority. UTM-M9's human-amendment-only eval-tower gate remains unchanged.


- [x] **UTM-V3-SYNTHETIC — characterize native structural/parser/readout contracts without semantic gold.** ✅ 2026-10-06 — [Contract and source acceptance](../../docs/reference/utm-synthetic-conformance-contract.md), original CI37444684189 TRUE2/2;8store categories/5parser batches/6attempts. Generated readout is captured at execution. Source/privacy/scope/freshness/poisoning/manipulation remain unassessed, dangling source IDs characterized rather than declared safe. Human semantic calibration, live judge and UTM-M9 remain open.

#### Read-only registration source companion — 2026-10-07

- [x] **UTM-B1-SOURCE — prepare the existing read-only trace navigation registrar and synthetic MCP/SQLite controls.** Exact `ms.search`/`ms.expand` tool names, declared session_id, fixed default read store and no model-selected paths, writes or embeddings. Keep the default orchestrator MCP catalog unchanged until catalog-growth acceptance; source registrar is explicit and uninvoked. Actual off-host FastMCP schema/defaults and synthetic SQLite navigation controls through VB-UTM-B1-CONFORMANCE. Parent model-facing registration and real consumers remain open. ✅ 2026-10-07 — MAIN accepted [published source and original5/5](../../artifacts/ni08/utm-b1-read-only-mcp-source-20261007/README.md).

2026-10-07 MAIN source finding: UTM-B4 is already implemented by the checked CME-4 backend in current Research `de02a21d88e006dd542b7a1a56bf8090a27de1f3`: chapter Events in a private SQLite store, existing `navigation.search_records` candidate retrieval and FTS BM25 selection, default retrieved-arm construction and missing-source refusal. VB-UTM-B4-CONFORMANCE now owns a prospective full synthetic native capture, including the four trace-dependent cases with an exact APP source path; no skipped control will count. UTM-B4 source routing is now checked after MAIN accepted original23/23; real-data/model quality remains unassessed. UTM-B3's prospective filter/count source remains executable independently of the future real BEAM run; its historical COMPUTE-GATED rider does not gate source authoring.

- [x] **UTM-B3-SOURCE — add prospective BEAM memory ingest provenance to question/run artifacts.** Preserve all flattened role/content messages in source order, record zero-based half-open indexed range, normalized role/message/chunk counts and exact pair-chunk granularity for retrieved arms. Label the full-history arm without claiming a retriever lookup; no historical backfill or real BEAM outcome. MAIN-reviewed isolated Research source180a772445e2c227979998cdec9b7a50ae5aa54e; actual synthetic module validation through VB-UTM-B3-CONFORMANCE precedes publication. Parent real experimental run remains open. ✅ 2026-10-07 — MAIN accepted [source and original21/21](../../artifacts/ni08/utm-b3-beam-provenance-source-20261007/README.md).

#### 2026-10-20 — lesson-revision A/B spec (intake-1999#record)

- [x] **UTM-R1 — Lesson-revision A/B spec (design only; no run).** Arm B revises retrieved lessons after a labelled outcome using only the lesson's source trajectory plus the outcome as feedback, as append-only supersession built on the existing `superseded` retention state and `previous_event_id` (`orchestration/repl_memory/memory_actions.py:30,268 @5d4ad2c0`); arm A is forward-only reflection; both keep a raw-trace baseline and a no-memory control (UTM-V6 matrix, UTM-M9 stays operator-gated and unticked). Instruments: M-12, BEAM M-12b and UTM-B4 under P-AB-1, with N >= 100 per arm and run-local CI and MDE declarations. Report a grounded/leaked/unsupported audit of revised claims on a sample; a counterfactual same-instance replay is allowed only as a labelled diagnostic upper bound, never an arm (`intake-1999#record`). Fixtures required at filing: two consecutive opposite-sign single-instance outcomes must not oscillate the stored lesson (recency flip), and a revision that ignores an unused notepad entry is reported (`intake-2149#03`). Record the decision whether revision runs as a background or idle-time job (not serve-time) at result time, with no compute claim now. ✅ 2026-10-20
  UTM-R1 readout addendum (UTM-R2, 2026-10-21), two report lines: (a) revised-lesson reuse rate = retrieved-and-used after revision / retrieved-after-revision, defined on the existing `superseded` and `previous_event_id` fields, an adoption proxy and not a quality measure (intake-117#record); (b) the write-side cost line (LLM calls plus input and output tokens over every memory-construction call, judge excluded) beside the read-side injected-token line (intake-2311#record).
- [x] **UTM-R2 — UTM-R1 reporting addendum: revised-lesson reuse rate and write-side cost.** Add to the UTM-R1 readout: revised-lesson reuse rate equals retrieved-and-used after revision over retrieved-after-revision, defined on the existing superseded and previous_event_id fields, as an adoption proxy and not a quality measure (intake-117#record); and the write-side cost line (LLM calls plus input and output tokens over every memory-construction call, judge excluded) beside the read-side injected-token line (intake-2311#record). Acceptance: both lines are in the UTM-R1 readout text. Estimate: 0.2 day. ✅ 2026-10-21
- [ ] **UTM-V7 — Profile-write precision audit checklist from the Honcho deriver rubric.** Define the ProfileStore and `user_conclude` write-audit checklist from the Honcho deriver prompt (`src/deriver/prompts.py:67-86 @607438d`): one fact per entry; the fact is about the target user; no conversational mechanics; no paraphrase duplicates; references and dates resolved. Apply by deterministic checks where possible and a human-labelled sample otherwise; add it to the UTM-V3 criteria. Reference intake-2237#record. Acceptance: the checklist is filed, the deterministic checks have unit tests, and one audit run over the current profile store is reported. Estimate: 1 day.
  - 2026-10-21 `dpf-skill` NOT ticked. Checklist filed: [profile-write-audit-checklist](../../docs/reference/profile-write-audit-checklist.md); deterministic checks + unit tests in orchestrator `09396bbe` (`src/user_modeling/write_audit.py`, `tests/unit/test_profile_admission.py`). The one audit run is VACUOUS, not a pass: `features().user_modeling` is off and no `user_profiles.db` exists ([result](../../artifacts/dpf-skill-20261021/utm_v7_audit.json) = `store_not_found`). Run `python -m src.user_modeling.write_audit` once a profile store exists, then tick.

## Track: dev-harness-trace-mining
<!-- gate: EVL-10#memory-program, EVL-10#repl-session-memory-maturity, EVL-10#unified-trace-memory-service -->

> Folded from `handoffs/active/dev-harness-trace-mining.md` @ `ec0a9febab21` on 2026-11-03 (BRF-T7-F14, route 1b, operator D1/D5; retired row EVL-52 → EVL-10). Body moved verbatim, headings demoted two levels to nest under this track; every open and closed box kept its text and ID.

### Dev-Harness Trace Mining

**Status**: stub
**Created**: 2026-10-22 (via research intake, operator-approved plan of 2026-10-22)
**Categories**: agent_architecture, benchmark_methodology, knowledge_management

#### Objective

Mine EPYC's own development-harness transcripts (Claude Code, Codex, opencode) for operator-signal series,
guard behaviour and lesson efficacy, so that lessons, hooks and harness rules are kept or promoted on
measured recurrence rather than on anecdote. Measurement only; hook and policy edits stay human-applied.

#### Research Context

| Intake ID | Title | Relevance | Verdict | Verification |
|-----------|-------|-----------|---------|--------------|
| intake-2387 | Beacon cross-harness trace capture and distillation | high | adopt_patterns | dive-verified |
| intake-2395 | Measure Before You Manage (working memory) | medium | worth_investigating | dive-verified |
| intake-2396 | Agent memory distillation (disjoint-split protocol) | medium | worth_investigating | dive-verified |
| intake-2397 | SWE-chat (real coding-agent sessions) | medium | worth_investigating | dive-verified |
| intake-2426 | Invisible failures in human-AI interaction | medium | worth_investigating | dive-verified |
| intake-2428 | Transluce coding-agent misalignment in the wild | medium | worth_investigating | dive-verified |
| intake-2429 | Anthropic: measuring agent autonomy in practice | medium | worth_investigating | dive-verified |

#### Tasks

- [x] **DHM-1 — Mechanical operator-signal series: count both interrupt markers (plain and for-tool-use) and the Codex/opencode abort analogues per 1000 turns with Wilson CIs, split main vs subagent and by harness; keyword pass for operator corrections in ~/.claude/history.jsonl since 2026-03 (intake-2397, intake-2429).** ✅ 2026-10-22
  - *(2026-10-22, workspace-f8 / mining-m1.)* **Code done; full run scheduled tonight (dhm-mining-full)** (main thread, outside the quiet window): `scripts/dev_harness/mine_m1.py` (tests `tests/dev_harness/test_mine_m1.py`), aggregate `dhm1.aggregate.json` (dev-harness-aggregate.v1) under `<private-root>/mining/<run>/m1/aggregates/`. Turn = deduplicated assistant model call; split harness x source x main/subagent plus a monthly series; Codex child threads replay parent history with FRESH timestamps at birth (measured: one parent's aborts copied into 32 forks), so events within 5 s of a child's birth are excluded from numerator and denominator (raw kept); a marker copied into a Claude child with the same ts counts once. Sample (`sample-20261022`, 66 units, tiny N): claude main 2.3/1000 turns (1/429, CI 0.4-13.1), subagent 0/2752; opencode 19/1000 (2/105); codex 0/541. Correction keyword pass is implemented (`--tasks history --history <file>`) but NOT run: its only input, `~/.claude/history.jsonl`, is a live store this lane may not open; the main thread decides whether to pass it.
    Full run: `nice -n 19 /usr/bin/python3 scripts/dev_harness/mine_m1.py --projection /mnt/raid0/llm/private/dev-harness-traces/projections/full-20261022T1310Z` (est. 5-10 min, peak RSS ~1.5 GB; covers DHM-1, DHM-5, OAB-LB1, UFH14-LB8).
  - *(2026-10-22, workspace-f8 / mining results.)* **Full run `full-20261022T1310Z` (42,420 units); acceptance met.** Interrupts per 1000 turns, any marker (Wilson 95% CI): Claude main 6.30 (5.70-6.97, 380/60,294), Claude subagent 0.088 (0.052-0.148, 14/158,974); Codex main 6.83 (5.70-8.18, 116/16,987), Codex subagent 2.21 (1.91-2.56, 178/80,572); opencode main 0.71 (0.55-0.93, 56/78,445), opencode subagent 2.36 (1.61-3.46, 26/11,018). Claude markers: 329 plain, 65 for-tool-use. Per 1000 human turns, Claude main: 41.9 (38.0-46.2). Monthly series and the history keyword pass are in the aggregate. Full tables: `docs/design/dev-harness-mining-results-20261022.md`; committed aggregate `data/dev_harness/mining-full-20261022T1310Z.aggregate.json`.
- [x] **DHM-2 — Retrospective guard audit over sampled sessions per harness: predicates for pattern kills, edits of a running script, writes outside the allowlist, wholesale git add, piped gate push, glob rm -rf, git clean, llama-cli without timeout and the monitor-evasion surface forms (no-verify, hooks path to /dev/null, skipped or deleted tests), plus a hook-denial and tool-error census; report would-fire, blocked and slipped-through per class and harness (intake-2387, intake-2428).** ✅ 2026-10-22
  - 2026-10-22 (f8, branch `f8/mining-m2-20261022`): code done; full run scheduled tonight (dhm-mining-full). `scripts/dev_harness/m2_guards.py`: 21 classes; the hooked ones reuse the production scanners (pattern-kill, filesystem containment, llama-cli, shell_scan); outcome from the paired result (blocked_hook / blocked_user / errored / slipped_through / no_result) and hook era (git add-date). Denial census by hook name; tool-error census per tool. Sample `sample-20261022` (65 units, 4,050 tool calls): 63 would-fire, 43 of them containment refusals, all blocked by the hook; 75 hook denials, all Claude Code. Full run: driver `nice -n 19 /usr/bin/python3 scripts/dev_harness/mine_m2.py --projection /mnt/raid0/llm/private/dev-harness-traces/projections/full-20261022T1310Z`.
  - *(2026-10-22, workspace-f8 / mining results.)* **Full run: 21,924 would-fire; acceptance met** (per class x harness x blocked/slipped/errored in the aggregate). Top classes per 1000 tool calls (Claude / Codex / opencode): pgrep_pattern 3.59 / 2.02 / 17.57; edit_running_script 1.45 / 0.085 / 0.67; git_stash 1.16 / 0.004 / 0.40; git_worktree_prune_or_force 1.13 / 0.94 / 0.22; glob_rm 0.75 / 0.006 / 0.50; wholesale_git_add 1.04 / 0.064 / 0.64. Claude hook denials: 2,294 blocked_hook (filesystem_containment 1,171, commit_hygiene 926). Almost every would-fire on Codex and opencode slipped through (no hooks). Follow-ups: DHM-8 to DHM-11 below. Full tables: `docs/design/dev-harness-mining-results-20261022.md`; committed aggregate `data/dev_harness/mining-full-20261022T1310Z.aggregate.json`.
- [x] **DHM-3 — Lesson registry and interrupted-time-series pilot: register feedback memories, incident rules and CLAUDE.md rules with date, channel and a mechanical detector; write the ITS spec (violation, operator-signal and mechanical verified-outcome families; tool-call exposure with a per-turn companion; segmented regression with trend and model/harness change points; permission-mode, work-mode and specificity covariates; session and day clustering, never-lessoned control classes, campaign-grouped self-exclusion); run 3-5 lessons with forbidden surface forms as violations per 1000 tool calls pre/post, split prose-only vs hook-enforced, with the delivered-context rate (intake-2395, intake-2396, intake-2426, intake-2429).** ✅ 2026-10-22
  - 2026-10-22 (f8): registry + spec done, pilot code done; full run scheduled tonight (dhm-mining-full; same driver). `scripts/dev_harness/lesson_registry.json` (290 lessons: 227 feedback memories, 38 incidents, 25 CLAUDE.md rules; 22 with a detector, 9 hook-enforced; built by `m2_lessons.py build-registry`, read-only on its sources). Spec: `docs/design/dev-harness-its-pilot-spec.md`. Pilot: pattern_kill, llama_cli_unbounded, wholesale_git_add (prose then hook), piped_gate_push, glob_rm (prose-only), with never-lessoned control classes and delivered-context rates. The sample covers 3 days only, so it carries no pre/post read.
  - *(2026-10-22, workspace-f8 / mining results.)* **Full-run ITS pilot, 5 lessons; acceptance met** (registry and spec already on main; `lesson_registry.json`, `dev-harness-its-pilot-spec.md`). Violations per 1000 tool calls, Claude, pre vs post: pattern_kill 1.71 -> 0.089 (post-hook, k=15); llama_cli_unbounded 0.45 -> 0.032 (post-hook, k=5); piped_gate_push 0.26 -> 0 (prose-only); glob_rm 0.62 -> 1.30 (prose-only, k=56, ROSE; segmented level change -0.52 does not match the raw rates); wholesale_git_add 0.36 -> 0.56 prose-only -> 1.22 post-hook (k=224, ROSE). Delivered-context rate for glob_rm: 0.27 pre, 0.47 post (memory 0.44, incident log 0.03). Rises filed as DHM-8, DHM-9. Full tables: `docs/design/dev-harness-mining-results-20261022.md`; committed aggregate `data/dev_harness/mining-full-20261022T1310Z.aggregate.json`.
- [ ] **DHM-4 — Prepare a 100-item operator labelling sheet of interrupts plus the next operator message with the reason clusters (correction, slow/hanging, next step myself, requirement change, other) and a lesson-provenance template (harness, session, event range; trigger-phrased applicability) for new incident and feedback lessons; agent labels are not used (intake-2429).**
  - 2026-10-22 (f8): code done; full run scheduled tonight (dhm-mining-full); the sheet is generated by that run into `/mnt/raid0/llm/private/dev-harness-traces/mining/full-20261022T1310Z/dhm4_label_sheet.{csv,md}` (PRIVATE, never commit). 100 items stratified by harness x source; the operator fills `label` (correction / slow_hanging / next_step_myself / requirement_change / other) + `note`; `m2_label_sheet.read_labels` validates. Provenance template in the sheet and the ITS spec §7. Blocked after the run only on operator labelling.
  - *(2026-10-22, workspace-f8 / mining results.)* Sheet ready at `/mnt/raid0/llm/private/dev-harness-traces/mining/full-20261022T1310Z/dhm4_label_sheet.{csv,md}` (PRIVATE), 100 items drawn from 863 interrupt candidates. Not ticked: the operator labels it.
  - *(2026-10-23 15:05Z, operator decision, recorded by workspace-f8.)* The operator chose a **30-item pilot first**: label `dhm4_pilot30.csv` (PRIVATE, same dir as the 100-item sheet; 30 of the 100, harness x source proportions by largest remainder, min 1 per stratum, item_ids kept so labels merge back), then the remaining 70 only if the categories separate. Decision rule, run with `dhm4_pilot_check.py` after labelling: `other` > 25% of labelled items, or any of the five labels used for < 2 items, prints `REVISE_CATEGORIES`; otherwise `PROCEED_TO_70`. Not ticked: the labels are the operator's and the 70 remain.
- [ ] **DHM-5 — Measure the always-on prefix (CLAUDE.md plus the MEMORY.md index) in tokens per turn from transcript usage fields, per harness (intake-2408, intake-2410).**
  - *(2026-10-22, workspace-f8 / mining-m1.)* **Code done; full run scheduled tonight (dhm-mining-full)** (same driver, `dhm5.aggregate.json`). Per harness x source x role: first-turn prompt tokens (input incl. cache = the observed per-turn floor), mean prompt per turn, cache-read share, and the always-on files (claude main CLAUDE.md+MEMORY.md, subagent CLAUDE.md, codex/opencode AGENTS.md) in tokens per turn. Finding: Claude Code JSONL `usage.output_tokens` is a stale streamed value (calibrates to 14.5 chars/token), so it is excluded from chars/token calibration; opencode/codex calibrate, else 3.6 assumed (flagged). Sample: claude main first-turn p50 27.9k tok, mean prompt 211k/turn, always-on files ~12.4k tok/turn (3.6 chars/token assumed: nothing calibrated in the sample) = 5.9% of prompt tokens (44% of the first-turn floor); subagents ~6.1k = 3.7%.
  - *(2026-10-22, workspace-f8 / mining results.)* **Full run measured; NOT ticked.** Always-on files est. 17,158 tok/turn for Claude main (0.451 of the p50 first-turn prompt of 38,056; cache-read share 0.978) and 8,326 tok/turn for Claude subagent, Codex and opencode, where the identical figure shows it is a file-size estimate (chars/token calibration), not a per-harness usage-field measurement. Acceptance asks for usage fields: DHM-5.1 below. Full tables: `docs/design/dev-harness-mining-results-20261022.md`; committed aggregate `data/dev_harness/mining-full-20261022T1310Z.aggregate.json`.
  - [x] **DHM-5.1 — Measure the real per-harness always-on prefix from usage fields** (cache-creation on turn 1 and first-turn input tokens per harness x role, minus the tool-schema and system-prompt baseline from a turn-1 diff against a session with the files absent), replacing the shared 8,326 file-size estimate; then tick DHM-5. ✅ 2026-10-24
    - *(2026-10-24, workspace-f8 sweep.)* Measured from turn-1 usage fields (root `ef7902e2c`: `scripts/dev_harness/mine_dhm51.py`, tests `tests/dev_harness/test_mine_dhm51.py`, aggregate `data/dev_harness/dhm51-20261024.aggregate.json`, results doc section DHM-5.1). Regression of turn-1 cache-inclusive prompt tokens on the char counts sent before the first call, intercept per model/version/directory bucket, bootstrap CIs, file-less units as control. Always-on tokens (95 % CI) / system+tools baseline: Claude subagent **14,628** (12,982-15,707; includes the MEMORY.md index, R² 0.998) / 17,647; Codex main **2,525** (2,266-2,796) / 9,355; Claude main 4,459 (3,436-6,694, weak; mostly orchestrator worktrees, a /workspace main fits ~9.4k-12.5k) / 8,276. NOT measurable from transcripts: Codex subagent (unlogged spawn context, fits span 0) and opencode main/subagent (instruction files not logged; no in-config control). Weakest assumption: file size uncorrelated with unlogged prompt parts within a bucket. Per-unit rows private (0600) under `mining/dhm51-20261024/`.
  - [ ] **DHM-5.2 — paired first-call probe for Codex subagent and opencode** (filed 2026-10-24, f8 sweep): one turn-1 call per harness x role with the always-on files present vs hidden (same cwd, model and config), read the usage-field difference; tick DHM-5 after it. Inference (a few cloud/harness calls, no local model load); class (c).
  - *(2026-10-24, f8 sweep.)* NOT ticked: DHM-5.1 replaced the shared 8,326 estimate for Claude main, Claude subagent and Codex main; Codex subagent and opencode carry no usage-field number because their transcripts do not log the files or offer a control. The remainder is DHM-5.2 (inference).
- [x] **DHM-6 — Draft the guard-denial ledger proposal: every PreToolUse refusal appends ts, hook, session, harness, rule and fidelity=observed to one private JSONL (enables detecting a command executed after its denial); hook edits stay human-applied (intake-2387).** ✅ 2026-10-22
  - *(2026-10-22, workspace-f8 / mining-m1.)* Proposal written: [`docs/design/guard-denial-ledger-proposal.md`](../../docs/design/guard-denial-ledger-proposal.md) (record schema `dev-harness-guard-denial.v1` with keyed-HMAC command blocks joinable to projector tool_call events, best-effort flock append, the 11 refusing Claude hooks + Codex/opencode containment guards, tests, rollout order). Applying it is a human hook edit.
- [x] **DHM-7 — Write a pure-python converter from Claude Code, Codex and opencode transcripts to AgentRun-style JSON (tool calls and results, both interrupt markers kept, sessions split into capped task-window segments, private output), then run a no-LLM clustering baseline over tool-error and denial segments (CPU sentence embedding, k-means, mechanical facets) validated by planted recovery of known incident classes, reporting a cluster only with at least 3 distinct sessions and 2 distinct days (intake-2443, intake-2444).** ✅ 2026-10-24 (DHM-7.1 converter + DHM-7.2 baseline)
  - [x] **DHM-7.1 — converter** ✅ 2026-10-22: `scripts/dev_harness/agentrun.py` (stdlib; Docent AgentRun shape
    written from scratch) → `/mnt/raid0/llm/private/dev-harness-traces/agentrun/<run>/<harness>/<unit>.seg-NNN.json`
    + `index.jsonl`; task windows split at operator prompts and capped (120 msgs / 60k chars / 4k per message); both
    Claude markers kept verbatim, Codex/opencode aborts as synthesized markers. Sample `sample-20261022`: 291
    segments (122 with a tool error, 64 with a denial, 3 with an interrupt), 1.4 s.
  - [x] **DHM-7.2 — no-LLM clustering baseline** over the index's tool-error/denial segments (CPU sentence embedding, k-means, mechanical facets, planted recovery, ≥3 sessions and ≥2 days per reported cluster); needs the full run (UTM-LB2.1) for the day spread. ✅ 2026-10-24 (on the hashed TF-IDF full run, by the predeclared tie rule; see DHM-7.2a)
    - 2026-10-22 (f8): code done; full run scheduled tonight (dhm-mining-full). `scripts/dev_harness/m2_cluster.py`: signed-hashed TF-IDF (D=1024) as the CPU embedding, because /usr/bin/python3 has no onnxruntime or sentence-transformers and `embed()` is the drop-in point; spherical k-means; 5 planted incident classes; reports a cluster only with >=3 sessions and >=2 days. Sample: 122 docs, 6 clusters reported; 3 of 5 planted classes recovered at k=8 (two merged), which is expected at sample size.
    - *(2026-10-22, workspace-f8 / clerical.)* Neural CPU embedder added as the drop-in: `scripts/dev_harness/m2_embed_gguf.py` (`llama-embedding` from the production CPU store, `granite-embedding-97m-multilingual-r2-Q8_0.gguf` already on disk, `-t 1 -ngl 0`, nice 19, docs capped at 1200 chars; wired as `mine_m2.py --embed-gguf`, `m2_cluster.run(embedder=)`; tests in `tests/dev_harness/test_mining_m2.py`). Sample `sample-20261022` (122 docs + 60 planted), same k=10: hashed TF-IDF recovered 3 of 5 planted classes (6 clusters reported), granite-97m recovered 5 of 5 (5 clusters reported, 100% of docs in a reported cluster), 48 s single-threaded, peak RSS 44 MB for the driver. Full-corpus run is scheduled compute, NOT run: `nice -n 19 /usr/bin/python3 scripts/dev_harness/mine_m2.py --projection /mnt/raid0/llm/private/dev-harness-traces/projections/full-20261022T1310Z --agentrun /mnt/raid0/llm/private/dev-harness-traces/agentrun/full-20261022T1310Z --embed-gguf /mnt/raid0/llm/models/granite-embedding-97m-multilingual-r2-Q8_0.gguf` (about 0.25 s per document; output under `mining/<run>/`, private). Stays open for the full-run day spread.
    - [x] **DHM-7.2a — run the granite-97m embedder over the full corpus** (the tonight `dhm-mining-full` job runs `mine_m2.py` WITHOUT `--embed-gguf`, i.e. hashed TF-IDF only). Command: `nice -n 19 /usr/bin/python3 scripts/dev_harness/mine_m2.py --projection /mnt/raid0/llm/private/dev-harness-traces/projections/full-20261022T1310Z --agentrun /mnt/raid0/llm/private/dev-harness-traces/agentrun/full-20261022T1310Z --embed-gguf /mnt/raid0/llm/models/granite-embedding-97m-multilingual-r2-Q8_0.gguf`. CPU compute (1 core, ~0.25 s/doc, llama-embedding from the production CPU store), needs a CPU-quarter grant; private output only. Compare planted recovery and reported clusters against the TF-IDF full run; tick DHM-7.2 on the better of the two. (filed 2026-10-22, f8 evening wrap-up) ✅ 2026-10-24
      - *(2026-10-23, workspace-f8.)* Launcher ARMED (pid 1640838) at `/mnt/raid0/llm/tmp/f8-launchers-20261022/dhm72a-granite/` (filler_run7 --repeat, class cpu, one core, nice 19, ~1 h + 15 m TF-IDF pass; FILLERS row `dhm72a-granite`; booking requested from workspace-58). Runs from detached root worktree `f8-dhm72a-run` @ ea5722f79; output private at `mining/full-20261022T1310Z-granite97m` (`--out` added so the TF-IDF run dir is not overwritten). Report-only PREDECLARATION; DHM-7.2 ticks on the better of the two runs.
      - *(2026-10-24, workspace-f8 subagent, verification.)* The run is DONE: `dhm72a-granite` ENDED rc 0 at 2026-10-23T15:57:18Z, and its FILLERS row is COMPLETE. Output (private): `mining/full-20261022T1310Z-granite97m`.
        - What remains is the zero-compute read-out: planted recovery and reported clusters vs the TF-IDF full run.
        - Then tick DHM-7.2a, and DHM-7.2 on the better of the two runs. No launcher is needed.
      - *(2026-10-24, f8 sweep.)* Run DONE 2026-10-23 15:57Z, rc 0, `aggregate_valid` true (job `dhm72a-granite`, q2 grant, 4,844 s, peak RSS 368 MB; private output `mining/full-20261022T1310Z-granite97m/`). Predeclared quantities: planted recovery 3/5 (fs_containment, pattern_kill, pytest_workers; git_stash and wholesale_add merged into one cluster at purity 0.5), 78 of 80 clusters reported (>= 3 sessions, >= 2 days). Versus TF-IDF 3/5 and 80/80: delta 0 planted, -2 reported; flipped +pattern_kill +pytest_workers, -git_stash -wholesale_add. Predeclared rule: a tie goes to TF-IDF (no model dependency).
      - *(2026-10-24, workspace-f8 read-out addendum; same verdict, re-derived independently from both private aggregates.)* Per-class best-cluster purity TF-IDF -> granite: fs_containment 0.141 -> 0.045, git_stash 0.128 -> 0.500, pattern_kill 0.375 -> 0.667, pytest_workers 0.375 -> 1.000, wholesale_add 0.255 -> 0.500. Granite's cluster stage took 4,634.9 s against 5.65 s for TF-IDF, which shows the embedder ran. Three additions:
        - A counts-only aggregate is now committed: `data/dev_harness/mining-full-20261022T1310Z-granite97m.dhm72.aggregate.json`. It has top terms and rules dropped, carries a `dhm72a_vs_tfidf` comparison block, and passed `raw_trace_publish_preflight`. The results-doc table is in the section "DHM-7.2a".
        - Bug fixed: the private aggregate's `notes` said "hashed TF-IDF (no model)" even under `--embed-gguf`. `mine_m2.py` now names the GGUF, and a test is added.
        - Belief: there is no adapter yet for `dev-harness-aggregate.v1`. The source row exists (`scripts/vidya/adapters/README.md`) and the adapter task VB-LB1.1 is open, so there was nothing to dry-run. This aggregate is a ready first input for VB-LB1.1.
  - *(2026-10-22, workspace-f8 / mining results.)* DHM-7.2 baseline on the full corpus (hashed TF-IDF, no model): 13,989 docs, k=80, 80 reported (each >=3 sessions and >=2 days), planted 3/5 recovered (fs_containment, git_stash, wholesale_add yes; pattern_kill, pytest_workers no; best-cluster purity 0.13-0.38). DHM-7.2 stays unticked pending DHM-7.2a (granite embed, NOT run).

- [ ] **DHM-8 — Guard the glob rm -rf class with a hook (D9, per-change operator ack required; file the proposal, do not apply).** The prose-only lesson did not reduce Claude violations: 0.62 pre -> 1.30 post per 1000 tool calls (k=56 vs 116), 180 would-fire, 12 blocked. Draft the PreToolUse predicate from `m2_guards.py` glob_rm and the false-positive count over the same corpus. (2026-10-22 mining results)
- [ ] **DHM-9 — Explain why wholesale_git_add ROSE after its hook** (Claude 0.36 pre, 0.56 prose-only, 1.22 post-hook per 1000 tool calls, k=224): split by main vs subagent, session cohort and campaign, and check the hook's pathspec coverage (harness mix versus a hook gap). Output: attribution table, then a fix proposal (D9 ack for any hook edit). (2026-10-22 mining results)
- **[declined: ws58 2026-11-03 content-review: merged into DHM-11 — the per-harness coverage matrix covers the pgrep_pattern class]** **DHM-10 — pgrep_pattern guard coverage for opencode and Codex.** would-fire 17.57 (opencode), 2.02 (Codex), 3.59 (Claude) per 1000 tool calls; 1,658 of 1,659 opencode and 889 of 948 Codex slipped through. Decide per harness: port the process-pattern check, or write an explicit decline (pgrep alone is read-only; the harm is the kill, `pattern_kill` is already counted separately). Hook edits are D9 (per-change operator ack). (2026-10-22 mining results)
- [ ] **DHM-11 — Hook coverage for Codex and opencode in general.** Both are `harness_uncovered` for every guarded class (e.g. codex git_worktree_prune_or_force 442 would-fire, 0 blocked; opencode write_tool_outside_allowlist 7,138 would-fire, but the allowlist is Claude-rooted, so first calibrate it per harness). Produce a per-harness coverage matrix and a port-or-decline per class. Hook edits are D9 (per-change operator ack). (2026-10-22 mining results) Includes the pgrep_pattern class (absorbs DHM-10): would-fire 17.57 (opencode), 2.02 (Codex), 3.59 (Claude) per 1000 tool calls; port the process-pattern check or write an explicit decline per harness.

#### Open Questions

- Does a memory-only lesson change its violation rate at all, or only hook-enforced ones?
- What fraction of interrupts are agent errors (operator labels, DHM-4) versus slow/hanging or scope change?

#### Notes

- **Sources (operator 2026-10-22, scope ruling: mine EVERYTHING; every record carries a `source` tag epyc|host|twyne).**
  opencode: the read-only hourly snapshots `/mnt/raid0/llm/opencode-db/{epyc.db,host-daniele.db}` (symlink to
  `/mnt/raid0/llm/opencode/readonly/`; at most ~1 h stale, full history; open `file:<path>?mode=ro`, retry once if the open
  fails because the copy is being replaced; tables `session`/`message`/`part`, never `event`). Claude Code + Codex:
  `/mnt/raid0/llm/cloud-llm-vault/{host,twyne,epyc}/{claude,codex}/` (append-only JSONL). The LIVE opencode stores
  (`~/.local/share/opencode/opencode.db`, `/mnt/raid0/llm/opencode/<src>/opencode.db`) are never opened for mining.
  Shared helper: `scripts/dev_harness/dh_sources.py` (`OPENCODE_RO_DBS`, `open_ro`, `refuse_live_opencode_path`).
- Inputs are read from the existing conversation backup (the nightly cloud-llm-vault sync and the ai-sessions tarballs;
  coverage checked by UTM-LB1) through the private projector (UTM-LB2); no parallel backup is built. Outputs are
  aggregate-only and private (F3-LB1). epyc-root is a public repository: never commit transcript content.
- Hosted annotators are not used on our data (typed-decision ruling); labels come from the operator.
- harness-improvement-loop.md excludes the shell surface from its mutation loop, which is why this measurement
  work has its own owner.

#### Memory index readability from intake-2617/2619 (ws58 intake 2026-11-02; operator approved "Approve, go to Stage 4", D9 acknowledged for scripts/coordination)

Plan: [knowledge-transparency.md](../../research/deep-dives/ws58-jev-20261102/knowledge-transparency.md). **Order (operator, 2026-11-02):** (1) SA-1 + JEV-1; (2) SA-2, SA-3, JEV-3; (3) JEV-5 phase A, KT-1, KT-3; (4) the rest (JEV-2, JEV-4, JEV-6, SA-4, KT-2, KT-4, KT-5). JEV-5 phases B/C only after the operator has used phase A.

- [ ] **KT-5** [S] Split the Claude memory `MEMORY.md` index into category index files under the load limit, and include memory and progress files in the KT-3 map's search by reusing the kb-search index (DHM-5 measures the always-on cost). Note 2026-11-02: proposal at `/mnt/raid0/llm/tmp/ws58-kt5-memory-split-proposal.md`; ws58 applies the memory split. The kb-search indexer config is not in any of our repos, so the search half needs its owner located. removes: the truncated-on-load single index and grep-only access to memory files.
