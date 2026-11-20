"""C4 gap 4 (rowflow side): every handoff_task consumer resolves through handoff_ref, so a box moved by a track split
(.moves.jsonl) routes to its NEW file - rowflow legacy migration + unfiled-ack filing, notify owner routing,
backlog_gen, churn filing."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "coordination"))
sys.path.insert(0, str(ROOT / "scripts" / "coordination" / "rowflow"))
sys.path.insert(0, str(ROOT / "scripts" / "coordination" / "churn"))
import handoff_ref as HR  # noqa: E402

MOVE = {"box_id": "T-1", "text_sha": "sha-t1", "from": "old.md", "to": "new.md", "at": "2026-11-20"}


def _repo(tmp_path, monkeypatch, moves=(MOVE,)):
    act = tmp_path / "handoffs" / "active"
    act.mkdir(parents=True)
    (act / ".moves.jsonl").write_text("".join(json.dumps(m) + "\n" for m in moves))
    monkeypatch.setenv("ROWFLOW_REPO", str(tmp_path))
    return tmp_path


def test_repoint_keeps_prefix_and_task(tmp_path, monkeypatch):
    _repo(tmp_path, monkeypatch)
    assert HR.repoint("handoffs/active/old.md:T-1") == "handoffs/active/new.md:T-1"
    assert HR.repoint("old.md:T-1") == "new.md:T-1"
    assert HR.repoint("old.md:T-2") == "old.md:T-2"                       # another box did not move
    assert HR.repoint("old.md:X-9", sha="sha-t1") == "new.md:X-9"         # text_sha wins over the id
    assert HR.repoint("FILLERS:abc") == "FILLERS:abc" and HR.repoint(None) is None


def test_repoint_never_raises_without_moves(tmp_path, monkeypatch):
    monkeypatch.setenv("ROWFLOW_REPO", str(tmp_path / "nowhere"))
    assert HR.repoint("old.md:T-1") == "old.md:T-1"


def test_rowflow_legacy_handoff_task_migrates_to_new_file(tmp_path, monkeypatch):
    _repo(tmp_path, monkeypatch)
    import rowflow as rf
    assert rf.legacy_handoff_task({"id": "r", "handoff_task": "old.md:T-1"}) == "handoffs/active/new.md:T-1"
    assert rf.legacy_handoff_task({"id": "r"}) == "FILLERS:r"


def test_rowflow_unfiled_ack_files_against_new_file():
    src = (ROOT / "scripts/coordination/rowflow/rowflow.py").read_text()
    i = src.index("has no handoff_task <handoff.md>:<BOX-ID> in its manifest")
    assert "handoff_ref.repoint(task)" in src[i:i + 600]                  # resolved before `hp, box = task.rsplit`


def test_notify_routes_alert_to_new_owner(tmp_path, monkeypatch):
    _repo(tmp_path, monkeypatch)
    import notify
    rec = {"handoff_task": "handoffs/active/old.md:T-1", "owner": "someone"}
    monkeypatch.setattr(notify, "read_inbox", lambda flags, unacked=False: [rec])
    assert notify.alerts_for("f", handoff="new.md") == [rec]
    assert notify.alerts_for("f", handoff="old.md") == []


def test_backlog_gen_buckets_moved_row_under_new_handoff(tmp_path, monkeypatch):
    _repo(tmp_path, monkeypatch)
    from scripts.coordination import backlog_gen as bg
    sys.path.insert(0, str(ROOT / "tests" / "coordination"))
    import test_backlog_gen as T
    import rowflow as rf
    monkeypatch.setattr(bg, "_rf", rf)
    F, pri = T._flags(tmp_path)
    T._row(F, "moved-row", rank=2, handoff_task="handoffs/active/old.md:T-1")
    data = T._build(F, pri)
    rec = next(r for w in data["workers"].values() for r in w["rows"] if r["id"] == "moved-row")
    assert rec["handoff"] == "handoffs/active/new.md"


def test_filing_records_current_handoff_task(tmp_path, monkeypatch):
    _repo(tmp_path, monkeypatch)
    import filing
    m = {"handoff_task": "handoffs/active/old.md:T-1"}
    assert filing.current_handoff_task(m) == "handoffs/active/new.md:T-1"
    assert filing.current_handoff_task(m, repo=str(tmp_path)) == "handoffs/active/new.md:T-1"
    assert filing.current_handoff_task({"handoff_task": None}) is None
    src = (ROOT / "scripts/coordination/churn/filing.py").read_text()
    assert src.count('"handoff_task": current_handoff_task(m') == 2       # file_terminal + file_receipt records
