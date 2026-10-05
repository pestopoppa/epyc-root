"""Offline injected-probe fixtures for the NI05-44 observer leaf gate.

These fixtures never connect to tmux or the session bus. They exercise the
small adapter wrapper with captured probe JSON and process failure shapes.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.coordination.qualified_idle_probe import qualified_idle

REPO_ROOT = Path(__file__).resolve().parents[3]
IDLE_WATCH = REPO_ROOT / "scripts" / "coordination" / "idle_watch.sh"
IDLE_SUPERVISOR = REPO_ROOT / "scripts" / "coordination" / "idle_supervisor.sh"


def _result(stdout: str, *, returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=["probe"], returncode=returncode,
                                       stdout=stdout, stderr="")


def _payload(*, decided: bool = True, state: str = "idle",
             nudge_ok: bool = True) -> str:
    return json.dumps({"runtime_decided": decided, "runtime_state": state,
                       "nudge_ok": nudge_ok})


@pytest.mark.parametrize("state", ["active", "working", "compacting", "blocked", "unavailable"])
def test_non_idle_runtime_vocabulary_never_qualifies(state: str) -> None:
    idle, _ = qualified_idle("mainA", run=lambda *_a, **_kw: _result(_payload(state=state)))
    assert idle is False


def test_qualified_idle_requires_all_three_positive_fields() -> None:
    idle, _ = qualified_idle("mainA", run=lambda *_a, **_kw: _result(_payload()))
    assert idle is True


def test_idle_but_final_guard_blocked_is_unknown() -> None:
    idle, _ = qualified_idle(
        "mainA", run=lambda *_a, **_kw: _result(_payload(nudge_ok=False)))
    assert idle is False


def test_idle_without_runtime_authority_is_unknown() -> None:
    idle, _ = qualified_idle(
        "mainA", run=lambda *_a, **_kw: _result(_payload(decided=False)))
    assert idle is False


@pytest.mark.parametrize("raw", [
    "not-json", '{"runtime_decided":true', "", "[]",
    '{"runtime_decided":true,"runtime_decided":false,"runtime_state":"idle",'
    '"nudge_ok":true}',
    '{"runtime_decided":true,"runtime_state":"idle","nudge_ok":false,'
    '"nudge_ok":true}',
    '{"runtime_decided":true,"runtime_state":"active","runtime_state":"idle",'
    '"nudge_ok":true}',
])
def test_malformed_truncated_or_wrong_shape_json_is_unknown(raw: str) -> None:
    idle, _ = qualified_idle("mainA", run=lambda *_a, **_kw: _result(raw))
    assert idle is False


def test_nonzero_probe_is_unknown_even_with_positive_looking_json() -> None:
    idle, _ = qualified_idle(
        "mainA", run=lambda *_a, **_kw: _result(_payload(), returncode=1))
    assert idle is False


def test_new_runtime_vocabulary_and_missing_authority_are_unknown() -> None:
    idle, _ = qualified_idle(
        "mainA", run=lambda *_a, **_kw: _result(_payload(state="new-runtime-state")))
    assert idle is False
    idle, _ = qualified_idle(
        "mainA", run=lambda *_a, **_kw: _result('{"runtime_state":"idle","nudge_ok":true}'))
    assert idle is False


@pytest.mark.parametrize("raw", [
    '{"runtime_decided":1,"runtime_state":"idle","nudge_ok":true}',
    '{"runtime_decided":"true","runtime_state":"idle","nudge_ok":true}',
    '{"runtime_decided":true,"runtime_state":"idle","nudge_ok":1}',
    '{"runtime_decided":true,"runtime_state":"idle","nudge_ok":"true"}',
])
def test_wrong_boolean_types_never_qualify(raw: str) -> None:
    idle, _ = qualified_idle("mainA", run=lambda *_a, **_kw: _result(raw))
    assert idle is False


def test_timeout_is_unknown() -> None:
    def timeout(*_args, **_kwargs):
        raise subprocess.TimeoutExpired("probe", 15)

    idle, reason = qualified_idle("mainA", run=timeout)
    assert idle is False
    assert "timed out" in reason


def test_unreadable_probe_is_unknown() -> None:
    def unreadable(*_args, **_kwargs):
        raise FileNotFoundError("adapter unavailable")

    idle, reason = qualified_idle("mainA", run=unreadable)
    assert idle is False
    assert "invocation failed" in reason


def test_probe_invocation_is_read_only_and_uses_injected_adapter(tmp_path: Path) -> None:
    adapter = tmp_path / "probe-shim.py"
    seen: list[list[str]] = []

    def injected(argv, **_kwargs):
        seen.append(argv)
        return _result(_payload())

    idle, _ = qualified_idle("mainA", adapter=adapter, run=injected)
    assert idle is True
    assert seen[0][-5:] == [str(adapter), "probe", "--agent", "mainA", "--json"]
    assert "nudge" not in seen[0]


def test_prefilter_success_does_not_bypass_final_nudge_guard(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A qualified first read cannot authorize a later nudge by itself."""
    qualified, _ = qualified_idle("mainA", run=lambda *_a, **_kw: _result(_payload()))
    assert qualified is True

    adapter_path = Path(__file__).resolve().parents[1] / "tmux_adapter.py"
    spec = importlib.util.spec_from_file_location("ni44_final_guard_adapter", adapter_path)
    assert spec is not None and spec.loader is not None
    adapter = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = adapter
    spec.loader.exec_module(adapter)
    adapter.LEDGER = tmp_path / "adapter-ledger.jsonl"
    monkeypatch.setattr(adapter, "load_config", lambda: {})
    monkeypatch.setattr(adapter, "probe", lambda *_a: {
        "nudge_ok": False, "target": "throwaway:pane", "seconds_since_last_nudge": None,
        "blockers": ["state changed after the observer probe"],
    })

    class Args:
        agent = "mainA"
        message = "drain the bus"
        min_interval_s = 20.0
        dry_run = False
        quiet_s = 20.0
        heartbeat_max_age = 900.0
        settle_s = 0.0

    assert adapter.cmd_nudge(Args()) == adapter.EX_BLOCKED


