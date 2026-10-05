"""Unit tests for the region_locks dashboard helpers.

Covers the three pure functions that drive the new CPU REGION LOCKS panel:
- `_shape_for_regions`: classify a region set into a column bucket.
- `_resolve_pid_to_instance_idx`: derive instance idx from the regions a
  PID currently holds (locks are acquired by uvicorn workers, not
  llama-server, so PID→instance must come from the region set).
- `_panel_shapes_from_matrix`: strict matrix-driven shape filter — the
  operator-curated `contention_matrix.yaml` same_role.instance_pairs
  is the source of truth for which shapes appear in the panel.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.api.routes import dashboard_topology
from src.api.routes.dashboard import (
    _port_role_shape,
    _region_locks_payload,
    region_locks_snapshot,
    _filter_instance_regions_for_mode,
    _shape_for_regions,
    _resolve_pid_to_instance_idx,
    _panel_shapes_from_matrix,
    _lock_root_provenance,
    _placement_telemetry_status,
)
from src.scheduling.contention import ContentionMatrix, InstancePair, Pair, SameRole

ROOT = Path(__file__).resolve().parents[2]

# Lineup-independence (2026-09-26). The stack_numa_mode filter and the
# `launch_selected` overlay read the LIVE NUMA_CONFIG for the role's
# `full_instance_idx` / instance count. The mode tests below used to name
# `worker_general` as "the multi-instance role"; the operator-signed 2026-09-22
# lineup cutover (orchestrator 860b0b2d) made it an ALIAS of frontdoor's fleet
# and deleted its NUMA_CONFIG entry, so the filter passed every instance through
# and the mode assertions failed. The role is now DERIVED: the fleet that hosts
# worker_general per orchestration/model_registry.yaml server_mode. (The 1 full
# + 4 quarters region maps those tests install stay SYNTHETIC — no live role
# carries quarters since the 2026-07-30 retirement; only the mode lookup is live.)


def _registry_server_mode() -> dict:
    import yaml

    return yaml.safe_load(
        (ROOT / "orchestration" / "model_registry.yaml").read_text(encoding="utf-8")
    )["server_mode"]


def _host_fleet_of(role: str) -> str:
    """The server_mode row that physically hosts ``role`` (shared_with/alias_of)."""
    for host, row in _registry_server_mode().items():
        if row.get("alias_of"):
            continue
        if host == role or role in (row.get("shared_with") or []):
            return host
    raise AssertionError(f"registry declares no host fleet for {role!r}")


def _mode_filtered_roles() -> tuple[list[str], list[str]]:
    """(multi, single): NUMA_CONFIG roles the mode filter splits by full_instance_idx,
    and roles it passes through whole (no full idx or a single instance)."""
    from scripts.server.stack_numa import NUMA_CONFIG

    multi, single = [], []
    for role, cfg in NUMA_CONFIG.items():
        instances = cfg.get("instances") or []
        if isinstance(cfg.get("full_instance_idx"), int) and len(instances) > 1:
            multi.append(role)
        else:
            single.append(role)
    return sorted(multi), sorted(single)


# The multi-instance fleet the mode/grid tests render (was: worker_general).
_HOST = _host_fleet_of("worker_general")


@pytest.fixture(autouse=True)
def _neutralize_realized_and_manifest_numa(monkeypatch):
    """Realized-fleet-first mode resolution (audit C1) probes localhost sockets and
    reads the host runtime-facts manifest. These grid tests drive the mode purely
    via ORCHESTRATOR_STACK_NUMA_MODE, so neutralize the two higher-precedence
    layers to keep them hermetic and env-driven (their original contract)."""
    monkeypatch.setattr(dashboard_topology, "_cached_realized_numa_mode", lambda: None)
    monkeypatch.setattr(dashboard_topology, "_fail_closed_runtime_stack_numa_mode", lambda: None)


class TestShapeForRegions:
    """Region-set → canonical column-bucket name."""

    @pytest.mark.parametrize(
        "regs,expected",
        [
            (frozenset({"q0", "q1", "q2", "q3"}), "full"),
            (frozenset({"q0", "q1"}), "half0"),
            (frozenset({"q2", "q3"}), "half1"),
            (frozenset({"q0"}), "q0"),
            (frozenset({"q1"}), "q1"),
            (frozenset({"q2"}), "q2"),
            (frozenset({"q3"}), "q3"),
        ],
    )
    def test_canonical_shapes(self, regs: frozenset, expected: str) -> None:
        assert _shape_for_regions(regs) == expected

    def test_accepts_set_or_list(self) -> None:
        assert _shape_for_regions({"q0", "q1"}) == "half0"
        assert _shape_for_regions(["q2", "q3"]) == "half1"

    def test_exotic_shape_falls_back_to_joined(self) -> None:
        # Cross-node half (q0+q2) is not a canonical shape — fallback.
        assert _shape_for_regions(frozenset({"q0", "q2"})) == "q0+q2"
        # Three-quarter shape (q0+q1+q2) — also unusual.
        assert _shape_for_regions(frozenset({"q0", "q1", "q2"})) == "q0+q1+q2"


class TestResolvePidToInstanceIdx:
    """Held-region-set → instance idx via NUMA_CONFIG match."""

    @staticmethod
    def _ingest_region_map() -> dict[str, dict[frozenset[str], int]]:
        # Matches the live ingest_long_context shape: idx 0 = half0,
        # idx 1..4 = q0..q3 quarters.
        return {
            "ingest_long_context": {
                frozenset({"q0", "q1"}): 0,
                frozenset({"q0"}): 1,
                frozenset({"q1"}): 2,
                frozenset({"q2"}): 3,
                frozenset({"q3"}): 4,
            },
        }

    def test_half0_holder_resolves_to_idx_0(self) -> None:
        """PID holding {q0, q1} of ingest_long_context → half0 instance (idx 0).

        This is the exact live case that exposed the bug: the orchestrator
        worker had both q0 and q1 locks but the old /proc-scan resolver
        couldn't see it because the worker isn't a llama-server process.
        """
        role_pid_regions = {"ingest_long_context": {"1779172": {"q0", "q1"}}}
        out = _resolve_pid_to_instance_idx(role_pid_regions, self._ingest_region_map())
        assert out == {("ingest_long_context", "1779172"): 0}

    def test_quarter_holders_resolve_individually(self) -> None:
        """Two PIDs each holding one disjoint quarter → idx 3 and idx 4."""
        role_pid_regions = {
            "ingest_long_context": {
                "alice": {"q2"},
                "bob": {"q3"},
            }
        }
        out = _resolve_pid_to_instance_idx(role_pid_regions, self._ingest_region_map())
        assert out == {
            ("ingest_long_context", "alice"): 3,
            ("ingest_long_context", "bob"): 4,
        }

    def test_full_instance_holder(self) -> None:
        region_map = {
            "worker_general": {
                frozenset({"q0", "q1", "q2", "q3"}): 0,
                frozenset({"q0"}): 1,
                frozenset({"q1"}): 2,
                frozenset({"q2"}): 3,
                frozenset({"q3"}): 4,
            },
        }
        role_pid_regions = {"worker_general": {"42": {"q0", "q1", "q2", "q3"}}}
        out = _resolve_pid_to_instance_idx(role_pid_regions, region_map)
        assert out == {("worker_general", "42"): 0}

    def test_unknown_region_set_skipped(self) -> None:
        """A PID holding regions that don't match any configured instance
        is dropped silently (could happen during a topology transition)."""
        role_pid_regions = {"ingest_long_context": {"42": {"q0", "q2"}}}  # not configured
        out = _resolve_pid_to_instance_idx(role_pid_regions, self._ingest_region_map())
        assert out == {}

    def test_unknown_role_returns_empty(self) -> None:
        role_pid_regions = {"some_other_role": {"42": {"q0"}}}
        out = _resolve_pid_to_instance_idx(role_pid_regions, self._ingest_region_map())
        assert out == {}

    def test_multiple_roles_resolve_independently(self) -> None:
        region_map = {
            "ingest_long_context": {frozenset({"q0", "q1"}): 0},
            "worker_general": {frozenset({"q0", "q1", "q2", "q3"}): 0},
        }
        role_pid_regions = {
            "ingest_long_context": {"pid-a": {"q0", "q1"}},
            "worker_general": {"pid-b": {"q0", "q1", "q2", "q3"}},
        }
        out = _resolve_pid_to_instance_idx(role_pid_regions, region_map)
        assert out == {
            ("ingest_long_context", "pid-a"): 0,
            ("worker_general", "pid-b"): 0,
        }

    def test_same_pid_holding_for_two_different_roles(self) -> None:
        """A single PID could (in principle) hold locks for two distinct
        roles concurrently. Each (role, pid) is resolved independently."""
        region_map = {
            "ingest_long_context": {frozenset({"q0"}): 1},
            "worker_general": {frozenset({"q3"}): 4},
        }
        role_pid_regions = {
            "ingest_long_context": {"7": {"q0"}},
            "worker_general": {"7": {"q3"}},
        }
        out = _resolve_pid_to_instance_idx(role_pid_regions, region_map)
        assert out == {
            ("ingest_long_context", "7"): 1,
            ("worker_general", "7"): 4,
        }


class TestPanelShapesFromMatrix:
    """Strict matrix-driven per-role shape filter.

    These fixtures mirror the actual entries in
    `orchestration/contention_matrix.yaml` as of 2026-05-26.
    """

    def test_none_returns_empty(self) -> None:
        """A role not in the matrix → no panel row."""
        assert _panel_shapes_from_matrix(None, primary_shape="full") == set()

    def test_no_instance_pairs_returns_only_primary(self) -> None:
        """ingest_long_context has `verdict: allow` but no instance_pairs
        (note explicitly says 'runs full/half in practice'). Strict result:
        only the primary shape (its idx=0 = half0) appears."""
        sr = SameRole(role="ingest_long_context", verdict="allow", note="")
        assert _panel_shapes_from_matrix(sr, primary_shape="half0") == {"half0"}

    def test_verdict_na_returns_only_primary(self) -> None:
        """architect_general / worker_vision: `verdict: n/a`, single-instance.
        Result: just the role's primary shape."""
        sr_arch = SameRole(role="architect_general", verdict="n/a")
        assert _panel_shapes_from_matrix(sr_arch, primary_shape="full") == {"full"}
        sr_wv = SameRole(role="worker_vision", verdict="n/a")
        assert _panel_shapes_from_matrix(sr_wv, primary_shape="q1") == {"q1"}

    def test_frontdoor_full_plus_quarters(self) -> None:
        """frontdoor: instance_pairs include {full,q0,q1,q2,q3}; "full"
        translates to its primary shape (half0)."""
        sr = SameRole(
            role="frontdoor",
            verdict="allow",
            instance_pairs=(
                InstancePair(a="full", b="q3"),
                InstancePair(a="q0", b="q2"),
                InstancePair(a="full", b="q2"),
                InstancePair(a="q0", b="q1"),
                InstancePair(a="q0", b="q3"),
                InstancePair(a="q1", b="q2"),
                InstancePair(a="q2", b="q3"),
                InstancePair(a="q1", b="q3"),
            ),
        )
        assert _panel_shapes_from_matrix(sr, primary_shape="half0") == {
            "half0",
            "q0",
            "q1",
            "q2",
            "q3",
        }

    def test_worker_general_strict_no_full(self) -> None:
        """Regression of the strict shape filter: with instance_pairs containing
        ONLY q+q entries (no full+q), Full is excluded even though NUMA_CONFIG
        defines a full instance.

        Note: as of 2026-05-26 the *live* worker_general YAML entry has structural
        full+qN block pairs added (so the panel surfaces a Full cell that renders
        🔒 whenever any quarter is held). This test deliberately uses a fixture
        without those entries to keep covering the no-full-pairs branch.
        """
        sr = SameRole(
            role="worker_general",
            verdict="borderline",
            instance_pairs=(
                InstancePair(a="q0", b="q1"),
                InstancePair(a="q0", b="q2"),
                InstancePair(a="q0", b="q3"),
                InstancePair(a="q1", b="q2"),
                InstancePair(a="q1", b="q3"),
                InstancePair(a="q2", b="q3"),
            ),
        )
        result = _panel_shapes_from_matrix(sr, primary_shape="full")
        assert result == {"q0", "q1", "q2", "q3"}
        assert "full" not in result, "strict: full must not appear without a full+q pair"

    def test_vision_escalation_half1_plus_quarters(self) -> None:
        """vision_escalation: primary is half1 (q2+q3, right socket);
        pairs include full+q0, full+q1 + the 6 quarter+quarter pairs."""
        sr = SameRole(
            role="vision_escalation",
            verdict="borderline",
            instance_pairs=(
                InstancePair(a="q0", b="q3"),
                InstancePair(a="q1", b="q2"),
                InstancePair(a="q0", b="q2"),
                InstancePair(a="q0", b="q1"),
                InstancePair(a="q2", b="q3"),
                InstancePair(a="q1", b="q3"),
                InstancePair(a="full", b="q0"),
                InstancePair(a="full", b="q1"),
            ),
        )
        assert _panel_shapes_from_matrix(sr, primary_shape="half1") == {
            "half1",
            "q0",
            "q1",
            "q2",
            "q3",
        }

    def test_full_alias_translates_per_role(self) -> None:
        """The matrix's "full" label means 'the role's primary instance',
        which can be a true full (worker_general), a half0 (frontdoor), or
        a half1 (vision_escalation). The translation is parameterized on
        primary_shape so each role gets the right column."""
        sr = SameRole(
            role="dummy",
            verdict="allow",
            instance_pairs=(InstancePair(a="full", b="q0"),),
        )
        assert _panel_shapes_from_matrix(sr, primary_shape="full") == {"full", "q0"}
        assert _panel_shapes_from_matrix(sr, primary_shape="half0") == {"half0", "q0"}
        assert _panel_shapes_from_matrix(sr, primary_shape="half1") == {"half1", "q0"}


