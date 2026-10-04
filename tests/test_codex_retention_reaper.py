"""Offline tests for scripts/system/codex_retention_reaper.py (NIB2-84).

Everything runs against temp fixtures: a fake codex home, a fake vault and a temp state dir.
The real ~/.codex and the real vault are never read or written. The only processes spawned are
the reaper itself (as a subprocess, so the pytest process counts as a FOREIGN holder of any file
it opens) and a stand-in `codex` copied from /bin/sleep, reaped by its own pid.

    python3 -m pytest -q -p no:randomly tests/test_codex_retention_reaper.py
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "system" / "codex_retention_reaper.py"
DAY = 86400
OLD = time.time() - 30 * DAY


def _write(path: Path, data: bytes, mtime: float | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    if mtime is not None:
        os.utime(path, (mtime, mtime))
    return path


@pytest.fixture
def env(tmp_path):
    home, vault, state = tmp_path / "home", tmp_path / "vault", tmp_path / "state"
    (home / "sessions").mkdir(parents=True)
    vault.mkdir()
    return {"home": home, "vault": vault, "state": state, "tmp": tmp_path}


def run(env, *args, check_rc=None):
    cmd = [sys.executable, str(SCRIPT), *args, "--home", str(env["home"]),
           "--vault", str(env["vault"]), "--state-dir", str(env["state"])]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if check_rc is not None:
        assert res.returncode == check_rc, (res.returncode, res.stdout, res.stderr)
    return res


def report(env, *extra):
    res = run(env, "report", "--json", *extra, check_rc=0)
    return json.loads(res.stdout)


def rollout(env, rel: str, data: bytes, mtime=OLD, vault_data: bytes | None = None,
            vault: bool = True) -> Path:
    p = _write(env["home"] / "sessions" / rel, data, mtime)
    if vault:
        _write(env["vault"] / rel, data if vault_data is None else vault_data)
    return p


R_ARCH = "2026/08/01/rollout-2026-08-01T00-00-00-aaaa.jsonl"
R_NOVAULT = "2026/08/02/rollout-2026-08-02T00-00-00-bbbb.jsonl"
R_HASHDIFF = "2026/08/03/rollout-2026-08-03T00-00-00-cccc.jsonl"
R_OPEN = "2026/08/04/rollout-2026-08-04T00-00-00-dddd.jsonl"
R_YOUNG = "2026/10/03/rollout-2026-10-03T00-00-00-eeee.jsonl"
R_SIZEDIFF = "2026/08/05/rollout-2026-08-05T00-00-00-ffff.jsonl"


def _rels(rep, cls):
    return set(rep["rollouts"]["classes"][cls]["sample"])


def test_classification_archived_unarchived_open(env):
    rollout(env, R_ARCH, b'{"a":1}\n' * 100)
    rollout(env, R_NOVAULT, b'{"b":1}\n' * 100, vault=False)
    rollout(env, R_HASHDIFF, b'{"c":1}\n' * 100, vault_data=b'{"X":1}\n' * 100)  # same size
    rollout(env, R_SIZEDIFF, b'{"f":1}\n' * 100, vault_data=b"short\n")
    p_open = rollout(env, R_OPEN, b'{"d":1}\n' * 100)
    rollout(env, R_YOUNG, b'{"e":1}\n' * 100, mtime=time.time() - 3600)
    with open(p_open, "rb"):  # a foreign holder: this pytest process
        rep = report(env)
    assert _rels(rep, "archived") == {R_ARCH}
    assert _rels(rep, "unarchived") == {R_NOVAULT, R_HASHDIFF, R_SIZEDIFF}
    assert _rels(rep, "open") == {R_OPEN}
    assert rep["rollouts"]["young"]["count"] == 1
    reasons = rep["rollouts"]["classes"]["unarchived"]["reasons"]
    assert reasons.get("size match but sha256 differs") == 1
    assert reasons.get("no vault copy") == 1
    assert rep["reclaimable_bytes"]["rollouts_archived"] == 800
    assert rep["confirm_token"] and Path(rep["manifest"]).exists()
    assert (env["state"] / "last_report.json").exists()
    assert set(rep) >= {"schema", "observer", "rollouts", "packages", "sqlite",
                        "reclaimable_bytes", "confirm_token"}


def test_size_match_hash_differ_is_unarchived_not_archived(env):
    rollout(env, R_HASHDIFF, b"A" * 4096, vault_data=b"B" * 4096)
    rep = report(env)
    assert _rels(rep, "unarchived") == {R_HASHDIFF}
    assert rep["confirm_token"] is None


def test_hash_budget_zero_leaves_candidates_unverified(env):
    rollout(env, R_ARCH, b"A" * 4096)
    rep = report(env, "--max-hash-gib", "0")
    assert _rels(rep, "unverified") == {R_ARCH}
    assert rep["hashing"]["hashed_bytes"] == 0
    assert rep["confirm_token"] is None
    # a later run with budget verifies, and a third run reuses the cache without hashing
    assert _rels(report(env), "archived") == {R_ARCH}
    rep3 = report(env, "--max-hash-gib", "0")
    assert _rels(rep3, "archived") == {R_ARCH} and rep3["hashing"]["cache_hits"] == 2


def test_hard_link_in_vault_is_not_a_copy(env):
    p = rollout(env, R_ARCH, b"A" * 64, vault=False)
    (env["vault"] / R_ARCH).parent.mkdir(parents=True)
    os.link(p, env["vault"] / R_ARCH)
    assert _rels(report(env), "unarchived") == {R_ARCH}


def test_apply_refuses_without_or_with_wrong_token(env):
    p = rollout(env, R_ARCH, b"A" * 64)
    rep = report(env)
    tok = rep["confirm_token"]
    assert run(env, "apply", "--older-than-days", "14").returncode == 4
    assert run(env, "apply", "--older-than-days", "14", "--confirm-token", "0" * 20).returncode == 4
    assert run(env, "apply", "--older-than-days", "14", "--confirm-token", "nothex").returncode == 4
    # the right token with a different window is refused too
    assert run(env, "apply", "--older-than-days", "7", "--confirm-token", tok).returncode == 4
    # an edited manifest no longer hashes to its token
    m = Path(rep["manifest"])
    doc = json.loads(m.read_text())
    doc["rollouts"].append(dict(doc["rollouts"][0], rel="2026/08/09/rollout-x.jsonl"))
    m.write_text(json.dumps(doc))
    assert run(env, "apply", "--older-than-days", "14", "--confirm-token", tok).returncode == 4
    assert p.exists()
    assert not (env["state"] / "ledger.jsonl").exists() or \
        "unlink" not in (env["state"] / "ledger.jsonl").read_text()


def test_apply_deletes_only_archived_old_files_and_ledgers_them(env):
    keep = {
        R_NOVAULT: rollout(env, R_NOVAULT, b"B" * 64, vault=False),
        R_HASHDIFF: rollout(env, R_HASHDIFF, b"C" * 64, vault_data=b"D" * 64),
        R_YOUNG: rollout(env, R_YOUNG, b"E" * 64, mtime=time.time() - 3600),
    }
    p_arch = rollout(env, R_ARCH, b"A" * 64)
    p_open = rollout(env, R_OPEN, b"O" * 64)
    with open(p_open, "rb"):
        rep = report(env)
        assert _rels(rep, "archived") == {R_ARCH}
        res = run(env, "apply", "--older-than-days", "14",
                  "--confirm-token", rep["confirm_token"], check_rc=0)
    out = json.loads(res.stdout)
    assert out["unlinked"] == 1 and out["unlinked_bytes"] == 64
    assert not p_arch.exists()
    assert (env["vault"] / R_ARCH).exists(), "the vault copy must never be touched"
    assert p_open.exists() and all(p.exists() for p in keep.values())
    led = [json.loads(ln) for ln in (env["state"] / "ledger.jsonl").read_text().splitlines()]
    unl = [r for r in led if r["action"] == "unlink"]
    assert len(unl) == 1 and unl[0]["path"] == str(p_arch) and unl[0]["size"] == 64
    assert unl[0]["sha256"] and unl[0]["token"] == rep["confirm_token"]


def test_apply_skips_a_file_changed_after_report(env):
    p = rollout(env, R_ARCH, b"A" * 64)
    tok = report(env)["confirm_token"]
    _write(p, b"Z" * 64, OLD + 5)  # same size, new content and mtime
    out = json.loads(run(env, "apply", "--older-than-days", "14",
                         "--confirm-token", tok, check_rc=0).stdout)
    assert out["unlinked"] == 0 and out["skipped"] == 1 and p.exists()


def test_open_after_report_is_skipped_at_apply(env):
    p = rollout(env, R_ARCH, b"A" * 64)
    tok = report(env)["confirm_token"]
    with open(p, "rb"):
        out = json.loads(run(env, "apply", "--older-than-days", "14",
                             "--confirm-token", tok, check_rc=0).stdout)
    assert out["unlinked"] == 0 and p.exists()


def _release(env, name: str, mtime: float, real_binary: bool = False) -> Path:
    d = env["home"] / "packages" / "app-server-daemon" / "releases" / name
    (d / "bin").mkdir(parents=True)
    if real_binary:
        # /bin/sleep on this host is a multi-call (uutils) binary that dispatches on argv0,
        # so the stand-in `codex` is a copy of the (standalone) python interpreter instead.
        shutil.copy2(os.path.realpath(sys.executable), d / "bin" / "codex")
    else:
        _write(d / "bin" / "codex", b"#!/bin/false\n")
    _write(d / "codex-package.json", b"{}")
    os.utime(d, (mtime, mtime))
    return d


def test_package_release_referenced_by_running_process_is_kept(env):
    r1 = _release(env, "0.1.0-x", OLD, real_binary=True)
    r2 = _release(env, "0.2.0-x", OLD + 10)
    r3 = _release(env, "0.3.0-x", OLD + 20)
    r4 = _release(env, "0.4.0-x", OLD + 30)
    os.symlink(r4, env["home"] / "packages" / "app-server-daemon" / "current")
    proc = subprocess.Popen([str(r1 / "bin" / "codex"), "-S", "-c", "import time; time.sleep(120)"],
                            env=dict(os.environ, PYTHONHOME=sys.base_prefix),
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.time() + 5
        while time.time() < deadline:
            try:
                if os.readlink(f"/proc/{proc.pid}/exe") == str(r1 / "bin" / "codex"):
                    break
            except OSError:
                pass
            time.sleep(0.05)
        assert proc.poll() is None, "stand-in codex exited early"
        rep = report(env, "--keep-releases", "1")
        by = {p["release"]: p for p in rep["packages"]["releases"]}
        assert by["0.1.0-x"]["verdict"] == "keep"
        assert "referenced by a running process" in by["0.1.0-x"]["keep_reasons"]
        assert by["0.4.0-x"]["verdict"] == "keep" and "current" in by["0.4.0-x"]["keep_reasons"]
        assert by["0.2.0-x"]["verdict"] == "eligible" and by["0.3.0-x"]["verdict"] == "eligible"
        assert rep["observer"]["channels"]["proc_scan"] == "present"
        out = json.loads(run(env, "apply", "--older-than-days", "14", "--keep-releases", "1",
                             "--confirm-token", rep["confirm_token"], check_rc=0).stdout)
        assert out["rmtree"] == 2
        assert r1.exists() and r4.exists() and not r2.exists() and not r3.exists()
        led = (env["state"] / "ledger.jsonl").read_text()
        assert led.count('"action": "rmtree"') == 2
    finally:
        proc.kill()
        proc.wait(timeout=10)
        assert proc.poll() is not None


def test_sqlite_is_report_only_and_never_opened(env):
    db = _write(env["home"] / "state_5.sqlite", b"x" * 1000)
    _write(env["home"] / "state_5.sqlite-wal", b"w" * 10)
    before = db.stat()
    rep = report(env)
    s = {r["name"]: r for r in rep["sqlite"]}["state_5.sqlite"]
    assert s["bytes"] == 1000 and s["wal_bytes"] == 10 and s["action"].startswith("report-only")
    after = db.stat()
    assert (before.st_mtime_ns, before.st_size) == (after.st_mtime_ns, after.st_size)
    assert not (env["home"] / "state_5.sqlite-shm").exists()


def test_missing_home_exits_3(env):
    shutil.rmtree(env["home"])
    assert run(env, "report", "--json").returncode == 3
