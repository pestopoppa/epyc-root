"""Branch-focused tests for benchmark preflight helpers."""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import urllib.error


_ROOT = Path(__file__).resolve().parents[2] / "scripts" / "benchmark"
sys.path.insert(0, str(_ROOT))
_SPEC = importlib.util.spec_from_file_location("seeding_infra_branching", _ROOT / "seeding_infra.py")
_MOD = importlib.util.module_from_spec(_SPEC)
sys.modules["seeding_infra_branching"] = _MOD
_SPEC.loader.exec_module(_MOD)
_MOD.os.environ[_MOD.STACK_CHANGE_GATE_ENV] = "0"
_REAL_WAIT_FOR_WORKERS_READY = _MOD._wait_for_workers_ready
_REAL_IS_SERVER_IDLE = _MOD._is_server_idle
_REAL_LAUNCH_API_ONLY = _MOD._launch_api_only


def _reset_diags() -> None:
    _MOD._preflight_diagnostics["api_health"] = {}
    _MOD._preflight_diagnostics["idle_probes"] = {}
    _MOD._preflight_diagnostics["last_preflight"] = {}


def test_check_server_health_records_exception_metadata():
    client = Mock()
    client.get.side_effect = RuntimeError("boom")
    _MOD.state.get_poll_client = Mock(return_value=client)

    assert _MOD._check_server_health("http://localhost:8000") is False

    diag = _MOD.get_preflight_diagnostics()["api_health"]["http://localhost:8000"]
    assert diag["failure_reason"] == "RuntimeError"
    assert diag["status_code"] is None


def test_check_port_handles_connection_refused_as_down():
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
        assert _MOD._check_port(8000) is False


def test_check_port_treats_other_url_errors_as_listening():
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("HTTP Error 500")):
        assert _MOD._check_port(8000) is True


def test_check_port_treats_non_urlerror_exception_as_listening():
    with patch("urllib.request.urlopen", side_effect=RuntimeError("unexpected")):
        assert _MOD._check_port(8000) is True


def test_check_port_success_path_reports_port_up():
    with patch("urllib.request.urlopen", return_value=SimpleNamespace()):
        assert _MOD._check_port(8000) is True


def test_kill_port_returns_true_when_port_no_longer_listening():
    with (
        patch("subprocess.run", return_value=SimpleNamespace(returncode=0)),
        patch.object(_MOD, "_check_port", return_value=False) as check_port,
        patch("time.sleep"),
    ):
        assert _MOD._kill_port(8000) is True
    check_port.assert_called_once_with(8000)


def test_launch_api_only_frees_port_then_starts_successfully():
    _MOD._check_port = Mock(return_value=True)
    _MOD._kill_port = Mock(return_value=True)
    _MOD._check_server_health = Mock(return_value=True)
    fake_proc = MagicMock(pid=5555)
    fake_proc.poll.return_value = None

    with (
        patch("subprocess.Popen", return_value=fake_proc),
        patch("builtins.open", MagicMock()),
        patch("time.sleep"),
    ):
        assert _MOD._launch_api_only() is True

    _MOD._kill_port.assert_called_once_with(8000)
    _MOD._check_server_health.assert_called_once_with(_MOD.DEFAULT_ORCHESTRATOR_URL)


def test_auto_launch_stack_returns_false_on_nonzero_exit():
    result = SimpleNamespace(returncode=2, stderr="e1\ne2\ne3\ne4\ne5\ne6")
    with (
        patch.object(_MOD, "STACK_SCRIPT", SimpleNamespace(exists=lambda: True, __str__=lambda self: "stack.py")),
        patch("subprocess.run", return_value=result),
    ):
        assert _MOD._auto_launch_stack() is False


def test_auto_launch_stack_returns_false_when_health_never_recovers():
    result = SimpleNamespace(returncode=0, stderr="")
    _MOD._check_server_health = Mock(return_value=False)

    with (
        patch.object(_MOD, "STACK_SCRIPT", SimpleNamespace(exists=lambda: True, __str__=lambda self: "stack.py")),
        patch("subprocess.run", return_value=result),
        patch("time.sleep"),
    ):
        assert _MOD._auto_launch_stack() is False


