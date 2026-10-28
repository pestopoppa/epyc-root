"""Synthetic capture must reach planning through the normal CLI."""
import json
import subprocess
import sys
from pathlib import Path


def test_producer_cli_planning_and_tamper(tmp_path):
    root = Path(__file__).resolve().parents[2]
    seal = tmp_path / "seal"
    seal.write_text("synthetic runtime seal\n")
    out = tmp_path / "canary"
    subprocess.run([sys.executable, str(root / "scripts/vidya/ufh12_irt_paired_canary.py"),
                    "--out", str(out), "--runtime-seal", str(seal)], check=True)
    receipt = json.loads((out / "canary-receipt.json").read_text())
    assert receipt["status"] == "passed"
    assert receipt["planning_context"] == "visible"
    assert receipt["real_model_fixture_claims"] == 0
    assert str(root / "scripts/vidya/cli.py") in receipt["pins"]
