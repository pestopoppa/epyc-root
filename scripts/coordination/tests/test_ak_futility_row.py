"""AK-EVAL-FUT default in mk_ak_row polar: helper parity, scaffold output, refusal, LOOSE-FUTILITY lint, cx41 publish."""
import hashlib
import json
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
RF = os.path.normpath(os.path.join(HERE, "..", "rowflow"))
sys.path.insert(0, RF)
import ak_futility_row as F  # noqa: E402
import ak_row_lint as L  # noqa: E402
import mk_ak_row as MK  # noqa: E402

RESEARCH = "/mnt/raid0/llm/epyc-inference-research"
UPSTREAM = "scripts/kernel_rnd/autokernel/loop/futility.py"

# Fixture numbers computed with research loop/futility.py @ sha256 F.UPSTREAM_SHA256 (the first three are the
# literal cases of research test_futility.py::test_look_never_answers_and_waits_for_min_pairs).
LOOKS = [
    (([-9.0], 1.0, 1.0, 2.5), {"decision": "continue", "k": 1, "bound_pct": None}),
    (([-9.0, -9.0], 1.0, 1.0, 2.5), {"decision": "futile", "k": 2, "bound_pct": -7.2322}),
    (([50.0, 50.0], 1.0, 1.0, 2.5), {"decision": "continue", "k": 2, "bound_pct": 51.7678}),
    (([0.3, -0.2, 0.1, 0.4], 0.8, 1.0, 3.5), {"decision": "continue", "k": 4, "bound_pct": 1.55}),
    (([-1.2, -0.4, -0.9], 0.5, 1.0, 2.5), {"decision": "futile", "k": 3, "bound_pct": -0.1116}),
]


@pytest.mark.parametrize("args,want", LOOKS)
def test_helper_look_parity_with_upstream_fixtures(args, want):
    r, s, b, z = args
    assert F.look(r, sigma_pair_pct=s, bar_pct=b, z=z) == want


def test_helper_sigma_and_ratio_parity():
    assert F.log_ratios_pct([100, 100, 100], [90, 100.2, 105]) == pytest.approx(
        [-10.536051565782628, 0.1998002662673058, 4.879016416943205], abs=1e-12)
    assert F.sigma_from_aa_samples([100, 101, 99, 100], [100.5, 100, 99.7, 101]) == pytest.approx(0.8875752096503974)
    assert F.sigma_from_aa_samples([100, 100], [101, 99]) is None
    assert F.sigma_from_single_pair_floor(1.5) == pytest.approx(0.7653061224489796)
    assert (F.Z_SERVING, F.Z_BENCH, F.MIN_PAIRS, F.P95_Z) == (2.5, 3.5, 2, 1.96)
    assert F.STOPPING == "fixed_pairs+futility_only.v1" and F.SCHEMA == "epyc.autokernel.futility_look.v1"


def test_live_upstream_sha_and_parity_when_available(tmp_path):
    if not os.path.isdir(os.path.join(RESEARCH, ".git")) and not os.path.isfile(os.path.join(RESEARCH, ".git")):
        pytest.skip("research repo absent")
    r = subprocess.run(["git", "-C", RESEARCH, "show", f"origin/main:{UPSTREAM}"], capture_output=True)
    assert r.returncode == 0, f"research repo present but origin/main:{UPSTREAM} unreadable: {r.stderr[:200]!r}"
    got = hashlib.sha256(r.stdout).hexdigest()
    assert got == F.UPSTREAM_SHA256, (f"upstream futility.py drifted ({got} != pinned {F.UPSTREAM_SHA256}): re-vendor "
                                      "rowflow/ak_futility_row.py from it, re-verify parity and re-pin UPSTREAM_SHA256")
    (tmp_path / "upfut.py").write_bytes(r.stdout)
    sys.path.insert(0, str(tmp_path))
    try:
        import upfut
    finally:
        sys.path.pop(0)
    for (rr, s, b, z), _ in LOOKS:
        assert F.look(rr, sigma_pair_pct=s, bar_pct=b, z=z) == upfut.look(rr, sigma_pair_pct=s, bar_pct=b, z=z)


def test_futile_result_is_polar_fail_never_keep():
    fut = F.Look(0.5, 1.0, 2.5)
    rec = fut([100, 100], [90, 91])
    assert rec["decision"] == "futile" and {"k", "bound_pct", "sigma_pair_pct", "z", "bar_pct"} <= set(rec)
    res = fut.result(rec)
    assert res["verdict"] == "FUTILITY_CANDIDATE_BELOW_BAR" and res["polar"] == "FAIL"
    assert res["futility"]["stop_on_answer"] is False and res["futility"]["stopped_at"] is rec
    assert fut([100, 100], [150, 150])["decision"] == "continue"   # a huge win only continues


