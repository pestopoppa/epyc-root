# R24-8 pool health alarms — implementation evidence capsule

Implementation-only publication. Research implementation commit: `991033729e9479249909ea3ae5ddc5d2e18772c2`. ROOT implementation/capsule commit: `844689e0a75dbc9d5b5f0a9c701ebb4af9b65024`; current-main integration merge: `1d2e0a5a1955228308d8745e3e663267b96230d2`. The source and existing `/loop` surface are implemented, but the original R24-8 handoff remains OPEN: the requested run-5–9 retrodiction is not fully executable because August per-run native outcome rows for runs 5–8 were not found. This capsule claims no quota completion and does not authorize a checkbox change.

## Code and visibility

- Research commit: `991033729e9479249909ea3ae5ddc5d2e18772c2` (`R24-8: add observe-only pool alarms`). It adds native `comparison: null` to current `Outcome.to_attempt()` records when no native `Comparison` was captured; derives configurable observe-only alarms; passes active evidence to the next planner context; and tests status/effect/keep direction.
- ROOT changes in this publication add a live, escaped operator-attention renderer to the existing `/loop` page and two current-writer fixtures. The existing `/api/loop` pass-through carries the producer body. No route, registry, freshness, health, or new-page contract changed.
- Existing ROOT parent-owned notes for HIL-15 and P17.BT-5c were included unchanged. Their task states remain as written; no other team's lane was touched.

## Semantics preserved

- `Comparison.effect` is the reducer's normalized candidate/anchor rate minus one; negative means worse. Missing, malformed, Boolean, and non-finite values remain unknown.
- `kept` alone is a landed keep. `keep_candidate` is not a keep.
- Explicit current `comparison: null` counts as no recorded native Comparison. Missing legacy keys and malformed values break the known suffix/window as UNKNOWN; they are not backfilled.
- `stopped_mid_formation` is excluded from the no-measurement streak. Explicit nulls are skipped in measured-only windows.
- Warnings default to 10 and are configurable operational attention only. They do not alter grading, promotion, keep decisions, pool limits, or stop behavior. Planner text appears only when active. The UI says “no recorded native Comparison,” never GPU idle or physical absence.

## Retrodiction

Machine-readable replay is in `retrodiction-projection.json`; exact native `loop_run.v1` inputs for 9 and 18 are copied verbatim under `source-inputs/` and retain their original SHA-256.

- Run 9 has 10 outcome rows, all missing `comparison`. The conservative current reader reports UNKNOWN/insufficient data and no alarm; it does not retrofit nulls. The historical summary says 0/10 measurements in 149 min, but its per-row source lacks the explicit marker.
- Run 18 has 188 outcomes: 138 comparison mappings and 50 missing keys. Prefix replay first crosses both measured alarms at outcome 68. Later legacy UNKNOWN rows break the ending suffix; the final-row live projection has one known measured row and does not claim a persistent alarm.
- Historical Research writer commits `6408f68521501b05068be7f1efe51164d247196e` and `1e01328447c201d74faa314e08284d6b8a7c42d6` show `Outcome.to_attempt()` emitted the `comparison` key only inside `if self.comparison is not None`. This establishes how that writer schema represented null comparisons. The saved run 9 artifact does not pin the emitting source commit, so this schema evidence is recorded without retrofilling or changing the conservative reader.
- The handoff/progress sources only group nine real iterations and zero measurements across runs 5–9; they do not partition the observations by run. The expected `/mnt/raid0/llm/autokernel/loop-memory/run5..run8/loop-run.json` files are absent. Alternate `state-run5..8` records found in the September `ak-ds41-cpu-decode-20260923` campaign are later, `legacy-serial`, have `iterations_done=0` and empty recent rows, and are excluded as unrelated. Run-5–8 per-run replay remains UNKNOWN and OPEN.

Original grouped historical sources:

- `/workspace/progress/2026-08/2026-08-28.md` SHA-256 `124a7cee3ebeeb93848e63e471bde4ea983d4cd777fc1fc53effbbf6fff9c0c0`
- `/workspace/progress/2026-08/2026-08-29.md` SHA-256 `30de69f1ab7ec34b209a52f6de1681bd5ca76b8bbd949570a84e1aa1b9513e45`

## Controls and GitNexus

- Research controls: 51 passed in `research-controls.log` (`test_status`, `OutcomeAttempt`, `ContextBundle`).
- ROOT `/loop` controls: 79 passed in `root-render-controls.log` (`tests/test_dashboard_loop_surface.py`). The suite covers current producer fixture through API pass-through, active/inactive/legacy-unknown rendering, and dynamic text escaping.
- `r6-controls.log` records the one matched logical/SMT CPU pair lock, task affinity, `OMP_NUM_THREADS=1`, 8 GiB address-space limit, timeout, captured test PID/birth/RSS/VSZ, and confirmed process absence. No model or inference was run.
- Research GitNexus was current at base `3864923d9dec3d72c2f168cff95faa168c3c2762`; upstream impact risk was LOW for `status.write` (0), `Outcome.to_attempt` (0), `actors.render_context` (6), and `run.build_context` (0). The ROOT lane is not GitNexus-indexed; the change is in HTML/JS in the existing page.

See `SHA256SUMS.txt` for capsule and source hashes. The R24-8 source/handoff row, index, belief source table, and semantic checkbox are not changed here; Main owns that final reconciliation.
