"""Publish-time admission (P3.5), the token algebra, map_legacy over real (sanitized) v3 manifests, and the tunable count."""
import glob
import json
import os

import pytest

from rf2 import rf, spec

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "legacy")
yes = lambda p: True  # noqa: E731


def errs(**kw):
    return rf.validate(spec("r", **kw), launcher_exists=yes)


def test_exactly_nine_tunables_and_every_constant_classified():
    # 8 + IDLE_HELD_S (operator 2026-11-05 "auto-end in rowflow2"): the only wall-clock idle budget; its warning (IDLE_WARN_S)
    # and retry count (IDLE_HELD_RETRY) are derived / fixed FACTS, not tunables
    assert len(rf.TUNABLES) == 9
    assert set(rf.TUNABLES) == {"SMOKE_CORES", "IDLE_SAMPLES", "IDLE_PCT", "SMOKE_DEADLINE_S", "OVERRUN_FACTOR",
                                "QUIET_MAX_RANK", "FILE_OWNERLESS_S", "CLAIM_TTL_S", "IDLE_HELD_S"}
    assert rf.IDLE_HELD_S == 900 and rf.IDLE_WARN_S == 300 and rf.IDLE_HELD_RETRY == 1
    upper = {k for k, v in vars(rf).items() if k.isupper() and not k.startswith("_") and not callable(v)}
    assert upper == set(rf.TUNABLES) | set(rf.CONFIG) | set(rf.FACTS), upper ^ (set(rf.TUNABLES) | set(rf.CONFIG) | set(rf.FACTS))
    assert rf.IDLE_SAMPLES == 2 and rf.OVERRUN_FACTOR == 1.5 and rf.QUIET_MAX_RANK == 10
    assert rf.SMOKE_CORES == frozenset({20, 21, 22, 23})


def test_token_algebra():
    assert rf.parse_cpus("q2").options == (frozenset(range(48, 72)),)
    assert rf.parse_cpus("q0").options == (frozenset(range(0, 20)),)             # smoke lane carved
    assert rf.parse_cpus("0-47,96-143").options[0] == frozenset(range(48)) - rf.SMOKE_CORES  # siblings fold
    assert len(rf.parse_cpus("any-quarter").options) == 4
    assert rf.parse_cpus("any-quarter-of-q1,q3").options == (rf.QUARTERS[1], rf.QUARTERS[3])
    n = rf.parse_cpus("any-2-of-q3")
    assert n.width == 2 and n.pool == frozenset(range(72, 96))
    assert rf.parse_cpus(4).width == 4 and rf.parse_cpus(0).min_width() == 0
    for bad in ("184-191", "20-23", "q4", "any-30-of-q3", "banana", True):
        with pytest.raises(ValueError):
            rf.parse_cpus(bad)
    # the gpu token owns 184-191: a grant's taskset adds them only with gpu, and c88-95 never carry their sibling
    assert rf.taskset_list(frozenset(range(88, 96)), "none") == "88-95"
    assert rf.taskset_list(frozenset({48}), "shared") == "48,144,184-191"


@pytest.mark.parametrize("kw,needle", [
    (dict(cpus="q2", threads=25), "threads 25 not in 1..24"),                  # 1 threads <= |cpus|
    (dict(cpus="q2", threads=4), "over-declared"),                             # 2 |cpus|>=24 needs threads>=12
    (dict(quiet=True, rank=50), "quiet needs priority_rank"),                  # 3
    (dict(gpu="exclusive", cpus=0, threads=8, est=7201), "gpu exclusive needs estimate_s"),  # 4
    (dict(stop="$D/STOP"), "not an absolute literal path"),                    # 5
    (dict(rule="prose only", owner="?"), "decision_rule is not machine-evaluable"),         # 7
])
def test_seven_admission_lines_refuse(kw, needle):
    assert any(needle in e for e in errs(**kw)), errs(**kw)


def test_admission_passes_and_operator_escapes():
    assert errs() == []
    assert errs(quiet=True, rank=5) == []
    assert errs(quiet=True, rank=100, quiet_reason="operator: overnight timing") == []
    assert errs(gpu="exclusive", cpus=0, threads=8, est=28800, quiet_reason="operator: long A/B") == []
    assert errs(cpus=0, threads=8, gpu="shared") == []
    assert errs(rule="the prose rule a human files", owner="mainA") == []
    assert rf.validate(spec("r", launcher="/nonexistent/launch.sh")) != []      # 6 launcher exists
    assert any("unknown field shape" in e for e in errs(shape="quarter"))       # no legacy keys in a v4 spec
    assert any("type" in e for e in errs(threads=True))