def test_slots_vs_lease_role_disagreement_is_explicit_conflict() -> None:
    status = _placement_telemetry_status(
        activity={8072: {"n_active": 2, "n_total": 4}},
        port_roles={8072: "worker_general"},
        region_locks={
            "by_role": {"frontdoor": {}, "worker_general": {}},
            "occupancy": {
                "entries": [
                    {
                        "token": "frontdoor-lease",
                        "role": "frontdoor",
                        "instance_idx": 0,
                    }
                ],
            },
            "coherence": {"status": "coherent"},
        },
    )

    assert status["status"] == "conflict"
    assert status["conflict"] is True
    assert status["busy_roles"] == ["worker_general"]
    assert status["lease_roles"] == ["frontdoor"]


def test_serving_capacity_is_verified_against_live_slots() -> None:
    region_locks = {
        "by_role": {"frontdoor": {}},
        "occupancy": {
            "entries": [{"role": "frontdoor", "instance_idx": 0}],
        },
        "coherence": {"status": "coherent"},
        "lock_root": {"suspicious_test_root": False},
        "display_matrix": {
            "rows": [
                {
                    "role": "frontdoor",
                    "cells": [{"state": "active", "shape": "full", "capacity": 4}],
                }
            ],
        },
    }

    matched = _placement_telemetry_status(
        activity={8070: {"n_active": 1, "n_total": 4}},
        port_roles={8070: "frontdoor"},
        region_locks=region_locks,
    )
    assert matched["status"] == "coherent"
    assert matched["capacity_conflicts"] == []
    assert matched["capacity_observations"] == [
        {
            "role": "frontdoor",
            "shape": "full",
            "port": 8070,
            "configured": 4,
            "observed": 4,
            "matches": True,
        }
    ]

    mismatched = _placement_telemetry_status(
        activity={8070: {"n_active": 1, "n_total": 2}},
        port_roles={8070: "frontdoor"},
        region_locks=region_locks,
    )
    assert mismatched["status"] == "capacity_conflict"
    assert mismatched["capacity_conflicts"][0]["observed"] == 2
    assert mismatched["capacity_conflicts"][0]["configured"] == 4


