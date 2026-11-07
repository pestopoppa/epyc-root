"""Decision 10 (2026-11-07): keeper-divergence gaps closed before cutover.
1. any-N-quarters CPU options never include q3; 2. only GPU TIMING rows hold 88-95; 3. job sha re-arms a FAILed row."""
import json
import os

from hypothesis import given, settings, strategies as st

from rf2 import T0, rf, spec

Q3 = frozenset(range(72, 96))


def _legacy(rid, **kw):
    m = {"schema": rf.LEGACY_SCHEMA, "id": rid, "launcher": "/bin/sh", "estimate_s": 3600, "min_window_s": 600,
         "decision_rule": "rc == 0", "handoff_task": "handoffs/active/x.md:ROW", "owner": "o", "priority_rank": 50}
    m.update(kw)
    s, why = rf.map_legacy(m)
    assert s, why
    return s


def test_incident_lsa_quality_32k_r5_pca_any_2_quarters_never_takes_q3():
    """lsa-quality-32k-r5-pca (multi-quarter(2), accepted) was granted q1+q3: c7-q38-ppl-bisect-r5 then waited 600 s on
    q3, rc75, MI210 idle ~40 min. With q0 and q2 busy (q1, q3 free), the row must wait rather than take q1+q3 / q2+q3."""
    s = _legacy("lsa-quality-32k-r5-pca", regions="any-cpu-quarter", shape="multi-quarter(2)",
                width_justification="32k perplexity sweep needs two quarters of memory bandwidth")
    assert s["cpus"] == "any-2-quarters"
    need = rf.grant_need(s)
    assert all(not (o & Q3) for o in need.options) and len(need.options) == 3
    busy = [rf.Grant(f"b{i}", rf.QUARTERS[i], "none", False, 8, 1, T0, T0 + 3600, 1800) for i in (0, 2)]
    plan = rf.admit([s], busy, T0)
    assert not plan.grants
    plan = rf.admit([s], [], T0)
    assert plan.grants and not (plan.grants[0].cores & Q3)
    # a single-quarter non-timing row may still land on q3
    assert rf.QUARTERS[3] in rf.grant_need(spec("one", cpus="any-quarter", threads=24)).options


@settings(max_examples=150, deadline=None)
@given(cpus=st.sampled_from(["any-2-quarters", "any-3-quarters", "any-30-of-q0,q1,q2,q3", "any-48-of-q0,q1,q2,q3"]),
       busy=st.sets(st.integers(0, 3), max_size=3), timing=st.booleans())
def test_property_no_cpu_multi_quarter_grant_touches_q3(cpus, busy, timing):
    s = spec("mq", cpus=cpus, threads=24, timing=timing)
    grants = [rf.Grant(f"b{i}", rf.QUARTERS[i], "none", False, 1, 1, T0, T0 + 3600, 1800) for i in busy]
    for g in rf.admit([s], grants, T0).grants:
        assert not (g.cores & Q3), (cpus, sorted(g.cores & Q3))


def test_classless_legacy_gpu_row_holds_no_cores_beyond_declared():
    """keeper: shape gpu = GPU + 184-191, q3 stays grantable. A class-less legacy gpu row stays exclusive (decision 1)
    but holds no 88-95; a gpu-q3 / block-timing row still does."""
    s = _legacy("c6-gpu-build", regions="mi210_0,184-191", shape="gpu")
    assert s["gpu"] == "exclusive" and not s.get("timing")
    plan = rf.admit([s], [], T0)
    assert [g.cores for g in plan.grants] == [frozenset()]
    t = _legacy("c6-gpu-timing", regions="mi210_0,184-191", shape="gpu-q3")
    assert rf.admit([t], [], T0).grants[0].cores == rf.GPU_SIBLING_CORES
    b = _legacy("c6-gpu-bt", regions="mi210_0,184-191", shape="gpu", admission_class="block-timing-pairable")
    assert rf.admit([b], [], T0).grants[0].cores == rf.GPU_SIBLING_CORES


def test_failed_row_whose_job_changes_under_same_launcher_is_rearmed(tmp_path):
    flags, d = tmp_path / "flags", tmp_path / "job"
    for sub in ("ready", "grants", "dryrun/r1"):
        (flags / sub).mkdir(parents=True)
    d.mkdir()
    job, eng = d / "job.py", d / "filler_run15.sh"
    job.write_text("print(1)\n")
    eng.write_text("#!/bin/sh\n")
    lp = d / "launch.sh"
    lp.write_text(f"#!/bin/bash\nD={d}\nexec $D/filler_run15.sh --id r1 --cmd \"python3 $D/job.py\"\n")
    assert str(job) in rf.launcher_refs(str(lp))
    s = spec("r1", cpus="q2", threads=12, launcher=str(lp))
    (flags / "ready" / "r1.json").write_text(json.dumps(dict(s, schema=rf.SCHEMA)))
    j0 = rf.job_sha(str(lp))
    (flags / "dryrun/r1/SMOKE.json").write_text(json.dumps({"start": 0, "job_sha256": j0}))
    (flags / "dryrun/r1/FAIL-1.json").write_text(json.dumps({"reason": "smoke failed", "launcher_sha256": rf.sha256(str(lp))}))
    rf.stamp_job_sha(str(flags), "r1")
    os.remove(flags / "dryrun/r1/SMOKE.json")
    assert json.loads((flags / "dryrun/r1/FAIL-1.json").read_text())["job_sha256"] == j0
    w = rf.load_world(str(flags), T0)
    assert w.state["r1"] == "failed", w.unmapped
    job.write_text("print(2)  # the fix\n")
    assert rf.job_sha(str(lp)) != j0
    assert rf.load_world(str(flags), T0).state["r1"] == "needs-smoke"
