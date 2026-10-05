"""NIB2-74: code tasks must run under the scorer's own interpreter, not PATH python3."""

import ast
from pathlib import Path


def test_no_bare_python3_interpreter():
    """Assert that debug_scorer.py does not use bare 'python3' as subprocess interpreter."""
    scorer_path = Path(__file__).parent.parent.parent / "scripts" / "benchmark" / "debug_scorer.py"
    source = scorer_path.read_text()
    tree = ast.parse(source)

    # Walk the AST looking for list literals containing "python3" as first element
    for node in ast.walk(tree):
        if isinstance(node, ast.List) and node.elts:
            first_elem = node.elts[0]
            if isinstance(first_elem, ast.Constant) and first_elem.value == "python3":
                # Found a bare "python3" string literal in a list context
                raise AssertionError(
                    f"Found bare 'python3' string literal at line {first_elem.lineno}. "
                    "Use sys.executable instead."
                )


def test_sys_executable_is_referenced():
    """Assert that debug_scorer.py references sys.executable."""
    scorer_path = Path(__file__).parent.parent.parent / "scripts" / "benchmark" / "debug_scorer.py"
    source = scorer_path.read_text()
    assert "sys.executable" in source, "sys.executable must be referenced in debug_scorer.py"
