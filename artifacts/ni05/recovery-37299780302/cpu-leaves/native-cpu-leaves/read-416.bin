"""flush_cache_with_pause + the autopilot loop pause-bug fix.

2026-05-24: pre-fix, `autopilot.py pause` was a no-op on running autopilots
because `state.get("paused")` read a cached in-memory dict and `save_state()`
after each trial clobbered any externally-set True. The fix reloads state at
the top of every iteration. This test mocks out the subprocess+sudo paths and
verifies the wrapper does the right state-file dance.
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from unittest import mock

import yaml


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "autopilot"))


host_health = importlib.import_module("host_health")
experiment_journal = importlib.import_module("experiment_journal")


def _write_state(path: Path, paused: bool, trial_counter: int = 1) -> None:
    path.write_text(json.dumps({"paused": paused, "trial_counter": trial_counter}, indent=2))


def _write_stack_priors(path: Path, roles: dict[str, dict]) -> Path:
    path.write_text(
        yaml.safe_dump(
            {
                "stack_priors_version": 4,
                "contract": {"schema": "epyc.stack_priors", "version": 4},
                "compiled_at": "2026-06-15T00:00:00Z",
                "status": "compiled",
                "coverage_scope": "unit",
                "precedence_spec": "unit",
                "source_artifacts": {},
                "roles": roles,
                "known_global_gaps": {},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def _stack_prior_record(role: str, model_path: str) -> dict:
    return {
        "role": role,
        "deployment_status": "live_stack",
        "status": "compiled",
        "model_id": f"{role}-model",
        "display_name": role,
        "serving": {
            "endpoint": "http://localhost:9999",
            "server_role": role,
            "binding": "unit",
            "ports": [9999],
            "slots": 1,
            "tier": "hot",
            "binary": "llama.cpp",
            "binary_dir": None,
            "numa_policy": "unit",
            "shared_mmap": False,
            "launch": {
                "entries": [],
                "primary_roles": [role],
                "modes": ["default"],
                "requirements": {"model_path": model_path},
                "runtime": {},
            },
        },
        "priors": {
            "throughput_tps": 1.0,
            "quality_overall": 0.5,
            "memory_cost": 1.0,
        },
        "acceleration": {},
        "model": {"mem_gb": 1.0, "modalities": ["text"]},
        "evidence": {},
        "known_gaps": [],
    }


def test_exogenous_cache_flush_category_exists() -> None:
    """DeficiencyCategory.EXOGENOUS_CACHE_FLUSH must be defined for journal tagging."""
    assert hasattr(experiment_journal.DeficiencyCategory, "EXOGENOUS_CACHE_FLUSH")
    assert (
        experiment_journal.DeficiencyCategory.EXOGENOUS_CACHE_FLUSH.value == "exogenous_cache_flush"
    )


def test_llama_server_memory_reader_aggregates_rollup(tmp_path: Path) -> None:
    proc = tmp_path / "123"
    proc.mkdir()
    (proc / "cmdline").write_bytes(
        b"/mnt/raid0/llm/llama.cpp/build/bin/llama-server\x00--port\x008070"
    )
    (proc / "smaps_rollup").write_text(
        "Pss:                2048 kB\nPrivate_Dirty:      1024 kB\nLocked:              512 kB\n"
    )
    other = tmp_path / "456"
    other.mkdir()
    (other / "cmdline").write_bytes(b"python\x00worker.py")
    (other / "smaps_rollup").write_text(
        "Pss:                9999 kB\nPrivate_Dirty:      9999 kB\nLocked:             9999 kB\n"
    )

    assert host_health._read_llama_server_memory_mb(tmp_path) == (1, 2.0, 1.0, 0.5)


def test_memory_residency_warnings_are_advisory() -> None:
    state = host_health.HostHealthState(
        loadavg_1min=1.0,
        n_cores_online=64,
        mean_cur_mhz=2000.0,
        base_mhz=2000.0,
        page_cache_mb=500_000.0,
        mem_available_mb=500_000.0,
        unevictable_mb=160_000.0,
        mlocked_mb=160_000.0,
        llama_process_count=28,
        llama_pss_mb=650_000.0,
        llama_private_dirty_mb=400_000.0,
        llama_locked_mb=150_000.0,
        timestamp=0.0,
    )

    warnings = state.memory_residency_warnings()
    assert warnings
    assert "llama_private_dirty" in warnings[0]
    assert state.is_throttled() == (False, [])


def test_default_rewarm_paths_derive_from_launcher_targets(monkeypatch) -> None:
    derived = ("/models/b.gguf", "/models/a.gguf")

    monkeypatch.setattr(host_health, "_stack_rewarm_ggufs", lambda: derived)

    assert host_health._default_rewarm_ggufs() == derived


def test_default_rewarm_paths_fall_back_to_stack_priors_when_launcher_targets_fail(
    monkeypatch, tmp_path: Path
) -> None:
    priors = _write_stack_priors(
        tmp_path / "stack_priors.yaml",
        {
            "frontdoor": _stack_prior_record("frontdoor", "/models/frontdoor.gguf"),
            "vision_escalation": _stack_prior_record("vision_escalation", "/models/vision.gguf"),
            "worker_general": _stack_prior_record("worker_general", "/models/worker.gguf"),
        },
    )

    def _raise() -> tuple[str, ...]:
        raise RuntimeError("registry unavailable")

    monkeypatch.setattr(host_health, "_stack_rewarm_ggufs", _raise)
    assert host_health._default_rewarm_ggufs(stack_priors_path=priors) == (
        "/models/frontdoor.gguf",
        "/models/vision.gguf",
        "/models/worker.gguf",
    )


def test_default_rewarm_paths_fall_back_to_empty_tuple_when_no_stack_priors_exist(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(host_health, "_stack_rewarm_ggufs", lambda: ())
    monkeypatch.setattr(
        host_health, "_fallback_rewarm_ggufs_from_stack_priors", lambda *args, **kwargs: ()
    )

    assert host_health._default_rewarm_ggufs(stack_priors_path=tmp_path / "missing.yaml") == ()


def test_numa_rewarm_resolves_default_paths_lazily(monkeypatch) -> None:
    monkeypatch.setattr(host_health, "_default_rewarm_ggufs", lambda: ("/tmp/missing.gguf",))
    monkeypatch.setattr(host_health.shutil, "which", lambda binary: f"/usr/bin/{binary}")

    assert host_health._numa_interleave_rewarm() == {"/tmp/missing.gguf": False}


def test_flush_sets_paused_true_then_restores(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    _write_state(state_path, paused=False)

    captured_states: list[bool] = []

    def _fake_remediate() -> bool:
        # While flush runs, capture what the state file says — should be True.
        with open(state_path) as f:
            captured_states.append(json.load(f).get("paused", False))
        return True

    with (
        mock.patch.object(host_health, "remediate", side_effect=_fake_remediate),
        mock.patch.object(host_health, "_numa_interleave_rewarm", return_value={}),
        mock.patch("time.sleep"),
    ):
        result = host_health.flush_cache_with_pause(state_path=state_path, rewarm=False)

    assert result["flush_ok"] is True
    assert result["paused_pre"] is False
    # During the flush, state was paused
    assert captured_states == [True]
    # After the flush, state was restored to False
    with open(state_path) as f:
        assert json.load(f)["paused"] is False


def test_flush_preserves_user_set_pause(tmp_path: Path) -> None:
    """If autopilot was already paused before the flush, leave it paused after."""
    state_path = tmp_path / "state.json"
    _write_state(state_path, paused=True)

    with (
        mock.patch.object(host_health, "remediate", return_value=True),
        mock.patch.object(host_health, "_numa_interleave_rewarm", return_value={}),
        mock.patch("time.sleep"),
    ):
        result = host_health.flush_cache_with_pause(state_path=state_path, rewarm=False)

    assert result["paused_pre"] is True
    with open(state_path) as f:
        # Stay paused — the user/operator wants it paused
        assert json.load(f)["paused"] is True


def test_flush_runs_rewarm_when_enabled(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    _write_state(state_path, paused=False)

    fake_rewarm_results = {"/tmp/fake1.gguf": True, "/tmp/fake2.gguf": True}
    with (
        mock.patch.object(host_health, "remediate", return_value=True),
        mock.patch.object(
            host_health, "_numa_interleave_rewarm", return_value=fake_rewarm_results
        ) as mock_warm,
        mock.patch("time.sleep"),
    ):
        result = host_health.flush_cache_with_pause(state_path=state_path, rewarm=True)

    assert mock_warm.called
    assert result["rewarm"] == fake_rewarm_results


def test_flush_skips_rewarm_when_disabled(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    _write_state(state_path, paused=False)

    with (
        mock.patch.object(host_health, "remediate", return_value=True),
        mock.patch.object(
            host_health, "_numa_interleave_rewarm", return_value={"x": True}
        ) as mock_warm,
        mock.patch("time.sleep"),
    ):
        result = host_health.flush_cache_with_pause(state_path=state_path, rewarm=False)

    assert not mock_warm.called
    assert result["rewarm"] == {}


def test_flush_skips_rewarm_on_flush_failure(tmp_path: Path) -> None:
    """If flush itself failed (no sudo, no helper), skip rewarm — pages are still cached."""
    state_path = tmp_path / "state.json"
    _write_state(state_path, paused=False)

    with (
        mock.patch.object(host_health, "remediate", return_value=False),
        mock.patch.object(
            host_health, "_numa_interleave_rewarm", return_value={"x": True}
        ) as mock_warm,
        mock.patch("time.sleep"),
    ):
        result = host_health.flush_cache_with_pause(state_path=state_path, rewarm=True)

    assert result["flush_ok"] is False
    assert not mock_warm.called


def test_flush_handles_missing_state_file(tmp_path: Path) -> None:
    """If state.json doesn't exist, log a warning but still proceed with flush."""
    state_path = tmp_path / "nonexistent.json"
    with (
        mock.patch.object(host_health, "remediate", return_value=True),
        mock.patch.object(host_health, "_numa_interleave_rewarm", return_value={}),
        mock.patch("time.sleep"),
    ):
        result = host_health.flush_cache_with_pause(state_path=state_path, rewarm=False)
    assert result["flush_ok"] is True
    assert result["paused_pre"] is None


