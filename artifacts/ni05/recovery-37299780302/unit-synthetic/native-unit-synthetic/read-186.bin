"""Tests for additive diagnostics in src.config.validation."""

from __future__ import annotations

from pathlib import Path

from src.config.validation import (
    _load_registry_runtime_defaults,
    _load_registry_timeouts,
    get_validation_diagnostics,
    reset_validation_caches,
)


def test_runtime_defaults_records_missing_registry(monkeypatch, tmp_path: Path):
    reset_validation_caches()
    monkeypatch.setenv(
        "ORCHESTRATOR_PATHS_REGISTRY_PATH",
        str(tmp_path / "missing-model-registry.yaml"),
    )

    assert _load_registry_runtime_defaults() == {}

    diag = get_validation_diagnostics()["runtime_defaults"]
    assert diag["status"] == "missing"
    assert diag["failure_reason"] == "missing_registry"


def test_timeouts_records_yaml_parse_fallback(monkeypatch, tmp_path: Path):
    reset_validation_caches()
    registry_path = tmp_path / "model_registry.yaml"
    registry_path.write_text("runtime_defaults:\n  timeouts: [broken\n", encoding="utf-8")
    monkeypatch.setenv("ORCHESTRATOR_PATHS_REGISTRY_PATH", str(registry_path))

    assert _load_registry_timeouts() == {"default": 600}

    diag = get_validation_diagnostics()["timeouts"]
    assert diag["status"] == "fallback"
    assert diag["failure_reason"]
    assert diag["entries"] == 1
