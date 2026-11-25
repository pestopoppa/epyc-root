#!/usr/bin/env python3
"""D9-ack 2026-11-24 deterministic rowflow preflight (preflight.py): a pass and a FAIL/WARN fixture per check, the
warn-first switch, the publish / grant hooks, the --report counts, and the 2026-11-24 regression incidents
(gvfattn-served-r2 debug cap, c21-gpu27b-identity model/threads/borrowed timing, c21-cpu-r2 interleave contention,
missing selftest handlers, wrong smoke paths, lane-wrong argv). No compute: fake stores are text files run through
`strings`; big models are sparse files."""
import hashlib
import json
import os
import sys

import pytest

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
import preflight as P  # noqa: E402
import rowflow as rf  # noqa: E402

SELFTEST_OK = ("import sys\ndef selftest(): return 0\ndef main(): return 0\n"
               "if __name__ == '__main__':\n    sys.exit(selftest() if '--selftest' in sys.argv[1:] else main())\n")
SRV_FLAGS = ["-m", "-md", "-t", "-tb", "--port", "-c", "--n-cpu-moe", "--spec-draft-ngl", "--cpu-iqk-fa", "-np", "-ctk",
             "--no-mmap"]
NODES = ({0: set(range(0, 24)) | set(range(96, 120)), 1: set(range(24, 48)) | set(range(120, 144)),
          2: set(range(48, 72)) | set(range(144, 168)), 3: set(range(72, 96)) | set(range(168, 192))},
         {n: 256 << 30 for n in range(4)})


def _sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def make_store(base, name="gpu-20261124-abcdef123-t", sha="abcdef1234567890", flags=SRV_FLAGS, knobs=("GGML_CPU_FA_SPLIT_KV",),
               extra=()):
    root = base / "kernels" / "builds" / name
    (root / "bin").mkdir(parents=True)
    (root / "bin" / "llama-server").write_text("\n".join(flags) + "\n")
    (root / "bin" / "libggml-cpu.so").write_text("\n".join(list(knobs) + list(extra)) + "\n")
    rels = ["bin/llama-server", "bin/libggml-cpu.so"]
    (root / "SHA256SUMS").write_text("".join(f"{_sha(root / r)}  {r}\n" for r in rels))
    (root / "BUILD-IDENTITY.json").write_text(json.dumps({"source_sha": sha}))
    return root


def make_model(base, name="Qwen3.8-27B-Q8_0.gguf", size=4096):
    p = base / "models" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "wb") as f:
        f.write(b"GGUF")
        f.truncate(size)   # sparse
    return p


def make_row(base, rid, job=SELFTEST_OK, spec=None, launch="#!/bin/bash\n"):
    d = base / rid
    d.mkdir(parents=True)
    (d / "job.py").write_text(job)
    (d / "launch.sh").write_text(launch)
    s = dict({"id": rid, "owner": "tester", "lane": "cpu", "regions": "q0"}, **(spec or {}))
    (d / "spec.json").write_text(json.dumps(s))
    s["launcher"] = str(d / "launch.sh")
    return d, s


def server_job(store, model, argv='"-t", "8"', head=SELFTEST_OK):
    return (head + f"STORE = {str(store)!r}\nMODEL = {str(model)!r}\n"
            f"def argv():\n    return [STORE + '/bin/llama-server', '-m', MODEL, {argv}, '--port', '1']\n")


def codes(findings, check=None, level=None):
    return {c for ch, l, c, _m in findings if (check is None or ch == check) and (level is None or l == level)}


def run(spec, d, check, **kw):
    kw.setdefault("nodes", NODES)
    return P.run(spec, row_dir=str(d), flags=kw.pop("flags", None), checks=(check,), **kw)


@pytest.fixture(autouse=True)
def _cache(tmp_path, monkeypatch):
    monkeypatch.setenv("PREFLIGHT_CACHE", str(tmp_path / "pfcache"))
    monkeypatch.setattr(P, "TMP_ROOT", str(tmp_path))


# ---------------------------------------------------------------- the switch
def test_enforce_table_all_false_and_one_entry_per_check():
    assert set(P.PREFLIGHT_ENFORCE) == set(P.CHECKS) and len(P.CHECKS) == 16
    assert {c for c, v in P.PREFLIGHT_ENFORCE.items() if v} == {"store", "ports", "append", "witness_log", "witness_decl", "witness_log_tools", "inputs"}
    assert set(P.DRIFT_CHECKS) <= set(P.CHECKS)


def test_effective_demotes_unless_enforced():
    raw = [("ports", "FAIL", "PORT-CLASH", "x"), ("lane", "WARN", "THREADS-DECLARED", "y")]
    assert [f[1] for f in P.effective(raw, {})] == ["WARN", "WARN"]
    assert [f[1] for f in P.effective(raw, {"ports": True})] == ["FAIL", "WARN"]


# ---------------------------------------------------------------- 1 selftest
def test_selftest_missing_handler_every_owner(tmp_path):
    d, s = make_row(tmp_path, "zz-st-20261124", job="def selftest():\n    return 0\nmain()\n")
    assert "SELFTEST-MISSING" in codes(run(s, d, "selftest"), level="FAIL")      # this week: missing handlers
    (d / "job.py").write_text(SELFTEST_OK)
    assert "SELFTEST-MISSING" not in codes(run(s, d, "selftest"))


