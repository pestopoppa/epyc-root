#!/usr/bin/env python3
"""2026-11-23 failure-audit checks in ak_row_lint / ak_row_harness / mk_ak_row (no compute; selftest is a stub script)."""
import io
import json
import os
import sys
import time

import pytest

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
import ak_row_harness as H  # noqa: E402
import ak_row_lint as LINT  # noqa: E402
import mk_ak_row as MK  # noqa: E402


def _row(tmp_path, rid="ak-t-20261123", job="x = 1\n", launch="", spec=None):
    d = tmp_path / rid
    d.mkdir()
    (d / "job.py").write_text(job)
    (d / "launch.sh").write_text(launch)
    (d / "spec.json").write_text(json.dumps(dict(spec or {}, id=rid)))
    return d


def codes(d, lvl=None, selftest=False):
    return {c for l, c, _ in LINT.lint_dir(str(d), selftest=selftest) if lvl is None or l == lvl}


def test_sha_cwd(tmp_path):
    d = _row(tmp_path, launch='D=%s\n/usr/bin/sha256sum --check --status SOURCE.sha256\n' % (tmp_path / "ak-t-20261123"))
    (d / "SOURCE.sha256").write_text("00  job.py\n")
    assert "SHA-CWD" in codes(d, "FAIL")                              # no cd: caller's cwd
    (d / "launch.sh").write_text('D=%s\ncd "$D"\n/usr/bin/sha256sum --check --status SOURCE.sha256\n' % d)
    assert "SHA-CWD" not in codes(d)
    (d / "BIN.sha256").write_text("00  bin/libx.so\n")
    (d / "launch.sh").write_text('D=%s\ncd "$D"\nsha256sum --check "$D/BIN.sha256"\n' % d)
    assert "SHA-CWD" in codes(d, "FAIL")                              # entries do not resolve from that cwd
    (d / "launch.sh").write_text('cd /\nsha256sum -c - <<<"x"\nsha256sum --check --status <<"P"\nP\n')
    assert "SHA-CWD" not in codes(d)                                  # stdin / heredoc lists skipped


def test_sealed_spec(tmp_path):
    d = _row(tmp_path)
    (d / "SOURCE.sha256").write_text("00  job.py\n11  spec.json\n")
    assert "SEALED-SPEC" in codes(d, "FAIL")
    (d / "SOURCE.sha256").write_text("00  job.py\n")
    assert "SEALED-SPEC" not in codes(d)


def test_stale_out(tmp_path):
    d = _row(tmp_path)
    for sub in ("out", "out-smoke"):
        (d / sub).mkdir()
        (d / sub / "RESULT.json").write_text("{}")
        os.utime(d / sub / "RESULT.json", (time.time() - 100, time.time() - 100))
    (d / "out-smoke" / "stale-1").mkdir()
    (d / "out-smoke" / "stale-1" / "x").write_text("")
    os.utime(d / "out-smoke" / "stale-1" / "x", (1, 1))
    (d / "SOURCE.sha256").write_text("00  job.py\n")
    r = [m for _, c, m in LINT.lint_dir(str(d), selftest=False) if c == "STALE-OUT"]
    assert len(r) == 2 and not any("stale-1" in m for m in r)


def test_server_no_trap(tmp_path):
    d = _row(tmp_path, job="import subprocess\np = subprocess.Popen(['llama-server', '-m', 'x'])\n")
    (d / "srv.sh").write_text("#!/bin/bash\nllama-server -m x --port 1 &\nwait\n")
    r = [m for _, c, m in LINT.lint_dir(str(d), selftest=False) if c == "SERVER-NO-TRAP"]
    assert len(r) == 2
    (d / "job.py").write_text("import subprocess, atexit\np = subprocess.Popen(['llama-server'])\natexit.register(p.kill)\n")
    (d / "srv.sh").write_text("#!/bin/bash\ntrap 'kill $S' EXIT\nllama-server -m x &\nS=$!\nwait\n")
    assert "SERVER-NO-TRAP" not in codes(d)


