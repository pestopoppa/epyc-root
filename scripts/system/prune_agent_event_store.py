#!/usr/bin/env python3
"""Prune opencode's `event` change-feed by WHOLE SESSION (aggregate), oldest first.

EXECUTED 2026-09-07: 236.1 GB -> 11.4 GB, quick_check ok, +225 GB reclaimed. The store is an
outbox change feed retaining ~3.2 snapshots of every streamed part; content lives in
session/message/part and is never touched here. Full record and the safety gate:
progress/2026-09/2026-09-07-ak-rebuild-20260828.md and wiki/tool-implementation.md.

BEFORE RUNNING: stop every agent CLI holding the DB (a read snapshot blocks the WAL
truncation), run exactly ONE instance in ONE foreground terminal, and prove the log is not
load-bearing first -- export one old session, delete that session's events, re-export, diff.

Never touches session/message/part (the content). Never deletes a partial aggregate
(seq gaps inside a retained session). Batches by session, checkpoints the WAL between
batches so it cannot balloon, VACUUMs at the end (optional).

Preconditions the caller owns: no opencode process has the DB open; gate (step 4) passed.
"""
import argparse, sqlite3, time, sys

DB = "/home/node/.local/share/opencode/opencode.db"

ap = argparse.ArgumentParser()
ap.add_argument("--keep-days", type=float, required=True,
                help="sessions created within this many days keep their events")
ap.add_argument("--batch", type=int, default=5, help="sessions per transaction")
ap.add_argument("--apply", action="store_true", help="without this: dry run, no writes")
ap.add_argument("--vacuum", action="store_true", help="VACUUM after the deletes (only with --apply)")
a = ap.parse_args()

cutoff_ms = int((time.time() - a.keep_days * 86400) * 1000)
con = sqlite3.connect(DB, timeout=60, isolation_level=None)
con.execute("PRAGMA foreign_keys=OFF")           # never rely on the cascade (trap 1)
# Debian/Ubuntu libsqlite3 is compiled with SQLITE_SECURE_DELETE=1: every freed page is
# zero-filled and written through the WAL, so deleting ~200 GB of rows WRITES ~200 GB
# (measured 2026-09-07: 66 GB WAL, 269 GB written, ~4.5 MB/s). The content is not
# secret-grade and the freelist pages are reclaimed by VACUUM anyway, so turn it off:
# a delete then touches only b-tree/freelist-trunk pages and is near-instant.
con.execute("PRAGMA secure_delete=OFF")
assert con.execute("PRAGMA journal_mode").fetchone()[0] == "wal"

victims = con.execute(
    "SELECT s.id, s.time_created, "
    "  (SELECT count(*) FROM event e WHERE e.aggregate_id=s.id), "
    "  0 "  # byte sum would re-read the whole 200 GB payload; counts are index-covered
    "FROM session s WHERE s.time_created < ? "
    "  AND EXISTS (SELECT 1 FROM event e WHERE e.aggregate_id=s.id) "
    "ORDER BY s.time_created ASC", (cutoff_ms,)).fetchall()
tot_ev = sum(v[2] for v in victims); tot_b = sum(v[3] for v in victims)
print(f"cutoff: sessions created before {time.strftime('%Y-%m-%d %H:%M', time.gmtime(cutoff_ms/1000))}Z "
      f"(keep-days={a.keep_days})")
print(f"victims: {len(victims)} sessions, {tot_ev:,} events, {tot_b/1073741824:.1f} GB")
if not a.apply:
    print("DRY RUN — nothing deleted. Re-run with --apply."); sys.exit(0)

done_ev = done_b = 0; t0 = time.time()
for i in range(0, len(victims), a.batch):
    chunk = victims[i:i + a.batch]
    con.execute("BEGIN")
    for sid, _, _, _ in chunk:
        con.execute("DELETE FROM event WHERE aggregate_id=?", (sid,))
    con.execute("COMMIT")
    done_ev += sum(c[2] for c in chunk); done_b += sum(c[3] for c in chunk)
    busy, wal_pages, ckpt = con.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()   # trap 2
    print(f"  batch {i//a.batch+1}: {min(i+a.batch,len(victims))}/{len(victims)} sessions, "
          f"{done_ev:,} events, {done_b/1073741824:.1f} GB freed-in-db, "
          f"ckpt busy={busy} wal_pages={wal_pages} [{time.time()-t0:.0f}s]", flush=True)

left = con.execute("SELECT count(*), coalesce(sum(octet_length(data)),0) FROM event").fetchone()
print(f"remaining events: {left[0]:,} ({left[1]/1073741824:.1f} GB); freelist_count="
      f"{con.execute('PRAGMA freelist_count').fetchone()[0]:,} pages")
if a.vacuum:
    print("VACUUM ...", flush=True); t1 = time.time()
    con.execute("VACUUM")
    print(f"VACUUM done in {time.time()-t1:.0f}s")
print(f"integrity: {con.execute('PRAGMA quick_check').fetchone()[0]}")
