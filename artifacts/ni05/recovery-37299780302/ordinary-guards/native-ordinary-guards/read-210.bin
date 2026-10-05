"""Tests for corpus_quality_gate stack-derived model selection."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace


_BENCH = Path(__file__).resolve().parents[2] / "scripts" / "benchmark"
_SPEC = importlib.util.spec_from_file_location(
    "corpus_quality_gate_test",
    _BENCH / "corpus_quality_gate.py",
)
_MOD = importlib.util.module_from_spec(_SPEC)
sys.modules["corpus_quality_gate_test"] = _MOD
_SPEC.loader.exec_module(_MOD)


def _write_v1_corpus(index_path: Path, prompt: str, *, match: bool = True) -> None:
    from src.services.corpus_retrieval import extract_code_query

    index_path.mkdir(parents=True)
    query = extract_code_query(prompt)
    words = query.lower().split()
    grams = [" ".join(words[idx : idx + 4]) for idx in range(max(len(words) - 3, 0))]
    index_path.joinpath("meta.json").write_text(
        json.dumps({"ngram_size": 4}),
        encoding="utf-8",
    )
    index_path.joinpath("snippets.json").write_text(
        json.dumps(
            [
                {
                    "code": "def alpha_beta():\n    return 'ok'\n",
                    "file": "alpha.py",
                    "start_line": 10,
                    "hash": "snippet-hash",
                }
            ]
        ),
        encoding="utf-8",
    )
    index_path.joinpath("ngram_index.json").write_text(
        json.dumps({gram: [0] for gram in grams} if match else {}),
        encoding="utf-8",
    )


def test_load_live_models_reads_stack_prior_ports(tmp_path: Path) -> None:
    stack_priors = tmp_path / "stack_priors.yaml"
    stack_priors.write_text(
        """
roles:
  frontdoor:
    deployment_status: live_stack
    display_name: Frontdoor Display
    serving:
      endpoint: http://localhost:9100
      ports: [9100]
  worker_general:
    deployment_status: live_stack
    serving:
      ports: [9200]
  candidate:
    deployment_status: benchmark_or_candidate
    serving:
      endpoint: http://localhost:9900
""",
        encoding="utf-8",
    )

    models = _MOD._load_live_models(stack_priors)

    assert models["frontdoor"] == {
        "port": 9100,
        "name": "Frontdoor Display",
        "role": "frontdoor",
    }
    assert models["worker_general"]["port"] == 9200
    assert "candidate" not in models


def test_load_live_models_falls_back_to_ports_when_endpoint_port_is_invalid(
    tmp_path: Path,
) -> None:
    stack_priors = tmp_path / "stack_priors.yaml"
    stack_priors.write_text(
        """
roles:
  frontdoor:
    deployment_status: live_stack
    serving:
      endpoint: http://localhost:notaport
      ports: [9100]
  worker_general:
    deployment_status: live_stack
    serving:
      endpoint: http://localhost:notaport
