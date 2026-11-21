"""BUILD-AUTO-RELEASE: an idle build-* claim (<5% of its CPUs busy for 30 min) is released by the keeper; never a measurement row."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rowflow"))
import rowflow as rf  # noqa: E402

CPUS = "0-23,96-119"


def _mk(tmp, rid, build=True):
    flags = str(tmp)
    G = os.path.join(flags, "grants")
    os.makedirs(G, exist_ok=True)
    with open(os.path.join(G, rid + ".grant"), "w") as f:
        f.write(f"regions=q0 start=1 end=9999999999 holds=q0 cpus={CPUS}\n")
    if build:
        rf.atomic_json(os.path.join(G, rid + ".build.json"), {"id": rid, "owner": "autokernel", "kind": "build", "quarters": ["q0"], "cpus": CPUS})
    return flags


def _sample(busy_frac, t):
    return {c: (int(t * 100 * busy_frac) if (c < 24 or 96 <= c < 120) else 0, t * 100) for c in range(192)}


def _run(flags, rid, frac, minutes=(0, 10, 20, 31)):
    logs, out = [], []
    for m in minutes:
        out = rf.build_idle_release(flags, {"q0": rid}, logs.append, sample=_sample(frac, m * 60), now=1000 + m * 60)
    return logs, out


def test_idle_build_claim_is_released_after_30_min(tmp_path):
    rid = "build-autokernel-20261121T005201Z"
    flags = _mk(tmp_path, rid)
    logs, out = _run(flags, rid, 0.02)
    assert out == [rid]
    ended = open(os.path.join(flags, "grants", rid + ".ended")).read()
    assert "reason=auto-released-idle-build" in ended
    assert any(l.startswith(f"BUILD-AUTO-RELEASED {rid} idle 31min") for l in logs)
    assert not os.path.exists(os.path.join(flags, "grants", rid + ".grant"))


def test_idle_build_not_released_before_30_min(tmp_path):
    rid = "build-autokernel-20261121T035716Z"
    flags = _mk(tmp_path, rid)
    _, out = _run(flags, rid, 0.02, minutes=(0, 10, 29))
    assert out == []
    assert not os.path.exists(os.path.join(flags, "grants", rid + ".ended"))


def test_active_build_claim_is_not_released(tmp_path):
    rid = "build-autokernel-20261121T010000Z"
    flags = _mk(tmp_path, rid)
    _, out = _run(flags, rid, 0.60, minutes=(0, 10, 20, 31, 45))
    assert out == []
    assert os.path.exists(os.path.join(flags, "grants", rid + ".grant"))
    assert not os.path.exists(os.path.join(flags, "grants", rid + ".ended"))


def test_a_busy_burst_resets_the_idle_window(tmp_path):
    rid = "build-autokernel-20261121T011500Z"
    flags = _mk(tmp_path, rid)
    cpus = rf._cpu_ids(CPUS)
    def smp(b, t):
        return {c: ((b if c in cpus else 0), t) for c in range(192)}
    logs = []
    rf.build_idle_release(flags, {"q0": rid}, logs.append, sample=smp(0, 0), now=1000)
    rf.build_idle_release(flags, {"q0": rid}, logs.append, sample=smp(0, 2000), now=1000 + 20 * 60)
    rf.build_idle_release(flags, {"q0": rid}, logs.append, sample=smp(1500, 2500), now=1000 + 25 * 60)  # burst: 60% busy
    out = rf.build_idle_release(flags, {"q0": rid}, logs.append, sample=smp(1500, 4500), now=1000 + 40 * 60)  # idle again 15 min
    assert out == []


def test_non_build_row_is_never_auto_released(tmp_path):
    rid = "r1-measurement-row-20261121"
    flags = _mk(tmp_path, rid, build=False)
    rf.atomic_json(os.path.join(flags, "grants", rid + ".build.json"), {"id": rid, "owner": "x", "cpus": CPUS})  # even a stray build.json
    logs, out = _run(flags, rid, 0.0)
    assert out == []
    assert not os.path.exists(os.path.join(flags, "grants", rid + ".ended"))
    assert not any("BUILD-AUTO-RELEASED" in l for l in logs)


def test_disabled_policy_releases_nothing(tmp_path):
    rid = "build-autokernel-20261121T020000Z"
    flags = _mk(tmp_path, rid)
    rf.atomic_json(os.path.join(flags, "allocator.json"), {"build_pocket": {"auto_release_idle": {"enabled": False}}})
    _, out = _run(flags, rid, 0.0)
    assert out == []
