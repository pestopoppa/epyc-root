"""Tests for orchestrator stack Docker container helpers."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass

from scripts.server import stack_docker
from scripts.server.stack_docker import (
    _docker_available,
    docker_container_running,
    start_docker_container,
    stop_docker_container,
)
from scripts.server.stack_state import ProcessInfo


@dataclass
class _Result:
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""


def _make_run_recorder(responses: dict[tuple, _Result] | list[_Result]):
    """Build a fake subprocess.run.

    If responses is a dict, look up by the docker subcommand tuple.
    If responses is a list, consume in call order.
    """
    calls: list[list[str]] = []

    def fake_run(cmd, *args, **kwargs):
        calls.append(list(cmd))
        if isinstance(responses, list):
            if not responses:
                return _Result(returncode=0)
            return responses.pop(0)
        # dict lookup by docker subcommand
        key = tuple(cmd[:2]) if len(cmd) >= 2 else tuple(cmd)
        if key in responses:
            return responses[key]
        # Fallback: a more specific match like ("docker", "rm", "-f", name)
        for k, v in responses.items():
            if list(k) == cmd[: len(k)]:
                return v
        return _Result(returncode=0)

    return fake_run, calls


def test_docker_available_true(monkeypatch) -> None:
    fake_run, _ = _make_run_recorder([_Result(returncode=0, stdout="20.10.0\n")])
    monkeypatch.setattr(subprocess, "run", fake_run)
    assert _docker_available() is True


def test_docker_available_false_when_cli_missing(monkeypatch) -> None:
    def fake_run(*a, **kw):
        raise FileNotFoundError("docker")
    monkeypatch.setattr(subprocess, "run", fake_run)
    assert _docker_available() is False


def test_docker_available_false_on_timeout(monkeypatch) -> None:
    def fake_run(*a, **kw):
        raise subprocess.TimeoutExpired("docker", 5)
    monkeypatch.setattr(subprocess, "run", fake_run)
    assert _docker_available() is False


def test_docker_container_running_true(monkeypatch) -> None:
    fake_run, calls = _make_run_recorder([_Result(returncode=0, stdout="true\n")])
    monkeypatch.setattr(subprocess, "run", fake_run)
    assert docker_container_running("nextplaid") is True
    assert calls[0][:3] == ["docker", "inspect", "-f"]


def test_docker_container_running_false_when_stopped(monkeypatch) -> None:
    fake_run, _ = _make_run_recorder([_Result(returncode=0, stdout="false\n")])
    monkeypatch.setattr(subprocess, "run", fake_run)
    assert docker_container_running("nextplaid") is False


def test_stop_docker_container_succeeds(monkeypatch) -> None:
    fake_run, calls = _make_run_recorder([_Result(returncode=0, stdout="nextplaid\n")])
    monkeypatch.setattr(subprocess, "run", fake_run)
    assert stop_docker_container("nextplaid") is True
    assert calls[0] == ["docker", "rm", "-f", "nextplaid"]


def test_stop_docker_container_returns_false_on_failure(monkeypatch) -> None:
    fake_run, _ = _make_run_recorder([_Result(returncode=1, stderr="no such container\n")])
    monkeypatch.setattr(subprocess, "run", fake_run)
    assert stop_docker_container("nope") is False


def test_start_docker_container_happy_path(monkeypatch) -> None:
    service = {
        "name": "searxng",
        "port": 8090,
        "image": "searxng/searxng:latest",
        "description": "metasearch",
        "volumes": ["/etc/searxng:/etc/searxng"],
        "args": ["--foo"],
    }
    # 1: docker rm -f (idempotent pre-cleanup)
    # 2: docker run -d ... (returns container id)
    responses = [
        _Result(returncode=0),
        _Result(returncode=0, stdout="abcdef1234567890\n"),
    ]
    fake_run, calls = _make_run_recorder(responses)
    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(stack_docker, "wait_for_health", lambda port, timeout, path: True)

    info = start_docker_container(service)
    assert isinstance(info, ProcessInfo)
    assert info.role == "searxng"
    assert info.port == 8090
    assert info.pid == -1
    assert info.model_path == "searxng/searxng:latest"
    # Verify docker run command had volume + image + args wired in
    run_cmd = calls[1]
    assert "docker" in run_cmd and "run" in run_cmd
    assert "-p" in run_cmd
    assert "8090:8080" in run_cmd
    assert "-v" in run_cmd
    assert "/etc/searxng:/etc/searxng" in run_cmd
    assert run_cmd[-2] == "searxng/searxng:latest"
    assert run_cmd[-1] == "--foo"


def test_start_docker_container_supports_nondefault_container_options(monkeypatch) -> None:
    service = {
        "name": "crawl4ai",
        "port": 11235,
        "container_port": 11235,
        "image": "unclecode/crawl4ai:latest",
        "description": "browser extraction",
        "shm_size": "1g",
        "run_timeout": 180,
        "env": {"BETA": "two", "ALPHA": "one"},
    }
    responses = [
        _Result(returncode=0),
        _Result(returncode=0, stdout="abcdef1234567890\n"),
    ]
    timeouts = []
    fake_run_inner, calls = _make_run_recorder(responses)

    def fake_run(cmd, *args, **kwargs):
        if cmd[:2] == ["docker", "run"]:
            timeouts.append(kwargs.get("timeout"))
        return fake_run_inner(cmd, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(stack_docker, "wait_for_health", lambda port, timeout, path: True)

    info = start_docker_container(service)

    assert isinstance(info, ProcessInfo)
    assert info.role == "crawl4ai"
    run_cmd = calls[1]
    assert run_cmd[:5] == ["docker", "run", "-d", "--name", "crawl4ai"]
    assert "--shm-size" in run_cmd
    assert "1g" in run_cmd
    assert "-p" in run_cmd
    assert "11235:11235" in run_cmd
    assert run_cmd.index("ALPHA=one") < run_cmd.index("BETA=two")
    assert run_cmd[-1] == "unclecode/crawl4ai:latest"
    assert timeouts == [180]


def test_start_docker_container_returns_none_on_run_timeout(monkeypatch) -> None:
    service = {
        "name": "crawl4ai",
        "port": 11235,
        "container_port": 11235,
        "image": "unclecode/crawl4ai:latest",
        "description": "browser extraction",
        "run_timeout": 180,
    }
    calls = []

    def fake_run(cmd, *args, **kwargs):
        calls.append(list(cmd))
        if cmd[:2] == ["docker", "run"]:
            assert kwargs.get("timeout") == 180
            raise subprocess.TimeoutExpired(cmd, 180)
        return _Result(returncode=0)

    def boom(*a, **kw):
        raise AssertionError("wait_for_health called after docker run timeout")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(stack_docker, "wait_for_health", boom)

    assert start_docker_container(service) is None
    assert calls[-1] == ["docker", "rm", "-f", "crawl4ai"]


def test_start_docker_container_returns_none_when_run_fails(monkeypatch) -> None:
    service = {"name": "x", "port": 1234, "image": "img", "description": "d"}
    responses = [
        _Result(returncode=0),
        _Result(returncode=1, stderr="image not found\n"),
    ]
    fake_run, _ = _make_run_recorder(responses)
    monkeypatch.setattr(subprocess, "run", fake_run)
    # wait_for_health must NOT be called when docker run fails
    def boom(*a, **kw):
        raise AssertionError("wait_for_health called after docker run failure")
    monkeypatch.setattr(stack_docker, "wait_for_health", boom)

    assert start_docker_container(service) is None


def test_start_docker_container_cleans_up_on_health_timeout(monkeypatch) -> None:
    """When health probe fails, container must be removed and result is None."""
    service = {"name": "y", "port": 5555, "image": "img", "description": "d"}
    responses = [
        _Result(returncode=0),                              # pre-cleanup rm
        _Result(returncode=0, stdout="containerid12\n"),    # run
        _Result(returncode=0, stdout="boot failed\n"),      # logs --tail 10
        _Result(returncode=0),                              # final rm -f
    ]
    fake_run, calls = _make_run_recorder(responses)
    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(stack_docker, "wait_for_health", lambda port, timeout, path: False)

    info = start_docker_container(service)
    assert info is None
    # Verify the cleanup rm -f happened (last call)
    assert calls[-1] == ["docker", "rm", "-f", "y"]
