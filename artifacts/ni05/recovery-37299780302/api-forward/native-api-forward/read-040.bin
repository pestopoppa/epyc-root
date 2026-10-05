"""`_ap3_prewarm_role_targets` must build a registry whose `get_role` satisfies
the access pattern `build_server_command` actually performs.

ORIGIN. Routed by `mainD` on 2026-08-12 as a latent defect, re-derived at HEAD by
`mainC` and CONFIRMED at runtime: `config_applicator.py` imported `load_registry`
from `scripts.lib.registry`, whose `ModelRegistry` has **no `get_role` method at
all** (`hasattr(reg, "get_role") is False`, verified against the live registry).
Every execution of that branch raised `AttributeError`. The row's line anchor had
rotted 1634 -> 1648; the finding underneath had not.

WHY THE OBVIOUS FIX IS WRONG, which is why this test checks a CONTRACT and not a
spelling. `ModelRegistry` does expose `get_role_config()`, so `get_role` ->
`get_role_config` reads like the natural repair. It is not:
`build_server_command` consumes the value by NESTED ATTRIBUTE access —
`role_config.model.full_path`, `role_config.acceleration`, `role_config.name`
(orchestrator_stack.py:1353-1355) — and `get_role_config()` returns a plain
`dict`. That swap trades an `AttributeError` on `registry.get_role` for an
`AttributeError` on `dict.model`, one frame deeper and later. The correct object
is the `RoleConfig` dataclass returned by `RegistryLoader.get_role()`, which is
what `orchestrator_stack` itself uses (it imports `RegistryLoader`, never
`load_registry`).

WHAT THIS PINS. Not the import line — a source-string assertion would pass for the
wrong reason the moment someone reformats it, and would false-FAIL on a harmless
rename. This resolves the callee actually used inside the function via AST, looks
it up in the module's real namespace, and asserts the object it produces supports
the attribute chain the consumer performs. Swap in any registry that does not, and
this fails.
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

import scripts.autopilot.config_applicator as ca

# The attribute chain build_server_command performs on role_config.
# orchestrator_stack.py:1353-1355.
_CONSUMER_CHAIN = (("model", "full_path"), ("acceleration",), ("name",))


def _registry_binding() -> tuple[str, object]:
    """AST-resolve the callee bound to `registry`, AND the module it comes from.

    Behaviour-anchored: finds the assignment as the code actually parses, so
    reformatting, renaming the alias, or moving the line does not matter.

    The module is resolved from the function's OWN import statements rather than
    hardcoded. That matters for the failure message: with the module hardcoded,
    reintroducing the defect made this test die with "module ... has no attribute
    load_registry" — a resolution error that hides the actual finding. Now the
    wrong registry resolves successfully and fails on the CONTRACT, which is the
    diagnostic the next reader needs.
    """
    tree = ast.parse(inspect.cleandoc(inspect.getsource(ca._ap3_prewarm_role_targets)))

    imports: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                imports[alias.asname or alias.name] = node.module

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if "registry" not in [t.id for t in node.targets if isinstance(t, ast.Name)]:
            continue
        if not isinstance(node.value, ast.Call):
            continue
        func = node.value.func
        name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
        module = imports.get(name)
        if module is None:
            pytest.fail(f"`registry` is built from {name!r}, imported from nowhere visible")
        obj = getattr(__import__(module, fromlist=[name]), name, None)
        assert obj is not None, f"could not resolve {name!r} from {module!r}"
        return name, obj

    pytest.fail(
        "No `registry = <call>` assignment found in _ap3_prewarm_role_targets. "
        "If the function was restructured, re-point this test at whatever now "
        "supplies role_config to build_server_command — do not delete it."
    )


def test_prewarm_registry_exposes_get_role() -> None:
    """The precise defect: what `registry` is bound to must produce a `get_role`."""
    name, callee = _registry_binding()
    try:
        registry = callee()
    except Exception as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f"registry not constructible in this environment: {exc}")
    assert hasattr(registry, "get_role"), (
        f"{name}() returns {type(registry).__name__}, which has no `get_role`; "
        f"_ap3_prewarm_role_targets calls registry.get_role(primary) and will "
        f"raise AttributeError. This is the exact 2026-08-12 defect. NOTE: "
        f"switching the CALL to `get_role_config` does NOT fix it — that returns "
        f"a dict and build_server_command needs attribute access. Use RegistryLoader."
    )


def test_get_role_returns_an_object_the_consumer_can_actually_read() -> None:
    """The contract behind the defect: a dict passes the test above and still fails."""
    name, callee = _registry_binding()
    try:
        registry = callee()
    except Exception as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f"registry not constructible in this environment: {exc}")
    if not hasattr(registry, "get_role"):
        pytest.fail(
            f"{name}() -> {type(registry).__name__} has no `get_role`; see "
            f"test_prewarm_registry_exposes_get_role for the diagnosis."
        )

    roles = list(getattr(registry, "_roles", {}) or {})
    if not roles:
        pytest.skip("registry exposes no roles to sample")

    role_config = registry.get_role(roles[0])
    for chain in _CONSUMER_CHAIN:
        obj = role_config
        for attr in chain:
            assert hasattr(obj, attr), (
                f"role_config{''.join('.' + a for a in chain)} is not reachable "
                f"(stopped at {attr!r} on {type(obj).__name__}). "
                f"build_server_command performs exactly this access at "
                f"orchestrator_stack.py:1353-1355, so this registry cannot feed it. "
                f"A plain dict from get_role_config() fails here — that is the trap."
            )
            obj = getattr(obj, attr)


def test_the_rejected_registry_still_fails_the_contract() -> None:
    """Guards the REASON, not just the symptom.

    If `ModelRegistry` ever grows a `get_role`, the comment in config_applicator
    explaining why it is unsuitable becomes stale and this fires so someone
    re-derives the choice rather than inheriting a stale rationale.
    """
    from scripts.lib.registry import ModelRegistry

    assert not hasattr(ModelRegistry, "get_role"), (
        "ModelRegistry now has `get_role`. Re-derive the config_applicator "
        "choice: verify what it RETURNS supports role_config.model.full_path "
        "before treating the two registries as interchangeable."
    )
