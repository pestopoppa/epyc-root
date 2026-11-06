"""job_fence: GPU-row fence rules (fails on the old v40 template), real Landlock behaviour, admission, HIP temp scan."""
import ctypes
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MOD = HERE.parent / "job_fence.py"
sys.path.insert(0, str(HERE.parent))
import job_fence as jf  # noqa: E402


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class RecLib:
    """Fake libc: records Landlock add_rule (path, access); never restricts the test process."""
    def __init__(self):
        self.rules = []

    def syscall(self, nr, a=0, b=0, c=0, *rest):
        if nr == 444:
            return 3 if c == 1 else os.open("/dev/null", os.O_RDONLY)
        if nr == 445:
            rule = c._obj
            self.rules.append((os.readlink(f"/proc/self/fd/{rule.fd}"), rule.access))
            return 0
        return 0

    def prctl(self, *a):
        return 0

    def allowed(self, path, bit=1 << 1):
        return any((path == p or path.startswith(p.rstrip("/") + "/")) and acc & bit for p, acc in self.rules)


def rules_of(apply_fn, monkeypatch, tmp_path, **kw):
    lib = RecLib()
    monkeypatch.setattr(ctypes, "CDLL", lambda *a, **k: lib)
    apply_fn([str(tmp_path)], **kw)
    return lib


def _new(paths, **kw):
    jf.apply(paths, gpu=True, **kw)


def _old(paths, **kw):
    load(HERE / "fixtures" / "write_fence_v40_template.py", "old_fence").apply(paths)


@pytest.mark.parametrize("impl", [
    _new,
    pytest.param(_old, marks=pytest.mark.xfail(strict=True, reason="v40 template denies /dev/kfd,/dev/dri (rc78)")),
], ids=["shared", "old-v40-template"])
def test_gpu_row_fence_allows_kfd_and_dri(impl, monkeypatch, tmp_path):
    lib = rules_of(impl, monkeypatch, tmp_path)
    assert lib.allowed("/dev/kfd") and lib.allowed("/dev/dri/renderD128")


def test_cpu_row_fence_does_not_open_gpu(monkeypatch, tmp_path):
    lib = RecLib()
    monkeypatch.setattr(ctypes, "CDLL", lambda *a, **k: lib)
    jf.apply([str(tmp_path)], gpu=False)
    assert not lib.allowed("/dev/kfd") and lib.allowed(str(tmp_path / "x"))


def test_gpu_tmpdir_gets_mkdir_rights(monkeypatch, tmp_path):
    tmp = Path(jf.hip_tmpdir(tmp_path))
    monkeypatch.setattr(jf, "TMP_ROOT", str(tmp_path))
    lib = RecLib()
    monkeypatch.setattr(ctypes, "CDLL", lambda *a, **k: lib)
    jf.apply([str(tmp_path)], gpu=True, tmpdir=str(tmp))
    assert lib.allowed(str(tmp / "comgr-1"), jf.MAKE_DIR) and lib.allowed(str(tmp / "comgr-1"), jf.REMOVE_DIR)


def _landlock():
    try:
        return ctypes.CDLL(None, use_errno=True).syscall(444, 0, 0, 1) >= 3
    except OSError:
        return False


PROBE = ("import os,sys\n"
         "try:\n os.close(os.open('/dev/kfd',os.O_RDWR)); print('kfd-ok')\n"
         "except OSError as e: print('kfd-denied',e.errno)\n"
         "try:\n open(sys.argv[1]+'/w','w').write('x'); print('out-ok')\n"
         "except OSError: print('out-denied')\n"
         "try:\n open(sys.argv[2]+'/w','w').write('x'); print('outside-ok')\n"
         "except OSError: print('outside-denied')\n")


@pytest.mark.skipif(not _landlock(), reason="Landlock ABI < 3")
def test_real_landlock_gpu_and_cpu(tmp_path):
    out, other = tmp_path / "out", tmp_path / "other"
    out.mkdir(); other.mkdir()
    probe = tmp_path / "probe.py"
    probe.write_text(PROBE)
    base = [sys.executable, str(MOD), "fence"]
    tail = [str(out), "--", sys.executable, "-I", str(probe), str(out), str(other)]
    cpu = subprocess.run(base + tail, capture_output=True, text=True, check=True).stdout
    assert "out-ok" in cpu and "outside-denied" in cpu
    if os.access("/dev/kfd", os.R_OK | os.W_OK):
        assert "kfd-denied" in cpu
        gpu = subprocess.run(base + ["--gpu"] + tail, capture_output=True, text=True, check=True).stdout
        assert "kfd-ok" in gpu and "outside-denied" in gpu and (out / ".hip-tmp").is_dir()


def test_admission_is_subset_not_two_cpus(tmp_path):
    granted = {20, 21, 22, 23, 116, 117, 118, 119}
    r = jf.check({20, 21, 116}, granted, flags=tmp_path, disk_path=tmp_path, floor=0, own={20, 21, 116})
    assert r["cpus"] == [20, 21, 116]
    with pytest.raises(RuntimeError, match="outside grant"):
        jf.check({20, 21}, granted, flags=tmp_path, disk_path=tmp_path, floor=0, own=set(range(192)))
    (tmp_path / "HOLD_X").write_text("")
    with pytest.raises(RuntimeError, match="HOLD"):
        jf.check({20}, granted, flags=tmp_path, disk_path=tmp_path, floor=0, own={20})


def test_rocm_full_affinity_thread_is_repinned(tmp_path):
    task = tmp_path / "7" / "task"
    for t in ("7", "8"):
        (task / t).mkdir(parents=True)
    aff = {7: {20, 21}, 8: set(range(192))}   # tid 8 = ROCr runtime thread, born on all cpus
    left = jf.repin_threads(7, {20, 21}, getaff=lambda t: aff[t], setaff=lambda t, c: aff.__setitem__(t, set(c)),
                            proc=str(tmp_path))
    assert left == [] and aff[8] == {20, 21}
    stuck = jf.repin_threads(7, {20, 21}, getaff=lambda t: set(range(192)), setaff=lambda t, c: None,
                             proc=str(tmp_path))
    assert sorted(stuck) == [7, 8]


def test_tree_usage_tolerates_vanishing_hip_temp(tmp_path, monkeypatch):
    (tmp_path / "comgr-abc").mkdir()
    (tmp_path / "comgr-abc" / "t.o").write_text("x")
    (tmp_path / "keep.txt").write_text("y")
    real = Path.lstat

    def flaky(self):
        if self.name == "t.o":
            raise FileNotFoundError(str(self))
        return real(self)
    monkeypatch.setattr(Path, "lstat", flaky)
    total, n = jf.tree_usage(tmp_path)
    assert total > 0
    (tmp_path / "gone.txt").write_text("z")
    monkeypatch.setattr(Path, "lstat", lambda self: (_ for _ in ()).throw(FileNotFoundError(str(self)))
                        if self.name == "gone.txt" else real(self))
    with pytest.raises(FileNotFoundError):
        jf.tree_usage(tmp_path)
