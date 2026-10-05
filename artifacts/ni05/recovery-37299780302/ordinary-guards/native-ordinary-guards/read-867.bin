"""NIB2-79: every python handler named in tool_registry.yaml must resolve.

An unresolvable ``module``/``function`` pair does not fail the API start: the
loader swaps in an error stub and logs one warning per uvicorn worker. That hid
four dead ``archive_*`` entries for eight months, so resolution is asserted here.
"""

from __future__ import annotations

import importlib
import logging
from pathlib import Path

import pytest
import yaml

REGISTRY = Path(__file__).resolve().parents[2] / "orchestration" / "tool_registry.yaml"


def _python_handlers() -> list[tuple[str, str, str]]:
    data = yaml.safe_load(REGISTRY.read_text())
    rows = []
    for name, spec in data["tools"].items():
        impl = (spec or {}).get("implementation") or {}
        if impl.get("type") == "python":
            rows.append((name, impl.get("module"), impl.get("function")))
    return rows


HANDLERS = _python_handlers()


def test_registry_has_python_handlers():
    assert len(HANDLERS) > 0


@pytest.mark.parametrize(("tool", "module", "function"), HANDLERS, ids=[h[0] for h in HANDLERS])
def test_python_handler_resolves(tool, module, function):
    assert module and function, f"{tool}: implementation needs both module and function"
    mod = importlib.import_module(module)
    handler = getattr(mod, function, None)
    assert handler is not None, f"{tool}: {module} has no attribute {function!r}"
    assert callable(handler), f"{tool}: {module}.{function} is not callable"


def test_load_from_yaml_logs_no_handler_failures(caplog):
    from src.registry.tool_registry import ToolRegistry, load_from_yaml

    with caplog.at_level(logging.WARNING, logger="src.registry.tool_registry"):
        loaded = load_from_yaml(ToolRegistry(), REGISTRY)

    assert loaded > 0
    failures = [
        r.getMessage() for r in caplog.records if "Could not load handler" in r.getMessage()
    ]
    assert failures == []


def test_archive_tools_are_repl_builtins_not_registry_entries():
    data = yaml.safe_load(REGISTRY.read_text())
    for name in ("archive_open", "archive_extract", "archive_file", "archive_search"):
        assert name not in data["tools"]
