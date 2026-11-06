"""Pass 4 fixtures (keeper-friction-review-20261105.md P4.3 #1, #2, #4 + INF-22 GPU ordering, operator decision 2026-11-06).
Every fix has a NEGATIVE CONTROL: the same scenario with the fix's switch off must FAIL the new assertion, so no test here
is a tautology."""
import glob
import json
import os

import pytest

from rf2 import T0, TICK_S, Sim, check_plan, rf, spec

G = lambda sim, *p: os.path.join(sim.flags, "grants", *p)  # noqa: E731
D = lambda sim, *p: os.path.join(sim.flags, "dryrun", *p)  # noqa: E731


def _until_granted(sim, rid, max_steps=12):
    for _ in range(max_steps):
        if any(f" GRANT {rid} " in x for x in sim.lines):
            return
        sim.step()
    raise AssertionError(f"fixture: {rid} never granted; {sim.lines[-5:]}")


def _alerts(sim, kind="refused"):
    p = os.path.join(sim.flags, "rowflow2-alerts.jsonl")
    return [json.loads(l) for l in open(p)] if os.path.exists(p) else []


# ================================================================ fix 1: refusal terminal once (P4.3 #1, P4.4 row 1)
def test_p4_1_precond_refusal_parks_once_one_fail_one_alert(tmp_path):
    """kpf41-direct-vec-impact-r5 / kpf50: --precond-cmd refused 171 times, once per 120 s tick, 171 FAIL files, 171 alerts.
    rowflow2: the first refusal parks the row (state `parked`); ONE FAIL-refused record, ONE alert, ONE launcher attempt;
    the row is neither re-granted nor filed `done` for the rest of the day."""
    sim = Sim(tmp_path)
    assert sim.publish(spec("kpf41-direct-vec-impact-r5", cpus="q1", threads=12, est=1800), refuse="released") == []
    _until_granted(sim, "kpf41-direct-vec-impact-r5")
    for _ in range(90):   # 3 h of ticks: the live loop produced 90 refusals in this span
        sim.step()
    grants = [x for x in sim.lines if " GRANT kpf41-direct-vec-impact-r5 " in x]
    refused = [x for x in sim.lines if " REFUSED kpf41-direct-vec-impact-r5 " in x]
    assert len(grants) == 1 and len(refused) == 1, (grants, refused)
    assert len(sim.refusals) == 1, "the launcher was asked again after it refused"
    assert len(glob.glob(D(sim, "kpf41-direct-vec-impact-r5", "FAIL-refused-*.json"))) == 1
    assert [a["row_id"] for a in _alerts(sim)] == ["kpf41-direct-vec-impact-r5"]
    w = rf.load_world(sim.flags, sim.now)
    assert w.state["kpf41-direct-vec-impact-r5"] == "parked" and "kpf41-direct-vec-impact-r5" in w.parked
    assert not glob.glob(G(sim, "kpf41-direct-vec-impact-r5.*")), "a parked row holds no grant / ended / complete"
    assert not os.path.exists(os.path.join(sim.flags, "filing-done", "kpf41-direct-vec-impact-r5.FILED")), "a refusal is not a verdict"


def test_p4_1_build_missing_ended_variant_parks_and_keeps_evidence(tmp_path):
    """filler_run15 --precond-cmd contract: `.ended rc=5 reason=build-missing:...`, grant deleted. Same park; the refusing
    .ended is kept as dryrun/<id>/REFUSED-1.ended, never filed as a job verdict."""
    sim = Sim(tmp_path)
    assert sim.publish(spec("kpf50-child-evidence-main-impact-r2", cpus="q2", threads=12), refuse="build-missing") == []
    _until_granted(sim, "kpf50-child-evidence-main-impact-r2")
    for _ in range(6):
        sim.step()
    rid = "kpf50-child-evidence-main-impact-r2"
    assert rf.load_world(sim.flags, sim.now).state[rid] == "parked"
    assert os.path.exists(D(sim, rid, "REFUSED-1.ended")) and not os.path.exists(G(sim, rid + ".ended"))
    assert len(glob.glob(D(sim, rid, "FAIL-refused-*.json"))) == 1 and len(_alerts(sim)) == 1
    assert not glob.glob(os.path.join(sim.flags, "filing-done", rid + ".*"))
    rec = json.load(open(D(sim, rid, "FAIL-refused-1.json")))
    assert rec["refusal"] == "build-missing" and rec["rc"] == 5 and rec["launcher_sha256"] and rec["spec_sha256"]


