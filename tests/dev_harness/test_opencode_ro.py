"""opencode mining readers use the operator's READ-ONLY snapshots (2026-10-22 ruling); live stores are refused."""
from __future__ import annotations

import importlib.util
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/dev_harness"))

import dh_privacy  # noqa: E402
import dh_sources as src  # noqa: E402
import projector  # noqa: E402

spec = importlib.util.spec_from_file_location("backup_coverage_oc", ROOT / "scripts/system/backup_coverage.py")
bc = importlib.util.module_from_spec(spec)
sys.modules["backup_coverage_oc"] = bc
spec.loader.exec_module(bc)

LIVE_PATHS = [
    "~/.local/share/opencode/opencode.db",
    "/home/node/.local/share/opencode/opencode.db",
    "/mnt/raid0/llm/opencode/epyc/opencode.db",
    "/mnt/raid0/llm/opencode/host-daniele/opencode.db",
]


def _mkdb(path: Path, sid: str) -> Path:
    c = sqlite3.connect(path)
    c.executescript("""
      CREATE TABLE session (id TEXT PRIMARY KEY, project_id TEXT, parent_id TEXT, version TEXT, agent TEXT,
                            model TEXT, time_created INTEGER);
      CREATE TABLE message (id TEXT PRIMARY KEY, session_id TEXT, time_created INTEGER, data TEXT);
      CREATE TABLE part (id TEXT PRIMARY KEY, message_id TEXT, session_id TEXT, time_created INTEGER, data TEXT);
      CREATE TABLE event (id TEXT PRIMARY KEY, data TEXT);
    """)
    c.execute("INSERT INTO event VALUES ('e', 'EVENT-TABLE-NEVER-READ')")
    c.execute("INSERT INTO session VALUES (?, 'p', NULL, '1', 'build', NULL, 1790000000000)", (sid,))
    c.execute("INSERT INTO message VALUES ('m1', ?, 1790000000001, ?)", (sid, json.dumps({"role": "user"})))
    c.execute("INSERT INTO part VALUES ('p1', 'm1', ?, 1790000000001, ?)", (sid, json.dumps({"type": "text", "text": "hi"})))
    c.commit()
    c.close()
    return path


# ─── path defaults ───────────────────────────────────────────────────────────

def test_defaults_are_the_readonly_snapshots():
    assert src.OPENCODE_RO_DBS == {"epyc": Path("/mnt/raid0/llm/opencode-db/epyc.db"),
                                   "host": Path("/mnt/raid0/llm/opencode-db/host-daniele.db")}
    assert not hasattr(src, "LIVE_OPENCODE_DB")
    a = projector.build_parser().parse_args([])
    assert a.opencode_db is None and a.tenant == "all"           # None => both snapshots; all => epyc,host,twyne
    assert src._tenants("all") == ["epyc", "host", "twyne"]
    assert src._tenants("host,epyc,host") == ["host", "epyc"]
    for p in src.OPENCODE_RO_DBS.values():
        assert not src.is_live_opencode_path(p)


def test_default_mines_both_dbs_with_source_tags(tmp_path, monkeypatch):
    dbs = {"epyc": _mkdb(tmp_path / "e.db", "ses_e"), "host": _mkdb(tmp_path / "h.db", "ses_h")}
    monkeypatch.setattr(src, "OPENCODE_RO_DBS", dbs)
    a = projector.build_parser().parse_args(["--opencode", "0"])
    units = [u for u in projector.gather_units(a) if u.harness == "opencode"]
    assert sorted((u.source, u.unit_key) for u in units) == [("epyc", "ses_e"), ("host", "ses_h")]
    assert all(r["source"] == u.source for u in units for r in u.records)
    ev = projector.project_record(units[0], units[0].records[0], b"k")
    assert ev["source"] == units[0].source
    assert not any("EVENT-TABLE-NEVER-READ" in (r.get("text") or "") for u in units for r in u.records)


def test_vault_tenants_tagged(tmp_path):
    vault = tmp_path / "vault"
    for t in src.VAULT_TENANTS:
        d = vault / t / "codex/2026/10/20"
        d.mkdir(parents=True)
        (d / f"rollout-2026-10-20T10-00-00-{t}.jsonl").write_text(
            json.dumps({"timestamp": "2026-10-20T10:00:00Z", "type": "session_meta",
                        "payload": {"id": t, "session_id": t}}) + "\n" + "x" * 3000 + "\n")
    units = list(src.select_vault_units("codex", 0, vault=vault))
    assert sorted(u.source for u in units) == ["epyc", "host", "twyne"]
    assert [u.source for u in src.select_vault_units("codex", 0, vault=vault, tenant="host")] == ["host"]


def test_reader_never_queries_event_table():
    text = (ROOT / "scripts/dev_harness/dh_sources.py").read_text()
    assert not __import__("re").search(r"(?i)\b(from|join)\s+event\b", text)


# ─── live-path refusal ───────────────────────────────────────────────────────

@pytest.mark.parametrize("live", LIVE_PATHS)
def test_live_paths_refused(live):
    assert src.is_live_opencode_path(live)
    with pytest.raises(src.LiveOpencodeStoreError, match="LIVE opencode store"):
        src.open_ro(live)
    with pytest.raises(src.LiveOpencodeStoreError):
        list(src.select_opencode_units(Path(os.path.expanduser(live)), 1))


