"""AK-BNSIG-P4: the bottleneck-signature planning-context canary, run end to end on the fixture census.

Needs an epyc-inference-research checkout that carries AK-BNSIG P2 (`autokernel/bnsig_planner.py`):
EPYC_RESEARCH, else /workspace/repos/epyc-inference-research. Skipped (never passed) without one.
"""
import json
import os
from pathlib import Path

import pytest

from scripts.vidya.canary import bnsig_context as bc

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "scripts/vidya/tests/fixtures/bnsig_census_fixture.json"
RESEARCH = Path(os.environ.get("EPYC_RESEARCH", "/workspace/repos/epyc-inference-research"))
HAS_P2 = (RESEARCH / "scripts/kernel_rnd/autokernel/bnsig_planner.py").is_file()


def test_expected_reads_the_fixture_hotspot():
    (e,) = bc.expected(FIXTURE)
    assert (e["kernel"], e["primary"]) == ("gemv_q8mf", "issue_bound")
    assert e["ruled_out"] == ["over_fetch", "latency_bound"]


def test_expected_refuses_an_unsigned_census(tmp_path):
    doc = json.loads(FIXTURE.read_text())
    for r in doc["records"].values():
        r.pop("signature")
    p = tmp_path / "c.json"
    p.write_text(json.dumps(doc))
    with pytest.raises(ValueError, match="no signature"):
        bc.expected(p)


def test_scratch_must_be_under_tmp_root():
    with pytest.raises(SystemExit):
        bc.main(["--research", str(RESEARCH), "--census", str(FIXTURE), "--scratch", "/tmp/x"])


@pytest.mark.skipif(not HAS_P2, reason="research checkout lacks AK-BNSIG P2 bnsig_planner.py")
def test_canary_passes_on_fixture(capsys):
    assert bc.main(["--research", str(RESEARCH), "--census", str(FIXTURE),
                    "--scratch", "/mnt/raid0/llm/tmp/bnsig-canary-tests"]) == 0
    out = Path(capsys.readouterr().out.strip())
    receipt = json.loads((out / "receipt.json").read_text())
    assert receipt["status"] == "passed"
    assert receipt["conflict"]["verdict"] == "signature_conflict"
    assert receipt["consistent"]["verdict"] == "consistent"
    assert "| `gemv_q8mf` | issue_bound |" in (out / "planner-context.txt").read_text()
