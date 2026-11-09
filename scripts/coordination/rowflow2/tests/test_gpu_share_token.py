"""ROWFLOW2-GPU-SHARE-TOKEN (operator 2026-11-05): correctness rows share the GPU, a timing row holds it exclusively and
refuses any co-tenant (both directions, same-tick and cross-tick, and for the legacy-manifest mapping). Negative control included."""
from rf2 import T0, rf, spec
from test_multiquarter_mirror import legacy


def _held(rid, gpu, cores=frozenset()):
    return rf.Grant(rid, cores, gpu, False, 8, 1, T0, T0 + 3600, 1800)


# ---------------------------------------------------------------- GPU share / exclusive token
def test_two_correctness_rows_are_co_resident_on_the_gpu():
    a = spec("c6-gpu-suite-a", cpus=0, threads=8, gpu="shared", rank=50)
    b = spec("c6-gpu-suite-b", cpus=0, threads=8, gpu="shared", rank=60)
    plan = rf.admit([a, b], [], T0)
    assert [g.id for g in plan.grants] == ["c6-gpu-suite-a", "c6-gpu-suite-b"], plan.skipped
    assert all(g.gpu == "shared" for g in plan.grants)
    # across ticks too: a third shared row joins two shared holders
    plan = rf.admit([spec("c6-gpu-suite-c", cpus=0, threads=8, gpu="shared")], plan.grants, T0)
    assert [g.gpu for g in plan.grants] == ["shared"], plan.skipped


def test_timing_row_refuses_any_co_tenant_and_is_refused_by_one():
    timing = spec("q38p4b-int8-20261105", cpus=0, threads=8, gpu="exclusive", rank=50, timing=True)
    shared = spec("c6-gpu-suite-a", cpus=0, threads=8, gpu="shared", rank=60)
    # a shared holder is open: the timing row is refused
    plan = rf.admit([timing], [_held("c6-gpu-suite-a", "shared")], T0)
    assert not plan.grants and plan.skipped["q38p4b-int8-20261105"] == "gpu busy"
    # the timing row is open: a correctness row is refused (it must not perturb the timing run)
    plan = rf.admit([shared], [_held("q38p4b-int8-20261105", "exclusive", frozenset(range(88, 96)))], T0)
    assert not plan.grants and plan.skipped["c6-gpu-suite-a"] == "gpu held exclusive"
    # two timing rows never co-run
    plan = rf.admit([timing], [_held("akx-lb3-2-cv5-pair-r2", "exclusive", frozenset(range(88, 96)))], T0)
    assert not plan.grants
    # same tick: whichever ranks first takes the device, the other is refused
    plan = rf.admit([timing, shared], [], T0)
    assert [g.id for g in plan.grants] == ["q38p4b-int8-20261105"] and "gpu" in plan.skipped["c6-gpu-suite-a"]
    plan = rf.admit([dict(shared, priority_rank=10), timing], [], T0)
    assert [g.id for g in plan.grants] == ["c6-gpu-suite-a"] and plan.skipped["q38p4b-int8-20261105"] == "gpu busy"


def test_legacy_manifests_map_timing_to_exclusive_and_correctness_to_shared_unknown_to_exclusive():
    for cls, want in (("block-timing-quiet", "exclusive"), ("block-timing-pairable", "exclusive"),
                      ("correctness", "shared"), ("block-correctness", "shared"), ("diagnostic", "shared"),
                      (None, "exclusive")):   # undeclared purpose: conservative, never shared
        s, why = rf.map_legacy(legacy("gpu-row", regions="mi210_0,184-191", shape="gpu", declared_shape="gpu",
                                      admission_class=cls))
        assert why is None and s["gpu"] == want, (cls, s and s["gpu"], why)


def test_negative_control_a_shared_timing_row_would_be_co_admitted():
    """If a timing row were declared shared the same admit() would co-admit it: the exclusivity comes from the token, not luck."""
    mislabelled = spec("q38p4b-int8-20261105", cpus=0, threads=8, gpu="shared", rank=50)
    assert rf.admit([mislabelled], [_held("c6-gpu-suite-a", "shared")], T0).grants


