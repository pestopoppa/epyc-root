"""Mirror of the 2026-11-06 emergency batch: multi-quarter persistence (fix A), GPU width_justification (q0-q2 only), and the four
batch-2 keeper fixes (NEEDS-OWNER heading, rank across the smoke queue, smoke_predicate multi-stage smoke, 1 s VRAM + verified
KFD residency). Each carries a negative control."""
import os

from rf2 import T0, Sim, rf, spec

WJ = "width-agnostic 32k CPU prefill; dense compute scales with threads"


def legacy(rid, **kw):
    m = {"schema": rf.LEGACY_SCHEMA, "id": rid, "owner": "o", "handoff_task": "handoffs/active/x.md:R", "launcher": "/bin/sh",
         "regions": "any-cpu-quarter", "shape": "multi-quarter(2)", "declared_shape": "multi-quarter(2)", "estimate_s": 3000,
         "min_window_s": 600, "decision_rule": "rc == 0", "priority_rank": 50, "gib": 8}
    m.update(kw)
    return m


# ---------------------------------------------------------------- fix A
def test_accepted_multiquarter_shape_is_booked_as_two_quarters_by_override_and_by_justification():
    for k in ({"shape_override": "operator: x 2026-11-06: widen"}, {"width_justification": WJ}):
        s, why = rf.map_legacy(legacy("mq", **k))
        assert why is None and s["cpus"] == "any-2-quarters"
        need = rf.parse_cpus(s["cpus"])
        assert all(sum(1 for q in rf.QUARTERS if q & o) == 2 for o in need.options)   # two whole quarters (q0 minus the smoke lane)
        assert not any(o & rf.QUARTERS[3] for o in need.options[:3])              # q0-q2 combinations first


def test_negative_control_without_override_or_justification_the_old_one_quarter_mapping_stands():
    s, _ = rf.map_legacy(legacy("mq-old"))
    assert s["cpus"] == "any-quarter"


def test_replay_two_quarter_row_is_granted_two_quarters_or_waits_never_one(tmp_path):
    s = spec("mq-row", cpus="any-2-quarters", threads=40, width_justification=WJ)
    assert rf.validate(s) == [] or all("launcher" in e or "stop" in e for e in rf.validate(s))
    for busy in (set(), set(rf.QUARTERS[0]), set(rf.QUARTERS[0]) | set(rf.QUARTERS[2]), set(rf.QUARTERS[0]) | set(rf.QUARTERS[1]) | set(rf.QUARTERS[2])):
        grants = [rf.Grant("busy", frozenset(busy), "none", False, 0, 0, T0, T0 + 9999, 1)] if busy else []
        plan = rf.admit([s], grants, T0)
        for g in plan.grants:
            assert sum(1 for q in rf.QUARTERS if q & g.cores) == 2
    free_q1_q3 = rf.admit([s], [rf.Grant("busy", frozenset(rf.QUARTERS[0] | rf.QUARTERS[2]), "none", False, 0, 0, T0, T0 + 9999, 1)], T0)
    assert [g.cores for g in free_q1_q3.grants] in ([], [rf.QUARTERS[1] | rf.QUARTERS[3]])


# ---------------------------------------------------------------- GPU width_justification (q0-q2 only)
def test_gpu_row_with_justified_q0_granted_unjustified_legacy_refused_q3_and_host_refused(tmp_path):
    sim = Sim(tmp_path)
    assert sim.publish(spec("g-wj", cpus="q0", threads=20, gpu="shared", width_justification=WJ)) == []
    assert any("q0-q2" in e for e in sim.publish(spec("g-q3", cpus="q3", threads=20, gpu="shared", width_justification=WJ)))
    assert any("q0-q2" in e for e in sim.publish(spec("g-host", cpus="q0,q1,q2,q3", threads=40, gpu="shared", width_justification=WJ)))
    plan = rf.admit([spec("g-wj", cpus="q0", threads=20, gpu="shared", width_justification=WJ)], [], T0)
    assert [g.id for g in plan.grants] == ["g-wj"] and plan.grants[0].cores == rf.QUARTERS[0] and plan.grants[0].gpu == "shared"
    m = legacy("g-leg", regions="mi210_0,0-23,184-191", shape="gpu")
    s, why = rf.map_legacy(m)
    assert s is None and "width_justification" in why                               # unjustified: refused
    s, why = rf.map_legacy({**m, "width_justification": WJ})
    assert why is None and s["gpu"] != "none"


