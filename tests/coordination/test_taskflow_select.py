"""taskflow/select.py: the box-level selector over .box-index.json (each skip rule + ordering + a real fixture build)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "coordination"))
sys.path.insert(0, str(ROOT / "scripts" / "handoffs"))
from taskflow import select as S  # noqa: E402
import box_index as BI  # noqa: E402


HS = "handoffs/active/holds.yaml"   # C3: select fails closed without a holds source


def rec(**kw):
    base = {"file": "handoffs/active/a.md", "line": 10, "state": "open", "class": "non-inference", "holds": [],
            "gate_open": False, "inputs_missing": [], "outside_backlog": False, "lint": {"ok": True, "fails": []},
            "row_rank": 5, "pos_in_backlog": 1, "text": "- [ ] **A-1** x"}
    base.update(kw)
    return base


def test_each_skip_rule():
    cases = {"state-frozen": rec(state="frozen"), "state-rollup": rec(state="rollup"),
             "state-needs-owner": rec(state="needs-owner"), "class-operator-decision": rec(**{"class": "operator-decision"}),
             "held": rec(holds=["H-AK"]), "gate-open": rec(gate_open=True), "inputs-missing": rec(inputs_missing=["x"]),
             "outside-backlog": rec(outside_backlog=True), "lint-fail": rec(lint={"ok": False, "fails": ["a"]}),
             "excluded-file": rec(file="handoffs/active/inflight.md"), "proposal-pending": rec(proposed_by="taskflow x")}
    for want, r in cases.items():
        assert S.skip_reason(r, {"inflight.md"}) == want
    assert S.skip_reason(rec(), set()) is None


def test_priority_then_backlog_position():
    doc = {"boxes": {"late": rec(row_rank=9, pos_in_backlog=1),
                     "second": rec(row_rank=2, pos_in_backlog=2, line=5),
                     "first": rec(row_rank=2, pos_in_backlog=1, line=50),
                     "unranked": rec(row_rank=None),
                     "blocked": rec(row_rank=1, gate_open=True)}, "holds_source": HS}
    nxt, hist = S.select(doc)
    assert nxt[0] == "first"
    keys = [k for k, _ in S.candidates(doc)[0]]
    assert keys == ["first", "second", "late", "unranked"] and hist["gate-open"] == 1


def test_in_flight_handoff_capped():
    doc = {"boxes": {"a1": rec(), "b1": rec(file="handoffs/active/b.md", row_rank=6)}, "holds_source": HS}
    assert S.select(doc, in_flight={"a.md"})[0][0] == "b1"


def test_end_to_end_on_fixture_build(tmp_path, monkeypatch):
    monkeypatch.setenv("EPYC_HOLDS_ROOT", str(tmp_path))
    (tmp_path / "handoffs" / "active").mkdir(parents=True)
    (tmp_path / "handoffs" / "active" / "holds.yaml").write_text("holds: []\n")
    f = tmp_path / "handoffs" / "active" / "fx.md"
    f.write_text("# F\n**Status**: ACTIVE — x\n\n## Track: t\n\n### Backlog\n\n"
                 "- [ ] **F-1** [non-inference] gated box\n      · done when: pytest a passes\n      · gate: F-2\n"
                 "- [ ] **F-2** [non-inference] fix the parser\n      · done when: pytest b passes\n"
                 "- [ ] **F-3** [non-inference] later\n      · done when: pytest c passes\n      · ❄ frozen until: OP-1\n")
    doc = BI.build(tmp_path, {"fx.md": f}, {"fx.md": "TST-1"}, {"TST-1": True}, {"rows": {"TST-1": {"rank": 1}}})
    nxt, hist = S.select(doc)
    assert nxt[0] == "F-2" and hist["gate-open"] == 1 and hist["state-frozen"] == 1
