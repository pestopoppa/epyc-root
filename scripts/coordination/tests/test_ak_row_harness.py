#!/usr/bin/env python3
"""ak_row_harness + ak_row_lint: stubbed, no compute (no readbw binary, no sockets bound beyond a stub)."""
import json
import os
import sys
from contextlib import contextmanager

import pytest

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
import ak_row_harness as H  # noqa: E402
import ak_row_lint as LINT  # noqa: E402


class Clock:
    def __init__(self):
        self.t = 1000.0
        self.sleeps = []

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.sleeps.append(s)
        self.t += s


class FakeProbe:
    def __init__(self, p):
        self.p = p

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass

    def p50(self):
        return self.p


def probes(seq):
    it = iter(seq)
    return lambda cpus: FakeProbe(next(it))


def refs(seq):
    it = iter(seq)
    return lambda cpus, node=None: {"rc": 0, "read_sum": next(it)}


def test_sibling_cpus():
    assert H.sibling_cpus([0, 23, 96, 191]) == [96, 119, 0, 95]


def test_guard_backs_off_between_tries_and_polls_every_5s(tmp_path):
    c = Clock()
    g = H.quiet_guard([0, 1], refs([50, 60, 100]), tmp_path, tries=4, backoff_s=90, probe_factory=probes([1, 1, 1]),
                      sleep=c.sleep, clock=c, stop_file=str(tmp_path / "STOP"), deadline=10 ** 10)
    assert g["status"] == "ok" and g["tries"] == 3 and bool(g)
    assert sum(c.sleeps) == 180 and max(c.sleeps) <= 5            # two 90 s backoffs, polled in 5 s steps
    assert json.loads((tmp_path / "ceil_pre.json").read_text())["read_sum"] == 100
    assert len((tmp_path / "contended.jsonl").read_text().splitlines()) == 2


def test_guard_contended_after_tries_and_sibling_probe_counts(tmp_path):
    c = Clock()
    g = H.quiet_guard([0], refs([100] * 4), tmp_path, tries=4, probe_factory=probes([40] * 4), sleep=c.sleep, clock=c,
                      deadline=10 ** 10)
    assert g["status"] == "contended" and len(g["samples"]) == 4 and not g
    assert all("sibling p50" in s["why"][0] for s in g["samples"])


def test_guard_stop_file_during_backoff(tmp_path):
    c = Clock()
    stop = tmp_path / "STOP"

    def sleep(s):
        c.sleep(s)
        if c.t > 1020:
            stop.write_text("")
    g = H.quiet_guard([0], refs([10, 10]), tmp_path, probe_factory=probes([0, 0]), sleep=sleep, clock=c,
                      stop_file=str(stop), deadline=10 ** 10)
    assert g["status"] == "stop" and c.t < 1040


def test_guard_deadline(tmp_path):
    c = Clock()
    g = H.quiet_guard([0], refs([10, 10]), tmp_path, probe_factory=probes([0, 0]), sleep=c.sleep, clock=c,
                      stop_file="", deadline=1030)
    assert g["status"] == "stop"


def test_mid_run_floor_uses_ceil_pre(tmp_path):
    H.set_ceil_pre(tmp_path, 120.0)
    assert H.guard_floor(tmp_path)[0] == 84.0                       # 0.70 x 120 > 0.70 x 112.9
    c = Clock()
    g = H.quiet_guard([0], refs([80.0]), tmp_path, tries=1, probe_factory=probes([0]), sleep=c.sleep, clock=c,
                      deadline=10 ** 10)
    assert g["status"] == "contended"                               # 80 clears 79.03 but not 84
    H.set_ceil_pre(tmp_path, 60.0)
    assert H.guard_floor(tmp_path)[0] == 79.03


def test_run_quiet_never_returns_contended_measurement(tmp_path):
    c = Clock()
    # guard probe, measure probe, guard probe, measure probe
    r = H.run_quiet(lambda: {"tok_s": 1}, [0], refs([100, 100]), tmp_path, probe_factory=probes([0, 48, 0, 3]),
                    sleep=c.sleep, clock=c, deadline=10 ** 10)
    assert r["status"] == "ok" and r["probe_p50"] == 3 and r["tries"] == 2
    c2 = Clock()
    r2 = H.run_quiet(lambda: {"tok_s": 1}, [0], refs([100] * 4), tmp_path, tries=2, probe_factory=probes([0, 48, 0, 48]),
                     sleep=c2.sleep, clock=c2, deadline=10 ** 10)
    assert r2["status"] == "contended" and r2["result"] is None


def test_ports_deterministic_free_and_disjoint_from_ancestors():
    a = H.alloc_ports("ak-x-20261123", 2, bind_test=lambda p: True)
    assert a == H.alloc_ports("ak-x-20261123", 2, bind_test=lambda p: True)
    assert all(H.PORT_LO <= p <= H.PORT_HI for p in a)
    r1 = H.expected_ports("ak-x-20261123-r1", 2)
    r2 = H.expected_ports("ak-x-20261123-r2", 2)
    assert not set(r2) & (set(a) | set(r1)) and not set(r1) & set(a)
    busy = set(a[:1])
    b = H.alloc_ports("ak-x-20261123", 2, bind_test=lambda p: p not in busy)
    assert a[0] not in b and a[1] in b
    assert H.ancestor_ids("x-r3") == ["x", "x-r1", "x-r2"] and H.ancestor_ids("x") == []
    with pytest.raises(RuntimeError):
        H.alloc_ports("y", 1, bind_test=lambda p: False)


