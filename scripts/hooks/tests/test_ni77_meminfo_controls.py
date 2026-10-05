"""Stage ordinary files through the real hook; runtime errors are never BLOCKs."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
HOOK = ROOT / "scripts/hooks/pii_precommit.sh"
FIXTURE = ROOT / "research/fixtures/pii_ni77_meminfo_controls.jsonl"
ROWS = [json.loads(line) for line in FIXTURE.read_text().splitlines() if line]


def _load_evaluator():
    spec = importlib.util.spec_from_file_location(
        "ni77_fixture_evaluator", ROOT / "scripts/validate/pii_fixture_eval.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def staged_evaluator(tmp_path_factory):
    evaluator = _load_evaluator()
    capture = tmp_path_factory.mktemp("ni77-private-originals")
    os.chmod(capture, 0o700)
    (capture / "hook.original.sh").write_bytes(HOOK.read_bytes())
    (capture / "controls.original.jsonl").write_bytes(FIXTURE.read_bytes())
    for path in capture.iterdir():
        path.chmod(0o600)
    original_run = evaluator._run
    commands = []

    def bounded_run(cmd, cwd, *, check=True):
        assert cwd.stat().st_mode & 0o777 == 0o700
        assert cwd.stat().st_uid == os.getuid()
        bound = 30 if cmd[0] == str(HOOK) else 10
        proc = subprocess.run(
            ["timeout", "--signal=TERM", "--kill-after=5s", f"{bound}s", *cmd],
            cwd=cwd, check=False, text=True, capture_output=True, timeout=bound + 10,
        )
        number = len(commands)
        record = {"argv": cmd, "cwd": str(cwd), "returncode": proc.returncode,
                  "stdout": proc.stdout, "stderr": proc.stderr}
        commands.append(record)
        path = capture / f"command-{number:04d}.json"
        path.write_text(json.dumps(record, indent=2) + "\n")
        path.chmod(0o600)
        if cmd[0] == str(HOOK):
            labels = re.findall(r"^BLOCKED: case_\d+\.txt:\d+: \[(account_number|secret)\]", proc.stderr, re.M)
            assert proc.returncode in (0, 1), record
            assert bool(labels) == (proc.returncode == 1), record
            assert not re.search(r"unbound variable|syntax error|Traceback|command not found", proc.stderr), record
        if check:
            proc.check_returncode()
        return proc

    evaluator._run = bounded_run
    try:
        # Preserve all existing fixture labels and run the same real staging path.
        baseline = evaluator.load_rows(evaluator.DEFAULT_FIXTURE)
        results = evaluator.evaluate(baseline, HOOK)
        sides = evaluator.summarize(results)
        assert sides.fa_errors == 0 and sides.fr_errors == 0
        baseline_report = capture / "baseline-report.json"
        baseline_report.write_text(json.dumps({"rows": len(results), "false_accept": sides.fa_errors,
                                               "false_reject": sides.fr_errors}, indent=2) + "\n")
        baseline_report.chmod(0o600)
        yield evaluator, commands
    finally:
        evaluator._run = original_run


@pytest.mark.parametrize("row", ROWS, ids=[row["id"] for row in ROWS])
def test_ni77_staged_meminfo_control(staged_evaluator, row):
    evaluator, commands = staged_evaluator
    result = evaluator.evaluate([row], HOOK)[0]
    assert result.actual_block == row["expected_match"]
    hook_call = next(record for record in reversed(commands) if record["argv"][0] == str(HOOK))
    if row["expected_match"]:
        for label in evaluator.row_labels(row):
            assert re.search(rf"^BLOCKED: case_01\.txt:\d+: \[{label}\]", hook_call["stderr"], re.M)
