O3 report (worktree `/workspace/wt/o3`, branch `wt/o3`): all 15 findings are done, in 13 commits. The worktree is clean, no stray scratch tests, nothing pushed.

On the relayed question "was this the cloud Claude session?": yes. This package ran in an ephemeral cloud container, not on the operator's host; `/mnt/raid0` does not exist here.

## Per finding
Net LOC is source / tests. Source counts include the one-line pin edits in `tests/fixtures/ni63_capacity_child/source_clone.py`.

**Done by the earlier implementer.** I re-checked these and their tests pass:
- **A3-01 + A1-03** — done, `b1f08459`. The stack-priors parse is cached on (inode, mtime_ns, size). Net -16 / +26.
- **A3-19** — done, `b3f5b483`. A failed `chat_template_kwargs` registry load now warns and backs off. Net +12 / +36.
- **A3-02** — done, `b14658e3`. `compile_stack_priors` fails closed when `scripts.server` does not import. Net +1 / +18.
- **A3-07** — done, `6a260c54`. Registry-derived Settings defaults are now factories, and `reset_config()` resets the caches. Net +13 / +37.
- **A3-08** — done, `bad6e18d`. `get_instance_regions` logs and retries instead of caching `{}`. Net +14 / +20.

**Done this session:**
- **A3-09** — done, `38346806`. I finished and committed the uncommitted partial attempt. The shadow worker is now one plain daemon thread fed by a `SimpleQueue`; the private-CPython `ThreadPoolExecutor` override is gone. I added an `except` so one bad task cannot kill the single worker.
  - Probe: interpreter exit took 5.85 s on base with a 3 s call in flight, 0.05 s now.
  - Test: `test_in_flight_shadow_call_does_not_hold_interpreter_exit` (subprocess, asserts exit < 1.5 s).
  - Net -58 / +9.
- **A3-M1** — done, `d552f224`. A scalar like `ORCHESTRATOR_REPL=1`, `ORCHESTRATOR_CHAT=1` or `ORCHESTRATOR_SERVER=1` no longer crashes `get_config()`.
  - The outer Settings model reads raw env strings. A JSON object still overrides a section; anything else is ignored with a warning.
  - `features.py` and `docs/chapters/01-runtime-environment.md` now point at `ORCHESTRATOR_FEATURE_REPL`.
  - Tests: `test_scalar_section_env_does_not_crash_config` (every section × `1`/`true`/`on`) and `test_json_section_env_still_overrides`.
  - Net +23 / +25.
- **A3-04** — done, `004e3f44`. Both loaders now build `TimeoutsConfig` by walking its dataclass fields.
  - Added `architect_critic` to `TimeoutsSettings`.
  - The env fallback now uses the dataclass's registry-backed defaults, so `default_request` is 600 on both paths (it was 120 in `_load_from_env`).
  - I did not apply the proposed `worker_explore` change. `worker_explore` is a deliberate alias of `worker_general`: `Role.from_string` maps it there and an existing test pins it.
  - Tests: per-field env override on both loaders, plus `default_request` parity.
  - Net -78 / +24.
- **A3-06** — done, `90e5506c`.
  - `validation.py` now defaults to the `__file__`-anchored `DEFAULT_LEAN_REGISTRY` instead of a CWD-relative path, and logs a WARNING when the registry is missing.
  - `RegistryLoader`, when config is unavailable, now falls back to the lean registry instead of the research master. I removed the now-unused `DEFAULT_REGISTRY_PATH` re-export; nothing in O or R imports it.
  - Tests: loading from `chdir(tmp)`, the missing-registry warning, and the loader fallback.
  - Net +1 / +36.
- **A3-15** — done, `c97002c7`.
  - `ocr_image` gains a `timeout` parameter, and `page_timeout` is passed through to it.
  - Each page is rendered under the semaphore, so at most `max_concurrent` bitmaps are alive.
  - The PDF closes in a `finally`.
  - Side effect: a render error is now a per-page failure instead of aborting the whole PDF.
  - New test file `tests/unit/test_document_client_partial_success.py` uses a fake `pypdfium2`, which is not installed here.
  - Net -6 / +86.
- **A3-05** — done, `b4b1a911`. The two boolean recursion guards and the `recursive_guard` diagnostic are gone; one double-checked `RLock` serializes first loads.
  - The `yaml`, `copy` and `model_descriptors` imports moved to module level.
  - Test: `test_concurrent_first_access_does_not_cache_a_fallback` returned -1 before the fix and the registry value after.
  - Net -15 / +32.