def test_selftest_reports_lint_fail(tmp_path):
    d, s = make_row(tmp_path, "zz-lint-20261124", job=SELFTEST_OK + "def f(:\n")
    assert "LINT-FAIL" in codes(run(s, d, "selftest"), level="FAIL")
    (d / "job.py").write_text(SELFTEST_OK)
    assert "LINT-FAIL" not in codes(run(s, d, "selftest"))


# ---------------------------------------------------------------- 2 store / model paths
def test_store_ok_and_missing(tmp_path):
    st = make_store(tmp_path)
    m = make_model(tmp_path)
    d, s = make_row(tmp_path, "zz-store-20261124", job=server_job(st, m))
    assert not codes(run(s, d, "store"), level="FAIL")
    (d / "job.py").write_text(server_job(str(st) + "-gone", str(m).replace(".gguf", "-gone.gguf")))
    got = codes(run(s, d, "store"), level="FAIL")
    assert {"STORE-MISSING", "MODEL-MISSING"} <= got


def test_store_sums_and_commit(tmp_path):
    st = make_store(tmp_path, sha="0123456789abcdef")    # name says abcdef123
    d, s = make_row(tmp_path, "zz-commit-20261124", job=server_job(st, make_model(tmp_path)))
    assert "STORE-COMMIT" in codes(run(s, d, "store"), level="FAIL")
    st2 = make_store(tmp_path, name="gpu-20261124-feed12345-u", sha="feed123450000")
    (d / "job.py").write_text(server_job(st2, make_model(tmp_path)))
    assert not codes(run(s, d, "store"), level="FAIL")
    with open(st2 / "bin" / "llama-server", "a") as f:
        f.write("tampered\n")
    assert "STORE-SUMS" in codes(run(s, d, "store", flags=str(tmp_path)), level="FAIL")


def test_store_name_being_formatted_is_skipped(tmp_path):
    d, s = make_row(tmp_path, "zz-fmt-20261124", job=SELFTEST_OK + "S = f'/x/kernels/builds/gpu-20261124-{sha}'\n")
    assert not codes(run(s, d, "store"))


# ---------------------------------------------------------------- 3 flags / knobs
def test_flags_known_unknown_and_tail_merged(tmp_path):
    st = make_store(tmp_path)
    m = make_model(tmp_path)
    d, s = make_row(tmp_path, "zz-flags-20261124", job=server_job(st, m, '"-t", "8", "-ngl", "99", "-fa", "on"'))
    assert "FLAG-UNKNOWN" not in codes(run(s, d, "flags"))          # -ngl / -fa only exist tail-merged
    (d / "job.py").write_text(server_job(st, m, '"-t", "8", "--dca-chunk-size", "8"'))
    assert "FLAG-UNKNOWN" in codes(run(s, d, "flags"), level="FAIL")


def test_flags_scoped_to_server_argv_not_test_backend_ops(tmp_path):
    """AK 2026-11-24: a test-backend-ops argv (--test-file) sharing a job with a server argv is not a llama-server argv."""
    st = make_store(tmp_path)
    m = make_model(tmp_path)
    extra = ("TBO = STORE + '/bin/test-backend-ops'\n"
             "def tbo_argv():\n    return [TBO, '--test-file', 'x.json', '-o', 'MUL_MAT']\n"
             "def tbo2():\n    return [STORE + '/bin/test-backend-ops', '--test-file', 'y.json']\n"
             "def bench():\n    return ['llama-bench', '--delay', '1']\n")
    d, s = make_row(tmp_path, "zz-tbo-20261124", job=server_job(st, m, '"-t", "8"') + extra)
    assert "FLAG-UNKNOWN" not in codes(run(s, d, "flags"))
    (d / "job.py").write_text(server_job(st, m, '"-t", "8", "--dca-chunk-size", "8"') + extra)
    msgs = [x[3] for x in run(s, d, "flags") if x[2] == "FLAG-UNKNOWN"]
    assert msgs and "--dca-chunk-size" in msgs[0] and "--test-file" not in msgs[0]   # server flags still checked


def test_knob_must_be_in_some_store_lib(tmp_path):
    st = make_store(tmp_path)
    m = make_model(tmp_path)
    job = server_job(st, m) + "ENV = {'GGML_CPU_FA_SPLIT_KV': '0'}\n"
    d, s = make_row(tmp_path, "zz-knob-20261124", job=job)
    assert "KNOB-UNKNOWN" not in codes(run(s, d, "flags"))
    (d / "job.py").write_text(job + "ENV2 = {'GGML_NOT_A_KNOB': '1'}\ndef selftest_x():\n    E = {'GGML_FIXTURE_ONLY': 1}\n")
    got = [m_ for _c, l, c, m_ in run(s, d, "flags") if c == "KNOB-UNKNOWN"]
    assert any("GGML_NOT_A_KNOB" in x for x in got) and not any("GGML_FIXTURE_ONLY" in x for x in got)