def test_estimate_and_spec_check(tmp_path):
    assert H.estimate_from_smoke(10.0, 16, 120, 1.25) == 350
    with pytest.raises(ValueError):
        H.estimate_from_smoke(0, 16, 0)
    m = H.write_smoke_measure(tmp_path, 10.0, 2, 120)
    spec = {"estimate_s": 349, "estimate_basis": {"smoke_measure": m, "units": 16}}
    with pytest.raises(ValueError):
        H.check_spec_estimate(spec)
    spec["estimate_s"] = 350
    assert H.check_spec_estimate(spec) == (350, [])
    assert H.check_spec_estimate({"estimate_s": 9})[1]
    with pytest.raises(ValueError):
        H.check_spec_estimate({"estimate_s": 9, "estimate_basis": {"smoke_measure": str(tmp_path / "nope"), "units": 1}})


def _row(tmp_path, rid, job, launch, spec):
    d = tmp_path / rid
    d.mkdir()
    (d / "job.py").write_text(job)
    (d / "launch.sh").write_text(launch)
    (d / "spec.json").write_text(json.dumps(dict(spec, id=rid)))
    return str(d)


def test_lint_flags_all_four(tmp_path):
    d = _row(tmp_path, "ak-bad-20261123-r2",
             "MAX_TRIES=3\nref=readbw(); x = ref['read_sum']\nPORT = 18941\nlibs = ['libllama.so']\ndiffers = any(sha(a, l) != sha(b, l) for l in libs)\n",
             "exec filler --port 18941,18942 --cmd x\n", {"estimate_s": 3600})
    codes = {c for _, c, _ in LINT.lint_dir(d)}
    assert codes == {"QUIET-NO-BACKOFF", "HARDCODED-PORT", "ESTIMATE-UNMEASURED", "DIFFERS-FIXED"}
    assert LINT.main([d]) == 1


def test_lint_clean_row(tmp_path):
    rid = "ak-good-20261123-r2"
    ports = H.expected_ports(rid, 2)
    m = H.write_smoke_measure(tmp_path / "sm", 5.0, 1, 30)
    d = _row(tmp_path, rid,
             "import ak_row_harness as H\nimport fold_row_guard as F\ng = H.quiet_guard(cpus, rb, OUT)\n"
             "ok = F.libs_differ(repo, a, b, x, y)  # libllama.so differs\n",
             f"exec filler --port {ports[0]},{ports[1]} --cmd x\n",
             {"estimate_s": 1000, "estimate_basis": {"smoke_measure": m, "units": 10}})
    assert LINT.lint_dir(d) == []
    assert LINT.main([d]) == 0


def test_lint_differs_ignores_vendored_gpu_common_and_prose(tmp_path):
    rid = "ak-gpu-20261123-r2"
    ports = H.expected_ports(rid, 2)
    m = H.write_smoke_measure(tmp_path / "sm", 5.0, 1, 30)
    d = _row(tmp_path, rid,
             "import ak_row_harness as H\ng = H.quiet_guard(cpus, rb, OUT)\n"
             "# prompt_n differs across launches; libggml-hip.so is checked elsewhere\n"
             "\"\"\"prompt_n differs across launches (libllama.so)\"\"\"\n",
             f"exec filler --port {ports[0]},{ports[1]} --cmd x\n",
             {"estimate_s": 1000, "estimate_basis": {"smoke_measure": m, "units": 10}})
    (tmp_path / os.path.basename(d) / "gpu_common.py").write_text(
        "LIBS = ['libggml-hip.so']\ndef libs_differs_fixed(a, b):\n    return any(a[l] != b[l] for l in LIBS)\n")
    assert LINT.lint_dir(d) == []


def test_lint_differs_still_flags_fixed_list_proof(tmp_path):
    rid = "ak-fx-20261123-r2"
    ports = H.expected_ports(rid, 2)
    m = H.write_smoke_measure(tmp_path / "sm", 5.0, 1, 30)
    d = _row(tmp_path, rid,
             "import ak_row_harness as H\ng = H.quiet_guard(cpus, rb, OUT)\n"
             "libs = ['libggml-hip.so']\nlibs_differ_ok = any(sha(a, l) != sha(b, l) for l in libs)\n".replace("libs_differ_ok", "lib_differs"),
             f"exec filler --port {ports[0]},{ports[1]} --cmd x\n",
             {"estimate_s": 1000, "estimate_basis": {"smoke_measure": m, "units": 10}})
    assert [c for _, c, _ in LINT.lint_dir(d)] == ["DIFFERS-FIXED"]