def test_p4_1_retry_only_after_sha_change_or_operator_unpark(tmp_path):
    """The park binds the row AS PUBLISHED. (a) `unpark` lifts it: exactly one more attempt, then parked again (FAIL-refused-2,
    second alert). (b) a launcher edit lifts it by itself (UNPARK-AUTO) and the row goes back through the smoke."""
    sim = Sim(tmp_path)
    rid = "kpf41-backend-gpu-qualification"
    assert sim.publish(spec(rid, cpus="q1", threads=12), refuse="released") == []
    _until_granted(sim, rid)
    for _ in range(4):
        sim.step()
    assert len(sim.refusals) == 1 and rf.load_world(sim.flags, sim.now).state[rid] == "parked"
    # (a) operator unpark -> one re-grant, one more refusal, parked again; no third attempt
    assert rf.main(["unpark", "--flags", sim.flags, "--id", rid]) == 0
    assert rf.load_world(sim.flags, sim.now).state[rid] == "pending"
    for _ in range(6):
        sim.step()
    assert len(sim.refusals) == 2, sim.refusals
    assert len(glob.glob(D(sim, rid, "FAIL-refused-*.json"))) == 2 and len(_alerts(sim)) == 2
    assert rf.load_world(sim.flags, sim.now).state[rid] == "parked"
    assert rf.main(["unpark", "--flags", sim.flags, "--id", "never-published"]) == 1
    # (b) the launcher changes: the park no longer binds, the row needs a fresh smoke (PASS sha is stale too)
    with open(sim.specs[rid]["launcher"], "a") as f:
        f.write("# fixed precond target\n")
    sim.step()
    assert any(f" UNPARK-AUTO {rid}" in x for x in sim.lines)
    assert not os.path.exists(D(sim, rid, "PARKED.json"))
    assert rf.load_world(sim.flags, sim.now).state[rid] in ("needs-smoke", "smoking")
    # (c) a manifest change alone (same launcher) also lifts the park: republish with a new estimate
    sim2 = Sim(tmp_path / "b")
    assert sim2.publish(spec("m", cpus="q1", threads=12, est=1800), refuse="released") == []
    _until_granted(sim2, "m")
    sim2.step(); sim2.step()
    assert rf.load_world(sim2.flags, sim2.now).state["m"] == "parked"
    d = json.load(open(os.path.join(sim2.flags, "ready", "m.json")))
    d["estimate_s"] = 2400
    json.dump(d, open(os.path.join(sim2.flags, "ready", "m.json"), "w"))
    assert rf.load_world(sim2.flags, sim2.now).state["m"] == "pending" and "m" in rf.load_world(sim2.flags, sim2.now).stale_parks


def test_p4_1_negative_control_without_park_the_row_loops_every_tick(tmp_path, monkeypatch):
    """Switch the fix off: the released grant is re-granted every tick and the launcher refuses every tick - the live 171-loop.
    The assertions of the fixture above fail here, so they measure the fix and not the harness."""
    monkeypatch.setattr(rf, "PARK_ON_REFUSAL", False)
    sim = Sim(tmp_path)
    assert sim.publish(spec("kpf41-direct-vec-impact-r5", cpus="q1", threads=12, est=1800), refuse="released") == []
    _until_granted(sim, "kpf41-direct-vec-impact-r5")
    for _ in range(10):
        sim.step()
    grants = [x for x in sim.lines if " GRANT kpf41-direct-vec-impact-r5 " in x]
    assert len(grants) >= 5 and len(sim.refusals) >= 5, "old path did not loop: the fixture would not detect the defect"
    assert not glob.glob(D(sim, "kpf41-direct-vec-impact-r5", "FAIL-refused-*.json")) and not _alerts(sim)
    assert rf.load_world(sim.flags, sim.now).state["kpf41-direct-vec-impact-r5"] in ("pending", "running"), "never parked"


