"""backup_coverage.py (UTM-LB1 checker, NIB2-LB1 reaper precondition) — read-only, synthetic dirs."""
from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("backup_coverage", ROOT / "scripts/system/backup_coverage.py")
bc = importlib.util.module_from_spec(spec)
sys.modules["backup_coverage"] = bc
spec.loader.exec_module(bc)


def _setup(tmp_path, monkeypatch, status_age_ok=True):
    backups = tmp_path / "backups"
    backups.mkdir()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    (backups / "LAST_STATUS").write_text(f"{now if status_age_ok else '2026-01-01T00:00:00Z'} STATUS OK\n")
    (backups / "backup.log").write_text(
        "2026-10-01T02:00:00Z BACKUP a (1G)\n2026-10-02T02:00:00Z BACKUP b (1G)\n"
        "2026-10-05T02:00:00Z VAULT v\n2026-10-05T02:10:00Z BACKUP c (1G)\n")
    vault = tmp_path / "vault"
    (vault / "epyc/codex/2026/10/01").mkdir(parents=True)
    (vault / "epyc/codex/2026/10/01/rollout-2026-10-01T00-00-00-x.jsonl").write_text("{}\n")
    live = tmp_path / "live"
    live.mkdir()
    (live / "opencode.db").write_bytes(b"x")
    monkeypatch.setattr(bc, "BACKUPS", backups)
    monkeypatch.setattr(bc, "STORES", {
        "codex_rollouts": {"live": [], "vault": [str(vault / "*/codex/*/*/*/rollout-*.jsonl")], "tar": r"rollout-"},
        "opencode_db": {"live": [str(live / "opencode.db")], "vault": [str(vault / "*/opencode*")],
                        "tar": r"opencode[^/]*\.db$", "files": [str(backups / "opencode-*.db.zst")]},
    })
    monkeypatch.setattr(bc, "job_status", lambda backups=backups, _f=bc.job_status: _f(backups))
    return backups


def test_gaps_and_job_status(tmp_path, monkeypatch):
    backups = _setup(tmp_path, monkeypatch)
    st = bc.job_status(backups)
    assert st["live"] and st["backup_day_gaps"] == ["2026-10-03..2026-10-04 (2 d)"]


def test_precondition_exit_codes(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    assert bc.main(["precondition", "--store", "codex_rollouts"]) == 0
    assert bc.main(["precondition", "--store", "opencode_db"]) == 3          # not covered: never delete
    assert bc.main(["precondition", "--store", "codex_rollouts", "--rows-before", "2999-01-01T00:00:00"]) == 4
    assert bc.main(["precondition", "--store", "nope"]) == 2


def test_snapshot_file_is_partial_not_covered(tmp_path, monkeypatch):
    backups = _setup(tmp_path, monkeypatch)
    (backups / "opencode-epyc-20261022.db.zst").write_bytes(b"z")
    r = bc.store_report("opencode_db", bc.STORES["opencode_db"], None)
    assert r["covered"] == "partial"
    assert bc.main(["precondition", "--store", "opencode_db"]) == 3


def test_stale_job_fails_precondition(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, status_age_ok=False)
    assert bc.main(["precondition", "--store", "codex_rollouts"]) == 3
