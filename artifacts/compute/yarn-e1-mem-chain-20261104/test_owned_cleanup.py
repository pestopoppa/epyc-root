"""No-GPU regression for cleanup after an early chain-entry exception."""
import importlib.util
import subprocess
import signal
import sys
from pathlib import Path

def test_main_reaps_owned_child_on_early_entry_failure(monkeypatch):
    spec = importlib.util.spec_from_file_location("chain_under_test", Path(__file__).with_name("run_chain.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    child = subprocess.Popen(["/bin/cat"], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL)
    module.CHILDREN.append(child)
    def fail_entry(mode):
        raise OSError("synthetic sampler-entry failure")
    monkeypatch.setattr(module, "run", fail_entry)
    monkeypatch.setattr(sys, "argv", ["run_chain.py"])
    previous_handler = signal.getsignal(signal.SIGTERM)
    try:
        assert module.main() == 1
        assert child.poll() is not None
    finally:
        signal.signal(signal.SIGTERM, previous_handler)
        if child.poll() is None:
            child.kill()
            child.wait(timeout=5)
        child.stdin.close()