# ================================================================ fix 2: a completed row is not a dead poller (P4.3 #2)
def test_p4_2_dead_poller_with_completion_receipt_is_a_completion():
    """11 of 11 live rc=14 'pid dead' FAILs had grants/<id>.complete: the poller was gone because the job had FINISHED.
    Pure rule: dead IDLE_SAMPLES samples + completion receipt -> ('completed'), never ('dead-poller')."""
    g = rf.Grant("v11-122-llg-build-cpu", rf.QUARTERS[1], "none", False, 8, 1, T0, T0 + 3600, 1800)
    h = rf.Grant("still-running-and-dead", rf.QUARTERS[2], "none", False, 8, 1, T0, T0 + 3600, 1800)
    state, acts = {}, []
    for i in range(rf.IDLE_SAMPLES):
        a, state = rf.reconcile([g, h], rf.Measurement(core_busy={c: 50.0 for c in range(96)}, alive={g.id: False, h.id: False},
                                                       complete=frozenset({g.id})), state, T0 + 120 * i)
        acts += a
    assert ("completed", g.id) in acts and ("dead-poller", g.id) not in acts
    assert ("dead-poller", h.id) in acts, "a genuinely dead poller without a receipt still ends rc=75"


def test_p4_2_tick_rechecks_the_receipt_at_write_time(tmp_path, monkeypatch):
    """The live race: the job completed 1 s before the keeper judged the poller dead. Even when the measurement predates
    the receipt, tick() re-reads grants/ before writing rc=75: COMPLETED is logged and no dead-poller .ended is written."""
    sim = Sim(tmp_path)
    assert sim.publish(spec("c6q4isum-llg-build-gpu", cpus=0, threads=8, gpu="shared", est=1800)) == []
    _until_granted(sim, "c6q4isum-llg-build-gpu")
    rid = "c6q4isum-llg-build-gpu"
    orig = rf.reconcile

    def racing_reconcile(grants, meas, state, now):   # the receipt lands AFTER the measurement judged the poller dead
        acts, new = orig(grants, meas, state, now)
        if any(a[0] == "dead-poller" and a[1] == rid for a in acts):
            open(G(sim, rid + ".complete"), "w").write(f"complete time={rf.iso(now)} id={rid}\n")
        return acts, new
    monkeypatch.setattr(rf, "reconcile", racing_reconcile)
    dead = lambda: rf.Measurement(core_busy={c: 0.0 for c in range(96)}, own_kfd={rid: set()}, alive={rid: False})  # noqa: E731
    sim.measurement = dead
    sim.runs[rid] = {"end": float("inf"), "use": frozenset(), "spin": sim.now}   # the fake filler never writes .ended itself
    for _ in range(rf.IDLE_SAMPLES + 1):
        sim.step()
    assert any(f" COMPLETED {rid}" in x for x in sim.lines), sim.lines[-6:]
    assert not any(f" DEAD-POLLER {rid}" in x for x in sim.lines)
    assert not os.path.exists(G(sim, rid + ".ended")), "a completed row got a dead-poller .ended"