def test_py_compile_and_selftest(tmp_path):
    d = _row(tmp_path, job="def f(:\n")
    assert "PY-COMPILE" in codes(d, "FAIL")
    (d / "job.py").write_text("import sys\nif '--selftest' in sys.argv: sys.exit(2)\n")
    assert "SELFTEST" in codes(d, "FAIL", selftest=True)
    assert "SELFTEST" not in codes(d, selftest=False)
    (d / "job.py").write_text("import sys\nif '--selftest' in sys.argv: sys.exit(0)\n")
    assert "SELFTEST" not in codes(d, selftest=True)


def test_claim_parse(tmp_path):
    d = _row(tmp_path, launch='W=$(printf %s "$WS58_REGIONS" | tr , "\\n" | grep -E "^[0-9]" | paste -sd, -)\n')
    assert "CLAIM-PARSE" in codes(d, "FAIL")
    (d / "launch.sh").write_text('C=${WS58_CPUS:-184-191}\nexec f --claim-cpus "$C" --role bench\n')
    assert "CLAIM-PARSE" not in codes(d)


def test_claim_parse_rejects_non_digit_claim(tmp_path):
    d = _row(tmp_path, launch='C=${WS58_CPUS:-any-of q0,q1,q2}\nexec f --claim-cpus "$C" --role bench\n')
    assert "CLAIM-PARSE" in codes(d, "FAIL")                          # the C= default
    (d / "launch.sh").write_text('exec f --claim-cpus "any-of q0,q1" --role bench\n')
    assert "CLAIM-PARSE" in codes(d, "FAIL")                          # a literal --claim-cpus
    (d / "launch.sh").write_text('exec f --claim-cpus 0-3,8 --role bench\n')
    assert "CLAIM-PARSE" not in codes(d)
    (d / "launch.sh").write_text('exec f --class cpu --role bench\n')   # no claim at all (grant default)
    assert "CLAIM-PARSE" not in codes(d)


def test_sha_cwd_job_py(tmp_path):
    d = _row(tmp_path)
    store = tmp_path / "store"
    (store / "bin").mkdir(parents=True)
    (store / "bin" / "llama-server").write_text("x")
    (store / "BIN.sha256").write_text("00  bin/llama-server\n")
    job = ("import subprocess\nSTORE = %r\nBIN = STORE + '/bin'\n"
           "subprocess.run(['/usr/bin/sha256sum', '--check', '--status', STORE + '/BIN.sha256'], cwd=%s)\n")
    (d / "job.py").write_text(job % (str(store), "BIN"))
    assert "SHA-CWD" in codes(d, "FAIL")                              # bin/llama-server does not resolve from store/bin
    (d / "job.py").write_text(job % (str(store), "STORE"))
    assert "SHA-CWD" not in codes(d)
    (d / "job.py").write_text("import subprocess, os\nsubprocess.run(['sha256sum', '--check', os.environ['L']], cwd=os.environ['C'])\n")
    assert "SHA-CWD" in codes(d, "WARN") and "SHA-CWD" not in codes(d, "FAIL")


def test_quiet_guard_regex_ignores_contended_verdict_names(tmp_path):
    d = _row(tmp_path, job="VERDICTS = ['KEEP', 'DROP', 'CONTENDED-INCONCLUSIVE', 'contended']\n")
    assert "QUIET-NO-BACKOFF" not in codes(d)
    (d / "job.py").write_text("ref = bench_readbw()\n")
    assert "QUIET-NO-BACKOFF" in codes(d, "FAIL")


def test_smoke_warns(tmp_path):
    d = _row(tmp_path, job="import os\nS = os.environ.get('FILLER_SMOKE')\n")
    assert {"SMOKE-FAIL-SILENT", "SMOKE-NO-MEASURE"} <= codes(d, "WARN")
    (d / "job.py").write_text("import os\nS = os.environ.get('FILLER_SMOKE')\nH.write_smoke_measure(o, 1, 1, 0)\n"
                              "H.end_smoke('PASS', 0, 'ok', o)\n")
    assert not codes(d) & {"SMOKE-FAIL-SILENT", "SMOKE-NO-MEASURE"}