def _new(tmp_path, rid, extra, lane="cpu"):
    args = ["new", rid, "--handoff", "x.md", "--box", "T", "--lane", lane,
            "--regions", "0-23" if lane == "cpu" else "88-95", "--threads", "8", "--units", "8", "--unit-s", "10",
            "--model", "X", "--root", str(tmp_path)] + extra
    return MK.polar_main(args, fetch=lambda *a: ("abc", {"gpu_common.py": b"", "gpuproof_row.py": b""}))


def test_default_scaffold_states_rule_and_pins_helper(tmp_path, capsys):
    assert _new(tmp_path, "ak-fut-cpu-20261125", ["--keep-bar-pct", "1.0", "--sigma-source", "floor1:1.5"]) == 0
    d = tmp_path / "ak-fut-cpu-20261125"
    job = (d / "job.py").read_text()
    assert "on-futility: TODO" not in job and "AK-EVAL-FUT z=2.5" in job and "no early KEEP" in job
    assert (d / "ak_futility_row.py").exists()
    sha = hashlib.sha256((d / "ak_futility_row.py").read_bytes()).hexdigest()
    assert sha in job and f"{sha}  ak_futility_row.py" in (d / "SOURCE.sha256").read_text()
    spec = json.loads((d / "spec.json").read_text())
    f = spec["futility"]
    assert f["rule"].startswith("AK-EVAL-FUT z=2.5") and f["look_pairs"] == 2 and f["bar_pct"] == 1.0
    assert f["sigma_pair_pct"] == pytest.approx(1.5 / 1.96, abs=1e-6) and f["upstream_sha256"] == F.UPSTREAM_SHA256
    compile(job, "job.py", "exec")


def test_gpu_lane_defaults_to_bench_z(tmp_path):
    assert _new(tmp_path, "ak-fut-gpu-20261125", ["--keep-bar-pct", "1.0", "--sigma-source", "floor1:1.5"], "gpu") == 0
    spec = json.loads((tmp_path / "ak-fut-gpu-20261125" / "spec.json").read_text())
    assert spec["futility"]["z"] == 3.5
    assert _new(tmp_path, "ak-fut-z-20261125", ["--keep-bar-pct", "1", "--sigma-source", "floor1:1", "--fut-z", "3"]) == 0
    assert json.loads((tmp_path / "ak-fut-z-20261125" / "spec.json").read_text())["futility"]["z"] == 3.0


def test_aa_sigma_source(tmp_path):
    aa = tmp_path / "aa.json"
    aa.write_text(json.dumps({"anchor": [100, 101, 99, 100], "candidate": [100.5, 100, 99.7, 101]}))
    assert _new(tmp_path, "ak-fut-aa-20261125", ["--keep-bar-pct", "1", "--sigma-source", f"aa:{aa}"]) == 0
    f = json.loads((tmp_path / "ak-fut-aa-20261125" / "spec.json").read_text())["futility"]
    assert f["sigma_pair_pct"] == pytest.approx(0.8875752096503974, abs=1e-6)


@pytest.mark.parametrize("extra", [[], ["--keep-bar-pct", "1"], ["--keep-bar-pct", "1", "--sigma-source", "floor1:0"],
                                   ["--keep-bar-pct", "1", "--sigma-source", "aa:/nonexistent/aa.json"]])
def test_refuses_without_sigma_unless_custom(tmp_path, capsys, extra):
    assert _new(tmp_path, "ak-nosig-cpu-20261125", extra) == 1
    assert "--custom-futility" in capsys.readouterr().out and not (tmp_path / "ak-nosig-cpu-20261125").exists()
    assert _new(tmp_path, "ak-nosig-cpu-20261125", extra + ["--custom-futility", "witness-only diagnostic"]) == 0
    d = tmp_path / "ak-nosig-cpu-20261125"
    spec = json.loads((d / "spec.json").read_text())
    assert spec["futility"]["custom_reason"] == "witness-only diagnostic" and not (d / "ak_futility_row.py").exists()


