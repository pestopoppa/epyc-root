"""D-f: cross-process session lease with fencing tokens.

uvicorn serves the API from several worker PROCESSES, so the mandatory fixtures
run in real child processes (fork) against one SQLite file: simultaneous
acquire, cross-process mutual exclusion, owner crash, delayed stale writer.
PID reuse, host reboot and foreign-host owners are driven through the injected
liveness/identity seams, because they cannot be staged honestly in a test.
"""

from __future__ import annotations

import asyncio
import multiprocessing as mp
import os
import time
import uuid
from datetime import datetime, timezone

import pytest

from src.session import Checkpoint, Session, SQLiteSessionStore
from src.session.lease import (
    HeldSessionLease,
    OwnerIdentity,
    SessionLeaseHeld,
    SessionLeaseLost,
    SessionLeaseManager,
    StaleFencingToken,
    process_start_ticks,
)

_CTX = mp.get_context("fork")


@pytest.fixture
def db(tmp_path):
    store = SQLiteSessionStore(
        db_path=tmp_path / "sessions.db", embeddings_path=tmp_path / "emb.npy"
    )
    session = Session.create(name="lease", working_directory="/tmp")
    store.create_session(session)
    yield store, session.id, tmp_path / "sessions.db"
    store.close()


def _checkpoint(session_id: str) -> Checkpoint:
    return Checkpoint(
        id=str(uuid.uuid4()),
        session_id=session_id,
        created_at=datetime.now(timezone.utc),
        context_hash="sha256:test",
        artifacts={},
        execution_count=0,
        exploration_calls=0,
        message_count=0,
        trigger="test",
    )


# ── child-process bodies (module level so fork can run them) ─────────────


def _race_acquire(db_path, session_id, barrier, out):
    mgr = SessionLeaseManager(db_path)
    barrier.wait()
    try:
        lease = mgr.try_acquire(session_id, ttl_s=30)
        out.put(("won", os.getpid(), lease.fencing_token))
    except SessionLeaseHeld:
        out.put(("lost", os.getpid(), None))


def _increment_under_lease(db_path, emb_path, session_id, n, out):
    store = SQLiteSessionStore(db_path=db_path, embeddings_path=emb_path)
    try:
        for _ in range(n):
            lease = store.leases.acquire(session_id, ttl_s=30, wait_s=60)
            try:
                session = store.get_session(session_id)
                seen = session.message_count
                time.sleep(0.002)  # widen the read-modify-write window
                session.message_count = seen + 1
                store.update_session(session, fencing_token=lease.fencing_token)
            finally:
                store.leases.release(lease)
        out.put(("ok", os.getpid()))
    except Exception as exc:  # pragma: no cover - reported to the parent
        out.put(("err", repr(exc)))


def _acquire_then_crash(db_path, session_id, out):
    mgr = SessionLeaseManager(db_path)
    lease = mgr.try_acquire(session_id, ttl_s=3600)
    out.send(lease.fencing_token)  # a Pipe write is synchronous; a Queue's is not
    os._exit(0)  # no release, no cleanup: a crashed worker


def _stale_writer(db_path, emb_path, session_id, ready, go, out):
    store = SQLiteSessionStore(db_path=db_path, embeddings_path=emb_path)
    lease = store.leases.try_acquire(session_id, ttl_s=0.3)
    out.put(("token", lease.fencing_token))
    ready.set()
    go.wait(30)  # parent reclaims after expiry, then releases us
    try:
        store.save_checkpoint(_checkpoint(session_id), fencing_token=lease.fencing_token)
        out.put(("write", "landed"))
    except StaleFencingToken:
        out.put(("write", "refused"))
    try:
        store.leases.heartbeat(lease)
        out.put(("heartbeat", "renewed"))
    except SessionLeaseLost:
        out.put(("heartbeat", "lost"))
    out.put(("release", store.leases.release(lease)))
    store.close()


# ── multi-process fixtures ───────────────────────────────────────────────


def test_simultaneous_acquire_across_processes_has_one_winner(db):
    _, sid, db_path = db
    n = 6  # uvicorn worker count
    barrier = _CTX.Barrier(n)
    out = _CTX.Queue()
    procs = [_CTX.Process(target=_race_acquire, args=(db_path, sid, barrier, out)) for _ in range(n)]
    for p in procs:
        p.start()
    results = [out.get(timeout=60) for _ in range(n)]
    for p in procs:
        p.join(30)
        assert p.exitcode == 0
    winners = [r for r in results if r[0] == "won"]
    assert len(winners) == 1
    assert winners[0][2] == 1


