import gzip
import importlib.util
import io
import shutil
import sqlite3
import sys
import tarfile
from pathlib import Path

_p = Path(__file__).resolve().parents[2] / "scripts" / "backup" / "backup_retention.py"
_s = importlib.util.spec_from_file_location("backup_retention", _p)
br = importlib.util.module_from_spec(_s)
sys.modules["backup_retention"] = br
_s.loader.exec_module(br)

GZ = "gzip -c {src} > {out}"
GZV = "gzip -t {out}"


def mk_tar(p: Path, payload=b"x" * 5000):
    with tarfile.open(p, "w:gz") as tf:
        ti = tarfile.TarInfo("a.txt"); ti.size = len(payload)
        tf.addfile(ti, io.BytesIO(payload))


def test_ai_sessions_keeps_only_newest_verified(tmp_path):
    for d in ("20261107", "20261108", "20261109"):
        mk_tar(tmp_path / f"ai-sessions-{d}-040001.tar.gz")
    rc, _ = br.prune_ai_sessions(tmp_path, 1, allow_unmirrored=True)
    assert rc == 0
    assert [p.name for p in tmp_path.glob("ai-sessions-*")] == ["ai-sessions-20261109-040001.tar.gz"]


def test_ai_sessions_requires_mirror_and_expect(tmp_path):
    mk_tar(tmp_path / "ai-sessions-20261107-040001.tar.gz")
    newest = tmp_path / "ai-sessions-20261108-040001.tar.gz"
    mk_tar(newest)
    rc, msg = br.prune_ai_sessions(tmp_path, 1, expect=newest)
    assert rc == br.EXIT_USAGE and "require-mirror" in msg
    assert len(list(tmp_path.glob("ai-sessions-*"))) == 2


def test_ai_sessions_expect_mismatch(tmp_path):
    older = tmp_path / "ai-sessions-20261107-040001.tar.gz"
    newer = tmp_path / "ai-sessions-20261108-040001.tar.gz"
    mk_tar(older); mk_tar(newer)
    rc, msg = br.prune_ai_sessions(tmp_path, 1, expect=older, allow_unmirrored=True)
    assert rc == br.EXIT_UNVERIFIED and "not expected" in msg
    assert older.exists() and newer.exists()


def test_ai_sessions_mirror_success(tmp_path):
    victim = tmp_path / "ai-sessions-20261107-040001.tar.gz"
    newest = tmp_path / "ai-sessions-20261108-040001.tar.gz"
    mk_tar(victim); mk_tar(newest)
    mirror = tmp_path / "mirror"; mirror.mkdir()
    shutil.copy2(victim, mirror / victim.name)
    rc, _ = br.prune_ai_sessions(tmp_path, 1, expect=newest, require_mirror=mirror,
                                 allow_same_device=True)
    assert rc == 0
    assert [p.name for p in tmp_path.glob("ai-sessions-*")] == [newest.name]
    assert (mirror / victim.name).exists()


def test_ai_sessions_mirror_hash_mismatch(tmp_path):
    victim = tmp_path / "ai-sessions-20261107-040001.tar.gz"
    newest = tmp_path / "ai-sessions-20261108-040001.tar.gz"
    mk_tar(victim); mk_tar(newest)
    mirror = tmp_path / "mirror"; mirror.mkdir()
    shutil.copy2(victim, mirror / victim.name)
    data = bytearray((mirror / victim.name).read_bytes())
    data[-1] ^= 0xFF
    (mirror / victim.name).write_bytes(data)
    rc, msg = br.prune_ai_sessions(tmp_path, 1, expect=newest, require_mirror=mirror,
                                   allow_same_device=True)
    assert rc == br.EXIT_MIRROR and "sha256 mismatch" in msg
    assert victim.exists() and newest.exists()


def test_ai_sessions_mirror_not_mounted(tmp_path):
    victim = tmp_path / "ai-sessions-20261107-040001.tar.gz"
    newest = tmp_path / "ai-sessions-20261108-040001.tar.gz"
    mk_tar(victim); mk_tar(newest)
    mirror = tmp_path / "mirror"; mirror.mkdir()
    shutil.copy2(victim, mirror / victim.name)
    rc, msg = br.prune_ai_sessions(tmp_path, 1, expect=newest, require_mirror=mirror,
                                   require_mount=str(tmp_path / "not-a-mount"),
                                   allow_same_device=True)
    assert rc == br.EXIT_USAGE and "not a mountpoint" in msg
    assert victim.exists() and newest.exists()


