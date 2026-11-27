"""Run the original W66 tests and probe a substituted continuation receipt."""
import hashlib
import importlib
import json
from pathlib import Path
import runpy
import sys

import pytest


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    oracle_path, scratch, selected_mode, evidence = sys.argv[1:]
    base = Path(scratch).resolve()
    output = Path(evidence)
    oracle = runpy.run_path(oracle_path)

    class Probe(oracle["ObserveIsolation"]):
        def __init__(self):
            super().__init__(base)
            self.validated = set()
            self.routing = None
            self.serial_receives_replacement = False

        def pytest_runtest_call(self, item):
            super().pytest_runtest_call(item)
            if "runtime_keep_then_source" not in item.name:
                return
            monkeypatch = item.funcargs["monkeypatch"]
            fixture = item.module.run_fixture
            run = fixture.__globals__["run"]
            serial = item.module.serial_run
            journal = importlib.import_module(f"{item.module.__package__}.phase_journal")
            assert run.main is fixture.__globals__["_PUBLIC_RUN_MAIN"]
            original_verify = journal._verify_terminal
            original_main = run._main
            original_batch = serial._batch_argv

            def observe_journal(row, store):
                original_verify(row, store)
                if (row["event"] == "COMPLETE" and row["phase"] == "integration"
                        and row["mutation"]["kind"] == "runtime"):
                    loc, _, sha = row["result"].rpartition("#")
                    self.validated.add((str(Path(loc).resolve()), sha))

            def after_real_main(argv):
                rc = original_main(argv)
                assert rc == 0 and self.validated
                store = Path(serial.option(argv, "--store")).resolve()
                out = Path(serial.option(argv, "--out")).resolve()
                assert store.is_relative_to(base.parent) and out.is_relative_to(base.parent)
                detailed = out / "loop-run.json"
                standalone = out / "loop-continuation.json"
                result = json.loads(detailed.read_bytes())
                continuation = json.loads(standalone.read_bytes())
                ref = continuation["runtime_recipe_reference"]
                assert result["continuation"]["runtime_recipe_reference"] == ref
                retained = (store / "runtime-preparation" / ref["locator"]).resolve()
                retained_bytes = retained.read_bytes()
                assert digest(retained_bytes) == ref["sha256"]
                original_payload = journal._read_proof(store, str(retained), ref["sha256"])
                self.routing = {
                    "real_main_module": run.__name__, "phase_verified_before_change": True,
                    "original": ref, "original_read_proof_verified": True,
                    "original_journal_matches": (str(retained), ref["sha256"]) in self.validated,
                    "verified_runtime_journal_references": [
                        {"locator": Path(path).name, "sha256": sha} for path, sha in sorted(self.validated)
                    ],
                }
                if selected_mode == "mutated":
                    alternate = retained.with_name("w66-substituted-selection-receipt.json")
                    with alternate.open("xb") as handle:
                        # Same JSON values, different bytes and therefore a different valid digest.
                        handle.write(retained_bytes + b"\n")
                    new_ref = {"locator": alternate.name, "sha256": digest(alternate.read_bytes()),
                               "verified": True}
                    alternate_payload = journal._read_proof(store, str(alternate), new_ref["sha256"])
                    assert original_payload == alternate_payload and new_ref != ref
                    result["continuation"]["runtime_recipe_reference"] = new_ref
                    continuation["runtime_recipe_reference"] = new_ref
                    assert result["continuation"]["runtime_recipe_reference"] == continuation["runtime_recipe_reference"]
                    detailed.write_text(json.dumps(result) + "\n")
                    standalone.write_text(json.dumps(continuation) + "\n")
                    self.routing.update(replacement=new_ref, same_content=True,
                                        same_recipe_sha256=digest(json.dumps(
                                            alternate_payload["current_recipe"], sort_keys=True).encode()))
                return rc

            def observe_serial(*args, **kwargs):
                launched = original_batch(*args, **kwargs)
                if self.routing and selected_mode == "mutated":
                    path = Path(serial.option(launched, "--runtime-recipe-reference")).resolve()
                    assert path.is_relative_to(base.parent)
                    reference = json.loads(path.read_bytes())
                    assert reference == self.routing["replacement"]
                    self.serial_receives_replacement = True
                return launched

            monkeypatch.setattr(journal, "_verify_terminal", observe_journal)
            monkeypatch.setattr(run, "_main", after_real_main)
            monkeypatch.setattr(serial, "_batch_argv", observe_serial)

    plugin = Probe()
    rc = pytest.main(["-q", "-p", "no:cacheprovider", "--basetemp", str(base), "--tb=short",
                      *oracle["TESTS"]], plugins=[plugin])
    record = {
        "mode": selected_mode, "rc": int(rc), "oracle_claim_observations": plugin.calls,
        "journal_completion_observations": plugin.completions, "routing": plugin.routing,
        "serial_receives_replacement": plugin.serial_receives_replacement,
    }
    output.write_text(json.dumps(record, sort_keys=True, indent=2) + "\n")
    if plugin.calls != 2 or plugin.completions < 1 or plugin.routing is None:
        raise SystemExit("control failed to reach the two original test calls and journal verification")
    raise SystemExit(rc)


if __name__ == "__main__":
    main()
