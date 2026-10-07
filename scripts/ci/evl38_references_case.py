"""One bounded subprocess case for the existing governance-reference validator."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_existing_governance_reference_validator_accepts_pinned_tree() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate" / "validate_agents_references.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "agent reference validation passed"
