#!/usr/bin/env python3
"""mk_ak_row v2 (RCA ak-row-robustness-rca-20261124 F1/F2): harness helpers, stamped template, production-argv smoke,
--served-ref, and the row_scaffold.py shim. No compute: no server, no model, the registry resolver is stubbed."""
import json
import os
import subprocess
import sys

import pytest

_TESTS = os.path.dirname(os.path.abspath(__file__))
_ROWFLOW = os.path.join(os.path.dirname(_TESTS), "rowflow")
sys.path.insert(0, _ROWFLOW)
import ak_row_harness as H  # noqa: E402
import mk_ak_row as MK  # noqa: E402

_SKILL = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(_TESTS))), ".claude", "skills", "row-owner-loop",
                      "scripts")
sys.path.insert(0, _SKILL)
import row_scaffold as RS  # noqa: E402


# ------------------------------------------------------------------------------------------------ harness helpers
def test_append_unit_appends_one_line_per_unit(tmp_path):
    H.append_unit({"unit": 0, "v": 1.5}, tmp_path)
    H.append_unit({"unit": 1, "v": 2.5}, tmp_path)
    rows = [json.loads(x) for x in (tmp_path / "results.jsonl").read_text().splitlines()]
    assert [r["unit"] for r in rows] == [0, 1] and all(r["utc"] for r in rows)


def test_grant_cpus_one_env_source():
    assert H.grant_cpus({"WS58_CPUS": "0-3,8", "FILLER_CPUS": "50"}) == [0, 1, 2, 3, 8]
    assert H.grant_cpus({"FILLER_CPUS": "10-11"}) == [10, 11]
    assert H.grant_cpus({}, default="4-5") == [4, 5]
    with pytest.raises(RuntimeError):
        H.grant_cpus({"WS58_REGIONS": "q0"})   # never parsed out of WS58_REGIONS
    with pytest.raises(ValueError):
        H.grant_cpus({"WS58_CPUS": "q0"})


def test_bench_json_tolerates_interleaved_stderr(tmp_path):
    text = ("ggml_cuda_init: found 1 ROCm devices:\n[\n  {\"model_type\": \"qwen\", \"n_gen\": 128, \"avg_ts\": 41.2}"
            ",\n  {\"model_type\": \"qwen\", \"n_prompt\": 512, \"avg_ts\": 900.0}\n]\nload_backend: loaded CPU {weird\n"
            "{\"model_type\": \"qwen\", \"n_gen\": 64, \"avg_ts\": 40.0}\n")
    p = tmp_path / "bench.json"
    p.write_text(text)
    for src in (str(p), p, text):
        r = H.bench_json(src)
        assert [x["avg_ts"] for x in r] == [41.2, 900.0, 40.0]
    assert H.bench_json("no json here") == []


def test_require_grant_exits_without_filler_env():
    codes = []
    assert H.require_grant({"FILLER_ID": "row-x"}, exit=codes.append) is True
    assert H.require_grant({"FILLER_DRYRUN": "1"}, exit=codes.append) is True
    assert H.require_grant({}, stream=open(os.devnull, "w"), exit=codes.append) is False and codes == [64]


def test_tbo_cases_header_to_header():
    out = ("Testing 1 devices\n"
           "  MUL_MAT(type_a=q4_K,type_b=f32,m=16,n=1,k=256): OK\n"
           "  MUL_MAT(type_a=q8_0,type_b=f32,m=16,n=1,k=256): [MUL_MAT] NMSE = 0.5 > 0.0005 FAIL\n"
           "    ggml_backend: some log line\n"
           "  FLASH_ATTN_EXT(hs=128,nh=8): not supported [CPU]\n"
           "  2/3 tests passed\n")
    c = H.tbo_cases(out)
    assert [x["op"] for x in c] == ["MUL_MAT", "MUL_MAT", "FLASH_ATTN_EXT"]
    assert [x["ok"] for x in c] == [True, False, None]
    assert "    ggml_backend: some log line" in c[1]["lines"]


