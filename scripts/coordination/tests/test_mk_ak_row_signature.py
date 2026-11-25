#!/usr/bin/env python3
"""mk_ak_row --profile signature (AK-BNSIG P1): scaffold lints, the vendored classifier is sealed, the job selftest
passes, futility is the harness-stop custom form and passes the publish futility check. No compute."""
import json
import os
import subprocess
import sys

import pytest

_TESTS = os.path.dirname(os.path.abspath(__file__))
_ROWFLOW = os.path.join(os.path.dirname(_TESTS), "rowflow")
sys.path.insert(0, _ROWFLOW)
import mk_ak_row as MK  # noqa: E402

RESEARCH = "/mnt/raid0/llm/worktrees/f2-bnsig-research/" + MK.SIG_MODULE_PATH


def _module():
    for p in (RESEARCH, os.path.join(MK.RESEARCH_REPO, MK.SIG_MODULE_PATH)):
        if os.path.isfile(p):
            return open(p, "rb").read()
    pytest.skip("bottleneck_signature.py not available on this host")


def _mk(tmp_path, rid="ak-bnsig-test-gpu-20261125", extra=()):
    mod = _module()
    stream = tmp_path / "stream2.hip"
    stream.write_text("// stub stream2 source\n")
    args = ["--profile", "signature", rid, "--task", "x.md:BOX", "--kernel", "q8mf6_mul_mat:70041600",
            "--kernel", "q8wt_mul_mat:70041600", "--workload", "/bin/true perf -o MUL_MAT", "--root", str(tmp_path),
            "--stream-src", str(stream), *extra]
    saved = MK.fetch_signature_module
    MK.fetch_signature_module = lambda repo, ref: ("deadbeef", mod)   # routed through main(--profile signature)
    try:
        rc = MK.main(args)
    finally:
        MK.fetch_signature_module = saved
    return rc, tmp_path / rid


def test_signature_profile_scaffold_lints(tmp_path):
    rc, d = _mk(tmp_path)
    assert rc == 0
    spec = json.loads((d / "spec.json").read_text())
    assert spec["generator"]["profile"] == "signature" and spec["generator"]["research_commit"] == "deadbeef"
    assert spec["lane"] == "gpu" and spec["regions"] == "mi210_0," + MK.GPU_HOST_CLAIM
    sealed = (d / "SOURCE.sha256").read_text()
    for n in ("job.py", "bottleneck_signature.py", "stream2.hip", "ak_row_harness.py", "launch.sh"):
        assert f"  {n}\n" in sealed, n
    assert "spec.json" not in sealed
    job = (d / "job.py").read_text()
    assert "@@" not in job and "q8mf6_mul_mat" in job and "profile=signature" in job
    assert not MK.lint(str(d))


def test_signature_futility_rule_filled_and_passes_publish_check(tmp_path):
    import publish_row as PR
    _rc, d = _mk(tmp_path)
    spec = json.loads((d / "spec.json").read_text())
    fut = spec["futility"]
    assert fut["rule"].startswith("custom: ") and "FUTILITY_REFERENCE_INCOHERENT" in fut["rule"]
    assert fut["custom_reason"] and "KEEP" in fut["custom_reason"]   # "no KEEP decision"
    assert PR.futility_missing(spec) is None


def test_signature_selftest_passes(tmp_path):
    _rc, d = _mk(tmp_path)
    p = subprocess.run([sys.executable, "-I", "-B", str(d / "job.py"), "--selftest"], capture_output=True, text=True,
                       env={"PATH": "/usr/bin:/bin"}, timeout=60)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "selftest ok" in p.stdout and not (d / "out-smoke").exists()


def _job(d):
    sys.path.insert(0, str(d))
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("sigjob_" + d.name.replace("-", "_"), d / "job.py")
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m
    finally:
        sys.path.remove(str(d))


def test_signature_futility_on_incoherent_refs(tmp_path):
    _rc, d = _mk(tmp_path)
    J = _job(d)
    assert J.decide(J.synth()) == "SIGNATURE_CLASSIFIED"
    assert J.decide(J.synth(s16=J.REF64, s64=J.REF16)) == "FUTILITY_REFERENCE_INCOHERENT"
    assert J.polar("FUTILITY_REFERENCE_INCOHERENT") is None


def test_signature_witness_missing_kernel(tmp_path):
    _rc, d = _mk(tmp_path)
    J = _job(d)
    assert J.trace_record(1, 0, [{"Kernel_Name": "other_kernel", "Start_Timestamp": "0", "End_Timestamp": "9"}])["witness"]["ok"] is False
    units = [dict(u, witness={"ok": False}) if u.get("kind") == "trace" and u["i"] == 1 else u for u in J.synth()]
    assert J.decide(units) == "FUTILITY_HARNESS_NOT_RESIDENT"


def test_signature_refuses_without_kernel_or_module(tmp_path):
    stream = tmp_path / "s.hip"
    stream.write_text("x")
    base = ["ak-bnsig-r-gpu-20261125", "--task", "x.md:B", "--workload", "/bin/true", "--root", str(tmp_path),
            "--stream-src", str(stream)]
    assert MK.signature_main(base, fetch=lambda r, f: ("c", b"")) == 1
    assert MK.signature_main(base + ["--kernel", "k:1"], fetch=lambda r, f: "missing") == 1
    assert not (tmp_path / "ak-bnsig-r-gpu-20261125").exists()
    with pytest.raises(SystemExit):
        MK.parse_sig_kernel("nobytes")


if __name__ == "__main__":
    raise SystemExit("REFUSING: pytest-fixture suite; run: "
                     "python -m pytest scripts/coordination/tests/test_mk_ak_row_signature.py -q")
