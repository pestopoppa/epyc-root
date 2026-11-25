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

def _module():
    """The classifier bytes via the profile's own fetch (commit resolved once, then `git show <commit>:<path>`), from the
    shared research clone: origin/main once landed, else the local P1 branch. No worktree path is hardcoded."""
    for ref in filter(None, (os.environ.get("BNSIG_RESEARCH_REF"), "origin/main", "f2-bnsig")):
        got = _show_only(ref)
        if not isinstance(got, str):
            return got[1]
    pytest.skip("bottleneck_signature.py not reachable in the research clone")


def _show_only(ref):
    """fetch_signature_module without its `git fetch` (the test never touches the remote)."""
    import subprocess as sp
    c = sp.run(["git", "-C", MK.RESEARCH_REPO, "rev-parse", "--verify", ref + "^{commit}"], capture_output=True, text=True)
    if c.returncode != 0:
        return "unresolvable"
    r = sp.run(["git", "-C", MK.RESEARCH_REPO, "show", f"{c.stdout.strip()}:{MK.SIG_MODULE_PATH}"], capture_output=True)
    return (c.stdout.strip(), r.stdout) if r.returncode == 0 else "missing"


def test_fetch_resolves_commit_once():
    got = MK.fetch_signature_module(MK.RESEARCH_REPO, "f2-bnsig")
    if isinstance(got, str):
        pytest.skip(got)
    assert len(got[0]) == 40 and b"def signature(" in got[1]


def _mk(tmp_path, rid="ak-bnsig-test-gpu-20261125", extra=()):
    mod = _module()
    stream = tmp_path / "stream2.hip"
    stream.write_text("// stub stream2 source\n")
    args = ["--profile", "signature", rid, "--task", "x.md:BOX", "--kernel", "q8mf6_mul_mat:70041600:106496",
            "--kernel", "q8wt_mul_mat:70041600:26624", "--workload", "/bin/true perf -o MUL_MAT", "--root", str(tmp_path),
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
    wrong = [{"Kernel_Name": "q8wt_mul_mat", "Start_Timestamp": "0", "End_Timestamp": "9", "Grid_Size": "64"}]
    assert J.trace_record(1, 0, wrong)["witness"]["ok"] is False   # resident but the wrong shape


def test_signature_all_unclassified_is_not_a_pass(tmp_path):
    _rc, d = _mk(tmp_path)
    J = _job(d)
    units = [dict(u, gbps=None) if u.get("kind") == "trace" else u
             for u in J.synth(k=dict(J.V5I, SQ_ACTIVE_INST_ANY=0.05, TA_ADDR_STALLED_BY_TC_CYCLES_sum=0.05))]
    v = J.decide(units)
    assert v == "FUTILITY_HARNESS_UNCLASSIFIED" and J.polar(v) is None
    units = [dict(u, witness={"ok": False}) if u.get("kind") == "trace" and u["i"] == 1 else u for u in J.synth()]
    assert J.decide(units) == "FUTILITY_HARNESS_NOT_RESIDENT"


def test_signature_refuses_without_kernel_or_module(tmp_path):
    stream = tmp_path / "s.hip"
    stream.write_text("x")
    base = ["ak-bnsig-r-gpu-20261125", "--task", "x.md:B", "--workload", "/bin/true", "--root", str(tmp_path),
            "--stream-src", str(stream)]
    assert MK.signature_main(base, fetch=lambda r, f: ("c", b"")) == 1
    assert MK.signature_main(base + ["--kernel", "k:1:64"], fetch=lambda r, f: "missing") == 1
    assert not (tmp_path / "ak-bnsig-r-gpu-20261125").exists()
    with pytest.raises(SystemExit):
        MK.parse_sig_kernel("nobytes")
    with pytest.raises(SystemExit):
        MK.parse_sig_kernel("k:100")   # no grid: multi-shape averaging refused


if __name__ == "__main__":
    raise SystemExit("REFUSING: pytest-fixture suite; run: "
                     "python -m pytest scripts/coordination/tests/test_mk_ak_row_signature.py -q")
