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
