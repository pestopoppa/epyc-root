# 2026-10-22 Final producer-side belief emits (3c4ca599)

No inference; no process started, killed or armed. Pollers 1039426 and 1198715 had only a `sleep` child (checked via `pgrep -P` + `/proc/<child>/comm`) before the pin was touched and again after.

| item | change | ref | tests |
|---|---|---|---|
| VB-YARN-AGG-EMIT | new `scripts/benchmark/yarn_gate/decision_records.py`; `arm_runner.decide` -> `belief_emit` (FINAL only); `agg_scoring.oolong_by_real_length` splits mixed zones and carries `prompt_n`/`n_contexts`; `helmet_judged_cell.score_cell` emits judged cell records (+ `load_judge_validation`, `--emit-belief-dir`) | research branch `yarn-native-gate-runner-20261022` e5173d638 -> `46d26f626de0b339b95f7c4a5efc966f7f26d0cb`; `YG_RESEARCH_SHA` in `yarn_gate_lib.sh` repinned (atomic replace, pollers idle) | yarn_gate suite 86 passed (research .venv); new `test_decision_records.py` 4 (FINAL fixture -> 1 tuple, INTERIM -> 0, fixture sidecar projects 0 tuples on a real read, mock refused in a real call, zone split, judged cell) |
| EV-19 | `gold_self_check.py` report gains `pool_sha256`, `pool_rows`, `generated_at`; `--belief-out/--eval-era-row/--pool-id/--run-id/--epyc-root` call `ev19_gold_selfcheck.write_belief_measurements` after the report is written; refusal exits 3 | orch main `b0cf16ba` | `tests/unit/test_ev19_gold_self_check.py` 11 passed (orch .venv) |
| RUS-2 | `rus2_result.json` gains `generated_at`, `results_dir`, `input_digests` (per file bytes + sha256, same selection rule as `load`), `script`, `script_sha256`; `--belief-out` calls `rus2_probe.write_belief_measurements`; refusal exits 3 | research main `04d4c1788` | `scripts/analysis/test_rus2_trace_length_probe.py` 5 passed |

## YaRN record decisions
- One record per (suite, task, REAL-length bin, zone); a bin that straddles zones is split by zone, never `mixed`. Metrics: `mean_score`, `no_answer_rate` (lower_better). `attempted_rate` is omitted (always 1.0 for an ok result).
- `ruler` items are excluded with a reason (the schema has no ruler suite), as is any result without a measured `real_n`/`n_source`, mixed `n_source`, or non-uniform source pins. Exclusions are listed in `decision.json` `belief_emit.excluded`.
- Verdicts: paired native-zone items per (suite, task, bin), `rule_id` = plan `protocol_id`, mean diff / b / c / p / alpha from `net_paired_mcnemar`, `a0_record_sha256`/`a1_record_sha256` = digests of the durable `belief_records/*.mean_score.json` cell files. `protocol_id` is not passed to the writer (rows are OBSERVATIONs until a ratified protocol is cited).
- Judged HELMET cells need `--judge-pin-json` (the validated `judge_pin.json`: pin + 50-item agreement + `sheet_sha256`), a measured `--prompt-n-source` and `--comparison/--arm-role/--model-pin`; the judge used must match the validated pin's model + prompt sha256 or no record is emitted (reason recorded in `decision_excluded`). The native-gate and extension-arms plans score by substring/exact match, so their records are `judged: false`.
- Emit failure never blocks `decision.json` or the COMPLETE marker: it is recorded as `belief_emit.status == "error"`.

## Notes
- `tests/unit/test_epyc_root_resolution.py::test_lb1_producer_emit_call_writes_rows` (not mine) fails against the pinned root worktree because it has no `hil_lb1_loop_score` adapter; pre-existing, unrelated to these changes.
- The root worktree `root-pbe-3c4ca599` must stay until the shared root clone is fast-forwarded (jobs fall back to it).