def test_cli_remediate_uses_safe_pause_flush(monkeypatch) -> None:
    throttled_state = host_health.HostHealthState(
        loadavg_1min=1.0,
        n_cores_online=64,
        mean_cur_mhz=1000.0,
        base_mhz=3200.0,
        page_cache_mb=1000.0,
        mem_available_mb=1000.0,
        unevictable_mb=0.0,
        mlocked_mb=0.0,
        llama_process_count=0,
        llama_pss_mb=0.0,
        llama_private_dirty_mb=0.0,
        llama_locked_mb=0.0,
        timestamp=0.0,
    )
    healthy_state = host_health.HostHealthState(
        loadavg_1min=1.0,
        n_cores_online=64,
        mean_cur_mhz=3200.0,
        base_mhz=3200.0,
        page_cache_mb=8192.0,
        mem_available_mb=1000.0,
        unevictable_mb=0.0,
        mlocked_mb=0.0,
        llama_process_count=0,
        llama_pss_mb=0.0,
        llama_private_dirty_mb=0.0,
        llama_locked_mb=0.0,
        timestamp=0.0,
    )
    snapshots = iter([throttled_state, healthy_state])

    monkeypatch.setattr(host_health.HostHealthState, "snapshot", staticmethod(lambda: next(snapshots)))
    safe_flush = mock.Mock(return_value={"flush_ok": True, "rewarm": {}})
    monkeypatch.setattr(host_health, "flush_cache_with_pause", safe_flush)
    bare_flush = mock.Mock(return_value=True)
    monkeypatch.setattr(host_health, "remediate", bare_flush)

    assert host_health._main(["--remediate"]) == 0
    safe_flush.assert_called_once_with()
    bare_flush.assert_not_called()


