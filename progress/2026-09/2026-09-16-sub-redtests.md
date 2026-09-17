# 2026-09-16 — sub-redtests: triage and fix of pre-existing red tests

Zero-inference, zero-process-management subagent. Worktrees were created off `origin/main`. Nothing was pushed.

| Repo | Branch | Commit(s) |
|---|---|---|
| epyc-root | `sub/redtests-root-20260916` | `58bd58c8` |
| epyc-inference-research | `sub/redtests-research-20260916` | `289b2e83`, `7d6dfb1e` |
| epyc-orchestrator | `sub/redtests-orch-20260916` | `0a2db256` |

All three branches merge cleanly into the current `origin/main` (root was re-checked after main moved).

## Counts (before → after)

| Suite | Runner | Before | After |
|---|---|---|---|
| root `tests/test_dashboard_*.py` | system python3 | 57 failed / 729 passed | **0 failed** / 775 passed |
| root `tests/` (whole suite) | system python3 | collection aborted (2 errors) | 10 failed / 3490 passed (the 10 are outside the dashboard files; see below) |
| research `scripts/benchmark` + `scripts/lib` | `uv run --frozen --with pytest --with pyyaml` (Makefile) | 41 failed + 1 error | **2 failed** (on purpose) / 2056 passed |
| research autokernel loop suites | python3 | 30 failed + 30 errors | not touched (owned by the autokernel session) |
| orchestrator `tests/unit` | orchestrator `.venv` with `-n 8` | 10 failed (the reported 2, plus 8 caused by a live bench) | **0 failed** / 13139 passed |

Note: the reviewers counted 39 root dashboard failures. 57 failed on the snapshot I ran. The extra failures come from the host's `current-serial-run.json` pointer, which the autokernel serial run started writing today.

## Classification

Classes: a = test stale versus the code · b = code bug · c = environment dependence · d = code only on a lane branch · e = owned by autokernel

| Tests | Class | Root cause | Fix |
|---|---|---|---|
| root champion_headline (15), knowledge_card (11) | a+c | Since `028d7c3d`, the canonical champion and knowledge readers use `DEFAULT_STORE_ROOT` and ignore `AUTOKERNEL_LOOP_STORE_ROOT`. Since `a1cb667f`, the live status follows the host's current-run pointer. Both made the tests read the real store. | The test seam patches `DEFAULT_STORE_ROOT` and sets the pointer environment variable to a missing path. |
| root champion_headline `no_production_sha…` | b | `a0f3daee` put 19 40-hex keep commits as literals in `loop_status.py`, which the reader's no-40-hex guard forbids. | Moved them to `dashboard/data/autokernel-legacy-deepseek-keep-commits.v1.json`, loaded strictly. |
| root autokernel_v26 (7) | b | `a7a88f4a` made the shared validator require the v27-only `backup_critic_*` actor keys, so every v26 contract returned None. | Added a per-schema flag, `backup_critic_required` (v27 = True). |
| root autokernel_live (1) | b | `2e1dd002` silently reverted the `producer_idle` fix from `24b3a480`, so an idle unlaunched deployment alarmed global health. | Restored the `24b3a480` rule. |
| root runtime_js (4), campaign_status (1) | c+a | Live pointer leak. `7c1d96cb` removed the `champ`/`champ-scope`/`tiles` elements but did not update the tests. | `tests/conftest.py` autouse pointer seam. Assertions retargeted to `champion-capabilities` and `accumulator`. |
| root dom_contract (1) | a | The regex matched `getElementById("serial-"+op)` as the id `serial-`. | The regex now requires the literal to be the whole argument. |
| root experimental_runtime (1) | a | `91da1172` added the separate `operator_gates` producer to every payload. | Excluded that key from the no-"champion" scan, and the test now asserts the block is present. |
| root hooks/pytest_worker_scan, e8_reseed_prepare (collection errors) | a / c | Sibling import of `shell_scan`; `httpx` missing from system python. | Added a `sys.path` entry; `importorskip`. |
| research convert_sr_to_patch (20), capture_contract_guard (2) | c | The converter sits in an untracked artifact directory that exists only in the canonical checkout. | Skip with a reason. The runner and judge guard is still checked. |
| research cpu_prefill_v8 (1) | a | The test found the root checkout by a path relative to its own location. | Uses the runner's configured absolute path. |
| research fg4b_a4 importer (5) | c | The live v8 `llama-bench` and the recipe hashes have moved on (v9). | Fixture pins the three live digests. A new test keeps the drift refusal's signal. |
| research fg4b_a4 reanchor (6, surfaced mid-run) | c | The tests failed in any checkout with uncommitted work. | Fixture reports a clean status. The dirty-refusal test still forces a dirty status. |
| research glm52 direct runner (4) | c | The experimental HIP binary and the GLM-5.2 model are absent from the host. | Stub binary and a stub 6-shard directory. |
| research laguna runner (4) | c | Laguna model removed; question files untracked. | Stub model; skip when the question files are absent. |
| research stage1 planner (1) | c | The test ran `--version` on the absent experimental binary. | Stub binary. |
| research longcot (4) | c | `datasets` cannot be imported, and the adapter fails open to 0 rows. | `pytest.skip`. |
| research memento_sft (collection) | c | `pyarrow` is in the optional `benchmark` extra. | `importorskip`. |
| research dflash2_followups runner sha, p3_bakeoff real manifest | b (pin drift) | `da06b371` (2026-08-26) edited `v7_quality_gate_runner.py` after the DFlash2 carrier (`6dea92dd`, the `baf36757` bytes) and the P3 manifest (`79721927`, the `b9ad1008` bytes) were sealed. P3 also needs the untracked `critic_tasks_v1.json`. | **Left red.** The operator or owner must choose between re-sealing and restoring; re-sealing a prospective measurement carrier crosses the human-only trust boundary. |
| orch config_consolidation, dashboard_helpers (embedder) | c | Both read the live runtime-facts lineup (sub-full: ingest on :8185 only; embedder missing from the selected servers). | `ORCHESTRATOR_IGNORE_RUNTIME_STACK_FACTS` seam; pinned manifest path and mode. |
| orch model_server_extended (5), stack_reload parser (3) | c | Refused because another session's CPU bench held cores. | Quiet-path stubs for `api_enforce_placement` and `guard_against_running_bench`. |
| research autokernel loop (30 failed + 30 errors) | e | See the handover below. | Report only. |

