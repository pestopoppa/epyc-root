"""BK-1 / BK-4: backup_loop_state.sh and restore_test_loop_state.sh against a tiny fixture tree only.
Never touches /mnt/raid0/llm, /mnt/micron or any real state; the 'large DB' threshold is lowered via env."""
import os
import sqlite3
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BACKUP = ROOT / "scripts/backup/backup_loop_state.sh"
RESTORE = ROOT / "scripts/backup/restore_test_loop_state.sh"


def mkdb(path: Path, rows=5, pad=0):
    path.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(path)
    c.execute("create table t(a text)")
    c.executemany("insert into t values (?)", [("x" * (pad or 10),)] * rows)
    c.commit()
    c.close()


@pytest.fixture
def fx(tmp_path):
    src, dst = tmp_path / "src", tmp_path / "dst"
    (src / "state/vidya/loop-memo").mkdir(parents=True)
    (src / "state/vidya/ledger.jsonl").write_text('{"a":1}\n{"a":2}\n')
    (src / "state/vidya/ledger.jsonl.lock").write_text("")
    (src / "state/vidya/loop-memo/m.json").write_text("{}")
    st = src / "autokernel/campaigns/c1/store-abc"
    mkdb(st / "experiments.db")
    (st / "inbox").mkdir()
    (st / "inbox/seed1.json").write_text("{}")
    (st / "journal-1.jsonl").write_text("j\n")
    mkdb(st / "resume-claims.sqlite3")
    (st / "experiments.db-wal").write_text("junk-wal")
    mkdb(src / "autokernel/campaigns/c2/store/experiments.db", rows=2000, pad=200)  # the "large" one (~0.5 MB)
    (src / "autokernel/campaigns/c1/inputs-x").mkdir()
    (src / "autokernel/campaigns/c1/inputs-x/b.json").write_text("{}")
    mkdb(src / "autokernel/loop-memory/experiments.db")
    o = src / "epyc-orchestrator/orchestration"
    (o / "autopilot_checkpoints").mkdir(parents=True)
    (o / "autopilot_checkpoints/ck.json").write_text("{}")
    (o / "autopilot_state.json").write_text("{}")
    (o / "autopilot_journal.jsonl").write_text("1\n")
    mkdb(o / "repl_memory/strategies/strategies.db")
    (o / "operator_hypotheses.yaml").write_text("a: 1\n")
    dst.mkdir()
    return src, dst, tmp_path / "local_status"


def run(fx, script=BACKUP, **env):
    src, dst, ls = fx
    e = dict(os.environ, SRC_ROOT=str(src), BACKUP_ROOT=str(dst / "bk"), LOCAL_STATUS_FILE=str(ls),
             ALLOW_SAME_DEVICE="1", LARGE_DB_MIN_BYTES="100000", SNAPSHOT_DATE="20261109")
    e.update({k: str(v) for k, v in env.items()})
    return subprocess.run(["bash", str(script)], capture_output=True, text=True, env=e)


def test_snapshot_complete_manifest_valid_and_status(fx):
    src, dst, ls = fx
    r = run(fx)
    assert r.returncode == 0, r.stdout + r.stderr
    snap = dst / "bk/20261109"
    for rel in ("state/vidya/ledger.jsonl", "state/vidya/loop-memo/m.json", "autokernel/loop-memory/experiments.db",
                "autokernel/campaigns/c1/store-abc/experiments.db", "autokernel/campaigns/c1/store-abc/inbox/seed1.json",
                "autokernel/campaigns/c1/store-abc/journal-1.jsonl", "autokernel/campaigns/c1/inputs-x/b.json",
                "epyc-orchestrator/orchestration/autopilot_checkpoints/ck.json",
                "epyc-orchestrator/orchestration/repl_memory/strategies/strategies.db",
                "epyc-orchestrator/orchestration/operator_hypotheses.yaml"):
        assert (snap / rel).is_file(), rel
    assert not (snap / "autokernel/campaigns/c1/store-abc/experiments.db-wal").exists()
    assert subprocess.run(["sha256sum", "-c", "--quiet", "SHA256SUMS"], cwd=snap).returncode == 0
    for p in (dst / "bk/LAST_STATUS", ls):
        assert " STATUS OK " in p.read_text()
    assert not list((dst / "bk").glob("*.partial"))
    assert sqlite3.connect(snap / "autokernel/loop-memory/experiments.db").execute("pragma integrity_check").fetchone() == ("ok",)


def test_large_db_policy_exclude_default_weekly_include(fx):
    src, dst, _ = fx
    big = "autokernel/campaigns/c2/store/experiments.db"
    assert run(fx).returncode == 0                                  # default: exclude
    snap = dst / "bk/20261109"
    assert not (snap / big).exists() and big in (snap / "SKIPPED.txt").read_text()
    assert run(fx, SNAPSHOT_DATE="20261110", LARGE_DB_POLICY="include").returncode == 0
    assert (dst / "bk/20261110" / big).is_file()
    assert run(fx, SNAPSHOT_DATE="20261111", LARGE_DB_POLICY="weekly").returncode == 0      # a Wednesday
    assert not (dst / "bk/20261111" / big).exists()
    assert run(fx, SNAPSHOT_DATE="20261115", LARGE_DB_POLICY="weekly").returncode == 0      # a Sunday
    assert (dst / "bk/20261115" / big).is_file()
    assert run(fx, LARGE_DB_POLICY="bogus", SNAPSHOT_DATE="20261120").returncode == 2


