# 2026-09-16 — sub-vbmhsops (VB-MHS-OPS adapter pair)

Zero-inference subagent. It ran in worktree `/mnt/raid0/llm/worktrees/sub-vbmhsops` on branch
`sub/vb-mhs-ops-20260916`, based on origin/main `5a1250ff`. The branch is not pushed. The producer
was read, never written: orchestrator `sub/gate-frontier-20260916` at `239ac5b8`, plus AP-53's
ledger on `main`.

## What landed

`scripts/vidya/adapters/mhs_guard.py` holds two measurement-class projections. Both only project;
`claim_tuple.grade()` decides the grade, and with no codified protocol every row grades as an
OBSERVATION.

- **`mhs_guard_verdict_rate`** (`cli.py ingest mhs-guard-verdicts`)
  - Emits one row per closed UTC-day window and reason class. The four classes are
    `eval_instance_leakage`, `eval_leakage_vocabulary_unavailable`, `effect_risk_gate` and
    `other_transfer_safety`.
  - Numerator: AP-53 `transfer_safety` records, classed by the prefix of `gate_detail`, which
    holds the mutation's `safety_reason`.
  - Denominator: the journal `prompt_mutation`/`code_mutation` rows the guard actually screened,
    joined by `trial_id`.
  - Held out of every denominator:
    - skipped rows with no ledger record, because no mutation was produced;
    - `syntax_validation` rejects, because `actions.py` checks syntax before it reads the guard
      verdict.
  - `vocabulary_unavailable` rejections are held out of the leakage denominator only.
- **`mhs_guard_operability`** (`cli.py ingest mhs-guard-ops`)
  - Emits one row per `preflight_failed` event and one per closed `alarm_raised` → `alarm_cleared`
    interval (value = seconds open).
  - Open raises, and raises superseded by a restart, yield no row. `open_alarm_intervals()`
    reports them.
  - An orphan clear refuses the unit.

## Absence rules

- **No pre-hook rows.** Nothing the producer persists marks a clean window as screened. The
  verdict source therefore declines every unit until `HOOK_SINCE` or
  `VIDYA_MHS_GUARD_HOOK_SINCE` is set. That epoch should be the time AutoPilot restarts on the
  merged producer, tracked as the new task VB-MHS-OPS-HOOK.
- Only closed windows project.
- An idle window is not a 0 % rate.

## Tests and fixture

- **Fixture:** `tests/vidya/fixtures/mhs_guard/regen.py` writes it with the producer's own code:
  `EvalLeakageMonitor`, `ExperimentJournal.append_ledger_event`/`record`,
  `rejected_mutation_ledger` and the `prompt_forge` reason builders.
- **Producer drift check:** `test_mhs_guard_adapter.py` compares the pinned field names, event
  names, reason prefixes and the syntax-before-guard order against the producer source, read with
  `git show` from the branch. A producer change fails this test.
- **Producer discrepancy:** the README row said the events carry `ts`. They actually carry
  `timestamp`, which `append_ledger_event` stamps.
- **Real-data dry run:** against the live `orchestration/` directory, `mhs-guard-ops` declined
  (no events yet) and `mhs-guard-verdicts` matched 0 units (the AP-53 ledger does not exist yet).

## Results

- `tests/vidya`: 1301 passed, 80 skipped. This includes 15 new adapter tests and the new
  end-to-end cases in `test_ingest_sources.py`.
- `index_state.py --check`: exit 0.
- `cite-check` on the handoff: clean.
- `cite-check` on `scripts/vidya/adapters/README.md` exits 3 both before and after this change,
  so the failure predates it. The three overturned citations are the illustrative `intake-896`
  citation-form table (lines 307–308) and the `intake-1245` row (line 271). The rows added here
  cite no intake.

## Bookkeeping

- VB-MHS-OPS is ticked.
- VB-MHS-OPS-HOOK is filed as a new task; it waits on the merge and restart.
- Both README rows now read "adapter ready, producer pending merge (sub/gate-frontier-20260916)".
