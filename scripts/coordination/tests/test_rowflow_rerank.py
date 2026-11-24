"""`rowflow.py rerank`: owner-only in-place priority_rank change of a queued ready row (no re-smoke) + stale-predecessor fix."""
import json
import os
import sys
import threading

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "rowflow"))
import rowflow as rf  # noqa: E402
import supersedes_check as SC  # noqa: E402

RID = "ak-verify-attn-x"


def wj(p, d):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(d, open(p, "w"))


@pytest.fixture
def flags(tmp_path):
    f = str(tmp_path)
    os.makedirs(os.path.join(f, "grants"))
    spec = os.path.join(f, "spec.json")
    wj(spec, {"id": RID, "priority_rank": 50})
    wj(rf.ready_path(f, RID), {"schema": rf.SCHEMA, "id": RID, "owner": "autokernel", "lane": "gpu", "priority_rank": 50,
                               "published_from": spec})
    wj(rf.pass_path(f, RID), {"launcher_sha256": "abc", "passed_at": "t0"})
    return f


def test_owner_only(flags):
    with pytest.raises(rf.Refused, match="only the row owner"):
        rf.rerank_row(flags, RID, 1, "pipeline-mgmt", "x", log=lambda s: None)
    assert rf.load_json(rf.ready_path(flags, RID))["priority_rank"] == 50


def test_refuses_granted_row(flags):
    open(os.path.join(flags, "grants", RID + ".grant"), "w").write("x\n")
    with pytest.raises(rf.Refused, match="grant is open"):
        rf.rerank_row(flags, RID, 1, "autokernel", "x", log=lambda s: None)


@pytest.mark.parametrize("bad", ["-1", "abc", "nan", "inf"])
def test_refuses_bad_rank(flags, bad):
    with pytest.raises(rf.Refused):
        rf.rerank_row(flags, RID, bad, "autokernel", "x", log=lambda s: None)


def test_refuses_absent_row(flags):
    with pytest.raises(rf.Refused, match="no ready"):
        rf.rerank_row(flags, "nope", 1, "autokernel", "x", log=lambda s: None)


def test_rerank_keeps_smoke_logs_history_and_next_tick_rank(flags):
    before_pass = open(rf.pass_path(flags, RID)).read()
    logs = []
    assert rf.rerank_row(flags, RID, "0", "autokernel", "verify attention first", log=logs.append) == (50, 0)
    assert open(rf.pass_path(flags, RID)).read() == before_pass
    d = rf.load_json(rf.ready_path(flags, RID))
    assert d["priority_rank"] == 0 and d["owner"] == "autokernel" and d["lane"] == "gpu"
    h = d["rerank_history"][-1]
    assert h["old"] == 50 and h["new"] == 0 and h["by"] == "autokernel" and h["spec_priority_rank"] == 50
    assert logs == ["RERANK ak-verify-attn-x 50 -> 0 by autokernel: verify_attention_first"]
    assert "RERANK ak-verify-attn-x 50 -> 0 by autokernel" in open(os.path.join(flags, "ws58-calendar-keeper.log")).read()
    assert rf.row_rank(rf.rows(flags)[RID]) == 0.0   # what allocate's candidate list reads next tick


def test_atomic_write_under_claim_lock(flags):
    import fcntl
    fd = os.open(os.path.join(flags, "grants", ".claim.lock"), os.O_CREAT | os.O_RDWR)
    fcntl.flock(fd, fcntl.LOCK_EX)
    t = threading.Thread(target=rf.rerank_row, args=(flags, RID, 3, "autokernel", "x"), kwargs={"log": lambda s: None})
    t.start()
    t.join(0.5)
    assert t.is_alive() and rf.load_json(rf.ready_path(flags, RID))["priority_rank"] == 50   # waits for the lock
    fcntl.flock(fd, fcntl.LOCK_UN)
    os.close(fd)
    t.join(5)
    assert rf.load_json(rf.ready_path(flags, RID))["priority_rank"] == 3
    assert not os.path.exists(rf.ready_path(flags, RID) + ".tmp")


def test_stale_failed_smoke_not_live_predecessor(tmp_path):
    """2026-11-24: a smoke-FAILed row leaves dryrun/<id>/unpublished.json + ended; withdraw says ABSENT, so it is not live."""
    f = str(tmp_path)
    fam = "ak-gvfattn-q4kv-gpu-20261124"
    for r in (fam, fam + "-r2"):
        wj(os.path.join(f, "dryrun", r, "unpublished.json"), {"id": r})
        open(os.path.join(f, "dryrun", r, "ended"), "w").write("rc=3\n")
    assert SC.check({"id": fam + "-r4"}, f) == ({}, None)
    assert rf.withdraw(f, fam + "-r2", "x") == "ABSENT"
    # still live: queued smoke marker, open grant, pending dry run
    wj(os.path.join(f, "dryrun", fam + "-r2", "GPU-SMOKE-QUEUED.json"), {})
    wj(os.path.join(f, "dryrun", fam + "-r3", "unpublished.json"), {"id": fam + "-r3"})
    wj(os.path.join(f, "dryrun", fam + "-r3", "RUNNING.json"), {"pid": 1})
    os.makedirs(os.path.join(f, "grants"), exist_ok=True)
    open(os.path.join(f, "grants", fam + ".grant"), "w").close()
    assert set(SC.check({"id": fam + "-r4"}, f)[0]) == {fam, fam + "-r2", fam + "-r3"}