def test_pytest_lock_root_is_explicitly_invalid_for_production(monkeypatch) -> None:
    monkeypatch.setenv("ORCHESTRATOR_TMP_DIR", "/tmp/pytest-of-node/pytest-1/live-api")

    provenance = _lock_root_provenance(Path("/tmp/pytest-of-node/pytest-1/live-api"))

    assert provenance["source"] == "ORCHESTRATOR_TMP_DIR"
    assert provenance["suspicious_test_root"] is True
    assert provenance["valid_for_production"] is False
    assert "invalid production provenance" in provenance["issue"]


class TestRegionLocksSnapshot:
    def test_instance_regions_filter_tracks_stack_numa_mode(self) -> None:
        """Run the filter over the LIVE topology: a multi-instance role keeps only
        its full in "full" mode and only its siblings in "quarter" mode; a
        single-instance role passes through in both. Roles are derived from
        NUMA_CONFIG (the same config the filter reads), never restated."""
        from scripts.server.stack_numa import NUMA_CONFIG
        from src.runtime.instance_topology import build_instance_regions

        multi, single = _mode_filtered_roles()
        # Non-vacuity: both branches of the filter must be exercised.
        assert multi and single, (multi, single)
        assert _HOST in multi

        topology = build_instance_regions(NUMA_CONFIG)
        keys = set(topology)
        full_idx = {r: NUMA_CONFIG[r]["full_instance_idx"] for r in multi}
        passthrough = {k for k in keys if k[0] not in full_idx}
        expected_full = {k for k in keys if k[0] in full_idx and k[1] == full_idx[k[0]]}
        expected_quarter = {k for k in keys if k[0] in full_idx and k[1] != full_idx[k[0]]}
        assert passthrough and expected_full and expected_quarter

        full = _filter_instance_regions_for_mode(topology, "full")
        assert set(full) == expected_full | passthrough

        quarter = _filter_instance_regions_for_mode(topology, "quarter")
        assert set(quarter) == expected_quarter | passthrough

        assert _filter_instance_regions_for_mode(topology, "both") == topology

    @pytest.mark.asyncio
    async def test_shared_occupancy_is_canonical_when_proc_role_disagrees(
        self, tmp_path, monkeypatch
    ) -> None:
        """Never combine a torn proc role with another cohort's staged load."""
        for region in ("q0", "q1", "q2", "q3"):
            (tmp_path / f"cpu_region.frontdoor.{region}.lock").write_text("")

        entries = [
            {
                "token": f"worker-{idx}",
                "pid": 9000 + idx,
                "role": "worker_general",
                "regions": ["q0", "q1", "q2", "q3"],
                "instance_idx": 0,
                "capacity": 4,
                "shared": True,
                "request_tag": f"chat-worker-{idx}",
            }
            for idx in range(2)
        ]
        occupancy = {"entries": entries, "per_region": {}}
        monkeypatch.setattr("src.runtime.cpu_region_lock._tmp_dir", lambda: tmp_path)
        monkeypatch.setattr(
            "src.runtime.cpu_region_lock._current_lock_owner_pids",
            lambda path: ["777"] if ".frontdoor." in path.name else [],
        )
        monkeypatch.setattr("src.runtime.cpu_region_lock.read_region_occupancy", lambda: occupancy)
        monkeypatch.setattr(
            "src.runtime.instance_topology.get_instance_regions",
            lambda: {
                ("frontdoor", 0): frozenset({"q0", "q1", "q2", "q3"}),
                ("worker_general", 0): frozenset({"q0", "q1", "q2", "q3"}),
            },
        )
        monkeypatch.setattr(
            "src.scheduling.contention.load_contention_matrix",
            lambda: type(
                "Matrix",
                (),
                {
                    "same_role": {
                        "frontdoor": SameRole(role="frontdoor", verdict="allow"),
                        "worker_general": SameRole(role="worker_general", verdict="allow"),
                    },
                },
            )(),
        )

        payload = json.loads((await region_locks_snapshot()).body)

        assert payload["by_role"]["frontdoor"]["proc_active_instance_idxs"] == [0]
        assert payload["by_role"]["frontdoor"]["active_instance_idxs"] == []
        assert payload["by_role"]["worker_general"]["active_instance_idxs"] == [0]
        rows = {row["role"]: row for row in payload["display_matrix"]["rows"]}
        assert rows["worker_general"]["cells"][0]["label"] == "⚡ 2/4"
        assert rows["frontdoor"]["cells"][0]["state"] == "blocked"
        assert payload["coherence"]["status"] == "mismatch"
        assert payload["coherence"]["proc_pairs"] == [["frontdoor", 0]]
        assert payload["coherence"]["occupancy_pairs"] == [["worker_general", 0]]

    @pytest.mark.asyncio
    async def test_region_snapshot_retries_when_occupancy_changes_during_proc_scan(
        self, tmp_path, monkeypatch
    ) -> None:
        first = {
            "entries": [
                {
                    "token": "departing",
                    "pid": 123,
                    "role": "frontdoor",
                    "regions": ["q0"],
                    "instance_idx": 0,
                    "capacity": 1,
                    "shared": False,
                }
            ],
            "per_region": {},
        }
        empty = {"entries": [], "per_region": {}}
        observations = iter((first, empty, empty, empty))
        calls = 0

        def read_occupancy():
            nonlocal calls
            calls += 1
            return next(observations)

        monkeypatch.setattr("src.runtime.cpu_region_lock._tmp_dir", lambda: tmp_path)
        monkeypatch.setattr(
            "src.runtime.cpu_region_lock._current_lock_owner_pids", lambda _path: []
        )
        monkeypatch.setattr("src.runtime.cpu_region_lock.read_region_occupancy", read_occupancy)
        monkeypatch.setattr(
            "src.runtime.instance_topology.get_instance_regions",
            lambda: {("frontdoor", 0): frozenset({"q0"})},
        )
        monkeypatch.setattr(
            "src.scheduling.contention.load_contention_matrix",
            lambda: type(
                "Matrix",
                (),
                {"same_role": {"frontdoor": SameRole(role="frontdoor", verdict="allow")}},
            )(),
        )

        payload = json.loads((await region_locks_snapshot()).body)

        assert calls == 4
        assert payload["coherence"]["status"] == "coherent"
        assert payload["coherence"]["retries"] == 1
        assert payload["occupancy"]["entries"] == []

    @pytest.mark.asyncio
    async def test_region_lock_grid_keeps_configured_quarters_visible_in_full_mode(
        self, tmp_path, monkeypatch
    ) -> None:
        monkeypatch.setenv("ORCHESTRATOR_STACK_NUMA_MODE", "full")
        for region in ("q0", "q1", "q2", "q3"):
            (tmp_path / f"cpu_region.{_HOST}.{region}.lock").write_text("")

        monkeypatch.setattr("src.runtime.cpu_region_lock._tmp_dir", lambda: tmp_path)
        monkeypatch.setattr(
            "src.runtime.cpu_region_lock._current_lock_owner_pids", lambda _path: ["wg-full"]
        )
        monkeypatch.setattr(
            "src.runtime.instance_topology.get_instance_regions",
            lambda: {
                (_HOST, 0): frozenset({"q0", "q1", "q2", "q3"}),
                (_HOST, 1): frozenset({"q0"}),
                (_HOST, 2): frozenset({"q1"}),
                (_HOST, 3): frozenset({"q2"}),
                (_HOST, 4): frozenset({"q3"}),
            },
        )
        monkeypatch.setattr(
            "src.scheduling.contention.load_contention_matrix",
            lambda: type(
                "Matrix",
                (),
                {
                    "same_role": {
                        _HOST: SameRole(role=_HOST, verdict="allow"),
                    },
                },
            )(),
        )

        payload = json.loads((await region_locks_snapshot()).body)

        worker = payload["by_role"][_HOST]
        assert payload["stack_numa_mode"] == "full"
        assert [inst["shape"] for inst in worker["instances"]] == [
            "full",
            "q0",
            "q1",
            "q2",
            "q3",
        ]
        assert [inst["launch_selected"] for inst in worker["instances"]] == [
            True,
            False,
            False,
            False,
            False,
        ]
        assert worker["active_instance_idxs"] == [0]
        assert payload["display_matrix"]["active_holder_count"] == 1
        assert payload["display_matrix"]["topology_mode"] == "all_configured"
        assert payload["display_matrix"]["launch_mode"] == "full"
        assert payload["display_matrix"]["row_kind"] == "role"
        assert payload["display_matrix"]["role_count"] == 1
        worker_display = next(
            row for row in payload["display_matrix"]["rows"] if row["role"] == _HOST
        )
        # The grid renders one column per DEPLOYABLE SHAPE (bc1da61f: quarters
        # were retired as a deployable shape on 2026-07-30, so a column per
        # quarter implied four deployable instances per role). Derive the cell
        # expectation from the payload's own declared columns instead of a fixed
        # 7-element literal, and pin the shape contract itself.
        columns = [col["key"] for col in payload["display_matrix"]["columns"]]
        assert columns == ["full", "half0", "half1"]
        states = [cell["state"] for cell in worker_display["cells"]]
        labels = [cell["label"] for cell in worker_display["cells"]]
        # Full is ACTIVE (it holds all four regions); this synthetic topology
        # declares q0..q3 and no half shapes, so every other column is "na".
        assert states == ["active"] + ["na"] * (len(columns) - 1)
        assert labels == ["⚡"] + ["—"] * (len(columns) - 1)
        # The quarter granularity the columns no longer show is NOT lost: it is
        # still carried per-instance and per-region for anything that needs the
        # atomic view (the guarantee the source comment makes).
        assert [inst["shape"] for inst in worker["instances"][1:]] == ["q0", "q1", "q2", "q3"]
        assert {str(r["region"]) for r in worker["regions"]} == {"q0", "q1", "q2", "q3"}

    @pytest.mark.asyncio
    async def test_region_lock_grid_renders_unselected_free_quarters_as_ready(
        self, tmp_path, monkeypatch
    ) -> None:
        monkeypatch.setenv("ORCHESTRATOR_STACK_NUMA_MODE", "full")

        monkeypatch.setattr("src.runtime.cpu_region_lock._tmp_dir", lambda: tmp_path)
        monkeypatch.setattr(
            "src.runtime.cpu_region_lock._current_lock_owner_pids", lambda _path: []
        )
        monkeypatch.setattr(
            "src.runtime.instance_topology.get_instance_regions",
            lambda: {
                (_HOST, 0): frozenset({"q0", "q1", "q2", "q3"}),
                (_HOST, 1): frozenset({"q0"}),
                (_HOST, 2): frozenset({"q1"}),
                (_HOST, 3): frozenset({"q2"}),
                (_HOST, 4): frozenset({"q3"}),
            },
        )
        monkeypatch.setattr(
            "src.scheduling.contention.load_contention_matrix",
            lambda: type(
                "Matrix",
                (),
                {
                    "same_role": {
                        _HOST: SameRole(role=_HOST, verdict="allow"),
                    },
                },
            )(),
        )

        payload = json.loads((await region_locks_snapshot()).body)

        worker_display = next(
            row for row in payload["display_matrix"]["rows"] if row["role"] == _HOST
        )
        columns = [col["key"] for col in payload["display_matrix"]["columns"]]
        assert columns == ["full", "half0", "half1"]
        # A configured, unheld shape reads "ready" — never "blocked", never
        # hidden. Shapes with no matching instance in this synthetic topology
        # read "na".
        assert [cell["state"] for cell in worker_display["cells"]] == ["ready"] + ["na"] * (
            len(columns) - 1
        )
        assert [cell["label"] for cell in worker_display["cells"]] == ["✅"] + ["—"] * (
            len(columns) - 1
        )

        # "configured quarters stay visible" — the property this test is named
        # for — is now enforced at the layer that still models quarters: the
        # unselected quarter instances are present with launch_selected False.
        worker = payload["by_role"][_HOST]
        unselected = [i for i in worker["instances"] if not i["launch_selected"]]
        assert [i["shape"] for i in unselected] == ["q0", "q1", "q2", "q3"]
        # The rendered FREE cell is the launch-SELECTED full in this mode, so it
        # carries the region list and no "not selected" annotation. (The
        # annotation path itself is covered by
        # test_region_lock_grid_shapes_follow_quarter_mode, where the full is the
        # unselected shape.)
        full_title = worker_display["cells"][0]["title"]
        assert worker["instances"][0]["launch_selected"] is True
        assert "FREE" in full_title and "q0,q1,q2,q3" in full_title
        assert "not selected by stack_numa_mode" not in full_title

    @pytest.mark.asyncio
    async def test_region_lock_grid_shapes_follow_quarter_mode(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv("ORCHESTRATOR_STACK_NUMA_MODE", "quarter")
        (tmp_path / f"cpu_region.{_HOST}.q0.lock").write_text("")

        monkeypatch.setattr("src.runtime.cpu_region_lock._tmp_dir", lambda: tmp_path)
        monkeypatch.setattr(
            "src.runtime.cpu_region_lock._current_lock_owner_pids", lambda _path: ["wg-q0"]
        )
        monkeypatch.setattr(
            "src.runtime.instance_topology.get_instance_regions",
            lambda: {
                (_HOST, 0): frozenset({"q0", "q1", "q2", "q3"}),
                (_HOST, 1): frozenset({"q0"}),
                (_HOST, 2): frozenset({"q1"}),
                (_HOST, 3): frozenset({"q2"}),
                (_HOST, 4): frozenset({"q3"}),
            },
        )
        monkeypatch.setattr(
            "src.scheduling.contention.load_contention_matrix",
            lambda: type(
                "Matrix",
                (),
                {
                    "same_role": {
                        _HOST: SameRole(
                            role=_HOST,
                            verdict="allow",
                            instance_pairs=(InstancePair(a="q0", b="q1"),),
                        ),
                    },
                },
            )(),
        )

        payload = json.loads((await region_locks_snapshot()).body)

        worker = payload["by_role"][_HOST]
        assert payload["stack_numa_mode"] == "quarter"
        # Visible shapes follow the role's CONFIGURED quarter instances (all four),
        # plus the inactive full instance. The matrix's co-placement pairs are
        # not a visibility filter — every configured server is shown.
        assert [inst["shape"] for inst in worker["instances"]] == [
            "full",
            "q0",
            "q1",
            "q2",
            "q3",
        ]
        assert [inst["launch_selected"] for inst in worker["instances"]] == [
            False,
            True,
            True,
            True,
            True,
        ]
        assert worker["active_instance_idxs"] == [1]

    @pytest.mark.asyncio
    async def test_empty_region_embedder_is_not_a_cpu_lock_panel_role(
        self,
        tmp_path,
        monkeypatch,
    ) -> None:
        """Embedding servers have no physical CPU-region lock footprint.

        They are monitored by topology/activity, but the CPU-region lock panel
        should remain limited to roles that can actually acquire q0..q3 locks.
        """
        (tmp_path / "cpu_region.embedder.q0.lock").write_text("")

        monkeypatch.setattr("src.runtime.cpu_region_lock._tmp_dir", lambda: tmp_path)
        monkeypatch.setattr(
            "src.runtime.cpu_region_lock._current_lock_owner_pids", lambda _path: ["embed-pid"]
        )
        monkeypatch.setattr(
            "src.runtime.instance_topology.get_instance_regions",
            lambda: {
                ("embedder", 0): frozenset(),
                ("frontdoor", 0): {"q0", "q1"},
                ("frontdoor", 1): {"q0"},
            },
        )
        monkeypatch.setattr(
            "src.scheduling.contention.load_contention_matrix",
            lambda: type(
                "Matrix",
                (),
                {
                    "same_role": {
                        "embedder": SameRole(role="embedder", verdict="n/a"),
                        "frontdoor": SameRole(role="frontdoor", verdict="allow"),
                    },
                },
            )(),
        )

        response = await region_locks_snapshot()
        payload = json.loads(response.body)

        assert "embedder" not in payload["by_role"]
        assert "embedder" not in payload["topology_quartered_roles"]
        assert "frontdoor" in payload["by_role"]

    @pytest.mark.asyncio
    async def test_pair_measured_roles_appear_without_same_role_entries(
        self, tmp_path, monkeypatch
    ) -> None:
        """Cross-role measurements establish panel membership for CPU roles."""
        monkeypatch.setattr("src.runtime.cpu_region_lock._tmp_dir", lambda: tmp_path)
        monkeypatch.setattr(
            "src.runtime.cpu_region_lock._current_lock_owner_pids", lambda _path: []
        )
        monkeypatch.setattr(
            "src.runtime.instance_topology.get_instance_regions",
            lambda: {
                ("architect_general", 0): {"q0", "q1", "q2", "q3"},
                ("worker_vision", 0): {"q1"},
                ("vision_escalation", 0): {"q3"},
                ("frontdoor", 0): {"q0", "q1"},
            },
        )
        matrix = ContentionMatrix(
            version=1,
            measured_at="test",
            host="test",
            topology_hash="test",
            default_floor=0.85,
            same_role={},
            pairs={
                tuple(sorted(("architect_general", "worker_vision"))): Pair(
                    roles=tuple(sorted(("architect_general", "worker_vision"))),
                    ratio=1.0,
                    verdict="allow",
                ),
                tuple(sorted(("vision_escalation", "worker_vision"))): Pair(
                    roles=tuple(sorted(("vision_escalation", "worker_vision"))),
                    ratio=1.0,
                    verdict="allow",
                ),
            },
        )
        monkeypatch.setattr("src.scheduling.contention.load_contention_matrix", lambda: matrix)

        payload = json.loads((await region_locks_snapshot()).body)

        assert set(payload["by_role"]) == {
            "architect_general",
            "worker_vision",
            "vision_escalation",
        }
        assert "frontdoor" not in payload["by_role"]
        assert [inst["shape"] for inst in payload["by_role"]["architect_general"]["instances"]] == [
            "full"
        ]
        assert [inst["shape"] for inst in payload["by_role"]["worker_vision"]["instances"]] == [
            "q1"
        ]

    @pytest.mark.asyncio
    async def test_runtime_holder_outside_matrix_visible_shapes_resolves(
        self, tmp_path, monkeypatch
    ) -> None:
        """Runtime locks resolve against full topology, not just panel-visible shapes."""
        monkeypatch.setenv("ORCHESTRATOR_STACK_NUMA_MODE", "both")
        lock = tmp_path / "cpu_region.ingest_long_context.q2.lock"
        lock.write_text("")

        monkeypatch.setattr("src.runtime.cpu_region_lock._tmp_dir", lambda: tmp_path)
        monkeypatch.setattr(
            "src.runtime.cpu_region_lock._current_lock_owner_pids", lambda _path: ["2928025"]
        )
        monkeypatch.setattr(
            "src.runtime.instance_topology.get_instance_regions",
            lambda: {
                ("ingest_long_context", 0): {"q0", "q1"},
                ("ingest_long_context", 3): {"q2"},
            },
        )
        monkeypatch.setattr(
            "src.scheduling.contention.load_contention_matrix",
            lambda: type(
                "Matrix",
                (),
                {
                    "same_role": {
                        "ingest_long_context": SameRole(
                            role="ingest_long_context",
                            verdict="allow",
                        ),
                    },
                },
            )(),
        )

        response = await region_locks_snapshot()
        payload = json.loads(response.body)

        ingest = payload["by_role"]["ingest_long_context"]
        assert ingest["active_instance_idxs"] == [3]
        # The held q2 quarter resolves to idx 3 and appears as a first-class
        # configured instance now that visible shapes follow the role's configured
        # instances (it is no longer an "outside-matrix" runtime_only-only holder).
        assert any(inst["idx"] == 3 and inst["shape"] == "q2" for inst in ingest["instances"])
        held = [r for r in ingest["regions"] if r["held"]]
        assert held == [
            {
                "region": "q2",
                "held": True,
                "holder_pids": ["2928025"],
                "holder_instance_idxs": [3],
            }
        ]

    @pytest.mark.asyncio
    async def test_lock_payload_instance_idx_wins_over_region_set_fallback(
        self,
        tmp_path,
        monkeypatch,
    ) -> None:
        """JSON payload under the flock is the direct instance attribution path."""
        monkeypatch.setenv("ORCHESTRATOR_STACK_NUMA_MODE", "both")
        lock = tmp_path / "cpu_region.frontdoor.q0.lock"
        lock.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "pid": 12345,
                    "role": "frontdoor",
                    "region": "q0",
                    "regions": ["q0", "q1"],
                    "instance_idx": 0,
                    "request_tag": "chat-unit",
                    "started_at": 1000.0,
                }
            )
        )

        monkeypatch.setattr("src.runtime.cpu_region_lock._tmp_dir", lambda: tmp_path)
        monkeypatch.setattr(
            "src.runtime.cpu_region_lock._current_lock_owner_pids",
            lambda _path: ["12345"],
        )
        monkeypatch.setattr(
            "src.runtime.instance_topology.get_instance_regions",
            lambda: {
                ("frontdoor", 0): {"q0", "q1"},
                ("frontdoor", 1): {"q0"},
                ("frontdoor", 2): {"q1"},
            },
        )
        monkeypatch.setattr(
            "src.scheduling.contention.load_contention_matrix",
            lambda: type(
                "Matrix",
                (),
                {
                    "same_role": {
                        "frontdoor": SameRole(role="frontdoor", verdict="allow"),
                    },
                },
            )(),
        )

        payload = json.loads((await region_locks_snapshot()).body)

        frontdoor = payload["by_role"]["frontdoor"]
        assert frontdoor["active_instance_idxs"] == [0]
        held = [r for r in frontdoor["regions"] if r["held"]]
        assert held == [
            {
                "region": "q0",
                "held": True,
                "holder_pids": ["12345"],
                "holder_instance_idxs": [0],
                "lock_payload": {
                    "schema_version": 1,
                    "pid": 12345,
                    "role": "frontdoor",
                    "region": "q0",
                    "regions": ["q0", "q1"],
                    "instance_idx": 0,
                    "request_tag": "chat-unit",
                    "started_at": 1000.0,
                },
            }
        ]

    @pytest.mark.asyncio
    async def test_blocked_by_roles_uses_contention_matrix_not_raw_overlap(
        self, tmp_path, monkeypatch
    ) -> None:
        """Admission metadata still distinguishes allowed and queued cross-role pairs."""
        for region in ("q0", "q1", "q2", "q3"):
            (tmp_path / f"cpu_region.worker_general.{region}.lock").write_text("")

        monkeypatch.setattr("src.runtime.cpu_region_lock._tmp_dir", lambda: tmp_path)
        monkeypatch.setattr(
            "src.runtime.cpu_region_lock._current_lock_owner_pids", lambda _path: ["wg-pid"]
        )
        monkeypatch.setattr(
            "src.runtime.instance_topology.get_instance_regions",
            lambda: {
                ("worker_general", 0): {"q0", "q1", "q2", "q3"},
                ("worker_general", 1): {"q0"},
                ("ingest_long_context", 0): {"q0", "q1"},
                ("architect_general", 0): {"q0", "q1", "q2", "q3"},
            },
        )
        matrix = ContentionMatrix(
            version=1,
            measured_at="test",
            host="test",
            topology_hash="test",
            default_floor=0.85,
            same_role={
                "worker_general": SameRole(role="worker_general", verdict="allow"),
                "ingest_long_context": SameRole(role="ingest_long_context", verdict="allow"),
                "architect_general": SameRole(role="architect_general", verdict="n/a"),
            },
            pairs={
                tuple(sorted(("ingest_long_context", "worker_general"))): Pair(
                    roles=tuple(sorted(("ingest_long_context", "worker_general"))),
                    ratio=1.087,
                    verdict="allow",
                ),
                tuple(sorted(("architect_general", "worker_general"))): Pair(
                    roles=tuple(sorted(("architect_general", "worker_general"))),
                    ratio=0.50,
                    verdict="block",
                ),
            },
        )
        monkeypatch.setattr("src.scheduling.contention.load_contention_matrix", lambda: matrix)

        response = await region_locks_snapshot()
        payload = json.loads(response.body)

        assert payload["by_role"]["worker_general"]["blocked_by_roles"] == ["worker_general"]
        assert payload["by_role"]["ingest_long_context"]["blocked_by_roles"] == []
        assert payload["by_role"]["architect_general"]["blocked_by_roles"] == ["worker_general"]

    @pytest.mark.asyncio
    async def test_two_worker_halves_lock_every_overlapping_display_shape(
        self, tmp_path, monkeypatch
    ) -> None:
        """Two half-machine leases occupy all regions even for matrix-allowed roles."""
        occupancy = {
            "entries": [
                {
                    "token": "worker-half0",
                    "pid": 9001,
                    "role": "worker_general",
                    "regions": ["q0", "q1"],
                    "instance_idx": 1,
                    "capacity": 1,
                    "shared": False,
                },
                {
                    "token": "worker-half1",
                    "pid": 9002,
                    "role": "worker_general",
                    "regions": ["q2", "q3"],
                    "instance_idx": 2,
                    "capacity": 1,
                    "shared": False,
                },
            ],
            "per_region": {},
        }
        monkeypatch.setattr("src.runtime.cpu_region_lock._tmp_dir", lambda: tmp_path)
        monkeypatch.setattr(
            "src.runtime.cpu_region_lock._current_lock_owner_pids", lambda _path: []
        )
        monkeypatch.setattr("src.runtime.cpu_region_lock.read_region_occupancy", lambda: occupancy)
        monkeypatch.setattr(
            "src.runtime.instance_topology.get_instance_regions",
            lambda: {
                (role, idx): regions
                for role in (
                    "architect_critic",
                    "frontdoor",
                    "ingest_long_context",
                    "worker_general",
                )
                for idx, regions in (
                    (0, frozenset({"q0", "q1", "q2", "q3"})),
                    (1, frozenset({"q0", "q1"})),
                    (2, frozenset({"q2", "q3"})),
                )
            },
        )
        roles = {
            role: SameRole(role=role, verdict="allow")
            for role in (
                "architect_critic",
                "frontdoor",
                "ingest_long_context",
                "worker_general",
            )
        }
        allowed_pairs = {
            tuple(sorted((role, "worker_general"))): Pair(
                roles=tuple(sorted((role, "worker_general"))),
                ratio=1.0,
                verdict="allow",
            )
            for role in ("architect_critic", "frontdoor", "ingest_long_context")
        }
        matrix = ContentionMatrix(
            version=1,
            measured_at="test",
            host="test",
            topology_hash="test",
            default_floor=0.85,
            same_role=roles,
            pairs=allowed_pairs,
        )
        monkeypatch.setattr("src.scheduling.contention.load_contention_matrix", lambda: matrix)
        monkeypatch.setattr("src.api.routes.dashboard._port_roles_cached", lambda: {})

        payload = json.loads((await region_locks_snapshot()).body)

        rows = {row["role"]: row for row in payload["display_matrix"]["rows"]}
        assert [cell["state"] for cell in rows["worker_general"]["cells"]] == [
            "blocked",
            "active",
            "active",
        ]
        for role in ("architect_critic", "frontdoor", "ingest_long_context"):
            assert [cell["state"] for cell in rows[role]["cells"]] == [
                "blocked",
                "blocked",
                "blocked",
            ]
            assert all("LOCKED" in cell["title"] for cell in rows[role]["cells"])

    @pytest.mark.asyncio
    async def test_frontdoor_full_locks_all_cpu_models_and_shows_serving_capacity(
        self, tmp_path, monkeypatch
    ) -> None:
        """Exact live regression: frontdoor.full occupies q0-q3 and has four slots."""
        occupancy = {
            "entries": [
                {
                    "token": "frontdoor-full",
                    "pid": 9100,
                    "role": "frontdoor",
                    "regions": ["q0", "q1", "q2", "q3"],
                    "instance_idx": 0,
                    # Ordinary traffic owns one EXCLUSIVE placement lease even
                    # though the selected llama-server exposes four slots.
                    "capacity": 1,
                    "shared": False,
                }
            ],
            "per_region": {},
        }
        monkeypatch.setattr("src.runtime.cpu_region_lock._tmp_dir", lambda: tmp_path)
        monkeypatch.setattr(
            "src.runtime.cpu_region_lock._current_lock_owner_pids", lambda _path: []
        )
        monkeypatch.setattr("src.runtime.cpu_region_lock.read_region_occupancy", lambda: occupancy)
        monkeypatch.setattr(
            "src.runtime.instance_topology.get_instance_regions",
            lambda: {
                (role, idx): regions
                for role in (
                    "architect_critic",
                    "frontdoor",
                    "ingest_long_context",
                    "worker_general",
                )
                for idx, regions in (
                    (0, frozenset({"q0", "q1", "q2", "q3"})),
                    (1, frozenset({"q0", "q1"})),
                    (2, frozenset({"q2", "q3"})),
                )
                if role != "architect_critic" or idx == 0
            },
        )
        roles = {
            role: SameRole(role=role, verdict="allow")
            for role in (
                "architect_critic",
                "frontdoor",
                "ingest_long_context",
                "worker_general",
            )
        }
        matrix = ContentionMatrix(
            version=1,
            measured_at="test",
            host="test",
            topology_hash="test",
            default_floor=0.85,
            same_role=roles,
            pairs={
                tuple(sorted((role, "frontdoor"))): Pair(
                    roles=tuple(sorted((role, "frontdoor"))),
                    ratio=1.0,
                    verdict="allow",
                )
                for role in (
                    "architect_critic",
                    "ingest_long_context",
                    "worker_general",
                )
            },
        )
        monkeypatch.setattr("src.scheduling.contention.load_contention_matrix", lambda: matrix)
        monkeypatch.setattr("src.api.routes.dashboard._port_roles_cached", lambda: {})

        payload = json.loads((await region_locks_snapshot()).body)

        rows = {row["role"]: row for row in payload["display_matrix"]["rows"]}
        active = rows["frontdoor"]["cells"][0]
        assert active["state"] == "active"
        assert active["label"] == "⚡ 1/4"
        assert active["capacity"] == 4
        assert active["lease_capacity"] == 1
        assert "1 of 4 configured serving slot(s)" in active["title"]
        assert "placement lease admission capacity=1" in active["title"]
        assert [cell["state"] for cell in rows["frontdoor"]["cells"][1:]] == [
            "blocked",
            "blocked",
        ]
        assert rows["architect_critic"]["cells"][0]["state"] == "blocked"
        for role in ("ingest_long_context", "worker_general"):
            assert [cell["state"] for cell in rows[role]["cells"]] == [
                "blocked",
                "blocked",
                "blocked",
            ]


