from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml

from src.classifiers.xmas_routing import XMAS_DOMAINS, XMAS_FUNCTIONS

MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "validate"
    / "validate_xmas_winner_table.py"
)
SPEC = importlib.util.spec_from_file_location("validate_xmas_winner_table", MODULE_PATH)
assert SPEC is not None
validate_xmas = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(validate_xmas)


def _complete_evidence_backed_table_payload() -> dict:
    cells = {
        domain: {function: "frontdoor" for function in XMAS_FUNCTIONS}
        for domain in XMAS_DOMAINS
    }
    evidence = {
        domain: {
            function: {
                "cell": f"{domain}:{function}",
                "winner": "frontdoor",
                "sample_count": 2,
                "source_summary_path": f"summary.table.{domain}.frontdoor",
                "candidates": {
                    "frontdoor": {
                        "correct": 2,
                        "total": 2,
                        "accuracy": 1.0,
                        "wall_mean_s": 1.0,
                    }
                },
            }
            for function in XMAS_FUNCTIONS
        }
        for domain in XMAS_DOMAINS
    }
    return {
        "version": "xmas-test",
        "fallback_role": "frontdoor",
        "provenance": {
            "source_results": [
                "data/research/2026-05-20-xmas-v3-25tasks-nothink/results.json"
            ],
            "derivation_mode": "function_axis_sweep",
        },
        "cells": cells,
        "evidence": evidence,
    }


def test_validate_config_ignores_default_off_without_table(tmp_path: Path) -> None:
    config = tmp_path / "classifier_config.yaml"
    config.write_text(
        "xmas_routing:\n  mode: off\n  winner_table_path: ''\n",
        encoding="utf-8",
    )

    assert validate_xmas.validate_config(config) == []


def test_validate_config_rejects_enforce_without_table(tmp_path: Path) -> None:
    config = tmp_path / "classifier_config.yaml"
    config.write_text(
        "xmas_routing:\n  mode: enforce\n  winner_table_path: ''\n",
        encoding="utf-8",
    )

    assert validate_xmas.validate_config(config) == [
        "xmas_routing.mode=enforce requires winner_table_path"
    ]


def test_validate_config_rejects_enforce_with_unevidenced_table(tmp_path: Path) -> None:
    table = tmp_path / "winner.yaml"
    payload = _complete_evidence_backed_table_payload()
    payload.pop("evidence")
    table.write_text(yaml.safe_dump(payload), encoding="utf-8")
    config = tmp_path / "orchestration" / "classifier_config.yaml"
    config.parent.mkdir()
    config.write_text(
        f"xmas_routing:\n  mode: enforce\n  winner_table_path: {table}\n",
        encoding="utf-8",
    )

    errors = validate_xmas.validate_config(config)

    assert len(errors) == 1
    assert "missing evidence for 25 cells" in errors[0]


def test_validate_config_rejects_enforce_with_domain_proxy_table(tmp_path: Path) -> None:
    table = tmp_path / "winner.yaml"
    payload = _complete_evidence_backed_table_payload()
    payload["provenance"]["derivation_mode"] = "domain_winner_reused_for_function"
    table.write_text(yaml.safe_dump(payload), encoding="utf-8")
    config = tmp_path / "orchestration" / "classifier_config.yaml"
    config.parent.mkdir()
    config.write_text(
        f"xmas_routing:\n  mode: enforce\n  winner_table_path: {table}\n",
        encoding="utf-8",
    )

    errors = validate_xmas.validate_config(config)

    assert errors == [
        f"{table}: winner table uses domain-proxy evidence; mode=enforce requires "
        "true function-axis 5x5 sweep evidence"
    ]


def test_validate_table_accepts_complete_evidence_backed_table(tmp_path: Path) -> None:
    table = tmp_path / "winner.yaml"
    table.write_text(
        yaml.safe_dump(_complete_evidence_backed_table_payload()),
        encoding="utf-8",
    )

    assert validate_xmas.validate_table(table) == []


def test_validate_table_can_accept_domain_proxy_artifact_directly(tmp_path: Path) -> None:
    table = tmp_path / "winner.yaml"
    payload = _complete_evidence_backed_table_payload()
    payload["provenance"]["derivation_mode"] = "domain_winner_reused_for_function"
    table.write_text(yaml.safe_dump(payload), encoding="utf-8")

    assert validate_xmas.validate_table(table) == []
    assert validate_xmas.validate_table(table, require_function_axis=True) == [
        "winner table uses domain-proxy evidence; mode=enforce requires "
        "true function-axis 5x5 sweep evidence"
    ]


def test_cli_table_validation_can_require_function_axis(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    table = tmp_path / "winner.yaml"
    payload = _complete_evidence_backed_table_payload()
    payload["provenance"]["derivation_mode"] = "domain_winner_reused_for_function"
    table.write_text(yaml.safe_dump(payload), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "validate_xmas_winner_table.py",
            "--table",
            str(table),
            "--require-function-axis",
        ],
    )

    assert validate_xmas.main() == 1

    captured = capsys.readouterr()
    assert "winner table uses domain-proxy evidence" in captured.err