def test_p4_2_negative_control_old_path_writes_rc75_over_a_completed_row(tmp_path, monkeypatch):
    monkeypatch.setattr(rf, "COMPLETE_BEATS_DEAD", False)
    g = rf.Grant("v11-122-llg-build-cpu", rf.QUARTERS[1], "none", False, 8, 1, T0, T0 + 3600, 1800)
    state, acts = {}, []
    for i in range(rf.IDLE_SAMPLES):
        a, state = rf.reconcile([g], rf.Measurement(core_busy={}, alive={g.id: False}, complete=frozenset({g.id})), state, T0 + 120 * i)
        acts += a
    assert ("dead-poller", g.id) in acts and ("completed", g.id) not in acts, "old path did not misjudge: fixture is vacuous"
    # and at tick level the old path writes the false rc=75 .ended the live keeper wrote 11 times
    sim = Sim(tmp_path)
    assert sim.publish(spec("lsa-gpu-dense-bf16-8k", cpus="q1", threads=12, est=1800)) == []
    _until_granted(sim, "lsa-gpu-dense-bf16-8k")
    rid = "lsa-gpu-dense-bf16-8k"
    orig = rf.reconcile

    def racing(grants, meas, state, now):
        acts, new = orig(grants, meas, state, now)
        if any(a[0] == "dead-poller" and a[1] == rid for a in acts):
            open(G(sim, rid + ".complete"), "w").write(f"complete time={rf.iso(now)} id={rid}\n")
        return acts, new
    monkeypatch.setattr(rf, "reconcile", racing)
    sim.measurement = lambda: rf.Measurement(core_busy={c: 0.0 for c in range(96)}, alive={rid: False})
    sim.runs[rid] = {"end": float("inf"), "use": frozenset(), "spin": sim.now}
    for _ in range(rf.IDLE_SAMPLES + 1):
        sim.step()
    assert any(f" DEAD-POLLER {rid}" in x for x in sim.lines) and rf.head1(G(sim, rid + ".ended")).startswith("rc=75 reason=dead-poller")


# ================================================================ fix 3: GPU idleness by GPU signals (P4.3 #4, P4.4 rows 3-4)
def _gpu_grant():
    return rf.Grant("ak-asm-t1-harness", frozenset(range(88, 96)), "exclusive", False, 8, 1, T0, T0 + 7200, 3600)


def _run(grant, samples, step_s=120):
    """samples: [(core_pct, own_kfd_set|None, gpu_util)] -> all actions."""
    state, acts = {}, []
    for i, (pct, kfd, util) in enumerate(samples):
        own = {} if kfd is None else {grant.id: set(kfd)}
        a, state = rf.reconcile([grant], rf.Measurement(core_busy={c: pct for c in range(96)}, own_kfd=own, gpu_util=util), state, T0 + i * step_s)
        acts += a
        if any(x[0] == "idle-end" for x in a):
            break
    return acts, state


def test_p4_3_gpu_grant_with_own_kfd_pid_is_busy_whatever_the_cpu_reads():
    """ak-asm-t1-harness: a running GPU harness, CPU 0% on its sibling cores -> the frozen keeper logged IDLE-HELD 21 ticks and
    OVER-DECLARED. rowflow2: own KFD pid present = busy; no release-cores, no over-declared, no idle clock, no measured
    busy_p95 feedback from CPU %."""
    acts, state = _run(_gpu_grant(), [(90.0, {4242}, 100.0)] + [(0.0, {4242}, 100.0)] * 12)
    kinds = {a[0] for a in acts}
    assert not kinds & {"release-cores", "over-declared", "idle-warn", "idle-end", "release-gpu"}, acts
    assert rf.measured_summary(state["ak-asm-t1-harness"]) is None, "CPU-% busy_p95 must not be recorded for a gpu grant"


def test_p4_3_gpu_grant_idle_only_by_empty_kfd_and_zero_util_two_samples():
    """No own KFD pid + device ~0% across IDLE_SAMPLES -> release-gpu, then the idle clock (warn at 300 s, end at 900 s) -
    even while its CPU cores read 90% (a hot sibling is not GPU work). Device utilisation without an own pid (foreign work)
    is NOT idle; one sample is never enough."""
    acts, _ = _run(_gpu_grant(), [(90.0, set(), 0.0)] * 10)
    assert ("release-gpu", "ak-asm-t1-harness") in acts
    assert [a[0] for a in acts if a[0] in ("idle-warn", "idle-end")] == ["idle-warn", "idle-end"]
    assert not [a for a in acts if a[0] in ("release-cores", "over-declared")]
    first_rel = next(i for i, a in enumerate(acts) if a[0] == "release-gpu")
    acts1, _ = _run(_gpu_grant(), [(0.0, set(), 0.0)])
    assert not acts1, "one idle sample acted"
    acts2, _ = _run(_gpu_grant(), [(0.0, set(), 60.0)] * 10)       # device busy, no own pid: not idle, no release
    assert not [a for a in acts2 if a[0] in ("release-gpu", "idle-warn", "idle-end")], acts2
    acts3, _ = _run(_gpu_grant(), [(0.0, None, 0.0)] * 10)         # KFD side unmeasured: never idle
    assert not [a for a in acts3 if a[0] in ("release-gpu", "idle-warn", "idle-end")], acts3
    assert first_rel >= 0


