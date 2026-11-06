"""Mirror of the rowflow queued-GPU-smoke emergency fixes (operator 2026-11-06): the smoke lane drains by priority_rank, then
published_at, then id; every smoke that is not a PASS (FAIL or deadline) alerts the owner with id, reason, fix_task and the FAIL
path. Each fix has a negative control."""
import json
import os

from rf2 import T0, Sim, rf, spec


def _alerts(sim):
    p = os.path.join(sim.flags, "rowflow2-alerts.jsonl")
    return [json.loads(x) for x in open(p)] if os.path.exists(p) else []


def _q(rid, rank, pub="2026-11-06T16:00:00Z"):
    return {"id": rid, "priority_rank": rank, "published_at": pub}


def test_smoke_step_rank_then_published_then_id():
    q = [_q("ak-asm-aiter-vs-c6-timing-20261106-r2", 100), _q("c7-q38-ppl-bisect-20261106", 8),
         _q("yarn-e1-mem-c7-20261106", 8, "2026-11-06T15:00:00Z"), _q("a-tie", 8, "2026-11-06T15:00:00Z")]
    order = []
    while q:
        a = rf.smoke_step(q, None, False, 0.0)
        order.append(a[0][1])
        q = [s for s in q if s["id"] != a[0][1]]
    assert order == ["a-tie", "yarn-e1-mem-c7-20261106", "c7-q38-ppl-bisect-20261106", "ak-asm-aiter-vs-c6-timing-20261106-r2"]


def test_negative_control_old_fifo_order_runs_the_rank_100_row_first():
    q = [_q("ak-asm-aiter-vs-c6-timing-20261106-r2", 100), _q("c7-q38-ppl-bisect-20261106", 8)]
    old = sorted(q, key=lambda s: (s.get("published_at") or "", s["id"]))[0]["id"]     # the pre-fix key
    assert old == "ak-asm-aiter-vs-c6-timing-20261106-r2"
    assert rf.smoke_step(q, None, False, 0.0)[0][1] == "c7-q38-ppl-bisect-20261106"


def test_missing_or_bad_rank_defaults_to_100():
    assert rf.smoke_order_key({"id": "x"})[0] == 100.0
    assert rf.smoke_order_key({"id": "x", "priority_rank": "n/a"})[0] == 100.0
    assert rf.smoke_order_key({"id": "x", "priority_rank": 0})[0] == 0.0


def test_replay_failed_smoke_alerts_owner_once(tmp_path):
    sim = Sim(tmp_path)
    assert sim.publish(spec("c7b-fa128-gate-20261106", cpus="q1", threads=12, owner="main-inf22"), smoke_outcome="fail") == []
    for _ in range(12):
        sim.step()
    a = [x for x in _alerts(sim) if x["kind"] == "smoke-fail"]
    assert len(a) == 1, a
    assert a[0]["row_id"] == "c7b-fa128-gate-20261106" and a[0]["reason"] == "smoke failed"
    assert a[0]["fail_file"].endswith("FAIL-1.json") and a[0]["fix_task"]


def test_pass_smoke_does_not_alert(tmp_path):
    sim = Sim(tmp_path)
    assert sim.publish(spec("ok-row", cpus="q1", threads=12)) == []
    for _ in range(12):
        sim.step()
    assert [x for x in _alerts(sim) if x["kind"] == "smoke-fail"] == []


def test_negative_control_without_smoke_alert_the_failure_is_silent(tmp_path, monkeypatch):
    monkeypatch.setattr(rf, "smoke_alert", lambda *a, **k: None)
    sim = Sim(tmp_path)
    assert sim.publish(spec("c7b-fa128-gate-20261106", cpus="q1", threads=12), smoke_outcome="fail") == []
    for _ in range(12):
        sim.step()
    assert os.path.exists(os.path.join(sim.flags, "dryrun", "c7b-fa128-gate-20261106", "FAIL-1.json"))   # the FAIL happened ...
    assert _alerts(sim) == []                                                                             # ... and nobody was told


def test_deadline_kill_alerts_owner(tmp_path):
    sim = Sim(tmp_path)
    assert sim.publish(spec("hang-row", cpus="q1", threads=12), smoke_outcome="hang") == []
    for _ in range(60):
        sim.step()
    a = [x for x in _alerts(sim) if x["kind"] == "smoke-fail"]
    assert len(a) == 1 and a[0]["reason"] == "smoke deadline" and a[0]["fail_file"].endswith("FAIL-deadline.json")