def test_measured_busy_feedback_refuses_successor_unless_acked():
    pred = {"busy_p95": 0.04, "cpus": 20}
    assert any("measured" in e for e in rf.validate(spec("r2", cpus="any-quarter"), pred, yes))
    assert rf.validate(spec("r2", cpus="any-quarter", measured_ack="op: needs the RAM bandwidth"), pred, yes) == []
    assert rf.validate(spec("r2", cpus=4, threads=4), pred, yes) == []          # declares less: fine
    assert rf.validate(spec("r2", cpus="any-quarter"), {"busy_p95": 0.6, "cpus": 20}, yes) == []


def test_machine_rule_is_ast_whitelisted():
    assert rf.machine_rule("rc == 0 and reason != 'disk-floor'")
    assert rf.machine_rule("rc in (0, 75)")
    for bad in ("__import__('os').system('x')", "open('/etc/passwd')", "rc.__class__", "C6 timing: lower is better"):
        assert rf.machine_rule(bad) is None


def _legacy(name):
    with open(os.path.join(FIX, name + ".json")) as f:
        return json.load(f)


@pytest.mark.parametrize("name,cpus,gpu,quiet", [
    ("akagg-ch-lb1-c5-ansi-r2-20261104", "any-quarter", "none", False),
    ("akagg-ch26-compact-observer-overhead-r2-20261104", "0-95", "none", False),
    ("akagg-ch26b-mmap-abi-20261102", "0-3", "none", False),
    ("ak-asm-h5-fa-retarget-20261105", 0, "exclusive", False),          # gpu-q3 shape -> timing -> exclusive
    ("inf22-m4-aa-np4-r8-20261103", 0, "exclusive", False),             # block-timing-pairable -> exclusive
    ("c6q4-timing-4arm-20261105", "88-95", "exclusive", False),
    ("codex-ni-s18-qwenvl-cpu-r1-20261031", "0-47", "none", False),     # siblings 96-143 fold into cores
    ("yarn-oolong-s0-split256-eligible28-anyofq012-v27-20261030", "any-quarter-of-q0,q1,q2", "none", False),
    ("inf75-c5-w3-halfb-census-c6-r3-20261105", "48-95", "exclusive", False),
    ("akx-auto10-q4k-mmid-v3-20261102", "0-95", "none", True),          # quiet-host -> quiet (refused later: rank 22)
])
def test_map_legacy_representative(name, cpus, gpu, quiet):
    s, why = rf.map_legacy(_legacy(name))
    assert why is None and s["cpus"] == cpus and s["gpu"] == gpu and s["quiet"] is quiet


def test_map_legacy_gpu_shared_for_correctness_classes():
    m = dict(_legacy("akagg-c3-native-bolt-r9-20261102"), admission_class="block-correctness")
    assert rf.map_legacy(m)[0]["gpu"] == "shared"
    m["admission_class"] = "diagnostic"
    assert rf.map_legacy(m)[0]["gpu"] == "shared"
    m["shape"] = "gpu-q3"                       # a timing shape wins over a correctness class
    assert rf.map_legacy(m)[0]["gpu"] == "exclusive"


def test_map_legacy_threads_declared_or_width_default():
    m = dict(_legacy("akagg-ch26b-mmap-abi-20261102"), declared_threads=2)
    assert rf.map_legacy(m)[0]["threads"] == 2
    assert rf.map_legacy(_legacy("handoff-kvu-16a-load-20261102"))[0]["threads"] == 4     # mi210_0,184-187
    m = dict(_legacy("akagg-ch26-compact-observer-overhead-r2-20261104"), declared_threads=1)
    s, _ = rf.map_legacy(m)
    assert any("over-declared" in e for e in rf.validate(s, launcher_exists=yes))      # host + 1 thread: refused


@pytest.mark.parametrize("name,needle", [
    ("c6-pre-mmq-capture-build-20261104", "gpu host threads 184-191 but the row declares no gpu"),
    ("refactor-c6-cpu-build-729599d69-20261030", "is not epyc.row.v3"),
])
def test_map_legacy_explicit_reasons(name, needle):
    s, why = rf.map_legacy(_legacy(name))
    assert s is None and needle in why


def test_every_fixture_maps_or_names_a_reason():
    for p in glob.glob(os.path.join(FIX, "*.json")):
        with open(p) as f:
            s, why = rf.map_legacy(json.load(f))
        assert (s is None) == bool(why)
        if s:
            assert all(isinstance(e, str) and e for e in rf.validate(s, launcher_exists=yes))