def test_p4_3_negative_control_cpu_metric_misjudges_gpu_grants(monkeypatch):
    """Switch the fix off: the CPU-% path releases the sibling cores of a busy GPU harness and flags it OVER-DECLARED, and a
    CPU-busy sibling keeps a dead GPU grant alive. Both are what the live keeper did; the new assertions fail here."""
    monkeypatch.setattr(rf, "GPU_IDLE_BY_GPU_SIGNALS", False)
    acts, state = _run(_gpu_grant(), [(90.0, {4242}, 100.0)] + [(0.0, {4242}, 100.0)] * 4)
    assert {a[0] for a in acts} >= {"release-cores", "over-declared"}, "old path did not misjudge: fixture is vacuous"
    assert rf.measured_summary(state["ak-asm-t1-harness"]) is not None
    acts, _ = _run(_gpu_grant(), [(90.0, set(), 0.0)] * 10)
    assert not [a for a in acts if a[0] in ("idle-warn", "idle-end")], "old path should keep a CPU-hot GPU grant alive"


def test_p4_3_shared_gpu_grant_without_cores_is_judged_by_kfd_too(tmp_path):
    """kvu16g3-retune: gpu shared, cpus 0 (host threads only): 'OVER-DECLARED busy_fraction: declared 1, measured 0.075' was a
    CPU reading. A shared grant with own KFD pids is busy; with none for 300 s the owner is warned - from KFD, not CPU."""
    g = rf.Grant("kvu16g3-retune-r3", frozenset(), "shared", False, 60, 1, T0, T0 + 7200, 3600)
    acts, _ = _run(g, [(0.0, {77}, 90.0)] * 6)
    assert not acts
    acts, _ = _run(g, [(0.0, set(), 0.0)] * 6)
    assert [a[0] for a in acts if a[0].startswith("idle")] == ["idle-warn"]
    assert not [a for a in acts if a[0] == "release-gpu"], "shared grants never release the token early"


# ================================================================ fix 4: GPU grant ordering (INF-22 2026-11-06 01:59Z / 02:34:30Z)
RANKED = [("ak-asm-h14h15-gate", 10), ("ak-asm-h1b-gate", 11), ("ak-asm-h1h7-gate-r7", 12)]
LATE = ("ak-asm-h11h13-gate-r3", 20)   # arrives mid-wait; its id sorts FIRST alphabetically, as live


def _incident_02_34z(tmp_path, check=True):
    """Device not quiet for one sample (a foreign KFD client: the GPU-SMOKE-BATCH), the rank-20 row becomes grantable between
    the samples, the device reaches IDLE_SAMPLES quiet samples -> which exclusive row is granted?"""
    sim = Sim(tmp_path)
    for rid, rank in RANKED:
        assert sim.publish(spec(rid, cpus=0, threads=8, gpu="exclusive", rank=rank, est=3600)) == []
        sim.write_pass(rid)
    step = sim.step if check else _step_nocheck(sim)
    sim.foreign = frozenset({2808208})      # sample 1: foreign client on the device
    step()
    p1 = sim.plans[-1][2]
    assert not p1.grants and all("device not quiet" in p1.skipped[r] for r, _ in RANKED), p1.skipped
    sim.foreign = frozenset()
    assert sim.publish(spec(LATE[0], cpus=0, threads=8, gpu="exclusive", rank=LATE[1], est=3600)) == []
    sim.write_pass(LATE[0])               # the newcomer's smoke passed between the samples
    step()
    p2 = sim.plans[-1][2]
    assert not p2.grants and all(f"device quiet 1/{rf.IDLE_SAMPLES} samples" in p2.skipped[r] for r in [LATE[0]] + [r for r, _ in RANKED]), p2.skipped
    step()
    p3 = sim.plans[-1][2]
    return sim, [g.id for g in p3.grants], p3


