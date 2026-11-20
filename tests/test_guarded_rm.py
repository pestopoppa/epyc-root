"""guarded_rm.sh / trash-sweep.sh — tmp_path only (TRASH_ROOT and SAFETY_AUDIT_LOG redirected)."""
import os, re, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RM = ROOT / "scripts/safety/guarded_rm.sh"
SWEEP = ROOT / "scripts/safety/trash-sweep.sh"


def run(script, *args, env):
    return subprocess.run(["bash", str(script), *args], capture_output=True, text=True, env=env)


def test_same_basename_same_second_never_overwrites(tmp_path):
    trash = tmp_path / "trash"
    env = dict(os.environ, TRASH_ROOT=str(trash), SAFETY_AUDIT_LOG=str(tmp_path / "audit.log"))
    srcs = []
    for i in range(3):
        d = tmp_path / f"d{i}"; d.mkdir()
        f = d / "a3b-C.bin"; f.write_text(f"payload-{i}"); srcs.append(f)
    cp = run(RM, *map(str, srcs), env=env)          # one invocation: same second guaranteed
    assert cp.returncode == 0, cp.stderr
    entries = sorted(trash.iterdir())
    assert len(entries) == 3, [e.name for e in entries]
    assert sorted(e.read_text() for e in entries) == ["payload-0", "payload-1", "payload-2"]
    for e in entries:                                 # trash-sweep still parses the time prefix
        assert re.match(r"^\d{8}-\d{6}-[0-9a-f]{8}-a3b-C\.bin(-\d+)?$", e.name), e.name
    # the same source path trashed again in the same second gets a counter, not an overwrite
    srcs[0].write_text("again")
    assert run(RM, str(srcs[0]), env=env).returncode == 0
    assert len(list(trash.iterdir())) == 4 and not any(s.exists() for s in srcs)


def test_trash_dir_not_moved_into_existing_entry(tmp_path):
    trash = tmp_path / "trash"; trash.mkdir()
    env = dict(os.environ, TRASH_ROOT=str(trash), SAFETY_AUDIT_LOG=str(tmp_path / "audit.log"))
    d = tmp_path / "x" / "build"; d.mkdir(parents=True); (d / "f").write_text("1")
    d2 = tmp_path / "y" / "build"; d2.mkdir(parents=True); (d2 / "g").write_text("2")
    assert run(RM, str(d), str(d2), env=env).returncode == 0
    names = [e.name for e in trash.iterdir()]
    assert len(names) == 2 and all(n.endswith("build") for n in names)
    assert all(not (trash / n / "build").exists() for n in names)   # never nested into another entry


def test_sweep_ages_by_prefix_and_removes_old(tmp_path):
    trash = tmp_path / "trash"; trash.mkdir()
    env = dict(os.environ, TRASH_ROOT=str(trash), SAFETY_AUDIT_LOG=str(tmp_path / "audit.log"))
    old = trash / "20200101-000000-deadbeef-old.bin"; old.write_text("o")
    new = trash / "20990101-000000-deadbeef-new.bin"; new.write_text("n")
    cp = run(SWEEP, "--older-than", "1", env=env)
    assert cp.returncode == 0 and not old.exists() and new.exists(), cp.stdout + cp.stderr


def test_protected_path_refused_even_with_bypass_and_for_ancestors(tmp_path):
    trash = tmp_path / "trash"
    prot = tmp_path / "keep" / "ck"; prot.mkdir(parents=True); (prot / "CY2.bin").write_text("x")
    other = tmp_path / "keep" / "other"; other.mkdir(); (other / "f").write_text("y")
    plist = tmp_path / "protected_paths.txt"; plist.write_text(f"# c\n{prot}\n")
    env = dict(os.environ, TRASH_ROOT=str(trash), SAFETY_AUDIT_LOG=str(tmp_path / "audit.log"), PROTECTED_PATHS_FILE=str(plist))
    for args in ([str(prot)], [str(prot / "CY2.bin")], [str(prot.parent)], ["--bypass-guard", str(prot)], ["--bypass-guard", str(prot.parent)]):
        cp = run(RM, *args, env=env)
        assert cp.returncode == 1 and "operator-protected" in cp.stderr, (args, cp.stderr)
        assert (prot / "CY2.bin").read_text() == "x"
    assert run(RM, str(other), env=env).returncode == 0          # an unrelated sibling is still trashable
    assert not other.exists() and (prot / "CY2.bin").exists()
