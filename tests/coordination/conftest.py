"""Shared fixtures for tests/coordination."""
import pytest


@pytest.fixture(autouse=True)
def _isolated_holds_root(tmp_path_factory, monkeypatch):
    tmp_path = tmp_path_factory.mktemp("holdsroot")   # never inside the test's own tmp_path (scanners count it)
    """handoff_sessions `gate`/`unpark` write holds.yaml (handoff standard C3); never let a test touch the real tree."""
    (tmp_path / "_holds_root" / "handoffs" / "active").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("EPYC_HOLDS_ROOT", str(tmp_path / "_holds_root"))
    import sys as _s, os as _o
    _root = _o.path.abspath(__file__)
    for _ in range(3):
        _root = _o.path.dirname(_root)
    _s.path.insert(0, _o.path.join(_root, "scripts", "coordination"))
    (tmp_path / "_holds_root" / "handoffs" / "active" / "holds.yaml").write_text("holds: []\n")   # valid, empty
    try:
        import toolroot
        monkeypatch.setattr(toolroot, "HUB", str(tmp_path / "_holds_root"))   # publish_row reads holds hub-first
    except ImportError:
        pass
