"""AST-isolated loader for the nine original MF-VBS2 batch-edit fixtures.

This module intentionally does not import ``src.graph.helpers``. The fixture test
module imports this loader and receives an H module backed by the fingerprint-pinned
actual helper function nodes. Batch-edit parser/core/runner modules remain actual APP
source modules. This is a bounded native fixture harness, not full-app execution.
"""
from __future__ import annotations

import ast
import asyncio
import functools
import importlib.util
import logging
import os
from pathlib import Path
import sys
import types

APP_COMMIT = "c0263f8c36f3042e9a8145d03dfda63952ade199"
APP_BLOBS = {
    "src/graph/helpers.py": "64e8fb412a42c608d07c1880593a905dff82e2bc",
    "src/batch_edit_parse.py": "1a917c9691238414730945436f00fbb2aae42f17",
    "src/batch_edit.py": "2cacb2bc056043d1fa691fd0255c2801cfcee127",
    "src/batch_edit_runner.py": "3fcebbf7a7d9438be2889cbcc4c5ce2bbbb90a6a",
    "tests/unit/test_graph_helpers_batch_edit.py": "ed05a963cff15fdda0ee444fcc92894b73354025",
    "pyproject.toml": "b4fe6ccada3a1aee3e08aa860045a78d8b85c7b1",
    "uv.lock": "ef2306018773ff9a1e80389970d92f66fcf8d5b7",
}
HELPER_NODES = (
    "_batch_edit_repo_root",
    "_batch_edit_verify_fn",
    "_batch_edit_failure_summary",
    "_finalize_batch_edit",
    "_record_batch_edit_state",
    "_maybe_batch_edit_turn",
)
TEST_HELPERS = ("_ctx", "_wrap", "_no_session_record", "_set_flag", "_point_repo", "_run")
SELECTED_TESTS = (
    "test_flag_off_returns_none_even_with_valid_patchset",
    "test_verify_failure_does_not_promote",
    "test_verify_command_uses_full_tree_sandbox",
    "test_verifier_label_uses_the_command_snapshot",
    "test_syntax_only_success_is_not_described_as_acceptance_verified",
    "test_verify_command_failure_does_not_promote",
    "test_stale_base_does_not_promote",
    "test_telemetry_distinguishes_absent_vs_malformed",
    "test_telemetry_records_applied_and_verify_failed",
)


def _git(app: Path, *args: str) -> str:
    import subprocess

    return subprocess.check_output(["git", "-C", str(app), *args], text=True).strip()


def verify_app_readset(app: Path) -> None:
    app = app.resolve()
    if _git(app, "rev-parse", "HEAD") != APP_COMMIT:
        raise RuntimeError("APP checkout is not the approved MF-VBS2 source commit")
    if _git(app, "status", "--porcelain", "--untracked-files=no"):
        raise RuntimeError("APP tracked worktree is dirty")
    for rel, expected in APP_BLOBS.items():
        if _git(app, "rev-parse", f"HEAD:{rel}") != expected:
            raise RuntimeError(f"APP source pin mismatch: {rel}")
        if not (app / rel).is_file():
            raise RuntimeError(f"APP source file missing: {rel}")


