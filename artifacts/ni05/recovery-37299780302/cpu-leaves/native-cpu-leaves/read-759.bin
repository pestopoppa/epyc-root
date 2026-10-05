"""Additional coverage for benchmark preflight helpers."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch


_ROOT = Path(__file__).resolve().parents[2] / "scripts" / "benchmark"
sys.path.insert(0, str(_ROOT))
_SPEC = importlib.util.spec_from_file_location("seeding_infra_additional", _ROOT / "seeding_infra.py")
_MOD = importlib.util.module_from_spec(_SPEC)
sys.modules["seeding_infra_additional"] = _MOD
_SPEC.loader.exec_module(_MOD)
_MOD.os.environ[_MOD.STACK_CHANGE_GATE_ENV] = "0"


def _reset_diags() -> None:
    _MOD._preflight_diagnostics["api_health"] = {}
    _MOD._preflight_diagnostics["idle_probes"] = {}
    _MOD._preflight_diagnostics["last_preflight"] = {}


def test_is_server_idle_records_non_200_as_assumed_idle():
    response = Mock(status_code=500)
    _MOD.state.get_poll_client = Mock(return_value=Mock(get=Mock(return_value=response)))

    assert _MOD._is_server_idle(8080) is True

    diag = _MOD.get_preflight_diagnostics()["idle_probes"]["8080"]
    assert diag["assumed_idle"] is True
    assert diag["failure_reason"] == "http_status"
    assert diag["status_code"] == 500


def test_is_server_idle_records_busy_slots():
    response = Mock(status_code=200)
    response.json.return_value = [{"is_processing": False}, {"is_processing": True}]
    _MOD.state.get_poll_client = Mock(return_value=Mock(get=Mock(return_value=response)))

    assert _MOD._is_server_idle(8081) is False

    diag = _MOD.get_preflight_diagnostics()["idle_probes"]["8081"]
    assert diag["idle"] is False
    assert diag["assumed_idle"] is False
    assert diag["slots_seen"] == 2


def test_latest_probe_helpers_return_copied_payloads():
    _MOD._record_diag("api_health", "http://localhost:8000", {"ok": True, "status_code": 200})
    _MOD._record_diag("idle_probes", "8082", {"idle": True, "assumed_idle": False})

    api_diag = _MOD._latest_api_probe("http://localhost:8000")
    idle_diag = _MOD._latest_idle_probe(8082)

    api_diag["ok"] = False
    idle_diag["idle"] = False

    fresh = _MOD.get_preflight_diagnostics()
    assert fresh["api_health"]["http://localhost:8000"]["ok"] is True
    assert fresh["idle_probes"]["8082"]["idle"] is True


def test_launch_api_only_fails_when_port_busy_and_not_freed():
    _MOD._check_port = Mock(return_value=True)
    _MOD._kill_port = Mock(return_value=False)

    assert _MOD._launch_api_only() is False


def test_launch_api_only_succeeds_after_health_recovers():
    _MOD._check_port = Mock(return_value=False)
    _MOD._check_server_health = Mock(side_effect=[False, True])
    fake_proc = MagicMock(pid=4321)
    fake_proc.poll.return_value = None

    with (
        patch("subprocess.Popen", return_value=fake_proc) as popen,
        patch("builtins.open", MagicMock()),
        patch("time.sleep"),
    ):
        assert _MOD._launch_api_only() is True

    assert popen.called
    _MOD._check_server_health.assert_called()


def test_launch_api_only_kills_process_when_health_never_recovers():
    _MOD._check_port = Mock(return_value=False)
    _MOD._check_server_health = Mock(return_value=False)
    fake_proc = MagicMock(pid=9999)
    fake_proc.poll.return_value = None

    with (
        patch("subprocess.Popen", return_value=fake_proc),
        patch("builtins.open", MagicMock()),
        patch("time.sleep"),
    ):
        assert _MOD._launch_api_only() is False

    fake_proc.kill.assert_called_once()


def test_auto_launch_stack_handles_missing_script():
    with patch.object(_MOD, "STACK_SCRIPT", SimpleNamespace(exists=lambda: False)):
        assert _MOD._auto_launch_stack() is False


def test_auto_launch_stack_handles_subprocess_timeout():
    with (
        patch.object(_MOD, "STACK_SCRIPT", SimpleNamespace(exists=lambda: True, __str__=lambda self: "stack.py")),
        patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["stack.py", "start"], timeout=600),
        ),
    ):
        assert _MOD._auto_launch_stack() is False


def test_auto_launch_stack_succeeds_after_health_probe():
    run_result = SimpleNamespace(returncode=0, stderr="")
    _MOD._check_server_health = Mock(side_effect=[False, True])
    with (
        patch.object(_MOD, "STACK_SCRIPT", SimpleNamespace(exists=lambda: True, __str__=lambda self: "stack.py")),
        patch("subprocess.run", return_value=run_result),
        patch("time.sleep"),
    ):
        assert _MOD._auto_launch_stack() is True


def test_run_preflight_uses_full_stack_path_and_records_failure_when_launch_fails():
    _reset_diags()
    _MOD._check_server_health = Mock(return_value=False)
    _MOD._check_port = Mock(return_value=False)
    _MOD._auto_launch_stack = Mock(return_value=False)

    assert _MOD.run_preflight("http://localhost:8000", restart_api=False) is False

    diag = _MOD.get_preflight_diagnostics()["last_preflight"]
    assert diag["stage"] == "stack_launch"
    assert diag["failure_reason"] == "stack_launch_failed"


def test_run_preflight_restart_kill_failure_continues_when_api_is_healthy():
    _reset_diags()
    _MOD._check_server_health = Mock(return_value=True)
    _MOD._check_port = Mock(side_effect=lambda port: port == 8000)
    _MOD._kill_port = Mock(return_value=False)
    _MOD._wait_for_workers_ready = Mock()

    health_resp = Mock(status_code=200)
    health_resp.json.return_value = {"backends": {"worker": {"healthy": True}}}
    smoke_resp = Mock(status_code=200)
    smoke_resp.json.return_value = {"answer": "4", "routed_to": "worker"}
    client = Mock(get=Mock(return_value=health_resp), post=Mock(return_value=smoke_resp))
    _MOD.state.get_poll_client = Mock(return_value=client)

    assert _MOD.run_preflight("http://localhost:8000", restart_api=True) is True
    _MOD._kill_port.assert_called_once_with(8000)


def test_run_preflight_ignores_backend_health_exception_and_still_passes():
    _reset_diags()
    _MOD._check_server_health = Mock(return_value=True)
    _MOD._check_port = Mock(return_value=False)
    _MOD._wait_for_workers_ready = Mock()

    client = Mock()
    client.get.side_effect = RuntimeError("health endpoint unavailable")
    smoke_resp = Mock(status_code=200)
    smoke_resp.json.return_value = {"answer": "4", "routed_to": "worker"}
    client.post.return_value = smoke_resp
    _MOD.state.get_poll_client = Mock(return_value=client)

    assert _MOD.run_preflight("http://localhost:8000", restart_api=False) is True