def _offline_shims(tmp_path: Path) -> tuple[Path, Path]:
    """Install inert tmux/sleep commands and a stateful JSON adapter shim."""
    bindir = tmp_path / "bin"
    bindir.mkdir()
    tmux = bindir / "tmux"
    tmux.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = has-session ]; then exit 0; fi\n"
        "printf '%s\\n' \"$*\" >> \"$NI44_TMUX_CALLS\"\n"
        "exit 9\n", encoding="utf-8")
    sleep = bindir / "sleep"
    sleep.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    tmux.chmod(0o755)
    sleep.chmod(0o755)

    adapter = tmp_path / "adapter-shim.py"
    adapter.write_text(
        "import json, os, pathlib, sys\n"
        "args = sys.argv[1:]\n"
        "op = args[0]\n"
        "calls = pathlib.Path(os.environ['NI44_ADAPTER_CALLS'])\n"
        "with calls.open('a', encoding='utf-8') as f: f.write(op + '\\n')\n"
        "if op == 'probe':\n"
        "    states_path = pathlib.Path(os.environ['NI44_STATES'])\n"
        "    states = json.loads(states_path.read_text(encoding='utf-8'))\n"
        "    cursor_path = pathlib.Path(os.environ['NI44_CURSOR'])\n"
        "    n = int(cursor_path.read_text() or '0') if cursor_path.exists() else 0\n"
        "    state = states[min(n, len(states) - 1)]\n"
        "    cursor_path.write_text(str(n + 1), encoding='utf-8')\n"
        "    print(json.dumps({'runtime_decided': state.get('decided', True),\n"
        "                      'runtime_state': state.get('runtime_state'),\n"
        "                      'nudge_ok': state.get('nudge_ok', True)}))\n"
        "    raise SystemExit(int(os.environ.get('NI44_PROBE_EXIT', '0')))\n"
        "if op == 'nudge':\n"
        "    print('REFUSING to nudge: final guard state changed after observer probe')\n"
        "    raise SystemExit(2)\n"
        "raise SystemExit(64)\n", encoding="utf-8")
    return bindir, adapter


