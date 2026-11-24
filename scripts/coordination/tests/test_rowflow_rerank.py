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


# ---------------------------------------------------------------- scope extension (operator 2026-11-24)
def test_operator_overrides_owner(flags):
    logs = []
    rf.rerank_row(flags, RID, 1, "operator", "op first", log=logs.append)
    assert logs[0].startswith("RERANK-OPERATOR ak-verify-attn-x 50 -> 1 by operator")
    assert rf.load_json(rf.ready_path(flags, RID))["priority_rank"] == 1


def test_family_reranks_only_ungranted(flags):
    for r in ("ak-verify-attn-y", "ak-verify-attn-z"):
        wj(rf.ready_path(flags, r), {"id": r, "owner": "autokernel", "lane": "gpu", "priority_rank": 60})
    wj(rf.ready_path(flags, "other-row"), {"id": "other-row", "owner": "autokernel", "priority_rank": 60})
    open(os.path.join(flags, "grants", "ak-verify-attn-z.grant"), "w").close()
    res = rf.rerank_family(flags, "ak-verify-attn", 2, "autokernel", "family", log=lambda s: None)
    assert res[RID] == (50, 2) and res["ak-verify-attn-y"] == (60, 2) and res["ak-verify-attn-z"].startswith("SKIP")
    assert rf.load_json(rf.ready_path(flags, "other-row"))["priority_rank"] == 60
    assert rf.load_json(rf.ready_path(flags, "ak-verify-attn-z"))["priority_rank"] == 60
    assert rf.main(["--flags", flags, "rerank", "--family", "ak-verify-attn-y", "4", "--by", "autokernel", "--reason", "r"]) == 0
    assert rf.load_json(rf.ready_path(flags, "ak-verify-attn-y"))["priority_rank"] == 4
    with pytest.raises(rf.Refused):
        rf.rerank_family(flags, "nomatch", 1, "autokernel", "r", log=lambda s: None)


def test_republish_rank_only_routes_to_rerank(flags, monkeypatch):
    import publish_row as pr
    launcher = os.path.join(flags, "l.sh")
    monkeypatch.setattr(rf, "job_sha", lambda p: "jobsha")
    open(launcher, "w").write("#!/bin/bash\necho hi\n")
    spec = {"id": RID, "owner": "autokernel", "launcher": launcher, "priority_rank": 50, "notes": "a"}
    d = rf.load_json(rf.ready_path(flags, RID))
    d["launcher"] = {"path": launcher}
    d["smoke_identity"] = pr.smoke_identity(spec, d)
    rf.atomic_json(rf.ready_path(flags, RID), d)
    # legacy row (no norank sha): rank-only change routes
    assert pr.route_rerank(dict(spec, priority_rank=0), flags, log=lambda s: None) == (50, 0)
    # a real change (or a cosmetic one on a legacy row) does not
    assert pr.route_rerank(dict(spec, priority_rank=5, estimate_s=999), flags, log=lambda s: None) is None
    # new rows carry spec_sha256_norank: cosmetic fields may differ too
    d = rf.load_json(rf.ready_path(flags, RID))
    d["spec_sha256_norank"] = pr.norank_sha(spec)
    rf.atomic_json(rf.ready_path(flags, RID), d)
    assert pr.route_rerank(dict(spec, priority_rank=3, notes="b"), flags, log=lambda s: None) == (0, 3)
    assert open(rf.pass_path(flags, RID)).read()   # PASS kept
    open(os.path.join(flags, "grants", RID + ".grant"), "w").close()
    assert pr.route_rerank(dict(spec, priority_rank=7), flags, log=lambda s: None) is None   # granted: normal path


def test_queue_status_shows_rerank_history():
    sys.path.insert(0, os.path.join(HERE, "..", "..", "..", ".claude", "skills", "inference-backlog-scheduling", "scripts"))
    import queue_status as QS
    assert QS._rerank_note({}) == ""
    assert QS._rerank_note({"rerank_history": [{"old": 50, "new": 0, "by": "operator"}]}) == " reranked[50->0 by operator]"


