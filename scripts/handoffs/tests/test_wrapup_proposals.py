"""C1 (handoff standard Stage C, decision 6): LLM proposals land as NEEDS-OWNER children; owners accept / edit / reject."""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "scripts" / "coordination"))
import box_index as BI  # noqa: E402
import handoff_box as HB  # noqa: E402
import propose_rewrites as PR  # noqa: E402
import task_lint as TL  # noqa: E402
from taskflow import select as S  # noqa: E402

DOC = ("# F\n**Status**: ACTIVE — x\n\n## Track: t\n\n### Backlog\n\n"
       "- [ ] **F-1** [non-inference] make the parser faster\n"
       "      · gate: none\n"
       "- [ ] **F-2** [non-inference] fix the scorer\n      · done when: pytest tests/test_s.py passes\n\n"
       "## History\n\n- 2026-11-01 started\n")


def _root(tmp_path):
    act = tmp_path / "handoffs/active"
    act.mkdir(parents=True)
    (act / "holds.yaml").write_text("holds: []\n")
    f = act / "f.md"
    f.write_text(DOC)
    return f


def _build(tmp_path, f):
    return BI.build(tmp_path, {"f.md": f}, {"f.md": "TST-1"}, {"TST-1": True}, {"rows": {"TST-1": {"rank": 1}}})


def _propose(f, tmp_path, **kw):
    a = argparse.Namespace(box="F-1", cls="non-inference", text="make the parser faster", inputs=None, tier=None,
                           owner=None, needs_owner=True, proposed_by="taskflow 2026-11-20T10:00Z", stop_rule=None,
                           done_when="`pytest tests/test_parser.py` passes", **kw)
    return HB.apply(f, "propose", a, tmp_path)


def test_propose_writes_needs_owner_child_and_never_edits_parent(tmp_path, monkeypatch):
    monkeypatch.setenv("EPYC_HOLDS_ROOT", str(tmp_path))
    f = _root(tmp_path)
    _propose(f, tmp_path)
    text = f.read_text()
    assert "- [ ] **F-1** [non-inference] make the parser faster\n      · gate: none\n" in text   # parent untouched
    assert "  - [ ] **F-1.p1** [non-inference] make the parser faster NEEDS-OWNER" in text
    assert "· proposed-by: taskflow 2026-11-20T10:00Z        · parent: F-1" in text
    doc = _build(tmp_path, f)
    child = doc["boxes"]["F-1.p1"]
    assert child["state"] == "needs-owner" and child["proposed_by"] and child["parent"] == "F-1" and not child["gate"]
    assert doc["counts"]["proposals_pending"] == 1
    assert S.skip_reason(child, set()) in ("state-needs-owner", "proposal-pending")
    _propose(f, tmp_path)
    assert "**F-1.p2**" in f.read_text()


def test_accept_by_deleting_needs_owner_makes_child_dispatchable(tmp_path, monkeypatch):
    monkeypatch.setenv("EPYC_HOLDS_ROOT", str(tmp_path))
    f = _root(tmp_path)
    _propose(f, tmp_path)
    f.write_text(f.read_text().replace(" NEEDS-OWNER\n", "\n").replace(
        "      · proposed-by: taskflow 2026-11-20T10:00Z        · parent: F-1", "        · parent: F-1"))
    child = _build(tmp_path, f)["boxes"]["F-1.p1"]
    assert child["state"] == "open" and not child["proposed_by"] and S.skip_reason(child, set()) in (None, "outside-backlog")


def test_edit_changes_continuation_only(tmp_path, monkeypatch):
    monkeypatch.setenv("EPYC_HOLDS_ROOT", str(tmp_path))
    f = _root(tmp_path)
    _propose(f, tmp_path)
    lines = f.read_text().split("\n")
    i = next(n for n, l in enumerate(lines) if "**F-1.p1**" in l)
    new = HB.set_field(lines, i, "done when", "`pytest tests/test_parser.py -k fast` passes")
    HB.guard_first_lines(lines, new)                                   # first line (identity) unchanged
    assert TL.parse_fields("\n".join(new[i:i + 4]))["done when"].startswith("`pytest tests/test_parser.py -k fast`")


