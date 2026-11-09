# 2026-11-09 apr2 stack-ready (phase 2, Autopilot hold)

Branches: root `apr2/stack-ready-20261109`, orchestrator `apr2/stack-ready-20261109` @ `70dbf5ea`.

## 1. Autopilot relaunch era (prepared, operator runs it)
`scripts/operator/ratify_autopilot_relaunch_era_20261109.sh`: appends one `autopilot_speed` era row after E20.
Required args (never defaulted): `--from`, `--kernel-name`, `--binary-version`, `--kernel-commit`, `--lineup-sha256`.
Instrument fields (`policy_version`, `execution_instrument_id`, `scoring_schedule_id`) carried from the latest
autopilot_speed row. Refuses: stale `--from`, unregistered kernel, existing uncommitted edits, staged files,
untyped operator. Exercised with `--dry-run`, `--apply --commit` and the re-run no-op on a COPY in the
scratchpad; `check_ratification_receipts.py` still 0 failing. The real `instrument_eras.yaml` was not touched.

## 2. Registry paths and ik_llama text (diff prepared, not applied)
Package `artifacts/analysis/stack-ready-kernel-store-paths-20261109/`. See the autopilot-program.md note for
consumer findings. Orchestrator `70dbf5ea` adds the inert `{llama_bin_dir}` placeholder.

## 3. RTG-DUR-1 (built default off, not regenerated)
See the routing-program.md RTG-DUR-1 note. Tests: `tests/unit/test_duration_baseline_freshness.py` (19) and
`tests/unit/test_registry_loader.py` (31), run with the repo venv python 3.11 plus system pytest
(`PYTHONPATH=/usr/lib/python3/dist-packages .venv python -m pytest`), because the venv has no pytest.

## Not verified
gitnexus reports "Repository not indexed" in the orchestrator worktree, so no impact analysis was run;
q_scorer.py and stack_change_pipeline.py edits are additive and default off. Their existing test files were not
run (brief: touched test files only).