def _step_nocheck(sim):
    def step():
        sim._filler()
        w0 = rf.load_world(sim.flags, sim.now)
        plan, sim.state = rf.tick(sim.flags, sim.now, sim.measurement(), sim.state, sim.log, sim.Runner(sim))
        sim.plans.append((sim.now, w0, plan))
        sim.now += TICK_S
    return step


def test_p4_4_incident_once_quiet_the_best_ranked_exclusive_row_is_granted(tmp_path):
    """02:34:30Z: rank 10-12 rows WAITed 'device quiet 1/2 samples'; the rank-20 row that became grantable mid-wait was granted.
    rowflow2: the quiet counter is per DEVICE (gpu_quiet_step), gated rows take no hold, and admit() re-ranks every grantable
    row at grant time -> the rank-10 row gets the device; the newcomer is neither favoured nor skipped: it is ranked."""
    sim, granted, p3 = _incident_02_34z(tmp_path)
    assert granted == ["ak-asm-h14h15-gate"], (granted, p3.skipped)
    assert "gpu busy" in p3.skipped[LATE[0]], "the newcomer waits behind the granted row, by rank"
    assert isinstance(sim.state.get("gpu_quiet_n"), int) and sim.state["gpu_quiet_n"] >= rf.IDLE_SAMPLES
    # the converse: a newcomer that IS the best-ranked is granted first, not skipped for arriving late
    sim2 = Sim(tmp_path / "b")
    for rid, rank in RANKED:
        assert sim2.publish(spec(rid, cpus=0, threads=8, gpu="exclusive", rank=rank, est=3600)) == []
        sim2.write_pass(rid)
    sim2.foreign = frozenset({1}); sim2.step()
    sim2.foreign = frozenset()
    assert sim2.publish(spec("zz-urgent-gate", cpus=0, threads=8, gpu="exclusive", rank=1, est=3600)) == []
    sim2.write_pass("zz-urgent-gate")
    sim2.step(); sim2.step()
    assert [g.id for g in sim2.plans[-1][2].grants] == ["zz-urgent-gate"]


def test_p4_4_device_quiet_gate_never_blocks_shared_or_cpu_rows():
    """Like the frozen keeper's held_back: only gpu-EXCLUSIVE rows wait for a quiet device; shared GPU rows and CPU rows
    are admitted meanwhile, and the gated rows hold nothing back."""
    pend = [spec("x", cpus=0, threads=8, gpu="exclusive", rank=1), spec("s", cpus=0, threads=8, gpu="shared", rank=5),
            spec("c", cpus="q1", threads=12, rank=9)]
    plan = rf.admit(pend, [], T0, gpu_quiet=False, quiet_n=1)
    assert {g.id for g in plan.grants} == {"s", "c"} and plan.hold is None and "quiet device" in plan.skipped["x"]
    n, q = rf.gpu_quiet_step(0, frozenset({1}))
    assert (n, q) == (0, False)
    n, q = rf.gpu_quiet_step(n, frozenset()); n2, q2 = rf.gpu_quiet_step(n, frozenset())
    assert (n, q, n2, q2) == (1, False, 2, True)


def test_p4_4_negative_control_first_grantable_in_id_order_grants_the_rank_20_row(tmp_path, monkeypatch):
    """Switch rank-at-grant-time off (first grantable row in id order once the device is quiet): the live outcome - the
    rank-20 newcomer `ak-asm-h11h13…` sorts first and takes the device. The fixture's assertion fails here."""
    monkeypatch.setattr(rf, "RANK_AT_GRANT_TIME", False)
    sim, granted, p3 = _incident_02_34z(tmp_path, check=False)
    assert granted == [LATE[0]], granted
    with pytest.raises(AssertionError):
        check_plan(sim.plans[-1][1].pending, p3.basis, p3, sim.now)   # the two-sided oracle catches the priority inversion