def _load_module(name: str, path: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load exact source module {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _install_source_package(app: Path) -> None:
    """Create a minimal src package so only declared leaf source modules can load."""
    package = types.ModuleType("src")
    package.__path__ = [str(app / "src")]
    package.__package__ = "src"
    sys.modules["src"] = package

    # Keep the exact feature monkeypatch seam used in the original tests without
    # importing src.features' unrelated registry/dependency graph.
    features = types.ModuleType("src.features")
    features.features = lambda: types.SimpleNamespace(batch_edit_mode=False)
    features.__package__ = "src"
    sys.modules["src.features"] = features
    package.features = features

    repl = types.ModuleType("src.repl_environment")
    repl.__path__ = []
    repl.__package__ = "src.repl_environment"
    sys.modules["src.repl_environment"] = repl
    task_root = types.ModuleType("src.repl_environment.task_root")
    task_root.request_scope = lambda: None
    task_root.get_task_root = lambda: Path.cwd()
    task_root.__package__ = "src.repl_environment"
    sys.modules["src.repl_environment.task_root"] = task_root
    repl.task_root = task_root


def _compile_helper_namespace(app: Path) -> types.ModuleType:
    source = (app / "src/graph/helpers.py").read_text(encoding="utf-8")
    tree = ast.parse(source, filename="src/graph/helpers.py")
    wanted = {node.name: node for node in tree.body
              if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
              and node.name in HELPER_NODES}
    if set(wanted) != set(HELPER_NODES):
        raise RuntimeError("pinned helper AST is missing an approved function node")
    module_ast = ast.Module(body=[
        ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0),
        *[wanted[name] for name in HELPER_NODES],
    ], type_ignores=[])
    ast.fix_missing_locations(module_ast)
    namespace = types.ModuleType("mf_vbs2_isolated_helpers")
    namespace.__file__ = "src/graph/helpers.py (AST node extraction; source pinned)"
    namespace.Path = Path
    namespace.os = os
    namespace.asyncio = asyncio
    namespace.functools = functools
    namespace.log = logging.getLogger("mf_vbs2_isolated_helpers")
    namespace._record_session_turn = lambda *args, **kwargs: None
    namespace._BATCH_EDIT_STATE_COUNTS = {}
    exec(compile(module_ast, namespace.__file__, "exec"), namespace.__dict__)
    return namespace


def initialize() -> types.ModuleType:
    """Load exact leaf modules and return the isolated actual helper namespace."""
    app_env = os.environ.get("MF_VBS2_APP_ROOT")
    if not app_env:
        raise RuntimeError("MF_VBS2_APP_ROOT is required for the isolated fixture")
    app = Path(app_env).resolve()
    verify_app_readset(app)
    _install_source_package(app)
    _load_module("src.batch_edit", app / "src/batch_edit.py")
    _load_module("src.batch_edit_parse", app / "src/batch_edit_parse.py")
    runner = _load_module("src.batch_edit_runner", app / "src/batch_edit_runner.py")
    sys.modules["src"].batch_edit = sys.modules["src.batch_edit"]
    sys.modules["src"].batch_edit_parse = sys.modules["src.batch_edit_parse"]
    sys.modules["src"].batch_edit_runner = runner
    return _compile_helper_namespace(app)


H = initialize()


def _node_sources(path: Path, names: tuple[str, ...]) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    tree = ast.parse(text, filename=str(path))
    found = {node.name: node for node in tree.body
             if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
             and node.name in names}
    if set(found) != set(names):
        raise RuntimeError(f"test source does not contain exact selected nodes: {path}")
    sources = {}
    for name in names:
        node = found[name]
        first_line = min([node.lineno, *[decorator.lineno for decorator in node.decorator_list]])
        sources[name] = "".join(lines[first_line - 1:node.end_lineno])
    return sources


def extract_original_tests(app: Path, destination: Path) -> tuple[str, ...]:
    """Write original selected helpers/bodies; replace only the graph import boundary."""
    verify_app_readset(app)
    source_path = app / "tests/unit/test_graph_helpers_batch_edit.py"
    original = source_path.read_text(encoding="utf-8")
    required_imports = (
        "from __future__ import annotations\n",
        "from pathlib import Path\n",
        "from types import SimpleNamespace\n",
        "import pytest\n",
    )
    if "from src.batch_edit import sha256_text\n" not in original:
        raise RuntimeError("pinned original test sha256 import changed")
    if not all(item in original for item in required_imports):
        raise RuntimeError("pinned original test imports changed")
    imports = "".join(required_imports)
    imports += "from mf_vbs2_ast_fixture import H\n"
    imports += "from src.batch_edit import sha256_text\n\n"
    helpers = _node_sources(source_path, TEST_HELPERS)
    tests = _node_sources(source_path, SELECTED_TESTS)
    generated = imports + "\n".join(helpers[name] for name in TEST_HELPERS)
    generated += "\n" + "\n".join(tests[name] for name in SELECTED_TESTS)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(generated, encoding="utf-8")
    return SELECTED_TESTS


if __name__ == "__main__":
    raise SystemExit("This module is imported by the capture driver and generated tests only")