class TestNonLockRoleCompleteness:
    """Task D (2026-07-26): the panel must show ALL active serving instances,
    not only lock-domain (matrix-measured) roles — roles with no lock domain
    render display-only rows with lock state "n/a (no lock domain)"."""

    @staticmethod
    def _manifest_speech_roles() -> dict[str, int]:
        """Speech rows the panel folds in, DERIVED from the two sources it reads.

        bc1da61f folds whisper/tts in from the launch manifest because they are
        not llama-server processes, so ps(1) port discovery never sees them and
        they were invisible in the panel since going live on the MI210 on
        2026-08-02. Reading `_SPEECH_ROLES` and `AUX_SERVICES` here keeps the
        expectation honest if another speech service is declared later.
        """
        from scripts.server.stack_manifest import AUX_SERVICES

        import src.api.routes.dashboard as dash_mod

        return {
            str(getattr(svc, "name", "")): int(svc.port)
            for svc in AUX_SERVICES.values()
            if str(getattr(svc, "name", "")) in dash_mod._SPEECH_ROLES
            and isinstance(getattr(svc, "port", None), int)
        }

    @staticmethod
    def _base_env(tmp_path, monkeypatch) -> None:
        monkeypatch.setattr("src.runtime.cpu_region_lock._tmp_dir", lambda: tmp_path)
        monkeypatch.setattr(
            "src.runtime.cpu_region_lock._current_lock_owner_pids", lambda _path: []
        )
        monkeypatch.setattr(
            "src.runtime.instance_topology.get_instance_regions",
            lambda: {
                ("worker_general", 0): frozenset({"q0", "q1", "q2", "q3"}),
                ("worker_general", 1): frozenset({"q0"}),
                ("architect_general", 0): frozenset({"q0", "q1", "q2", "q3"}),
            },
        )
        matrix = ContentionMatrix(
            version=1,
            measured_at="test",
            host="test",
            topology_hash="test",
            default_floor=0.85,
            same_role={"worker_general": SameRole(role="worker_general", verdict="allow")},
            pairs={},
        )
        monkeypatch.setattr("src.scheduling.contention.load_contention_matrix", lambda: matrix)

    @pytest.mark.asyncio
    async def test_non_lock_roles_rendered_with_na_lock_state(self, tmp_path, monkeypatch) -> None:
        self._base_env(tmp_path, monkeypatch)
        import src.api.routes.dashboard as dash_mod

        monkeypatch.setattr(
            dash_mod,
            "_port_roles_cached",
            lambda: {
                8080: "worker_general",
                8081: "worker_general.q0",  # quarter lane folds onto its base role
                8090: "embedder",
                9101: "coder_escalation",
            },
        )

        payload = json.loads((await region_locks_snapshot()).body)

        speech = self._manifest_speech_roles()
        assert speech, "no speech service declared in AUX_SERVICES"

        # Lock-domain role keeps its normal lock row.
        assert "worker_general" in payload["by_role"]
        # Every other active/configured serving role appears as a non-lock row —
        # including the manifest-sourced speech services, which ps(1) discovery
        # can never see.
        nlr = payload["non_lock_roles"]
        assert set(nlr) == {
            "architect_general",
            "embedder",
            "coder_escalation",
        } | set(speech)
        for info in nlr.values():
            assert info["lock_state"] == "n/a (no lock domain)"
        for name, port in speech.items():
            assert nlr[name]["ports"] == [port]
        # Configured full instance rides along with its shape/regions.
        assert [i["shape"] for i in nlr["architect_general"]["instances"]] == ["full"]
        assert nlr["architect_general"]["instances"][0]["regions"] == ["q0", "q1", "q2", "q3"]
        # Port-only roles (embedders, aliases) show their ports even with no NUMA shape.
        assert nlr["embedder"]["ports"] == [8090]
        assert nlr["embedder"]["instances"] == []
        assert nlr["coder_escalation"]["ports"] == [9101]
        # The quarter lane never spawns a duplicate row for a lock-domain role.
        assert "worker_general.q0" not in nlr and "worker_general" not in nlr

        rows = {r["role"]: r for r in payload["display_matrix"]["rows"]}
        # The embedder pool / eval-batch lane are hidden from DISPLAY only
        # (bc1da61f: 7 all-dash rows buried the roles that matter). The payload
        # contract is that hiding is display-only, so `embedder` must be absent
        # from the grid rows AND present in `non_lock_roles` above — pinning both
        # halves is what stops "legible" from silently becoming "lossy".
        assert "embedder" not in rows
        # Shaped non-lock role: the n/a cell sits in its configured shape column.
        arch_cells = rows["architect_general"]["cells"]
        assert arch_cells[0]["state"] == "nolock"  # column 0 == "full"
        assert "q0,q1,q2,q3" in arch_cells[0]["title"]
        # Lock-domain display rows are untouched (no display-only marker).
        assert "no_lock_domain" not in rows["worker_general"]

    @pytest.mark.asyncio
    async def test_non_lock_roles_fail_open_on_port_discovery_error(
        self, tmp_path, monkeypatch
    ) -> None:
        """Broken ps discovery must not break the panel: lock rows render,
        and configured-but-unmatched roles still appear (with no ports).

        The manifest-sourced speech rows survive too — they come from
        AUX_SERVICES, a source INDEPENDENT of ps(1) discovery, so a discovery
        outage must not make the panel LESS accurate. Their expected names are
        derived from the same two sources the code reads.
        """
        self._base_env(tmp_path, monkeypatch)
        import src.api.routes.dashboard as dash_mod

        def _boom() -> dict[int, str]:
            raise RuntimeError("ps scan failed")

        monkeypatch.setattr(dash_mod, "_port_roles_cached", _boom)

        payload = json.loads((await region_locks_snapshot()).body)

        speech = self._manifest_speech_roles()
        assert speech, "no speech service declared in AUX_SERVICES"

        assert "worker_general" in payload["by_role"]
        assert set(payload["non_lock_roles"]) == {"architect_general"} | set(speech)
        assert payload["non_lock_roles"]["architect_general"]["ports"] == []
        # Ports prove the speech rows came from the manifest, not from the
        # failed discovery path.
        for name, port in speech.items():
            assert payload["non_lock_roles"][name]["ports"] == [port]