def test_attempt_recovery_restarts_api_when_model_port_is_up():
    _MOD._check_port = Mock(side_effect=lambda port: port == 8080)
    _MOD._launch_api_only = Mock(return_value=True)
    _MOD._auto_launch_stack = Mock(return_value=False)
    _MOD._wait_for_workers_ready = Mock()

    with patch.object(_MOD, "MODEL_PORTS", [8080, 8081]):
        assert _MOD._attempt_recovery("http://localhost:8000") is True

    _MOD._launch_api_only.assert_called_once()
    _MOD._auto_launch_stack.assert_not_called()
    _MOD._wait_for_workers_ready.assert_called_once_with("http://localhost:8000")


def test_attempt_recovery_uses_full_stack_when_no_model_ports_up():
    _MOD._check_port = Mock(return_value=False)
    _MOD._launch_api_only = Mock(return_value=False)
    _MOD._auto_launch_stack = Mock(return_value=True)
    _MOD._wait_for_workers_ready = Mock()

    with patch.object(_MOD, "MODEL_PORTS", [8080, 8081]):
        assert _MOD._attempt_recovery("http://localhost:8000") is True

    _MOD._launch_api_only.assert_not_called()
    _MOD._auto_launch_stack.assert_called_once()
    _MOD._wait_for_workers_ready.assert_called_once_with("http://localhost:8000")


def test_wait_for_heavy_models_idle_returns_after_timeout():
    _MOD.state.shutdown = False
    _MOD._is_server_idle = Mock(return_value=False)

    with (
        patch.object(_MOD, "HEAVY_PORTS", [8001]),
        patch.object(_MOD.time, "perf_counter", side_effect=[0.0, 0.0, 5.0, 11.0]),
        patch.object(_MOD.time, "sleep"),
    ):
        _MOD._wait_for_heavy_models_idle(max_wait=10)

    assert _MOD._is_server_idle.call_count >= 2


def test_wait_for_heavy_models_idle_logs_elapsed_when_eventually_idle():
    _MOD._is_server_idle = Mock(side_effect=[False, True])
    _MOD.state.shutdown = False

    with (
        patch.object(_MOD, "HEAVY_PORTS", [8001]),
        patch.object(_MOD.time, "perf_counter", side_effect=[0.0, 0.5, 1.5]),
        patch.object(_MOD.time, "sleep"),
        patch.object(_MOD.logger, "info") as info,
    ):
        _MOD._wait_for_heavy_models_idle(max_wait=10)

    assert any("Heavy models idle after" in str(call.args[0]) for call in info.call_args_list)


def test_wait_for_heavy_models_idle_respects_shutdown_flag():
    _MOD._is_server_idle = Mock(return_value=False)
    _MOD.state.shutdown = True
    try:
        with (
            patch.object(_MOD, "HEAVY_PORTS", [8001]),
            patch.object(_MOD.time, "perf_counter", side_effect=[0.0, 0.1]),
            patch.object(_MOD.time, "sleep") as sleep,
        ):
            _MOD._wait_for_heavy_models_idle(max_wait=10)
    finally:
        _MOD.state.shutdown = False
        _MOD._is_server_idle = _REAL_IS_SERVER_IDLE

    sleep.assert_not_called()


def test_wait_for_workers_ready_uses_parent_when_no_children():
    _MOD._wait_for_workers_ready = _REAL_WAIT_FOR_WORKERS_READY

    def _run(cmd, **kwargs):  # noqa: ANN001
        if cmd[:2] == ["lsof", "-ti"]:
            return SimpleNamespace(stdout="123\n")
        if cmd[:2] == ["ps", "--ppid"]:
            return SimpleNamespace(stdout="")
        if cmd[:3] == ["ps", "-o", "pid=,%cpu="]:
            return SimpleNamespace(stdout="123 1.0\n")
        raise AssertionError(f"unexpected command: {cmd}")

    _MOD.state.shutdown = False
    with (
        patch("subprocess.run", side_effect=_run),
        patch.object(_MOD.time, "perf_counter", side_effect=[0.0, 0.0, 1.0]),
    ):
        _MOD._wait_for_workers_ready("http://localhost:8000", max_wait=10, settle_checks=1)