- **A3-16 + A4-08** — done, `d3dd210f`. Same root cause, fixed once.
  - The `src/__init__.py` finder now maps all 16 aliases: the 14 unmitigated shims plus `inference_lock` and `inference_tap`. It also restores the target's `__spec__`, so an alias import no longer renames or re-specs the canonical module.
  - Tests: per-alias identity / `__name__` / `__spec__` checks (15 failed before the fix), and a 24-thread first-import stress test over all aliases.
  - Net +13 / +72.
  - **I kept the shim files on disk and did not codemod importers.** epyc-root capture scripts list these file paths in their copy closures: `scripts/ci/ni08_run_hosted_capture.py`, `w4_native_capture.py`, `s49_mtmd_probe_capture.py`, and `pip02`, which has hash pins. The shim bodies never run now. Deleting the files and codemodding importers is a follow-up once those closures drop them.
  - `python -m src.model_server` used to be a silent no-op; it now raises. I changed the usage text in `src/inference/model_server.py` to `python -m src.inference.model_server`.
- **A3-M2** — done, `c270cac2`.
  - `scripts/lib/env.sh` now self-locates the project root and honours an inherited `ORCHESTRATOR_PATHS_PROJECT_ROOT` only if that root holds `orchestration/model_registry.yaml`.
  - `models._get_default_project_root` warns once per root that lacks the registry.
  - Tests: `env.sh` with no inherited root or a foreign one resolves the repo registry; `PathsConfig` logs the warning.
  - Net +18 / +23.

## Tests run
All runs used `cd /workspace/wt/o3 && CI=true ORCHESTRATOR_MOCK_MODE=1 /workspace/repos/epyc-orchestrator/.venv/bin/python -m pytest -q -p no:cacheprovider -o addopts="" -n 2 <files>`.

- **Final combined run: 535 passed, 2 failed, 7 skipped.** It covered `test_config`, `test_config_validation`, `test_config_consolidation`, `test_conversation_shadow`, `test_cpu_region_lock`, `test_document_client_partial_success`, `test_inference_lock_concurrent_import` (with `-k "not reproducer_catches_the_pre_fix_shim"`), `test_inference_tap`, `test_registry_chat_template_kwargs`, `test_registry_loader`, `test_stack_priors_compiler`, `test_thinking_roles_chat_lane`, `test_typed_decisions_shadow`, `test_chat_completions_roles`, `test_chat_delegation`, `test_instance_topology_smt_siblings`, `test_runtime_flags`, `test_chat_vision` and `test_mtmd_probe`.
- **Alias-target modules: 533 passed, 3 skipped.** 25 files: `test_escalation`, `test_executor*`, `test_model_server*`, `test_tool_registry*`, `test_prefix_cache*`, `test_task_ir*`, `test_memrl_service` and the rest.
- **Stack-priors consumers: 217 passed** (5 files that grep for `load_stack_priors_artifact`, `live_stack_role_ids`, `_valid_delegate_roles`, `fence_nonserving_route` or `_priors_cache_key`).
- **Document and vision: 131 passed** (`test_chat_vision`, `test_odl_structured`, `tests/integration/test_document_pipeline.py`).
- **Pre-existing failures** (all in `orch_baseline2_failing_ids.txt`):
  - `test_config_consolidation.py::TestPathsDefaults::test_all_paths_on_raid` and `TestWorkerPoolPathsDefaults::test_paths_on_raid` need `/mnt/raid0`.
  - `test_orchestrator_stack_import_is_argv_safe.py` (4 tests). The `scripts/server/orchestrator_stack.py` pin in `source_clone.py` is already stale at base (I did not touch that file). With that pin corrected temporarily, they still fail here with "no real interpreter distinct from the project venv". So the ni63 clone with the new `src/__init__.py` could not be exercised in this container.
- I skipped the 700-trial `test_reproducer_catches_the_pre_fix_shim` because of the shared-box load; the code it exercises did not change.

## For the integrator
- **Pins updated** in `tests/fixtures/ni63_capacity_child/source_clone.py`: `src/__init__.py`, `src/config/__init__.py`, `src/config/models.py`, `src/config/validation.py`, `src/registry/registry_loader.py`. Other packages that touch these files will conflict on those pin lines.
- **Files outside the config/registry/runtime area:** `src/__init__.py`, `src/inference/model_server.py` (docstring only), `src/services/document_client.py`, `scripts/lib/env.sh`, `docs/chapters/01-runtime-environment.md`, `src/features.py` (docstring only).
- **epyc-root, not editable from here.** `scripts/harness/strategy_projection_report_capture.py` `TRUSTED_APP_SOURCES` pins `src/__init__.py` (`src-package-source.bin`). That pin matched base and does not match after `d3dd210f`. Six of that file's 11 pins were already stale at base (including `tier_specs.py`), so the tool already refused; its pin needs refreshing if it is revived.
- **Follow-ups:**
  - Delete the 14 shim files and codemod importers once the epyc-root capture closures drop them.
  - Optionally retarget the pyproject entry point to `src.registry.registry_loader:main`. It works through the alias today.
- No kernel defects found, and no fingerprinted autopilot files touched.