def test_auxiliary_occupancy_is_rendered_and_blocks_every_overlapping_shape(
    tmp_path, monkeypatch
) -> None:
    topology = {
        ("frontdoor", 0): frozenset({"q0", "q1", "q2", "q3"}),
        ("frontdoor", 1): frozenset({"q0", "q1"}),
        ("frontdoor", 2): frozenset({"q2", "q3"}),
        ("worker_general", 0): frozenset({"q0", "q1", "q2", "q3"}),
        ("worker_general", 1): frozenset({"q0", "q1"}),
        ("worker_general", 2): frozenset({"q2", "q3"}),
        ("eval_batch_frontdoor", 0): frozenset({"q0", "q1"}),
    }
    occupancy = {
        "entries": [
            {
                "token": "eval-lease",
                "pid": 101,
                "role": "eval_batch_frontdoor",
                "regions": ["q0", "q1"],
                "instance_idx": 0,
                "capacity": 2,
                "shared": True,
            },
            {
                "token": "worker-lease",
                "pid": 102,
                "role": "worker_general",
                "regions": ["q2", "q3"],
                "instance_idx": 2,
                "capacity": 1,
                "shared": False,
            },
        ],
        "per_region": {},
    }
    for role, regions in {
        "eval_batch_frontdoor": ("q0", "q1"),
        "worker_general": ("q2", "q3"),
    }.items():
        for region in regions:
            (tmp_path / f"cpu_region.{role}.{region}.lock").write_text("")

    def holders(path: Path) -> list[str]:
        return ["101"] if ".eval_batch_frontdoor." in path.name else ["102"]

    matrix = ContentionMatrix(
        version=1,
        measured_at="test",
        host="test",
        topology_hash="test",
        default_floor=0.85,
        same_role={
            "frontdoor": SameRole(role="frontdoor", verdict="allow"),
            "worker_general": SameRole(role="worker_general", verdict="allow"),
        },
        pairs={},
    )
    monkeypatch.setattr("src.runtime.cpu_region_lock._tmp_dir", lambda: tmp_path)
    monkeypatch.setattr("src.runtime.cpu_region_lock._current_lock_owner_pids", holders)
    monkeypatch.setattr("src.runtime.cpu_region_lock.read_region_occupancy", lambda: occupancy)
    monkeypatch.setattr("src.runtime.instance_topology.get_instance_regions", lambda: topology)
    monkeypatch.setattr("src.scheduling.contention.load_contention_matrix", lambda: matrix)
    monkeypatch.setattr(
        "src.api.routes.dashboard._port_roles_cached",
        lambda: {18070: "eval_batch_frontdoor", 8182: "worker_general.q1"},
    )

    payload = _region_locks_payload("both")
    rows = {row["role"]: row for row in payload["display_matrix"]["rows"]}

    assert rows["eval_batch_frontdoor"]["cells"][1]["state"] == "active"
    assert rows["eval_batch_frontdoor"]["cells"][1]["label"] == "⚡ 1/2"
    assert [cell["state"] for cell in rows["frontdoor"]["cells"]] == [
        "blocked",
        "blocked",
        "blocked",
    ]
    assert payload["display_matrix"]["held_regions"] == ["q0", "q1", "q2", "q3"]
    assert payload["coherence"]["proc_pairs"] == [
        ["eval_batch_frontdoor", 0],
        ["worker_general", 2],
    ]
    assert payload["coherence"]["occupancy_pairs"] == payload["coherence"]["proc_pairs"]
    assert "eval_batch_frontdoor" not in payload["non_lock_roles"]