def test_failure_is_nonzero_writes_failed_status_and_leaves_no_snapshot(fx):
    src, dst, ls = fx
    (src / "autokernel/loop-memory/experiments.db").write_bytes(b"this is not a sqlite database" * 50)
    r = run(fx)
    assert r.returncode != 0
    assert " STATUS FAILED" in ls.read_text() and " STATUS FAILED" in (dst / "bk/LAST_STATUS").read_text()
    assert not (dst / "bk/20261109").exists() and not list((dst / "bk").glob("*.partial"))


def test_refuses_same_device_unless_allowed_and_missing_parent(fx):
    src, dst, ls = fx
    r = run(fx, ALLOW_SAME_DEVICE="0")
    assert r.returncode == 2 and "same device" in r.stdout
    assert " STATUS FAILED" in ls.read_text()
    r = run(fx, BACKUP_ROOT=dst / "absent-mount/bk")
    assert r.returncode == 2 and not (dst / "absent-mount").exists()


def test_empty_scope_fails_and_rerun_same_day_is_noop(fx, tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    assert run(fx, SRC_ROOT=empty).returncode == 5
    assert run(fx).returncode == 0
    r = run(fx)
    assert r.returncode == 0 and "already exists" in r.stdout


def test_retention_keeps_7_daily_and_4_weekly(fx):
    src, dst, _ = fx
    bk = dst / "bk"
    old = []
    for i in range(1, 29):                    # 20261001..20261028 pre-made dirs with manifests
        d = bk / f"202610{i:02d}"
        d.mkdir(parents=True)
        (d / "SHA256SUMS").write_text("")
        old.append(d.name)
    (bk / "notadate").mkdir()
    (bk / "20260101").mkdir()                 # old dir WITHOUT manifest: never deleted
    assert run(fx, SNAPSHOT_DATE="20261029").returncode == 0
    left = sorted(p.name for p in bk.iterdir() if p.is_dir())
    daily = [f"202610{i}" for i in range(23, 30)]
    # Sundays in Oct 2026: 4, 11, 18, 25 -> newest 4 weekly
    weekly = ["20261004", "20261011", "20261018", "20261025"]
    assert left == sorted(set(daily + weekly + ["notadate", "20260101"]))


def _restore(fx, tmp_path, cli_body):
    cli = tmp_path / "cli.py"
    cli.write_text(cli_body)
    return subprocess.run(["bash", str(RESTORE), "--backup-root", str(fx[1] / "bk"), "--scratch", str(tmp_path / "scr"),
                           "--vidya-cli", str(cli)], capture_output=True, text=True)


def test_restore_test_passes_then_detects_corruption(fx, tmp_path):
    assert run(fx).returncode == 0
    ok_cli = 'import sys\nprint(\'{"chain_ok": true}\')\n'
    r = _restore(fx, tmp_path, ok_cli)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PASS sha256sum -c" in r.stdout and "PASS vidya verify chain_ok" in r.stdout
    assert not (tmp_path / "scr").exists()                      # scratch cleaned
    r = _restore(fx, tmp_path, 'print(\'{"chain_ok": false}\')\n')
    assert r.returncode == 1 and "FAIL vidya verify" in r.stdout
    snap = fx[1] / "bk/20261109"
    (snap / "autokernel/loop-memory/inbox").mkdir(exist_ok=True)
    victim = snap / "state/vidya/loop-memo/m.json"
    victim.write_text("tampered")
    r = _restore(fx, tmp_path, ok_cli)
    assert r.returncode == 1 and "FAIL sha256sum -c" in r.stdout


def test_restore_flags_corrupt_db_and_missing_cli(fx, tmp_path):
    assert run(fx).returncode == 0
    snap = fx[1] / "bk/20261109"
    db = snap / "autokernel/loop-memory/experiments.db"
    db.write_bytes(db.read_bytes()[:2000] + b"\0" * 3000)       # break pages; manifest rewritten so only the DB check can catch it
    subprocess.run("find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS", shell=True, cwd=snap, check=True)
    r = subprocess.run(["bash", str(RESTORE), "--backup-root", str(fx[1] / "bk"), "--scratch", str(tmp_path / "scr"),
                        "--vidya-cli", str(tmp_path / "missing.py")], capture_output=True, text=True)
    assert r.returncode == 1
    assert "PASS sha256sum -c" in r.stdout and "FAIL integrity_check autokernel/loop-memory/experiments.db" in r.stdout
    assert "FAIL vidya verify (ledger or cli missing" in r.stdout