def test_reject_moves_child_to_history_with_declined_tag(tmp_path, monkeypatch):
    monkeypatch.setenv("EPYC_HOLDS_ROOT", str(tmp_path))
    f = _root(tmp_path)
    _propose(f, tmp_path)
    HB.apply(f, "reject", argparse.Namespace(box="F-1.p1", by="mainA", reason="not the bottleneck", date="2026-11-21"),
             tmp_path)
    text = f.read_text()
    assert "**F-1.p1**" in text and "- [ ] **F-1.p1**" not in text
    hist = text.split("## History", 1)[1]
    assert "[declined: mainA 2026-11-21 not the bottleneck]" in hist and "**F-1.p1**" in hist
    assert "- [ ] **F-1** [non-inference] make the parser faster" in text


def test_reject_refuses_a_non_proposal(tmp_path, monkeypatch):
    monkeypatch.setenv("EPYC_HOLDS_ROOT", str(tmp_path))
    f = _root(tmp_path)
    try:
        HB.apply(f, "reject", argparse.Namespace(box="F-2", by="x", reason="y", date=None), tmp_path)
        raise AssertionError("rejected a non-proposal")
    except HB.BoxError:
        pass


def test_propose_rewrites_end_to_end_with_fake_model(tmp_path, monkeypatch):
    monkeypatch.setenv("EPYC_HOLDS_ROOT", str(tmp_path))
    f = _root(tmp_path)
    doc = _build(tmp_path, f)
    monkeypatch.setattr(PR.BI, "load", lambda root, regenerate=True: _build(tmp_path, f))
    calls = []

    def fake(prompt):
        calls.append(prompt)
        return json.dumps({"done_when": "`pytest tests/test_parser.py` passes", "rationale": "r"}), \
            {"input_tokens": 900, "cache_creation_input_tokens": 0, "output_tokens": 60}

    ledger = tmp_path / "ledger.jsonl"
    assert PR.main(["--ledger", str(ledger), "--stop-share", "1.0", "--recent-minutes", "0"], runner=fake,
                   root=tmp_path) == 0
    assert len(calls) == 1 and "F-1" in calls[0]                       # F-2 passes lint a: not proposed
    assert "**F-1.p1**" in f.read_text()
    rec = json.loads(ledger.read_text().splitlines()[0])
    assert rec["tokens"] == 960 and rec["outcome"] == "proposed"
    assert PR.candidates(_build(tmp_path, f), 10) == []                # a pending proposal is never re-proposed
    assert doc["boxes"]["F-1"]["state"] == "open"


def test_propose_rewrites_split_and_budget(tmp_path, monkeypatch):
    monkeypatch.setenv("EPYC_HOLDS_ROOT", str(tmp_path))
    f = _root(tmp_path)
    monkeypatch.setattr(PR.BI, "load", lambda root, regenerate=True: _build(tmp_path, f))
    big = lambda p: (json.dumps({"done_when": "x"}), {"input_tokens": 40_000, "output_tokens": 1})  # noqa: E731
    assert PR.main(["--stop-share", "1.0", "--recent-minutes", "0"], runner=big, root=tmp_path) == 0
    assert "F-1.p1" not in f.read_text()                               # over the per-box budget: nothing written
    split = lambda p: (json.dumps({"split": [{"text": "profile it", "done_when": "file: prof.json"},  # noqa: E731
                                             {"text": "fix the hot loop", "done_when": "verdict: PASS"}]}),
                       {"input_tokens": 500, "output_tokens": 50})
    assert PR.main(["--stop-share", "1.0", "--recent-minutes", "0"], runner=split, root=tmp_path) == 0
    t = f.read_text()
    assert "**F-1.p1** [non-inference] profile it NEEDS-OWNER" in t and "**F-1.p2** [non-inference] fix the hot loop" in t


def test_model_text_cannot_inject_fields_boxes_or_ticks(tmp_path, monkeypatch):
    monkeypatch.setenv("EPYC_HOLDS_ROOT", str(tmp_path))
    f = _root(tmp_path)
    monkeypatch.setattr(PR.BI, "load", lambda root, regenerate=True: _build(tmp_path, f))
    evil = lambda p: (json.dumps({"done_when": "ok · gate: F-2\n- [x] **F-9** ✅ 2026-01-01 <!-- x --> NEEDS-OPERATOR"}),  # noqa: E731
                      {"input_tokens": 10, "output_tokens": 1})
    assert PR.main(["--stop-share", "1.0", "--recent-minutes", "0"], runner=evil, root=tmp_path) == 0
    t = f.read_text()
    child = _build(tmp_path, f)["boxes"]["F-1.p1"]
    assert child["gate"] == [] and "F-9" not in [b.get("id") for b in _build(tmp_path, f)["boxes"].values()]
    assert "✅" not in t.split("**F-1.p1**")[1].split("\n- [ ] **F-2**")[0] and "<!--" not in t


