# 2026-09-16 — sub-cleanup2 (cleanup subagent)

Follow-up to [`2026-09-16-sub-cleanup.md`](2026-09-16-sub-cleanup.md). There was no inference and no
process management. No `*-index.md` file was edited. Agent log session: `sub-cleanup2`.

## Task 1 — EVL-03: E8 boxes closed SUPERSEDED (per ruling_op19)

The file is `handoffs/active/autopilot-decision-plane-audit-2026-07-22.md`. Each box was flipped to `[x]` with
`✅ 2026-09-16 CLOSED SUPERSEDED (not completed)` and cites `ruling_op19_e8_chain_20260827.json` (root `1ee8bd7c`).
This follows the B10 precedent at :382 and the SESSION_LIFECYCLE *Two axioms* date stamp, which goes on the
checkbox line and after the task-key text so the timeline key does not change.
- :223 E8 RE-ARM (full note; original text retained)
- :302 E8 lineage-composition successor · :310 E8 universal abort terminalization ·
  :315 E8 staged-input/race-retry layout · :320 E8 c1 race/finalizer path
- :404 child "Repair the historical producer-pin … before final E8 promotion". It is an E8-successor
  child of :320, and a parent should not be closed while its child stays open.
- :415 E8 quality baseline reseed/apply

## Task 2 — ruling_op19 pointer notes in six handoffs (history text untouched)

- `autopilot-continuous-optimization.md:1716`: under the open "E8 quality-baseline reseed" box. The box is
  left open because closing it is the owner's call.
- `non-inference-backlog.md:312`: OBS-10
- `stale-open-audit-2026-07-18.md:185`: end of the mainB READ-CERTIFIED (7 rows) bullet
- `session-bus-thin-dispatcher.md:1949`: C39
- `moe-spec-cpu-spec-dec-integration.md:419`: after the "E8-reseed/OP-19 gate" registry-implication line
- `loop-owned-fleet-implementation.md:632`: after the "folded into OP-19" paragraph

## Task 3 — deleted-dispatcher notes

`dispatch_swarm_fanout` / `src/swarm_fanout.py` (with `SwarmCompletion`, `SwarmFanoutResult`,
`bradley_terry_aggregate` and `length_proxy_aggregator`) were deleted in orchestrator `771348c8` (2026-06-16,
an ancestor of `origin/main`). This was verified by `git show 771348c8^:src/swarm_fanout.py` and by 0 hits
for these symbols in `origin/main`.
- `bulk-inference-campaign.md:496`: a note at the head of the J14 description cell
- `decision-aware-routing.md:212`: a blockquote covering the DAR-6.1..6.4 text and the :223 bullet

## Task 4 — EVL-12 A2 residue fixed (pending integration)

The fix is on orchestrator branch `sub/cleanup2-20260916` @ `d111d432`, in worktree
`/mnt/raid0/llm/worktrees/sub-cleanup2-orch`. It is not merged or pushed.
- **Finding:** the research `question_pool.py` has **no `load_questions_by_ids`**; only the orch shadow copy
  has it. The bare imports bound the orch copy, while the sampler (`8d729ca1`) reads the research copy, so
  `--rebuild-pool` built the pool with a different module from the one that sampled it. Both copies point
  `POOL_FILE` at the same research pool file.
- **Fix:** `seeding_sampling.build_question_pool()` and `seeding_sampling.load_questions_by_ids(ids, *, logger)`
  both use the existing path-bound `_load_research_benchmark_module`. The second is built over research
  `load_pool(warn_stale=False)` and keeps the original semantics (suite/ prefix strip, input order, de-dup,
  missing-id warning). Both fail closed. The call sites changed are
  `seed_specialist_routing.py:998,1163` and `seed_specialist_routing_v2.py:920`.
- **Tests:** the existing `main()` tests previously planted `sys.modules["question_pool"]`. After the fix
  they would have run the REAL research `build_pool`, so they now plant a stale decoy and patch the loader.
  Three new helper tests use a fake `EPYC_RESEARCH_ROOT` tree. 352 passed across every test file referencing
  `question_pool`/`seeding_sampling`/`seed_specialist_routing`. Ruff: no new findings (8 pre-existing).
  Mutation check: restoring the bare imports fails 4 tests.
- gitnexus: the orchestrator is not in the gitnexus index (not among the listed repos), so the blast radius
  was derived with grep. The change is confined to two CLI `main()` sites plus additive helpers, so the risk
  is LOW.
- Recorded in `eval-tower-architecture-audit-2026-07-20.md:282` (`[x]` residue fixed) and :283 (new `[ ]`
  integrate `d111d432` into orch main, for the owning session).
- Left as is: the orch shadow `scripts/benchmark/question_pool.py`, still imported by
  `deprecated/seed_specialist_routing_v1.py` and its own tests.

## Checks

`python3 scripts/handoffs/index_state.py --check`: 1 problem, the known `FRESHNESS: master index generated
block is stale`. cite-check is clean. Write mode was not run, because the master index belongs to the main session.

Belief kernel: nothing was measured, and no unwired verified-finding source was found.

## Prepared for the main session (not applied)

The `research-evaluation-index.md` EVL-03 next action should now move past E8 to the next open non-E8 box.
EVL-12's next action should drop "the unowned A2 residue" and point at integrating `d111d432`.
