"""Prospective pin projection controls; all observations here are synthetic."""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))
from adapters import typed_decisions_measurement as adapter  # noqa: E402
import claim_tuple  # noqa: E402
from test_typed_decisions_measurement_adapter import calibration_receipt  # noqa: E402


def pin():
    return {
        "schema": "typed_decisions.llama_decision_backend.v1",
        "model_identity": [1, 2, 3, 4, 5],
        "gguf_sha256": "a" * 64,
        "model_architecture": "lfm3",
        "native_temperature_prefix": "lfm3.decision.temperature.",
        "decision_temperatures": {
            "lfm3.decision.temperature.choice": 1.25,
            "other.decision.temperature.noul": "1.5",
        },
        "server_build_commit": "abcdef123",
        "server_argv_flags": {"np": 1, "batch": 32, "ubatch": 16},
        "server_build_commit_custody": "executable_version",
        "model_path": "/synthetic/model.gguf",
        "process": {
            "pid": 1,
            "start_ticks": 2,
            "exe": "/synthetic/server",
            "argv_sha256": "c" * 64,
            "exe_identity": [1, 2],
        },
        "argv_custody": "proc_observed",
        "socket_inode": "123",
        "endpoint": "http://127.0.0.1:1234/completion",
        "endpoint_kind": "llama_completion_json",
        "transport_method": "direct_local_completion_v1",
        "decision_temperature_scaling": "not_asserted_for_json",
        "server_version": "version: 0.8.0-dev (build 12030, commit abcdef123)",
        "request_count": 1,
        "requests": [
            {
                "n_predict": 32,
                "temperature": 0.0,
                "seed": 0,
                "stream": False,
                "stop": "server_default_not_requested",
                "other_sampling": "server_default_not_requested",
                "json_schema_sha256": "b" * 64,
            }
        ],
    }


def test_legacy_remains_unknown_and_new_pin_retained_without_regrading():
    old = calibration_receipt()
    old_claim = adapter.project(adapter.native_rows(old)[0])
    assert (
        "decision_backend_pin" not in old_claim.extra and old_claim.applicability == {}
    )
    fresh = calibration_receipt(decision_backend_pin=pin())
    claim = adapter.project(adapter.native_rows(fresh)[0])
    assert claim.extra["decision_backend_pin"] == pin()
    assert claim.applicability["model_file"] == "model.gguf"
    assert claim.applicability["model_sha256"] == "a" * 64
    assert claim.applicability["build_sha"] == "abcdef123"
    assert claim.applicability["knobs"]["server_argv_np"] == 1
    assert claim.applicability["knobs"]["server_argv_batch"] == 32
    assert claim.applicability["knobs"]["server_argv_ubatch"] == 16
    assert "source_receipt_sha256" not in claim.applicability["knobs"]
    assert "backend/device are not recorded" in claim.claim
    assert claim_tuple.grade(claim) == claim_tuple.grade(old_claim)
    fresh["decision_backend_pin"]["server_argv_flags"]["np"] = 5
    assert claim.extra["decision_backend_pin"]["server_argv_flags"]["np"] == 1


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: p.update(schema="wrong"),
        lambda p: p.update(gguf_sha256="bad"),
        lambda p: p.update(model_path="relative.gguf"),
        lambda p: p.update(native_temperature_prefix="wrong"),
        lambda p: p.update(
            decision_temperatures={"x.decision.temperature.a": float("nan")}
        ),
        lambda p: p.update(server_build_commit="f" * 9),
        lambda p: p["server_argv_flags"].pop("ubatch"),
        lambda p: p["server_argv_flags"].update(np=True),
        lambda p: p.update(endpoint="https://evil:12/completion"),
        lambda p: p.update(request_count=2),
        lambda p: p["requests"][0].update(json_schema_sha256="bad"),
        lambda p: p["process"].update(pid=0),
        lambda p: p.update(argv_custody="caller_asserted"),
    ],
)
def test_present_invalid_pin_refused_at_native_boundary(mutate):
    payload = pin()
    mutate(payload)
    with pytest.raises(claim_tuple.ProjectionError, match="decision_backend_pin"):
        adapter.native_rows(calibration_receipt(decision_backend_pin=payload))


def test_null_pin_is_not_treated_as_legacy():
    with pytest.raises(claim_tuple.ProjectionError, match="decision_backend_pin"):
        adapter.native_rows(calibration_receipt(decision_backend_pin=None))