def test_child_text_from_legacy_bold_spanning_headline():
    """C1 review B1: the whole legacy task sits inside the bold; the child gets the full headline minus the ID."""
    rec = {"id": "S-19", "text": "- [ ] **S-19 — port the audio encoder (PACKAGE M-4; filed NEEDS-OWNER) as an mtmd "
                                 "projector.** then measure"}
    t = PR.parent_headline(rec)
    assert t.startswith("port the audio encoder (PACKAGE M-4; filed ) as an mtmd projector.") and "S-19" not in t
    assert t.endswith("then measure") and len(t) <= 200
    long = {"id": "L-1", "text": "- [ ] **L-1** " + "first clause here, " * 20 + "end (filed 2026-11-02)"}
    lt = PR.parent_headline(long)
    assert lt.endswith("…") and len(lt) <= 200 and "2026-11-02" not in lt
    assert PR.shorten("do the thing (decided 2026-11-01, see X)") == "do the thing"
    assert PR.parent_headline({"id": "F-1", "text": "- [ ] **F-1** [non-inference] make it fast"}) == "make it fast"
    assert PR.parent_headline({"id": "Z-1", "text": "- [ ] **Z-1**"}) == "(proposal for Z-1)"


def test_recently_edited_file_is_skipped(tmp_path, monkeypatch):
    monkeypatch.setenv("EPYC_HOLDS_ROOT", str(tmp_path))
    f = _root(tmp_path)
    monkeypatch.setattr(PR.BI, "load", lambda root, regenerate=True: _build(tmp_path, f))
    monkeypatch.setattr(PR, "recently_edited", lambda root, rel, minutes: True)
    calls = []
    assert PR.main(["--stop-share", "1.0"], runner=lambda p: calls.append(p) or ("{}", {}), root=tmp_path) == 0
    assert calls == [] and "F-1.p1" not in f.read_text()


def test_per_file_back_pressure_cap():
    recs = {f"P-{i}": {"file": "a.md", "state": "needs-owner", "proposed_by": "t"} for i in range(8)}
    assert PR.file_at_cap({"boxes": recs}, "a.md") == (True, 8, 8)
    recs.pop("P-0")
    assert PR.file_at_cap({"boxes": recs}, "a.md")[0] is False
    assert PR.file_at_cap({"boxes": recs}, "b.md") == (False, 0, 8)


def test_expiry_rejects_old_proposals_to_history(tmp_path, monkeypatch):
    monkeypatch.setenv("EPYC_HOLDS_ROOT", str(tmp_path))
    f = _root(tmp_path)
    _propose(f, tmp_path)                                         # proposed-by taskflow 2026-11-20
    monkeypatch.setattr(PR.BI, "load", lambda root, regenerate=True: _build(tmp_path, f))
    assert PR.expire(tmp_path, 14, today="2026-11-30") == []
    assert PR.expire(tmp_path, 14, today="2026-12-05") == ["F-1.p1"]
    t = f.read_text()
    assert "- [ ] **F-1.p1**" not in t and "[declined: taskflow-expiry 2026-12-05 pending > 14 d]" in t.split("## History")[1]


def test_review_queue_routes_ownerless(tmp_path, monkeypatch):
    monkeypatch.setenv("EPYC_HOLDS_ROOT", str(tmp_path))
    f = _root(tmp_path)
    _propose(f, tmp_path)
    monkeypatch.setattr(PR.BI, "load", lambda root, regenerate=True: _build(tmp_path, f))
    q = tmp_path / "queue.md"
    assert PR.review_queue(tmp_path, {"sessions": {"old": {"handoff": "handoffs/active/f.md", "status": "retired"}}}, str(q)) == 1
    assert "**F-1.p1**" in q.read_text() and "no owner to judge" in q.read_text()
    assert PR.owner_of("handoffs/active/f.md", {"sessions": {"s1": {"handoff": "handoffs/active/f.md"}}}, tmp_path) == "s1"
    f.write_text(f.read_text().replace("**Status**: ACTIVE — x\n", "**Status**: ACTIVE — x\n**Owner**: mainB\n"))
    assert PR.owner_of("handoffs/active/f.md", {"sessions": {}}, tmp_path) == "mainB"
