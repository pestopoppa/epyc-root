# MF-VBS2 native fixture capture

This is a prospective hosted capture recipe for nine selected original APP test
functions. It makes no capture until this workflow is manually dispatched after
MAIN reviews the source, generated test module, exact dependency set and readset.
No dispatch or local fixture execution has occurred for this proposal.

## Pinned source and readset

The APP checkout is fixed at `c0263f8c36f3042e9a8145d03dfda63952ade199`; the
producer/carrier checkout is ROOT `f5a316b64ac4078df0afc7d6e67a62645564037c`.
`mf_vbs2_ast_fixture.py` checks APP HEAD, tracked cleanliness and each following
Git blob before generating or loading test code:

| APP path | Blob |
|---|---|
| `src/graph/helpers.py` | `64e8fb412a42c608d07c1880593a905dff82e2bc` |
| `src/batch_edit_parse.py` | `1a917c9691238414730945436f00fbb2aae42f17` |
| `src/batch_edit.py` | `2cacb2bc056043d1fa691fd0255c2801cfcee127` |
| `src/batch_edit_runner.py` | `3fcebbf7a7d9438be2889cbcc4c5ce2bbbb90a6a` |
| `tests/unit/test_graph_helpers_batch_edit.py` | `ed05a963cff15fdda0ee444fcc92894b73354025` |
| `pyproject.toml` | `b4fe6ccada3a1aee3e08aa860045a78d8b85c7b1` |
| `uv.lock` | `ef2306018773ff9a1e80389970d92f66fcf8d5b7` |

The native readset also includes the workflow, capture driver, AST bootstrap,
ROOT `scripts/ci/native_conformance.py` (`d2d7bd90f86cffa23c51db803288641c5c6fe461`),
ROOT `scripts/vidya/adapters/ci_conformance.py`
(`b5a521ef4debe7ad105830f5fa27bbf9c2168dcd`), ROOT `scripts/vidya/claim_tuple.py`
(`309af769e45245fd1452482eb2e0592a86a4a79f`), generated test module, environment
metadata, lock-derived install requirements, and installed-package freeze.

## Exact tested nodes

The helper namespace is compiled from actual APP AST nodes
`_batch_edit_repo_root` (513–518), `_batch_edit_verify_fn` (521–568),
`_batch_edit_failure_summary` (571–580), `_finalize_batch_edit` (583–601),
`_record_batch_edit_state` (612–614), and `_maybe_batch_edit_turn` (617–711).
Actual APP parser `parse_patchset_from_model_output` (93–136), all of
`src/batch_edit.py`, and actual runner nodes `compute_current_shas` (84–94),
`apply_patchset_sandboxed` (312–339), `promote_sandbox` (342–399), and
`cleanup_sandbox` (402–404) stay on the execution path.

The generated module copies the original decorators and function source ranges for
the six test support functions `_ctx`, `_wrap`, `_no_session_record`, `_set_flag`,
`_point_repo`, `_run`, and the nine tests below. It changes only the import boundary
that would otherwise import the full graph helper module: `H` comes from the
fingerprint-checked AST namespace. The exact original test module and generated
module both enter the native readset.

| Original case | Control covered |
|---|---|
| `test_flag_off_returns_none_even_with_valid_patchset` | default-off |
| `test_verify_failure_does_not_promote` | compile failure and no promotion |
| `test_verify_command_uses_full_tree_sandbox` | owner command observes changed and untouched files |
| `test_verifier_label_uses_the_command_snapshot` | verifier command/label use same captured configuration |
| `test_syntax_only_success_is_not_described_as_acceptance_verified` | honest syntax-only label |
| `test_verify_command_failure_does_not_promote` | owner-command failure and no promotion |
| `test_stale_base_does_not_promote` | stale content hash refusal |
| `test_telemetry_distinguishes_absent_vs_malformed` | distinct input accounting |
| `test_telemetry_records_applied_and_verify_failed` | applied and verifier-failure accounting |

The 13-case source module is intentionally not run wholesale: its other four cases
are outside the approved verifier-label delta.

## Bootstrap and test boundary

The bootstrap does not import `src.graph.helpers`. It loads a deliberately minimal
synthetic `src` package, then loads the pinned batch-edit core/parser/runner from
their actual source files. It supplies the original monkeypatch seam
`src.features.features` with a minimal flag provider and `src.repl_environment.task_root`
with `request_scope() -> None`; those two imports are unrelated to this behavior and
would pull in the graph/runtime dependency tree. The original autouse test fixture
stubs `_record_session_turn`, and every test redirects the repository root to
`tmp_path`. The snapshot test monkeypatches the same actual runner module object used
by the helper namespace.

The installed test dependency closure is the exact APP `uv.lock` set for Python 3.11:
pytest 9.0.3, pytest-asyncio 1.3.0, iniconfig 2.3.0, packaging 26.0, pluggy 1.6.0,
Pygments 2.20.0, and typing-extensions 4.15.0. The driver checks every version against
the lock and installs with `--no-deps`; the complete venv package freeze and install
requirements are retained and hashed. The workflow uses `--noconftest`, disables
plugin autoload and explicitly enables `pytest_asyncio.plugin`.

Synthetic shell verifier strings originate in fixed original test bodies and run
only inside each test's temporary sandbox. The capture removes ambient verifier
command/timeout environment variables; each test sets or clears its own command.
Patchset `postconditions` remain inert declarations. The source path does not
execute model output as a command.

## Capture and shared grade

The driver calls the existing ROOT `native_conformance.capture_fixture_execution`
with three clean repository identities, exact selections and declared read paths.
It retains the original JUnit, request, receipt, command log and readset artifacts.
It then reopens that receipt through `native_rows` and `project_ci_conformance`, calls
the existing shared `claim_tuple.grade`, and hashes every native artifact before and
after projection/grading. The separate `shared-grade-analysis.json` records the
result and both hash maps; it does not rewrite an original.

The evidence claim is limited to those nine named fixture bodies on the pinned
source and runner. It does not establish full graph/app execution, arbitrary owner
command safety, model postconditions, deployment, runtime behavior, model quality,
performance, or general batch-edit acceptance.
