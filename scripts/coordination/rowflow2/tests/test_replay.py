"""Whole-tick replay (P3.6.3): reconcile -> admit -> smoke lane -> file, plus publish and a fake filler, over a temp
flags dir. The idle budget is GATED here (asserted, not printed)."""
import glob
import os

import pytest

from hypothesis import given, settings
from hypothesis import strategies as st

from rf2 import TICK_S, Sim, rf, spec

IDLE_BUDGET_QH, IDLE_BUDGET_GPUH = 0.5, 0.25   # per replayed day (P3.6.1 v)


def realistic_day(sim, rng, n_rows=48):
    """A day shaped like the live 2026-11-05 census: mostly quarter rows, host rows, gpu rows (shared/exclusive),
    sub-quarter pinned pairs, gpu-q3, an occasional sanctioned quiet row. Arrivals spread over the day."""
    plan = []
    for i in range(n_rows):
        t = rng.uniform(0, 20 * 3600)
        k = rng.random()
        if k < 0.42:
            s = dict(cpus="any-quarter", threads=20, est=rng.randint(900, 5400))
        elif k < 0.52:
            s = dict(cpus="0-95", threads=48, est=rng.randint(1200, 3600))
        elif k < 0.70:
            s = dict(cpus=0, threads=8, gpu=rng.choice(["shared", "exclusive"]), est=rng.randint(600, 3600))
        elif k < 0.84:
            a = rng.choice(range(72, 96, 2))
            s = dict(cpus=f"{a}-{a + 1}", threads=1, est=rng.randint(600, 2400))
        elif k < 0.92:
            s = dict(cpus=rng.choice(["q1", "q2", "48-71"]), threads=24, est=rng.randint(900, 3600))
        elif k < 0.97:
            s = dict(cpus="88-95", threads=8, gpu="exclusive", est=rng.randint(600, 1800))
        else:
            s = dict(cpus="0-95", threads=48, quiet=True, est=rng.randint(600, 1800), rank=5)
        s.setdefault("rank", rng.randint(10, 100))
        plan.append((t, f"d{i:02d}", s, rng.random() < 0.3))
    return sorted(plan)


def run_day(tmp_path, seed, n_rows=48, ticks=720):
    import random
    rng = random.Random(seed)
    sim = Sim(tmp_path, seed)
    arrivals = realistic_day(sim, rng, n_rows)
    for _ in range(ticks):
        while arrivals and arrivals[0][0] <= sim.now - rf.parse_iso("2026-11-05T00:00:00Z"):
            _, rid, kw, overdecl = arrivals.pop(0)
            text = "#!/bin/bash\ncmake -B build-hip -DGGML_HIP=ON\n" if rng.random() < 0.2 else "#!/bin/bash\nexec true\n"
            errs = sim.publish(spec(rid, minwin=300, ram=rng.choice([8, 32, 64]), **kw), launcher_text=text,
                               use=0.1 if overdecl else 1.0, gpu_use=rng.random() < 0.8)
            assert errs == [], errs
        sim.step()
    return sim


