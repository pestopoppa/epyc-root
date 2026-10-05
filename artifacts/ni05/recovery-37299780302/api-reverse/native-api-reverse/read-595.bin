from __future__ import annotations

import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "benchmark" / "placement_fanout_probe.py"
SPEC = importlib.util.spec_from_file_location("placement_fanout_probe", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
placement_fanout_probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(placement_fanout_probe)


def test_parse_roles_preserves_single_role_default() -> None:
    assert placement_fanout_probe.parse_roles("frontdoor", None) == ["frontdoor"]


def test_parse_roles_accepts_comma_separated_override() -> None:
    assert placement_fanout_probe.parse_roles(
        "frontdoor",
        "frontdoor, ingest_long_context,worker_general",
    ) == ["frontdoor", "ingest_long_context", "worker_general"]


def test_request_roles_round_robins() -> None:
    assert placement_fanout_probe.request_roles(["frontdoor", "ingest_long_context"], 5) == [
        "frontdoor",
        "ingest_long_context",
        "frontdoor",
        "ingest_long_context",
        "frontdoor",
    ]


def test_placement_summary_preserves_legacy_primary_role_fields() -> None:
    poller = placement_fanout_probe.RegionLockPoller(
        "http://127.0.0.1:8000",
        ["frontdoor", "ingest_long_context"],
        0.1,
    )
    poller.enabled_flag = True
    poller.max_active_by_role["frontdoor"] = 1
    poller.max_active_by_role["ingest_long_context"] = 1
    poller.observed_idxs_by_role["frontdoor"].update({0})
    poller.observed_idxs_by_role["ingest_long_context"].update({2})
    poller.max_roles_active_same_sample = 2
    poller.samples.append(
        {"t": 1.0, "roles": {"frontdoor": [0], "ingest_long_context": [2]}}
    )

    summary = placement_fanout_probe._placement_summary(poller, "frontdoor")

    assert summary["per_region_locks_enabled"] is True
    assert summary["max_distinct_active_instances"] == 1
    assert summary["observed_active_instance_idxs"] == [0]
    assert summary["max_roles_active_same_sample"] == 2
    assert summary["by_role"] == {
        "frontdoor": {
            "max_distinct_active_instances": 1,
            "observed_active_instance_idxs": [0],
        },
        "ingest_long_context": {
            "max_distinct_active_instances": 1,
            "observed_active_instance_idxs": [2],
        },
    }