# ---------------------------------------------------------------- 4 model
def test_model_declared_vs_argv(tmp_path):
    st = make_store(tmp_path)
    m = make_model(tmp_path, "Qwen3.8-27B-Q8_0.gguf")
    d, s = make_row(tmp_path, "zz-gpu27b-20261124", job=server_job(st, m), spec={"model": "Qwen3.8-27B Q8_0"})
    assert not codes(run(s, d, "model"))
    m2 = make_model(tmp_path, "Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00001.gguf")
    (d / "job.py").write_text(server_job(st, m2))
    assert "MODEL-DECLARED" in codes(run(s, d, "model"), level="FAIL")


# ---------------------------------------------------------------- 5 lane
def test_lane_membind_remote_and_outside_grant(tmp_path):
    st, m = make_store(tmp_path), make_model(tmp_path)
    head = SELFTEST_OK + "W = ['/usr/bin/taskset', '-c', '0-7', '/usr/bin/numactl', '--membind=0']\n"
    d, s = make_row(tmp_path, "zz-lane-20261124", job=server_job(st, m, head=head), spec={"declared_threads": 8})
    assert not codes(run(s, d, "lane"), level="FAIL")
    (d / "job.py").write_text(server_job(st, m, head=head.replace("--membind=0", "--membind=3")))
    assert "MEMBIND-REMOTE" in codes(run(s, d, "lane"), level="FAIL")
    (d / "job.py").write_text(server_job(st, m, head=head.replace("0-7", "184-191")))   # lane-wrong argv
    assert "CPUS-OUTSIDE-GRANT" in codes(run(s, d, "lane"), level="FAIL")


def test_lane_host_shape_overlaps_gpu(tmp_path):
    d, s = make_row(tmp_path, "zz-host-20261124", spec={"shape": "host", "regions": "q0,q1,q2,q3"})
    assert "HOST-SHAPE-OVERLAPS-GPU" in codes(run(s, d, "lane"), level="WARN")
    s.update(shape="quiet-host", regions="q0,q1,q2")
    assert "HOST-SHAPE-OVERLAPS-GPU" not in codes(run(s, d, "lane"))
    s.update(lane="gpu", shape="host", regions="mi210_0,184-191")
    assert "HOST-SHAPE-OVERLAPS-GPU" not in codes(run(s, d, "lane"))


def test_lane_threads(tmp_path):
    st, m = make_store(tmp_path), make_model(tmp_path)
    head = SELFTEST_OK + "W = ['/usr/bin/taskset', '-c', '0-3']\n"
    d, s = make_row(tmp_path, "zz-thr-20261124", job=server_job(st, m, '"-t", "8"', head=head),
                    spec={"declared_threads": 4, "regions": "0-3"})
    got = codes(run(s, d, "lane"))
    assert "THREADS-OVERSUB" in got and "THREADS-DECLARED" in got


def test_lane_ram_and_vram_fit(tmp_path):
    st = make_store(tmp_path)
    big = make_model(tmp_path, "Huge-999B.gguf", size=P.host_mem_bytes() + (1 << 30))
    d, s = make_row(tmp_path, "zz-ram-20261124", job=server_job(st, big))
    assert "RAM-FIT" in codes(run(s, d, "lane"), level="FAIL")
    m = make_model(tmp_path, "Small-1B.gguf", size=8 << 20)
    d2, s2 = make_row(tmp_path, "zz-vram-20261124", job=server_job(st, m, '"-t", "8", "-ngl", "99"'),
                      spec={"lane": "gpu", "regions": "mi210_0,184-191"})
    assert "VRAM-FIT" in codes(run(s2, d2, "lane", vram=1 << 20), level="FAIL")
    assert "VRAM-FIT" not in codes(run(s2, d2, "lane", vram=64 << 30))


# ---------------------------------------------------------------- 6 smoke
def test_smoke_measure_path_and_stale_out(tmp_path):
    hdr = "import os, sys\nD = os.path.dirname(os.path.abspath(__file__))\nS = os.environ.get('FILLER_SMOKE')\n"
    end = "H.end_smoke('PASS', 0, 'ok', os.path.join(D, 'out'))\n"
    good = hdr + "OUT_SMOKE = os.path.join(D, 'out-smoke')\nH.write_smoke_measure(OUT_SMOKE, 1, 1, 0)\n" + end
    d, s = make_row(tmp_path, "zz-smoke-20261124", job=SELFTEST_OK + good)
    assert not codes(run(s, d, "smoke"), level="FAIL")
    (d / "job.py").write_text(SELFTEST_OK + hdr + "H.write_smoke_measure(os.path.join(D, 'out', 'smoke'), 1, 1, 0)\n" + end)
    assert "SMOKE-MEASURE-PATH" in codes(run(s, d, "smoke"), level="FAIL")    # this week: wrong smoke path
    (d / "job.py").write_text(SELFTEST_OK + good)
    (d / "out").mkdir()
    (d / "out" / "TERMINAL-smoke.json").write_text("{}")
    (d / "SOURCE.sha256").write_text("00  job.py\n")
    os.utime(d / "out" / "TERMINAL-smoke.json", (1, 1))
    assert "STALE-OUT" in codes(run(s, d, "smoke"), level="FAIL")