def test_leased_read_modify_write_loses_no_update_across_six_processes(db, tmp_path):
    store, sid, db_path = db
    workers, per_worker = 6, 8
    out = _CTX.Queue()
    procs = [
        _CTX.Process(
            target=_increment_under_lease,
            args=(db_path, tmp_path / f"emb{i}.npy", sid, per_worker, out),
        )
        for i in range(workers)
    ]
    for p in procs:
        p.start()
    results = [out.get(timeout=120) for _ in range(workers)]
    for p in procs:
        p.join(30)
    assert all(r[0] == "ok" for r in results), results
    assert store.get_session(sid).message_count == workers * per_worker
    # One acquisition per increment: the token counted every one of them.
    assert store.leases.get(sid).fencing_token == workers * per_worker


def test_crashed_owner_is_reclaimed_immediately_by_liveness(db):
    store, sid, db_path = db
    recv, send = _CTX.Pipe(duplex=False)
    p = _CTX.Process(target=_acquire_then_crash, args=(db_path, sid, send))
    p.start()
    assert recv.poll(30)
    crashed_token = recv.recv()
    p.join(30)
    assert p.exitcode == 0
    assert store.leases.get(sid).is_live(time.time())  # an hour of TTL left

    lease = store.leases.try_acquire(sid, ttl_s=30)  # PID gone -> reclaimable now
    assert lease.fencing_token == crashed_token + 1


def test_delayed_stale_writer_is_fenced_off(db, tmp_path):
    store, sid, db_path = db
    before = store.get_session(sid).last_checkpoint_at
    ready, go, out = _CTX.Event(), _CTX.Event(), _CTX.Queue()
    p = _CTX.Process(
        target=_stale_writer, args=(db_path, tmp_path / "emb_w.npy", sid, ready, go, out)
    )
    p.start()
    assert ready.wait(30)
    stale_token = out.get(timeout=30)[1]

    # The child is ALIVE, so only expiry can hand the lease over.
    with pytest.raises(SessionLeaseHeld):
        store.leases.try_acquire(sid)
    time.sleep(0.4)
    mine = store.leases.try_acquire(sid, ttl_s=30)
    assert mine.fencing_token == stale_token + 1

    go.set()
    got = dict(out.get(timeout=30) for _ in range(3))
    p.join(30)
    assert got == {"write": "refused", "heartbeat": "lost", "release": False}
    assert store.get_checkpoints(sid) == []
    assert store.get_session(sid).last_checkpoint_at == before
    # The stale release did not disturb the current owner.
    assert store.leases.get(sid).is_live(time.time())
    store.save_checkpoint(_checkpoint(sid), fencing_token=mine.fencing_token)
    assert len(store.get_checkpoints(sid)) == 1


# ── in-process contract ──────────────────────────────────────────────────


def test_pid_reuse_is_detected_by_start_time(db):
    _, sid, db_path = db
    me = OwnerIdentity.current()
    owner = SessionLeaseManager(db_path, identity=me)
    owner.try_acquire(sid, ttl_s=3600)

    same = SessionLeaseManager(db_path, liveness=lambda pid: me.start_ticks)
    with pytest.raises(SessionLeaseHeld):
        same.try_acquire(sid)

    reused = SessionLeaseManager(db_path, liveness=lambda pid: "not-" + me.start_ticks)
    assert reused.try_acquire(sid).fencing_token == 2


def test_unreadable_owner_identity_is_not_treated_as_dead(db):
    _, sid, db_path = db
    SessionLeaseManager(db_path).try_acquire(sid, ttl_s=3600)
    with pytest.raises(SessionLeaseHeld):
        SessionLeaseManager(db_path, liveness=lambda pid: "").try_acquire(sid)


def test_foreign_host_owner_only_expires(db):
    _, sid, db_path = db
    me = OwnerIdentity.current()
    foreign = OwnerIdentity("other-host", me.boot_id, 1, "1")
    SessionLeaseManager(db_path, identity=foreign).try_acquire(sid, ttl_s=0.2)
    dead_everywhere = SessionLeaseManager(db_path, liveness=lambda pid: None)
    with pytest.raises(SessionLeaseHeld):
        dead_everywhere.try_acquire(sid)
    time.sleep(0.3)
    assert dead_everywhere.try_acquire(sid).fencing_token == 2


def test_rebooted_host_owner_is_dead(db):
    _, sid, db_path = db
    me = OwnerIdentity.current()
    before_reboot = OwnerIdentity(me.host, "old-boot-id", me.pid, me.start_ticks)
    SessionLeaseManager(db_path, identity=before_reboot).try_acquire(sid, ttl_s=3600)
    assert SessionLeaseManager(db_path).try_acquire(sid).fencing_token == 2