""",
        encoding="utf-8",
    )

    models = _MOD._load_live_models(stack_priors)

    assert models["frontdoor"]["port"] == 9100
    assert "worker_general" not in models


def test_fallback_models_derive_ports_from_manifest(monkeypatch) -> None:
    monkeypatch.setattr(
        _MOD,
        "PORT_MAP",
        {
            "coder_escalation": 9000,
            "frontdoor": 9001,
            "worker_general": 9002,
            "architect_general": 9003,
        },
    )
    monkeypatch.setattr(
        _MOD,
        "HOT_ROLES",
        {"coder_escalation", "frontdoor", "worker_general", "architect_general"},
    )

    models = _MOD._fallback_models()

    assert models == {
        "coder_escalation": {
            "port": 9000,
            "name": "coder_escalation (manifest fallback)",
            "role": "coder_escalation",
        },
        "worker_general": {
            "port": 9002,
            "name": "worker_general (manifest fallback)",
            "role": "worker_general",
        },
        "frontdoor": {
            "port": 9001,
            "name": "frontdoor (manifest fallback)",
            "role": "frontdoor",
        },
        "architect_general": {
            "port": 9003,
            "name": "architect_general (manifest fallback)",
            "role": "architect_general",
        },
    }


def test_preferred_fallback_model_roles_filters_missing_manifest_entries(monkeypatch) -> None:
    monkeypatch.setattr(
        _MOD,
        "PORT_MAP",
        {"coder_escalation": 9000, "frontdoor": 9001, "worker_general": 9002},
    )
    monkeypatch.setattr(
        _MOD,
        "HOT_ROLES",
        {"coder_escalation", "frontdoor", "worker_general"},
    )

    assert _MOD._preferred_fallback_model_roles() == (
        "coder_escalation",
        "worker_general",
        "frontdoor",
    )


def test_default_model_keys_are_valid_loaded_roles() -> None:
    models = {
        "coder_escalation": {"port": 8070},
        "frontdoor": {"port": 8070},
        "worker_general": {"port": 8072},
        "architect_general": {"port": 8073},
        "custom_role": {"port": 9000},
    }

    defaults = _MOD._default_model_keys(models)

    assert defaults == ["coder_escalation", "worker_general"]
    assert set(defaults) <= set(models)


def test_default_model_keys_falls_back_to_available_models() -> None:
    models = {"custom_role": {"port": 9000}}

    assert _MOD._default_model_keys(models) == ["custom_role"]


def test_build_corpus_prompt_with_diagnostics_reports_injection(tmp_path: Path) -> None:
    from src.services.corpus_retrieval import CorpusRetriever

    prompt = "Implement alpha_beta gamma_delta helper with retry logic."
    index_path = tmp_path / "corpus"
    _write_v1_corpus(index_path, prompt)
    CorpusRetriever.reset_instance()

    try:
        build = _MOD.build_corpus_prompt_with_diagnostics(
            prompt,
            {
                "index_path": str(index_path),
                "max_snippets": 1,
                "max_chars": 1000,
                "min_score": 0.5,
            },
            mode="speed",
        )
    finally:
        CorpusRetriever.reset_instance()

    assert build.prompt.startswith("<reference_code")
    assert prompt in build.prompt
    assert build.diagnostics["injected"] is True
    assert build.diagnostics["snippets_returned"] == 1
    assert build.diagnostics["loaded"] is True
    assert build.diagnostics["format"] == "json"
    assert build.diagnostics["snippet_sources"] == [
        {
            "file": "alpha.py",
            "start_line": 10,
            "score": 1.0,
            "hash": "snippet-hash",
        }
    ]


def test_run_corpus_preflight_marks_missing_snippets_not_ready(tmp_path: Path) -> None:
    from src.services.corpus_retrieval import CorpusRetriever

    prompt = "Implement alpha_beta gamma_delta helper with retry logic."
    index_path = tmp_path / "corpus"
    _write_v1_corpus(index_path, prompt, match=False)
    CorpusRetriever.reset_instance()

    try:
        preflight = _MOD.run_corpus_preflight(
            {
                "index_path": str(index_path),
                "max_snippets": 1,
                "max_chars": 1000,
                "min_score": 0.5,
            },
            mode="speed",
            prompts=[{"id": "alpha", "prompt": prompt, "language": "python"}],
        )
    finally:
        CorpusRetriever.reset_instance()

    assert preflight["prompt_count"] == 1
    assert preflight["injected_count"] == 0
    assert preflight["failure_count"] == 0
    assert preflight["ready_for_ab"] is False
    assert preflight["records"][0]["corpus"]["snippets_returned"] == 0


def test_role_corpus_retrieval_metadata_records_forced_worker_arm() -> None:
    class FakeRegistry:
        def __init__(self, validate_paths: bool = True):
            self.validate_paths = validate_paths

        def get_corpus_config(self):
            return {"enabled": True}

        def get_role(self, role):
            enabled = role == "coder_escalation"
            return SimpleNamespace(
                acceleration=SimpleNamespace(corpus_retrieval=enabled)
            )

    metadata = _MOD._role_corpus_retrieval_metadata(
        ["coder_escalation", "worker_general"],
        models={
            "coder_escalation": {"role": "coder_escalation"},
            "worker_general": {"role": "worker_general"},
        },
        registry_loader_cls=FakeRegistry,
    )

    assert metadata["coder_escalation"]["production_role_enabled"] is True
    assert metadata["worker_general"]["production_role_enabled"] is False
    assert metadata["worker_general"]["benchmark_forces_prompt_injection"] is True


def test_run_corpus_preflight_records_selected_model_metadata(
    tmp_path: Path, monkeypatch,
) -> None:
    from src.services.corpus_retrieval import CorpusRetriever

    prompt = "Implement alpha_beta gamma_delta helper with retry logic."
    index_path = tmp_path / "corpus"
    _write_v1_corpus(index_path, prompt)
    CorpusRetriever.reset_instance()
    monkeypatch.setattr(
        _MOD,
        "_role_corpus_retrieval_metadata",
        lambda model_keys: {
            key: {
                "role": key,
                "production_runtime_enabled": True,
                "production_role_enabled": key != "worker_general",
                "benchmark_forces_prompt_injection": True,
                "status": "ok",
                "error": "",
            }
            for key in model_keys
        },
    )

    try:
        preflight = _MOD.run_corpus_preflight(
            {
                "index_path": str(index_path),
                "max_snippets": 1,
                "max_chars": 1000,
                "min_score": 0.5,
            },
            mode="speed",
            prompts=[{"id": "alpha", "prompt": prompt, "language": "python"}],
            model_keys=["coder_escalation", "worker_general"],
        )
    finally:
        CorpusRetriever.reset_instance()

    assert preflight["selected_models"] == ["coder_escalation", "worker_general"]
    assert preflight["benchmark_forces_prompt_injection"] is True
    assert (
        preflight["production_role_corpus_retrieval"]["worker_general"][
            "production_role_enabled"
        ]
        is False
    )


def _gate_args(**overrides):
    defaults = {
        "preflight_only": False,
        "dry_run": False,
        "results_only": None,
        "confirm_clean_window": False,
        "allow_active_autopilot": False,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_live_generation_refuses_without_clean_window() -> None:
    refusal = _MOD._live_generation_refusal(_gate_args())

    assert refusal is not None
    status, message = refusal
    assert status == 2
    assert "--confirm-clean-window" in message


def test_preflight_and_results_only_do_not_require_clean_window() -> None:
    assert _MOD._live_generation_refusal(_gate_args(preflight_only=True)) is None
    assert _MOD._live_generation_refusal(_gate_args(dry_run=True)) is None
    assert _MOD._live_generation_refusal(_gate_args(results_only="results.json")) is None


def test_live_generation_refuses_active_autopilot(monkeypatch) -> None:
    monkeypatch.setattr(_MOD, "_active_autopilot", lambda: True)

    refusal = _MOD._live_generation_refusal(_gate_args(confirm_clean_window=True))

    assert refusal is not None
    status, message = refusal
    assert status == 75
    assert "AutoPilot appears active" in message


def test_live_generation_allows_explicit_active_autopilot_override(monkeypatch) -> None:
    monkeypatch.setattr(_MOD, "_active_autopilot", lambda: True)

    refusal = _MOD._live_generation_refusal(
        _gate_args(confirm_clean_window=True, allow_active_autopilot=True)
    )

    assert refusal is None
