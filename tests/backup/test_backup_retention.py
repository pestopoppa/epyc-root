import gzip
import importlib.util
import io
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
    rc, _ = br.prune_ai_sessions(tmp_path, 1)
    assert rc == 0
    assert [p.name for p in tmp_path.glob("ai-sessions-*")] == ["ai-sessions-20261109-040001.tar.gz"]


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
    assert br.prune_ai_sessions(tmp_path / "empty-none", 1)[0] == br.EXIT_UNVERIFIED


def snap(d, src, stamp, **kw):
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


def test_opencode_failed_write_keeps_previous_and_hash(tmp_path):
    src = tmp_path / "epyc.db"; d = tmp_path / "out"; d.mkdir()
    src.write_bytes(b"v1"); snap(d, src, "20261101-000000")
    src.write_bytes(b"v2")
    rc, _ = br.opencode_snapshot(d, "opencode-epyc", src, compress_cmd="false", verify_cmd=GZV, stamp="20261102-000000")
    assert rc == br.EXIT_UNVERIFIED
    rc, _ = br.opencode_snapshot(d, "opencode-epyc", src, compress_cmd="true", verify_cmd=GZV, stamp="20261102-000000")
    assert rc == br.EXIT_UNVERIFIED                                   # no output produced
    rc, _ = br.opencode_snapshot(d, "opencode-epyc", src, compress_cmd="echo junk > {out}", verify_cmd=GZV, stamp="20261102-000000")
    assert rc == br.EXIT_UNVERIFIED                                   # corrupt output fails verify
    assert [p.name for p in d.glob("opencode-epyc-2*")] == ["opencode-epyc-20261101-000000.db.zst"]
    assert not list(d.glob(".*tmp"))
    assert snap(d, src, "20261103-000000")[0] == 0                    # hash not advanced by failures: v2 now written
