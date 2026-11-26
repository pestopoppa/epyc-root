"""Independent check that the calibrated LOOP-62 XFAIL preserves its pinned stress test."""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path


_REFERENCE = "5886e5aeb273fd4a8aaf1447bb3d8bc163d5c082:tests/unit/test_inference_lock_concurrent_import.py"
_CANDIDATE = Path("tests/unit/test_compat_alias_cold_import.py")
_IDENTITY = "test_compat_alias_is_the_unrenamed_target_module"
_MIXED = "test_all_compat_aliases_concurrent_first_import_is_safe"
_XFAIL_REASON = "LOOP-62: mixed-alias cold-import cycle via src.dispatcher, open"


def validate(lane: Path) -> str | None:
    """Return a contract violation, or None when the expected XFAIL is preserved."""
    result = subprocess.run(
        ["git", "-C", str(lane), "show", _REFERENCE],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode:
        raise RuntimeError(f"cannot read pinned LOOP-62 source: {result.stderr.strip()}")
    path = lane / _CANDIDATE
    if not path.is_file():
        return f"missing LOOP-62 candidate test: {_CANDIDATE}"
    return _validate_source(result.stdout, path.read_text())


def _aliases(tree: ast.Module) -> dict[str, str] | None:
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "_COMPAT_ALIASES" for target in node.targets
        ):
            try:
                return ast.literal_eval(node.value)
            except (TypeError, ValueError, SyntaxError):
                return None
    return None


def _statements(function: ast.FunctionDef) -> list[str]:
    body = function.body[1:] if ast.get_docstring(function) is not None else function.body
    return [ast.dump(node) for node in body]


def _has_identity_assertion(function: ast.FunctionDef) -> bool:
    arguments = function.args.posonlyargs + function.args.args
    if len(arguments) != 2:
        return False
    alias, target = (arg.arg for arg in arguments)
    imported_alias = f"importlib.import_module({alias})"
    alias_values = {imported_alias}
    for statement in function.body:
        if isinstance(statement, ast.Assign) and ast.unparse(statement.value) == imported_alias:
            alias_values.update(ast.unparse(name) for name in statement.targets if isinstance(name, ast.Name))
            alias_values.add(f"sys.modules[{alias}]")
        if isinstance(statement, ast.Expr) and ast.unparse(statement.value) == imported_alias:
            alias_values.add(f"sys.modules[{alias}]")
        if isinstance(statement, ast.Assert) and isinstance(statement.test, ast.Compare):
            test = statement.test
            if len(test.ops) == 1 and isinstance(test.ops[0], ast.Is):
                operands = {ast.unparse(test.left), ast.unparse(test.comparators[0])}
                if f"sys.modules[{target}]" in operands and operands & alias_values:
                    return True
    return False


def _has_expected_xfail(function: ast.FunctionDef) -> bool:
    if len(function.decorator_list) != 1:
        return False
    mark = function.decorator_list[0]
    if not isinstance(mark, ast.Call) or ast.unparse(mark.func) != "pytest.mark.xfail" or mark.args:
        return False
    keywords = {kw.arg: kw.value for kw in mark.keywords}
    return (
        keywords.keys() == {"strict", "reason"}
        and isinstance(keywords["strict"], ast.Constant)
        and keywords["strict"].value is False
        and isinstance(keywords["reason"], ast.Constant)
        and keywords["reason"].value == _XFAIL_REASON
    )


def _validate_source(reference: str, candidate: str) -> str | None:
    baseline = ast.parse(reference)
    try:
        tree = ast.parse(candidate)
    except SyntaxError as exc:
        return f"invalid LOOP-62 test source: {exc.msg}"
    if _aliases(tree) != _aliases(baseline):
        return "LOOP-62 must preserve the pinned 16-entry alias map"

    original = {node.name: node for node in baseline.body if isinstance(node, ast.FunctionDef)}
    tests = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    identity = tests.get(_IDENTITY)
    if identity is None or not _has_identity_assertion(identity):
        return "LOOP-62 must assert alias and target object identity"

    mixed = tests.get(_MIXED)
    if mixed is None or _statements(mixed) != _statements(original[_MIXED]):
        # An XFAIL also accepts format/compile failures in replacements for the
        # original mixed script, before a single concurrent import is attempted.
        return "LOOP-62 must preserve the pinned mixed test body (20 cold subprocesses × 24 threads)"
    if not _has_expected_xfail(mixed):
        return "LOOP-62 mixed test requires the pinned xfail reason and strict=False"
    return None