def test_no_witness_and_replay_baseline(tmp_path):
    d = _row(tmp_path, rid="ak-rsreplay-t-20261123", spec={"decision_rule": "KEEP iff GGML_HIP_FOO=1 is faster"})
    assert {"NO-WITNESS", "REPLAY-NO-BASELINE"} <= codes(d, "WARN")
    (d / "job.py").write_text("res = {'witness': w, 'baseline_ok': b}\n")
    assert not codes(d) & {"NO-WITNESS", "REPLAY-NO-BASELINE"}
    assert LINT.main(["--no-selftest", str(d)]) == 0                  # WARN never fails the exit code


def test_end_smoke(tmp_path):
    buf = io.StringIO()
    assert H.end_smoke("fail", 3, "", tmp_path, stream=buf) == 3
    rec = json.loads((tmp_path / "TERMINAL-smoke.json").read_text())
    assert rec["verdict"] == "FAIL" and rec["rc"] == 3 and not rec["ok"] and rec["reason"].startswith("UNSPECIFIED")
    assert "SMOKE FAIL rc=3" in buf.getvalue()
    H.end_smoke("PASS", 0, "1 unit", tmp_path, stream=buf)
    assert json.loads((tmp_path / "TERMINAL-smoke.json").read_text())["ok"] is True


def test_mk_ak_row_scaffold_is_lint_clean(tmp_path):
    rid = "ak-mk-gdn-gpu-20261124-r2"
    assert MK.main(["--id", rid, "--task", "x.md:T", "--rule", "KEEP iff GGML_HIP_X faster", "--knob", "GGML_HIP_X",
                    "--lane", "gpu", "--servers", "2", "--root", str(tmp_path)]) == 0
    d = tmp_path / rid
    assert (d / "spec.json").exists()
    assert "spec.json" not in (d / "SOURCE.sha256").read_text()
    launch = (d / "launch.sh").read_text()
    assert "C=${WS58_CPUS:-" in launch and 'cd "$D"' in launch
    assert ",".join(map(str, H.expected_ports(rid, 2))) in launch
    # estimate_basis comes from the smoke, so ESTIMATE-UNMEASURED is the only expected FAIL before it
    assert [r[1] for r in LINT.lint_dir(str(d)) if r[0] == "FAIL"] == ["ESTIMATE-UNMEASURED"]   # incl. --selftest


def test_mk_ak_row_cpu_default_has_no_claim(tmp_path):
    rid = "ak-mk-cpu-20261124"
    assert MK.main(["--id", rid, "--task", "t", "--rule", "r", "--lane", "cpu", "--root", str(tmp_path)]) == 0
    launch = (tmp_path / rid / "launch.sh").read_text()
    assert "C=" not in launch and "--claim-cpus" not in launch and "any-of" not in launch
    assert "--class cpu --role bench" in launch
    rid2 = "ak-mk-cpu2-20261124"
    assert MK.main(["--id", rid2, "--task", "t", "--rule", "r", "--claim", "0-3,8", "--root", str(tmp_path)]) == 0
    assert "C=${WS58_CPUS:-0-3,8}" in (tmp_path / rid2 / "launch.sh").read_text()
    for bad in ("any-of q0,q1,q2", "q0", "1-", ""):
        with pytest.raises(SystemExit):
            MK.main(["--id", "ak-mk-bad2-20261124", "--task", "t", "--rule", "r", "--claim", bad,
                     "--root", str(tmp_path)])


def test_reseal_preserves_extra_sealed_files(tmp_path):
    rid = "ak-mk-reseal-20261124"
    assert MK.main(["--id", rid, "--task", "t", "--rule", "r", "--root", str(tmp_path)]) == 0
    d = tmp_path / rid
    for n in ("own_port_proof.py", "lp_common.py"):
        (d / n).write_text("x = 1\n")
    sums = (d / "SOURCE.sha256")
    sums.write_text(sums.read_text() + "".join(f"{MK._sha(str(d / n))}  {n}\n" for n in ("own_port_proof.py", "lp_common.py"))
                    + "00  spec.json\n00  gone.py\n")
    MK.main(["--reseal", str(d)])
    names = [ln.split()[1] for ln in sums.read_text().splitlines()]
    assert {"own_port_proof.py", "lp_common.py", "job.py", "check_complete.py", "launch.sh", "ak_row_harness.py"} <= set(names)
    assert "spec.json" not in names and "gone.py" not in names
    (d / "lp_common.py").write_text("x = 2\n")
    MK.main(["--reseal", str(d)])
    assert f"{MK._sha(str(d / 'lp_common.py'))}  lp_common.py" in sums.read_text()