def test_release_is_idempotent_and_token_stays_monotonic(db):
    store, sid, _ = db
    first = store.leases.try_acquire(sid)
    assert store.leases.release(first) is True
    assert store.leases.release(first) is False
    second = store.leases.try_acquire(sid)
    assert second.fencing_token == first.fencing_token + 1
    assert store.leases.release(first) is False  # old holder cannot free the new one
    assert store.leases.get(sid).is_live(time.time())


def test_same_process_contender_is_also_excluded(db):
    store, sid, _ = db
    store.leases.try_acquire(sid)
    with pytest.raises(SessionLeaseHeld):
        store.leases.try_acquire(sid)
    with pytest.raises(SessionLeaseHeld):
        store.leases.acquire(sid, wait_s=0.2)


def test_writes_are_fenced_and_reads_are_not(db):
    store, sid, _ = db
    lease = store.leases.try_acquire(sid)
    session = store.get_session(sid)

    with pytest.raises(StaleFencingToken):
        store.update_session(session)
    with pytest.raises(StaleFencingToken):
        store.save_checkpoint(_checkpoint(sid))
    with pytest.raises(StaleFencingToken):
        store.delete_session(sid)
    with pytest.raises(StaleFencingToken):
        store.archive_session(sid)
    with pytest.raises(StaleFencingToken):
        store.update_session(session, fencing_token=lease.fencing_token + 1)

    # Read-only inspection is untouched by the lease.
    assert store.get_session(sid) is not None
    assert store.get_latest_checkpoint(sid) is None
    assert [s.id for s in store.list_sessions()] == [sid]

    session.name = "renamed"
    store.update_session(session, fencing_token=lease.fencing_token)
    store.save_checkpoint(_checkpoint(sid), fencing_token=lease.fencing_token)
    assert store.get_session(sid).last_checkpoint_at is not None

    store.leases.release(lease)
    with pytest.raises(StaleFencingToken):  # a released token is dead
        store.update_session(session, fencing_token=lease.fencing_token)
    store.update_session(session)  # unleased: lease-unaware callers still work
    assert store.get_session(sid).name == "renamed"


def test_heartbeat_extends_and_expired_lease_cannot_be_revived(db):
    store, sid, _ = db
    lease = store.leases.try_acquire(sid, ttl_s=0.3)
    time.sleep(0.2)
    lease = store.leases.heartbeat(lease)
    time.sleep(0.2)  # past the ORIGINAL expiry
    store.save_checkpoint(_checkpoint(sid), fencing_token=lease.fencing_token)
    time.sleep(0.35)
    with pytest.raises(SessionLeaseLost):
        store.leases.heartbeat(lease)
    with pytest.raises(StaleFencingToken):
        store.save_checkpoint(_checkpoint(sid), fencing_token=lease.fencing_token)


def test_process_start_ticks_distinguishes_missing_pid():
    assert process_start_ticks(os.getpid())
    assert process_start_ticks(2**22 + 12345) is None


def test_held_session_lease_renews_reports_and_releases(db):
    store, sid, _ = db

    async def scenario():
        async with HeldSessionLease(store.leases, sid, ttl_s=0.2, wait_s=0) as held:
            assert held.error is None and held.token == 1
            async with HeldSessionLease(store.leases, sid, ttl_s=0.2, wait_s=0) as other:
                assert other.token is None
                assert other.error.startswith("held_by_other_owner")
            await asyncio.sleep(0.5)  # > TTL: only the heartbeat keeps it alive
            assert not held.lost
            store.save_checkpoint(_checkpoint(sid), fencing_token=held.token)
        assert not store.leases.get(sid).is_live(time.time())

    asyncio.run(scenario())


def test_sessions_api_maps_a_leased_session_write_to_409(db):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from src.api.dependencies import dep_session_store
    from src.api.routes.sessions import router

    store, sid, _ = db
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[dep_session_store] = lambda: store
    lease = store.leases.try_acquire(sid)
    with TestClient(app) as client:
        assert client.get(f"/sessions/{sid}").status_code == 200  # reads unaffected
        for method, path in (
            ("post", f"/sessions/{sid}/resume"),
            ("post", f"/sessions/{sid}/archive"),
            ("delete", f"/sessions/{sid}"),
            ("post", f"/sessions/current/rename?name=x&session_id={sid}"),
        ):
            assert getattr(client, method)(path).status_code == 409, path
        store.leases.release(lease)
        assert client.post(f"/sessions/{sid}/archive").status_code == 200
