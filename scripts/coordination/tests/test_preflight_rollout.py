"""Warn-first rollout counts use the same scope and grandfathering as --report."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "rowflow"))
import preflight as pf  # noqa: E402
import rowflow as rf  # noqa: E402


def test_rollout_counts_rows_and_grandfathers_publish_only(tmp_path, monkeypatch):
    flags = tmp_path / "flags"
    pass_dir = flags / "dryrun" / "smoked"
    pass_dir.mkdir(parents=True)
    (pass_dir / "PASS.json").write_text(json.dumps({"at": "2026-11-24T00:00:00Z"}))
    queued = {rid: {"id": rid} for rid in ("smoked", "fresh")}
    monkeypatch.setattr(pf, "report_scope", lambda path: (queued, {"excluded": "STOP-held"}))
    monkeypatch.setattr(pf, "node_map", lambda: None)
    monkeypatch.setattr(pf, "TMP_ROOT", str(tmp_path))
    for check in pf.CHECKS:
        monkeypatch.setitem(pf.CHECK_FNS, check, lambda row, ctx: [])
    monkeypatch.setitem(pf.PREFLIGHT_ENFORCE, "witness_decl", False)
    monkeypatch.setitem(pf.PREFLIGHT_ENFORCE, "store", True)
    monkeypatch.setitem(pf.CHECK_FNS, "witness_decl", lambda row, ctx: [
        ("FAIL", "ONE", "first"), ("FAIL", "TWO", "second")])
    monkeypatch.setitem(pf.CHECK_FNS, "selftest", lambda row, ctx: [("WARN", "ADVICE", "advisory")])
    lines = []
    before = dict(pf.PREFLIGHT_ENFORCE)
    counts = pf.rule_rollout_report(str(flags), out=lines.append)
    assert counts["witness_decl"] == 1  # two findings, one non-grandfathered row
    assert counts["selftest"] == 0  # advisory warnings are not failures
    assert "store" not in counts
    assert set(counts) == {c for c in pf.CHECKS if not before.get(c, False)}
    assert "witness_decl: failing=1" in lines
    assert "selftest: failing=0 READY TO ENFORCE" in lines
    assert pf.PREFLIGHT_ENFORCE == before


def test_rowflow_rollout_cli_and_json(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(pf, "report_scope", lambda flags: ({}, {}))
    monkeypatch.setattr(pf, "node_map", lambda: None)
    assert rf.main(["--flags", str(tmp_path), "preflight", "--rollout"]) == 0
    output = capsys.readouterr().out
    assert "rule changes frozen during AK pushes" in output
    assert "READY TO ENFORCE" in output
    assert rf.main(["--flags", str(tmp_path), "preflight", "--rollout", "--json"]) == 0
    counts = json.loads(capsys.readouterr().out)
    assert counts == {c: 0 for c in pf.CHECKS if not pf.PREFLIGHT_ENFORCE.get(c, False)}
