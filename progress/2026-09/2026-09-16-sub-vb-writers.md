# 2026-09-16 — sub-vb-writers (durable writers for VB-AP53-RATE and SC83)

Zero-inference subagent with no process management. Both worktrees are based on origin/main:
- root: `/mnt/raid0/llm/worktrees/sub-vbwriters-root`, branch `sub/vb-writers-root-20260916`
- orchestrator: `/mnt/raid0/llm/worktrees/sub-vbwriters-orch`, branch `sub/vb-writers-orch-20260916`

Neither branch is merged or pushed.

## Problem

Two belief-kernel sources had a merged producer but wrote nothing durable, so no adapter could read
them:
- the AP-53 re-proposal rate (VB-AP53-RATE);
- the RA-9 reviewer false-accept rate (SC83).

## Orchestrator `2789b56d`

### VB-AP53-RATE: `scripts/autopilot/reproposal_rate.py`

- **Hook.** `autopilot.py` calls it after both `journal.record` sites. The call is fail-open, never
  touches the journal, and can be disabled with `AUTOPILOT_REPROPOSAL_RATE_WRITER=0`.
- **Arming.** The first call writes an `armed` record. Windows before `armed_from_trial` never get a
  row.
- **Output.** Each closed 100-trial window gets one self-hashed line in
  `orchestration/autopilot_reproposal_rates.jsonl`. The line carries:
  - counts, split by action type and by standing class;
  - `definition_sha256` over the planner fold's key, rejection-class and clearing code. A test pins
    this fold equal to `rejected_configs_from_entries`.
  - the journal and mutation-ledger prefix digests;
  - up to three rows, each with its numerator and denominator stated: `all_trials`, `keyed_trials`,
    and the ledger's `diff_repeat_rate`.

### SC83: `false_accept_record.py` plus `scripts/review/score_false_accept.py`

The script writes one line per scoring run to `data/reviewer_eval/false_accept_runs.jsonl`.
- The RA-12 `check_binding` filter runs before scoring. Stale verdicts are listed.
- The endorsement is read only from the signed body.
- A run that mixes reviewer configs is refused.
- The denominator must account for every decoy.
- There is no protocol (RC-6a has not merged).
- A run with no scored decoy writes no row.

`gold_annotations.py` and `review_envelope.py` are untouched.

### Blast radius

The orchestrator has no GitNexus index; `gitnexus impact` finds no orchestrator repo. Deriving it from
the source:
- the only producer edit is 11 added lines in `autopilot.py`: one wrapper and two call sites;
- no signature changed;
- risk is LOW.

### Tests

- New: 12 (AP-53) + 7 (SC83).
- Adjacent AP-53, journal, gold and envelope suites: 894 passed.

## Root (this branch)

- **Adapters.** `adapters/autopilot_reproposal_rate.py` and `adapters/reviewer_false_accept.py`.
  - They are strict readers and registered projections, with no ladder.
  - The shared ladder grades every row `Judged/Located`.
  - The writer half of each pair lives in the orchestrator, because it must run where the producer
    runs.
- **Wiring.** Both are registered in `ingest_sources.py` and `cli.py` as `autopilot-reproposal-rate`
  and `reviewer-fa`.
- **Fixtures.** `tests/vidya/fixtures/vb_writers/` holds output from the real writers, and
  `generate.py` regenerates it.
- **Docs.** README rows were added. The SC83 box is ticked, the VB-AP53-RATE box was added and
  ticked, and the VB-WIRE status table is updated.
- **Tests.**
  - The root adapter tests number 10 + 9. Each includes a live cross-repo test: the real writer, then
    `cli.py ingest`, then the tuple. It runs when `EPYC_ORCHESTRATOR_ROOT` points at a checkout that has
    the writers; otherwise it is skipped.
  - `test_ingest_sources.py` now covers both names.
  - Full `tests/vidya` with the orchestrator worktree: 1243 passed, 80 skipped.
- **Gates.**
  - `index_state.py --check`: 0 problems after regeneration. The open count went 407 → 406.
  - README cite-check flags only the 3 known `overturned` citations (intake-896, intake-896#03,
    intake-1245), which are also on origin/main.

## Backfill decision

The rule is spec §4.7: "a row that predates a producer's provenance hook is skipped rather than
back-filled". It is followed exactly.

**AP-53: zero belief rows.**
- `reproposal_rate.py backfill` writes `*.retrospective.jsonl`. Every line is
  `retrospective: true` with `belief_measurements: []` and a `no_warrant_reason`: today's key
  definition and supersessions are not the ones that were in force at those trials.
- The reader declines that file.
- A read-only run over the live journal (trials 0-1505, 14 windows) went to
  `/mnt/raid0/llm/tmp/sub-vb-writers/ap53_retro_w100.jsonl`. It was not committed.
  - Result: 48 re-proposals, which is 48 of 216 keyed trials and 48 of 1366 trials overall.
  - By action type: structural 43, prompt 3, code 2.
  - This matches the AP-53 planner-fold replay (48/216).
- The one-off 133/1372 came from a scratch script that is not in git. It counted numeric trials,
  which this key excludes. It remains a non-gating observation.

**SC83: nothing to backfill.** No decoy corpus or scored reviewer run exists.

## For the owning session

1. Merge orchestrator `sub/vb-writers-orch-20260916` first, then this branch.
2. The AutoPilot restart that is already due (AP-53/AP-55/W3) arms the hook. The first post-restart
   trial arms it at the next 100-trial boundary, and the first rows appear when that window closes:
   at most about 200 trials later.
3. SC83's trigger is the first RA-9 decoy corpus plus a scored reviewer run:
   `score_false_accept.py`, then `cli.py ingest reviewer-fa`.

## Fable review fixes (MERGE-AFTER-FIX; orchestrator `e93edfdb`)

1. **SC83 stale arbitration decoys.** The writer listed every stale decoy under `stale`, including
   `needs_arbitration` decoys that `false_accept_rate` routes to `excluded_for_arbitration`. The
   reader's `stale <= unscored` check then voided the whole file. Now:
   - `stale` holds settled decoys only;
   - stale arbitration decoys go in a new `stale_excluded`, and the reader checks it against
     `excluded_for_arbitration`;
   - tests on both sides; fixture run `fixture-r3` comes from the real writer, and the reviewer's
     repro now projects.
2. **AP-53 journal rewind.** Before writing, `record_closed_windows` checks each emitted window's
   recorded journal prefix digests against the current shards. The check makes one hashing pass per
   shard, memoised by inode; a size check runs first, so in-place truncation is still caught. On a
   mismatch it renames the file to `*.rewound-<utc>`, logs a warning, and re-arms. Tests cover a
   rewind followed by a re-run window, and an in-place edit that keeps size and inode.
3. The source-identity key was renamed `mutation_ledger` → `rejected_mutation_ledger`. The BSV-3
   tripwire (`test_mutation_ledger_tripwire.py`) greps tracked files for the whole identifier
   `mutation_ledger`, so the committed file tripped it.

Checks after the fixes:
- orchestrator: 897 passed across the new and adjacent suites;
- root: `tests/vidya` 1305 passed, 80 skipped.
