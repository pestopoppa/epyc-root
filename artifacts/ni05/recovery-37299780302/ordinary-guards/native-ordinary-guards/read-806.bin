"""Tests for orchestrator stack HTTP health-probe helper."""

from __future__ import annotations

import urllib.error
from contextlib import contextmanager


from scripts.server import stack_health
from scripts.server.stack_health import wait_for_health


class _Resp:
    def __init__(self, status: int) -> None:
        self.status = status


@contextmanager
def _ctx(status: int):
    yield _Resp(status)


def test_returns_true_on_first_200(monkeypatch) -> None:
    def fake_urlopen(url, timeout):
        assert url == "http://localhost:8000/health"
        return _ctx(200)
    monkeypatch.setattr(stack_health, "time", _FakeTime())
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    assert wait_for_health(8000, timeout=10) is True


def test_returns_false_after_timeout(monkeypatch) -> None:
    """Endpoint never responds — function must give up and return False."""
    def fake_urlopen(url, timeout):
        raise urllib.error.URLError("connection refused")
    fake_time = _FakeTime(start=0.0, increments=[0.0, 0.5, 1.5, 2.5, 3.5, 11.0])
    monkeypatch.setattr(stack_health, "time", fake_time)
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    assert wait_for_health(8000, timeout=10) is False


def test_uses_custom_path(monkeypatch) -> None:
    seen: dict = {}

    def fake_urlopen(url, timeout):
        seen["url"] = url
        return _ctx(200)
    monkeypatch.setattr(stack_health, "time", _FakeTime())
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    wait_for_health(9000, timeout=5, path="/sdapi/v1/samplers")
    assert seen["url"] == "http://localhost:9000/sdapi/v1/samplers"


def test_non_200_status_keeps_polling(monkeypatch) -> None:
    """503 in flight should not be treated as ready."""
    states = iter([503, 503, 200])

    def fake_urlopen(url, timeout):
        return _ctx(next(states))
    monkeypatch.setattr(stack_health, "time", _FakeTime())
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    assert wait_for_health(8000, timeout=10) is True


class _FakeTime:
    """Drop-in replacement for the `time` module — controllable clock with a no-op sleep."""

    def __init__(self, start: float = 0.0, increments: list[float] | None = None) -> None:
        self._now = start
        self._increments = list(increments) if increments else None

    def time(self) -> float:
        if self._increments:
            self._now = self._increments.pop(0)
        return self._now

    def sleep(self, _seconds: float) -> None:
        # No-op so the test doesn't actually wait.
        if not self._increments:
            self._now += 0.5
