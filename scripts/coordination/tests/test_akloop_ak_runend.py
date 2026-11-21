#!/usr/bin/env python3
"""AKPL-P3 wiring: ak_runend (watcher ENDED hook) and the keeper's record_fail failure classifier. Temp dirs only."""
import json
import os
import sys
from types import SimpleNamespace

_COORD = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_COORD, "akloop"))
sys.path.insert(0, os.path.join(_COORD, "rowflow"))
import ak_runend as AR  # noqa: E402


class FakeNotify:
    def __init__(self):
        self.calls = []

    def emit(self, flags, kind, rid, disc, summary, severity, **kw):
        self.calls.append((kind, rid, disc))
        return {"kind": kind}

    def smoke_fail(self, *a, **k):
        return None


def _row(tmp_path, rid, result):
    flags = tmp_path / "flags"
    rp = tmp_path / f"{rid}.RESULT.json"
    if result is not None:
        rp.write_text(json.dumps(result))
    (flags / "ready").mkdir(parents=True, exist_ok=True)
    (flags / "ready" / f"{rid}.json").write_text(json.dumps({"id": rid, "owner": "autokernel", "result_path": str(rp)}))
    return str(flags)


def test_chain_row_files_with_gate_eval_and_routes_harness(tmp_path):
    flags = _row(tmp_path, "akc-x-oracle-kld-20261121", {"complete": True, "verdict": "FUTILITY_RESIDENCY (proof)"})
    seen, nm = [], FakeNotify()
    run = lambda argv, **k: seen.append(argv) or SimpleNamespace(stdout="AUTO-FILE akc-x: FAIL\n", returncode=0)
    rep = AR.handle("akc-x-oracle-kld-20261121", flags, runend_run=run, notify_mod=nm)
    assert seen and seen[0][-3:] == ["akc-x-oracle-kld-20261121", "--gate-eval", "--file"]
    assert rep["filed"].startswith("AUTO-FILE") and rep["class"]["side"] == "harness" and rep["class"]["routed"]
    assert nm.calls and nm.calls[0][0] == "ak-harness-failure"
    assert "lineage" not in rep


def test_candidate_failure_is_not_routed(tmp_path):
    flags = _row(tmp_path, "akc-x-ab-timing-20261121", {"complete": True, "verdict": "FAIL_NO_GAIN", "polar": "FAIL"})
    nm = FakeNotify()
    rep = AR.handle("akc-x-ab-timing-20261121", flags, runend_run=lambda a, **k: SimpleNamespace(stdout="", returncode=0),
                    notify_mod=nm)
    assert rep["class"]["side"] == "candidate" and not nm.calls


def test_composite_row_triggers_lineage_and_no_filing(tmp_path):
    flags = _row(tmp_path, "c18-fold-gpu-20261121-r1", {"complete": True, "verdict": "PASS", "polar": "PASS"})
    got = []
    rep = AR.handle("c18-fold-gpu-20261121-r1", flags, runend_run=lambda *a, **k: (_ for _ in ()).throw(AssertionError),
                    lineage=lambda rid: got.append(rid) or "/tmp/lin", notify_mod=FakeNotify())
    assert got == ["c18-fold-gpu-20261121-r1"] and rep["lineage"] == "/tmp/lin" and "filed" not in rep
    assert "AK-RUNEND c18-fold-gpu-20261121-r1" in AR.line(rep)


def test_dry_run_runs_nothing(tmp_path):
    flags = _row(tmp_path, "akc-x-build-20261121", None)
    rep = AR.handle("akc-x-build-20261121", flags, dry_run=True,
                    runend_run=lambda *a, **k: (_ for _ in ()).throw(AssertionError))
    assert rep["filed"].startswith("dry-run") and rep["class"]["klass"] == "result_contract"
    assert "routed" not in rep["class"]


def test_record_fail_classifies_ak_rows_only(tmp_path, monkeypatch):
    import rowflow as rf
    nm = FakeNotify()
    monkeypatch.setattr(rf, "notify", nm)
    flags = str(tmp_path / "flags")
    os.makedirs(os.path.join(flags, "dryrun", "akc-x-build-20261121"))
    launcher = tmp_path / "launch.sh"
    launcher.write_text("#!/bin/bash\n")
    d = {"launcher": {"path": str(launcher)}, "owner": "pipeline-mgmt"}
    monkeypatch.setattr(rf, "row_sha", lambda flags, rid: "x")
    rec = rf.record_fail(flags, "akc-x-build-20261121", d, "smoke_predicate `test -s x` never exited 0", {})
    assert rec["failclass"]["side"] == "harness" and rec["failclass"]["routed"]
    assert ("ak-harness-failure", "akc-x-build-20261121") == nm.calls[0][:2]
    os.makedirs(os.path.join(flags, "dryrun", "other-row-20261121"))
    rec2 = rf.record_fail(flags, "other-row-20261121", d, "smoke_predicate `x` never exited 0", {})
    assert "failclass" not in rec2
    on_disk = json.load(open(os.path.join(flags, "dryrun", "akc-x-build-20261121", "FAIL-1.json")))
    assert on_disk["failclass"]["klass"] == "smoke_wiring"


if __name__ == "__main__":
    raise SystemExit("REFUSING: pytest-fixture suite; run: python -m pytest scripts/coordination/tests/test_akloop_ak_runend.py -q")