def _offline_env(tmp_path: Path, states: list[dict]) -> dict[str, str]:
    bindir, adapter = _offline_shims(tmp_path)
    env = os.environ.copy()
    env.update({
        "PATH": f"{bindir}:{env['PATH']}",
        "EPYC_TMUX_ADAPTER": str(adapter),
        "NI44_STATES": str(tmp_path / "states.json"),
        "NI44_CURSOR": str(tmp_path / "cursor"),
        "NI44_ADAPTER_CALLS": str(tmp_path / "adapter-calls.log"),
        "NI44_TMUX_CALLS": str(tmp_path / "tmux-calls.log"),
        "LOG": str(tmp_path / "idle-supervisor.log"),
        "SESSION": "offline-fixture",
    })
    Path(env["NI44_STATES"]).write_text(json.dumps(states), encoding="utf-8")
    return env


def test_idle_watch_drift_reports_unknown_and_never_idle(tmp_path: Path) -> None:
    env = _offline_env(tmp_path, [{"runtime_state": "new-runtime-vocabulary"}])
    env["MAINS"] = "mainA mainB"
    result = subprocess.run(["bash", str(IDLE_WATCH), "1", "1"], cwd=REPO_ROOT,
                            env=env, capture_output=True, text=True, timeout=10)
    assert result.returncode == 1
    assert "UNKNOWN: mainA mainB" in result.stdout
    assert "IDLE:" not in result.stdout
    assert not Path(env["NI44_TMUX_CALLS"]).exists()


def test_idle_watch_zero_window_exits_without_unset_unknown(tmp_path: Path) -> None:
    env = _offline_env(tmp_path, [])
    result = subprocess.run(["bash", str(IDLE_WATCH), "1", "0"], cwd=REPO_ROOT,
                            env=env, capture_output=True, text=True, timeout=10)
    assert result.returncode == 1
    assert "NO_IDLE_WITHIN 0s" in result.stdout
    assert "unbound variable" not in result.stderr


@pytest.mark.parametrize("state", ["unavailable", "working", "compacting"])
def test_idle_supervisor_unqualified_probe_never_reaches_nudge(
        tmp_path: Path, state: str) -> None:
    env = _offline_env(tmp_path, [{"runtime_state": state}])
    env.update({"MAINS": "mainA"})
    result = subprocess.run(["bash", str(IDLE_SUPERVISOR), "1", "1", "1"],
                            cwd=REPO_ROOT, env=env, capture_output=True, text=True,
                            timeout=10)
    assert result.returncode == 0
    calls = Path(env["NI44_ADAPTER_CALLS"]).read_text(encoding="utf-8").splitlines()
    assert calls == ["probe"]
    assert "RE-NUDGED" not in result.stdout


def test_idle_supervisor_two_qualified_polls_still_hit_final_guard_refusal(
        tmp_path: Path) -> None:
    env = _offline_env(tmp_path, [
        {"runtime_decided": True, "runtime_state": "idle", "nudge_ok": True},
    ])
    env["MAINS"] = "mainA"
    result = subprocess.run(["bash", str(IDLE_SUPERVISOR), "1", "2", "2"],
                            cwd=REPO_ROOT, env=env, capture_output=True, text=True,
                            timeout=10)
    assert result.returncode == 0
    calls = Path(env["NI44_ADAPTER_CALLS"]).read_text(encoding="utf-8").splitlines()
    assert calls == ["probe", "probe", "nudge"]
    assert "REFUSED mainA" in result.stdout
    assert "RE-NUDGED mainA" not in result.stdout


@pytest.mark.parametrize("state", ["active", "working", "compacting", "blocked", "unavailable"])
def test_coordinator_leaf_returns_unknown_for_unqualified_runtime(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, state: str) -> None:
    _, adapter = _offline_shims(tmp_path)
    states = tmp_path / "states.json"
    states.write_text(json.dumps([{"runtime_state": state}]), encoding="utf-8")
    monkeypatch.setenv("EPYC_TMUX_ADAPTER", str(adapter))
    monkeypatch.setenv("NI44_STATES", str(states))
    monkeypatch.setenv("NI44_CURSOR", str(tmp_path / "cursor"))
    monkeypatch.setenv("NI44_ADAPTER_CALLS", str(tmp_path / "adapter-calls.log"))

    from scripts.coordination import session_bus_coordinator

    active, detail = session_bus_coordinator._pane_generating("mainA", [])
    assert active is None
    assert "did not qualify idle" in detail