def test_server_stays_in_job_session_and_kill_tree_reaps_children(tmp_path):
    import subprocess
    job = MK.JOB
    assert "start_new_session" not in job and "killpg" not in job and "H.kill_tree(p)" in job
    # a "server" that forks a child; same session/pgrp as this test process, as the template now starts it
    p = subprocess.Popen(["/bin/sh", "-c", "sleep 300 & sleep 300 & wait"])
    time.sleep(0.5)
    assert os.getsid(p.pid) == os.getsid(0) and os.getpgid(p.pid) == os.getpgid(0)
    kids = H.descendants(p.pid)
    assert len(kids) >= 2
    assert H.kill_tree(p, term_wait=5) == []
    assert p.poll() is not None
    assert not [k for k in kids if os.path.exists(f"/proc/{k}") and not open(f"/proc/{k}/stat").read().split(")")[-1].split()[0] == "Z"]


def test_mk_ak_row_refuses_existing_and_withholds_spec_on_fail(tmp_path, monkeypatch):
    rid = "ak-mk-bad-20261124"
    monkeypatch.setattr(MK, "lint", lambda d: [("FAIL", "X", "y")])
    assert MK.main(["--id", rid, "--task", "t", "--rule", "r", "--root", str(tmp_path)]) == 1
    assert not (tmp_path / rid / "spec.json").exists()
    try:
        MK.main(["--id", rid, "--task", "t", "--rule", "r", "--root", str(tmp_path)])
        raise AssertionError("expected refusal")
    except SystemExit as e:
        assert "exists" in str(e)


if __name__ == "__main__":
    raise SystemExit("REFUSING: pytest-fixture suite; run: python -m pytest scripts/coordination/tests/test_ak_row_audit.py -q")


def test_provisional_estimate_basis(tmp_path):
    import pytest
    prov = {"provisional": True, "reason": "pre-smoke", "rebook_from": "out-smoke/smoke_measure.json"}
    d = _row(tmp_path, spec={"estimate_s": 2400, "estimate_basis": prov})
    assert "ESTIMATE-PROVISIONAL" in codes(d, "WARN")
    assert "ESTIMATE-UNMEASURED" not in codes(d)
    # smoke measurement now exists: a provisional basis must FAIL (re-book required)
    (d / "out-smoke").mkdir()
    (d / "out-smoke" / "smoke_measure.json").write_text("{}")
    assert "ESTIMATE-UNMEASURED" in codes(d, "FAIL")
    assert "ESTIMATE-PROVISIONAL" not in codes(d)
    # GPU publication rebooks from a fresh smoke or an identity-bound PASS, not this old file.
    gpu = {"id": "ak-t-20261123", "lane": "gpu", "estimate_s": 2400, "estimate_basis": prov}
    assert H.check_spec_estimate(gpu, base_dir=str(d))[1][0].startswith("ESTIMATE-PROVISIONAL")
    (d / "spec.json").write_text(json.dumps(gpu))
    assert "ESTIMATE-PROVISIONAL" in codes(d, "WARN")
    assert "ESTIMATE-UNMEASURED" not in codes(d, "FAIL")
    # missing reason / rebook_from fails
    d2 = _row(tmp_path, rid="ak-t2-20261123", spec={"estimate_s": 5, "estimate_basis": {"provisional": True}})
    assert "ESTIMATE-UNMEASURED" in codes(d2, "FAIL")
    # non-dict basis fails cleanly (no AttributeError)
    with pytest.raises(ValueError):
        H.check_spec_estimate({"estimate_s": 5, "estimate_basis": "out-smoke/smoke_measure.json"})
    d3 = _row(tmp_path, rid="ak-t3-20261123", spec={"estimate_s": 5, "estimate_basis": "x"})
    assert "ESTIMATE-UNMEASURED" in codes(d3, "FAIL")
    # dict form still works
    m = H.write_smoke_measure(tmp_path / "sm", 10.0, 2, 120)
    assert H.check_spec_estimate({"estimate_s": 350, "estimate_basis": {"smoke_measure": m, "units": 16}}) == (350, [])
