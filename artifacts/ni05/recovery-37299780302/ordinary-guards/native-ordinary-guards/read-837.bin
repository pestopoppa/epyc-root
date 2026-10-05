"""Tests for syncing procedure role enums from stack priors."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from scripts.registry.sync_procedure_role_enums import sync_procedure_role_enums


def _write_yaml(path: Path, data: dict) -> Path:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def _write_schema(path: Path) -> Path:
    path.write_text(
        """{
  "properties": {
    "permissions": {
      "properties": {
        "roles": {
          "items": {
            "enum": ["frontdoor", "admin"]
          }
        }
      }
    }
  }
}
""",
        encoding="utf-8",
    )
    return path


def test_sync_procedure_role_enums_updates_role_input(tmp_path: Path) -> None:
    priors = _write_yaml(
        tmp_path / "stack_priors.yaml",
        {
            "roles": {
                "worker_math": {"deployment_status": "live_stack"},
                "frontdoor": {"deployment_status": "live_stack"},
            }
        },
    )
    procedure = _write_yaml(
        tmp_path / "add_model_to_registry.yaml",
        {
            "id": "add_model_to_registry",
            "inputs": [
                {
                    "name": "role",
                    "type": "string",
                    "description": "Role assignment",
                    "validation": {"enum": ["frontdoor"]},
                }
            ],
        },
    )
    schema = _write_schema(tmp_path / "procedure.schema.json")

    assert not sync_procedure_role_enums(
        priors_path=priors,
        procedure_path=procedure,
        schema_path=schema,
        check=True,
    )
    assert sync_procedure_role_enums(
        priors_path=priors,
        procedure_path=procedure,
        schema_path=schema,
    )

    payload = yaml.safe_load(procedure.read_text(encoding="utf-8"))
    assert payload["inputs"][0]["validation"]["enum"] == ["frontdoor", "worker_math"]
    schema_payload = json.loads(schema.read_text(encoding="utf-8"))
    assert schema_payload["properties"]["permissions"]["properties"]["roles"]["items"][
        "enum"
    ] == ["frontdoor", "worker_math", "admin"]
