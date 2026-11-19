"""LB1c must not derive crossover cuts from incomplete or unmatched launches."""
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("lb1c_driver", Path(__file__).with_name("v11_driver.py"))
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)


class Context:
    def __init__(self, stop_after=100):
        self.res = {}
        self.saves = 0
        self.stop_after = stop_after

    def save(self):
        self.saves += 1

    def should_stop(self):
        return self.saves >= self.stop_after


def collect(monkeypatch, modify=lambda i, r: None, stop_after=100):
    ctx = Context(stop_after)
    monkeypatch.setattr(d, "LB1C_TYPES", ["q4_K"])

    def launch(*args, **kwargs):
        i = ctx.saves
        # A's shape mean is 100 us, B's is 50 us; lower is better.
        us = 100 if i % 2 == 0 else 50
        r = {"rc": 0, "perf": {f"q4_K|{n}|{m}|256": us + offset
                               for n in range(4, 10)
                               for m, offset in ((256, -10), (512, 10))}}
        modify(i, r)
        return r

    monkeypatch.setattr(d, "tbo", launch)
    return d.run_lb1c(ctx, Path("A"), Path("B")), ctx


def test_complete_matching_launches(monkeypatch):
    out, ctx = collect(monkeypatch)
    assert out["q4_K"][4] == {"A": [100, 100, 100], "B": [50, 50, 50]}
    assert d.lb1c_crossover(out) == {"q4_K": 4}
    assert len(ctx.res["lb1c_launches"]["q4_K"]) == ctx.saves == 6


def test_disjoint_arm_shapes_cannot_create_a_cut(monkeypatch):
    def modify(i, r):
        # All launches succeed and contain equal counts, but B measured a
        # different shape. The former per-arm means falsely yielded cut=4.
        if i % 2:
            r["perf"] = {k.replace("|512|", "|1024|"): v for k, v in r["perf"].items()}

    out, _ = collect(monkeypatch, modify)
    assert out == {"q4_K": {}}
    assert d.lb1c_crossover(out) == {}


def test_missing_shape_in_one_launch_invalidates_that_width(monkeypatch):
    def modify(i, r):
        if i == 3:
            r["perf"].pop("q4_K|9|512|256")

    out, _ = collect(monkeypatch, modify)
    assert 8 in out["q4_K"] and 9 not in out["q4_K"]
    assert d.lb1c_crossover(out) == {}


@pytest.mark.parametrize("rc", [1, 124, 125, None])
def test_failed_launch_cannot_supply_partial_timings(monkeypatch, rc):
    def modify(i, r):
        if i == 3:
            r["rc"] = rc

    out, ctx = collect(monkeypatch, modify)
    assert out == {"q4_K": {}}
    assert ctx.res["lb1c_launches"]["q4_K"][3]["result"]["rc"] == rc


def test_deadline_stop_cannot_shrink_the_launch_population(monkeypatch):
    out, ctx = collect(monkeypatch, stop_after=4)
    assert out == {"q4_K": {}}
    assert ctx.saves == 4


@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf"), "50"])
def test_invalid_timings_are_refused(monkeypatch, value):
    def modify(i, r):
        if i == 3:
            r["perf"]["q4_K|9|512|256"] = value

    out, _ = collect(monkeypatch, modify)
    assert out == {"q4_K": {}}


@pytest.mark.parametrize("key", ["malformed", "q6_K|9|512|256"])
def test_wrong_type_or_malformed_cell_is_refused(monkeypatch, key):
    def modify(i, r):
        if i == 3:
            r["perf"][key] = 50

    out, _ = collect(monkeypatch, modify)
    assert out == {"q4_K": {}}


def perf_line(runs="100", us="50", shape="m=256,n=9,k=256"):
    return (f"MUL_MAT(type_a=q4_K,type_b=f32,{shape},bs=[1,1]): "
            f"{runs} runs - {us} us/run\n")


@pytest.mark.parametrize("runs,us", [
    ("0", "50"), ("-1", "50"), ("1.5", "50"), ("bad", "50"),
    ("100", "0"), ("100", "-1"), ("100", "nan"), ("100", "inf"),
    ("100", "1.2.3"),
])
def test_parser_refuses_invalid_record_even_among_valid_repeats(runs, us):
    # In particular, zero-run records previously became ordinary timings,
    # and NaN/Inf records were silently omitted from otherwise valid logs.
    with pytest.raises(ValueError, match="invalid MUL_MAT perf record"):
        d.parse_tbo_perf(perf_line() + perf_line(runs, us) + perf_line())


@pytest.mark.parametrize("shape", ["m=0,n=9,k=256", "m=256,n=-1,k=256",
                                       "m=256,n=9", "m=bad,n=9,k=256"])
def test_parser_refuses_invalid_shape(shape):
    with pytest.raises(ValueError, match="invalid MUL_MAT perf record"):
        d.parse_tbo_perf(perf_line(shape=shape))


def test_parser_retains_valid_repeats_and_scientific_notation():
    assert d.parse_tbo_perf(perf_line(us="4e1") + perf_line(us="60")) == {
        ("q4_K", 9, "256", "256"): 50}


@pytest.mark.parametrize("child_rc,expected_rc", [(0, 126), (124, 124)])
def test_tbo_retains_invalid_record_refusal(monkeypatch, tmp_path, child_rc, expected_rc):
    ctx = Context()
    ctx.dir = tmp_path
    ctx.time_left = lambda: 1000
    ctx.say = lambda msg: None

    def run(argv, env, log, timeout, **kwargs):
        log.write_text(perf_line() + perf_line(runs="0"))
        return child_rc, 12345

    monkeypatch.setattr(d, "run_logged", run)
    result = d.tbo(ctx, "invalid", Path("A"), Path("A"), "gpu", "ROCm0",
                   "MUL_MAT", perf_filter="type_a=q4_K,type_b=f32")
    assert result["rc"] == expected_rc
    assert result["perf"] == {}
    assert "0 runs" in result["perf_parse_error"]
    assert Path(result["log"]).is_file()
