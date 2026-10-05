from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_scrub_gatelock_narrative_is_retired_fail_closed() -> None:
    repo = Path(__file__).resolve().parents[2]
    script = repo / "scripts" / "maintenance" / "scrub_gatelock_narrative.py"

    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=repo,
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 2
    assert "retired" in result.stderr
    assert "append-only evidence-plane contract" in result.stderr
    assert "scripts/autopilot/scrub_journal.py" in result.stderr