# ---------------------------------------------------------------- 7 estimate (RCA F5)
def _measure(d, unit_s=100.0):
    p = d / "out-smoke" / "smoke_measure.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"unit_s": unit_s, "units_measured": 1, "loads_s": 0}))
    return p


def test_estimate_cites_measurement_and_arithmetic(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "_history", lambda *a: None)
    st, m = make_store(tmp_path), make_model(tmp_path)
    d, s = make_row(tmp_path, "zz-est-20261124", job=server_job(st, m))
    mp = _measure(d)
    basis = {"smoke_measure": str(mp), "sha256": _sha(mp), "units": 10, "unit_s": 100.0, "loads_s": 0, "margin": 1.25}
    s.update(estimate_s=1250, estimate_basis=basis)
    assert not codes(run(s, d, "estimate"), level="FAIL")
    s["estimate_s"] = 5000
    assert "ESTIMATE-ARITH" in codes(run(s, d, "estimate"), level="FAIL")
    s["estimate_s"] = 1250
    s["estimate_basis"] = dict(basis, sha256="0" * 64)
    assert "BASIS-SHA" in codes(run(s, d, "estimate"), level="FAIL")
    s["estimate_basis"] = {"units": 10, "unit_s": 100, "reason": "prose"}
    assert "BASIS-INCOMPLETE" in codes(run(s, d, "estimate"), level="FAIL")
    s["estimate_basis"] = dict(basis, unit_s=50.0)
    assert "BASIS-MISMATCH" in codes(run(s, d, "estimate"), level="FAIL")


def test_estimate_borrowed_needs_identical_cell(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "_history", lambda *a: None)
    st, m = make_store(tmp_path), make_model(tmp_path, "Qwen3.8-27B-Q8_0.gguf")
    d, s = make_row(tmp_path, "zz-bor-20261124", job=server_job(st, m), spec={"declared_threads": 8})
    same, _ = make_row(tmp_path, "zz-same-20261123", job=server_job(st, m), spec={"declared_threads": 8})
    mp = _measure(same)
    s.update(estimate_s=1250, estimate_basis={"smoke_measure": str(mp), "sha256": _sha(mp), "units": 10, "unit_s": 100.0,
                                              "loads_s": 0, "margin": 1.25})
    assert "BORROWED-BASIS" not in codes(run(s, d, "estimate"))
    other, _ = make_row(tmp_path, "zz-oth-20261123", job=server_job(st, make_model(tmp_path, "Qwen3.6-35B-A3B.gguf")),
                        spec={"declared_threads": 8})
    mp2 = _measure(other)
    s["estimate_basis"] = dict(s["estimate_basis"], smoke_measure=str(mp2), sha256=_sha(mp2))
    assert "BORROWED-BASIS" in codes(run(s, d, "estimate"), level="FAIL")


def test_estimate_history_warns_over_1p5x(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "_history", lambda *a: {"estimate_s": 500, "estimate_justification": "h"})
    d, s = make_row(tmp_path, "zz-hist-20261124")
    mp = _measure(d)
    s.update(estimate_s=1250, estimate_basis={"smoke_measure": str(mp), "sha256": _sha(mp), "units": 10,
                                              "unit_s": 100.0, "loads_s": 0, "margin": 1.25})
    assert "ESTIMATE-HISTORY" in codes(run(s, d, "estimate"), level="WARN")


# ---------------------------------------------------------------- 11 served argv (RCA F2)
def test_served_argv_against_registry(tmp_path, monkeypatch):
    reg = tmp_path / "reg.yaml"
    reg.write_text("server_mode:\n  worker:\n    no_mmap: true\n    slots: 2\n    serving_shape:\n      n_ctx: 32768\n"
                   "      kv_quant: {k: q8_0, v: q8_0}\n")
    monkeypatch.setattr(P, "REGISTRY", str(reg))
    P._REG.clear()
    monkeypatch.setattr(P, "rebuild_served_argv", lambda *a: (None, "test: no orchestrator"))
    st, m = make_store(tmp_path), make_model(tmp_path)
    good = '"-c", "32768", "-np", "2", "-ctk", "q8_0", "-ctv", "q8_0", "--no-mmap"'
    d, s = make_row(tmp_path, "zz-srv-20261124", job=server_job(st, m, good), spec={"served_ref": {"registry_role": "worker"}})
    assert not codes(run(s, d, "served"))
    (d / "job.py").write_text(server_job(st, m, good.replace('"32768"', '"36864"')))
    assert "SERVED-DELTA" in codes(run(s, d, "served"), level="FAIL")
    s["served_ref"]["argv_delta"] = [{"flag": "-c", "reason": "fits the 32k prompt"}]
    assert not codes(run(s, d, "served"))
    s.pop("served_ref")
    assert "SERVED-REF-MISSING" in codes(run(s, d, "served"), level="WARN")