**Class (d): none.** The lane `lane/autokernel-unified-20260908` has no commits that `origin/main` lacks; its HEAD is an ancestor. Its only uncommitted dashboard work is unrelated to these failures: the `/cockpit` page (`dashboard/static/cockpit.html`, `server.py` route, `registry.json`) and `handoffs.html`. Its uncommitted `loop_status.py` diff already landed as `a1cb667f`. The `codex/dashboard-v27-*` branches (2026-08-21) are stale and none of these tests needs them.

## Out-of-scope root failures (not fixed, all class c)

The remaining root failures depend on where the checkout sits or on host state:

- `coordination/test_worktree_isolation_phase2`: expects the mainC and mainD worktrees on disk.
- `test_heavy_wrap` end-to-end.
- `test_e8_quality_*` (3): need `httpx` in the interpreter and a clean root HEAD.
- `test_measurement_trust_boundary_writer_lock`: needs the `e8-clean-integration-20260728` worktree.
- `test_ratify_pbench4_fg4b_*` (2): need the canonical root path.
- `test_session_bus` audit-shadow (1).

## Handover — autokernel session (class e, report only)

Research `scripts/kernel_rnd/autokernel/loop`, run under python3:

- `test_serial_run.py` (5): `serial_scheduling.SerialSchedulingRefused: … issued selection awaits settlement`, plus `:791 assert False` and a `:758` store-path equality failure. This is the settlement cluster.
- `test_existing_cpu_run.py`, `test_existing_gpu_serving_run.py` (4), `test_matched_serving*.py` (3), `test_campaign_command_v2.py` (2: `assert 1 is None`), `test_seed.py` (2: prompt text missing `'do NOT re-measure'` / `'5/5 positive'`).
- `test_serial_roster.py` (3), `test_shared_history.py` (2), `test_runtime_progress.py`, `test_runtime_keep_source_continuity.py`, `test_cpu_interference.py`, `test_cpu_screen_scheduling.py`, `test_direct_gpu_control.py`, `test_loop_cpu_profile.py` (2: `BenchOutputError`, row missing `samples_ts`/`n_threads`/`build_commit`), `test_native_final_trial.py`, `test_validation_semantic_adapter.py`.
- ERRORS: `test_native_server_t0_witness.py` (12), `test_validation_final_receipt.py` (15), `test_feed_root_projection.py` (3). Of the errors, 13 show `ProducerSourceRefused: original raw server source has missing or unknown fields`. One references the missing `/mnt/raid0/llm/worktrees/mains/autokernel-consumers-root-20260909/tests/vidya/test_autokernel_unified_arm.py`.
- Under the uv (py3.14, no extras) environment the loop suites show 75 failed and 125 errors, most of them import or environment related.

## Integration

Agent `sub-int-redtests`: merged the three reviewed branches with `--no-ff` in fresh detached worktrees, and pushed each one through `serialized_push.py` (lock `push`). Before merging I checked that none of the branches was already in origin/main. Root, orchestrator and research origin/main all moved while I held the lock, so I redid each of those merges on the new tip and re-ran the tests before pushing.

| Repo | Branch | Pushed merge | Tests |
|---|---|---|---|
| epyc-root | `sub/redtests-root-20260916` @58bd58c8 | `6df6d793` | `tests/test_dashboard_*.py`: 776 passed, 55 skipped, 0 failed (on both tips). `index_state.py`: rollup not stale, so nothing to commit. `--check` 0 problems. cite-check rc 0 (2579 citations: 2143 unknown, 436 record) |
| epyc-orchestrator | `sub/redtests-orch-20260916` @0a2db256 | `3a7e8081` | `tests/unit -n 8` (repo `.venv`): 13139 passed, 82 skipped, 6 xfailed, 0 failed. After origin moved (a `launch_manifest.yaml`-only commit), the 10 unit files that reference the manifest: 415 passed |
| epyc-inference-research | `sub/redtests-research-20260916` @7d6dfb1e | `8eca61d5` | `scripts/benchmark scripts/lib` (uv runner): 2 failed, 2062 passed, 76 skipped. Both failures are the expected sealed-pin drift: `test_dflash2_followups::test_exact_runner_bytes_are_unchanged` and `test_p3_bakeoff::test_real_manifest_verifies` |

Reviewer follow-up: `longcot_mini_adapter._ensure_loaded` now **fails closed**. If the data is present but `datasets` cannot be imported, it raises `RuntimeError` instead of silently loading 0 rows. Commit `238d6503` on `sub/longcot-failclosed-20260916` is pushed to research main and the branch is pushed. New test `test_missing_datasets_package_fails_closed`. The longcot adapter, stack-runner and scorer tests give 38 passed, 4 skipped under uv (no datasets) and 42 passed with `--with datasets`.

Minor: `tests/test_longcot_mini_adapter.py` has an unused `import os` (ruff F401) that was already there before this change; I left it alone. All three worktrees were removed with a plain `git worktree remove`.