# ------------------------------------------------------------------------------------------------ generator v2
SERVED = {"registry_role": "frontdoor", "port": 8070, "argv": ["/x/llama-server", "-m", "/m.gguf", "--port", "{PORT}",
          "--slot-save-path", "{SLOTDIR}", "-t", "96"], "argv_sha256": "ab", "argv_delta": [], "serving_shape": {},
          "registry_sha256": "cd", "orchestrator_commit": "ef", "orchestrator_dirty": False, "resolved_utc": "t",
          "resolver": "stub"}


def _mk(tmp_path, rid, extra=(), served=None, monkeypatch=None):
    if served is not None:
        monkeypatch.setattr(MK, "resolve_served", lambda role, repo=None: dict(served, registry_role=role))
    assert MK.main(["--id", rid, "--task", "x.md:T", "--rule", "KEEP iff faster", "--root", str(tmp_path), *extra]) == 0
    d = tmp_path / rid
    return d, json.loads((d / "spec.json").read_text()), (d / "job.py").read_text()


@pytest.mark.parametrize("profile", ["default", "polar"])
def test_gpu_scaffold_regions_pass_publish_check(tmp_path, monkeypatch, profile):
    import publish_row as PR
    import rowflow as rf
    monkeypatch.setattr(rf, "TMP", str(tmp_path) + "/")
    monkeypatch.setenv("ROWFLOW_NO_VIEW_REFRESH", "1")
    flags = tmp_path / "flags"
    flags.mkdir()
    if profile == "default":
        _, spec, _ = _mk(tmp_path, "ak-default-gpu-20261125", ["--lane", "gpu"])
    else:
        args = ["new", "ak-polar-gpu-20261125", "--handoff", "x.md", "--box", "T", "--lane", "gpu",
                "--regions", "88-95", "--threads", "8", "--units", "1", "--unit-s", "400", "--model", "X",
                "--root", str(tmp_path)]
        assert MK.polar_main(args, fetch=lambda *a: ("abc", {"gpu_common.py": b"", "gpuproof_row.py": b""})) == 0
        spec = json.loads((tmp_path / "ak-polar-gpu-20261125" / "spec.json").read_text())
    assert spec["regions"] == "mi210_0,88-95,184-191"
    assert spec["claim_cpus"] == MK.GPU_HOST_CLAIM
    refusals = PR.rehearse(spec, str(flags))
    assert not any("gpu regions must name mi210_0" in item for _, item, _ in refusals)


def test_v2_stamp_predicate_and_selftest_runs_smoke(tmp_path):
    d, spec, job = _mk(tmp_path, "ak-v2-stamp-cpu-20261124")
    assert f"# GENERATED-BY: mk_ak_row.py {MK.GEN_VERSION} harness_sha256={MK.harness_sha()}" in job
    assert spec["generator"]["tool"] == "mk_ak_row.py" and spec["generator"]["harness_sha256"] == MK.harness_sha()
    assert "served_ref" not in spec and "SERVER_ARGV = []" in job
    assert "H.require_grant()" in job and "start_production_server(port)" in job and "H.grant_cpus()" in job
    # --selftest drives smoke() itself against the stub (rc 0) and leaves nothing in the row dir
    p = subprocess.run([sys.executable, "-I", "-B", str(d / "job.py"), "--selftest"], capture_output=True, text=True,
                       env={"PATH": "/usr/bin:/bin"})
    assert p.returncode == 0, p.stderr
    assert not (d / "out").exists() and not (d / "out-smoke").exists()


def test_v2_job_refuses_to_run_by_hand(tmp_path):
    d, _, _ = _mk(tmp_path, "ak-v2-hand-cpu-20261124")
    p = subprocess.run([sys.executable, "-I", "-B", str(d / "job.py")], capture_output=True, text=True,
                       env={"PATH": "/usr/bin:/bin"})
    assert p.returncode == 64 and "REFUSED" in p.stderr


def _pred(spec, env):
    return subprocess.run(["/bin/bash", "-c", spec["smoke_predicate"]], env=env, capture_output=True).returncode


