"""AP-55: every baseline-promotion call site in the autopilot loop honours the hold.

Structural guard added with the 2026-09-16 merge train: gate-frontier's decision (c)
added a within-noise ``gate.update_baseline`` call that the AP-55 branch never saw, so
an enforced hold was bypassed there. Each ``*.update_baseline(...)`` call inside
``scripts/autopilot/autopilot.py`` must sit under an ``if`` whose test contains
``not ap55_gate.get("hold")``, or in the ``else``/``elif`` of an ``if`` whose test
contains a positive ``ap55_gate.get("hold")``.
"""

from __future__ import annotations

import ast
from pathlib import Path

AUTOPILOT = Path(__file__).resolve().parents[2] / "scripts" / "autopilot" / "autopilot.py"


def _is_hold_get(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "get"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "ap55_gate"
        and bool(node.args)
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value == "hold"
    )


def _hold_polarities(test: ast.AST) -> set[bool]:
    """True = the test requires hold, False = the test requires no hold."""
    out: set[bool] = set()
    negated: set[int] = set()
    for node in ast.walk(test):
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not) and _is_hold_get(node.operand):
            negated.add(id(node.operand))
            out.add(False)
    for node in ast.walk(test):
        if _is_hold_get(node) and id(node) not in negated:
            out.add(True)
    return out


def _guarded_calls() -> list[tuple[int, bool]]:
    tree = ast.parse(AUTOPILOT.read_text())
    results: list[tuple[int, bool]] = []

    def visit(node: ast.AST, guarded: bool) -> None:
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "update_baseline":
            results.append((node.lineno, guarded))
        if isinstance(node, ast.If):
            pol = _hold_polarities(node.test)
            for child in node.body:
                visit(child, guarded or (False in pol))
            for child in node.orelse:
                visit(child, guarded or (True in pol))
            visit(node.test, guarded)
            return
        for child in ast.iter_child_nodes(node):
            visit(child, guarded)

    visit(tree, False)
    return results


def test_every_update_baseline_call_honours_ap55_hold():
    calls = _guarded_calls()
    assert len(calls) >= 3, calls  # within-noise, clean, multitier final_t1
    unguarded = [line for line, ok in calls if not ok]
    assert not unguarded, f"update_baseline calls bypassing the AP-55 hold at lines {unguarded}"


def test_detector_flags_an_unguarded_call():
    src = "if x:\n    gate.update_baseline(r)\nelif ap55_gate.get('hold'):\n    pass\n"
    tree = ast.parse(src)
    if_node = tree.body[0]
    assert _hold_polarities(if_node.test) == set()
    assert _hold_polarities(if_node.orelse[0].test) == {True}
    assert _hold_polarities(ast.parse("a and not ap55_gate.get('hold')").body[0].value) == {False}
