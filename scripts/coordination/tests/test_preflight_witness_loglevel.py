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


# ---- grandfathering + report scope (2026-11-24)
import json  # noqa: E402


def _flags_with_pass(tmp_path, rid, launcher_sha=None):
    d = tmp_path / "flags" / "dryrun" / rid
    d.mkdir(parents=True)
    pj = {"first_unit_at": "2026-11-24T20:01:02Z"}
    if launcher_sha:
        pj["launcher_sha256"] = launcher_sha
    (d / "PASS.json").write_text(json.dumps(pj))
    return str(tmp_path / "flags")


def test_grandfathered_pass_row_passes(tmp_path):
    rd = tmp_path / "row"
    rd.mkdir()
    r = _row(rd, BASE)
    spec = {"id": "r", "witness_lines": None}
    flags = _flags_with_pass(tmp_path, "r")
    res = pf.run(spec, row_dir=str(rd), flags=flags, checks=("witness_log", "witness_decl"), grandfather=True)
    assert [x[1] for x in res] == ["PASS", "PASS"] and "grandfathered: smoke PASS 2026-11-24" in res[0][3]
    assert pf.check_witness_loglevel(r, {})   # the raw check itself still fails


def test_unsmoked_row_still_fails(tmp_path):
    rd = tmp_path / "row"
    rd.mkdir()
    _row(rd, BASE)
    flags = str(tmp_path / "flags")
    os.makedirs(flags)
    for gf in (True, False):
        res = pf.run({"id": "r"}, row_dir=str(rd), flags=flags, checks=("witness_log", "witness_decl"), grandfather=gf)
        assert [x[1] for x in res] == ["FAIL", "FAIL"]


def test_stale_launcher_pass_not_grandfathered(tmp_path):
    flags = _flags_with_pass(tmp_path, "r", launcher_sha="a" * 64)
    assert pf.smoke_pass_date(flags, {"id": "r", "launcher": {"sha256": "b" * 64}}) is None
    assert pf.smoke_pass_date(flags, {"id": "r", "launcher": {"sha256": "a" * 64}}) == "2026-11-24"


def test_report_scope_excludes_ended_superseded_stop(tmp_path):
    import rowflow as rf
    flags = str(tmp_path / "f")
    for sub in ("ready/.superseded", "grants", "dryrun", "filing-done"):
        os.makedirs(os.path.join(flags, sub))
    stop = tmp_path / "stopme"
    stop.write_text("")
    def man(rid, **kw):
        m = {"schema": rf.SCHEMA, "id": rid}
        m.update(kw)
        (tmp_path / "f" / "ready" / f"{rid}.json").write_text(json.dumps(m))
    man("live"); man("ended"); man("old"); man("old-r2"); man("held", stop_file=str(stop))
    (tmp_path / "f" / "grants" / "ended.ended").write_text("")
    (tmp_path / "f" / "ready" / ".superseded" / "old.json").write_text(json.dumps({"by": "old-r2"}))
    q, ex = pf.report_scope(flags)
    assert "live" in q and "old-r2" in q
    assert not ({"ended", "old", "held"} & set(q))
    assert "superseded" in ex["old"] and "STOP-held" in ex["held"]
