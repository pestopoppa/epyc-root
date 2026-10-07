"""The scheduled native verifier's single assertion: the full root gate exited 0."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def test_candidate_eval_gate_exits_zero() -> None:
    if os.environ.get("CANDIDATE_EVAL_REQUIRE_DEPS") != "1":
        raise AssertionError("complete dependency mode was not enabled")
    required_repos = (
        "EPYC_ORCHESTRATOR_REPO",
        "EPYC_INFERENCE_RESEARCH_REPO",
        "EPYC_LLAMA_REPO",
    )
    missing = [name for name in required_repos if not os.environ.get(name)]
    if missing:
        raise AssertionError(f"required readiness source checkouts are missing: {missing}")
    for name in required_repos:
        if not Path(os.environ[name]).is_dir():
            raise AssertionError(f"configured readiness source checkout is absent: {name}")
    for name in (
        ROOT / "repos/epyc-orchestrator",
        ROOT / "repos/epyc-inference-research",
    ):
        if not name.exists():
            raise AssertionError(f"candidate-gate registry input is missing: {name}")
    env = os.environ.copy()
    env["PYTHON"] = sys.executable
    env["CANDIDATE_EVAL_REQUIRE_DEPS"] = "1"
    result = subprocess.run(
        ["bash", "scripts/validate/candidate_eval_gate.sh"],
        cwd=ROOT,
        env=env,
        check=False,
    )
    assert result.returncode == 0, f"candidate_eval_gate.sh exited {result.returncode}"
