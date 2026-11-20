"""C0.2 (handoff standard Stage C): box_index.load() builds once under flock, returns the stale copy on failure."""
import json
import os
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import box_index  # noqa: E402

FAKE_BUILDER = """
import json, os, sys, time
from pathlib import Path
root = Path.cwd()
with open(root / "builds.log", "a") as f:
    f.write("b\\n")
time.sleep(0.6)
if (root / "FAIL").exists():
    sys.exit(3)
(root / "handoffs/active/.box-index.json").write_text(json.dumps({"boxes": {"A-1": {}}, "counts": {}}))
"""


def _root(tmp_path: Path) -> Path:
    (tmp_path / "scripts/handoffs").mkdir(parents=True)
    (tmp_path / "handoffs/active").mkdir(parents=True)
    (tmp_path / "scripts/handoffs/index_state.py").write_text(FAKE_BUILDER)
    (tmp_path / "handoffs/active/x.md").write_text("- [ ] **A-1** t\n")
    return tmp_path


def test_concurrent_load_builds_once(tmp_path):
    root = _root(tmp_path)
    out = []
    ts = [threading.Thread(target=lambda: out.append(box_index.load(root))) for _ in range(3)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert (root / "builds.log").read_text().count("b") == 1
    assert all(d.get("boxes") == {"A-1": {}} and not d.get("stale") for d in out)


def test_failed_rebuild_returns_stale_copy_not_empty(tmp_path):
    root = _root(tmp_path)
    box_index.load(root)
    time.sleep(0.05)
    (root / "handoffs/active/x.md").write_text("- [ ] **A-1** t2\n")   # source newer -> rebuild needed
    os.utime(root / "handoffs/active/x.md", (time.time() + 5, time.time() + 5))
    (root / "FAIL").write_text("")
    doc = box_index.load(root)
    assert doc["stale"] is True and "rc=3" in doc["stale_reason"]
    assert doc["boxes"] == {"A-1": {}}
    assert "stale" in box_index.stale_note(doc, "t")


def test_never_built_and_failing_is_flagged(tmp_path):
    root = _root(tmp_path)
    (root / "FAIL").write_text("")
    doc = box_index.load(root)
    assert doc.get("stale") and doc["boxes"] == {}
    assert "unavailable" in box_index.stale_note(doc, "t")


def test_regenerate_false_flags_old_copy(tmp_path):
    root = _root(tmp_path)
    (root / "handoffs/active/.box-index.json").write_text(json.dumps({"boxes": {"A-1": {}}}))
    os.utime(root / "handoffs/active/x.md", (time.time() + 5, time.time() + 5))
    doc = box_index.load(root, regenerate=False)
    assert doc["stale"] is True and not (root / "builds.log").exists()
