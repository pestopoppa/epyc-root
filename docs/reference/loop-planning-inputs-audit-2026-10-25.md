# AutoKernel and AutoPilot planning inputs after the tmp reclaim (audit, 2026-10-25)

Workspace-58 ran this audit read-only, through a subagent. The operator's question: do the loops' pre-seeded hypotheses and planning-context inputs survive the 10-2x reclaim, and does anything need to change to guarantee proper loop operation? Code line numbers are taken at the shared-clone HEADs: research `99301fa14`, 26 commits behind origin/main `413f5b7f5`; orchestrator `84f6f6f15`, equal to origin/main.

## Answers

- **Nothing REQUIRED is missing.** Both planners have every input they refuse to run without: the belief ledger and reader, AK `program.md`, the store DBs and bundles, and AutoPilot's state, model_descriptors and roster. The reclaim deleted no file a planner reads programmatically.
- **Neither loop is running.**
  - AK last planned on 10-22 (Q38FN `state-fa-20261022`).
  - AutoPilot's last trial was #1505 on 08-09; it is `paused=true`, and it has never completed a belief read.
- **The 10-21 decision is implemented in both loops.** Planning refuses without current belief context (fail-closed), raises an alarm, runs queued work only, and the receipt records the ledger state.
  - AK: actors.py:3666-3669, loop.py:1650-1686, belief_context.py:542-570.
  - AutoPilot: autopilot.py:9137-9196, planner_coordinator.py:346, loop_beliefs_bridge.py:616-641.
  - **Gap in both:** an empty `ready` section (`no_applicable_claims`, `inapplicable_target`) is not treated as "ledger not current".
- **No backup covers loop state.** The NIB2-92 job (`backup-claude-sessions.sh` → `claude-backups`, keeps 3, Micron mirror) holds only Claude and Codex transcripts and memory, plus the opencode DBs. md127 is RAID0, and the root filesystem is 94% full.

## Top risks
1. **Loop state is single-copy on RAID0 with no backup:** `state/vidya` (42 MB), the AK store DBs and inboxes, AK `loop-memory`, the AutoPilot journal shards (no checkpoint includes them), AutoPilot state and the StrategyStore.
2. **The TensorFold 1.1.4 seeds exist only in tmp:** `/mnt/raid0/llm/tmp/tensorfold-114-review-20261024/inbox-drafts/` holds 7 ids in 3 drafts, not yet placed in any store.
3. **Stale belief reader.**
   - Both loops prefer `/workspace`, which is 145 commits behind root origin/main. Its `loop_beliefs.py` lacks the read log (cc69943a0) and the AC9 knob cap (1f3a14a4d).
   - Resolution order:
     - AK: argv → EPYC_ROOT_REPO → /workspace (if it holds the reader) → views (belief_context.py:101-118).
     - AutoPilot: argv → /workspace → views, with no env step (loop_beliefs_bridge.py:119-131).
   - Only the 10-22 AK run passed `--belief-root-repo` pointing at the current views checkout.
4. **Silent-empty inputs, with no error raised.**
   - AK: a wrong or new `--store` auto-creates an empty `experiments.db`, which also disarms do-not-repeat (controller/experiments.py:405-416; dispatch_guard.py:209-210). A missing inbox dir returns `[]`, and non-`.md` seed files are dropped (inbox.py:46-49). Shared-history errors go only to `errors[]` (archive.py:627-631).
   - AutoPilot: missing journal shards give 0 entries and an empty Pareto frontier, with only a warning (experiment_journal.py:919; pareto_archive.py:215-225). A missing StrategyStore is recreated empty (strategy_store.py:301,325-326). A missing constitution becomes the literal "(not found)".