def test_v2_smoke_predicate_needs_ok_and_this_run(tmp_path):
    d, spec, _ = _mk(tmp_path, "ak-v2-pred-cpu-20261124")
    out = d / "out"
    t0 = 2_000_000_000
    env = {"PATH": "/usr/bin:/bin", "FILLER_SMOKE_T0": str(t0)}
    assert _pred(spec, env) != 0                                   # nothing yet (publish preflight requires this)
    H.end_smoke("FAIL", 3, "x", out, stream=open(os.devnull, "w"))
    os.utime(out / H.TERMINAL_SMOKE, (t0 + 5, t0 + 5))
    assert _pred(spec, env) != 0                                   # ok:false
    H.end_smoke("PASS", 0, "1 unit", out, stream=open(os.devnull, "w"))
    os.utime(out / H.TERMINAL_SMOKE, (t0 - 5, t0 - 5))
    assert _pred(spec, env) != 0                                   # stale: older than this launch
    os.utime(out / H.TERMINAL_SMOKE, (t0 + 5, t0 + 5))
    assert _pred(spec, env) == 0
    assert _pred(spec, {"PATH": "/usr/bin:/bin"}) != 0            # T0 unset fails closed


def test_v2_served_ref_emits_registry_argv(tmp_path, monkeypatch):
    d, spec, job = _mk(tmp_path, "ak-v2-served-cpu-20261124", ["--served-ref", "frontdoor"], SERVED, monkeypatch)
    assert spec["served_ref"]["registry_role"] == "frontdoor" and spec["served_ref"]["argv"] == SERVED["argv"]
    assert f"SERVER_ARGV = {SERVED['argv']!r}" in job


def test_v2_served_argv_retarget(tmp_path, monkeypatch):
    d, _, _ = _mk(tmp_path, "ak-v2-retarget-cpu-20261124", ["--served-ref", "frontdoor"], SERVED, monkeypatch)
    code = ("import sys; sys.argv=['x']; sys.path.insert(0, %r); import job; "
            "print(job.server_argv(27123))") % str(d)
    p = subprocess.run([sys.executable, "-B", "-c", code], capture_output=True, text=True, cwd=str(d))
    assert p.returncode == 0, p.stderr
    argv = eval(p.stdout.strip())   # noqa: S307 - our own printed list
    assert argv[argv.index("--port") + 1] == "27123"
    assert argv[argv.index("--slot-save-path") + 1] == str(d / "out" / "kv_slots")


def test_resolve_served_placeholders(monkeypatch):
    class P:
        def __init__(self, out, rc=0):
            self.stdout, self.stderr, self.returncode = out, "", rc
    line = "RESOLVED " + json.dumps({"argv": ["/b/llama-server", "--port", "27999", "--slot-save-path", "/prod/kv"],
                                     "serving_shape": {"n_ctx": 1}, "port": 8070, "registry_sha256": "r"})
    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        return P(line) if cmd[0] == sys.executable else P("abc\n" if "rev-parse" in cmd else "")
    monkeypatch.setattr(subprocess, "run", fake_run)
    r = MK.resolve_served("frontdoor", repo="/nonexistent")
    assert r["argv"] == ["/b/llama-server", "--port", "{PORT}", "--slot-save-path", "{SLOTDIR}"]
    assert {x["flag"] for x in r["argv_delta"]} == {"--port", "--slot-save-path"}
    assert r["port"] == 8070 and r["orchestrator_commit"] == "abc" and r["serving_shape"] == {"n_ctx": 1}
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: P("", 1))
    with pytest.raises(SystemExit):
        MK.resolve_served("nope", repo="/nonexistent")


# ------------------------------------------------------------------------------------------------ row_scaffold shim
def test_row_scaffold_is_a_shim_over_mk_ak_row():
    assert RS.lint is MK.polar_lint and RS.seal is MK.polar_seal and RS.JOB_T is MK.JOB_T
    assert "RETIRED" in RS.__doc__
    assert len(open(RS.__file__).read().splitlines()) < 80


