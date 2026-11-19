"""AUTOFILE-OWNER-LIVENESS: the two writers of filing-owner-less.jsonl (churn/auto_file.py, rowflow2 file_step) share ONE owner
liveness rule and ONE record shape. A prose row whose owner is live is routed to the owner however old; an owner-less row is
queued once, with the keys auto_file writes."""
import json
import os

from rf2 import Sim, rf, spec

E = {"rc": 0, "reason": "complete", "base": "complete", "time": 1000.0, "busy_p95": None, "cpus": None}
OLD = 1000.0 + rf.FILE_OWNERLESS_S + 60


def _acts(owner_live):
    specs = {"p": {"decision_rule": "prose", "owner": "main-inf22"}, "n": {"decision_rule": "prose", "owner": ""}}
    ended = {k: (E, 1000.0) for k in specs}
    return {a[1]: a[0] for a in rf.file_decisions(ended, specs, {}, OLD, owner_live)}


def test_live_owner_keeps_the_row_however_old_dead_owner_and_no_owner_go_owner_less():
    assert _acts(lambda o: True) == {"p": "route-owner", "n": "owner-less"}   # no owner is never live
    assert _acts(lambda o: False) == {"p": "owner-less", "n": "owner-less"}
    assert _acts(None) == {"p": "owner-less", "n": "owner-less"}              # old age-only behaviour, unchanged


def test_one_liveness_rule_shared_with_auto_file(tmp_path):
    flags, bus = str(tmp_path / "flags"), str(tmp_path / "bus")
    os.makedirs(flags)
    os.makedirs(os.path.join(bus, "outbox"))
    live = rf._owner_liveness(flags, OLD)
    assert live is not None
    import auto_file
    assert live("main-inf22") == auto_file.owner_live("main-inf22", flags, auto_file.DEFAULT_BUS, 1800, OLD)
    assert live("")[0] is False


def test_record_carries_auto_file_keys_and_dedups_against_either_writer(tmp_path):
    rid = "lsa-oracle-reference-build-f6dddb7-20261104"
    rec = rf.owner_less_record(rid, {"owner": "main-inf22", "decision_rule": "judge by eye", "handoff_task": "h.md:T"}, "no running session", rf.parse_iso("2026-11-09T00:00:00Z"))
    for k in ("id", "at", "queued_at", "owner", "owner_state", "decision_rule", "handoff_task", "file_with", "writer"):
        assert k in rec
    q = tmp_path / "filing-owner-less.jsonl"
    q.write_text(json.dumps(rec, sort_keys=True) + "\n")
    import re
    # rowflow2's `routed` dedup regex and auto_file's json reader both find the id in the shared record
    assert re.findall(r'"id": "([^"]+)"', q.read_text()) == [rid]
    assert [json.loads(l)["id"] for l in q.read_text().splitlines()] == [rid]