# ---------------------------------------------------------------- 8 ports
def test_ports_unique_across_queued(tmp_path):
    d, s = make_row(tmp_path, "zz-port-20261124", spec={"ports": [28001]})
    q = {"zz-a-20261124": {"id": "zz-a-20261124", "ports": [28002]}}
    assert not codes(run(s, d, "ports", queued=q))
    q["zz-b-20261124"] = {"id": "zz-b-20261124", "ports": [28001]}
    assert "PORT-CLASH" in codes(run(s, d, "ports", queued=q), level="FAIL")
    s["supersedes"] = "zz-b-20261124"
    assert not codes(run(s, d, "ports", queued=q))


# ---------------------------------------------------------------- 9 append
def test_results_appended_per_unit(tmp_path):
    w = SELFTEST_OK + "def go(rows):\n    with open('out/results.jsonl', 'w') as f:\n        f.write('x')\n"
    d, s = make_row(tmp_path, "zz-app-20261124", job=w, spec={"resumable": True})
    assert "RESULT-NOT-APPENDED" in codes(run(s, d, "append"), level="FAIL")
    (d / "job.py").write_text(SELFTEST_OK + "def unit(r):\n    with open('out/results.jsonl', 'a') as f:\n        f.write(r)\n")
    assert not codes(run(s, d, "append"))


# ---------------------------------------------------------------- 10 witness
def test_witness_undeclared_cap_and_binary(tmp_path):
    st = make_store(tmp_path, extra=("gv_run n_q=%d n_kv=%d", "gv_fattn AUTO_TUNE regime"))
    rule = "KEEP iff witness holds (B logs both AUTO_TUNE regime lines; A/AA log neither)"
    d, s = make_row(tmp_path, "ak-gvfattn-served-gpu-20261124-r2", job=server_job(st, make_model(tmp_path)),
                    spec={"decision_rule": rule})
    assert "WITNESS-UNDECLARED" in codes(run(s, d, "witness"), level="FAIL")   # the gvfattn-served-r2 incident
    s["witness_lines"] = [{"line": "gv_run n_q=%d", "needs": 9, "cap": 8}]
    assert "WITNESS-CAP" in codes(run(s, d, "witness"), level="FAIL")
    s["witness_lines"] = [{"line": "gv_run n_q=%d", "needs": 2}]
    assert "WITNESS-CAP-UNDECLARED" in codes(run(s, d, "witness"), level="FAIL")
    s["witness_lines"] = [{"line": "no such line", "needs": 1, "cap": -1}]
    assert "WITNESS-NOT-IN-BINARY" in codes(run(s, d, "witness"), level="FAIL")
    s["witness_lines"] = [{"line": "gv_fattn AUTO_TUNE regime", "needs": 2, "cap": 8}]
    assert not codes(run(s, d, "witness"))


# ---------------------------------------------------------------- regression incidents
def test_regression_c21_gpu27b_identity(tmp_path, monkeypatch):
    """Flash-Next declared as 27b; 8 host threads under expert offload; timing borrowed from a different-shaped row."""
    monkeypatch.setattr(P, "_history", lambda *a: None)
    st = make_store(tmp_path)
    fn = make_model(tmp_path, "Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00001.gguf")
    argv = '"-t", "8", "-tb", "8", "--n-cpu-moe", "48"'
    make_row(tmp_path, "c20-gpu27b-margin-capture-20261124", job=server_job(st, fn), spec={"declared_threads": 24})
    basis = {"units": 128, "unit_s": 165, "margin": 1.25, "provisional": True,
             "reason": "128 units x ~165 s x 1.25 from c20-gpu27b-margin-capture-20261124 per-unit timing"}
    d, s = make_row(tmp_path, "c21-gpu27b-identity-20261124", job=server_job(st, fn, argv),
                    spec={"lane": "gpu", "regions": "mi210_0,184-191", "declared_threads": 8, "estimate_s": 26400,
                          "estimate_basis": basis})
    res = P.run(s, row_dir=str(d), nodes=NODES, checks=("model", "lane", "estimate"))
    assert "MODEL-DECLARED" in codes(res, "model", "FAIL")
    assert "HYBRID-THIN-HOST" in codes(res, "lane", "WARN")
    assert "BORROWED-BASIS" in codes(res, "estimate", "FAIL")


def test_regression_c21_cpu_r2_interleave_contention(tmp_path):
    st, m = make_store(tmp_path), make_model(tmp_path)
    head = SELFTEST_OK + ("def ppl(phys):\n    return ['/usr/bin/taskset', '-c', '0-23', '/usr/bin/numactl', '--interleave=all']\n")
    spec = {"regions": "q0,q1,q2", "shape_justification": "Three independent A/B paired streams, one per quarter"}
    d, s = make_row(tmp_path, "c21-fold-cpu-20261124-r2", job=server_job(st, m, head=head), spec=spec)
    (d / "launch.sh").write_text("#!/bin/bash\n# taskset -c 0-71\n")
    assert "INTERLEAVE-CONCURRENT" in codes(run(s, d, "lane"), level="FAIL")
    (d / "job.py").write_text(server_job(st, m, head=head.replace("--interleave=all", "--membind=0")))
    assert "INTERLEAVE-CONCURRENT" not in codes(run(s, d, "lane"))


