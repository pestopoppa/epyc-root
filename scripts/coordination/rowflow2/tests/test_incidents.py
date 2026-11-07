"""Named incident fixtures from 2026-11-05 (keeper-friction-review Pass 3, P3.2) - one test each."""
import glob
import os

from rf2 import T0, TICK_S, Sim, check_plan, rf, spec

yes = lambda p: True  # noqa: E731


def test_1_four_core_shrink_q2_gets_all_of_q2(tmp_path):
    """iqk-q8-prefill-ab-r3: regions q2, a 4-core smoke measured 2.2 threads -> GRANT 80-83. Now: the grant is the
    declaration; the smoke's measured_threads is never read; a q2 row with small threads is REFUSED at publish
    (over-declared), never silently shrunk."""
    sim = Sim(tmp_path)
    assert sim.publish(spec("iqk-q8-prefill-ab-r3", cpus="q2", threads=12)) == []
    for _ in range(4):
        sim.step()          # the smoke harness writes PASS.json with measured_threads=2.2
    g = rf.parse_grant("iqk-q8-prefill-ab-r3", rf.head1(os.path.join(sim.flags, "grants", "iqk-q8-prefill-ab-r3.grant")))
    assert g.cores == frozenset(range(48, 72))
    errs = rf.validate(spec("small", cpus="q2", threads=2), launcher_exists=yes)
    assert any("over-declared" in e for e in errs)
    assert rf.validate(spec("small", cpus="any-2-of-q2", threads=2), launcher_exists=yes) == []


def test_2_gpu_none_row_with_build_hip_text_gets_no_gpu_token(tmp_path):
    """STT5 r5 / iqk-q8-prefill-build held gpu-quiet because `build-hip` appeared in job text. Text is never read."""
    sim = Sim(tmp_path)
    hip = "#!/bin/bash\ncmake -B build-hip -DGGML_HIP=ON && hipcc x.cpp && llama-bench --device ROCm0 -ngl 99\n"
    # q2, not q3: since gpu-q3 NARROW (decision 8) a gpu-exclusive row holds 88-95, so a whole-q3 CPU row and a GPU
    # timing row conflict by design (test_8); this test is about job text never granting a gpu token
    sim.publish(spec("stt5-r5", cpus="q2", threads=24, rank=20), launcher_text=hip)
    sim.publish(spec("gpu-timing", cpus=0, threads=8, gpu="exclusive", rank=40))
    for _ in range(6):
        sim.step()
    G = os.path.join(sim.flags, "grants")
    a = rf.parse_grant("stt5-r5", rf.head1(os.path.join(G, "stt5-r5.grant")))
    b = rf.parse_grant("gpu-timing", rf.head1(os.path.join(G, "gpu-timing.grant")))
    assert a.gpu == "none" and "mi210" not in rf.head1(os.path.join(G, "stt5-r5.grant"))
    assert b.gpu == "exclusive" and max(a.start, b.start) < min(a.end, b.end), "the gpu row waited behind a CPU row"


def test_3_rank100_quiet_cannot_drain_over_better_ranked_gpu_rows():
    """c6-port35186-remeasure (rank 100, quiet-host) drained the host over rank-40 GPU rows."""
    q = spec("remeasure", cpus="0-95", threads=48, quiet=True, rank=100)
    assert any("quiet needs priority_rank" in e for e in rf.validate(q, launcher_exists=yes))
    # even with an operator quiet_reason it is strict priority: better-ranked GPU rows are admitted first and the
    # quiet row's hold binds only rows ranked below it
    q = dict(q, quiet_reason="operator: remeasure on a quiet host")
    gpus = [spec(f"gpu{i}", cpus=0, threads=8, gpu="shared", rank=40) for i in range(3)]
    cpu = [spec("cpu-q1", cpus="q1", threads=12, rank=30, est=36000)]
    plan = rf.admit([q] + gpus + cpu, [], T0)
    check_plan([q] + gpus + cpu, [], plan, T0)
    got = {g.id for g in plan.grants}
    assert {"gpu0", "gpu1", "gpu2", "cpu-q1"} <= got and "remeasure" not in got
    assert plan.hold.id == "remeasure"
    # next tick: a NEW better-ranked GPU row arrives while the quiet row holds -> it is still granted
    plan2 = rf.admit([q, spec("gpu-new", cpus=0, threads=8, gpu="shared", rank=40, est=36000)], plan.grants, T0 + 120)
    assert "gpu-new" in {g.id for g in plan2.grants}


