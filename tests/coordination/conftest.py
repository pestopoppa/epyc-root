"""Shared fixtures for tests/coordination."""
import pytest


@pytest.fixture(autouse=True)
def _isolated_holds_root(tmp_path, monkeypatch):
    """handoff_sessions `gate`/`unpark` write holds.yaml (handoff standard C3); never let a test touch the real tree."""
    (tmp_path / "_holds_root" / "handoffs" / "active").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("EPYC_HOLDS_ROOT", str(tmp_path / "_holds_root"))
