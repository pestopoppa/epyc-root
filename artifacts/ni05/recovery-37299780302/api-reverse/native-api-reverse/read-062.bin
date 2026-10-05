from __future__ import annotations

import pytest

from scripts.validate import attest_orchestrator_workers as attest


def _write_environ(proc_root, pid: str, values: dict[str, str]) -> None:
    pid_dir = proc_root / pid
    pid_dir.mkdir(parents=True)
    payload = b"\0".join(f"{key}={value}".encode() for key, value in values.items()) + b"\0"
    (pid_dir / "environ").write_bytes(payload)


def test_build_report_accepts_matching_features_and_process_env(tmp_path) -> None:
    seen = {
        "101": {
            "pid": 101,
            "flags": {"specialist_routing": True, "model_fallback": True},
            "sources": {"specialist_routing": "ORCHESTRATOR_FEATURE_SPECIALIST_ROUTING"},
        },
        "102": {
            "pid": 102,
            "flags": {"specialist_routing": True, "model_fallback": True},
            "sources": {"specialist_routing": "ORCHESTRATOR_FEATURE_SPECIALIST_ROUTING"},
        },
    }
    _write_environ(
        tmp_path,
        "101",
        {
            "ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT": "1",
            "ORCHESTRATOR_PLACEMENT_STATE_MACHINE": "1",
        },
    )
    _write_environ(
        tmp_path,
        "102",
        {
            "ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT": "1",
            "ORCHESTRATOR_PLACEMENT_STATE_MACHINE": "1",
        },
    )

    report = attest.build_report(
        seen=seen,
        expected_features={"specialist_routing": True, "model_fallback": True},
        expected_env={
            "ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT": "1",
            "ORCHESTRATOR_PLACEMENT_STATE_MACHINE": "1",
        },
        min_workers=2,
        proc_root=tmp_path,
    )

    assert report["workers_seen"] == 2
    assert not attest.report_failed(report)


def test_build_report_fails_on_missing_worker_or_env_mismatch(tmp_path) -> None:
    seen = {
        "101": {
            "pid": 101,
            "flags": {"specialist_routing": True},
            "sources": {"specialist_routing": "ORCHESTRATOR_FEATURE_SPECIALIST_ROUTING"},
        },
    }
    _write_environ(
        tmp_path,
        "101",
        {"ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT": "0"},
    )

    report = attest.build_report(
        seen=seen,
        expected_features={"specialist_routing": True},
        expected_env={"ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT": "1"},
        min_workers=2,
        proc_root=tmp_path,
    )

    assert report["too_few_workers"] is True
    assert report["env_expected_diffs"] == [
        {
            "pid": "101",
            "env": "ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT",
            "expected": "1",
            "actual": "0",
        }
    ]
    assert attest.report_failed(report)


def test_build_report_fails_on_feature_heterogeneity(tmp_path) -> None:
    seen = {
        "101": {"pid": 101, "flags": {"model_fallback": True}, "sources": {}},
        "102": {"pid": 102, "flags": {"model_fallback": False}, "sources": {}},
    }
    _write_environ(tmp_path, "101", {})
    _write_environ(tmp_path, "102", {})

    report = attest.build_report(
        seen=seen,
        expected_features={},
        expected_env={},
        min_workers=2,
        proc_root=tmp_path,
    )

    assert report["feature_heterogeneous"] == {
        "model_fallback": {"101": True, "102": False}
    }
    assert attest.report_failed(report)


def test_parse_expectations_reject_bad_values() -> None:
    with pytest.raises(SystemExit):
        attest._parse_bool_expect(["specialist_routing=maybe"])
    with pytest.raises(SystemExit):
        attest._parse_env_expect(["ORCHESTRATOR_MOCK_MODE"])