def test_refuses_too_few_units_for_first_look(tmp_path, capsys):
    args = ["new", "ak-few-cpu-20261125", "--handoff", "x.md", "--box", "T", "--lane", "cpu", "--regions", "0-23",
            "--threads", "8", "--units", "3", "--unit-s", "10", "--model", "X", "--root", str(tmp_path),
            "--keep-bar-pct", "1", "--sigma-source", "floor1:1"]
    assert MK.polar_main(args) == 1 and "n/2" in capsys.readouterr().out


def test_default_row_passes_cx41_publish_futility_check(tmp_path):
    import publish_row as PR
    assert _new(tmp_path, "ak-pub-cpu-20261125", ["--keep-bar-pct", "1.0", "--sigma-source", "floor1:1.5"]) == 0
    spec = json.loads((tmp_path / "ak-pub-cpu-20261125" / "spec.json").read_text())
    assert PR.futility_missing(spec) is None
    PR.check_futility(spec, "")


def _codes(d):
    return [c for lvl, c, _ in L.lint_dir(str(d), selftest=False) if c == "LOOSE-FUTILITY" and lvl == "WARN"]


def test_lint_loose_futility_warns_on_own_threshold(tmp_path):
    assert _new(tmp_path, "ak-loose-cpu-20261125", ["--custom-futility", "x"]) == 0
    d = tmp_path / "ak-loose-cpu-20261125"
    spec = json.loads((d / "spec.json").read_text())
    spec["futility"] = {"rule": "stop when mean < 0.97 after 3 units"}
    (d / "spec.json").write_text(json.dumps(spec))
    assert _codes(d) == ["LOOSE-FUTILITY"]
    assert all(lvl != "FAIL" for lvl, c, _ in L.lint_dir(str(d), selftest=False) if c == "LOOSE-FUTILITY")
    spec["futility"]["custom_reason"] = "a ratio-of-medians rule pre-registered in the box"
    (d / "spec.json").write_text(json.dumps(spec))
    assert _codes(d) == []


def test_lint_no_warn_on_standard_helper_row(tmp_path):
    assert _new(tmp_path, "ak-std-cpu-20261125", ["--keep-bar-pct", "1.0", "--sigma-source", "floor1:1.5"]) == 0
    assert _codes(tmp_path / "ak-std-cpu-20261125") == []


def test_cx42_futility_rule_opts_out_and_lint_wants_a_reason(tmp_path):
    assert _new(tmp_path, "ak-own-cpu-20261125", ["--futility", "stop when mean < 0.97 after 3"]) == 0
    d = tmp_path / "ak-own-cpu-20261125"
    assert json.loads((d / "spec.json").read_text())["futility"] == {"rule": "stop when mean < 0.97 after 3"}
    assert "on-futility: stop when mean < 0.97 after 3" in (d / "job.py").read_text()
    assert _codes(d) == ["LOOSE-FUTILITY"]
    assert _new(tmp_path, "ak-own2-cpu-20261125", ["--futility", "stop when mean < 0.97 after 3",
                                                   "--custom-futility", "ratio rule pre-registered in the box"]) == 0
    assert _codes(tmp_path / "ak-own2-cpu-20261125") == []