def test_served_v2_schema_rebuild_and_delta(tmp_path, monkeypatch):
    """mk_ak_row v2 served_ref: argv with {PORT}, argv_sha256, argv_delta[{flag, value, reason}]; rebuilt argv wins."""
    st, m = make_store(tmp_path), make_model(tmp_path)
    served = ["llama-server", "-m", str(m), "--port", "{PORT}", "-c", "32768", "-np", "2", "--slot-save-path", "{SLOTDIR}"]
    monkeypatch.setattr(P, "rebuild_served_argv", lambda *a: (list(served), None))
    job_argv = '"-c", "32768", "-np", "2", "--slot-save-path", SLOTS'
    d, s = make_row(tmp_path, "zz-v2-20261124", job=server_job(st, m, job_argv),
                    spec={"served_ref": {"registry_role": "worker", "port": 1, "argv": served,
                                         "argv_sha256": hashlib.sha256(json.dumps(served).encode()).hexdigest(),
                                         "argv_delta": []}})
    assert not codes(run(s, d, "served"))
    (d / "job.py").write_text(server_job(st, m, job_argv.replace('"32768"', '"36864"')))
    assert "SERVED-DELTA" in codes(run(s, d, "served"), level="FAIL")
    s["served_ref"]["argv_delta"] = [{"flag": "-c", "value": "36864", "reason": "fits the 32k prompt"}]
    assert not codes(run(s, d, "served"), level="FAIL")
    s["served_ref"]["argv_delta"] = [{"flag": "-c", "value": "36864"}]
    assert "SERVED-DELTA-UNREASONED" in codes(run(s, d, "served"), level="FAIL")
    s["served_ref"]["argv_delta"] = [{"flag": "-c", "value": "36864", "reason": "r"}]
    monkeypatch.setattr(P, "rebuild_served_argv", lambda *a: ([x if x != "2" else "4" for x in served], None))
    assert "SERVED-STALE" in codes(run(s, d, "served"), level="FAIL")       # the registry moved since generation
    s["served_ref"]["argv_sha256"] = "0" * 64
    assert "SERVED-ARGV-SHA" in codes(run(s, d, "served"), level="FAIL")


# ---------------------------------------------------------------- 12 generator (WARN only)
def test_generator_stamp_warn_only(tmp_path):
    d, s = make_row(tmp_path, "zz-gen-20261124")
    got = run(s, d, "generator")
    assert "GENERATOR-UNSTAMPED" in codes(got, level="WARN") and not codes(got, level="FAIL")
    (d / "ak_row_harness.py").write_text("# harness\n")
    hs = _sha(d / "ak_row_harness.py")
    (d / "job.py").write_text(f"# GENERATED-BY: mk_ak_row.py v2 harness_sha256={hs}\n" + SELFTEST_OK)
    s["generator"] = {"tool": "mk_ak_row.py", "version": "v2", "harness_sha256": hs}
    assert not codes(run(s, d, "generator"))
    s.pop("generator")
    assert not codes(run(s, d, "generator"))                                # the stamp alone is valid
    (d / "job.py").write_text(SELFTEST_OK)
    s["generator"] = {"tool": "mk_ak_row.py", "version": "v2", "harness_sha256": hs, "profile": "polar"}
    assert not codes(run(s, d, "generator"))                                # polar: spec.generator alone is valid
    s.pop("generator")
    (d / "job.py").write_text(f"# GENERATED-BY: mk_ak_row.py v2 harness_sha256={'1' * 64}\n" + SELFTEST_OK)
    got = codes(run(s, d, "generator"))
    assert {"GENERATOR-HARNESS", "GENERATOR-UNSTAMPED"} <= got and not codes(run(s, d, "generator"), level="FAIL")


# ---------------------------------------------------------------- AK lever-row gaps (ak-spec-copy-ngrammod-gpu-20261124)
def test_lane_region_wider_than_threads_is_warn_only(tmp_path):
    st, m = make_store(tmp_path), make_model(tmp_path)
    d, s = make_row(tmp_path, "zz-lev-20261124", job=server_job(st, m, '"-t", "8"'),
                    spec={"lane": "gpu", "regions": "mi210_0,88-95,184-191", "declared_threads": 16})
    got = run(s, d, "lane")
    assert "THREADS-DECLARED" in codes(got, level="WARN") and not codes(got, level="FAIL")
    (d / "job.py").write_text(server_job(st, m, '"-t", "32"'))
    assert "THREADS-OVERSUB" in codes(run(s, d, "lane"), level="FAIL")       # only -t > granted cpus fails


def _served(st, m):
    return [str(st / "bin" / "llama-server"), "-m", str(m), "--port", "{PORT}", "-c", "32768", "-t", "8"]


