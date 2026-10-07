"""Run the complete candidate gate and retain its exact exit as a separate outcome."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def test_candidate_eval_gate_records_exact_outcome() -> None:
    if os.environ.get("CANDIDATE_EVAL_REQUIRE_DEPS") != "1":
        raise AssertionError("complete dependency mode was not enabled")
    log_path = Path(os.environ["EVL38_GATE_LOG"])
    exit_path = Path(os.environ["EVL38_GATE_EXIT_FILE"])
    runner_temp = Path(os.environ["RUNNER_TEMP"]).resolve()
    for path in (log_path, exit_path):
        if not path.resolve().is_relative_to(runner_temp):
            raise AssertionError("gate outcome artifacts must remain under RUNNER_TEMP")
        if os.path.lexists(path):
            raise AssertionError("gate outcome artifact already exists")

    for name in (
        "EPYC_ORCHESTRATOR_REPO",
        "EPYC_INFERENCE_RESEARCH_REPO",
        "EPYC_LLAMA_REPO",
    ):
        source = Path(os.environ[name])
        if not source.is_dir() or not (source / ".git").exists():
            raise AssertionError(f"required source checkout is absent: {name}")
    for path in (
        ROOT / "repos/epyc-orchestrator",
        ROOT / "repos/epyc-inference-research",
    ):
        if not path.exists():
            raise AssertionError(f"candidate-gate registry input is missing: {path}")

    env = os.environ.copy()
    env.update({"PYTHON": sys.executable, "CANDIDATE_EVAL_REQUIRE_DEPS": "1"})
    with log_path.open("xb") as log:
        result = subprocess.run(
            ["bash", "scripts/validate/candidate_eval_gate.sh"],
            cwd=ROOT,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )
    with exit_path.open("xb") as handle:
        handle.write(f"{result.returncode}\n".encode("ascii"))
    if result.returncode < 0:
        raise AssertionError("candidate gate process was interrupted rather than returning a shell status")
    # A red gate is a legitimate captured result. This expected assertion makes
    # the native CI verifier receipt FALSE for a red gate; the workflow then
    # uploads the originals before reflecting that exact nonzero status.
    assert result.returncode == 0, f"candidate_eval_gate.sh exited {result.returncode}"
