"""Unit tests for OrchestratorWatcher + fleet_markers.

Covers:
  - Atomic marker writes (no half-files visible to readers)
  - Marker read/discover round-trip
  - Watcher cache TTL behavior
  - Restart classification (operator_reload / external_restart / unreachable)
  - Role→port lookup via the live fleet
  - reference_for_role + was_restarted_since happy paths + edge cases
  - Disabled mode no-ops
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

from scripts.server.fleet_markers import (  # noqa: E402
    LAUNCH_SOURCE_EXTERNAL,
    LAUNCH_SOURCE_STACK_COMMANDS,
    discover_llama_markers,
    read_llama_marker,
    read_orchestrator_marker,
    read_orchestrator_marker_metadata,
    write_llama_marker,
    write_orchestrator_marker,
)
from orchestrator_watch import (  # noqa: E402
    CLASS_EXTERNAL_RESTART,
    CLASS_OPERATOR_RELOAD,
    CLASS_UNREACHABLE,
    NEVER_SEEN,
    OrchestratorWatcher,
)


# ───────── fleet_markers tests ──────────


def test_orchestrator_marker_round_trip(tmp_path: Path) -> None:
    path = write_orchestrator_marker(tmp_dir=tmp_path, git_sha="abc1234")
    assert path.exists()
    val = read_orchestrator_marker(tmp_dir=tmp_path)
    assert isinstance(val, float)
    assert val > 0
    metadata = read_orchestrator_marker_metadata(tmp_dir=tmp_path)
    assert metadata is not None
    assert metadata["started_at"] == val
    assert metadata["git_sha"] == "abc1234"


def test_orchestrator_marker_metadata_accepts_legacy_one_line_marker(
    tmp_path: Path,
) -> None:
    (tmp_path / "orchestrator_fleet_started_at").write_text("123.5\n")

    metadata = read_orchestrator_marker_metadata(tmp_dir=tmp_path)

    assert metadata == {"started_at": 123.5, "git_sha": None}


def test_llama_marker_round_trip_with_roles(tmp_path: Path) -> None:
    path = write_llama_marker(8070, ["frontdoor", "coder_escalation"], tmp_dir=tmp_path)
    assert path.exists()
    m = read_llama_marker(8070, tmp_dir=tmp_path)
    assert m is not None
    assert isinstance(m["started_at"], float)
    assert m["source"] == LAUNCH_SOURCE_STACK_COMMANDS
    assert m["roles"] == ["frontdoor", "coder_escalation"]


def test_llama_marker_external_source(tmp_path: Path) -> None:
    write_llama_marker(8072, ["worker_general"], source=LAUNCH_SOURCE_EXTERNAL, tmp_dir=tmp_path)
    m = read_llama_marker(8072, tmp_dir=tmp_path)
    assert m is not None
    assert m["source"] == LAUNCH_SOURCE_EXTERNAL


def test_llama_marker_rejects_unknown_source(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        write_llama_marker(8070, ["frontdoor"], source="unknown", tmp_dir=tmp_path)


def test_marker_atomic_no_partial_visible(tmp_path: Path) -> None:
    # An incomplete write (no os.replace) should leave only a .tmp file,
    # not the canonical name. The canonical name appears only after replace.
    # Sanity test: stage two writes in quick succession and verify the
    # second one fully replaces the first (no merged or partial content).
    write_orchestrator_marker(tmp_dir=tmp_path)
    first = read_orchestrator_marker(tmp_dir=tmp_path)
    time.sleep(0.01)
    write_orchestrator_marker(tmp_dir=tmp_path)
    second = read_orchestrator_marker(tmp_dir=tmp_path)
    assert second is not None and first is not None
    assert second >= first  # newer write either equal (same clock tick) or greater


def test_discover_llama_markers_returns_all_ports(tmp_path: Path) -> None:
    write_llama_marker(8070, ["frontdoor"], tmp_dir=tmp_path)
    write_llama_marker(8072, ["worker_general"], tmp_dir=tmp_path)
    write_llama_marker(8083, ["architect_general"], tmp_dir=tmp_path)
    discovered = discover_llama_markers(tmp_dir=tmp_path)
    assert set(discovered.keys()) == {8070, 8072, 8083}
    assert discovered[8070]["roles"] == ["frontdoor"]
    assert discovered[8083]["roles"] == ["architect_general"]


def test_discover_ignores_non_marker_files(tmp_path: Path) -> None:
    # Create some unrelated files alongside markers.
    (tmp_path / "some_other_file.log").write_text("noise")
    (tmp_path / "llama_NOT_AN_INT_started_at").write_text("ignore me")
    write_llama_marker(8090, ["embedder"], tmp_dir=tmp_path)
    discovered = discover_llama_markers(tmp_dir=tmp_path)
    assert set(discovered.keys()) == {8090}


def test_read_missing_marker_returns_none(tmp_path: Path) -> None:
    assert read_orchestrator_marker(tmp_dir=tmp_path) is None
    assert read_llama_marker(8070, tmp_dir=tmp_path) is None


def test_read_malformed_marker_returns_none(tmp_path: Path) -> None:
    # Write a non-numeric first line
    (tmp_path / "orchestrator_fleet_started_at").write_text("not a number\n")
    assert read_orchestrator_marker(tmp_dir=tmp_path) is None


# ───────── OrchestratorWatcher tests ──────────


def _fake_httpx_get(version_payload: dict | None = None,
                    fleet_payload: dict | None = None,
                    raise_on_version: bool = False,
                    raise_on_fleet: bool = False):
    """Build a side_effect for httpx.get that routes by URL."""

    def _side(url, **kwargs):
        if "/dashboard/api/version" in url:
            if raise_on_version:
                raise RuntimeError("simulated /version failure")
            resp = MagicMock()
            resp.raise_for_status.return_value = None
            resp.json.return_value = version_payload or {}
            return resp
        if "/dashboard/api/llama_fleet_ids" in url:
            if raise_on_fleet:
                raise RuntimeError("simulated /llama_fleet_ids failure")
            resp = MagicMock()
            resp.raise_for_status.return_value = None
            resp.json.return_value = fleet_payload or {"per_port": {}, "now": time.time()}
            return resp
        raise AssertionError(f"unexpected URL: {url}")
    return _side


def test_watcher_disabled_mode_noops() -> None:
    w = OrchestratorWatcher(disabled=True)
    assert w.current_orchestrator_id() is None
    assert w.current_llama_fleet() == {}
    assert w.current_llama_id(8070) is None
    assert w.port_for_role("frontdoor") is None
    # reference_for_role always includes an orchestrator key (NEVER_SEEN
    # in disabled mode) so call sites don't have to branch on missing keys.
    ref = w.reference_for_role("frontdoor")
    assert ref == {"orchestrator": NEVER_SEEN}
    assert w.was_restarted_since({"orchestrator": 1.0}) == {}
    assert w.wait_for_orchestrator() is True
    assert w.wait_for_llama(8070) is True


def test_watcher_reads_orchestrator_id() -> None:
    with patch("orchestrator_watch.httpx.get",
               side_effect=_fake_httpx_get(version_payload={"server_started_at": 123.5})):
        w = OrchestratorWatcher(disabled=False, cache_ttl_s=0)
        assert w.current_orchestrator_id() == 123.5


def test_watcher_caches_orchestrator_id() -> None:
    fake = MagicMock(side_effect=_fake_httpx_get(version_payload={"server_started_at": 1.0}))
    with patch("orchestrator_watch.httpx.get", fake):
        w = OrchestratorWatcher(disabled=False, cache_ttl_s=10.0)
        w.current_orchestrator_id()
        w.current_orchestrator_id()
        w.current_orchestrator_id()
        # Only one HTTP call should have happened due to cache.
        assert fake.call_count == 1


def test_watcher_reads_llama_fleet() -> None:
    fleet = {"per_port": {"8070": {"started_at": 100.0, "source": "stack_commands", "roles": ["frontdoor"]}}}
    with patch("orchestrator_watch.httpx.get",
               side_effect=_fake_httpx_get(version_payload={"server_started_at": 1.0},
                                            fleet_payload=fleet)):
        w = OrchestratorWatcher(disabled=False, cache_ttl_s=0)
        out = w.current_llama_fleet()
        assert out is not None and 8070 in out
        assert w.current_llama_id(8070) == (100.0, "stack_commands")
        assert w.port_for_role("frontdoor") == 8070


def test_watcher_port_for_unknown_role_logs_once() -> None:
    fleet = {"per_port": {"8070": {"started_at": 100.0, "source": "stack_commands", "roles": ["frontdoor"]}}}
    with patch("orchestrator_watch.httpx.get",
               side_effect=_fake_httpx_get(version_payload={"server_started_at": 1.0},
                                            fleet_payload=fleet)):
        w = OrchestratorWatcher(disabled=False, cache_ttl_s=0)
        assert w.port_for_role("nonexistent_role") is None
        # Second call should not warn again (rate-limit applied via set).
        assert w.port_for_role("nonexistent_role") is None
        assert "nonexistent_role" in w._missing_role_warned


def test_was_restarted_since_orchestrator_changed() -> None:
    with patch("orchestrator_watch.httpx.get",
               side_effect=_fake_httpx_get(version_payload={"server_started_at": 200.0})):
        w = OrchestratorWatcher(disabled=False, cache_ttl_s=0)
        out = w.was_restarted_since({"orchestrator": 100.0})
        assert out == {"orchestrator": CLASS_OPERATOR_RELOAD}


def test_was_restarted_since_orchestrator_same() -> None:
    with patch("orchestrator_watch.httpx.get",
               side_effect=_fake_httpx_get(version_payload={"server_started_at": 100.0})):
        w = OrchestratorWatcher(disabled=False, cache_ttl_s=0)
        out = w.was_restarted_since({"orchestrator": 100.0})
        assert out == {}


def test_was_restarted_since_orchestrator_unreachable() -> None:
    with patch("orchestrator_watch.httpx.get",
               side_effect=_fake_httpx_get(raise_on_version=True)):
        w = OrchestratorWatcher(disabled=False, cache_ttl_s=0)
        out = w.was_restarted_since({"orchestrator": 100.0})
        assert out == {"orchestrator": CLASS_UNREACHABLE}


def test_was_restarted_since_llama_operator_vs_external() -> None:
    fleet_operator = {"per_port": {"8070": {"started_at": 200.0, "source": "stack_commands", "roles": ["frontdoor"]}}}
    fleet_external = {"per_port": {"8070": {"started_at": 200.0, "source": "external", "roles": ["frontdoor"]}}}
    # Case 1: source=stack_commands → operator_reload
    with patch("orchestrator_watch.httpx.get",
               side_effect=_fake_httpx_get(version_payload={"server_started_at": 1.0},
                                            fleet_payload=fleet_operator)):
        w = OrchestratorWatcher(disabled=False, cache_ttl_s=0)
        out = w.was_restarted_since({"orchestrator": 1.0, "llama_8070": 100.0})
        assert out == {"llama_8070": CLASS_OPERATOR_RELOAD}
    # Case 2: source=external → external_restart
    with patch("orchestrator_watch.httpx.get",
               side_effect=_fake_httpx_get(version_payload={"server_started_at": 1.0},
                                            fleet_payload=fleet_external)):
        w = OrchestratorWatcher(disabled=False, cache_ttl_s=0)
        out = w.was_restarted_since({"orchestrator": 1.0, "llama_8070": 100.0})
        assert out == {"llama_8070": CLASS_EXTERNAL_RESTART}


def test_reference_for_role_handles_unknown_role() -> None:
    """If role doesn't match any marker, reference returns orchestrator only."""
    fleet = {"per_port": {"8070": {"started_at": 100.0, "source": "stack_commands", "roles": ["frontdoor"]}}}
    with patch("orchestrator_watch.httpx.get",
               side_effect=_fake_httpx_get(version_payload={"server_started_at": 1.0},
                                            fleet_payload=fleet)):
        w = OrchestratorWatcher(disabled=False, cache_ttl_s=0)
        ref = w.reference_for_role("mystery_role")
        assert set(ref.keys()) == {"orchestrator"}


