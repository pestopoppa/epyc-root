"""PROPOSED ROOT tests/vidya/test_ingest_root_precondition.py; NOT RUN.

Two adapters x three modes + valid normal-mode serialization (8 cases).
No real corpus, canonical ledger, native transport or model.
"""
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
import pytest

# This file is installed only in a reviewed private ROOT clone before grant tests.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))
import cli

@pytest.mark.parametrize("adapter", ["inf70", "autokernel"])
@pytest.mark.parametrize("dry,only_new", [(False, False), (True, False), (False, True)])
def test_missing_root_never_constructs_ledger(tmp_path, adapter, dry, only_new, capsys):
    args = SimpleNamespace(adapter=adapter, root=str(tmp_path / "missing"),
                           dry_run=dry, only_new=only_new)
    with patch.object(cli, "_ledger", side_effect=AssertionError("ledger constructed")), \
         patch.object(cli, "_cmd_ingest", side_effect=AssertionError("dispatch reached")):
        assert cli.cmd_ingest(args) == 2
    assert "no such" in capsys.readouterr().err
    assert not list(tmp_path.iterdir())

@pytest.mark.parametrize("adapter", ["inf70", "autokernel"])
def test_valid_root_retains_write_lock(tmp_path, adapter):
    events = []
    class Lock:
        def __enter__(self): events.append("locked")
        def __exit__(self, *args): events.append("released")
    led = SimpleNamespace(write_lock=lambda: Lock())
    args = SimpleNamespace(adapter=adapter, root=str(tmp_path), dry_run=False, only_new=False)
    def dispatch(actual):
        assert actual is args
        assert events == ["locked"]
        events.append("dispatched")
        return 0
    construct = Mock(return_value=led)
    with patch.object(cli, "_ledger", construct), patch.object(cli, "_cmd_ingest", dispatch):
        assert cli.cmd_ingest(args) == 0
    construct.assert_called_once_with(args)
    assert events == ["locked", "dispatched", "released"]
