import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "system"))
import comgr_cache_reaper as cr  # noqa: E402

OLD = time.time() - 10 * 86400


def _mk(d, name, mtime):
    p = d / name
    p.write_bytes(b"x" * 100)
    os.utime(p, (mtime, mtime))
    return p


def test_old_unused_removed_young_and_foreign_names_kept(tmp_path):
    old = _mk(tmp_path, ".9adb5fffeff6eff7-00000000.so", OLD)
    young = _mk(tmp_path, ".9adb68fdf6e9efdf-00000000.so", time.time() - 3600)
    other = _mk(tmp_path, "keep-00000000.so", OLD)
    other2 = _mk(tmp_path, ".notes.txt", OLD)
    dry = cr.reap(str(tmp_path), 3, apply=False)
    assert dry["removed"] == 1 and old.exists()
    r = cr.reap(str(tmp_path), 3, apply=True)
    assert r["removed"] == 1 and r["removed_bytes"] == 100
    assert not old.exists() and young.exists() and other.exists() and other2.exists()


def test_open_file_is_kept(tmp_path):
    p = _mk(tmp_path, ".aaaa-00000000.so", OLD)
    with open(p, "rb"):
        r = cr.reap(str(tmp_path), 3, apply=True)
    assert r["in_use"] == 1 and r["removed"] == 0 and p.exists()


def test_symlink_is_kept(tmp_path):
    t = _mk(tmp_path, "target", OLD)
    l = tmp_path / ".bbbb-00000000.so"
    l.symlink_to(t)
    r = cr.reap(str(tmp_path), 3, apply=True)
    assert r["removed"] == 0 and l.is_symlink()