def test_4_gpu_blocked_whole_quarter_rows_never_starve_the_smoke_lane(tmp_path):
    """117 SMOKE-WAITs: whole-quarter GPU rows reserved quarters; smokes had no 4 free cores. The smoke lane is fixed."""
    sim = Sim(tmp_path)
    sim.publish(spec("gpu-hog", cpus="q3", threads=24, gpu="exclusive", rank=1, est=7000))
    for _ in range(3):
        sim.step()
    for i in range(3):   # GPU-blocked whole-quarter rows, already smoke-passed
        sim.publish(spec(f"blocked{i}", cpus=f"q{i}", threads=20, gpu="exclusive", rank=2))
        sim.write_pass(f"blocked{i}")
    for i in range(3):
        sim.publish(spec(f"needs-smoke{i}", cpus="q1", threads=12, rank=90))
    for _ in range(12):
        sim.step()
    started = [x for x in sim.lines if "SMOKE-START" in x]
    assert len(started) >= 3 and all(f"cores={rf.cpulist(rf.SMOKE_CORES)}" in x for x in started)
    for gp in glob.glob(os.path.join(sim.flags, "grants", "*.grant")):
        assert not rf.parse_grant("x", rf.head1(gp)).cores & rf.SMOKE_CORES


def test_5_smoke_that_writes_outputs_never_produces_complete(tmp_path):
    """c6-features-cpu: the smoke ran the real job, the job wrote its summary, --complete-cmd saw it -> COMPLETE."""
    sim = Sim(tmp_path)
    sim.publish(spec("c6-features-cpu", cpus="q2", threads=12, est=1200), smoke_outcome="pass")
    for _ in range(3):
        sim.step()   # smoke runs, writes results/c6-features-cpu/smoke/RESULT.json, PASS
    assert os.path.exists(os.path.join(sim.root, "results", "c6-features-cpu", "smoke", "RESULT.json"))
    G = os.path.join(sim.flags, "grants")
    assert "c6-features-cpu" in sim.smoked_ever
    # a stray COMPLETE for a row that never held a grant is rejected, not filed
    open(os.path.join(G, "smoked-only.complete"), "w").write("complete time=x id=smoked-only\n")
    sim.step()
    assert not os.path.exists(os.path.join(G, "smoked-only.complete"))
    assert any("COMPLETE-WITHOUT-GRANT smoked-only" in x for x in sim.lines)
    for cp in glob.glob(os.path.join(G, "*.complete")):
        assert os.path.exists(cp[:-9] + ".grant")


def test_6_double_grant_is_impossible(tmp_path):
    """iqk-q8-prefill-ab-r3: two GRANT lines for one pid in one tick (72-75 and 80-83)."""
    s = spec("iqk-q8-prefill-ab-r3", cpus="any-4-of-q3", threads=4, est=7000)
    plan = rf.admit([s, dict(s), dict(s, cpus="any-4-of-q2")], [], T0)
    assert [g.id for g in plan.grants] == ["iqk-q8-prefill-ab-r3"]
    sim = Sim(tmp_path)
    sim.publish(s)
    for _ in range(6):
        sim.step()
    grants = [x for x in sim.lines if " GRANT iqk-q8-prefill-ab-r3 " in x]
    assert len(grants) == 1, grants
    g = rf.parse_grant("iqk-q8-prefill-ab-r3", rf.head1(os.path.join(sim.flags, "grants", "iqk-q8-prefill-ab-r3.grant")))
    try:
        rf.write_grant(sim.flags, g)
        raise AssertionError("a second grant file for an open grant was written")
    except RuntimeError as e:
        assert "DOUBLE-GRANT" in str(e)


def test_7_q3_timing_grant_must_hold_smt_siblings_184_191():
    """INF22 2026-11-05: iqk-q8-prefill-ab-r6 (CPU timing, whole q3, cores 72-95) did not hold siblings 168-191; GPU
    host threads 184-191 (c6-gpu-27b-identity reloading a 27B server) shared 8 of 24 decode cores; requests 20-70%
    slow. Now: a timing row on 88-95 must declare gpu exclusive; an any-quarter timing row lands on q0-q2."""
    errs = rf.validate(spec("iqk-q8-prefill-ab-r6", cpus="q3", threads=24, timing=True), launcher_exists=yes)
    assert any("88-95" in e for e in errs)
    assert rf.validate(spec("r6", cpus="q3", threads=24, gpu="exclusive", timing=True), launcher_exists=yes) == []
    assert rf.validate(spec("corr", cpus="q3", threads=24), launcher_exists=yes) == []    # correctness unaffected
    gpu_row = rf.Grant("c6-gpu-27b-identity", frozenset(), "shared", False, 60, 1, T0, T0 + 3600, 1800)
    # whole q3 + shared gpu busy: an any-quarter timing row goes to q0-q2, never q3
    busy = [rf.Grant(f"b{i}", rf.QUARTERS[i], "none", False, 8, 1, T0, T0 + 3600, 1800) for i in (0, 1)]
    plan = rf.admit([spec("t", cpus="any-quarter", threads=24, timing=True)], [gpu_row] + busy, T0)
    assert [g.cores for g in plan.grants] == [rf.QUARTERS[2]]
    # with q2 busy too, it waits rather than take q3 beside the gpu host lane
    busy.append(rf.Grant("b2", rf.QUARTERS[2], "none", False, 8, 1, T0, T0 + 3600, 1800))
    plan = rf.admit([spec("t", cpus="any-quarter", threads=24, timing=True)], [gpu_row] + busy, T0)
    assert not plan.grants
    # negative control: the same row without `timing` (correctness) takes q3 alongside the gpu lane
    plan = rf.admit([spec("c", cpus="any-quarter", threads=24)], [gpu_row] + busy, T0)
    assert [g.cores for g in plan.grants] == [rf.QUARTERS[3]]
    # gitnexus-q3 coexist shape (cores 72-87, never 184-191) stays legal for a timing row without the gpu
    assert rf.validate(spec("gx", cpus="72-87", threads=16, timing=True), launcher_exists=yes) == []