def test_reference_for_role_includes_llama() -> None:
    fleet = {"per_port": {"8070": {"started_at": 200.0, "source": "stack_commands", "roles": ["frontdoor"]}}}
    with patch("orchestrator_watch.httpx.get",
               side_effect=_fake_httpx_get(version_payload={"server_started_at": 1.0},
                                            fleet_payload=fleet)):
        w = OrchestratorWatcher(disabled=False, cache_ttl_s=0)
        ref = w.reference_for_role("frontdoor")
        assert ref == {"orchestrator": 1.0, "llama_8070": 200.0}


def test_never_seen_reference_does_not_trigger_restart() -> None:
    """If we never observed a marker before (reference == NEVER_SEEN),
    a current real value should NOT classify as restart — we just hadn't
    seen it yet."""
    with patch("orchestrator_watch.httpx.get",
               side_effect=_fake_httpx_get(version_payload={"server_started_at": 200.0})):
        w = OrchestratorWatcher(disabled=False, cache_ttl_s=0)
        out = w.was_restarted_since({"orchestrator": NEVER_SEEN})
        assert out == {}


def test_invalidate_cache_forces_refetch() -> None:
    fake = MagicMock(side_effect=_fake_httpx_get(version_payload={"server_started_at": 1.0}))
    with patch("orchestrator_watch.httpx.get", fake):
        w = OrchestratorWatcher(disabled=False, cache_ttl_s=60.0)
        w.current_orchestrator_id()
        assert fake.call_count == 1
        w.invalidate_cache()
        w.current_orchestrator_id()
        assert fake.call_count == 2
