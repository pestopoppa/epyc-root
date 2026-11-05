"""Named incident fixtures from 2026-11-05 (keeper-friction-review Pass 3, P3.2) - one test each."""
import glob
import os

from rf2 import T0, Sim, check_plan, rf, spec

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
    sim.publish(spec("stt5-r5", cpus="q3", threads=24, rank=20), launcher_text=hip)
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