def _load_job(d, pairs):
    """Import the generated job.py with a stubbed authored slot (measure_pair) returning `pairs`."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(f"job_{d.name.replace('-', '_')}", d / "job.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.measure_pair = lambda i: pairs[i]
    mod.finish_pairs = lambda a, c: {"complete": True, "verdict": "RAN_ALL", "polar": "PASS", "n": len(a)}
    return mod


def test_generated_job_calls_fut_and_stops_futile(tmp_path):
    assert _new(tmp_path, "ak-call-cpu-20261125", ["--keep-bar-pct", "1.0", "--sigma-source", "floor1:1.0"]) == 0
    d = tmp_path / "ak-call-cpu-20261125"
    job = (d / "job.py").read_text()
    assert L.FUT_CALL_RX.search(job) and "def measure_pair" in job and "raise SystemExit(run_pairs())" in job
    mod = _load_job(d, [(100.0, 90.0)] * 8)
    assert mod.N_PAIRS == 8 and mod.run_pairs() == 0
    res = json.loads((d / "out" / "RESULT.json").read_text())
    assert res["verdict"] == "FUTILITY_CANDIDATE_BELOW_BAR" and res["polar"] == "FAIL"
    assert res["futility"]["stopped_at"]["k"] == 2 and len(res["anchor"]) == 2
    mod = _load_job(d, [(100.0, 103.0)] * 8)
    assert mod.run_pairs() == 0 and json.loads((d / "out" / "RESULT.json").read_text())["n"] == 8


def test_lint_fut_uncalled_warns(tmp_path):
    assert _new(tmp_path, "ak-uncall-cpu-20261125", ["--keep-bar-pct", "1.0", "--sigma-source", "floor1:1.0"]) == 0
    d = tmp_path / "ak-uncall-cpu-20261125"
    job = (d / "job.py").read_text().replace("look = FUT(anchor, candidate)", "look = {'decision': 'continue'}  # FUT(x)")
    (d / "job.py").write_text(job)
    msgs = [m for lvl, c, m in L.lint_dir(str(d), selftest=False) if c == "LOOSE-FUTILITY"]
    assert len(msgs) == 1 and msgs[0].startswith("FUT-UNCALLED")
    assert all(lvl == "WARN" for lvl, c, _ in L.lint_dir(str(d), selftest=False) if c == "LOOSE-FUTILITY")


def test_latency_three_pct_win_is_not_futile_when_direction_lower(tmp_path, capsys):
    lat = ([10.0, 10.0], [9.7, 9.7])   # a 3% latency WIN (lower is better)
    assert F.Look(0.5, 1.0, 2.5)(*lat)["decision"] == "futile"            # read as higher-better: wrongly futile
    assert F.Look(0.5, 1.0, 2.5, direction="lower")(*lat)["decision"] == "continue"
    assert F.Look(0.5, 1.0, 2.5, direction="lower")([10.0, 10.0], [10.3, 10.3])["decision"] == "futile"
    base = ["--keep-bar-pct", "1.0", "--sigma-source", "floor1:1.0", "--metric", "e2e_ms_per_round"]
    assert _new(tmp_path, "ak-lat-cpu-20261125", base) == 1 and "--metric-direction" in capsys.readouterr().out
    assert _new(tmp_path, "ak-lat-cpu-20261125", base + ["--metric-direction", "lower"]) == 0
    d = tmp_path / "ak-lat-cpu-20261125"
    assert json.loads((d / "spec.json").read_text())["futility"]["direction"] == "lower"
    assert "direction=lower" in (d / "job.py").read_text()
    mod = _load_job(d, [lat[0][0:1] + lat[1][0:1]] * 8)
    assert mod.run_pairs() == 0 and json.loads((d / "out" / "RESULT.json").read_text())["n"] == 8
    assert _new(tmp_path, "ak-tps-cpu-20261125", ["--keep-bar-pct", "1.0", "--sigma-source", "floor1:1.0",
                                                  "--metric", "tok_per_s"]) == 0


def test_keep_bar_ratio_and_ratio_looking_pct(tmp_path, capsys):
    import math
    assert _new(tmp_path, "ak-ratio-cpu-20261125", ["--keep-bar-ratio", "1.01", "--sigma-source", "floor1:1"]) == 0
    assert "100*ln(1.01)" in capsys.readouterr().out
    bar = json.loads((tmp_path / "ak-ratio-cpu-20261125" / "spec.json").read_text())["futility"]["bar_pct"]
    assert bar == pytest.approx(100 * math.log(1.01), abs=1e-6)
    assert _new(tmp_path, "ak-rpct-cpu-20261125", ["--keep-bar-pct", "1.015", "--sigma-source", "floor1:1"]) == 1
    assert "looks like a ratio; use --keep-bar-ratio" in capsys.readouterr().out
    assert _new(tmp_path, "ak-rpct2-cpu-20261125", ["--keep-bar-pct", "1.05", "--sigma-source", "floor1:1"]) == 0


def test_unit_kind_run_counts_pairs(tmp_path, capsys):
    args = ["new", "ak-runs-cpu-20261125", "--handoff", "x.md", "--box", "T", "--lane", "cpu", "--regions", "0-23",
            "--threads", "8", "--units", "6", "--unit-s", "10", "--model", "X", "--root", str(tmp_path),
            "--keep-bar-pct", "1", "--sigma-source", "floor1:1", "--unit-kind", "run"]
    assert MK.polar_main(args) == 1 and "got 3" in capsys.readouterr().out
    args[args.index("6")] = "8"
    assert MK.polar_main(args) == 0
    f = json.loads((tmp_path / "ak-runs-cpu-20261125" / "spec.json").read_text())["futility"]
    assert f["pairs"] == 4 and f["unit_kind"] == "run"


if __name__ == "__main__":
    raise SystemExit("REFUSING: pytest-fixture suite; run: python -m pytest scripts/coordination/tests/test_ak_futility_row.py -q")
