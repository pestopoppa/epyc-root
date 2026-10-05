"""Tests for orchestrator stack runtime-requirements lookup."""

from __future__ import annotations

from types import SimpleNamespace

from scripts.server.stack_runtime import runtime_requirements_for_role


def _registry(server_mode: dict) -> SimpleNamespace:
    return SimpleNamespace(_raw={"server_mode": server_mode})


def test_returns_none_for_unknown_role() -> None:
    reg = _registry({"some_entry": {"model_role": "frontdoor"}})
    assert runtime_requirements_for_role(reg, "nonexistent") == (None, None)


def test_returns_none_when_registry_is_none() -> None:
    assert runtime_requirements_for_role(None, "anyrole") == (None, None)


def test_returns_none_when_registry_has_no_raw_attr() -> None:
    """Defensive: stub-registry-like object without _raw must not crash."""
    fake = object()
    assert runtime_requirements_for_role(fake, "anyrole") == (None, None)


def test_extracts_binary_dir_and_ld_library_path() -> None:
    reg = _registry({
        "gemma4_mtp": {
            "model_role": "worker_general",
            "runtime_requirements": {
                "binary_dir": "/opt/ik_llama.cpp/build/bin",
                "ld_library_path": ["/opt/ik_llama.cpp/build/lib", "/usr/lib/llvm-20/lib"],
            },
        },
    })
    binary_dir, ld_paths = runtime_requirements_for_role(reg, "worker_general")
    assert binary_dir == "/opt/ik_llama.cpp/build/bin"
    assert ld_paths == ["/opt/ik_llama.cpp/build/lib", "/usr/lib/llvm-20/lib"]


def test_returns_none_when_runtime_requirements_missing() -> None:
    """Entry exists for the role but has no runtime_requirements key."""
    reg = _registry({"plain": {"model_role": "frontdoor"}})
    assert runtime_requirements_for_role(reg, "frontdoor") == (None, None)


def test_skips_non_dict_server_mode_entries() -> None:
    """server_mode may contain non-dict garbage that must not raise AttributeError."""
    reg = _registry({
        "garbage": "stringy",
        "list_thing": ["nope"],
        "good": {
            "model_role": "architect_general",
            "runtime_requirements": {"binary_dir": "/usr/local/bin"},
        },
    })
    binary_dir, _ = runtime_requirements_for_role(reg, "architect_general")
    assert binary_dir == "/usr/local/bin"