def test_gzip_trailer_truncation_fails(tmp_path):
    p = tmp_path / "ai-sessions-20261109-040001.tar.gz"
    mk_tar(p)
    data = p.read_bytes()
    assert br.verify_tarball(p)
    p.write_bytes(data[:-8])
    assert not br.verify_tarball(p)


def test_truncated_newest_keeps_previous(tmp_path):
    mk_tar(tmp_path / "ai-sessions-20261108-040001.tar.gz")
    good = tmp_path / "ai-sessions-20261109-040001.tar.gz"
    mk_tar(good, bytes(range(256)) * 400)
    good.write_bytes(good.read_bytes()[:-40])
    rc, _ = br.prune_ai_sessions(tmp_path, 1)
    assert rc == br.EXIT_UNVERIFIED
    assert len(list(tmp_path.glob("ai-sessions-*"))) == 2


def test_corrupt_and_empty_newest_keep_previous(tmp_path):
    mk_tar(tmp_path / "ai-sessions-20261108-040001.tar.gz")
    (tmp_path / "ai-sessions-20261109-040001.tar.gz").write_bytes(b"")
    assert br.prune_ai_sessions(tmp_path, 1)[0] == br.EXIT_UNVERIFIED
    (tmp_path / "ai-sessions-20261109-040001.tar.gz").write_bytes(b"not gzip at all" * 50)
    assert br.prune_ai_sessions(tmp_path, 1)[0] == br.EXIT_UNVERIFIED
    assert len(list(tmp_path.glob("ai-sessions-*"))) == 2


def test_never_zero_and_keep_zero_refused(tmp_path):
    mk_tar(tmp_path / "ai-sessions-20261109-040001.tar.gz")
    assert br.prune_ai_sessions(tmp_path, 0)[0] == 2
    assert br.prune_ai_sessions(tmp_path, 1)[0] == 0
    assert len(list(tmp_path.glob("ai-sessions-*"))) == 1
    empty = tmp_path / "empty"; empty.mkdir()
    assert br.prune_ai_sessions(empty, 1)[0] == br.EXIT_UNVERIFIED


def snap(d, src, stamp, **kw):
    kw.setdefault("integrity_check", "off")
    kw.setdefault("allow_unmirrored", True)
    return br.opencode_snapshot(d, "opencode-epyc", src, compress_cmd=GZ, verify_cmd=GZV, stamp=stamp, **kw)


def test_opencode_dedupe_and_bounded_count(tmp_path):
    src = tmp_path / "epyc.db"; d = tmp_path / "out"; d.mkdir()
    src.write_bytes(b"v1")
    assert snap(d, src, "20261101-000000")[0] == 0
    assert snap(d, src, "20261102-000000")[0] == br.EXIT_SKIPPED      # identical: no new file
    assert len(list(d.glob("opencode-epyc-2*"))) == 1
    for i, stamp in enumerate(["20261103-000000", "20261104-000000", "20261105-000000", "20261106-000000"]):
        src.write_bytes(b"v%d" % (i + 2))
        assert snap(d, src, stamp)[0] == 0
    names = sorted(p.name for p in d.glob("opencode-epyc-2*"))
    assert names == [f"opencode-epyc-2026110{n}-000000.db.zst" for n in (4, 5, 6)]


def test_opencode_skip_still_prunes_with_mirror(tmp_path):
    src = tmp_path / "epyc.db"; d = tmp_path / "out"; d.mkdir()
    mirror = tmp_path / "mirror"; mirror.mkdir()
    src.write_bytes(b"v1")
    assert snap(d, src, "20261101-000000")[0] == 0
    for i, stamp in enumerate(["20261102-000000", "20261103-000000", "20261104-000000", "20261105-000000"]):
        src.write_bytes(b"v%d" % (i + 2))
        assert snap(d, src, stamp)[0] == 0
    for p in d.glob("opencode-epyc-*.db.zst"):
        shutil.copy2(p, mirror / p.name)
    rc, msg = br.opencode_snapshot(d, "opencode-epyc", src, keep=3, compress_cmd=GZ,
                                   verify_cmd=GZV, integrity_check="off",
                                   require_mirror=mirror, allow_same_device=True)
    assert rc == br.EXIT_SKIPPED and "skipped" in msg
    assert sorted(p.name for p in d.glob("opencode-epyc-*.db.zst")) == [
        "opencode-epyc-20261103-000000.db.zst",
        "opencode-epyc-20261104-000000.db.zst",
        "opencode-epyc-20261105-000000.db.zst",
    ]


