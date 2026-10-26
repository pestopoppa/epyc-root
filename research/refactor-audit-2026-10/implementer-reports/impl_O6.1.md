O6 stage 1 report. All seven findings are done, one commit each, on branch `wt/o6` in `/workspace/wt/o6` (cut from `16ec725a`, not pushed). Every bug fix has a regression test that fails on the base code and passes now. The 6 test failures in the combined run all fail the same way in the unmodified base checkout.

## Per finding

**A5-M1 — done, `1626f5ce`, net −613**
- **What:** deleted three scripts that killed processes by name pattern or port:
  - `scripts/session/start_orchestrator_test.sh`: a stale fork of the hardened epyc-root copy; it ran `pkill -9 -f llama-server` and `pkill -9 -f uvicorn`.
  - `scripts/benchmark/kill_seeding.sh`: it killed every `pgrep -f` match with `kill -9`, including all `multiprocessing.spawn` workers on the host, and ran `fuser -k 8000/tcp`.
  - `scripts/server/start_servers.sh`: its `--stop` ran `pkill -f llama-server`, and it told users to run cmake inside the frozen tree.
- **References:** grep across all three repos found no live references. The only extra hit is epyc-root `scripts/ci/pip02_selected_library_capture.py`, which reads files at a pinned past commit, so deleting at HEAD is safe.
- **Also:** the log hint in `src/inference/model_server.py` now says `python3 scripts/server/orchestrator_stack.py start`.
- **Test added:** `tests/unit/test_scripts_no_name_pattern_kill.py`. It fails on the base tree with 5 hits; it does not catch a pgrep-then-kill loop spread over several lines.
- **Check:** the epyc-root `scripts/session/tests/test_start_orchestrator_test.sh` still passes 15/15.

**A5-06 — done, `26462e4a`, net +41**
- **What:** `scripts/graph_router/reembed_episodic_store.py` used to launch the v9 binary at `llama.cpp/build/bin/llama-server` with all output sent to DEVNULL. It now:
  - launches `kernel_paths.server_binary("cpu")`;
  - sets `LD_LIBRARY_PATH` from `backend_ld_library_path("cpu")` through `compose_ld_library_path`, only when that list is non-empty (an empty list would add a leading `:`);
  - writes output to `<log_dir>/reembed_<port>.log`.
- **Beyond the brief:** I dropped `--log-disable` so the log actually records load errors, and added an early-exit check during the health wait.
- **Extra bug fixed:** the launch loop is now inside the `try`, so a failed launch also stops the servers this script already spawned (they used to leak).
- **Test added:** in `tests/unit/test_reembed_episodic_store.py`.

**A5-07 — done, `8a26a07d`, net +13**
- **What:** removed the v8 pins `LANE_BINARY_VERSION`/`COMMIT` (`10107`/`67a433bf4`) and the duplicate version/commit/freeze lines in `orchestration/gpu_shadow_lane_tenancy.yaml`. Those pins made the lane's preflight block every v9 or v10 binary.
- **Preflight now:** it blocks only when the binary prints no `version: N (sha)` line. It records the identity in the report's infos and in a new attestation field, `binary_identity`.
- **Stage0:** the `slot.binary_pin` check is replaced by `slot.binary_from_store`, which fails if the slot's binary directory is not the store's gpu backend. `LaneSlot` no longer has `binary_version`/`binary_commit` fields.
- **Docs:** two lines in `docs/gpu-shadow-lane.md` updated.
- **Deliberately unchanged:** `orchestration/gpu_shadow_lane_np_ceiling.yaml` keeps its line saying the np grid was measured on build 10107. That is measurement provenance, and the file is also hash-pinned (`CAPACITY_ARTIFACT_PIN` in `tests/fixtures/ni63_capacity_child/source_clone.py`). So the no-pin guard test covers `scripts/server/gpu_shadow_lane*.py` plus the tenancy yaml only, which is narrower than the verifier's suggested scope.
- **Tests added:** two in `tests/unit/test_gpu_shadow_lane_preflight.py` (v10 identity recorded, missing version blocks), the no-pin guard test, and an off-store smoke test in `tests/unit/test_gpu_shadow_lane_p2.py`. With a 10303 binary, the old code gave 14 preflight test failures. `gpu_shadow_lane_stage0.py smoke` runs clean (rc 0).

**A5-04 — done, `c6c005e5`, net +11 (script −40, test +51)**
- **What:** in `scripts/benchmark/seed_specialist_routing.py`, both `build_diagnostic` call sites now use one `_diagnostic_kwargs(rr, prompt_info, config_key)` helper. The retry copy was missing `tool_chains`.
- **Test added:** in `tests/unit/test_seed_specialist_routing_main_and_retry.py`, using a stubbed `pop_retries` and `evaluate_question_3way` as the verifier described. It also asserts that the first-pass and retry diagnostics have the same keys.
- **Not touched:** the v2 fork, which also lacks `tool_output_tokens`. A5-05 deletes that file.

**A5-12 — done, `0afa7c21`, net +41**
- **What:** all five swallowed excepts in `scripts/server/stack_log_banner.py` now print one `[launch-banner] ...` line to stderr, and to the server log where possible.
- **Stale sidecar:** a failed sidecar rewrite now deletes the previous launch's `<port>.json` and the temp file, so `serving_calls` reports identity `absent` instead of the old launch. A failure appending to `launches.jsonl` after the rewrite succeeded keeps the new sidecar.
- **Pin updated:** the `SOURCE_PINS` entry for this file in `tests/fixtures/ni63_capacity_child/source_clone.py`.
- **Test added:** in `tests/unit/test_stack_log_banner.py`. I injected the failure by patching `os.replace` to raise ENOSPC, because the brief's chmod read-only approach does not fail when running as root, and a read-only directory would block the unlink anyway.