def test_8_gpu_timing_grant_holds_88_95_never_the_rest_of_q3():
    """gpu-q3 NARROW (operator 2026-11-05 "Narrow + emergency deploy"): q38p4b-int8-20261105 (GPU timing) was refused
    "needs gpu-quiet,q3,t184..t191: q3 busy" by the frozen keeper while an 8-core AITER build sat on 80-87/176-183. A
    gpu-exclusive (timing) grant holds the gpu + cores 88-95 (the SMT siblings of host threads 184-191) and NEVER q3
    cores 72-87; shared (correctness) GPU rows hold the gpu alone. Same rule as rowflow GPU_Q3_TOKENS."""
    sib = frozenset(range(88, 96))
    build = rf.Grant("rock-aiter-prebuild-r4", frozenset(range(80, 88)), "none", False, 8, 1, T0, T0 + 7200, 3600)
    busy = [rf.Grant(f"b{i}", rf.QUARTERS[i], "none", False, 8, 1, T0, T0 + 3600, 1800) for i in (0, 1, 2)]
    # the live refusal: GPU timing row (cpus 0 = host threads only) beside the 8-core q3 build -> granted, holds gpu + 88-95
    plan = rf.admit([spec("q38p4b-int8", cpus=0, threads=8, gpu="exclusive", rank=50, timing=True)], [build] + busy, T0)
    assert [g.id for g in plan.grants] == ["q38p4b-int8"], plan.skipped
    g = plan.grants[0]
    assert g.gpu == "exclusive" and g.cores == sib, sorted(g.cores)
    assert not (g.cores & frozenset(range(72, 88)))
    # the other way round: the GPU timing grant is open, the 8-core q3 build is granted beside it
    plan = rf.admit([spec("rock-aiter-prebuild-r4", cpus="80-87", threads=8, rank=60)], [g] + busy, T0)
    assert [x.cores for x in plan.grants] == [frozenset(range(80, 88))], plan.skipped
    # ... and a whole-q3 row is NOT (88-95 are held): the GPU timing run keeps its sibling cores quiet
    plan = rf.admit([spec("q3-whole", cpus="q3", threads=24, rank=60)], [g] + busy, T0)
    assert not plan.grants and "cpus busy" in plan.skipped["q3-whole"]
    # negative control (the rule this replaces): had the timing grant booked all of q3 the build could not be placed
    old = rf.Grant("q38p4b-old", rf.QUARTERS[3], "exclusive", False, 8, 1, T0, T0 + 7200, 3600)
    plan = rf.admit([spec("rock-aiter-prebuild-r4", cpus="80-87", threads=8, rank=60)], [old] + busy, T0)
    assert not plan.grants
    # correctness / production GPU rows: gpu shared, no cores at all (unchanged)
    plan = rf.admit([spec("c6-gpu-suite", cpus=0, threads=8, gpu="shared", rank=70)], [build] + busy, T0)
    assert [(x.gpu, x.cores) for x in plan.grants] == [("shared", frozenset())]
    # a timing row that wants a quieter neighbourhood declares it: explicit cpus 72-87 + gpu exclusive = all of q3
    plan = rf.admit([spec("quiet-q3-timing", cpus="72-87", threads=16, gpu="exclusive", rank=50, timing=True)], busy, T0)
    assert [x.cores for x in plan.grants] == [rf.QUARTERS[3]]
    # grant_need is the single rule: option and width needs both gain exactly 88-95
    assert rf.grant_need(spec("a", cpus="q0", threads=24, gpu="exclusive", timing=True)).options == (rf.QUARTERS[0] | sib,)
    w = rf.grant_need(spec("b", cpus=4, threads=4, gpu="exclusive", timing=True))
    assert w.fixed == sib and not (w.pool & sib) and w.width == 4
    assert rf.fits_need(w, frozenset(range(0, 4)) | sib) and not rf.fits_need(w, frozenset(range(0, 4)))
    assert rf.grant_need(spec("c", cpus=4, threads=4, gpu="shared")).fixed == frozenset()


