"""The E8 quality reseed preparation is intentionally non-writing."""

from __future__ import annotations

from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "artifacts/operator/prepare_e8_quality_baseline_reseed_20260726.sh"


def test_plan_documents_full_pool_evidence_and_no_numeric_derivation() -> None:
    result = subprocess.run(["bash", str(SCRIPT), "--plan"], capture_output=True, text=True)

    assert result.returncode == 0, result.stderr
    assert "dedicated full-pool tier evidence" in result.stdout
    assert "never derive quality baseline values from numeric trials" in result.stdout


def test_script_exposes_no_writing_or_attestation_mode() -> None:
    result = subprocess.run(["bash", str(SCRIPT), "--attest"], capture_output=True, text=True)

    assert result.returncode != 0
    assert "usage: --plan|--validate-only" in result.stderr