def test_wait_for_workers_ready_returns_when_no_pid_found():
    _MOD._wait_for_workers_ready = _REAL_WAIT_FOR_WORKERS_READY

    with patch("subprocess.run", return_value=SimpleNamespace(stdout="")):
        _MOD._wait_for_workers_ready("http://localhost:8000", max_wait=10)


def test_wait_for_workers_ready_returns_when_lsof_fails():
    _MOD._wait_for_workers_ready = _REAL_WAIT_FOR_WORKERS_READY

    with patch("subprocess.run", side_effect=RuntimeError("lsof unavailable")):
        _MOD._wait_for_workers_ready("http://localhost:8000", max_wait=10)


def test_wait_for_workers_ready_hot_then_stable_updates_deque_status():
    _MOD._wait_for_workers_ready = _REAL_WAIT_FOR_WORKERS_READY

    class DequeHandler:
        def __init__(self):
            self.records = ["workers booting..."]

    handler = DequeHandler()
    root = logging.getLogger()
    original_handlers = root.handlers
    root.handlers = [handler]

    child_calls = {"n": 0}

    def _run(cmd, **kwargs):  # noqa: ANN001
        if cmd[:2] == ["lsof", "-ti"]:
            return SimpleNamespace(stdout="123\n")
        if cmd[:2] == ["ps", "--ppid"]:
            child_calls["n"] += 1
            if child_calls["n"] == 1:
                return SimpleNamespace(stdout="234 85.0\n235 5.0\n")
            return SimpleNamespace(stdout="234 1.0\n235 0.5\n")
        raise AssertionError(f"unexpected command: {cmd}")

    _MOD.state.shutdown = False
    try:
        with (
            patch("subprocess.run", side_effect=_run),
            patch.object(_MOD.time, "perf_counter", side_effect=[0.0, 0.1, 0.2, 6.1, 6.2]),
            patch.object(_MOD.time, "sleep"),
        ):
            _MOD._wait_for_workers_ready(
                "http://localhost:8000",
                max_wait=10,
                cpu_threshold=10.0,
                settle_checks=1,
            )
    finally:
        root.handlers = original_handlers

    assert "Workers stabilized after" in handler.records[-1]


def test_wait_for_workers_ready_times_out_when_probe_paths_fail():
    _MOD._wait_for_workers_ready = _REAL_WAIT_FOR_WORKERS_READY

    def _run(cmd, **kwargs):  # noqa: ANN001
        if cmd[:2] == ["lsof", "-ti"]:
            return SimpleNamespace(stdout="123\n")
        if cmd[:2] == ["ps", "--ppid"]:
            raise RuntimeError("ps failed")
        if cmd[:3] == ["ps", "-o", "pid=,%cpu="]:
            return SimpleNamespace(stdout="")
        raise AssertionError(f"unexpected command: {cmd}")

    _MOD.state.shutdown = False
    with (
        patch("subprocess.run", side_effect=_run),
        patch.object(_MOD.time, "perf_counter", side_effect=[0.0, 0.0, 2.0]),
        patch.object(_MOD.time, "sleep"),
        patch.object(_MOD.logger, "warning") as warning,
    ):
        _MOD._wait_for_workers_ready("http://localhost:8000", max_wait=1)

    warning.assert_called_once()


def test_wait_for_workers_ready_handles_parent_probe_exception():
    _MOD._wait_for_workers_ready = _REAL_WAIT_FOR_WORKERS_READY

    def _run(cmd, **kwargs):  # noqa: ANN001
        if cmd[:2] == ["lsof", "-ti"]:
            return SimpleNamespace(stdout="123\n")
        if cmd[:2] == ["ps", "--ppid"]:
            return SimpleNamespace(stdout="")
        if cmd[:3] == ["ps", "-o", "pid=,%cpu="]:
            raise RuntimeError("parent probe failed")
        raise AssertionError(f"unexpected command: {cmd}")

    _MOD.state.shutdown = False
    with (
        patch("subprocess.run", side_effect=_run),
        patch.object(_MOD.time, "perf_counter", side_effect=[0.0, 0.0, 2.0]),
        patch.object(_MOD.time, "sleep"),
        patch.object(_MOD.logger, "warning") as warning,
    ):
        _MOD._wait_for_workers_ready("http://localhost:8000", max_wait=1)

    warning.assert_called_once()


