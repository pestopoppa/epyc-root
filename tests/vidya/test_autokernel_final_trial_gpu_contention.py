"""AKU-07o3: a contention PASS is refused unless foreign GPU consumers are none."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/vidya"))
from adapters import autokernel_final_trial as final  # noqa: E402
from adapters import autokernel_unified_arm as arm  # noqa: E402
from claim_tuple import ProjectionError  # noqa: E402
from test_autokernel_final_trial import _receipt_case, _write  # noqa: E402


def _case(tmp_path, status, gpu):
    parent, receipt, witnesses, evidence, configured, reader, body = _receipt_case(
        tmp_path, "contention", status)
    body["report"] = {"reason": "r", "facts": {"foreign_gpu_consumers": gpu}}
    facts = parent["findings"]["contention"]["facts"]
    facts["report"] = body["report"]
    facts["receipt"]["artifact"] = _write(tmp_path, "gpu", body)
    facts["receipt"]["digest"] = arm._hash(body)
    return parent, receipt, witnesses, evidence, configured, reader


@pytest.mark.parametrize("gpu", [{"status": "present"}, {"status": "unknown"}, "present", []])
def test_contention_pass_refused_when_foreign_gpu_consumers_not_none(tmp_path, gpu):
    with pytest.raises(ProjectionError, match="foreign GPU consumers"):
        final._witness_receipts(*_case(tmp_path, "pass", gpu))


@pytest.mark.parametrize("gpu", [{"status": "none"}, {"status": "not_applicable"}])
def test_contention_pass_allowed_when_none_or_cpu(tmp_path, gpu):
    final._witness_receipts(*_case(tmp_path, "pass", gpu))


def test_present_with_fail_verdict_is_accepted(tmp_path):
    final._witness_receipts(*_case(tmp_path, "fail", {"status": "present"}))