def test_host_timing_covariates_best_effort_handles_reader_failure(monkeypatch) -> None:
    monkeypatch.setattr(host_health, "_read_loadavg_1min", lambda: 7.25)
    monkeypatch.setattr(host_health, "_read_online_cores", lambda: 64)
    monkeypatch.setattr(
        host_health,
        "_read_mean_cur_mhz",
        lambda: (_ for _ in ()).throw(RuntimeError("freq")),
    )
    monkeypatch.setattr(host_health, "_read_base_mhz", lambda: 3200.0)
    monkeypatch.setattr(
        host_health,
        "_read_meminfo_mb",
        lambda field: {"Cached": 2048.0, "MemAvailable": 8192.0}.get(field, 0.0),
    )
    monkeypatch.setattr(
        host_health,
        "_read_llama_server_memory_mb",
        lambda proc_root=None: (2, 128.0, 64.0, 16.0),
    )
    monkeypatch.setattr(host_health.time, "time", lambda: 123.456)

    covariates = host_health.host_timing_covariates()

    assert isinstance(covariates, dict)
    assert {
        "min_core_mhz",
        "host_inflight",
        "numa_balancing",
        "cache_warm_state",
        "page_cache_mb",
        "mem_available_mb",
        "timestamp",
        "loadavg_1min",
    }.issubset(covariates)
    assert covariates["timestamp"] == 123.456
    assert covariates["loadavg_1min"] == 7.25
    assert covariates["page_cache_mb"] == 2048.0
    assert covariates["mem_available_mb"] == 8192.0