def test_whole_day_replay_invariants_and_idle_budget(tmp_path):
    sim = run_day(tmp_path, seed=20261105)
    F, G = os.path.join(sim.flags, "filing-done"), os.path.join(sim.flags, "grants")
    granted = [p for _, _, p in sim.plans for _ in p.grants]
    assert len(granted) >= 40, f"replay too thin to gate anything: {len(granted)} grants"
    # (vi) every .ended carries a reason from the closed set; every COMPLETE came from a grant, never from a smoke
    reasons = sim.ended_reasons()
    assert reasons and set(reasons.values()) <= set(rf.ENDED_REASONS), set(reasons.values())
    for cp in glob.glob(os.path.join(G, "*.complete")):
        rid = os.path.basename(cp)[:-9]
        assert rid in sim.granted_ever and os.path.exists(os.path.join(G, rid + ".grant"))
    assert sim.smoked_ever, "the smoke lane never ran"
    # file(): every machine-rule .ended was filed by the keeper tick itself
    for rid in reasons:
        assert os.path.exists(os.path.join(F, rid + ".FILED")), f"{rid} ended but not filed"
    # (v) idle token-hours are GATED (waste: free tokens a pending row could take now); the hold price is reported
    print(f"idle waste {sim.idle_q:.2f} q-h {sim.idle_gpu:.2f} gpu-h; hold price {sim.hold_q:.2f} q-h {sim.hold_gpu:.2f} gpu-h")
    assert sim.idle_q <= IDLE_BUDGET_QH, f"idle {sim.idle_q:.2f} quarter-h > {IDLE_BUDGET_QH}: {sim.idle_parts['q'][:20]}"
    assert sim.idle_gpu <= IDLE_BUDGET_GPUH, f"idle {sim.idle_gpu:.2f} gpu-h > {IDLE_BUDGET_GPUH}: {sim.idle_parts['gpu'][:20]}"
    # gpu:none rows with `build-hip` in their launcher text never held the gpu token
    for rid, s in sim.specs.items():
        if s["gpu"] == "none" and not s["quiet"] and os.path.exists(os.path.join(G, rid + ".grant")):
            assert " gpu=none " in open(os.path.join(G, rid + ".grant")).read()
    # measured feedback reached the .ended of over-declared rows
    od = [line for line in sim.lines if " OVER-DECLARED " in line]
    assert od, "no over-declared row was detected by measurement"


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_idle_budget_holds_across_seeds(tmp_path, seed):
    sim = run_day(tmp_path, seed)
    assert sim.idle_q <= IDLE_BUDGET_QH and sim.idle_gpu <= IDLE_BUDGET_GPUH, (sim.idle_q, sim.idle_gpu)


def test_idle_gate_is_not_vacuous(tmp_path, monkeypatch):
    """Negative control: an allocator that 'reserves' q3 (the 11-05 reservation class) or hands CPU rows the gpu must
    blow the same budget."""
    real = rf.admit

    def reserving(pending, grants, now, **kw):
        plan = real(pending, grants, now, **kw)
        plan.grants = [g for g in plan.grants if not g.cores & rf.QUARTERS[3] and g.gpu == "none"]
        return plan
    monkeypatch.setattr(rf, "admit", reserving)
    monkeypatch.setattr(rf, "HOLD_BUDGET_QH", float("inf"))   # dropped grants are invisible to the oracle; keep holds binding
    sim = run_day(tmp_path, 20261105)
    assert sim.idle_q > IDLE_BUDGET_QH and sim.idle_gpu > IDLE_BUDGET_GPUH, (sim.idle_q, sim.idle_gpu)


@settings(max_examples=12, deadline=None)
@given(st.integers(0, 10 ** 6), st.lists(st.tuples(st.sampled_from(["any-quarter", "q1", "72-73", 0, "0-95", 6]),
                                                  st.sampled_from(["none", "shared", "exclusive"]),
                                                  st.integers(1, 100), st.floats(0.05, 1.0)), min_size=8, max_size=8))
def test_short_replays_eight_rows_per_tick(tmp_path_factory, seed, rows):
    sim = Sim(tmp_path_factory.mktemp("r"), seed)
    for tick in range(3):
        for j, (cpus, gpu, rank, use) in enumerate(rows):
            need = rf.parse_cpus(cpus)
            g = "shared" if need.min_width() == 0 and gpu == "none" else gpu
            th = 12 if need.min_width() >= 24 else 1
            sim.publish(spec(f"t{tick}r{j}", cpus=cpus, threads=th, gpu=g, rank=rank, est=600, minwin=120), use=use)
        for _ in range(4):
            sim.step()          # check_plan runs inside every step
    for _ in range(30):
        sim.step()
    assert set(sim.ended_reasons().values()) <= set(rf.ENDED_REASONS)


