"""WITNESS-LOGLEVEL / WITNESS-UNDECLARED (knob form): a knob witness is an INFO line; llama-server needs -lv >= 4."""
import os
import sys

_T = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_T), "rowflow"))
import preflight as pf  # noqa: E402


def _row(tmp_path, argv, knobs=("GGML_HIP_I8PC",), wl=None):
    (tmp_path / "job.py").write_text(f"KNOBS = {list(knobs)!r}\nSERVER_ARGV = {argv!r}\n# llama-server\n")
    spec = {"id": "r"}
    if wl:
        spec["witness_lines"] = wl
    return pf.Row(spec, str(tmp_path))


BASE = ["/x/llama-server", "-m", "/m.gguf", "--port", "{PORT}"]


def test_no_lv_fails(tmp_path):
    f = pf.check_witness_loglevel(_row(tmp_path, BASE), {})
    assert f and f[0][0] == "FAIL" and f[0][1] == "WITNESS-LOGLEVEL"
    assert "witness GGML_HIP_I8PC needs -lv >= 4; argv has none" in f[0][2]


def test_low_lv_fails_and_lv4_passes(tmp_path):
    assert pf.check_witness_loglevel(_row(tmp_path, BASE + ["-lv", "3"]), {})
    assert not pf.check_witness_loglevel(_row(tmp_path, BASE + ["-lv", "4"]), {})
    assert not pf.check_witness_loglevel(_row(tmp_path, BASE + ["--log-verbose"]), {})


def test_no_witness_no_check(tmp_path):
    assert not pf.check_witness_loglevel(_row(tmp_path, BASE, knobs=()), {})
    assert not pf.check_witness_declared(_row(tmp_path, BASE, knobs=()), {})


def test_served_ref_delta_counts(tmp_path):
    r = _row(tmp_path, BASE)
    r.spec["served_ref"] = {"argv": BASE + ["-lv", "4"], "argv_delta": []}
    assert not pf.check_witness_loglevel(r, {})


def test_undeclared(tmp_path):
    f = pf.check_witness_declared(_row(tmp_path, BASE), {})
    assert f and f[0][1] == "WITNESS-UNDECLARED"
    assert not pf.check_witness_declared(_row(tmp_path, BASE, wl=[{"line": "x", "needs": 1, "cap": -1}]), {})