5. **Test-polluted live input:** `/mnt/raid0/llm/tmp/seeding_batch_telemetry.jsonl` holds 48 microsecond test rows and is an AutoPilot planning input (seeding_telemetry.py:58-64).
6. **The 27B GPU campaign bundle can't relaunch.** It points at a missing `tmp/ak-27b-gpu-run2-20261006/anchor-b0ba1d427`. It must be rebuilt before the TensorFold 27B seeds can run.
7. **Seed write-ups are gone.** 12 of the 16 tmp paths cited inside AK inbox seeds are missing, including the original Fable CPU low-bit and structural seed write-ups and `ds41-hypotheses/HYPOTHESES.md`. The seed text itself survives inline in the store inboxes.
8. **Load-bearing tmp dirs that are not KEEP-marked:** `ak-q38fn-topk-20261022` (launcher of the last real AK run), `ds41-1017-ak-floor-20261022` (2 GB), `ak-loop-lanes` (pool.py:61 default) and `v9v-build-base` (production.py:128 default).

## Ledger and missing tmp paths
- 1,342 of 38,415 records cite tmp: 187 distinct paths, of which **22 are missing** (106 references).
- `prepare` performs no existence check. Grades are frozen at write time, and `adapters/evidence_durability.py` is a write-side diagnostic, so `prepare` neither degrades nor refuses. The effect on planning is not material: about 24 host-tier claims per CPU target cite missing files, and none is usable.
- `cli.py verify`: chain_ok. Published tamper checkpoints stop at seq 12,538, so about 25.9k frames are protected by the chain alone.

## Usable claims, live re-count (read-only)
| Target | Target-tier | Usable ids |
|---|---|---|
| Qwen3.8-27B-Q8_0 GPU | 74 | 16 (0 on 10-21) |
| Q38FN CPU | 371 | 23 |
| DS41-1017 CPU | 151 | 15 |
| Q3.6-35B CPU | 394 | 16 |

The last AK receipts (10-22, Q38FN, 4 turns) declared no reliance. **VB-REFOCUS-NONEMPTY-READ-PROOF is still OPEN.**

## Belief redesign
- DESIGN.md (62 KB) and the review REPORT.md (16 KB) exist only in tmp, untracked; they are KEEP-marked.
- Phase 1 landed through the P1 integration merges (9bc641bd5, 7a5535062).
- Phase 1 moved no planning input.

## Seeds
- AK's only live seed source is `<store>/inbox/*.md`.
- `loop/seeds/` is installed only by a manual `seed.py` run. Tracked seeds 04-06 are in no store, and 01-03 differ from the installed copies.
- No `--preseeded-hypotheses` JSONL exists anywhere.
- AutoPilot: 48 rows in operator_seed_strategies.yaml reach the planner only through the StrategyStore (49 opseed rows). The YAML and the DB have drifted (1 row never seeded, 1 stale). operator_hypotheses has 0 entries. No AutoPilot input references tmp.

## Recommendations (ranked)
1. **Nightly off-RAID0 backup of loop state**, under 0.5 GB:
   - state/vidya;
   - the live stores' experiments.db, inbox, accumulator, journal and resume DBs;
   - loop-memory DB and inbox;
   - campaigns/*/inputs*;
   - AutoPilot state, journal shards, strategies and operator_hypotheses.
2. **Move the tmp-only planning inputs to durable homes:**
   - TensorFold drafts → research `loop/seeds/hypotheses/`, or the store inboxes once the hold lifts.
   - The belief design and review docs → root `docs/design/`.
   - Launchers → `campaigns/<c>/launch/`.
   - cor-anchor and the ds41-c57 evidence → under campaigns, re-pointed through a new bundle.
   - KEEP-mark the four unmarked load-bearing dirs, and fix the KEEP text.
3. **Pin the current belief reader:** default to the views checkout, or refuse with `reader_stale` when the chosen ROOT HEAD ≠ origin/main. Until then, every launcher passes `--belief-root-repo /mnt/raid0/llm/views/epyc-root-main`.
4. **Fail closed on the silent-empty cases** (risk 4), and alarm when an empty model-tier section comes back for a target that has had usable claims before.
5. **Isolate the telemetry path in tests,** move its default out of tmp, and set the 48 fake rows aside before any AutoPilot restart.
6. **Make reclaim refuse referenced paths:** campaign inputs, inbox content, code defaults and recent run argv. Extend scratch_cleanup.py's KEEP-REFERENCED check, and make trash-sweep.sh do a dry run against that set first.
7. **Seed hygiene:** install or withdraw seeds 04-06; re-run seed_operator_strategies.py; rebuild the 27B GPU bundle.