def test_wait_for_workers_ready_respects_shutdown_after_hot_sample():
    _MOD._wait_for_workers_ready = _REAL_WAIT_FOR_WORKERS_READY

    def _run(cmd, **kwargs):  # noqa: ANN001
        if cmd[:2] == ["lsof", "-ti"]:
            return SimpleNamespace(stdout="123\n")
        if cmd[:2] == ["ps", "--ppid"]:
            return SimpleNamespace(stdout="234 50.0\n")
        raise AssertionError(f"unexpected command: {cmd}")

    _MOD.state.shutdown = True
    try:
        with (
            patch("subprocess.run", side_effect=_run),
            patch.object(_MOD.time, "perf_counter", side_effect=[0.0, 0.1, 0.2]),
            patch.object(_MOD.time, "sleep") as sleep,
        ):
            _MOD._wait_for_workers_ready("http://localhost:8000", max_wait=10)
    finally:
        _MOD.state.shutdown = False

    sleep.assert_not_called()


def test_launch_api_only_returns_false_when_process_exits_early():
    _MOD._launch_api_only = _REAL_LAUNCH_API_ONLY
    _MOD._check_port = Mock(return_value=False)
    _MOD._check_server_health = Mock(return_value=True)
    fake_proc = MagicMock(pid=4444)
    fake_proc.poll.return_value = 1
    fake_proc.returncode = 7

    with (
        patch("subprocess.Popen", return_value=fake_proc),
        patch("builtins.open", MagicMock()),
        patch.object(_MOD.time, "sleep"),
    ):
        assert _MOD._launch_api_only() is False

    _MOD._check_server_health.assert_not_called()


def test_run_preflight_restart_successful_kill_sleeps_before_relaunch():
    _reset_diags()
    _MOD._check_server_health = Mock(return_value=True)
    _MOD._check_port = Mock(return_value=True)
    _MOD._kill_port = Mock(return_value=True)
    _MOD._wait_for_workers_ready = Mock()

    health_resp = Mock(status_code=200)
    health_resp.json.return_value = {"backends": {"worker": {"healthy": True}}}
    smoke_resp = Mock(status_code=200)
    smoke_resp.json.return_value = {"answer": "4", "routed_to": "worker"}
    client = Mock(get=Mock(return_value=health_resp), post=Mock(return_value=smoke_resp))
    _MOD.state.get_poll_client = Mock(return_value=client)

    with (
        patch.object(_MOD, "MODEL_PORTS", []),
        patch.object(_MOD.time, "sleep") as sleep,
    ):
        assert _MOD.run_preflight("http://localhost:8000", restart_api=True) is True

    sleep.assert_any_call(2)


def test_run_preflight_records_non_timeout_smoke_error_reason():
    _reset_diags()
    _MOD._check_server_health = Mock(return_value=True)
    _MOD._check_port = Mock(return_value=False)
    _MOD._wait_for_workers_ready = Mock()

    health_resp = Mock(status_code=200)
    health_resp.json.return_value = {"backends": {"worker": {"healthy": True}}}
    client = Mock(get=Mock(return_value=health_resp))
    client.post.side_effect = ValueError("bad payload")
    _MOD.state.get_poll_client = Mock(return_value=client)

    assert _MOD.run_preflight("http://localhost:8000", restart_api=False) is False

    diag = _MOD.get_preflight_diagnostics()["last_preflight"]
    assert diag["stage"] == "smoke_test"
    assert diag["failure_reason"] == "ValueError"
    assert "bad payload" in diag["failure_detail"]