def test_store_keys_on_effective_argv0(tmp_path, monkeypatch):
    reg = make_store(tmp_path, name="gpu-20260921-ffc1bac82", sha="ffc1bac82")
    (reg / "BUILD-IDENTITY.json").unlink()                                  # the registry store: no identity
    cand = make_store(tmp_path, name="gpu-20261124-98ff8a42a-c21", sha="98ff8a42a00c")
    m = make_model(tmp_path)
    served = _served(reg, m)
    d, s = make_row(tmp_path, "zz-argv0-20261124", job=SELFTEST_OK + f"SERVER_ARGV = {served!r}\n",
                    spec={"served_ref": {"registry_role": "r", "argv": served, "argv_delta": [
                        {"flag": "argv[0]", "value": str(cand / "bin" / "llama-server"), "reason": "lever on C21"}]}})
    got = codes(run(s, d, "store"))
    assert "STORE-NO-IDENTITY" not in got and not codes(run(s, d, "store"), level="FAIL")
    (cand / "BUILD-IDENTITY.json").write_text(json.dumps({"source_sha": "0000000000"}))
    assert "STORE-COMMIT" in codes(run(s, d, "store"), level="FAIL")          # the binary it RUNS is checked
    s["served_ref"]["argv_delta"] = []
    assert "STORE-NO-IDENTITY" in codes(run(s, d, "store"))                   # no swap: the registry binary runs


def _arm_job(served, extras):
    return (SELFTEST_OK + f"SERVER_ARGV = {served!r}\nARM_EXTRA = {extras!r}\n"
            "def argv(arm):\n    return list(SERVER_ARGV) + ARM_EXTRA.get(arm, [])\n")


def test_served_arm_scoped_deltas(tmp_path, monkeypatch):
    st, m = make_store(tmp_path), make_model(tmp_path)
    served = _served(st, m)
    monkeypatch.setattr(P, "rebuild_served_argv", lambda *a: (list(served), None))
    ref = {"registry_role": "r", "argv": served, "argv_sha256": P.served_argv_sha256(served), "argv_delta": [
        {"arm": "ON", "flag": "--spec-ngram-mod-n-match", "value": "4", "reason": "lever arm"}]}
    d, s = make_row(tmp_path, "zz-arm-20261124", job=_arm_job(served, {"ON": ["--spec-ngram-mod-n-match", "4"]}),
                    spec={"served_ref": ref})
    assert not codes(run(s, d, "served"), level="FAIL")
    (d / "job.py").write_text(_arm_job(served, {"ON": ["--spec-ngram-mod-n-match", "4"], "OFF": ["--draft-p-min", "0.5"]}))
    assert "SERVED-DELTA" in codes(run(s, d, "served"), level="FAIL")          # an undeclared per-arm flag fails
    s["served_ref"]["argv_delta"] = [{"arm": "", "flag": "-c", "value": "1", "reason": "r"}]
    assert "SERVED-DELTA-SPEC" in codes(run(s, d, "served"), level="FAIL")


def test_served_legacy_arm_argv_delta(tmp_path, monkeypatch):
    st, m = make_store(tmp_path), make_model(tmp_path)
    served = _served(st, m)
    monkeypatch.setattr(P, "rebuild_served_argv", lambda *a: (list(served), None))
    d, s = make_row(tmp_path, "zz-leg-20261124", job=_arm_job(served, {"ON": ["--spec-ngram-mod-n-match", "4", "-c", "65536"]}),
                    spec={"served_ref": {"registry_role": "r", "argv": served, "argv_sha256": P.served_argv_sha256(served)},
                          "arm_argv_delta": {"ON": {"replace": {"-c": "65536"}, "append": ["--spec-ngram-mod-n-match", "4"]},
                                             "OFF": {}}})
    got = run(s, d, "served")
    assert "ARM-DELTA-LEGACY" in codes(got, level="WARN") and not codes(got, level="FAIL")


def test_mk_ak_row_arm_delta_rows_pass_check_11_per_arm(tmp_path, monkeypatch):
    import mk_ak_row as MK
    st, m = make_store(tmp_path), make_model(tmp_path)
    served = _served(st, m)
    monkeypatch.setattr(P, "rebuild_served_argv", lambda *a: (list(served), None))
    arms = {"ON": ["ON:--spec-ngram-mod-n-match=4:lever", "ON:--no-warmup"], "OFF": ["OFF:-c=65536:fits prompt"]}
    deltas = [MK.parse_arm_delta(x) for xs in arms.values() for x in xs]
    assert all(set(x) == {"arm", "flag", "value", "reason"} and x["reason"] for x in deltas)
    extras = {"ON": ["--spec-ngram-mod-n-match", "4", "--no-warmup"], "OFF": ["-c", "65536"]}
    for arm in arms:
        d, s = make_row(tmp_path / arm, f"zz-mk-{arm.lower()}-20261124", job=_arm_job(served, {arm: extras[arm]}),
                        spec={"served_ref": {"registry_role": "r", "argv": served,
                                             "argv_sha256": P.served_argv_sha256(served), "argv_delta": deltas}})
        assert not codes(run(s, d, "served"), level="FAIL"), arm
    with pytest.raises(SystemExit):
        MK.parse_arm_delta("noflag")