def test_smoke_deadline_kills_and_fails_never_completes(tmp_path):
    sim = Sim(tmp_path)
    sim.publish(spec("hang", cpus="q1", threads=12), smoke_outcome="hang")
    for _ in range(rf.SMOKE_DEADLINE_S // TICK_S + 3):
        sim.step()
    assert any("SMOKE-DEADLINE hang" in x for x in sim.lines)
    assert os.path.exists(os.path.join(sim.flags, "dryrun", "hang", "FAIL-deadline.json"))
    assert rf.load_world(sim.flags, sim.now).state["hang"] == "failed"
    assert not glob.glob(os.path.join(sim.flags, "grants", "hang.*"))


def test_reconcile_releases_idle_cores_and_unused_gpu_then_regrants(tmp_path):
    sim = Sim(tmp_path)
    sim.publish(spec("fat", cpus="q1", threads=12, est=7000), use=0.05)
    sim.publish(spec("gpux", cpus=0, threads=8, gpu="exclusive", est=7000), gpu_use=False)
    for _ in range(8):
        sim.step()
    assert any("RELEASE fat cores=" in x for x in sim.lines)
    assert any("RELEASE gpux gpu" in x for x in sim.lines)
    sim.publish(spec("next", cpus="any-4-of-q1", threads=4, gpu="exclusive", est=7000))
    for _ in range(6):
        sim.step()
    assert os.path.exists(os.path.join(sim.flags, "grants", "next.grant")), sim.lines[-10:]


def test_supersede_withdraws_and_lineage_counts_since_fix_ref(tmp_path):
    sim = Sim(tmp_path)
    sim.publish(spec("a-r1", cpus="q2", threads=12))
    sim.publish(spec("a-r2", cpus="q2", threads=12, supersedes="a-r1"))
    e = rf.ended_fields(rf.head1(os.path.join(sim.flags, "grants", "a-r1.ended")))
    assert e["base"] == "superseded" and os.path.exists(os.path.join(sim.root, "stops", "a-r1.STOP"))
    specs = {"x1": {}, "x2": {"supersedes": "x1"}, "x3": {"supersedes": "x2", "fix_ref": "abc123"}, "x4": {"supersedes": "x3"}}
    fails = {"x1": 2, "x2": 1, "x3": 0, "x4": 1}
    assert rf.lineage_fails("x4", specs, fails) == 1          # x4 + x3 (fix_ref) only
    assert rf.lineage_fails("x2", specs, fails) == 3


def test_measured_feedback_refuses_overdeclared_successor(tmp_path):
    sim = Sim(tmp_path)
    sim.publish(spec("od-r1", cpus="q2", threads=12, est=1200), use=0.04)
    for _ in range(20):
        sim.step()
    assert "measured busy_p95=" in open(os.path.join(sim.flags, "grants", "od-r1.ended")).read()
    errs = sim.publish(spec("od-r2", cpus="q2", threads=12, supersedes="od-r1"))
    assert errs and "measured" in errs[0]
    assert sim.publish(spec("od-r2", cpus="q2", threads=12, supersedes="od-r1", measured_ack="op: bandwidth-bound")) == []


def test_filing_routes_prose_rules_by_claim_and_ownerless_timeout():
    e = {"rc": 0, "reason": "complete", "base": "complete", "time": 1000.0, "busy_p95": None, "cpus": None}
    specs = {"m": {"decision_rule": "rc == 0"}, "p": {"decision_rule": "prose", "owner": "mainA"},
             "c": {"decision_rule": "prose", "owner": "mainA"}, "s": {"decision_rule": "prose", "owner": "mainA"}}
    ended = {k: (e, 1000.0) for k in specs}
    acts = {a[1]: a for a in rf.file_decisions(ended, specs, {"c": 1000.0, "s": 0.0}, 1000.0 + 600)}
    assert acts["m"][:3] == ("file", "m", "pass") and acts["p"][0] == "route-owner" and acts["c"][0] == "wait-claim"
    acts = {a[1]: a for a in rf.file_decisions(ended, specs, {"s": 0.0}, 1000.0 + rf.CLAIM_TTL_S + 1)}
    assert acts["p"][0] == "owner-less" and acts["s"][0] == "reopen"