# --- smoke-pending rows (2026-11-24): manifest lives in dryrun/<id>/unpublished.json until PASS moves it to ready/ ---
PID = "ak-pending-x"


@pytest.fixture
def pflags(tmp_path):
    f = str(tmp_path)
    os.makedirs(os.path.join(f, "grants"))
    wj(os.path.join(rf.dry_dir(f, PID), "unpublished.json"),
       {"schema": rf.SCHEMA, "id": PID, "owner": "autokernel", "lane": "gpu", "priority_rank": 100})
    return f


def _up(f):
    return os.path.join(rf.dry_dir(f, PID), "unpublished.json")


def test_pending_rerank(pflags):
    logs = []
    assert rf.rerank_row(pflags, PID, 15, "autokernel", "edit", log=logs.append) == (100, 15)
    d = rf.load_json(_up(pflags))
    assert d["priority_rank"] == 15 and d["rerank_history"][-1]["old"] == 100
    assert logs[0].startswith("RERANK-PENDING " + PID)
    assert not os.path.exists(rf.ready_path(pflags, PID))
    assert rf.rerank_family(pflags, "ak-pending", 7, "autokernel", "fam", log=lambda s: None)[PID] == (15, 7)


def test_pending_rank_survives_pass_promotion(pflags):
    rf.rerank_row(pflags, PID, 15, "autokernel", "edit", log=lambda s: None)
    os.makedirs(os.path.dirname(rf.ready_path(pflags, PID)), exist_ok=True)
    os.replace(_up(pflags), rf.ready_path(pflags, PID))   # publish_row's PASS promotion (run_queued_smoke / GPU batch)
    d = rf.load_json(rf.ready_path(pflags, PID))
    assert d["priority_rank"] == 15 and len(d["rerank_history"]) == 1


def test_pending_owner_check(pflags):
    with pytest.raises(rf.Refused, match="only the row owner"):
        rf.rerank_row(pflags, PID, 1, "pipeline-mgmt", "x", log=lambda s: None)
    assert rf.load_json(_up(pflags))["priority_rank"] == 100
    assert rf.rerank_row(pflags, PID, 1, "operator", "x", log=lambda s: None) == (100, 1)


def test_pending_open_grant_refused(pflags):
    open(os.path.join(pflags, "grants", PID + ".grant"), "w").write("x\n")
    with pytest.raises(rf.Refused, match="grant is open"):
        rf.rerank_row(pflags, PID, 1, "autokernel", "x", log=lambda s: None)
    open(os.path.join(pflags, "grants", PID + ".grant"), "w").close()
    os.remove(os.path.join(pflags, "grants", PID + ".grant"))
    open(os.path.join(pflags, "grants", PID + ".ended"), "w").close()
    with pytest.raises(rf.Refused, match="terminal"):
        rf.rerank_row(pflags, PID, 1, "autokernel", "x", log=lambda s: None)


def test_pending_republish_rank_only_routes(pflags, monkeypatch):
    import publish_row as pr
    launcher = os.path.join(pflags, "l.sh")
    monkeypatch.setattr(rf, "job_sha", lambda p: "jobsha")
    open(launcher, "w").write("#!/bin/bash\necho hi\n")
    spec = {"id": PID, "owner": "autokernel", "launcher": launcher, "priority_rank": 100}
    d = rf.load_json(_up(pflags))
    d["launcher"] = {"path": launcher}
    d["smoke_identity"] = pr.smoke_identity(spec, d)
    d["spec_sha256_norank"] = pr.norank_sha(spec)
    rf.atomic_json(_up(pflags), d)
    assert pr.route_rerank(dict(spec, priority_rank=15), pflags, log=lambda s: None) == (100, 15)
    assert rf.load_json(_up(pflags))["priority_rank"] == 15
    assert pr.route_rerank(dict(spec, priority_rank=5, estimate_s=9), pflags, log=lambda s: None) is None
