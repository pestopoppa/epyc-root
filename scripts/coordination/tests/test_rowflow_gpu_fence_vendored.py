"""2026-11-26: vendored ak_gate.py op-unit code must not make a CPU ak_gate row look like GPU work."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "rowflow"))
import rowflow as rf  # noqa: E402


def _row(tmp_path, job_argv):
    d = tmp_path / "row"
    d.mkdir()
    (d / "ak_gate.py").write_text('argv = ["perf", "-b", op.get("backend", "ROCm0")]\nGGML_HIP = 1\n')
    (d / "job.py").write_text(f"import ak_gate\nSERVER_ARGV = {job_argv!r}\n")
    (d / "launch.sh").write_text(f"#!/bin/bash\npython3 {d}/job.py\npython3 {d}/ak_gate.py\n")
    return {"launcher": str(d / "launch.sh"), "lane": "cpu", "regions": "q0"}


def test_vendored_harness_is_not_gpu_evidence(tmp_path):
    row = _row(tmp_path, ["llama-server", "-ngl", "0", "-t", "24"])
    assert any(os.path.basename(f) == "ak_gate.py" for f in rf.job_texts(row, {}))   # it IS read ...
    assert rf.gpu_work_evidence(row, {}) == []                                          # ... but not evidence
    assert not rf._kfd_capable(row, {})


def test_row_own_gpu_argv_still_detected(tmp_path):
    row = _row(tmp_path, ["llama-server", "-ngl", "99", "--device", "ROCm0"])
    assert rf.gpu_work_evidence(row, {})