# ---------------------------------------------------------------- hooks + report
def test_publish_check_warns_then_refuses_only_when_enforced(tmp_path, monkeypatch):
    monkeypatch.setitem(P.PREFLIGHT_ENFORCE, "ports", False)
    d, s = make_row(tmp_path, "zz-pub-20261124", spec={"ports": [28001]})
    q = {"zz-b-20261124": {"id": "zz-b-20261124", "ports": [28001]}}
    seen = []
    P.publish_check(s, str(tmp_path), warn=seen.append, queued=q)
    assert any("PORT-CLASH" in w and "would FAIL" in w for w in seen)
    monkeypatch.setitem(P.PREFLIGHT_ENFORCE, "ports", True)
    with pytest.raises(rf.Refused):
        P.publish_check(s, str(tmp_path), warn=seen.append, queued=q)


def test_grant_check_drift_only_and_hold_when_enforced(tmp_path, monkeypatch):
    monkeypatch.setitem(P.PREFLIGHT_ENFORCE, "ports", False)
    d, s = make_row(tmp_path, "zz-grant-20261124", job="main()\n", spec={"ports": [28001]})
    q = {"zz-b-20261124": {"id": "zz-b-20261124", "ports": [28001]}}
    why, lines = P.grant_check(str(tmp_path), s["id"], s, queued=q)
    assert why is None and any("PORT-CLASH" in x for x in lines)
    assert not any("SELFTEST" in x for x in lines)                      # selftest is publish-only (sealed code)
    monkeypatch.setitem(P.PREFLIGHT_ENFORCE, "ports", True)
    why, _ = P.grant_check(str(tmp_path), s["id"], s, queued=q)
    assert why and "PORT-CLASH" in why


def test_rowflow_preflight_hold_never_raises(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("x")
    monkeypatch.setattr(P, "grant_check", boom)
    logs = []
    assert rf.preflight_hold(str(tmp_path), "zz", {}, logs.append) is None and "skipped" in logs[0]


def test_report_counts_fail_rows(tmp_path):
    d1, s1 = make_row(tmp_path, "zz-r1-20261124", spec={"ports": [28001]})
    d2, s2 = make_row(tmp_path, "zz-r2-20261124", spec={"ports": [28001]})
    d3, s3 = make_row(tmp_path, "zz-r3-20261124", spec={"ports": [28003]})
    lines = []
    per = P.report(str(tmp_path), out=lines.append, queued={s["id"]: s for s in (s1, s2, s3)})
    assert sorted(per["ports"]["fail"]) == ["zz-r1-20261124", "zz-r2-20261124"]
    assert any(x.startswith("ports") and "fail=  2" in x for x in lines)


# ---------------------------------------------------------------- inputs (2026-11-25, q8wp: kld_text.txt never copied)
KLD_SHA_JOB = SELFTEST_OK + "TEXT_SHA = %r\nTEXT = HERE + '/inputs/kld_text.txt'\n"


def _inputs_row(tmp_path, body=b"corpus", pin=None, put=True, rid="inp-row-20261125"):
    sha = hashlib.sha256(b"corpus").hexdigest() if pin is None else pin
    d, s = make_row(tmp_path, rid, job=KLD_SHA_JOB % sha)
    if put:
        (d / "inputs").mkdir()
        (d / "inputs" / "kld_text.txt").write_bytes(body)
    return d, s


def test_inputs_missing_fails(tmp_path):
    d, s = _inputs_row(tmp_path, put=False)
    r = run(s, d, "inputs")
    assert codes(r, "inputs", "FAIL") == {"INPUT-MISSING"} and "inputs/kld_text.txt" in r[0][3]


def test_inputs_wrong_sha_fails(tmp_path):
    d, s = _inputs_row(tmp_path, body=b"other")
    assert codes(run(s, d, "inputs"), "inputs", "FAIL") == {"INPUT-SHA"}


def test_inputs_present_right_sha_passes(tmp_path):
    d, s = _inputs_row(tmp_path)
    assert run(s, d, "inputs") == []


def test_inputs_sha256sums_pin(tmp_path):
    d, s = make_row(tmp_path, "inp-sums-20261125")
    (d / "data.bin").write_bytes(b"x")
    (d / "SHA256SUMS").write_text(f"{hashlib.sha256(b'x').hexdigest()}  data.bin\n{'0' * 64}  gone.txt\n")
    r = run(s, d, "inputs")
    assert codes(r, "inputs", "FAIL") == {"INPUT-MISSING"} and len(r) == 1


def test_inputs_none_pinned_no_check(tmp_path):
    d, s = make_row(tmp_path, "inp-none-20261125")
    assert run(s, d, "inputs") == []


def test_inputs_publish_only_grandfathered():
    assert "inputs" in P.PUBLISH_ONLY


def test_inputs_argv_hex_and_host_not_a_pin(tmp_path):
    job = SELFTEST_OK + ("SERVER_ARGV = ['llama-server', '--host', '127.0.0.1', '--port', '8080', "
                         "'--chat-template-sha', %r]\n" % ("ab" * 32))
    d, s = make_row(tmp_path, "inp-argv-20261125", job=job)
    assert run(s, d, "inputs") == []
    assert P.pinned_inputs(P.Row(s, str(d))) == {}