def test_9_rock_aiter_tests_r3_idle_held_gpu_grant_warns_then_ends_rc75_and_requeues(tmp_path):
    """rock-aiter-tests-r3-20261105 (21:20-21:41Z): hung on a stale lock, held gpu-quiet + 88-95 at 0% for ~20 min while 7
    GPU rows queued; the frozen keeper logged IDLE-HELD every tick and told nobody. rowflow2: the owner is warned once at
    300 s of whole-grant idleness, the grant ends rc=75 at 900 s and the row is re-queued (one retry); a second idle end
    is terminal (.ended rc=75 reason=idle-held) and the next GPU row gets the device."""
    sim = Sim(tmp_path)
    assert sim.publish(spec("rock-aiter-tests-r3", cpus=0, threads=8, gpu="exclusive", rank=40, est=7200, timing=True)) == []
    G = os.path.join(sim.flags, "grants")
    gp = os.path.join(G, "rock-aiter-tests-r3.grant")
    for _ in range(10):               # its smoke (20-300 s) then admission
        if os.path.exists(gp):
            break
        sim.step()
    assert os.path.exists(gp), "fixture: r3 never granted"
    # a GPU timing row arrives and queues behind the hung grant (7 did on 2026-11-05)
    assert sim.publish(spec("q38p4b-int8", cpus=0, threads=8, gpu="exclusive", rank=50, est=3600, timing=True)) == []
    for r in sim.runs.values():
        r["end"] = float("inf")       # the hung job never finishes on its own
    hung = lambda: rf.Measurement(core_busy={c: 0.0 for c in range(96)},  # noqa: E731
                                  own_kfd={rid: set() for rid in ("rock-aiter-tests-r3", "q38p4b-int8") if os.path.exists(os.path.join(G, rid + ".grant"))},
                                  alive={})
    sim.measurement = hung
    t_grant = sim.now
    n0 = len(sim.lines)
    while os.path.exists(gp) and sim.now - t_grant < 4000:
        sim.step()
    lines = sim.lines[n0:]
    warns = [l for l in lines if " IDLE-HELD-WARN rock-aiter-tests-r3 " in l]
    ends = [l for l in lines if " IDLE-END rock-aiter-tests-r3 " in l]
    assert len(warns) == 1 and len(ends) == 1, lines
    t_warn = rf.parse_iso(warns[0].split(" ")[0]); t_end = rf.parse_iso(ends[0].split(" ")[0])
    assert rf.IDLE_WARN_S <= t_warn - t_grant < rf.IDLE_HELD_S and t_end - t_grant >= rf.IDLE_HELD_S and t_warn < t_end
    assert "re-queued (attempt 1 of 2)" in ends[0]
    assert os.path.exists(os.path.join(sim.flags, "dryrun", "rock-aiter-tests-r3", "IDLE-HELD-1.json"))
    assert not os.path.exists(os.path.join(G, "rock-aiter-tests-r3.ended")), "a re-queue is not terminal"
    # the same tick's admit() hands the device to the waiting row; the hung row is pending again (not done, not failed)
    assert os.path.exists(os.path.join(G, "q38p4b-int8.grant")), "the waiting GPU row did not get the device"
    assert rf.load_world(sim.flags, sim.now).state["rock-aiter-tests-r3"] == "pending"
    sim.step()                                         # the filler picks the new grant up ...
    sim.runs["q38p4b-int8"]["end"] = sim.now           # ... and it finishes; the re-queued row is re-granted, fresh idle clock
    sim.step()
    assert os.path.exists(gp), "re-queued row not re-granted"
    t_regrant, n1 = sim.now - TICK_S, len(sim.lines)
    while os.path.exists(gp) and sim.now - t_regrant < 4000:
        sim.step()
    lines = sim.lines[n1:]
    ends = [l for l in lines if " IDLE-END rock-aiter-tests-r3 " in l]
    assert len(ends) == 1 and "terminal after 2 idle-held ends" in ends[0], lines
    assert len([l for l in lines if " IDLE-HELD-WARN rock-aiter-tests-r3 " in l]) == 1, "the warning is per grant, once"
    assert rf.parse_iso(ends[0].split(" ")[0]) - t_regrant >= rf.IDLE_HELD_S
    assert rf.head1(os.path.join(G, "rock-aiter-tests-r3.ended")).startswith("rc=75 reason=idle-held")
    assert os.path.exists(os.path.join(sim.flags, "dryrun", "rock-aiter-tests-r3", "IDLE-HELD-2.json"))
    assert rf.load_world(sim.flags, sim.now).state["rock-aiter-tests-r3"] == "done"