**A5-22 — done, `de0000b8`, net +15**
- **What:** in `scripts/server/preflight_gate.py`, a new `_topology_hash_or_cause` falls back to the full-topology hash only when the matrix is missing. A corrupt matrix returns `matrix unreadable: <exc>`, and `check_topology_hashes` puts that cause in `result["error"]` instead of reporting "topology hash drift".
- **Kept compatible:** `_live_topology_hash()` still returns `str | None`, because epyc-root `scripts/coordination/derive_topology_hash.py` and `scripts/server/embedder_placement_capture.py` depend on that.
- **Deviation from the proposal:** the import `except` stays broad but now carries the cause text. Narrowing it to `ImportError` would let a `KernelPathError` raised while importing `stack_numa` crash the gate before it writes an attestation.
- **Tests:** one added in `tests/test_preflight_gate.py`; two existing monkeypatches updated.

**A5-M2 — done, `c6c12d3c`, net −28**
- **What:** `scripts/lib/env.sh`, `src/vision/analyzers/vl_describe.py` and `src/services/lightonocr_llama_server.py` no longer fall back to `llama.cpp/build*` binaries when the store's `llama-mtmd-cli` fails to run. Each keeps the store path and reports the failure (stderr in env.sh, `logger.error` in Python).
- **Why removing the fallback is safe:** epyc-root `verify_kernel_store.sh` already fails if `llama-mtmd-cli` is missing from `production/cpu`.
- **env.sh:** also guards an unset `LLAMA_CPP_BIN`, which previously failed under `set -u`.
- **Launch env:** `mtmd_subprocess_env` moved to `src/services/mtmd_probe.py`. `vl_describe`'s CLI run now uses it, so it launches with the same `LD_LIBRARY_PATH` the probe checked (it used to pass no env). This also sets `OMP_NUM_THREADS` to the thread count there.
- **Not done:** I did not add `kernel_paths.tool_binary()`. The config default already resolves to the store path, so it would be unused abstraction, and it would mean another `SOURCE_PINS` change.
- **Check:** `git grep 'build/bin/llama-mtmd-cli' -- scripts src` returns nothing.
- **Tests:** four rewritten or added in `tests/unit/test_mtmd_probe.py` and `tests/unit/test_lightonocr_llama_server.py`.

## Tests run
- Each finding: `cd /workspace/wt/o6 && CI=true ORCHESTRATOR_MOCK_MODE=1 /workspace/repos/epyc-orchestrator/.venv/bin/python -m pytest -q -p no:cacheprovider -o addopts="" -n 2 <files>`, with the new test confirmed failing before the fix.
- Final combined run over 39 files (all touched tests plus the lane, seeding, serving_calls, dispatch_log, embedder_placement, vision and NI63 pin tests): **785 passed, 1 skipped, 3 failed, 3 errors**. All six fail the same way in the unmodified base checkout `/workspace/repos/epyc-orchestrator` (`16ec725a`):
  - `tests/test_preflight_gate.py::test_role_scoped_require_servers_uses_primary_role_ports` and `::test_role_scoped_live_only_ports_skip_nonlive_configured_ports`: port lists differ from the test's expectations.
  - `tests/unit/test_orchestrator_stack_import_is_argv_safe.py` (4 tests): "source differs from accepted APP pin: `scripts/server/orchestrator_stack.py`". That is base drift in a file I did not touch; all other `SOURCE_PINS` entries match in my worktree, including the updated `stack_log_banner.py`. These 4 are also in the 2026-10-07 baseline list.
- ruff on the changed Python files: 7 findings, all identical in base (unused imports in `seed_specialist_routing.py` and `gpu_shadow_lane_stage0.py`, an E741 in `test_stack_log_banner.py`). None introduced. `bash -n scripts/lib/env.sh` passes; shellcheck is not installed here.

## For the integrator
- **Other repos:** nothing edited outside `/workspace/wt/o6`. Suggested for epyc-root (not done, read-only for me): add `scripts/graph_router/reembed_episodic_store.py` to the offender history in `docs/reference/kernel-freeze-runbook.md`, now fixed.
- **Interfaces changed:**
  - `LANE_BINARY_VERSION`/`LANE_BINARY_COMMIT` and `LaneSlot.binary_version`/`binary_commit` are gone; there are no other users in any of the three repos.
  - The stage0 check name changed from `slot.binary_pin` to `slot.binary_from_store`.
  - `_mtmd_subprocess_env` moved from lightonocr to `src.services.mtmd_probe.mtmd_subprocess_env`.
- **Files outside the stated areas that I touched:** `src/inference/model_server.py` (one log string), `docs/gpu-shadow-lane.md` (two lines), and the NI63 `source_clone.py` pin.
- **Follow-ups:**
  - A5-05 should delete `seed_specialist_routing_v2.py` and drop its parametrisation.
  - Someone needs to re-pin `scripts/server/orchestrator_stack.py` in NI63 `SOURCE_PINS`; it is already drifted at base.
  - No kernel (llama.cpp) defects came up.