def test_unprojected_occupancy_still_prevents_ready_cell(tmp_path, monkeypatch) -> None:
    topology = {
        ("frontdoor", 0): frozenset({"q0", "q1", "q2", "q3"}),
        ("frontdoor", 1): frozenset({"q0", "q1"}),
        ("frontdoor", 2): frozenset({"q2", "q3"}),
    }
    occupancy = {
        "entries": [
            {
                "token": "unknown-lease",
                "pid": 103,
                "role": "future_auxiliary",
                "regions": ["q0", "q1"],
                "instance_idx": 9,
                "capacity": 1,
                "shared": False,
            }
        ],
        "per_region": {},
    }
    matrix = ContentionMatrix(
        version=1,
        measured_at="test",
        host="test",
        topology_hash="test",
        default_floor=0.85,
        same_role={"frontdoor": SameRole(role="frontdoor", verdict="allow")},
        pairs={},
    )
    monkeypatch.setattr("src.runtime.cpu_region_lock._tmp_dir", lambda: tmp_path)
    monkeypatch.setattr("src.runtime.cpu_region_lock._current_lock_owner_pids", lambda _path: [])
    monkeypatch.setattr("src.runtime.cpu_region_lock.read_region_occupancy", lambda: occupancy)
    monkeypatch.setattr("src.runtime.instance_topology.get_instance_regions", lambda: topology)
    monkeypatch.setattr("src.scheduling.contention.load_contention_matrix", lambda: matrix)
    monkeypatch.setattr("src.api.routes.dashboard._port_roles_cached", lambda: {})

    payload = _region_locks_payload("both")
    row = next(row for row in payload["display_matrix"]["rows"] if row["role"] == "frontdoor")

    assert row["cells"][1]["state"] == "blocked"
    assert "future_auxiliary.idx9" in row["cells"][1]["title"]


def test_unsuffixed_auxiliary_port_resolves_physical_half_shape(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.runtime.instance_topology.topology_instance_for_port",
        lambda port: ("eval_batch_frontdoor", 0) if port == 18070 else None,
    )
    monkeypatch.setattr(
        "src.runtime.instance_topology.get_instance_regions",
        lambda: {("eval_batch_frontdoor", 0): frozenset({"q0", "q1"})},
    )

    assert _port_role_shape("eval_batch_frontdoor", 18070) == (
        "eval_batch_frontdoor",
        "half0",
    )
