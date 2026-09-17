# 2026-09-17 — sub-vb-wire (VB-AP-PROMO-RULE, VB-RUNNER-PATHS)

This was zero-inference work. Nothing was started, stopped or killed.

## VB-AP-PROMO-RULE — done (root `f71277f7`)

- **Producer shape** was verified on orchestrator main `a1a0251a`:
  - `scripts/autopilot/autopilot.py` stamps `eval_details.frontier_admission = "representative"`
    (`src/autopilot_core/learning_exclusions.py`) on clean frontier points.
  - When a promotion was decided, it also stamps `eval_details.promotion_rule` and
    `promotion_status` (`pending_commit` | `refused`).
  - The rule vocabulary is in `safety_gate.py`: `frontier`, `empty_frontier_repro`, `seed`,
    `archive_unavailable_no_baseline` and `refused_guard_unavailable`.
  - A `pending_commit` row is confirmed only by a later `baseline_promotion` ledger event with that
    `source_trial_id` (re-review B3).
- **Adapter change** (`scripts/vidya/adapters/autopilot_journal.py`):
  - The three fields are carried verbatim.
  - `promotion_committed` is joined within the shard.
  - An uncommitted pending row gets a stated reason.
  - A pending row on the shard's newest trial is held back, so the append-only ledger never records a
    promotion as uncommitted while its commit is still being written.
  - Absent keys stay absent, and the grade is unchanged.
- **Tests:** `tests/vidya/test_autopilot_journal_adapter.py` and `test_autopilot_settled.py`,
  21 passed. The end-to-end test ran against the real `ExperimentJournal` with
  `EPYC_ORCH_ROOT=<orch main checkout>`.
- **Ingest:** 0 rows. The live journal was last written 2026-08-09, so it has no post-hook trials.
  The dry run matched 1 unit, projected 0 and declined 1.

## VB-RUNNER-PATHS — done (research `0b295a25`)

- **New helper, `scripts/benchmark/belief_capture.py`:**
  - resolves the root from `EPYC_ROOT` and refuses if it is unset or wrong;
  - loads capture modules by file path;
  - `preflight()` runs before the GPU claim;
  - `CaptureLog` prints a stderr banner, records a `belief_capture` block, and sets exit code 3.
- **`review_f1/ev13b_run.py`:** the `/workspace/scripts/vidya` literal and the exception swallow are
  gone.
- **`prb_t4_tale_gpu.py`**, ported to main from `sub/gpu-runner-20260916` (`91d66725` (on main as `0b295a25`)):
  - The tmp worktree literal is gone.
  - The harness runs from its own checkout, which has the stratified sampler.
  - `--pool` and `--python` are checked before the server starts.
  - A failed or missing suite capture is loud.
- **Tests:** `scripts/benchmark/test_belief_capture.py` (10 passed) and `review_f1/tests` (34 passed).
- **VB-PRB-T4:** its driver blocker is cleared (annotated, left to its owner to tick).

## Follow-ups filed

- **VB-RUNNER-PATHS-2:** move `score_tulving_run.py` and `occ1/run_occ1.py` off their guessed-root
  fallback lists.
- **VB-AP-PROMO-RULE-INGEST:** run the first ingest after AutoPilot restarts on orchestrator main.
