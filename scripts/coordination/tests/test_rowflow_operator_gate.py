"""Operator gate on row publication (operator-approved 2026-11-18): rows of operator-gated sessions and rows whose id
matches a registry operator_gated_row_prefixes entry are refused until operator-ratify/<name>.json exists."""
import json
import os
import sys

import pytest

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
import publish_row as pr  # noqa: E402
import rowflow as rf  # noqa: E402


@pytest.fixture(autouse=True)
def _isolated_hub(tmp_path, monkeypatch):
    """F4/F5: holds.yaml is read from the hub view; never let the live hub's holds leak into these fixtures."""
    sys.path.insert(0, os.path.dirname(_TESTS))
    import toolroot
    monkeypatch.setattr(toolroot, "HUB", str(tmp_path / "no-hub"))
    # C3: the repo now carries handoffs/active/holds.yaml; toolroot.resolve falls back to the checkout when the hub
    # has no copy, so give the fixture hub an empty one (these tests exercise the registry/prefix gate only).
    (tmp_path / "no-hub" / "handoffs" / "active").mkdir(parents=True, exist_ok=True)
    (tmp_path / "no-hub" / "handoffs" / "active" / "holds.yaml").write_text("holds: []\n")
    monkeypatch.setattr(pr, "REPO", str(tmp_path / "no-hub"))


@pytest.fixture
def flags(tmp_path):
    reg = {"operator_gated_row_prefixes": ["v11-"],
           "sessions": {"kp": {"handoff": "handoffs/active/kernel-promotion.md", "operator_gate": {"reason": "v11", "since": "x"}},
                        "ok": {"handoff": "handoffs/active/other.md"}}}
    (tmp_path / "handoff-sessions.json").write_text(json.dumps(reg))
    return str(tmp_path)


def ratify(flags, name, **kw):
    d = os.path.join(flags, "operator-ratify")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, f"{name}.json"), "w") as f:
        json.dump({"slug": name, "by": "operator", "at": "2026-11-18T00:00:00Z", "reason": "ok", **kw}, f)


def test_refuses_gated_prefix_row(flags):
    with pytest.raises(rf.Refused, match="OPERATOR-GATED.*v11-"):
        pr.check_operator_gate({"id": "v11-bench", "handoff_task": "other.md:T1"}, flags)


def test_refuses_gated_handoff_row(flags):
    with pytest.raises(rf.Refused, match="OPERATOR-GATED.*kp"):
        pr.check_operator_gate({"id": "kp-r1", "handoff_task": "kernel-promotion.md:T1"}, flags)


def test_main_exits_nonzero(flags, tmp_path, capsys):
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps({"id": "v11-x", "handoff_task": "other.md"}))
    assert pr.main([str(spec), "--flags", flags]) == 2
    assert "REFUSED: OPERATOR-GATED" in capsys.readouterr().out


def test_wrong_slug_ratification_rejected(flags):
    ratify(flags, "kp", slug="ok")
    with pytest.raises(rf.Refused, match="names slug"):
        pr.check_operator_gate({"id": "kp-r1", "handoff_task": "kernel-promotion.md"}, flags)


def test_allowed_after_ratification(flags):
    ratify(flags, "kp")
    ratify(flags, "rowprefix-v11-")
    pr.check_operator_gate({"id": "kp-r1", "handoff_task": "kernel-promotion.md:T1"}, flags)
    pr.check_operator_gate({"id": "v11-bench", "handoff_task": "other.md:T1"}, flags)


def test_ungated_rows_allowed(flags, tmp_path):
    pr.check_operator_gate({"id": "ok-r1", "handoff_task": "other.md:T1"}, flags)
    pr.check_operator_gate({"id": "v10-r1", "handoff_task": "other.md"}, str(tmp_path / "noflags"))  # no registry


def test_default_prefixes_and_promotion_handoff(tmp_path):
    (tmp_path / "handoff-sessions.json").write_text(json.dumps({"sessions": {}}))  # no prefix key: v11..v14 default
    f = str(tmp_path)
    for rid in ("v12-cut", "v14-x"):
        with pytest.raises(rf.Refused, match="OPERATOR-GATED"):
            pr.check_operator_gate({"id": rid, "handoff_task": "other.md"}, f)
    with pytest.raises(rf.Refused, match="production kernel promotion"):
        pr.check_operator_gate({"id": "x-r1", "handoff_task": "v11-promotion-cutover.md:T2"}, f)
    ratify(f, "rowprefix-v11-")
    pr.check_operator_gate({"id": "x-r1", "handoff_task": "v11-promotion-cutover.md:T2"}, f)


def test_champion_row_is_never_gated(tmp_path):
    (tmp_path / "handoff-sessions.json").write_text(json.dumps({"sessions": {}}))
    for rid in ("c14-fold-build-20261118", "promote-c15-keep", "promotion-c13-gate"):
        pr.check_operator_gate({"id": rid, "handoff_task": "kernel-champion-and-promotion.md:C14"}, str(tmp_path))


def test_scoped_release_admits_only_listed_rows(flags):
    ratify(flags, "kp", rows=["kp-meas-", "kp-exact-1"])
    pr.check_operator_gate({"id": "kp-meas-r2", "handoff_task": "kernel-promotion.md:T1"}, flags)
    pr.check_operator_gate({"id": "kp-exact-1", "handoff_task": "kernel-promotion.md:T1"}, flags)
    with pytest.raises(rf.Refused, match="outside the operator release scope"):
        pr.check_operator_gate({"id": "kp-loop-r1", "handoff_task": "kernel-promotion.md:T1"}, flags)


def test_unscoped_release_warns(flags, capsys):
    ratify(flags, "kp")
    pr.check_operator_gate({"id": "kp-r1", "handoff_task": "kernel-promotion.md:T1"}, flags)
    assert "UNSCOPED" in capsys.readouterr().err


def test_scoped_rowprefix_release(flags):
    ratify(flags, "rowprefix-v11-", rows=["v11-meas-"])
    pr.check_operator_gate({"id": "v11-meas-1", "handoff_task": "other.md:T1"}, flags)
    with pytest.raises(rf.Refused, match="outside"):
        pr.check_operator_gate({"id": "v11-bench", "handoff_task": "other.md:T1"}, flags)