# ---------------------------------------------------------------- batch 2
def test_escalation_heading_needs_owner_unless_operator_only_option():
    assert rf.escalation_tag([("fix and republish", False), ("unpark", False)]) == "NEEDS-OWNER"
    assert rf.escalation_tag([("fix", False), ("ratify", True)]) == "NEEDS-OPERATOR"


def test_refusal_park_writes_owner_level_escalation(tmp_path):
    rf.write_escalation(str(tmp_path), "r1", "launcher refused", [("fix and republish", False)], T0)
    text = open(os.path.join(tmp_path, "operator-escalations", "r1.md")).read()
    assert text.startswith("# PARKED NEEDS-OWNER") and "NEEDS-OPERATOR" not in text


def test_gpu_rows_worse_than_a_queued_gpu_smoke_wait_negative_control(monkeypatch):
    ready = [spec("gpu-bad", cpus="q1", threads=12, gpu="shared", rank=100), spec("gpu-good", cpus="q2", threads=12, gpu="shared", rank=5),
             spec("cpu-bad", cpus="q0", threads=12, rank=100)]
    smoke = [spec("gsmoke", cpus="q1", threads=12, gpu="shared", rank=8)]
    kept, waiting = rf.smoke_rank_gate(ready, smoke)
    assert [s["id"] for s in waiting] == ["gpu-bad"] and {s["id"] for s in kept} == {"gpu-good", "cpu-bad"}
    assert rf.smoke_rank_gate(ready, [spec("cpu-smoke", cpus="q1", threads=12, rank=1)])[1] == []   # CPU smokes never gate
    monkeypatch.setattr(rf, "SMOKE_RANK_GATE", False)
    assert rf.smoke_rank_gate(ready, smoke)[1] == []                                                  # old path: rank ignored


def test_predicate_smoke_is_multi_stage_and_stops_only_on_the_predicate():
    plain, pred = spec("p0", cpus="q0", threads=12), spec("p1", cpus="q0", threads=12, smoke_predicate="test -s out/stage2.json")
    assert rf.smoke_env(plain)["FILLER_SMOKE_UNITS"] == "1" and "FILLER_SMOKE_UNITS" not in rf.smoke_env(pred)
    assert rf.smoke_may_stop(plain, 1, False) and not rf.smoke_may_stop(pred, 5, False) and rf.smoke_may_stop(pred, 1, True)
    assert rf.validate({**pred, "launcher": "/bin/sh"}) is not None


def test_residency_sampled_at_1s_and_job_record_only_when_verified():
    assert rf.VRAM_SAMPLE_S == 1 and rf.smoke_env(spec("v", cpus="q0", threads=12))["FILLER_VRAM_SAMPLE_S"] == "1"
    big = 1 << 30
    rec = {"schema": rf.RESIDENCY_SCHEMA, "pid": 77, "vram_bytes": big, "at": rf.iso(T0 + 5)}
    assert rf.smoke_resident([0, None], rec, {77}, {77: big}, T0)[0] is True            # verified: pid in tree + KFD client
    assert rf.smoke_resident([0], rec, {1}, {77: big}, T0)[0] is False                   # pid outside the smoke's tree
    assert rf.smoke_resident([0], rec, {77}, {}, T0)[0] is False                         # never seen as a KFD client
    assert rf.smoke_resident([0], {**rec, "schema": "x"}, {77}, {77: big}, T0)[0] is False
    assert rf.smoke_resident([0], {**rec, "at": rf.iso(T0 - 600)}, {77}, {77: big}, T0)[0] is False
    assert rf.smoke_resident([big], None, set(), {}, T0)[0] is True                      # harness sample alone suffices
