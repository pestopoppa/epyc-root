"""Ingestion preflight and ODL identity controls; no model or corpus execution."""
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))
import cli


@pytest.mark.parametrize("adapter,label", [("inf70", "INF-70"), ("autokernel", "AutoKernel")], ids=["inf70", "autokernel"])
@pytest.mark.parametrize("mode", [[], ["--dry-run"], ["--only-new"]], ids=["write", "dry-run", "only-new"])
def test_missing_corpus_never_materializes_ledger(adapter, label, mode, tmp_path, monkeypatch, capsys):
    def forbidden(*args, **kwargs):
        raise AssertionError("missing corpus must not construct or lock a ledger")
    monkeypatch.setattr(cli, "_ledger", forbidden)
    missing = tmp_path / "absent"
    assert cli.main(["ingest", adapter, "--root", str(missing), "--as-of", "2026-10-21T00:00:00Z", *mode]) == 2
    assert f"no such {label} corpus root: {missing}" in capsys.readouterr().err
    # Exercise the actual script entry point without any /mnt/raid0 dependency.
    ledger_dir = tmp_path / "must-not-materialize"
    direct = subprocess.run([sys.executable, str(ROOT / "scripts" / "vidya" / "cli.py"),
                             "--ledger", str(ledger_dir / "ledger.jsonl"),
                             "ingest", adapter, "--root", str(missing), "--as-of", "2026-10-21T00:00:00Z", *mode],
                            cwd=tmp_path, capture_output=True, text=True, timeout=30)
    assert direct.returncode == 2, direct.stdout + direct.stderr
    assert f"no such {label} corpus root: {missing}" in direct.stderr
    assert not ledger_dir.exists()


@pytest.mark.parametrize("first", ["adapters.odl_model_gated", "scripts.vidya.adapters.odl_model_gated"], ids=["direct-first", "package-first"])
def test_odl_import_orders_reuse_one_registered_module(first):
    # Fresh interpreters prevent sys.modules from hiding import-order regressions.
    code = r"""
import importlib
from pathlib import Path
import sys
root = Path(sys.argv[1])
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / "scripts" / "vidya"))
first = importlib.import_module(sys.argv[2])
from ingest_sources import SOURCES
matches = [s for s in SOURCES.values() if s.module == "odl_model_gated"]
assert matches and all(s.load() is first for s in matches)
assert importlib.import_module("adapters.odl_model_gated") is first
assert importlib.import_module("scripts.vidya.adapters.odl_model_gated") is first
from claim_tuple import ProjectionError, register
name = "test-cli-ingest-genuine-duplicate"
def original(native): pass
def different(native): pass
register(name)(original)
try:
    register(name)(different)
except ProjectionError:
    pass
else:
    raise AssertionError("genuine duplicate registration must refuse")
"""
    result = subprocess.run([sys.executable, "-c", code, str(ROOT), first],
                            cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("adapter", ["inf70", "autokernel"])
def test_existing_corpus_retains_writer_lock(adapter, tmp_path, monkeypatch):
    from contextlib import contextmanager
    from types import SimpleNamespace
    events = []
    class FakeLedger:
        @contextmanager
        def write_lock(self):
            events.append("locked")
            yield
            events.append("unlocked")
    def dispatch(args):
        assert events == ["locked"]
        events.append("dispatched")
        return 0
    monkeypatch.setattr(cli, "_ledger", lambda args: FakeLedger())
    monkeypatch.setattr(cli, "_cmd_ingest", dispatch)
    args = SimpleNamespace(adapter=adapter, root=str(tmp_path), dry_run=False, only_new=False)
    assert cli.cmd_ingest(args) == 0
    assert events == ["locked", "dispatched", "unlocked"]
