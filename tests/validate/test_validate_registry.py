from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "validate" / "validate_registry.py"
_SPEC = importlib.util.spec_from_file_location("validate_registry", _SCRIPT)
assert _SPEC and _SPEC.loader
validate_registry_module = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = validate_registry_module
_SPEC.loader.exec_module(validate_registry_module)
validate_registry = validate_registry_module.validate_registry


def test_validate_registry_accepts_valid_field_values(tmp_path: Path) -> None:
    registry = tmp_path / "model_registry.yaml"
    registry.write_text(
        """
runtime_defaults:
  agent_file_compression_operating_point: mild
roles:
  worker_general:
    agent_file_compression_operating_point: aggressive
""".lstrip(),
        encoding="utf-8",
    )

    assert validate_registry(registry) == []


def test_validate_registry_reports_invalid_values(tmp_path: Path) -> None:
    registry = tmp_path / "model_registry.yaml"
    registry.write_text(
        """
runtime_defaults:
  agent_file_compression_operating_point: banana
roles:
  worker_general:
    agent_file_compression_operating_point: maybe
""".lstrip(),
        encoding="utf-8",
    )

    errors = validate_registry(registry)

    assert any(
        "runtime_defaults.agent_file_compression_operating_point" in err for err in errors
    )
    assert any(
        "roles.worker_general.agent_file_compression_operating_point" in err for err in errors
    )


def test_validate_registry_reports_missing_default_field(tmp_path: Path) -> None:
    registry = tmp_path / "model_registry.yaml"
    registry.write_text(
        """
roles:
  worker_general:
    agent_file_compression_operating_point: none
""".lstrip(),
        encoding="utf-8",
    )

    errors = validate_registry(registry)

    assert any(
        "missing runtime_defaults.agent_file_compression_operating_point" in err
        for err in errors
    )
