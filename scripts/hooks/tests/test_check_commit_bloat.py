"""D9 commit-size guard (scripts/hooks/check_commit_bloat.py) against real throwaway git repos."""
from __future__ import annotations

import importlib.util
import os
import subprocess
from pathlib import Path

import pytest

P = Path(__file__).resolve().parents[1] / "check_commit_bloat.py"
spec = importlib.util.spec_from_file_location("check_commit_bloat_undertest", P)
cb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cb)


def _repo(tmp_path, branch):
    r = tmp_path / "r"
    r.mkdir()
    g = lambda *a: subprocess.run(["git", "-C", str(r), *a], check=True, capture_output=True)
    g("init", "-q", "-b", branch)
    g("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "init")
    return r, g


def _stage(r, g, files):
    for p, txt in files.items():
        f = r / p
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(txt)
        g("add", "--", p)


def _rc(r, monkeypatch, env=None):
    monkeypatch.chdir(r)
    monkeypatch.delenv("EPYC_CODEX_WRAPUP", raising=False)
    for k, v in (env or {}).items():
        monkeypatch.setenv(k, v)
    return cb.main([])


def lines(n):
    return "".join(f"l{i}\n" for i in range(n))


def test_duplicate_blob_refused(tmp_path, monkeypatch, capsys):
    r, g = _repo(tmp_path, "lane/h-x")
    _stage(r, g, {"a/one.txt": "same\nx\ny\n", "b/two.txt": "same\nx\ny\n"})
    assert _rc(r, monkeypatch) == 1
    assert "SHA-256" in capsys.readouterr().err


def test_oversize_file_refused(tmp_path, monkeypatch):
    r, g = _repo(tmp_path, "h-x")
    _stage(r, g, {"big.txt": lines(2001)})
    assert _rc(r, monkeypatch) == 1


def test_evidence_total_cap_refused(tmp_path, monkeypatch):
    r, g = _repo(tmp_path, "main")
    _stage(r, g, {f"data/vidya/run/packet/f{i}.txt": f"{i}\n" + lines(1999) for i in range(11)})
    assert _rc(r, monkeypatch, {"EPYC_CODEX_WRAPUP": "1"}) == 1


def test_evidence_under_cap_allowed(tmp_path, monkeypatch):
    r, g = _repo(tmp_path, "lane/h-x")
    _stage(r, g, {f"data/vidya/run/packet/f{i}.txt": f"{i}\n" + lines(1999) for i in range(9)})
    assert _rc(r, monkeypatch) == 0


def test_exempt_generated_paths_allowed(tmp_path, monkeypatch):
    r, g = _repo(tmp_path, "lane/h-x")
    _stage(r, g, {"handoffs/active/.index-state.json": lines(5000), "wiki/source_manifest.json": lines(5000)})
    assert _rc(r, monkeypatch) == 0


def test_non_codex_branch_unaffected(tmp_path, monkeypatch):
    r, g = _repo(tmp_path, "main")
    _stage(r, g, {"a/one.txt": "same\n", "b/two.txt": "same\n", "big.txt": lines(3000)})
    assert _rc(r, monkeypatch) == 0


def test_tiny_duplicate_markers_allowed(tmp_path, monkeypatch):
    r, g = _repo(tmp_path, "lane/h-x")
    _stage(r, g, {"a/rc": "0\n", "b/rc": "0\n", "a/err": "", "b/err": ""})
    assert _rc(r, monkeypatch) == 0
