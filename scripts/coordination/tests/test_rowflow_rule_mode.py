"""Warn-first keeper rules use only temporary flag directories."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rowflow"))
import rowflow as rf


def test_rule_mode_counts_promotion_and_freeze(tmp_path, monkeypatch):
    flags = str(tmp_path)
    manifests = {"bad": {"decision_rule": " "}, "good": {"decision_rule": "PASS"},
                 "finished": {"decision_rule": ""}}
    states = {"bad": {"state": "needs-dryrun"}, "good": {"state": "armed"},
              "finished": {"state": "done"}}
    monkeypatch.setattr(rf, "rows", lambda flags: manifests)
    monkeypatch.setattr(rf, "status", lambda flags, rid, allrows: states[rid])
    assert rf.rule_modes(flags)["decision_rule_present"] == "warn"
    assert rf.rule_failures(flags, manifests)["decision_rule_present"] == {"bad"}
    with pytest.raises(rf.Refused, match="would fail 1 queued rows"):
        rf.set_rule_mode(flags, "decision_rule_present", "enforce")
    manifests["bad"]["decision_rule"] = "PASS"
    (tmp_path / "RULES-FREEZE").touch()
    with pytest.raises(rf.Refused, match="frozen"):
        rf.set_rule_mode(flags, "decision_rule_present", "enforce")
    (tmp_path / "RULES-FREEZE").unlink()
    rf.set_rule_mode(flags, "decision_rule_present", "enforce")
    assert rf.rule_modes(flags)["decision_rule_present"] == "enforce"
    (tmp_path / "RULES-FREEZE").touch()
    with pytest.raises(rf.Refused, match="frozen"):
        rf.set_rule_mode(flags, "decision_rule_present", "warn")


def test_rule_mode_snapshot_and_enforcement(tmp_path, monkeypatch):
    flags = str(tmp_path)
    row = {"id": "bad", "lane": "cpu", "window_s": 60, "decision_rule": ""}
    monkeypatch.setattr(rf, "rows", lambda flags: {"bad": row})
    monkeypatch.setattr(rf, "status", lambda *args, **kwargs: {"state": "grantable"})
    monkeypatch.setattr(rf, "rl_status", lambda: {})
    monkeypatch.setattr(rf, "open_grants", lambda flags: [])
    monkeypatch.setattr(rf, "host_snapshot", lambda *args: (set(), set(), {}))
    monkeypatch.setattr(rf, "contract_of", lambda *args, **kwargs: {"bench": False, "options": [], "shape": "quarter", "lock": "", "claim": "", "threads": 1, "explicit_cpus": False})
    monkeypatch.setattr(rf, "resumable_window_s", lambda *args: None)
    monkeypatch.setattr(rf, "book_s", lambda row: 60)
    lines = []
    rf.allocate(flags, log=lines.append, dry=True)
    assert any(line.startswith("SNAPSHOT ") and "rule_would_fail=decision_rule_present:1" in line and "cands=1" in line for line in lines)
    path = tmp_path / "ws58-keeper-state" / "rule_modes.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps({"decision_rule_present": "enforce"}))
    lines.clear()
    rf.allocate(flags, log=lines.append, dry=True)
    assert any(line.startswith("SNAPSHOT ") and "cands=0" in line for line in lines)
