# 2026-09-17: sub-land-vidya (land the stranded belief-kernel adapter branches)

This session ran no inference and did no process management. Tests were offline.

Three root branches from 2026-09-16 held vidya adapter work that had never reached origin/main. Their
orchestrator halves had already landed in the AutoPilot train (orchestrator `a1a0251a`):
`sub/ap54-root-20260916` (`7280da63`), `sub/ap55bc-root-20260916` (`febf56cd`) and
`sub/vb-writers-root-20260916` (`cace2013`, `9e1d5ab3`). `git cherry` listed every commit as missing.

**Pre-check.** Before merging, root main was grepped for the branches' content:
- `eval_fence_enforcement`, `ap55_gate`, `autopilot_reproposal_rate` and `reviewer_false_accept`: zero
  hits under `scripts/vidya` and `tests/vidya`.
- `would_hold`: one hit, a README note only.

None of the content had landed another way.

| Commit (branch `sub/land-vidya-adapters-20260917`) | What |
|---|---|
| `7d1ed3a5` | merge ap54: `eval_fence_enforcement` |
| `48dc08b3` | merge ap55bc: `ap55_gate` legs |
| `3671df47` | merge vb-writers: VB-AP53-RATE and SC83 adapters, ingest names, handoff reconciliation |
| `9d3d4f82` | carry the `cd79b80e` `would_hold_*` counterfactual verbatim in `ap55_gate` |
| (this commit) | closure-inflation annotations and this shard |

If the push rebased, these SHAs changed. The final SHAs are in `git log origin/main`.

## Field shapes, checked against orchestrator main (`61793b38`, which contains `a1a0251a` and `cd79b80e`)
- `experiment_journal.measurement_tuple` writes the following, which is what the adapter reads:
  - `measurement.eval_fence_enforcement`, from `details.eval_fence.fence_enforcement`;
  - `measurement.ap55_gate = {mode, seed_rerun, batch_homogeneity, hold}`.
- `autopilot.py` writes `eval_details.ap55_promotion_gate = gate_summary(...)`. Since `cd79b80e`, that summary
  includes `would_hold_enforce`, `would_hold_enforce_reasons` and `would_hold_strict`. The adapter copies those
  three keys into `ap55_gate` only when the row recorded them, and never reconstructs them
  (`ap55_shadow_review` owns reconstruction).
- The writers on the vb-writers side are on orchestrator main: `2789b56d` and `e93edfdb`, with
  `scripts/autopilot/reproposal_rate.py` hooked in `autopilot.py`, `false_accept_record.py` and
  `score_false_accept.py`.
- No grading rule was added. Every new field is carried, and the tests assert that the grade and the reasons are
  unchanged.

## Conflicts
- **`autopilot_journal.py`, 2 merges.** All fields were kept on both sides. The support frame now carries
  `ap55_gate`, `eval_fence`, `eval_fence_enforcement`, `run_manifest`, then `**decision`
  (`promotion_rule` / `promotion_status` / `frontier_admission` / `promotion_committed`). `_ap55_gate` sits after
  the promotion helpers.
- **`test_autopilot_journal_adapter.py`.** `ORCH` keeps main's `EPYC_ORCH_ROOT` override, and `WRITER`
  (`VIDYA_ORCH_WRITER_ROOT`) defaults to `ORCH`.
- **`cli.py` `_FILE_SOURCES` and `test_ingest_sources.py` `BUILDERS`.** Resolved as the union of both sides.
- **`adapters/README.md`.**
  - Main's newer rows are kept.
  - The branch's wired SC83 row replaces the candidate row, which main had not changed since the merge base.
  - The re-proposal-rate row is added.
  - The AP-53 ledger row's "rate writer under review, unmerged" now says it landed.
  - The autopilot-journal row now documents the new fields.
- **`master-handoff-index.md`.** Main's side was taken, and no regen was committed.
- **`vidya-belief-substrate-program.md`.** This file auto-merged, but the result was wrong: it held a second,
  ticked VB-AP53-RATE box next to main's unticked filing box. The evidence was folded into the filing box and the
  duplicate removed. The SC83 body and the status table rows were changed from "not merged" to "landed".

## Tests
- `tests/vidya/`: 1391 passed, 82 skipped (pre-existing environment skips).
- With `EPYC_ORCH_ROOT` set to a `git archive` export of orchestrator main:
  - `test_autopilot_journal_adapter.py`: 22 passed, 0 skipped. This includes the real-writer end-to-end tests
    and the new `gate_summary`-fed `would_hold` path.
  - The four touched vidya test files: 78 passed.
- The live cross-repo tests for reproposal-rate and reviewer-fa ran against the shared orchestrator clone at
  `a1a0251a`.
- `scripts/handoffs/index_state.py --check` exited 1, with one problem: FRESHNESS. The master rollup is stale
  because VB-AP53-RATE is now ticked. Coverage and schema passed. The regen belongs to the index owner, so it was
  not committed here.

## Ingest
`cli.py ingest autopilot-reproposal-rate` and `ingest reviewer-fa` were dry-run. Both matched 0 units, because
neither producer file exists yet. Their triggers are the AutoPilot restart on orchestrator main and the first
decoy corpus. There was nothing to ingest.

## Closure-inflation audit
These boxes were ticked on the claim that the adapters had landed, or on evidence that included them, while the
root half was still unmerged:
1. **VB-AP53-RATE** (`vidya-belief-substrate-program.md`). The branch ticked a duplicate box "✅ 2026-09-16 …
   not merged". Premature. It is now ticked once, on main's filing box, dated 2026-09-17, with the landing
   recorded.
2. **SC83** (same file). Ticked on the branch with "Neither is merged yet". Premature. The evidence is re-dated to
   the 2026-09-17 landing.
3. **AP-55** (`autopilot-continuous-optimization.md`). Ticked 2026-09-17 on orchestrator `a1a0251a`, while its
   (b)+(c) evidence named root `febf56cd` as "under review, unmerged". The orchestrator gate did land, but the
   vidya carry had not. A dated note now points to this landing, and the box is unchanged.
4. **AP-54** (same file). Ticked 2026-09-17. The fence evidence lists `eval_fence_enforcement` in the journal
   tuple, while the root adapter carry `7280da63` was unlanded. A dated note was added, and the box is unchanged.

**Not premature:** VB-MHS-OPS. Its adapter `mhs_guard.py` is on root main (`55527247`).

## Cleanup
See the report. The three old worktrees and branches were removed after `git cherry` showed them fully merged.
