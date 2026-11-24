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
    assert set(P.PREFLIGHT_ENFORCE) == set(P.CHECKS) and not any(P.PREFLIGHT_ENFORCE.values())
    assert set(P.DRIFT_CHECKS) <= set(P.CHECKS)


def test_effective_demotes_unless_enforced():
    raw = [("ports", "FAIL", "PORT-CLASH", "x"), ("lane", "WARN", "THREADS-DECLARED", "y")]
    assert [f[1] for f in P.effective(raw)] == ["WARN", "WARN"]
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
    (d / "job.py").write_text(server_job(str(st) + "-gone", str(m) + ".x.gguf"))
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


def test_lane_threads(tmp_path):
    st, m = make_store(tmp_path), make_model(tmp_path)
    head = SELFTEST_OK + "W = ['/usr/bin/taskset', '-c', '0-3']\n"
    d, s = make_row(tmp_path, "zz-thr-20261124", job=server_job(st, m, '"-t", "8"', head=head), spec={"declared_threads": 4})
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


# ---------------------------------------------------------------- 7 estimate
def test_estimate_accurate_off_and_borrowed(tmp_path):
    st = make_store(tmp_path)
    m = make_model(tmp_path, "Qwen3.8-27B-Q8_0.gguf")
    basis = {"units": 10, "unit_s": 100, "loads_s": 0, "margin": 1.25, "reason": "own smoke"}
    d, s = make_row(tmp_path, "zz-est-20261124", job=server_job(st, m),
                    spec={"estimate_s": 1250, "estimate_basis": basis, "shape": "q0"})
    assert not codes(run(s, d, "estimate"))
    s["estimate_s"] = 5000
    assert "ESTIMATE-OFF" in codes(run(s, d, "estimate"), level="WARN")
    other_m = make_model(tmp_path, "Qwen3.6-35B-A3B-Q8_0.gguf")
    make_row(tmp_path, "zz-src-20261123", job=server_job(st, other_m), spec={"shape": "q0"})
    s.update(estimate_s=1250, estimate_basis=dict(basis, reason="unit_s from zz-src-20261123 per-unit timing"))
    assert "BORROWED-BASIS" in codes(run(s, d, "estimate"), level="FAIL")
    make_row(tmp_path, "zz-same-20261123", job=server_job(st, m), spec={"shape": "q0"})
    s["estimate_basis"] = dict(basis, reason="unit_s from zz-same-20261123")
    assert "BORROWED-BASIS" in codes(run(s, d, "estimate"), level="WARN")
    assert "BORROWED-BASIS" not in codes(run(s, d, "estimate"), level="FAIL")


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
def test_regression_c21_gpu27b_identity(tmp_path):
    """Flash-Next declared as 27b; 8 host threads under expert offload; timing borrowed from a different-shaped row."""
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


# ---------------------------------------------------------------- hooks + report
def test_publish_check_warns_then_refuses_only_when_enforced(tmp_path, monkeypatch):
    d, s = make_row(tmp_path, "zz-pub-20261124", spec={"ports": [28001]})
    q = {"zz-b-20261124": {"id": "zz-b-20261124", "ports": [28001]}}
    seen = []
    P.publish_check(s, str(tmp_path), warn=seen.append, queued=q)
    assert any("PORT-CLASH" in w and "would FAIL" in w for w in seen)
    monkeypatch.setitem(P.PREFLIGHT_ENFORCE, "ports", True)
    with pytest.raises(rf.Refused):
        P.publish_check(s, str(tmp_path), warn=seen.append, queued=q)


def test_grant_check_drift_only_and_hold_when_enforced(tmp_path, monkeypatch):
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
