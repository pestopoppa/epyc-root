"""KT-2: a contradiction is filed only when both sides re-find verbatim; nothing auto-resolves."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))

import contradiction_gate as cg  # noqa: E402


def _repo(tmp_path):
    (tmp_path / "wiki").mkdir()
    (tmp_path / "wiki" / "a.md").write_text("intro\nThe MoE decodes faster than the dense model.\n")
    (tmp_path / "wiki" / "b.md").write_text("x\ny\nz\nThe dense model decodes faster than the MoE.\n")
    return tmp_path


def _prop(**over):
    p = {"a": {"path": "wiki/a.md", "line": 2, "quote": "The MoE decodes faster than the dense model."},
         "b": {"path": "wiki/b.md", "line": 2, "quote": "The dense model decodes faster than the MoE."},
         "rationale": "opposite ordering", "proposer": "test"}
    p.update(over)
    return p


def test_files_verified_pair_pending_and_dedupes_either_order(tmp_path):
    repo, q = _repo(tmp_path), tmp_path / "q.jsonl"
    res = cg.gate([_prop()], repo=repo, queue=q, now="T")
    assert len(res["filed"]) == 1
    row = cg.load_queue(q)[0]
    assert row["status"] == "pending" and row["b"]["line"] == 4 and row["b"]["line_as_proposed"] == 2
    assert row["a"]["sha256"] == cg.quote_hash("The MoE decodes  faster than the dense model.")
    swapped = _prop(a=_prop()["b"], b=_prop()["a"])
    res2 = cg.gate([swapped], repo=repo, queue=q, now="T")
    assert res2["duplicate"] == [row["id"]] and len(cg.load_queue(q)) == 1


def test_rejects_unfound_quote_missing_file_and_same_text(tmp_path):
    repo, q = _repo(tmp_path), tmp_path / "q.jsonl"
    bad_quote = _prop(b={"path": "wiki/b.md", "line": 4, "quote": "A statement that is not there."})
    bad_path = _prop(a={"path": "wiki/nope.md", "line": 1, "quote": "whatever text here"})
    escape = _prop(a={"path": "../etc/passwd", "line": 1, "quote": "root:x:0:0:root"})
    same = _prop(b=_prop()["a"])
    res = cg.gate([bad_quote, bad_path, escape, same], repo=repo, queue=q)
    assert len(res["rejected"]) == 4 and not res["filed"] and not q.exists()


def test_never_writes_a_resolution():
    src = (ROOT / "scripts" / "vidya" / "contradiction_gate.py").read_text()
    assert '"status": "pending"' in src
    for word in ('"resolved"', '"accepted"', '"rejected_by_operator"'):
        assert word not in src