def test_symlink_into_live_store_refused(tmp_path):
    link = tmp_path / "innocent.db"
    link.symlink_to("/mnt/raid0/llm/opencode/epyc/opencode.db")
    assert src.is_live_opencode_path(link)
    with pytest.raises(src.LiveOpencodeStoreError):
        src.open_ro(link)


def test_projector_refuses_explicit_live_db(tmp_path):
    a = projector.build_parser().parse_args(["--opencode", "1", "--opencode-db", "/mnt/raid0/llm/opencode/epyc/opencode.db"])
    with pytest.raises(src.LiveOpencodeStoreError):
        list(projector.gather_units(a))


def test_snapshot_locations_not_refused():
    for ok in ("/mnt/raid0/llm/opencode-db/epyc.db", "/mnt/raid0/llm/opencode/readonly/host-daniele.db", "/tmp/x/opencode.db"):
        assert not src.is_live_opencode_path(ok)


def test_privacy_never_write_roots(tmp_path):
    for bad in ("/mnt/raid0/llm/opencode-db/x.json", "/mnt/raid0/llm/opencode/readonly/x.json",
                "/mnt/raid0/llm/opencode/epyc/x.json"):
        with pytest.raises(dh_privacy.PrivacyError):
            dh_privacy.check_private_path(bad)


# ─── open_ro: ro, query_only, retry once ─────────────────────────────────────

def test_open_ro_is_query_only(tmp_path):
    db = _mkdb(tmp_path / "a.db", "s")
    conn = src.open_ro(db)
    try:
        assert conn.execute("PRAGMA query_only").fetchone()[0] == 1
        with pytest.raises(sqlite3.OperationalError):
            conn.execute("INSERT INTO session VALUES ('z','p',NULL,'1','a',NULL,1)")
    finally:
        conn.close()


def test_open_ro_retries_once(tmp_path):
    db = _mkdb(tmp_path / "a.db", "s")
    calls = []

    def flaky(target, **kw):
        calls.append(target)
        if len(calls) == 1:
            raise sqlite3.OperationalError("unable to open database file")
        return sqlite3.connect(target, **kw)

    conn = src.open_ro(db, retry_delay=0, _connect=flaky)
    assert len(calls) == 2 and calls[0].endswith("?mode=ro")
    assert conn.execute("select count(*) from session").fetchone()[0] == 1
    conn.close()


def test_open_ro_gives_up_after_one_retry(tmp_path):
    calls = []

    def dead(target, **kw):
        calls.append(target)
        raise sqlite3.OperationalError("unable to open database file")

    with pytest.raises(sqlite3.OperationalError):
        src.open_ro(tmp_path / "a.db", retry_delay=0, _connect=dead)
    assert len(calls) == 2


# ─── smoke on the REAL snapshots (skipped when absent) ───────────────────────

@pytest.mark.parametrize("tag", ["epyc", "host"])
def test_smoke_real_snapshot_session_count(tag):
    db = src.OPENCODE_RO_DBS[tag]
    if not db.exists():
        pytest.skip(f"{db} absent")
    conn = src.open_ro(db)
    try:
        n = conn.execute("select count(*) from session").fetchone()[0]
    finally:
        conn.close()
    print(f"SMOKE {tag}: {n} sessions")
    assert n > 0


# ─── backup_coverage: opencode covered by the hourly ro snapshots ────────────

def _snap_setup(tmp_path, monkeypatch, age_h):
    backups = tmp_path / "backups"
    backups.mkdir()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    (backups / "LAST_STATUS").write_text(f"2026-01-01T00:00:00Z STATUS OK\n")   # nightly job stale on purpose
    (backups / "backup.log").write_text("2026-10-05T02:00:00Z VAULT v\n")
    snapdir = tmp_path / "ro"
    snapdir.mkdir()
    for n in ("epyc.db", "host-daniele.db"):
        f = snapdir / n
        f.write_bytes(b"x")
        t = datetime.now(timezone.utc).timestamp() - age_h * 3600
        os.utime(f, (t, t))
    monkeypatch.setattr(bc, "BACKUPS", backups)
    monkeypatch.setattr(bc, "STORES", {"opencode_db": {
        "live": [], "snapshots": [str(snapdir / "*.db")], "vault": [str(tmp_path / "nope/*")], "tar": r"opencode[^/]*\.db$"}})
    monkeypatch.setattr(bc, "job_status", lambda backups=backups, _f=bc.job_status: _f(backups))


def test_real_opencode_spec_lists_ro_snapshots():
    assert str(bc.OPENCODE_RO_DIR / "*.db") in bc.STORES["opencode_db"]["snapshots"]


def test_fresh_snapshots_cover_opencode(tmp_path, monkeypatch):
    _snap_setup(tmp_path, monkeypatch, age_h=0.2)
    r = bc.store_report("opencode_db", bc.STORES["opencode_db"], None)
    assert r["covered"] == "covered" and r["snapshot_fresh"] and "hourly ro snapshots" in r["evidence"]
    assert bc.main(["precondition", "--store", "opencode_db"]) == 0     # independent of the (stale) nightly job


def test_stale_snapshots_do_not_cover_opencode(tmp_path, monkeypatch):
    _snap_setup(tmp_path, monkeypatch, age_h=30)
    assert bc.store_report("opencode_db", bc.STORES["opencode_db"], None)["covered"] == "not_covered"
    assert bc.main(["precondition", "--store", "opencode_db"]) == 3