def test_opencode_dry_run_projects_victim_and_deletes_nothing(tmp_path, capsys):
    src = tmp_path / "epyc.db"; d = tmp_path / "out"; d.mkdir()
    mirror = tmp_path / "mirror"; mirror.mkdir()
    src.write_bytes(b"v1")
    for i, stamp in enumerate(["20261101-000000", "20261102-000000", "20261103-000000"]):
        if i:
            src.write_bytes(b"v%d" % (i + 1))
        assert snap(d, src, stamp)[0] == 0
    for p in d.glob("opencode-epyc-*.db.zst"):
        shutil.copy2(p, mirror / p.name)
    src.write_bytes(b"v4")                      # unchanged is now false; a new snapshot is projected
    rc, msg = br.opencode_snapshot(d, "opencode-epyc", src, keep=3, compress_cmd=GZ,
                                   verify_cmd=GZV, integrity_check="off", dry_run=True,
                                   require_mirror=mirror, allow_same_device=True)
    assert rc == 0 and "would write" in msg
    assert (d / "opencode-epyc-20261101-000000.db.zst").exists()
    assert "WOULD_DELETE opencode-epyc-20261101-000000.db.zst" in capsys.readouterr().out


def test_opencode_wal_sibling_refused(tmp_path):
    src = tmp_path / "epyc.db"; d = tmp_path / "out"; d.mkdir()
    src.write_bytes(b"v1")
    Path(str(src) + "-wal").write_bytes(b"non-empty wal")
    rc, msg = br.opencode_snapshot(d, "opencode-epyc", src, integrity_check="off")
    assert rc == br.EXIT_USAGE and "-wal" in msg


def test_opencode_quick_check_corrupt_source(tmp_path):
    src = tmp_path / "epyc.db"; d = tmp_path / "out"; d.mkdir()
    src.write_bytes(b"this is not a sqlite database" * 50)
    rc, msg = br.opencode_snapshot(d, "opencode-epyc", src, integrity_check="quick_check")
    assert rc == br.EXIT_UNVERIFIED and "quick_check failed" in msg


def test_opencode_quick_check_valid_source(tmp_path):
    src = tmp_path / "epyc.db"; d = tmp_path / "out"; d.mkdir()
    c = sqlite3.connect(src)
    c.execute("create table t(a text)")
    c.execute("insert into t values ('x')")
    c.commit(); c.close()
    assert snap(d, src, "20261101-000000", integrity_check="quick_check")[0] == 0


def test_strict_regex_ignores_pre_v2_file(tmp_path):
    src = tmp_path / "epyc.db"; d = tmp_path / "out"; d.mkdir()
    src.write_bytes(b"v1")
    pre = d / "opencode-epyc-pre-v2-20261106T0920Z.db.zst"
    pre.write_bytes(b"do not touch")
    assert snap(d, src, "20261101-000000")[0] == 0
    assert pre.exists()
    assert sorted(p.name for p in d.glob("opencode-epyc-*.db.zst")) == sorted(
        [pre.name, "opencode-epyc-20261101-000000.db.zst"])


def test_opencode_failed_write_keeps_previous_and_hash(tmp_path):
    src = tmp_path / "epyc.db"; d = tmp_path / "out"; d.mkdir()
    src.write_bytes(b"v1"); snap(d, src, "20261101-000000")
    src.write_bytes(b"v2")
    rc, _ = br.opencode_snapshot(d, "opencode-epyc", src, compress_cmd="false", verify_cmd=GZV,
                                 stamp="20261102-000000", integrity_check="off")
    assert rc == br.EXIT_UNVERIFIED
    rc, _ = br.opencode_snapshot(d, "opencode-epyc", src, compress_cmd="true", verify_cmd=GZV,
                                 stamp="20261102-000000", integrity_check="off")
    assert rc == br.EXIT_UNVERIFIED                                   # no output produced
    rc, _ = br.opencode_snapshot(d, "opencode-epyc", src, compress_cmd="echo junk > {out}", verify_cmd=GZV,
                                 stamp="20261102-000000", integrity_check="off")
    assert rc == br.EXIT_UNVERIFIED                                   # corrupt output fails verify
    assert [p.name for p in d.glob("opencode-epyc-2*")] == ["opencode-epyc-20261101-000000.db.zst"]
    assert not list(d.glob(".*tmp"))
    assert snap(d, src, "20261103-000000")[0] == 0                    # hash not advanced by failures: v2 now written
