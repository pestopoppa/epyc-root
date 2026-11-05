"""Two-sided (spec, grant) property invariants over hypothesis-generated 12-field specs (P3.6.1/P3.6.2)."""
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from rf2 import T0, check_plan, rf, spec

CONCRETE = ["q0", "q1", "q2", "q3", "48-71", "72-73", "0-3", "80-83", "88-95", "0-95", "0-47", "24-47,72-95", "72-72"]


@st.composite
def specs(draw, rid):
    kind = draw(st.sampled_from(["concrete", "class", "int", "gpu-only", "quiet"]))
    if kind == "concrete":
        cpus = draw(st.sampled_from(CONCRETE))
    elif kind == "class":
        cpus = draw(st.sampled_from(["any-quarter", "any-quarter-of-q1,q2", "any-2-of-q3", "any-4-of-q1", "any-8-of-q0,q1"]))
    elif kind == "int":
        cpus = draw(st.integers(1, 30))
    else:
        cpus = "0-95" if kind == "quiet" else 0
    need = rf.parse_cpus(cpus)
    n = need.min_width()
    gpu = "none" if kind == "quiet" else draw(st.sampled_from(["none", "none", "shared", "exclusive"]))
    if n == 0 and gpu == "none" and kind != "quiet":
        gpu = "shared"
    lo = 12 if n >= 24 else 1
    threads = draw(st.integers(lo, max(lo, n + (8 if gpu != "none" else 0))))
    if draw(st.booleans()) and n < 24:
        threads = 1                                   # explicit regions + 1 thread
    rank = draw(st.integers(1, 9)) if kind == "quiet" else draw(st.integers(1, 120))
    s = spec(rid, cpus=cpus, threads=threads, gpu=gpu, quiet=kind == "quiet",
             rank=rank, est=draw(st.integers(60, 7200)), minwin=draw(st.integers(0, 3600)),
             ram=draw(st.sampled_from([0, 4, 32, 128, 400])),
             published_at=rf.iso(T0 - draw(st.integers(0, 86400))))
    assert rf.validate(s, launcher_exists=lambda p: True) == [], (s, rf.validate(s, launcher_exists=lambda p: True))
    return s


@st.composite
def worlds(draw):
    n_old = draw(st.integers(0, 8))
    old = [draw(specs(f"old{i}")) for i in range(n_old)]
    seed_plan = rf.admit(old, [], T0 - 600)              # realistic open grants: whatever fit earlier
    ends = {g.id: T0 + draw(st.integers(-100, 20000)) for g in seed_plan.grants}
    grants = [rf.Grant(g.id, g.cores, g.gpu, g.quiet, g.ram_gib, g.disk_gib, g.start, max(T0 + 1, ends[g.id]),
                       g.estimate_s) for g in seed_plan.grants]
    pending = [draw(specs(f"row{i}")) for i in range(draw(st.integers(1, 8)))]   # 8 rows per tick
    if draw(st.booleans()) and pending:
        pending.append(dict(pending[0]))                 # the same id published twice (double-grant bait)
    return grants, pending


