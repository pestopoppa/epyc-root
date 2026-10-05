"""Regression coverage for the standalone region-lock status command."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_status_json_is_clean_when_stack_is_stopped(tmp_path: Path) -> None:
    """Status must not bootstrap config/runtime facts just to inspect locks."""
    env = os.environ.copy()
    env.pop("ORCHESTRATOR_TMP_DIR", None)
    env["ORCHESTRATOR_PATHS_TMP_DIR"] = str(tmp_path)

    result = subprocess.run(
        [sys.executable, "-m", "src.runtime.region_lock_cli", "status", "--json"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )

    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert json.loads(result.stdout) == [
        {"region": "q0", "global_held": False, "holders": []},
        {"region": "q1", "global_held": False, "holders": []},
        {"region": "q2", "global_held": False, "holders": []},
        {"region": "q3", "global_held": False, "holders": []},
    ]