def test_shim_new_cpu_row_is_stamped(tmp_path):
    hf = tmp_path / "h.md"
    hf.write_text("- [ ] **BOX-9** do it · model: X · stop: futility · est 100 s\n")
    rc = RS.main(["new", "row-shim", "--handoff", str(hf), "--box", "BOX-9", "--lane", "cpu", "--regions", "0-23",
                  "--threads", "24", "--units", "4", "--unit-s", "10", "--model", "X", "--root", str(tmp_path)])
    assert rc == 0
    spec = json.loads((tmp_path / "row-shim" / "spec.json").read_text())
    assert spec["generator"]["tool"] == "mk_ak_row.py" and spec["generator"]["profile"] == "polar"
    assert MK.main(["polar", "--lint", str(tmp_path / "row-shim"), "--box-file", str(hf)]) in (0, 1)


def test_shim_fetch_harness_monkeypatch_still_applies(tmp_path, monkeypatch):
    monkeypatch.setattr(RS, "fetch_harness", lambda repo, ref="origin/main": "stubbed refusal")
    hf = tmp_path / "h.md"
    hf.write_text("x")
    assert RS.main(["new", "row-g", "--handoff", str(hf), "--box", "B", "--lane", "gpu", "--regions", "88-95",
                    "--threads", "8", "--units", "1", "--unit-s", "1", "--model", "X", "--root", str(tmp_path)]) == 1
    assert not (tmp_path / "row-g").exists()


def test_knob_row_adds_witness_loglevel(tmp_path, monkeypatch):
    d, spec, job = _mk(tmp_path, "ak-v2-knoblv-cpu-20261124", ["--served-ref", "frontdoor", "--knob", "GGML_TEST_KNOB"], SERVED, monkeypatch)
    ref = spec["served_ref"]
    assert ref["argv"][-2:] == ["-lv", "4"]
    assert {"flag": "-lv", "value": "4", "reason": "witness log level"} in ref["argv_delta"]
    import hashlib
    assert ref["argv_sha256"] == hashlib.sha256(json.dumps(ref["argv"]).encode()).hexdigest()


def test_knob_row_keeps_explicit_lv_and_no_knob_no_lv(tmp_path, monkeypatch):
    served = dict(SERVED, argv=SERVED["argv"] + ["--verbosity", "5"])
    _, spec, _ = _mk(tmp_path, "ak-v2-knoblv2-cpu-20261124", ["--served-ref", "frontdoor", "--knob", "GGML_K"], served, monkeypatch)
    assert spec["served_ref"]["argv"] == served["argv"]
    _, spec, _ = _mk(tmp_path, "ak-v2-noknob-cpu-20261124", ["--served-ref", "frontdoor"], SERVED, monkeypatch)
    assert "-lv" not in spec["served_ref"]["argv"]


def test_kld_unit_knob_row_emits_lv4_delta_and_smoke_witness(tmp_path, monkeypatch):
    d, spec, job = _mk(tmp_path, "ak-v2-kld-gpu-20261125", ["--served-ref", "frontdoor", "--knob", "GGML_TEST_KNOB", "--kld-unit"],
                       SERVED, monkeypatch)
    assert "KLD_LV = ['-lv', '4']" in job and "*KLD_LV" in job
    assert spec["tool_argv_delta"] == [{"tool": "llama-perplexity", "flag": "-lv", "value": "4", "reason": "witness log level"}]
    assert "kld_witness_check()" in job and "ctx=128, chunks=1" in job and "timeout=55" in job
    p = subprocess.run([sys.executable, "-I", "-B", str(d / "job.py"), "--selftest"], capture_output=True, text=True,
                       env={"PATH": "/usr/bin:/bin"})
    assert p.returncode == 0, p.stderr


def test_kld_unit_without_knob_has_no_lv_and_no_kld_flag_no_block(tmp_path):
    _, spec, job = _mk(tmp_path, "ak-v2-kld2-gpu-20261125", ["--kld-unit"])
    assert "KLD_LV = []" in job and "tool_argv_delta" not in spec
    _, spec, job = _mk(tmp_path, "ak-v2-nokld-gpu-20261125", [])
    assert "KLD_BIN" not in job and "kld_witness_check" not in job
