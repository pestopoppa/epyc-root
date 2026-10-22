# 2026-10-22 Producer-side belief emits (3c4ca599)

No inference; no process started, killed or armed. Every edited job was idle (poller child = `sleep 45` only) when edited; job scripts replaced atomically.

| item | change | ref | tests |
|---|---|---|---|
| HIL-15a | `hil15a_flagon_run.py --served-model --belief-sidecar` -> `hil15a_auc.write_belief_measurements` after auc_table.json; failure recorded in manifest `auc_sidecar`, never fatal. Job passes `--served-model "$MODEL" --belief-sidecar --epyc-root`. | orch branch `hil15a-flagon-fix-20261022` 57d5c004 -> 51bcc77b; `hil15a_job.sh` DRV pin comment repinned | tests/unit/test_hil15a_flagon_run.py 12 passed |
| HS-PROF-1 | job RESEARCH -> `hsprof1-belief-write` @ `1d6359490edead7a7e0b8992201752d33592c937`; judge run_phase gets EPYC_ROOT | research branches `hsprof1-belief-write`, `vb-write-akpl-3c4ca599` pushed | `bash -n` ok |
| RTE-PFX-2 | recipe records window/role in RUN_HEADER+probe.json, calls capture after rc=0, skips -1 trials | orch branch `lane/qb2-rtepfx2-20261021` e6f3c8e4 | tests/unit/test_rte_pfx2_role_recipe.py 10 passed |
| Oolong | records carry run_id, gguf_sha256, sampling, prompt_tokens (+source) | research main 6ddc19d4b | 14 passed (research .venv) |
| D-RI-PREVIEW | adapter called after complete non-mock result | orch main 8eaec813 | tests/unit/test_run_repl_preview.py 8 passed |
| protocol_id bug | six carriers store empty protocol_id; legacy ids re-map on projection | this commit | carriers/hil15a/repl_preview/oolong/yarn/rte/hs_prof1/ibench: 140 passed |

Ledger check: 0 rows for the six source kinds in `.vidya/ledger.jsonl` (nothing rewritten).

## Notes
- `/workspace` is 678 commits behind origin/main, so it lacks the adapters; HIL-15a, HS-PROF-1 and the recipes fall back to the pinned root worktree `/mnt/raid0/llm/worktrees/root-pbe-3c4ca599` (keep it) until the shared clone is fast-forwarded.
- HIL-15a CIs for per-feature-set AUC rows: NOT added. The adapter requires `ci95_task_resampled == null` for feature-set rows and a CI there needs an extra bootstrap with its own RNG stream (so delta CIs stay unchanged); adapter + producer + tests, not small. Rows keep CI null.
- Poller 160622 is gone; the HS-PROF-1 reader poller is 881865 (idle at edit time).

## YaRN gate emit (runner not edited)
Call, once per aggregation pass: `yarn_gate_agg.write_belief_measurements(run_dir, run_id=..., producer="yarn-gate-runner", records=[{"record_path": <durable json holding the record>, "decision": <dict>}, ...])` (root `scripts/vidya/adapters/yarn_gate_agg.py`, add `scripts/vidya` to sys.path).
Mismatches versus `epyc.yarn_gate_decision.v1` (see the module docstring): `helmet_judged_cell.score_cell` emits schema `epyc.yarn_helmet_judged_cell.v1` and no `record_kind`, `mock`, `comparison`, `arm_role`, `suite`, `model_pin`, `bin`, `zone`, `source_pins`, `judged`, `judge_pin`, `judge_validation`, `metric`, `value`, `n_units`, `unit`, `n_unjudged`; its `prompt_n` has only count/min/max (needs `source` and `median`). `agg_scoring.net_paired_mcnemar` emits verdict FAIL/NOT-FAIL with n_pairs, b/c, p_one_sided, alpha but no `schema`, `record_kind:"verdict"`, `comparison`, `arm_role` (A1_vs_A0|CY2_vs_CN), `rule_id`, `mean_score_diff_a1_minus_a0`, `a0_record_sha256`, `a1_record_sha256`, `prompt_n`/`bin`/`zone`/pins. Oolong cells from `oolong_by_real_length` lack `nominal_length`, `source_pins`, `model_pin`. `comparable_to_published` must be false on every record; `zone` `mixed` is refused.
