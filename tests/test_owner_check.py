"""Tests for scripts/system/owner_check.py — tmp_path only."""
import importlib.util, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_S = importlib.util.spec_from_file_location("owner_check", ROOT / "scripts/system/owner_check.py")
oc = importlib.util.module_from_spec(_S); _S.loader.exec_module(oc)


def test_flags_unwritable_dir_and_foreign_uid_but_not_readonly_file(tmp_path):
    (tmp_path / "ok").mkdir(); (tmp_path / "ok" / "ro.txt").write_text("x"); (tmp_path / "ok" / "ro.txt").chmod(0o444)
    locked = tmp_path / "locked"; locked.mkdir(); (locked / "f").write_text("12345"); locked.chmod(0o555)
    foreign = tmp_path / "foreign"; foreign.mkdir()
    out = []
    try:
        res = oc.scan([str(tmp_path)], depth=3, uid=os.getuid() + 1 if False else os.getuid(), emit=out.append)
    finally:
        locked.chmod(0o755)
    paths = {r["path"]: r for r in res["rows"]}
    assert str(locked) in paths and not paths[str(locked)]["foreign"] and paths[str(locked)]["bytes"] == 5
    assert str(tmp_path / "ok" / "ro.txt") not in paths and str(tmp_path / "ok") not in paths
    assert out[-1].startswith("OWNER-CHECK SUMMARY") and res["flagged"] == 1
    # a different uid makes everything foreign (reported, never chmod-ed)
    res2 = oc.scan([str(tmp_path)], depth=1, uid=os.getuid() + 12345, fix_modes=True, emit=lambda s: None)
    assert res2["foreign"] == 3 and res2["fixed"] == 0 and all(r["foreign"] for r in res2["rows"])


def test_fix_modes_repairs_owned_dir_only(tmp_path):
    locked = tmp_path / "locked"; locked.mkdir(); (locked / "f").write_text("x"); locked.chmod(0o555)
    try:
        res = oc.scan([str(tmp_path)], depth=2, fix_modes=True, emit=lambda s: None)
        assert res["fixed"] == 1 and os.access(locked, os.W_OK)
    finally:
        locked.chmod(0o755)
