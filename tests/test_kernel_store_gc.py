import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "system"))
import kernel_store_gc as gc  # noqa: E402
import worktree_gate as wg  # noqa: E402

OLD = time.time() - 30 * 86400


def _age(root):
    for dp, dns, fns in os.walk(root):
        for n in dns + fns:
            os.utime(os.path.join(dp, n), (OLD, OLD), follow_symlinks=False)
    os.utime(root, (OLD, OLD))


@pytest.fixture
def env(tmp_path, monkeypatch):
    store = tmp_path / "kernels"
    b = store / "builds"
    names = ["a", "b", "c-20261101-aaaaaaaaa", "d-20261101-123456789", "e", "f-20261101-fffffffff"]
    for n in names:
        (b / n / "bin").mkdir(parents=True)
        (b / n / "bin" / "x").write_text("data")
    (b / "e" / "KEEP").write_text("")
    for n in names:
        _age(b / n)
    (store / "production").mkdir()
    (store / "candidates").mkdir()
    os.symlink(b / "a" / "bin", store / "production" / "cpu")
    os.symlink(b / "b", store / "candidates" / "x")
    refs = tmp_path / "refs"
    refs.mkdir()
    (refs / "h.md").write_text("see `c-20261101-aaaaaaaaa` for details\n")
    champ = tmp_path / "champ.md"
    champ.write_text("champion is commit 123456789\n")
    trash = tmp_path / "trash"
    monkeypatch.setenv("TRASH_ROOT", str(trash))
    monkeypatch.setenv("SAFETY_AUDIT_LOG", str(tmp_path / "audit.log"))
    base = ["--store", str(store), "--refs-glob", str(refs / "*.md"),
            "--commit-refs", str(champ), "--log", str(tmp_path / "gc.log")]
    return dict(store=store, b=b, refs=refs, trash=trash, base=base, tmp=tmp_path)


def run(env, extra=(), probe=None, proc=None):
    return gc.main(list(env["base"]) + list(extra),
                   probe_fn=lambda: probe or wg.Probe(),
                   proc_fn=proc or (lambda: (set(), True)))


def verdicts(env):
    out = {}
    for ln in (env["tmp"] / "gc.log").read_text().splitlines():
        if " build=" in ln:
            parts = dict(p.split("=", 1) for p in ln.split()[2:4])
            out[parts["build"]] = ln.split("verdict=")[1].split()[0]
    return out


def test_dry_run(env):
    assert run(env) == 0
    v = verdicts(env)
    assert v == {"a": "KEEP-PRODUCTION", "b": "KEEP-PRODUCTION",
                 "c-20261101-aaaaaaaaa": "KEEP-REFERENCED", "d-20261101-123456789": "KEEP-REFERENCED",
                 "e": "KEEP-MARKED", "f-20261101-fffffffff": "REAP"}
    assert (env["b"] / "f-20261101-fffffffff").exists()
    assert not env["trash"].exists()
    assert "SUMMARY builds=6 keep=5 reap=1" in (env["tmp"] / "gc.log").read_text()


def test_apply(env):
    assert run(env, ["--apply"]) == 0
    assert not (env["b"] / "f-20261101-fffffffff").exists()
    assert any("f-20261101-fffffffff" in p for p in os.listdir(env["trash"]))
    for n in ["a", "b", "c-20261101-aaaaaaaaa", "d-20261101-123456789", "e"]:
        assert (env["b"] / n).exists()


def test_recent(env):
    os.utime(env["b"] / "f-20261101-fffffffff" / "bin" / "x")
    run(env)
    assert verdicts(env)["f-20261101-fffffffff"] == "KEEP-RECENT"


def test_busy_probe(env):
    p = wg.Probe()
    p.cwds[os.path.realpath(env["b"] / "f-20261101-fffffffff" / "bin")] = "4242"
    run(env, ["--apply"], probe=p)
    assert verdicts(env)["f-20261101-fffffffff"] == "KEEP-BUSY"
    assert (env["b"] / "f-20261101-fffffffff").exists()


def test_busy_open_fd(env):
    path = str(env["b"] / "f-20261101-fffffffff" / "bin" / "x")
    run(env, proc=lambda: ({path}, True))
    assert verdicts(env)["f-20261101-fffffffff"] == "KEEP-BUSY"


def test_unreadable_ref_fails_closed(env, monkeypatch):
    real_open = open

    def bad_open(f, *a, **k):
        if str(f).endswith("h.md"):
            raise PermissionError(f)
        return real_open(f, *a, **k)
    monkeypatch.setattr("builtins.open", bad_open)
    run(env, ["--apply"])
    assert verdicts(env)["f-20261101-fffffffff"] == "KEEP-UNVERIFIABLE"
    assert (env["b"] / "f-20261101-fffffffff").exists()


def test_max_zero(env):
    run(env, ["--apply", "--max", "0"])
    assert (env["b"] / "f-20261101-fffffffff").exists()
    assert "reap=0" in (env["tmp"] / "gc.log").read_text()


def test_lineage_suffix(env):
    d = env["b"] / "gpu-20261106-62cb6a6af-c7r"
    (d / "bin").mkdir(parents=True)
    _age(d)
    run(env)
    assert verdicts(env)["gpu-20261106-62cb6a6af-c7r"] == "KEEP-LINEAGE"