@settings(max_examples=400, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(worlds())
def test_admit_two_sided_invariants(w):
    grants, pending = w
    plan = rf.admit(pending, grants, T0)
    check_plan(pending, grants, plan, T0)
    # the hold never lets a worse-ranked row hold over a better one: the holder is the best-ranked non-fitting row
    if plan.hold:
        order = [s["id"] for s in rf._order(pending)]
        first_skip = next(i for i in order if i in plan.skipped)
        assert plan.hold.id == first_skip
        # backfill onto held tokens only within the hold's ETA
        for g in plan.grants:
            if order.index(g.id) < order.index(plan.hold.id):
                continue                                  # admitted before the hold existed (better-ranked)
            if g.cores & plan.hold.cores or (plan.hold.gpu and g.gpu != "none"):
                assert g.end <= plan.hold.eta, f"{g.id} backfilled past the hold of {plan.hold.id}"


@settings(max_examples=200, deadline=None)
@given(st.lists(st.tuples(st.sampled_from(range(96)), st.floats(0, 100)), max_size=96),
       st.lists(st.booleans(), min_size=3, max_size=3), st.integers(0, 3))
def test_reconcile_never_releases_quiet_or_unworked_and_needs_two_samples(trace, kfd, which):
    cores = frozenset(rf.QUARTERS[which])
    gs = [rf.Grant("a", cores, "exclusive", False, 0, 0, T0, T0 + 3600, 1800),
          rf.Grant("q", frozenset(), "none", True, 0, 0, T0, T0 + 3600, 1800)]
    busy = {c: 0.0 for c in range(96)}
    busy.update({c: p for c, p in trace})
    state, released = {}, []
    for i, k in enumerate(kfd):
        acts, state = rf.reconcile(gs, rf.Measurement(core_busy=busy, own_kfd={"a": {1} if k else set()}), state, T0 + 120 * i)
        released += acts
        assert all(a[1] != "q" or a[0] == "overrun" for a in acts), "a quiet grant released something"
        if i == 0:
            assert not [a for a in acts if a[0] in ("release-cores", "release-gpu")], "released after one sample"
    worked = any(busy[c] >= rf.IDLE_PCT for c in cores)
    rel = set().union(*[a[2] for a in released if a[0] == "release-cores"]) if released else set()
    assert worked or not rel, "released the cores of a grant that never showed work (spin-up)"
    assert all(busy[c] < rf.IDLE_PCT for c in rel)


# ---------------------------------------------------------------- plain backfilling (operator 2026-11-05)
def _held_world(low_est):
    """q0-q2 busy for 2 days; b3 holds 8 of q3 until +600s; top needs a whole quarter (earliest start T0+600)."""
    gs = [rf.Grant(f"b{i}", rf.QUARTERS[i], "none", False, 8, 1, T0 - 60, T0 + 2 * 86400, 3600) for i in range(3)]
    gs.append(rf.Grant("b3", frozenset(range(72, 80)), "none", False, 8, 1, T0 - 60, T0 + 600, 300))
    top = spec("top", cpus="any-quarter", threads=24, rank=1)
    low = spec("low", cpus="any-8-of-q3", threads=8, rank=90, est=low_est)
    return gs, [top, low]


def _fit_check_ok(low_est):
    gs, pending = _held_world(low_est)
    plan = rf.admit(pending, gs, T0)
    return gs, pending, plan


@settings(max_examples=200, deadline=None)
@given(st.floats(10, 20000))
def test_backfill_granted_iff_it_ends_by_top_rows_start(est):
    gs, pending, plan = _fit_check_ok(est)
    assert plan.hold and plan.hold.id == "top"
    low = pending[1]
    fits = T0 + rf.window_s(low) <= plan.hold.eta
    granted = {g.id for g in plan.grants}
    assert ("low" in granted) == fits           # fitting backfill granted, non-fitting refused
    if not fits:
        assert "held-for" in plan.skipped["low"]
    check_plan(pending, gs, plan, T0)


@settings(max_examples=200, deadline=None)
@given(st.floats(10, 20000))
def test_backfill_never_delays_top_rows_start(est):
    gs, pending, plan = _fit_check_ok(est)
    eta = plan.hold.eta
    # simulate: whatever was granted ends (by window) no later than the hold's ETA on held cores
    for g in plan.grants:
        if g.cores & plan.hold.cores:
            assert g.end <= eta
    # and the top row's computed start with the backfill present equals the start without it
    without = rf.admit([pending[0]], gs, T0)
    again = rf.admit(pending, gs + plan.grants, T0 + 1)
    assert again.hold is None or again.hold.eta <= max(eta, without.hold.eta) + 1


def test_backfill_negative_control_fails_without_fit_check(monkeypatch):
    """Remove the fit check (every backfill allowed) and the non-fitting row is wrongly granted: the property bites."""
    gs, pending = _held_world(20000)
    assert "low" not in {g.id for g in rf.admit(pending, gs, T0).grants}
    real = rf.window_s
    monkeypatch.setattr(rf, "window_s", lambda s: 1.0 if s["id"] == "low" else real(s))   # fit check always passes
    plan = rf.admit(pending, gs, T0)
    assert "low" in {g.id for g in plan.grants}
    assert T0 + real(pending[1]) > plan.hold.eta       # ... though it really would delay top: the property would fail
